from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from main.models.product import Product
from main.models.category import Category
from main.models.property import Property, PropertyValue
from main.models.mod import Mod
from main.models.unit import Unit


class ProductTestCase(TestCase):
    fixtures = [
        'unit.json',
    ]

    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.get_by_code('piece')

    def test_create_product(self):
        product = Product.objects.create(
            title='Заголовок',
            articul='123',
            preview='preview',
            body='body',
            ext_id='ext1',
            unit=self.unit,
        )
        self.assertEqual(product.title, 'Заголовок')
        self.assertEqual(product.articul, '123')
        self.assertTrue(product.is_active)
        self.assertEqual(product.preview, 'preview')
        self.assertEqual(product.body, 'body')
        self.assertEqual(product.ext_id, 'ext1')

    def test_collision_slug(self):
        product = Product.objects.create(
            title='Заголовок',
            unit=self.unit,
        )
        product2 = Product.objects.create(
            title='Заголовок',
            unit=self.unit,
        )
        product3 = Product.objects.create(
            title='Заголовок',
            unit=self.unit,
        )
        self.assertEqual(product.slug, 'zagolovok')
        self.assertEqual(product2.slug, 'zagolovok-2')
        self.assertEqual(product3.slug, 'zagolovok-3')

    def test_str(self):
        product = Product.objects.create(
            title='Заголовок',
            unit=self.unit,
        )
        self.assertEqual(str(product), 'Заголовок')
        self.assertEqual(str(product.id), repr(product))

    def test_delete(self):
        product = Product.objects.create(
            title='Заголовок',
            unit=self.unit,
        )
        self.assertFalse(product.is_deleted)
        product.delete()
        product = Product.objects.get(title='Заголовок')
        self.assertTrue(product.is_deleted)
        self.assertTrue(product.date_deleted is not None)

        product = Product.objects.create(
            title='Заголовок2',
            unit=self.unit,
        )
        Product.objects.filter(title='Заголовок2').delete()
        with self.assertRaises(ObjectDoesNotExist):
            product = Product.objects.get(title='Заголовок2')

    def test_url(self):
        product = Product.objects.create(
            title='product1',
            unit=self.unit,
        )
        self.assertEqual(product.url, f'/catalog/product1__id{product.id}')

        category1 = Category.objects.create(
            title='category1'
        )
        product2 = Product.objects.create(
            title='product2',
            category=category1,
            unit=self.unit,
        )
        self.assertEqual(
            product2.url, f'/catalog/category1/product2__id{product2.id}')

        category2 = Category.objects.create(
            title='category2',
            parent=category1,
        )
        product3 = Product.objects.create(
            title='product3',
            category=category2,
            unit=self.unit,
        )
        self.assertEqual(
            product3.url, f'/catalog/category2/product3__id{product3.id}')

    def test_absolute_url(self):
        product = Product.objects.create(
            title='product1',
            unit=self.unit,
        )
        self.assertEqual(product.get_absolute_url(),
                         f'/catalog/product1__{product.id}')

        category1 = Category.objects.create(
            title='category1'
        )
        product2 = Product.objects.create(
            title='product2',
            category=category1,
            unit=self.unit,
        )
        self.assertEqual(
            product2.get_absolute_url(), f'/catalog/category1/product2__id{product2.id}')

        category2 = Category.objects.create(
            title='category2',
            parent=category1
        )
        product3 = Product.objects.create(
            title='product3',
            category=category2,
            unit=self.unit,
        )
        self.assertEqual(
            product3.get_absolute_url(), f'/catalog/category2/product3__id{product3.id}')

    def test_add_properties(self):
        product = Product.objects.create(
            title='product1',
            unit=self.unit,
        )
        prop = Property.objects.create(
            title='property1',
        )
        value = PropertyValue.objects.create(
            prop=prop,
            value_str='value1'
        )
        product.properties.add(value)
        self.assertEqual(product.properties.all().count(), 1)

        product.properties.remove(value)
        self.assertEqual(product.properties.all().count(), 0)

    def test_add_mods(self):
        product = Product.objects.create(
            title='product1',
            unit=self.unit,
        )
        mod = Mod.objects.create(
            title='mod1'
        )
        product.mods.add(mod)
        self.assertEqual(product.mods.all().count(), 1)

        product.mods.remove(mod)
        self.assertEqual(product.mods.all().count(), 0)
