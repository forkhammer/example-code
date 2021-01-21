"""
Модуль модели регионов России
"""
import reversion
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django_extensions.db.fields import AutoSlugField
from mptt.models import MPTTModel, TreeForeignKey
from slugify import slugify

from .accessory import AccessoryMixin
from .page_meta import PageMeta
from .site import Site
from .site_template import SiteTemplate
from .status_delete_model import StatusDeleteMixin
from .user import User
from .parents_mixin import ParentsMixin


@reversion.register()
class Section(ParentsMixin, StatusDeleteMixin, AccessoryMixin, MPTTModel):
    """
    Модель разделов сайта
    """
    title = models.CharField('Наименование', max_length=250, db_index=True)
    parent = TreeForeignKey('self', verbose_name='Родитель', default=None, 
                            blank=True, null=True, on_delete=models.CASCADE, related_name='children')
    code = AutoSlugField(populate_from=['_get_slug'], overwrite=False, overwrite_on_add=False, editable=True, db_index=True)
    template = models.ForeignKey(SiteTemplate, verbose_name='Шаблон',
                                default=None, blank=True, null=True, on_delete=models.CASCADE)
    sites = models.ManyToManyField(Site, verbose_name='Принадлежность к сайтам', blank=True, related_name='sections')
    is_global = models.BooleanField('Глобальный раздел?', default=False, blank=True)
    path = models.CharField('Путь к странице на сайте', max_length=250, default='', blank=True)
    can_deactivate = models.BooleanField('Может быть выключена на сайте', default=True, blank=True)
    is_default_active = models.BooleanField('По-умолчанию включен', default=True, blank=True)
    order = models.PositiveIntegerField('Индекс сортировки', default=100, blank=True, db_index=True)
    ext_id = models.CharField('Внешний идентификатор', max_length=250, default=None, blank=True, null=True, 
                                db_index=True)

    page_meta = GenericRelation(PageMeta, related_query_name='section')
    placeholders = GenericRelation('Placeholder')

    class Meta:
        verbose_name = 'Раздел сайта'
        verbose_name_plural = 'Разделы сайтов'
        unique_together = (
            ('code', 'template'),
        )
        permissions = [
            ('can_control_section', 'Управление содержимым раздела'),
        ]

    class MPTTMeta:
        order_insertion_by = ['order']

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return str(self.id)

    def _get_slug(self) -> str:
        """ Возвращает символьный код """
        result = slugify(self.title)
        return result

    @property
    def url(self) -> str:
        """ Возвращает URL раздела сайта """
        if not self.path:
            return f'/{self.code}'
        else:
            return self.path

    def get_absolute_url(self):
        return self.url

    @staticmethod
    def get_filter_query_by_site(site: Site):
        """ Возвращает фильтр ORM для выборки разделов по сайту """
        return (Q(template=site.template) if site else Q() )\
             & (Q(is_global=True) | (Q(sites=site) if site else Q()))

    @staticmethod
    def get_extrafilter_ordering_by_site(site: Site):
        """ Возвращает queryset extra для выборки данных сортировки """
        return {
            'select': {
                'ordering': """
                    SELECT ordsel.order FROM (
                        SELECT settings.order as order, 0 as ord FROM main_sectionsettings as settings
                        WHERE settings.section_id=main_section.id and settings.site_id=%s

                        UNION

                        SELECT 100 as order, 1 as ord
                    ) as ordsel ORDER BY ordsel.ord LIMIT 1
                """
            },
            'select_params': (site.id if site else 0, )
        }

    @staticmethod
    def get_extrafilter_active_by_site(site: Site):
        """ Возвращает queryset extra для фильтрации активных разделов """
        return {
            'where': ["""
                (
                    SELECT sq1.is_active FROM (
                        SELECT main_sectionsettings.is_active as is_active, 0 as ord FROM main_sectionsettings
                        WHERE main_sectionsettings.section_id=main_section.id and main_sectionsettings.site_id=%s

                        UNION

                        SELECT main_section.is_default_active as is_active, 1 as ord

                        UNION

                        SELECT true as is_active, 2 as ord
                    ) as sq1 ORDER BY sq1.ord ASC LIMIT 1
                ) = true
            """ % (site.id if site else 0, )]
        }

    def has_write_access(self, site: Site, user: User) -> bool:
        """ Возвращает флаг доступа на редактирование раздела для пользователя """
        if not site:
            return False
        if not user:
            return False
        if not user.is_authenticated:
            return False
        return self.id in user.get_sections_access_write_list(site)

    def get_settings(self, site: Site, cache: bool = True):
        """ Возвращает объект настроек раздела для сайта """
        from main.models.section_settings import SectionSettings
        if not cache:
            return SectionSettings.objects.filter(section=self, site=site).nocache().first()
        else:
            return SectionSettings.objects.filter(section=self, site=site).first()

    def is_active(self, site: Site) -> bool:
        """ Возвращает флаг доступности раздела для пользотвалей """
        if self.can_deactivate:
            settings = self.get_settings(site)
            # Если есть настройки то беру флаг оттуда, если нет то по умолчанию включено
            return settings.is_active if settings else self.is_default_active
        return True

    def clear_cache(self, site: Site = None):
        """ Очистка кеша """
        pass

    @staticmethod
    def has_perm(obj, perm, user, site) -> bool:
        from .site_right import SiteRight
        if not obj:
            return False

        if perm == 'main.can_control_section':
            if obj.is_global or obj.sites.filter(id=site.id).count() > 0:
                rights = user.get_rights_for_site(site)
                if rights:
                    if rights.rights_type == SiteRight.RightType.FULL:
                        return True
                    else:
                        if obj:
                            return rights.sections.filter(id=obj.id).count() > 0
                        else:
                            return True
        else:
            if not obj.is_global:
                if obj.sites.filter(id=site.id).count() > 0:
                    rights = user.get_rights_for_site(site)
                    if rights:
                        if rights.rights_type == SiteRight.RightType.FULL:
                            return True
        return False

    def get_serialized_parents(self, include_self=True, site: Site = None):
        from main.serializers.section import SectionParentSerializer
        return SectionParentSerializer(self.get_ancestors(include_self=include_self), many=True, context={'site': site}).data
