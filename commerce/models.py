from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here. (Users, orders, products, payments)
class User(AbstractUser):
    # extending default user model
    CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=CHOICES, null=False, default="customer")

    class Meta:
        indexes = [
            # For login lookups
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return self.username

class Product(models.Model):
    CHOICES = (
        ("electronics", "Electronics"),
        ("fashion", "Fashion"),
        ("home_kitchen", "Home & Kitchen"),
        ("beauty_care", "Beauty & Personal Care"),
        ("sports_outdoors", "Sports & Outdoors"),
        ("health_wellness", "Health & Wellness"),
        ("automotive", "Automotive"),
        ("books_media", "Books & Media"),
        ("toys_games", "Toys & Games"),
        ("groceries", "Groceries"),
        ("office_supplies", "Office Supplies"),
        ("pet_supplies", "Pet Supplies"),
        ("others", "Others"),
    )


    # add owner field to track who added the product
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(choices=CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [            
            # Price filtering (range queries)
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return self.name
    

class Order(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_status= models.CharField(choices=STATUS, null=False, default="pending", max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Most frequent: User's order history
            models.Index(fields=['user', 'created_at']),
            
            # Status-based queries (admin dashboard)
            # models.Index(fields=['order_status', 'created_at']),
            # models.Index(fields=['payment_status', 'order_status']),
        ]

    def total_amount(self):
        return sum([items.price * items.quantity for items in self.items.all()])

    def __str__(self):
        return f"Order {self.id} by {self.user.username} status: {self.order_status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price  = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Frequent: Order details page
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"Order {self.id} Item: {self.product.name} x {self.quantity}"

    def total_price(self):
        return self.quantity * self.price

# TODO add tx_ref
class Payment(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("cancel", "Cancel"),
        ("confirmed", "Confirmed")
    )
    
    METHOD = (
        ("card", "Card"),
        ("transfer", "Transfer"),
        ("cash", "Cash")
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status= models.CharField(choices=STATUS, null=False, default="pending", max_length=10)
    method = models.CharField(max_length=16, choices=METHOD, default="card")
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # User payment history
            models.Index(fields=['user', 'paid_at']),
        ]
        
    def __str__(self):
        return f"Payment {self.id} user: {self.user.username} for Order {self.order.id} status: {self.status}"
