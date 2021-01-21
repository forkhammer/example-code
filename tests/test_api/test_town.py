from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from rest_framework.test import APIClient

from main.models.town import Town
from main.models.region import Region
from main.models.user import User

from .general import PagedApiTestMixin


class TownApiTestCase(PagedApiTestMixin, TestCase):
    apiURL = '/api/town/'
    fixtures = [
        'user.json',
    ]

    @classmethod
    def setUpTestData(cls):
        cls.region1 = Region.objects.create(
            title='region1'
        )
        cls.region2 = Region.objects.create(
            title='region2'
        )
        cls.town1 = Town.objects.create(
            title='town1',
            region=cls.region1,
        )
        cls.town2 = Town.objects.create(
            title='town2',
            region=cls.region1,
        )
        cls.town3 = Town.objects.create(
            title='town3',
            region=cls.region1,
        )
        cls.admin_user = User.objects.get_by_username('admin')
        cls.user = User.objects.get_by_username('user')
        cls.staff_user = User.objects.get_by_username('staff')

    def setUp(self):
        self.api = APIClient()

    def check_fields(self, data: any, obj: Town):
        if 'id' in data:
            self.assertEqual(data['id'], obj.id)
        self.assertEqual(data['title'], obj.title)
        self.assertEqual(data['title_eng'], obj.title_eng)
        self.assertEqual(data['region'], obj.region_id)

    def test_list(self):
        data = self.api.get(self.apiURL).json()
        self.assertEqual(len(data['results']), 3)
        self.check_fields(data['results'][0], self.town1)

    def test_all(self):
        data = self.api.get(self.apiURL, {'all': 'true'}).json()
        self.assertEqual(len(data), 3)
        self.check_fields(data[0], self.town1)

    def test_get(self):
        data = self.api.get(f'{self.apiURL}{self.town1.id}/').json()
        self.check_fields(data, self.town1)

    def test_filter(self):
        data = self.api.get(self.apiURL, {
            'id': self.town1.id
        }).json()
        self.assertEqual(len(data['results']), 1)
        self.check_fields(data['results'][0], self.town1)

        data = self.api.get(self.apiURL, {
            'id__in': f'{self.town1.id},{self.town2.id}'
        }).json()
        self.assertEqual(len(data['results']), 2)
        self.check_fields(data['results'][0], self.town1)
        self.check_fields(data['results'][1], self.town2)

        data = self.api.get(self.apiURL, {
            'title': 'town'
        }).json()
        self.assertEqual(len(data['results']), 0)

        data = self.api.get(self.apiURL, {
            'title': 'town1'
        }).json()
        self.assertEqual(len(data['results']), 1)
        self.check_fields(data['results'][0], self.town1)

        data = self.api.get(self.apiURL, {
            'title__istartswith': 'town'
        }).json()
        self.assertEqual(len(data['results']), 3)
        self.check_fields(data['results'][0], self.town1)
        self.check_fields(data['results'][1], self.town2)

    def test_order(self):
        data = self.api.get(self.apiURL, {
            'ordering': 'id'
        }).json()
        self.check_fields(data['results'][0], self.town1)
        self.check_fields(data['results'][1], self.town2)
        self.check_fields(data['results'][2], self.town3)

        data = self.api.get(self.apiURL, {
            'ordering': '-id'
        }).json()
        self.check_fields(data['results'][0], self.town3)
        self.check_fields(data['results'][1], self.town2)
        self.check_fields(data['results'][2], self.town1)

        data = self.api.get(self.apiURL, {
            'ordering': 'title'
        }).json()
        self.check_fields(data['results'][0], self.town1)
        self.check_fields(data['results'][1], self.town2)
        self.check_fields(data['results'][2], self.town3)

        data = self.api.get(self.apiURL, {
            'ordering': '-title'
        }).json()
        self.check_fields(data['results'][0], self.town3)
        self.check_fields(data['results'][1], self.town2)
        self.check_fields(data['results'][2], self.town1)

    def test_post(self):
        post_data = {
            'title': 'town_post',
            'title_eng': 'town_eng',
            'region': self.region1.id,
        }

        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.post(self.apiURL, data=post_data)
        self.assertEqual(response.status_code, 201)
        self.check_fields(post_data, Town.objects.get(title='town_post'))

    def test_put(self):

        town = Town.objects.create(
            title='town_post',
            title_eng='title_eng',
            region=self.region1
        )
        put_data = {
            'id': town.id,
            'title': 'town_post_new',
            'title_eng': 'town_eng_new',
            'region': self.region2.id
        }

        response = self.api.put(f'{self.apiURL}{town.id}/', data=put_data)
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.put(f'{self.apiURL}{town.id}/', data=put_data)
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.put(f'{self.apiURL}{town.id}/', data=put_data)
        self.assertEqual(response.status_code, 200)
        self.check_fields(put_data, Town.objects.get(
            title='town_post_new'))

    def test_delete(self):
        town = Town.objects.create(
            title='town_delete'
        )

        response = self.api.delete(f'{self.apiURL}{town.id}/')
        self.assertEqual(response.status_code, 401)

        self.api.force_authenticate(user=self.user)
        response = self.api.delete(f'{self.apiURL}{town.id}/')
        self.assertEqual(response.status_code, 403)

        self.api.force_authenticate(user=self.admin_user)
        response = self.api.delete(f'{self.apiURL}{town.id}/')
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(ObjectDoesNotExist):
            Town.objects.get(id=town.id)
