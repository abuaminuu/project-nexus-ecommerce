from rest_framework import serializers
from commerce.models import User, Product, Order, OrderItem, Payment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]

class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = "__all__"

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['product', 'product_name', 'quantity', 'price', 'total_price']
    
    def get_total_price(self, object):
        return object.total_price()

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        # return relevant fields
        fields = "__all__"
        read_only_fields = ["user", "order_status", "tx_ref"]
    
    def get_total_amount(self, object):
        return object.total_amount()
    

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

class AdminOrderSerializer(serializers.ModelSerializer):
    """
    Docstring for CompactOrderSerializer
    - minimal order schema for simple profile summary
    """
    class Meta:
        model = Order
        fields = "__all__"

class UserProfileViewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    orders = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["user", "orders"]

        