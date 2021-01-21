from django.db import models
from django.utils import timezone
from constance import config


class StatusDeleteMixin(models.Model):
    """ Абстрактная модель для пометки объекта как удаленного """
    is_deleted = models.BooleanField('Удален', default=False, blank=True, db_index=True)
    date_deleted = models.DateTimeField('Дата удаления', default=None, blank=True, null=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """ Переопределение удаления объекта """
        if kwargs.get('force_delete'):
            del kwargs['force_delete']
            return super(StatusDeleteMixin, self).delete(*args, **kwargs)
        self.is_deleted = True
        self.date_deleted = timezone.datetime.now()
        self.save()
        return None

    def restore(self):
        """ Восстановление объекта """
        self.is_deleted = False
        self.date_deleted = None
        self.save()

    @staticmethod
    def get_deleted_query(user=None):
        """ Возвращает запрос на просмотр удаленных объектов """
        if user and user.is_authenticated:
            # округляю дату дедлайна до десятков минут чтобы не забивать кеш запросов разными значениями дат
            date_deadline = timezone.datetime.now() - timezone.timedelta(minutes=config.SHOW_DELETED_MINUTES)
            date_deadline = date_deadline.replace(minute=date_deadline.minute // 10 * 10, second=0, microsecond=0)
            return models.Q(is_deleted=False) | models.Q(is_deleted=True, date_deleted__gte=date_deadline)
        else:
            return models.Q(is_deleted=False)