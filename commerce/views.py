from urllib import request
from django.shortcuts import render, get_object_or_404
from commerce.recommendations import simple_recommender
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, serializers, status
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from . import permissions as custom_permissions
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.csrf import csrf_exempt as crsf_exempt
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
from commerce.tasks import send_welcome_email_task

# from rest_framework.filters import DjangoFilterBackend
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_project_nexus.settings')
import django
django.setup()


User = get_user_model()


class UserManagementViewSet():

    @action(detail=False, methods=["GET", "POST"], url_path="reset-password")
    def reset_password(request):
        return HttpResponse("please change your password")
    
# config logger
import logging
logger = logging.getLogger(__name__)


# Custom pagination class (optional)
class CustomPagination(PageNumberPagination):
    page_size = getattr(settings, 'REST_FRAMEWORK', {}).get('PAGE_SIZE', 5)
    page_size_query_param = 'page_size'  # Allow client to override
    max_page_size = getattr(settings, 'REST_FRAMEWORK', {}).get('MAX_PAGE_SIZE', 50)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    logger.info("Accessing RegisterView")
    
    def post(self, request):
        # get data from request
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        
        # handles missing fields
        if not username or not password or not email:
            return Response({"error": "Username, email or password are required"}, status=400)
        
        # check if username already exists
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)

        # if not, create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # send welcome email asynchronously from celery tasks
        send_welcome_email_task.delay(user.email)

        # redirect user to login page after registration
        # TODO change this to a frontend login page url in production
        # after user verifed his email, then redirect to login page
        login_url = reverse("/auth/token/")

        # return response
        return Response({
            "message": "User registered successfully",
            "status": "success",
            "redirect": login_url,
            }, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        from django.contrib.auth.forms import UserCreationForm
        class UserSerializer(serializers.ModelSerializer):
            password = serializers.CharField(write_only=True)

            class Meta:
                model = User
                fields = ["username", "email", "password"]
                ref_name = "UserRegisterSerializer"

            # after creating new user 
            def create(self, validated_data):
                user = User.objects.create(
                    username=validated_data["username"],
                    email=validated_data["email"],
                    password=validated_data["password"]
                )
                return user
        # 
        return UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
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
    

# class handler for product CRUD operations
class ProductViewSet(APIView):
    
    # create product
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)   

        # create a new product
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # get products
    def get(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data)

        # no pk provided, return all products
        products = Product.objects.all()
        paginator = CustomPagination()
        page = paginator.paginate_queryset(products, request)

        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


    # partial update product
    def put(self, request, pk):

        # must be authenticated and owner of the product to update it
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # requires product id to update
        if not pk:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        # check if product exists and belongs to the user
        product = get_object_or_404(Product, pk=pk)
        if product.owner != request.user:
            return Response({"error": "You do not have permission to edit product you dont own!"}, status=status.HTTP_403_FORBIDDEN)
        # else update the product
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # return error if serializer is not valid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # delete product
    def delete(self, request, pk):
        # must be authenticated and owner of the product to delete it
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required !"}, status=status.HTTP_401_UNAUTHORIZED)

        # requires product id to delete
        if not pk:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        # check if product exists and does not belong to the user
        product = get_object_or_404(Product, pk=pk)
        if product.owner != request.user:
            return Response({"error": "You do not have permission to delete product you dont own!"}, status=status.HTTP_403_FORBIDDEN)
        # else delete the product
        product.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_200_OK)    
    
    # works with ModelViewsets only (create separate endpoint for recommendations)
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

class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]


# the final receipt
class OrderViewSet(viewsets.ModelViewSet):

    # + is owner permission, and admin can view all orders
    permission_classes = [IsAuthenticated]
    # serializer class
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.all()
        # TODO filter by current loggedin user
        # prefetch order and their related items
        queryset = queryset.prefetch_related("items", "items__product")
        return queryset

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

        
        order_id = str(order.id)
        name = str(order.user.first_name + " " + order.user.last_name)
        email = str(order.user.email)
        amount = str(order.total_amount())
        phone = str(order.user.is_staff)
        redirect_callback = request.build_absolute_uri(f"/api/commerce/v1.1/payments/callback/{order.id}")        

        # check if payment for this order.id exists in payment table
        payment_exists = Payment.objects.filter(order=order.id).exists()
        if payment_exists is False:
            # make the payment
            payment_url = initiate_payment(order_id, name, email, amount, phone, redirect_callback)

            # local mock payment url for testing without making actual payment
            # payment_url = mock_initiate_payment(redirect_url)

            # proceed to payment gateway and return payment url to frontend
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

