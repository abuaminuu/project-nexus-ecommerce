from django.contrib import admin
from commerce.models import User ,Product, Order, OrderItem, Payment
def register(model):
    return admin.site.register(model)

# Register your models here.
register(User)
register(Product)
register(Order)
register(OrderItem)
register(Payment)
