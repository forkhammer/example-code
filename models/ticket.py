"""
Модуль модели обращений
"""
from django.db import models
from django.utils import timezone
from django_extensions.db.fields import CreationDateTimeField
import reversion
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.contenttypes.fields import GenericRelation

from main.models import User, Site
from main.models.status_delete_model import StatusDeleteMixin
from main.models.accessory import AccessoryMixin
from main.models.user_include import UserInclude
from main.models.chat_thread import ChatThread
from main.models.chat_message import ChatMessage


@reversion.register()
class Ticket(StatusDeleteMixin, AccessoryMixin, models.Model):
    """
    Модель тикета для пользователя
    """
    class Status:
        NEW = 'n'
        OPEN = 'o'
        CLOSED = 'c'
        RESOLVED = 'r'
        CANCELLED = 's'

        @classmethod
        def to_dict(cls):
            return {
                cls.NEW: 'Новая',
                cls.OPEN: 'В работе',
                cls.CLOSED: 'Закрыт',
                cls.RESOLVED: 'Исполнен',
                cls.CANCELLED: 'Отменен',
            }

    class TicketType:
        TECH = 't'
        ACTIVATE = 'a'
        SECTION = 's'
        NEWSITE = 'n'
        REVIEW = 'r'
        DOC = 'd'
        MONITORING = 'm'

        @classmethod
        def to_dict(cls):
            return  {
                cls.TECH: 'Технические проблемы',
                cls.ACTIVATE: 'Активация сайта',
                cls.SECTION: 'Работа с разделами',
                cls.NEWSITE: 'Создание нового сайта',
                cls.REVIEW: 'Отзыв, предложение',
                cls.DOC: 'Публикация муниципальных и региональных документов',
                cls.MONITORING: 'Экспертный мониторинг контента',
            }

    site = models.ForeignKey(Site, verbose_name='Сайт', default=None, blank=True, null=True, on_delete=True)
    title = models.CharField('Заголовок', max_length=250, default='', blank=False)
    body = models.TextField('Описание', default='', blank=False)
    date_created = CreationDateTimeField('Дата создания', db_index=True)
    sender = models.ForeignKey(User, verbose_name='Отправитель', default=None, blank=True, null=True, on_delete=models.CASCADE, related_name='ticket_sender')
    includes = models.ManyToManyField(UserInclude, verbose_name='Приложения', blank=True)
    status = models.CharField('Статус', max_length=1, choices=list(Status.to_dict().items()), default=Status.NEW, blank=True)
    ticket_type = models.CharField('Тип заявки', max_length=1, choices=list(TicketType.to_dict().items()))
    count_new_user = models.PositiveIntegerField('Количество новых сообщений для пользователей', default=0, blank=True, db_index=True)
    count_new_staff = models.PositiveIntegerField('Количество новых сообщений для модераторов', default=0, blank=True, db_index=True)

    threads = GenericRelation(ChatThread)

    class Meta:
        verbose_name = 'Тикет'
        verbose_name_plural = 'Тикеты'
        ordering = ('date_created',)
        permissions = [
            ('comment_ticket', 'Возможность комментирования'),
        ]

    def __str__(self) -> str:
        return f'Тикет №{self.id} от {self.date_created}'

    def __repr__(self) -> str:
        return str(self.id)

    @property
    def status_human(self):
        return self.Status.to_dict().get(self.status)

    @property
    def ticket_type_human(self):
        return self.TicketType.to_dict().get(self.ticket_type)

    @staticmethod
    def has_perm(obj, perm, user, site):
        # Доступ только на создание тикетов
        if perm == 'main.add_ticket':
            return True
        if perm == 'main.comment_ticket':
            if obj:
                if obj.status in [Ticket.Status.NEW, Ticket.Status.OPEN, Ticket.Status.RESOLVED]:
                    return True
        return False

    def onChatMessageAdd(self, message: ChatMessage):
        """ Обработчик сигнала добавления сообщения в чате """
        if message.user_id:
            if message.user.is_staff:
                self.count_new_user += 1
            else:
                self.count_new_staff += 1
            self.save()


@receiver(post_save, sender=Ticket, weak=False)
def ticket_post_save(instance: Ticket, created: bool = False, **kwargs):
    # создаю нить чата для нового тикета
    if created:
        if not instance.threads.all().exists():
            thread = ChatThread.objects.create(
                node=instance
            )
            thread.users.add(instance.sender)

