"""
Модуль модели новости
"""
import logging
import traceback
from django.db import models
from django_extensions.db.fields import AutoSlugField
from slugify import slugify
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField
from django.utils import timezone
import reversion
from django.contrib.contenttypes.fields import GenericRelation
from django.dispatch import receiver
from django.db.models.signals import post_save

from main.models import NewsSection, Site, Placeholder, Image
from main.models.include.image_transform import ImageTransform
from main.models.fields import SanitizedHTMLField

from .status_delete_model import StatusDeleteMixin
from .accessory import AccessoryMixin
from .search_model import SearchMixin


logger = logging.getLogger('debug')


@reversion.register()
class News(SearchMixin, AccessoryMixin, StatusDeleteMixin, models.Model):
    """
    Модель новостей
    """
    title = models.TextField('Наименование', max_length=250, default='')
    preview = SanitizedHTMLField(verbose_name='Текст', default='', blank=True, strip=True)
    show_preview_on_detail = models.BooleanField('Показывать анонс в детальной записи', default=False, blank=True)
    body = models.TextField('Текст новости', default='', blank=True)
    image = models.ForeignKey(ImageTransform, verbose_name='Изображение', default=None, 
        blank=True, null=True, on_delete=models.SET_DEFAULT)
    slug = AutoSlugField(populate_from=['_get_slug'], overwrite=True)
    section = models.ForeignKey(NewsSection, verbose_name='Раздел новостей', default=None, blank=True, null=True, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, verbose_name='Сайт', default=None, blank=True, null=True, on_delete=models.CASCADE)
    date_created = CreationDateTimeField('Дата создания', db_index=True, blank=True)
    date_modified = ModificationDateTimeField('Дата последнего изменения', db_index=True, blank=True)
    date_publish = models.DateTimeField('Дата публикации', default=timezone.datetime.now, blank=True, null=True, db_index=True)
    is_chronicles = models.BooleanField('Находиться в летописи', default=False, blank=True, db_index=True) 
    is_mailing = models.BooleanField('В рассылке', default=False, blank=True, db_index=True)
    date_mailing = models.DateTimeField('Время рассылки', default=None, blank=True, null=True)
    is_top = models.BooleanField('В топе', default=False, blank=True, db_index=True)
    date_top = models.DateField('Дата нахождения в топе (включительно)', default=None, blank=True, null=True)
    ext_id = models.CharField('Внешний идентификатор', max_length=250, default=None, blank=True, null=True, 
                                db_index=True)

    placeholders = GenericRelation(Placeholder)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ('title', )

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return str(self.id)

    def _get_slug(self) -> str:
        """ Возвращает символьный код """
        result = slugify(self.title)
        if self.site_id:
            result += '-' + str(self.site_id)
        return result

    def save(self, *args, **kwargs):
        if not self.date_publish:
            self.date_publish = timezone.now()
        return super(News, self).save(*args, **kwargs)

    @property
    def url(self):
        return f'/news/detail/{self.slug}__{self.id}'

    def get_absolute_url(self):
        return self.url

    @property
    def is_top_expired(self):
        """
        Возвращает флаг что важность новости истекла
        """
        if self.is_top:
            if (self.date_top is not None) and (self.date_top < timezone.datetime.now().date()):
                return True
        return False

    @property
    def search_text(self):
        result = self.preview
        placeholders = self.placeholders.all()
        if placeholders:
            result += ' ' + placeholders[0].text
        return result

    @staticmethod
    def has_perm(obj, perm, user, site) -> bool:
        from .site_right import SiteRight
        
        rights = user.get_rights_for_site(site)
        if rights:
            if rights.rights_type == SiteRight.RightType.FULL:
                return True
            else:
                return rights.sections.filter(code='news').count() > 0
        return False

    def copy_chronicles(self):
        """ Создает копию новости в летописи """
        placeholders = self.placeholders.all()[:1]
        placeholder = placeholders[0].duplicate() if placeholders else None

        self.id = None
        self.pk = None
        self.is_chronicles = True
        self.save()

        if placeholder:
            self.placeholders.all().delete()
            placeholder.node = self
            placeholder.code = f'news_{self.id}'
            placeholder.save()
        return self

    @staticmethod
    def get_published_query(user=None):
        """ Возвращает запрос на просмотр удаленных объектов """
        current = timezone.datetime.now()
        if user and user.is_authenticated:
            return models.Q()
        else:
            return models.Q(date_publish__lte=current)
    

@receiver(post_save, sender=News, weak=False)
def news_post_save(instance: News, created, **kwargs):
    from .mailing import Mailing
    from main.documents.news import NewsDocument

    if created:
        # создаю прейсхолжер для содержимого новости
        Placeholder.objects.create(
            code=f'news_{instance.id}',
            node=instance,
            site=instance.site
        )

    # обновление поискового индекса
    try:
        if instance.is_deleted:
            NewsDocument().update(instance, action='delete')
        else:
            NewsDocument().update(instance)
    except:
        logger.error('Error update search index for news')
        logger.error(traceback.format_exc())

    # обновление рассылки
    if instance.is_mailing and not instance.is_deleted:
        if not instance.mailings.all().exists():
            Mailing.objects.create(
                site=instance.site,
                title=instance.title,
                is_active=True,
                method=Mailing.TimeMethod.AUTO,
                category=Mailing.Category.NEWS,
                news=instance
            )
    else:
        instance.mailings.all().delete()