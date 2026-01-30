from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import viewsets, serializers
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
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from commerce.payments import initiate_payment

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_project_nexus.settings')
import django
django.setup()


User = get_user_model()
class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny)

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        pass
    def get_serializer_class(self):
        from django.contrib.auth.forms import UserCreationForm
        class UserSerializer(serializers.ModelSerializer):
            password = serializers.CharField(write_only=True)

            class Meta:
                model = User
                fields = ["username", "email", "password"]

            def create(self, validated_data):
                user = User.objects.create(
                    username=validated_data["username"],
                    email=validated_data["email"],
                    password=validated_data["password"]
                )
                return user
        return UserSerializer

# Create your views here.
class USerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=["GET"])
    def profile(self, request, pk=None):
        user = self.get_object()
        products = None #Product.objects.filter()  # TODO filter by user if owner field is added
        orders = Order.objects.filter(user=user)
        payments = None
        return Response({
            "bio": UserSerializer(user).data,
            "products": products,
            "orders": OrderSerializer(orders, many=True).data,
            "payments": payments,
        })
    

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny] # + is owner permission

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]  # + is owner permission
        return super(ProductViewSet, self).get_permissions()
    

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # + is owner permission, and admin can view all orders
    
    def get_queryset(self):
        queryset = Order.objects.all()
        # TODO filter by current loggedin user
        # prefetch order and their related items
        queryset = queryset.prefetch_related("items", "items__product")
        return queryset

    # serializer class
    serializer_class = OrderSerializer

    # add item to existing order
    @action(detail=True, methods=["GET"], url_path="add_item/(?P<pid>[^/.]+)")
    def add_item(self, request, pk=None, pid=None):
        # get current order object
        order = self.get_object()        
        try:
            product = Product.objects.get(pk=pid)
            # check if product exists
            existing_item = order.items.filter(product=product).first()
            if existing_item:
                existing_item.quantity += 1
                existing_item.save()
                # return redirect(r"{/orders/{order.id/}")
            else:
                # add new order item
                OrderItem.objects.update_or_create(
                    order=order,
                    product=product,
                    price=product.price,
                    quantity=1,
                )
            return Response(f"Added product {product.name} to order {order.id}")
        
        except Product.DoesNotExist:
            # return redirect({"error": "Product does not exist"}, status=404)
            return Response({f"error": "Product {pid} does not exist"}, status=404)
    
    @action(detail=False, methods=["GET"], url_path="create_order_with_item/(?P<pid>[^/.]+)")
    def create_order_with_item(self, request, pk=None, pid=None):
        user = request.user
    
        # create new order
        order = Order.objects.create(
            user=user,
            order_status="pending"
        )
        
        # TODO add item to order only if product exists
        try:
            product = Product.objects.get(pk=pid)
            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                quantity=1,
            )
            return Response(f"Created order {order.id} with product {product.name}")
        except Product.DoesNotExist:
            return Response({
                "error": "Product " + pid + " does not exist"}, 
                status=404
            )


    @action(detail=True, methods=["POST"])
    def pay(self, request, pk=None):
        order = self.get_object()
        # build absolute redirect url from request info
        id = str(order.id)
        name = str(order.user.first_name + " " + order.user.last_name)
        email = str(order.user.email)
        amount = str(order.total_amount())
        phone = str(order.user.is_staff)
        redirect_url = f"http://127.0.0.1:8001/api/orders/{order.id}/confirm_payment/"

        payment_url = initiate_payment(id, name, email, amount, phone, redirect_url)
        return Response({
            "payment_url": payment_url,
            "total_amount": amount,
        })
    
    @action(detail=True, methods=["POST"])
    def confirm_payment(self, request, pk=None):
        order = self.get_object()
        # get query params from request
        tx_ref = request.query_params.get("tx_ref")
        status = request.query_params.get("status")
        if status != "successful":
            # redirect to payment failed page or return failed response
            return Response({"status": f"Payment failed or cancelled for order {order.id}.. retry"})
        if status:
            if status == "successful":
                # get order details and update payment status
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=order.total_amount(),
                    status="confirmed",
                    method="card",
                )
                return Response({
                    "status": "Payment confirmed",
                    "order_id": order.id,
                    "message": "wait for shipment",
                })
            else:
                return Response({
                            "status": status,
                            "order_id": order.id,
                            "message": "wait for shipment",
                        })
        # something went wrong
        return Response({"error": "Invalid payment confirmation request"}, status=400)

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission, and admin can view all payments
