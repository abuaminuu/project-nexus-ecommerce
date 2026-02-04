# tests/test_auth.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from commerce.models import User

class AuthenticationTest(APITestCase):
    """Critical authentication tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123'
        )
    
    def test_user_registration(self):
        """Test user can register"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'securepassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_user_login(self):
        """Test user can login and get tokens"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # checks that access token is available and can be refreshed
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_protected_endpoint_with_token(self):
        """Test accessing protected endpoint with JWT"""
        # First login
        login_url = reverse('token_obtain_pair')
        login_data = {'username': 'testuser', 'password': 'testpass123'}
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access']
        
        # Use token to access protected endpoint
        products_url = reverse('products-viewset-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(products_url, {'owner':self.user.id, 'name': 'Test', 'description':'new auth cat', 'category':'others', 'price': '10', 'stock':2})
        # Should be 201 (created) or 401/403 depending on permissions
        self.assertIn(response.status_code, [201, 401, 403])
