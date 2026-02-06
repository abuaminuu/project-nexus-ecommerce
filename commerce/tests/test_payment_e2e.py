# tests/test_payment_e2e.py
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from commerce.models import User, Product, Order, OrderItem, Payment

class PaymentProcessE2ETest(TestCase):
    """
    End-to-end test for complete payment flow:
    1. User registration → 2. Login → 3. Browse products → 4. Add to cart
    5. Create order → 6. Initiate payment → 7. Confirm payment → 8. Verify order status
    """
    
    def setUp(self):
        self.client = APIClient()
        self.base_url = 'http://localhost:8000'
        
        # Create test data
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='seller123'
        )
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='buyer123'
        )
        
        self.product = Product.objects.create(
            owner=self.seller,
            name='Test Product',
            description="Hello descr",
            category="others",
            price=99.99,
            stock=3
        )
        
        # URLs
        self.register_url = reverse('register')
        self.login_url = reverse('token_obtain_pair')
        self.products_url = reverse('products-viewset-list')
        self.orders_url = reverse('orders-viewset-list')
    
    def test_complete_payment_process_success(self):
        """Complete happy path payment flow"""
        # print("Buyer exists?", User.objects.filter(username='buyer').exists())
        # print("Buyer password check:", self.buyer.check_password('buyer123'))
        
        # Print the URL being used
        # print("Login URL being called:", self.login_url)
        # print("Full URL:", f"{self.base_url}{self.login_url}")

        # === 1. USER LOGIN === 
        login_data = {'username': self.buyer.username, 'password': 'buyer123'}

        login_response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # === 2. CREATE ORDER ===
        order_data = {
            'user': self.buyer.id,
            'items': [{
                'product': self.product.id, 
                'price': self.product.price,
                'quantity': 2
            }],
            'order_status': 'pending',
        }
        
        order_response = self.client.post(self.orders_url, order_data, format='json')
        self.assertEqual(order_response.status_code, status.HTTP_201_CREATED)

        order_id = order_response.data['id']
        order = Order.objects.get(id=order_id)
        
        # === 3. INITIATE PAYMENT ===
        # Using your existing pay action
        pay_url = reverse('orders-viewset-pay', kwargs={'pk': order.id})
        pay_response = self.client.post(pay_url, format='json')
        
        # Should return payment URL or pending status
        self.assertIn(pay_response.status_code, [200, 201])
        self.assertIn('payment_url', pay_response.data or 'status' in pay_response.data)
        
        # === 4. MOCK PAYMENT CONFIRMATION ===
        # In real test, this would be Flutterwave webhook/callback
        # Here we simulate successful payment
        
        # Create payment record (simulating webhook)
        payment = Payment.objects.create(
            user=self.buyer,
            order=order,
            amount=order.total_amount(),
            status='confirmed',
            method='card',
        )
        
        # === 5. CONFIRM PAYMENT (Your confirm_payment action) ===
        confirm_url = reverse('orders-viewset-confirm-payment', kwargs={'pk': order.id})
        confirm_data = {
            'tx_ref': 'TEST_TXN_12345',
            'status': 'TEST_TXN_123451'
        }
        
        confirm_response = self.client.post(confirm_url, confirm_data, format='json')
        # print(confirm_response.data)
        # Payment should be confirmed
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        # TODO mock payment with decorators
        # self.assertEqual(confirm_response.data['status'], 'Payment confirmed')
        
#         # === 6. VERIFY ORDER STATUS UPDATED ===
#         order.refresh_from_db()
#         self.assertEqual(order.order_status, 'pending')  # Should move from pending to next status
        
#         # === 7. VERIFY PAYMENT RECORD ===
#         payment.refresh_from_db()
#         self.assertEqual(payment.status, 'confirmed')
        
#         # === 8. VERIFY PRODUCT STOCK REDUCED ===
#         self.product.refresh_from_db()
#         self.assertEqual(self.product.stock_quantity, 8)  # Started with 10, bought 2
        
#         print("✅ Complete payment process test PASSED")
    
#     def test_payment_failed_flow(self):
#         """Test payment failure scenario"""
        
