from django.test import TestCase
from django.contrib.auth.models import User

from item.models import category, item


class IndexSearchHeadingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='seller', password='testpass123')
        self.category = category.objects.create(name='Electronics')
        item.objects.create(
            name='Wireless Headphones',
            description='Great sound',
            price=99.99,
            created_by=self.user,
            category=self.category,
        )

    def test_search_heading_shows_query(self):
        response = self.client.get('/', {'q': 'Headphones'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Items searched for "Headphones"')
        self.assertNotContains(response, 'Featured Collections')
