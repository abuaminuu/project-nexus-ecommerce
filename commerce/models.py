from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here. (users, orders, products, payments)

class Customer(models.Model):
    ROLES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )
    username = models.CharField(max_length=32, null=False, unique=True)
    email = models.EmailField(max_length=255, null=False, unique=True)
    role = models.CharField(max_length=20, choices=ROLES, null=False, default="customer")
    password = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.username

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=255, index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

# class Order(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=['user', 'created_at'], name='user_created_at_idx'),
#         ]
#     def __str__(self):
#         return f"Order {self.id} by {self.user.username}"

# class Payment(models.Model):
#     STATUS = (
#         ("pending", "Pending"),
#         ("cancel", "Cancel"),
#         ("confirmed", "Confirmed")
#     )
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     order = models.ForeignKey(Order, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_status= models.Choices(choices=STATUS, null=False)
#     payment_date = models.DateTimeField(auto_now_add=True)
#     payment_method = models.CharField(max_length=50, default="Card")

#     def __str__(self):
#         return f"Payment {self.id} user: {user.username} for Order {self.order.id} status: {payment_status}"
#     class Meta:
#         indexes = [
#             models.Index(fields=['order', 'payment_date'], name='order_payment_date_idx'),
#         ]