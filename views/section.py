"""
API разделов сайта
"""
import logging
import traceback

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.transaction import atomic
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import filters, mixins, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from main.api.general import (DestroyManyMixin, IdsFilter, InfiniteMixin,
                              PageSizeMixin)
from main.api.mixins.status_delete import StatusDeleteMixin
from main.api.permissions import IsStaff, ReadObjectPermission
from main.models import Section, SectionSettings, Site
from main.serializers.section import (SectionHierarchySerializer,
                                      SectionSerializer,
                                      SectionStaffSerializer)
from main.serializers.section_settings import SectionSettingsSerializer

logger = logging.getLogger('debug')


class SectionFilter(FilterSet):
    class Meta:
        model = Section
        fields = {
            'id': ['exact'],
            'title': ['istartswith', 'iendswith', 'icontains', 'exact'],
            'code': ['exact', 'istartswith', 'iendswith', 'icontains'],
            'parent': ['exact'],
            'parent__code': ['exact', 'istartswith', 'iendswith', 'icontains'],
            'can_deactivate': ['exact'],
            'is_global': ['exact'],
            'template': ['exact'],
            'is_deleted': ['exact'],
        }


class BaseSectionView(StatusDeleteMixin, PageSizeMixin, ModelViewSet):
    """
    Базовый API разделов сайта
    """
    serializer_class = SectionSerializer
    permission_classes = [ReadObjectPermission]
    page_size = 30
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, IdsFilter, filters.OrderingFilter)
    filter_class = SectionFilter
    search_fields = ('title', )
    ordering = ["tree_id", "lft", "order"]
    ordering_fields = ('order', 'ordering', 'tree_id', 'lft')
    _ignore_model_permissions = True

    def get_queryset(self):
        return Section.objects.all()


class SectionView(BaseSectionView):
    """
    Публичный API разделов сайта
    """

    ordering = ["tree_id", "lft", "ordering", "order"]

    def _get_current_site(self, request):
        site = request.site

        # передача текущего сайта через параметр для администраторов
        if not site and request.user.is_staff:
            if request.GET.get('current_site'):
                try:
                    site = Site.objects.get(id=request.GET.get('current_site'))
                except ObjectDoesNotExist:
                    pass
        return site

    def get_queryset(self):
        site = self._get_current_site(self.request)

        query = Section.get_deleted_query(self.request.user)
        if site:
            query &= Section.get_filter_query_by_site(site)
        else:
            if not self.request.user.is_staff:
                query &= Q(id__isnull=True)
        return super(SectionView, self).get_queryset().filter(query)\
            .extra(
                **Section.get_extrafilter_ordering_by_site(site)
            )\
            .prefetch_related('settings')\
            .order_by('ordering', 'order')\
            .distinct()

    def perform_create(self, serializer):
        if not self.request.site:
            logger.error('Нет текущего сайта')
            logger.error(traceback.format_exc())
            raise APIException('Нет текущего сайта')

        if not self.request.site.template:
            logger.error('У сайта не установлен шаблон')
            logger.error(traceback.format_exc())
            raise APIException('У сайта не установлен шаблон')

        serializer.save(template=self.request.site.template)
        serializer.instance.sites.add(self.request.site)
        serializer.instance.clear_cache()
        if not self.request.user.has_perm('main.add_section', serializer.instance):
            raise PermissionDenied()

    def perform_update(self, serializer):
        serializer.save()
        if not self.request.user.has_perm('main.change_section', serializer.instance):
            raise PermissionDenied()

    @action(detail=False, methods=['get'], url_name='hierarchy')
    def hierarchy(self, request, *args, **kwargs) -> Response:
        """ Возвращает сериализованное дерево разделов """
        site = self._get_current_site(self.request)

        # получение разделов первого уровня
        query = Q(level=0, is_deleted=False)
        if request.GET.get('code'):
            query = Q(code=request.GET.get('code'))
        items = self.get_queryset().filter(query)
        if request.GET.get('is_active') == 'true' and site:
            # фильтрация отключенных в админке разделов
            items = items.extra(
                **Section.get_extrafilter_active_by_site(site)
            )

        # получение всех разделов сайта для постороения иерархии
        query = Q(is_deleted=False)
        all_items = self.get_queryset().filter(query)
        if request.GET.get('is_active') == 'true' and site:
            # фильтрация отключенных в админке разделов
            all_items = all_items.extra(
                **Section.get_extrafilter_active_by_site(site)
            )

        serializer_context = self.get_serializer_context()
        serializer_context.update({
            'sections': list(all_items)
        })

        return Response(SectionHierarchySerializer(items, many=True, context=serializer_context).data)

    @action(detail=False, methods=['get'], url_name='slug')
    def slug(self, request, *args, **kwargs):
        items = self.get_queryset().filter(code=request.GET.get('slug'))
        if items:
            serializer_class = self.get_serializer_class()
            return Response(serializer_class(items[0], context=self.get_serializer_context()).data)
        else:
            raise NotFound()

    @action(methods=['post'], detail=True, url_path='settings', permission_classes=[IsAuthenticated])
    @atomic
    def set_settings(self, request, *args, **kwargs):
        section = self.get_object()
        if not request.user.has_perm('main.change_site', request.site):
            raise PermissionDenied()
        settings = section.get_settings(request.site)
        if not settings:
            settings = SectionSettings.objects.create(
                site=request.site,
                section=section,
            )
        serializer = SectionSettingsSerializer(instance=settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SectionSerializer(section, context=self.get_serializer_context()).data)

    @action(detail=False, methods=['post'], url_name='save_ordering')
    def save_ordering(self, request, *args, **kwargs):
        """ Сохранение порядка сортировки элементов """
        if request.user.has_perm('main.change_site', request.site):
            try:
                result = []
                for item in request.data:
                    section = Section.objects.filter(Section.get_filter_query_by_site(request.site) & Q(id=item['id'])).first()
                    if section:
                        if item['order'] or item['order'] == 0:
                            settings = section.get_settings(request.site, cache=False)
                            if not settings:
                                settings = SectionSettings.objects.create(
                                    site=request.site,
                                    section=section,
                                )
                            settings.order = item['order']
                            settings.save()
                        result.append(section)
                return Response(SectionSerializer(result, many=True, context=self.get_serializer_context()).data)
            except:
                logger.error('Ошибка в отправляемых данных сортировки')
                logger.error(traceback.format_exc())
                raise serializers.ValidationError('Ошибка в отправляемых данных сортировки')
        else:
            raise PermissionDenied()


class SectionStaffView(InfiniteMixin, DestroyManyMixin, BaseSectionView):
    """
    API разделов сайта для администраторов
    """
    serializer_class = SectionStaffSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        site = None
        query = Q()
        if self.request.GET.get('site'):
            try:
                site = Site.objects.get(id=self.request.GET.get('site'))
            except ObjectDoesNotExist:
                pass
        if site:
            query &= Section.get_filter_query_by_site(site)
                 
        return super(SectionStaffView, self).get_queryset()\
            .filter(query)\
            .select_related('template')\
            .prefetch_related('sites')
