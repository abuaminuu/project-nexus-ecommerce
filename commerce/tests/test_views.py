# tests/test_views.py
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from commerce.models import Product, User

class ProductViewSetTest(APITestCase):
    """Integration tests for ProductViewSet"""
    
    def setUp(self):
        self.client = APIClient()
        self.normal_user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='adminpass123'
        )
        self.product = Product.objects.create(
            owner=self.normal_user,
            name='Test Product',
            description="for test",
            category="others",
            price=29.99,
            stock=3
        )
        self.list_url = reverse('products-viewset-list')
        self.detail_url = reverse('products-viewset-detail', kwargs={'pk': self.product.pk})
    
    def test_list_products_public(self):
        """Test anyone can view products (public endpoint)"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_product_authenticated(self):
        """Test authenticated user can create product"""
        self.client.force_authenticate(user=self.normal_user)
        data = {
            'owner':self.normal_user.id,
            'name': 'New Product',
            'description':"description 2",
            'category':"others",
            'price': '49.99',
            'stock':3
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_product_unauthenticated(self):
        """Test unauthenticated user cannot create product"""
        data = {'name': 'New Product', 'price': '49.99'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_filter_products(self):
        """Test product filtering"""
        Product.objects.create(
            owner=self.normal_user,
            name='Phone',
            description="desc 4",
            price=699.99, 
            stock=6
        )
        # Should return products containing 'phone'
        response = self.client.get(f'{self.list_url}?name__icontains=phone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"][1]["name"].lower(), "phone")
        