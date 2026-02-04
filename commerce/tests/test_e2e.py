# tests/test_e2e.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from commerce.models import User, Product, Order, OrderItem

class EndToEndTest(APITestCase):
    """End-to-end user journey tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='customer', email='customer@test.com', password='customer123'
        )
        self.seller = User.objects.create_user(
            username='seller', email='seller@test.com', password='seller123'
        )
    
    def test_complete_shopping_journey(self):
        """Complete user journey: register → login → browse → add to cart → checkout"""
        
        # 1. User registers
        register_url = reverse('register')
        register_data = {
            'username': 'newcustomer',
            'email': 'new@test.com',
            'password': 'newpass123'
        }

        # checks for succesfull registration
        register_response = self.client.post(register_url, register_data, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # 2. User logs in
        login_url = reverse('token_obtain_pair')
        login_data = {'username': 'newcustomer', 'password': 'newpass123'}
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access']

        # apply authentication token with the headers
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 3. user browses products
        products_url = reverse('products-viewset-list')
        browse_response = self.client.get(products_url)
        self.assertEqual(browse_response.status_code, status.HTTP_200_OK)
        
        # 4. User creates an order (simplified)
        order_url = reverse('orders-viewset-list')
        order_data = {'user': self.user.id, 'order_status': 'pending'}
        order_response = self.client.post(order_url, order_data, format='json')
        # 200 for succesfull post
        self.assertEqual(order_response.status_code, 201)
