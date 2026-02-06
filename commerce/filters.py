import django_filters
from .models import Product, Order, User


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price = django_filters.NumberFilter(field_name='price', lookup_expr='exact')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    class Meta:
        model = Product
        fields = []



