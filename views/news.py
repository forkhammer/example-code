"""
API новостей
"""
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import filters
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Case, IntegerField, When
from django.conf import settings
from django.utils import timezone

from main.api.general import DestroyManyMixin, IdsFilter, PageSizeMixin, InfiniteMixin
from main.api.permissions import IsStaff, ReadObjectPermission
from main.api.mixins.status_delete import StatusDeleteMixin
from main.models import News, Section
from main.serializers.news import NewsSerializer, NewsStaffSerializer, NewsKindergartenSerializer, NewsPortalSerializer, NewsListStaffSerializer


class NewsFilter(FilterSet):
    class Meta:
        model = News
        fields = {
            'id': ['exact'],
            'section': ['exact'],
            'section__code': ['exact'],
            'site': ['exact'],
            'is_chronicles': ['exact'],
            'is_mailing': ['exact'],
            'is_top': ['exact'],
            'title': ['exact', 'istartswith', 'iendswith', 'icontains'],
        }


class BaseNewsView(StatusDeleteMixin, PageSizeMixin, ModelViewSet):
    """
    Базовый API новостей
    """
    serializer_class = NewsSerializer
    permission_classes = [ReadObjectPermission]
    page_size = 10
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, IdsFilter, filters.OrderingFilter)
    filter_class = NewsFilter
    search_fields = ('title', )
    ordering = '-date_publish'
    ordering_fields = ('id', 'date_created', 'date_modified', 'date_publish', 'is_top', 'date_top', 'top_order')

    def get_queryset(self):
        query = Q()
        if self.request.GET.get('year'):
            try:
                year = int(self.request.GET.get('year'))
            except TypeError:
                year = None

            month = None
            if self.request.GET.get('month'):
                try:
                    month = int(self.request.GET.get('month'))
                except TypeError:
                    month = None

            if year:
                start_year = timezone.datetime(year=year, month=1, day=1)
                end_year = timezone.datetime(year=year, month=12, day=31)
                if month:
                    start_year = timezone.datetime(year=year, month=month, day=1)
                    end_year = (timezone.datetime(year=year, month=month, day=1) + timezone.timedelta(days=31)).replace(day=1) - timezone.timedelta(days=1)

                query &= Q(date_publish__range=(start_year, end_year))
        queryset = News.objects.filter(query)\
            .select_related('image', )
        queryset = queryset.annotate(
            top_order=Case(
                When(Q(is_top=True) & (Q(date_top__gt=timezone.datetime.now()) | Q(date_top__isnull=True)), then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        return queryset


class NewsView(BaseNewsView):
    """
    Публичный API раздела файлов
    """
    def get_queryset(self):
        site = self.request.site
        query = Q()
        query &= News.get_deleted_query(self.request.user)
        query &= News.get_published_query(self.request.user)
        if site:
            query &= Q(site=site)
        elif settings.IS_PORTAL_SITE:
            query &= Q(site__isnull=True)
        else:
            query &= Q(id__isnull=True)
        return super(NewsView, self).get_queryset().filter(query)

    def get_serializer_class(self):
        if settings.IS_PORTAL_SITE:
            return NewsPortalSerializer
        else:
            return NewsKindergartenSerializer
        return super(NewsView, self).get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(site=self.request.site)
        if not self.request.user.has_perm('main.add_news', serializer.instance):
            raise PermissionDenied()

    def perform_update(self, serializer):
        serializer.save()
        if not self.request.user.has_perm('main.change_news', serializer.instance):
            raise PermissionDenied()

    @action(detail=False, methods=['GET'], url_path='stats')
    def stats(self, request, *args, **kwargs):
        """ Возвращает статистику по разделу новостей """

        news_queryset = self.get_queryset()
        if self.request.GET.get('is_chronicles') == 'true':
            news_queryset = news_queryset.filter(is_chronicles=True)

        queryset = news_queryset.extra(
            select={'year': 'date_part(\'year\', main_news.date_publish)'}
        ).values_list('year').distinct()

        month_queryset = news_queryset.extra(
            select={
                'year': 'date_part(\'year\', main_news.date_publish)',
                'month': 'date_part(\'month\', main_news.date_publish)'
            }
        ).values_list('year', 'month').distinct()
        return Response({
            'years': sorted(set([item[0] for item in queryset])),
            'months': list(month_queryset)
        })

    @action(detail=True, methods=['POST'], url_name='copy_chronicles')
    def copy_chronicles(self, request, *args, **kwargs):
        news = self.get_object()
        if request.user.has_perm('main.add_news', news):
            new_obj = news.copy_chronicles()
            return Response(NewsKindergartenSerializer(new_obj).data)
        else:
            raise PermissionDenied()



class NewsStaffView(InfiniteMixin, DestroyManyMixin, BaseNewsView):
    """
    API раздела файлов для администраторов
    """
    serializer_class = NewsStaffSerializer
    permission_classes = [IsStaff]
    page_size = 30

    def get_serializer_class(self):
        if self.action == 'list':
            return NewsListStaffSerializer
        return super(NewsStaffView, self).get_serializer_class()

    def get_queryset(self):
        return super(NewsStaffView, self).get_queryset()\
                    .select_related('site')
