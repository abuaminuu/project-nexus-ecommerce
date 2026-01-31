import django_filters
from .models import Product, Order, User


class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            'price': ['lt', 'gt', 'exact'],
            'name': ['icontains'],
            'category': ['exact'],
        }

