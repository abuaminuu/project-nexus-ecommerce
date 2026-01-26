from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import viewsets
from commerce.models import User, Product, Order, OrderItem, Payment
from commerce.serializers import (
    UserSerializer,
    ProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
    PaymentSerializer,
    PaymentSerializer,
)
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from commerce.payments import initiate_payment


# Create your views here.
class USerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    @action(detail=True)
    def pay(self, request, pk=None):
        order = self.get_object()
        amount = order.total_amount()
        email = order.user.email
        redirect_url = "127.0.0.1:8001/api/orders/confirm_payment/"
        # request.build_absolute_uri(f"/orders/{order.id}/confirm_payment/")

        payment_url = initiate_payment(amount, email, redirect_url)
        return Response({"payment_url": payment_url})
    
    @action(detail=True)
    def confirm_payment(self, request, pk=None):
        order = self.get_object()
        # Here you would typically verify the payment status with the payment gateway
        # For simplicity, we'll assume the payment was successful
        order.status = "paid"
        order.save()
        return Response({"status": "Payment confirmed", "order_id": order.id})
    

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
