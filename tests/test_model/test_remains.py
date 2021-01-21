from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from main.models.remains import Remains, NotExistsRemainsExseption
from main.models.product import Product
from main.models.mod import Mod
from main.models.stock import Stock
from main.models.unit import Unit


class RemainsTestCase(TestCase):
    fixtures = [
        'unit.json'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.get_by_code('piece')
        cls.product = Product.objects.create(
            title='product1',
            unit=cls.unit,
        )
        cls.mod1 = Mod.objects.create(
            title='mod1'
        )
        cls.mod2 = Mod.objects.create(
            title='mod2'
        )
        cls.product.mods.add(cls.mod1, cls.mod2)

        cls.stock = Stock.objects.create(
            title='stock1',
            is_default=True
        )
        cls.stock2 = Stock.objects.create(
            title='stock2',
        )

    def test_create_remains(self):
        remains = Remains.objects.create(
            product=self.product,
            mod=self.mod1,
            stock=self.stock,
            count=1
        )
        self.assertEqual(remains.product, self.product)
        self.assertEqual(remains.mod, self.mod1)
        self.assertEqual(remains.count, 1)
        self.assertEqual(remains.stock, Stock.objects.default_stock())

    def test_str(self):
        remains = Remains.objects.create(
            product=self.product,
            mod=self.mod1,
            stock=self.stock,
            count=1
        )
        self.assertEqual(str(remains), str(remains.id))
        self.assertEqual(str(remains.id), repr(remains))

    def test_delete(self):
        remains = Remains.objects.create(
            product=self.product,
            mod=self.mod1,
            stock=self.stock,
            count=1
        )

        remains.delete()
        with self.assertRaises(ObjectDoesNotExist):
            remains = Remains.objects.get(product=self.product, mod=self.mod1)

    def test_remains(self):
        self.assertEqual(Remains.objects.remains(
            product=self.product
        ), 0)

        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1
        ), 0)

        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2,
        ), 0)

        Remains.objects.setCount(
            product=self.product,
            count=100
        )
        self.assertEqual(Remains.objects.remains(
            product=self.product
        ), 100)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1
        ), 0)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2
        ), 0)

        Remains.objects.setCount(
            product=self.product,
            mod=self.mod1,
            count=200
        )
        self.assertEqual(Remains.objects.remains(
            product=self.product
        ), 100)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1
        ), 200)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod2
        ), 0)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2
        ), 0)

        Remains.objects.setCount(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2,
            count=300
        )
        self.assertEqual(Remains.objects.remains(
            product=self.product
        ), 100)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1
        ), 200)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod2
        ), 0)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2
        ), 300)
        self.assertEqual(Remains.objects.remains(
            product=self.product,
            mod=self.mod2,
            stock=self.stock2
        ), 0)

    def test_decrease(self):
        Remains.objects.setCount(
            product=self.product,
            count=100
        )
        Remains.objects.setCount(
            product=self.product,
            mod=self.mod1,
            count=200
        )
        Remains.objects.setCount(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2,
            count=300
        )

        Remains.objects.decrease(
            product=self.product,
            count=2
        )
        self.assertEqual(Remains.objects.remains(product=self.product), 98)

        Remains.objects.decrease(
            product=self.product,
            mod=self.mod1,
            count=2
        )
        self.assertEqual(Remains.objects.remains(
            product=self.product, mod=self.mod1), 198)

        Remains.objects.decrease(
            product=self.product,
            mod=self.mod1,
            stock=self.stock2,
            count=2
        )
        self.assertEqual(Remains.objects.remains(
            product=self.product, mod=self.mod1, stock=self.stock2), 298)

        with self.assertRaises(NotExistsRemainsExseption):
            Remains.objects.decrease(
                product=self.product,
                mod=self.mod2,
                count=2
            )
