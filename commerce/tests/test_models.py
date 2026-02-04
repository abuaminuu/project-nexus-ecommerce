# tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from commerce.models import Product, Order, OrderItem

User = get_user_model()

class ProductModelTest(TestCase):
    """Unit tests for Product model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='userm1', email='userm1@example.com', password='userm1'
        )
    
    def test_product_creation(self):
        """Test basic product creation"""
        product = Product.objects.create(
            owner=self.user,
            name='Laptop',
            price=39.92,
            stock=5
        )

        self.assertEqual(str(product), 'Laptop')
        self.assertEqual(product.price, 39.92)
    
    def test_product_stock_status(self):
        """Test stock-related properties"""
        product = Product.objects.create(
            name='Phone',
            price=34.99,
            owner=self.user,
            stock=0
        )
        self.assertFalse(product.stock >= 1) # out of stock
        self.assertTrue(product.stock < 1)  # 0 ≤ low_stock_threshold
    
class OrderModelTest(TestCase):
    """Unit tests for Order model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='customer', email='customer@test.com', password='pass123'
        )
        self.product = Product.objects.create(
            name='Test Product', price=100, owner=self.user, stock=2
        )
    
    def test_order_total_calculation(self):
        """Test order total amount calculation"""
        order = Order.objects.create(user=self.user, order_status='pending')
        OrderItem.objects.create(
            order=order,
            product=self.product,
            price=100,
            quantity=2
        )
        self.assertEqual(order.total_amount(), 200)

class OrderItemModelTest(TestCase):
    """Unit tests for OrderItem model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='buyerpass'
        )
        self.product = Product.objects.create(
            name='Headphones', price=50, owner=self.user, stock=10
        )
        self.order = Order.objects.create(user=self.user, order_status='pending')
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=50,
            quantity=3
        )
    def test_order_item_total_price(self):
        """Test total price calculation for order item"""
        self.assertEqual(self.order_item.total_price(), 150)

