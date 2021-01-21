"""
Сериализаторы модели разделов сайта
"""
import typing
from rest_framework import serializers
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from main.models import Section
from .section_settings import SectionSettingsSerializer
from .site_template import BaseSiteTemplateSerializer
from .site import Site


class BaseSectionSerializer(serializers.ModelSerializer):
    """ Базовый сериализатор разделов сайта """
    class Meta:
        model = Section
        fields = (
            'id',
            'title',
            'code',
            'level',
            'url',
            'is_global',
            'is_deleted',
        )


class SectionParentSerializer(serializers.ModelSerializer):
    """ Сериализатор для хлебных крошек раздела """
    settings = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = (
            'id',
            'title',
            'code',
            'level',
            'url',
            'is_global',
            'settings',
            'is_deleted',
        )

    def get_settings(self, obj: Section):
        if self.context.get('site'):
            settings = obj.get_settings(self.context.get('site'))
            return SectionSettingsSerializer(settings).data if settings else None
        elif self.context.get('request') and self.context.get('request').site:
            settings = obj.get_settings(self.context.get('request').site)
            return SectionSettingsSerializer(settings).data if settings else None
        return None


class SectionSerializer(BaseSectionSerializer):
    """ Публичный сериализатор разделов сайта """
    is_active = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    can_change = serializers.SerializerMethodField()
    can_view = serializers.SerializerMethodField()

    class Meta(BaseSectionSerializer.Meta):
        fields = (
            'id',
            'parent',
            'title',
            'code',
            'level',
            'url',
            'is_active',
            'is_global',
            'parents',
            'settings',
            'can_deactivate',
            'can_change',
            'can_view',
            'is_deleted',
        )

        read_only_fields = (
            'code',
            'level',
            'url',
            'is_global',
            'can_deactivate',
            'is_deleted',
        )

    def get_is_active(self, obj):
        if self.context.get('request'):
            return obj.is_active(self.context.get('request').site)
        return False

    def get_parents(self, obj: Section) -> typing.List[dict]:
        return SectionParentSerializer(obj.get_ancestors(ascending=False), many=True, context=self.context).data

    def get_settings(self, obj: Section):
        if self.context.get('request'):
            settings = obj.get_settings(self.context.get('request').site)
            return SectionSettingsSerializer(settings).data if settings else None
        return None

    def get_can_change(self, obj: Section) -> bool:
        """ Сериализует флаг возможности редактирования """
        if self.context.get('request'):
            user = self.context['request'].user
            return user.has_perm('main.change_section', obj)
        else:
            return False

    def get_can_view(self, obj: Section) -> bool:
        """ Сериализует флаг возможности просмотра """
        if self.context.get('request'):
            site = self.context['request'].site
            return obj.is_active(site) if site else False
        else:
            return False


class SectionHierarchySerializer(SectionSerializer):
    """ Публичный сериализатор разделов сайта с иерархией """
    children = serializers.SerializerMethodField()

    class Meta(SectionSerializer.Meta):
        fields = (
            'id',
            'parent',
            'title',
            'code',
            'level',
            'url',
            'children',
            'is_active',
            'is_global',
            'settings',
            'can_deactivate',
            'can_change',
            'is_deleted',
        )

        read_only_fields = (
            'code',
            'level',
            'url',
            'is_global',
            'can_deactivate',
            'is_deleted',
        )

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

    def get_children(self, obj: Section) -> typing.List[dict]:
        """ Возвращает потомков сериализованных потомком пункта меню """
        result = []
        if 'sections' in self.context:
            # получение дочерних разделов из контекста сверху
            children_items = list(filter(lambda i: i.parent_id == obj.id, self.context['sections']))
            if len(children_items) > 0:
                result = SectionHierarchySerializer(children_items, many=True, context=self.context).data
        else:
            # получение дочерних разделов запросом в БД
            request = self.context.get('request')
            site = self._get_current_site(request) if request else None
            query = Q(is_deleted=False) & Section.get_filter_query_by_site(site if site else None)
            queryset = obj.get_children()\
                .extra(
                    **Section.get_extrafilter_ordering_by_site(site)
                )\
                .filter(query)\
                .prefetch_related('settings')\
                .order_by('ordering', 'order')\
                .distinct()

            # фильтрация отключенных разделов в адмикнке сайта
            if request and site and request.GET.get('is_active') == 'true':
                queryset = queryset.extra(
                    **Section.get_extrafilter_active_by_site(site)
                )
            result = SectionHierarchySerializer(queryset, many=True, context=self.context).data
        return result


class SectionStaffSerializer(BaseSectionSerializer):
    """ Сериализатор разделов сайта для администраторов """
    template_detail = serializers.SerializerMethodField()

    class Meta(BaseSectionSerializer.Meta):
        fields = (
            'id',
            'title',
            'code',
            'parent',
            'level',
            'path',
            'sites',
            'is_global',
            'url',
            'can_deactivate',
            'is_default_active',
            'template',
            'template_detail',
            'order',
            'is_deleted',
        )
        read_only_fields = (
            'level',
        )

    def get_template_detail(self, obj: Section) -> dict:
        return BaseSectionSerializer(obj.template).data if obj.template_id else None
