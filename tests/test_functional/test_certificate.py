#-*- coding: utf-8 -*-
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from django.core import mail
from . import SeleniumMixin
from main.models import *
from yandex_money.models import Payment


@override_settings(DEBUG=True)
class OrderTest(SeleniumMixin, StaticLiveServerTestCase):
    fixtures = ['sites.json', 'user.json', 'image.json', 'category.json', "brend.json", 'country.json', 'db.json']
    live_server_port = 9201

    def fill_form(self, data = dict()):
        self.browser.find_elements_by_css_selector('.certificate-form__sum-option')[data.get('value', 1)].click()
        self.browser.find_element_by_id('id_recepient_name').send_keys(data.get('recepient_name', ''))
        self.browser.find_element_by_id('id_recepient_email').send_keys(data.get('recepient_email', ''))
        self.browser.find_element_by_id('id_recepient_phone').send_keys(data.get('recepient_phone', ''))
        self.browser.find_element_by_id('id_sender_name').send_keys(data.get('sender_name', ''))
        self.browser.find_element_by_id('id_sender_email').send_keys(data.get('sender_email', ''))
        self.browser.find_element_by_id('id_sender_phone').send_keys(data.get('sender_phone', ''))
        self.browser.find_element_by_id('id_message').send_keys(data.get('message', ''))

    def test_create_certificate(self):
        width = 1366
        height = 2000
        self.browser.set_window_size(width, height)
        self.browser.get('http://test:%s%s' % (self.live_server_port, '/certificate/form/'))
        self.browser.save_screenshot('/screenshots/certificate/certificate-form.png')

        self.fill_form({
            'value': 1,
            'recepient_name': 'Вася Пупкин',
            'recepient_email': 'test@test.ru',
            'recepient_phone': '79999999999',
            'sender_name': 'Вася Иванов',
            'sender_email': 'test2@test.ru',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })
        self.browser.find_element_by_css_selector('.certificate-form__agreement label').click()
        self.browser.save_screenshot('/screenshots/certificate/certificate-form-fill.png')
        self.browser.find_element_by_css_selector('.certificate-form__actions button').click()
        sleep(10)
        self.browser.save_screenshot('/screenshots/certificate/certificate-form-complete.png')
        h1_payment = self.browser.find_element_by_css_selector('h1.payment-detail__title')
        self.assertIsNotNone(h1_payment)
        self.assertTrue('оплата подарочного сертификата' in h1_payment.text.lower())

        certificate = Certificate.objects.all().last()
        self.assertEqual(certificate.sender_name, 'Вася Иванов')
        self.assertEqual(certificate.sender_email, 'test2@test.ru')
        self.assertEqual(certificate.sender_phone, '7 (999) 999-9991')
        self.assertEqual(certificate.recepient_name, 'Вася Пупкин')
        self.assertEqual(certificate.recepient_email, 'test@test.ru')
        self.assertEqual(certificate.recepient_phone, '7 (999) 999-9999')
        self.assertEqual(certificate.value, 1000)

        payment = Payment.objects.filter(certificate=certificate).first()
        self.assertEqual(payment.order_amount, 1000)

    def not_full_fill_form(self, data):
        width = 1366
        height = 2000
        self.browser.set_window_size(width, height)
        self.browser.get('http://test:%s%s' % (self.live_server_port, '/certificate/form/'))

        self.fill_form(data)
        self.browser.find_element_by_css_selector('.certificate-form__actions button').click()
        sleep(5)
        with self.assertRaises(NoSuchElementException):
            h1_payment = self.browser.find_element_by_css_selector('h1.payment-detail__title')
            self.assertIsNone(h1_payment)

    def test_not_full_fill_form_recepient_name(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_email': 'test@test.ru',
            'recepient_phone': '79999999999',
            'sender_name': 'Вася Иванов',
            'sender_email': 'test2@test.ru',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })

    def test_not_full_fill_form_recepient_email(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_name': 'Вася Пупкин',
            'recepient_phone': '79999999999',
            'sender_name': 'Вася Иванов',
            'sender_email': 'test2@test.ru',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })

    def test_not_full_fill_form_recepient_phone(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_name': 'Вася Пупкин',
            'recepient_email': 'test@test.ru',
            'sender_name': 'Вася Иванов',
            'sender_email': 'test2@test.ru',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })

    def test_not_full_fill_form_sender_name(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_name': 'Вася Пупкин',
            'recepient_email': 'test@test.ru',
            'recepient_phone': '79999999999',
            'sender_email': 'test2@test.ru',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })

    def test_not_full_fill_form_sender_email(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_name': 'Вася Пупкин',
            'recepient_email': 'test@test.ru',
            'recepient_phone': '79999999999',
            'sender_name': 'Вася Иванов',
            'sender_phone': '79999999991',
            'sender_message': 'С днем рождения',
        })

    def test_not_full_fill_form_sender_phone(self):
        self.not_full_fill_form({
            'value': 0,
            'recepient_name': 'Вася Пупкин',
            'recepient_email': 'test@test.ru',
            'recepient_phone': '79999999999',
            'sender_name': 'Вася Иванов',
            'sender_email': 'test2@test.ru',
            'sender_message': 'С днем рождения',
        })
