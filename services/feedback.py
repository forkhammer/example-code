from django_mail_admin import mail, models
from django.conf import settings


def send_form_data_on_email(template_name: str, form_data: dict) -> None:
    """
    Оправляет данные формы почтой
    :param template_name: Имя шаблона письма
    :param form_data: Данные формы
    :return:
    """
    mail_template = models.EmailTemplate.objects.get(name=template_name)
    mail.send(
        sender=settings.DEFAULT_FROM_EMAIL,
        recipients=settings.NOTICE_FEEDBACK_EMAIL,
        template=mail_template,
        variable_dict=form_data,
        priority=models.PRIORITY.now,
    )


def send_new_order_notice(form_data: dict) -> None:
    """
    Отправляет уведомление о новом заказе на сайте
    :param form_data: данные формы
    :return:
    """
    send_form_data_on_email('order', form_data)


def send_feedback_notice(form_data: dict) -> None:
    """
    Отправляет уведомление о новом вопросе на сайте
    :param form_data: данные формы
    :return: результат отправки
    """
    send_form_data_on_email('feedback', form_data)


def send_callback_notice(form_data: dict) -> None:
    """
    Отправляет уведомление о новом запросе звонка на сайте
    :param form_data: данные формы
    :return:
    """
    send_form_data_on_email('callback', form_data)
