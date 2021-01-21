#-*- coding: utf-8 -*-
from django.contrib.staticfiles.testing import StaticLiveServerTestCase, LiveServerTestCase
from django.test import override_settings
from time import sleep
from django.core import mail
from . import SeleniumMixin
from main.models import *

@override_settings(DEBUG=True)
class OrderTest(SeleniumMixin, StaticLiveServerTestCase):
    fixtures = ['sites.json', 'user.json', 'image.json', 'category.json', "brend.json", 'country.json', 'db.json']
    live_server_port = 9201

    def test_simple_order(self):
        """
        Тестирование простого заказа
        """
        product = Product.objects.get(id=6876)
        product.clear_cache()
        modvolume = product.modvolumes.all()[0]

        pricelist = Pricelist.objects.create(datedoc=timezone.datetime.now())
        priceitem = PricelistItem.objects.create(
            product = product,
            modvolume=modvolume,
            doc=pricelist,
            price=100
        )
        pricelist.do()

        product = Product.objects.get(id=6876)

        stock = Stock.objects.create(
            product=product,
            count=10
        )
        stock = Stock.objects.create(
            product=product,
            modvolume=modvolume,
            count=10
        )

        width = 1366
        height = 900
        self.browser.set_window_size(width, height)
        self.browser.get('http://test:%s%s' % (self.live_server_port, product.url()))
        self.browser.save_screenshot('/screenshots/simple-order/product-%s.png' % product.id)
        h1 = self.browser.find_element_by_class_name("product-detail__title")
        self.assertEqual(h1.text.lower(), product.title.lower())

        price_div = self.browser.find_element_by_class_name('product-detail__price')
        self.assertNotEqual(price_div, None, msg='Не найдена цена на странице товара')
        self.assertEqual(price_div.text, '100  руб.')

        order_btn = self.browser.find_element_by_class_name('product-detail__order-btn')
        self.assertIsNotNone(order_btn, msg='Не найдена кнопка покупки')

        # кликаю по кнопке заказа
        order_btn.click()
        sleep(2)
        self.browser.save_screenshot('/screenshots/simple-order/product-%s-after-order.png' % product.id)
        notice = self.browser.find_element_by_css_selector('div[data-notify="container"]')
        self.assertIsNotNone(notice, msg='Не вышло уведомление о добавлении в корзину')
        self.assertIn('добавлен в корзину', notice.text)

        # перехожу в корзину
        self.browser.get('http://test:%s%s' % (self.live_server_port, '/basket/'))
        sleep(2)
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order.png')      
        title = self.browser.find_element_by_class_name('basket-list__title')
        self.assertIsNotNone(title)
        count = self.browser.find_element_by_css_selector('.basket-list__count .updown-number__input')
        self.assertIsNotNone(count)
        self.assertEqual(count.get_attribute('value'), '1')  
        price = self.browser.find_element_by_class_name('basket-list__price')
        self.assertIsNotNone(price)
        self.assertEqual(price.text, '100 руб.')

        # нажимаю на кнопку оформить заказ
        next_btn = self.browser.find_element_by_class_name('basket-page__submit')
        self.assertIsNotNone(next_btn)
        next_btn.click()
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order-step2.png')   
        sleep(1)

        # запоняю личные данные
        self.browser.find_element_by_id('id_phone').send_keys('79999999999') 
        self.browser.find_element_by_id('id_email').send_keys('test@test.ru') 
        self.browser.find_element_by_id('id_last_name').send_keys('Пупкин') 
        self.browser.find_element_by_id('id_first_name').send_keys('Вася') 
        self.browser.find_element_by_id('id_desc').send_keys('Пример заказа') 
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order-step2-fill.png')   

        # нажимаю на кнопку оформить заказ
        next_btn = self.browser.find_element_by_css_selector('#checkout-contacts .basket-page__submit')
        self.assertIsNotNone(next_btn)
        self.assertEqual(next_btn.text, 'Перейти к доставке')
        next_btn.click()

        self.browser.find_element_by_css_selector('label[for="id_delivery_1"]').click()
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order-step3.png')
        next_btn = self.browser.find_element_by_css_selector('#checkout-delivery .basket-page__submit')
        self.assertIsNotNone(next_btn)
        self.assertEqual(next_btn.text, 'Перейти к оплате')
        next_btn.click()

        self.browser.find_element_by_css_selector('label[for="id_pay_1"]').click()
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order-step4.png')
        next_btn = self.browser.find_element_by_css_selector('#checkout-payment .basket-page__submit')
        self.assertIsNotNone(next_btn)
        self.assertEqual(next_btn.text, 'Завершить')
        next_btn.click()
        sleep(5)

        h2_complete = self.browser.find_element_by_css_selector('h2.checkout-complete__title')
        self.assertIsNotNone(h2_complete)
        self.assertTrue('Спасибо! Ваш заказ' in h2_complete.text)
        self.browser.save_screenshot('/screenshots/simple-order/basket-simple-order-step5.png')

        order = Order.objects.all().last()
        self.assertEqual(order.first_name, 'Вася')
        self.assertEqual(order.last_name, 'Пупкин')
        self.assertEqual(order.email, 'test@test.ru')
        self.assertEqual(order.phone, '7 (999) 999-9999')
        self.assertEqual(order.items.all().count(), 1)
        order_item = order.items.all().first()
        self.assertEqual(order_item.product.id, product.id)
        self.assertEqual(order_item.price, 100)
        self.assertEqual(order_item.discount_price, 100)
        self.assertEqual(order_item.count, 1)
