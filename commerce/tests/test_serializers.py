# tests/test_serializers.py
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from commerce.serializers import ProductSerializer, UserSerializer
from commerce.models import Product, User

class ProductSerializerTest(TestCase):
    """Unit tests for Product serializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='pass123'
        )
    
    def test_serializer_valid_data(self):
        """Test serializer with valid data"""
        data = {
            'owner': self.user.id,
            'name': 'Valid Product',
            'description':'Descr new product',
            "category":"electronics",
            'price': '49.99',
            "stock":3
        }
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_invalid_price(self):
        """Test serializer validation for negative price"""
        data = {
            "owner":self.user.id,
            'name': 'Test',
            "description":"new item",
            'price': -10
        }
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())

        self.assertTrue(data['price'] < 1)
        
        # checks that stock is required and not params(ie is in the serializer errors)
        self.assertIn("stock", serializer.errors)