# payment callback to present failure/success to the user 
class PaymentCallbackView(APIView):
    
    permission_classes = [permissions.AllowAny]

    def get(self, request, order_id=None):
        data = request.query_params
        reference = data.get("tx_ref")

        message = f"Payment callback received via GET for testing! ref: {reference}"
        transaction_status = data.get("status")
        if transaction_status == "successful":
            # handover success key to frontend for user to see success page
            return Response({
                "success": True,
                "message": message
                }, status=status.HTTP_200_OK)

        # payment failed or cancelled, return error message to frontend for user to see failure page
        message = f"Payment failed/cancelled for order {order_id} with reference: {reference}"
        return Response({
            "order_id": order_id,
            "tx_ref": reference,
            "success": False,
            "message": message
            }, status=status.HTTP_400_BAD_REQUEST)    

# webhook to handle notification from payment gateway without POLLing
class PaymentWebhookView(APIView):
    """ 
    webhook to handle notification from payment gateway without POLLing
    use this to trigger backend workflows like: 
    - sending a receipt 
    - updating an order status to Paid
    - granting access to restricted content.
    - since the endpoint is public and without any authentication, 
      verfiy payment gateways HMAC (Hash-based Message Authentication Code) to avoid 
      spoofing and ensure the request is from a trusted source.
    """
    # No authentication required for webhook
    authentication_classes = []  
    permission_classes = [permissions.AllowAny]

    @crsf_exempt
    def post(self, request):
        """
        Handle payment gateway webhook notifications.
        This endpoint is used to update order status based on payment results.
        """
        # verify HMAC signature
        signature = request.headers.get("X-Payment-Gateway-Signature")

        if not signature:
            return Response({"error": "Missing HMAc signature"}, status=400)
        
        payload = json.loads(request.body)

        # extract tx_ref and order_id
        tx_ref = payload.get("tx_ref")
        order_id = payload.get("order_id")
        
        if order_id is None or tx_ref is None:
            return Response({"error": "Order ID and transaction reference and order id are required/missing"}, status=400)
        
        # get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # check payment status
        Payment_status = payload.get("status")
        if Payment_status == "successful":
            order.status = "paid"
            order.save()

            # create payment record
            Payment.objects.create(
                order=order,
                tx_ref=tx_ref,
                status="confirmed"
            )
            return Response({"message": "Payment confirmed"}, status=200)
        
        elif Payment_status == "failed":
            # restore stock
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            order.status = "failed"
            order.save()
            return Response({"message": "Payment failed, stock restored"}, status=200)

        return Response({"error": "Invalid payment status"}, status=400)
    
# individula line items on reciept (Order)
class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission

# payment table
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission, and admin can view all payments

class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]  # + is owner permission, and admin can view


    @action(detail=False, methods=["GET"], url_path="orders")
    def orders(self, request):
        all_orders = Order.objects.all()

        return Response({
            "all_orders": all_orders
        })
    
    @action(detail=False, methods=["GET"], url_path="products")
    def products(self, request):

        all_products = Product.objects.all()
        serializer = ProductSerializer(all_products, many=True)
        page = self.paginate_queryset(serializer.data)

        return Response({
            "all_products": page
        })  
    
    @action(detail=False, methods=["GET"], url_path="users")
    def users(self, request):
        all_users = User.objects.all()
        serializer = UserSerializer(all_users, many=True)
        page = self.paginate_queryset(serializer.data)
        
        return Response({
            "all_users": page
        })
    
    @action(detail=False, methods=["GET"], url_path="payments")
    def payments(self, request):
        all_payments = Payment.objects.all()

        return Response({
            "all_payments": all_payments
        })  
    
    # TODO add (users, products, orders, order items, payments) stats 
    # for the last 7 days, 30 days, and 1 year
    # and add privilege check for admin only to access this dashboard view
