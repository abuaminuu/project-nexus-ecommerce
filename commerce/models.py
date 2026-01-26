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


class Product(models.Model):
    CHOICES = (
        ("electronics", "Electronics"),
        ("home", "Home"),
        ("fashion", "Fashion"),
        ("others", "Others"),
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(choices=CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Order(models.Model):
    ORDERSTATUS = (
        ("pending", "Pending"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_status= models.CharField(choices=ORDERSTATUS, null=False, default="pending", max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    def total_price(self):
        return self.quantity * self.price

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
    status= models.Choices(choices=STATUS, null=False, default="pending", max_length=10)
    method = models.CharField(max_length=16, choices=METHOD, default="card")
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} user: {self.user.username} for Order {self.order.id} status: {self.status}"
