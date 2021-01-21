from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from rest_framework.test import APIClient
from pprint import pprint

from main.models.category import Category
from main.models.user import User

from .general import PagedApiTestMixin


class CategoryApiTestCase(PagedApiTestMixin, TestCase):
    apiURL = '/api/category/'
    fixtures = [
        'user.json',
    ]

    @classmethod
    def setUpTestData(cls):
        for i in range(10):
            c = Category.objects.create(
                title=f'category{i}',
                order=i,
            )
            for j in range(1, 3):
                Category.objects.create(
                    title=f'subcategory{j}',
                    order=j,
                    parent=c,
                )
        cls.category1 = Category.objects.get(title='category1')
        cls.category2 = Category.objects.get(title='category2')
        cls.category3 = Category.objects.get(title='category3')
        cls.admin_user = User.objects.get_by_username('admin')
        cls.user = User.objects.get_by_username('user')
        cls.staff_user = User.objects.get_by_username('staff')

    def setUp(self):
        self.api = APIClient()

    def check_fields(self, data: dict, obj: Category):
        if 'id' in data:
            self.assertEqual(data['id'], obj.id)
        self.assertEqual(data['title'], obj.title)
        self.assertEqual(data['parent'], obj.parent_id)
        self.assertEqual(data['order'], obj.order)
        self.assertEqual(data['image'], obj.image_id)
        self.assertEqual(data['level'], obj.level)
        self.assertEqual(data['is_deleted'], obj.is_deleted)

    def check_post(self, data: dict, obj: Category):
        for key, value in data.items():
            attr = getattr(obj, key)
            if attr is not None:
                self.assertEqual(repr(value), repr(attr))
            else:
                self.assertIsNone(value)

    def test_list(self):
        data = self.api.get(self.apiURL).json()
        self.assertEqual(len(data['results']), 20)

    def test_all(self):
        data = self.api.get(self.apiURL, {'all': 'true'}).json()
        self.assertEqual(len(data), 30)

    def test_hierarchy(self):
        data = self.api.get(self.apiURL + 'hierarchy/').json()
        self.assertEqual(len(data), 10)

        self.assertEqual(len(data[0]['children']), 2)
        self.assertEqual(len(data[1]['children']), 2)
        self.assertEqual(len(data[2]['children']), 2)
        self.assertEqual(len(data[3]['children']), 2)

    def test_get(self):
        data = self.api.get(f'{self.apiURL}{self.category1.id}/').json()
        self.check_fields(data, self.category1)

    def test_filter(self):
        data = self.api.get(self.apiURL, {
            'id': self.category1.id
        }).json()
        self.assertEqual(len(data['results']), 1)
        self.check_fields(data['results'][0], self.category1)

        data = self.api.get(self.apiURL, {
            'id__in': f'{self.category1.id},{self.category2.id}'
        }).json()
        self.assertEqual(len(data['results']), 2)
        self.check_fields(data['results'][0], self.category1)
        self.check_fields(data['results'][1], self.category2)

        data = self.api.get(self.apiURL, {
            'title': 'category'
        }).json()
        self.assertEqual(len(data['results']), 0)

        data = self.api.get(self.apiURL, {
            'title': 'category1'
        }).json()
        self.assertEqual(len(data['results']), 1)
        self.check_fields(data['results'][0], self.category1)

        data = self.api.get(self.apiURL, {
            'title__istartswith': 'category'
        }).json()
        self.assertEqual(len(data['results']), 10)

        data = self.api.get(self.apiURL, {
            'parent': self.category1.id
        }).json()
        self.assertEqual(len(data['results']), 2)

        data = self.api.get(self.apiURL, {
            'slug': self.category1.slug
        }).json()
        self.assertEqual(len(data['results']), 1)

        data = self.api.get(self.apiURL, {
            'is_active': 'true'
        }).json()
        self.assertEqual(len(data['results']), 20)

        data = self.api.get(self.apiURL, {
            'is_deleted': 'true'
        }).json()
        self.assertEqual(len(data['results']), 0)

        data = self.api.get(self.apiURL, {
            'level': 0
        }).json()
        self.assertEqual(len(data['results']), 10)

        data = self.api.get(self.apiURL, {
            'level': 1
        }).json()
        self.assertEqual(len(data['results']), 20)

    def test_order(self):
        data = self.api.get(self.apiURL, {
            'all': 'true',
            'level': 0
        }).json()
        for index, elem in enumerate(data):
            if index < len(data) - 1:
                self.assertTrue(data[index]['order'] <= data[index+1]['order']) 

    def test_post(self):
        post_data = {
            'title': 'category_post',
            'parent': self.category1.id,
            'order': 10,
        }

        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 201)
        self.check_post(post_data, Category.objects.get(title='category_post'))

    def test_put(self):
        category = Category.objects.create(
            title='category_post',
            order=1000,
        )

        put_data = {
            'id': category.id,
            'title': 'category_put',
            'parent': self.category2.id,
            'order': 10,
        }

        response = self.api.put(f'{self.apiURL}{category.id}/', data=put_data)
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.put(f'{self.apiURL}{category.id}/', data=put_data)
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.put(f'{self.apiURL}{category.id}/', data=put_data)
        self.assertEqual(response.status_code, 200)
        self.check_post(put_data, Category.objects.get(
            title='category_put'))

    def test_delete(self):
        category = Category.objects.create(
            title='category_delete'
        )

        response = self.api.delete(f'{self.apiURL}{category.id}/')
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.delete(f'{self.apiURL}{category.id}/')
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.delete(f'{self.apiURL}{category.id}/')
        self.assertEqual(response.status_code, 204)
        c = Category.objects.get(id=category.id)
        self.assertTrue(c.is_deleted)