#         # Login
#         login_data = {'username': 'buyer', 'password': 'buyer123'}
#         login_response = self.client.post(self.login_url, login_data, format='json')
#         access_token = login_response.data['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
#         # Create order
#         order_data = {
#             'items': [{'product_id': self.product.id, 'quantity': 1}],
#             'shipping_address': '123 Test Street'
#         }
#         order_response = self.client.post(self.orders_url, order_data, format='json')
#         order_id = order_response.data['order_id']
#         order = Order.objects.get(id=order_id)
        
#         # Simulate failed payment
#         payment = Payment.objects.create(
#             user=self.buyer,
#             order=order,
#             amount=order.total_amount(),
#             status='failed',
#             payment_method='card',
#             transaction_id='FAILED_TXN_123'
#         )
        
#         # Verify order still pending
#         order.refresh_from_db()
#         self.assertEqual(order.order_status, 'pending')
        
#         # Verify product stock NOT reduced
#         initial_stock = self.product.stock_quantity
#         self.product.refresh_from_db()
#         self.assertEqual(self.product.stock_quantity, initial_stock)
        
#         print("✅ Payment failure flow test PASSED")
    
#     def test_insufficient_stock_payment(self):
#         """Test payment attempt with insufficient stock"""
        
#         # Create low stock product
#         low_stock_product = Product.objects.create(
#             name='Limited Product',
#             price=49.99,
#             owner=self.seller,
#             stock_quantity=1  # Only 1 available
#         )
        
#         # Login
#         login_data = {'username': 'buyer', 'password': 'buyer123'}
#         login_response = self.client.post(self.login_url, login_data, format='json')
#         access_token = login_response.data['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
#         # Try to order 2 items when only 1 available
#         order_data = {
#             'items': [{'product_id': low_stock_product.id, 'quantity': 2}],
#             'shipping_address': '123 Test Street'
#         }
        
#         order_response = self.client.post(self.orders_url, order_data, format='json')
        
#         # Should fail with insufficient stock error
#         self.assertEqual(order_response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('stock', order_response.data.get('error', '').lower())
        
#         print("✅ Insufficient stock test PASSED")
    
#     def test_payment_with_expired_token(self):
#         """Test payment with expired JWT token"""
        
#         # Get token
#         login_data = {'username': 'buyer', 'password': 'buyer123'}
#         login_response = self.client.post(self.login_url, login_data, format='json')
#         access_token = login_response.data['access']
        
#         # Create order with valid token
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
#         order_data = {
#             'items': [{'product_id': self.product.id, 'quantity': 1}],
#             'shipping_address': '123 Test Street'
#         }
#         order_response = self.client.post(self.orders_url, order_data, format='json')
#         order_id = order_response.data['order_id']
        
#         # Clear credentials (simulate expired token)
#         self.client.credentials()
        
#         # Try to initiate payment without token
#         pay_url = reverse('orders-pay', kwargs={'pk': order_id})
#         pay_response = self.client.post(pay_url, format='json')
        
#         # Should be unauthorized
#         self.assertEqual(pay_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
#         print("✅ Expired token test PASSED")

# class MockFlutterwavePaymentTest(TestCase):
#     """Mock Flutterwave API responses for testing"""
    
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
#         self.product = Product.objects.create(name='Test', price=100, owner=self.user)
        
#         # Login
#         login_response = self.client.post(
#             reverse('token_obtain_pair'),
#             {'username': 'testuser', 'password': 'pass123'},
#             format='json'
#         )
#         self.client.credentials(
#             HTTP_AUTHORIZATION=f'Bearer {login_response.data["access"]}'
#         )
    
#     def test_mock_payment_initiation(self):
#         """Test your pay() action with mocked Flutterwave response"""
        
#         # Create order
#         order_response = self.client.post(
#             reverse('orders-viewset-list'),
#             {'items': [{'product_id': self.product.id, 'quantity': 1}]},
#             format='json'
#         )
#         order_id = order_response.data['order_id']
        
#         # Mock the pay() action - Since it calls Flutterwave API,
#         # you might need to mock the requests.post call
        
#         # For now, test that endpoint exists and returns expected structure
#         pay_url = reverse('orders-pay', kwargs={'pk': order_id})
#         response = self.client.post(pay_url, format='json')
        
#         # Should return something (even if error due to missing Flutterwave config)
#         self.assertIn(response.status_code, [200, 201, 400, 500])
        
#         print("✅ Mock payment initiation test COMPLETE")

# Run specific tests
if __name__ == '__main__':
    import unittest
    unittest.main()
