import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from main.models.article import Article


class ArticleTestCase(TestCase):
    def test_create_article(self):
        now = timezone.datetime.now()
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
            date_publish=now
        )
        self.assertEqual(article.title, 'Заголовок')
        self.assertEqual(article.preview, 'preview')
        self.assertTrue(article.date_created is not None)
        self.assertTrue(article.date_modified is not None)
        self.assertEqual(article.date_publish, now)
        self.assertEqual(article.slug, 'zagolovok')
        self.assertEqual(
            article.url, f'/article/detail/zagolovok__{article.id}')
        self.assertEqual(article.get_absolute_url(),
                         f'/article/detail/zagolovok__{article.id}')
        self.assertEqual(article.search_text, 'preview')
        self.assertTrue(article.placeholders.all().first() is not None)

    def test_collision_slug(self):
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        article2 = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        article3 = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        self.assertEqual(article.slug, 'zagolovok')
        self.assertEqual(article2.slug, 'zagolovok-2')
        self.assertEqual(article3.slug, 'zagolovok-3')

    def test_date_publish(self):
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        self.assertTrue(article.date_publish is not None)

        now = timezone.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
            date_publish=now
        )
        self.assertEqual(article.date_publish, now)

    def test_str(self):
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        self.assertEqual(str(article), 'Заголовок')
        self.assertEqual(str(article.id), repr(article))

    def test_delete(self):
        article = Article.objects.create(
            title='Заголовок',
            preview='preview',
        )
        self.assertFalse(article.is_deleted)
        article.delete()
        article = Article.objects.get(title='Заголовок')
        self.assertTrue(article.is_deleted)
        self.assertTrue(article.date_deleted is not None)

        article = Article.objects.create(
            title='Заголовок2',
            preview='preview',
        )
        Article.objects.filter(title='Заголовок2').delete()
        with self.assertRaises(ObjectDoesNotExist):
            article = Article.objects.get(title='Заголовок2')
