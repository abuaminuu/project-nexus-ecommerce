from django.shortcuts import render, get_object_or_404
from commerce.recommendations import simple_recommender
from rest_framework.response import Response
from rest_framework import viewsets, serializers
from rest_framework.serializers import Serializer
from commerce.models import User, Product, Order, OrderItem, Payment
from commerce.serializers import (
    UserSerializer,
    ProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
    PaymentSerializer,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from commerce.payments import initiate_payment, mock_initiate_payment
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
from commerce.filters import ProductFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import filters
import json
from django.http import HttpResponse

# from rest_framework.filters import DjangoFilterBackend
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_project_nexus.settings')
import django
django.setup()


User = get_user_model()


def reset_password(request):
    
    return HttpResponse("please change your password")
    

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        pass
        if not username or not password or not email:
            return Response({"error": "Username, email and password are required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return Response({"message": "User registered successfully"}, status=201)

    def get_serializer_class(self):
        from django.contrib.auth.forms import UserCreationForm
        class UserSerializer(serializers.ModelSerializer):
            password = serializers.CharField(write_only=True)

            class Meta:
                model = User
                fields = ["username", "email", "password"]
                ref_name = "UserRegisterSerializer"

            def create(self, validated_data):
                user = User.objects.create(
                    username=validated_data["username"],
                    email=validated_data["email"],
                    password=validated_data["password"]
                )
                return user
        return UserSerializer


class USerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


    @action(detail=True, methods=["GET"], url_path="profile")
    def profile(self, request, pk=None):
        user = self.get_object()
        refresh = RefreshToken.for_user(user)
        products = Product.objects.filter(owner=user)
        orders = Order.objects.filter(user=user)
        payments = Payment.objects.filter(user=user)
        return Response({
            "bio": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "products": ProductSerializer(products, many=True).data,
            "orders": OrderSerializer(orders, many=True).data,
            "payments": PaymentSerializer(payments, many=True).data,
        })
    

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # ["=name"] for exact match for fields
    search_fields = ["name", "description"]
    ordering_fields = ["name", "price", "stock"]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            # TODO: add is owner permissions
            IsOwner = None
            self.permission_classes = [IsAuthenticated]  
        return super(ProductViewSet, self).get_permissions()


    @action(detail=True, methods=['GET'], url_path="recommendations")
    def recommendations(self, request, pk=None):
        """Get product recommendations"""
        product = self.get_object()
        recommended_products = simple_recommender.simple_recommendations(product.id, limit=4)
        
        serializer = ProductSerializer(recommended_products, many=True)
        return Response({
            'product': product.name,
            'recommended_products': serializer.data
        })
    

def payment_webhook(request):
    """ 
    webhook to handle notification from payment gateway without POLLing
    use this to trigger backend workflows like: 
    - sending a receipt 
    - updating an order status to Paid
    - granting access to digital content.
    """

    #get raw data
    payload = json.loads(request.body)

    # extract tx_ref and order_id
    tx_ref = payload.get("tx_ref", "")
    order_id = payload.get("order_id", "")
    if not order_id:
        return HttpResponse(status=400)
    
    # get the order
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExists as e:
        return HttpResponse(status=404)
    
    # check payment status
    status = payload.get("status")
    if status == "successfull":
        order.status = "paid"
        order.save()

        # create payment record
        Payment.objects.create(
            order=order,
            tx_ref=tx_ref,
            status="confirmed"
        )
    elif status == "failed":
        # restore stock
        for item in Order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        order.status = "failed"
        order.save()

    return HttpResponse(payload, status=200)


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

    @swagger_auto_schema(
        method='post',
        operation_description="Add item to order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Product ID'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity', default=1),
            },
            required=['product_id']
        ),
        responses={
            200: openapi.Response('Item added successfully'),
            404: 'Product not found',
            400: 'Bad request'
        }
    )

    # add item to existing order
    @action(detail=True, methods=["POST", "GET"], url_path="add_item/(?P<pid>[^/.]+)")
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
        
        # add item to order only if product exists
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

    # basename -> order-viewset-pay
    @action(detail=True, methods=["POST"], url_path="pay")
    def pay(self, request, pk=None):
        order = self.get_object()
        
        # reserve stock before redirecting to payment
        for item in order.items.all():
            product = item.product
            if product.stock < item.quantity:
                return Response({'error': 'Insufficient stock'}, status=400)
            # else
            product.update_stocks(item.quantity)

        
        id = str(order.id)
        name = str(order.user.first_name + " " + order.user.last_name)
        email = str(order.user.email)
        amount = str(order.total_amount())
        phone = str(order.user.is_staff)
        redirect_url = request.build_absolute_uri(f"/api/orders/{order.id}/confirm-payment/")
        redirect_webhook = request.build_absolute_uri(f"/api/payments/webhook/{order.id}")
        
        # TODO change in prod
        redirect_url = redirect_webhook

        # check if payment for this order.id exists in payment table
        payment_exists = Payment.objects.filter(order=order.id).exists()
        if payment_exists is False:
            # make the payment
            # payment_url = initiate_payment(id, name, email, amount, phone, redirect_url)
            payment_url = mock_initiate_payment(redirect_url)

            return Response({
                "payment_url": payment_url,
                "total_amount": amount,
            })

        # order paid already
        return Response({
            "message": f"order {order.id} paid already/processing"
        })

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('tx_ref', openapi.IN_QUERY, description="Transaction Reference", type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, description="Payment Status", type=openapi.TYPE_STRING),
        ]
    )
    @action(detail=True, methods=["GET"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        order = self.get_object()

        # check for  payment status for this order.id to avoid double update stock
        pay_exists = Payment.objects.filter(order=order.id, status__in=["confirmed","paid"]).exists()
        if pay_exists is True:
            return Response({
                "message": f"payment: {pay_exists.id} with order: {order.id} is under processing"
            })
        
        # else get status query param from request
        status = request.query_params.get("status")

        # redirect to payment failed page or return failed response
        if status != "successful":
            # rollback stock updates
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()

            # payment failed for other reasons
            return Response({"status": f"Payment failed or cancelled for order {order.id}.. retry"})

        # get tx_ref query param from request
        tx_ref = request.query_params.get("tx_ref")

        # if status success
        if status == "successful":
            # get order details and update payment status
            pay = Payment.objects.create(
                user=order.user,
                order=order,
                amount=order.total_amount(),
                status="confirmed",
                tx_ref=tx_ref,
                method="card",
            )

            # TODO send order information to logistics

            return Response({
                "items":str(Order.items),
                "pay_id": pay.id,
                "status": "Payment confirmed",
                "order_id": order.id,
                "message": "wait for shipment",
                "tx_ref": tx_ref,
            })
        else:
            # something went wrong/ order paid already
            return Response({
                "error": "the order: " + str(order.id ) + " is paid already",
                "message": "Invalid payment confirmation request"
            }, status=400
            )
        
    # confirm payment webhhok
    @action(detail=False, methods=["POST"], url_path="comfirm-payment-webhook")
    def comfirm_payment_webhook(request):
        """ 
        webhook to handle notification from payment gateway without POLLing
        use this to trigger backend workflows like: 
        - sending a receipt 
        - updating an order status to Paid
        - granting access to digital content.
        """

        #get raw data
        payload = json.loads(request.body)

        # extract tx_ref and order_id
        tx_ref = payload.get("tx_ref", "")
        order_id = payload.get("order_id", "")
        if not order_id:
            return HttpResponse(status=400)
        
        # get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExists as e:
            return HttpResponse(status=404)
        
        # check payment status
        status = payload.get("status")
        if status == "successfull":
            order.status = "paid"
            order.save()

            # create payment record
            Payment.objects.create(
                order=order,
                tx_ref=tx_ref,
                status="confirmed"
            )
        elif status == "failed":
            # restore stock
            for item in Order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            order.status = "failed"
            order.save()

        return HttpResponse(payload, status=200)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission, and admin can view all payments
