from django.shortcuts import get_object_or_404
from commerce.recommendations import simple_recommender
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework import viewsets, serializers, status
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from rest_framework.pagination import PageNumberPagination
from commerce.permissions import IsOwnerOrReadOnly
from django.conf import settings
from django.db.models import Q, Sum, Count
from rest_framework.pagination import PageNumberPagination
from commerce.models import User, Product, Order, OrderItem, Payment
from commerce.serializers import (
    UserSerializer,
    ProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
    PaymentSerializer,
    UserProfileViewSerializer
)

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from commerce.payments import initiate_payment, generate_txref
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
from django.utils import timezone

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

        # TODO change this to a frontend login page url in production
        # after user verifed his email, then redirect to login page frontend
        login_url = "/auth/login/"

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

class UserManagementViewSet():
    # only admin can see this
    @action(detail=False, methods=["GET", "POST"], url_path="reset-password")
    def reset_password(request):
        return HttpResponse("please change your password")

class UserProfileViewSet(APIView):

    permission_classes = [IsAuthenticated]


    def get(self, request, pk=None):
        user = request.user
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

    #ovverride getpermission to non auth see all products, other verbs must be authenticated
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
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

# products recommendations
class ProductRecommendationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk=None):
        product = Product.objects.get(pk=pk)
        # stub logic for testing (implement with ML Later)
        recommended_products = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id)[:5]

        serializer = ProductSerializer(recommended_products, many=True)

        return Response({
            "products": product.name,
            "recommendations": serializer.data
        }, status=status.HTTP_200_OK)

# the final receipt/cart
class OrderViewSet(viewsets.ModelViewSet):
    # + is owner permission, and admin can view all orders
    permission_classes = [IsAuthenticated]
    # serializer class
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.all()
        # prefetch order and their related items
        queryset = queryset.prefetch_related("items", "items__product")

        # admin can view/edit all orders; regular users see thier own
        if user.is_staff:
            return queryset

        # specific to user
        return queryset.filter(user=user)

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
    @action(detail=True, methods=["POST"], url_path="add_item/(?P<pid>[^/.]+)")
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
            return Response({f"error": "Product {pid} does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=["POST"], url_path="create_order_with_item/(?P<pid>[^/.]+)")
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
                status=status.HTTP_404_NOT_FOUND
            )

    # basename -> order-viewset-pay
    @action(detail=True, methods=["POST"], url_path="pay")
    def pay(self, request, pk=None):

        # lock row to prevent race condition during rapid double clicks
        with transaction.atomic():
            order = self.get_queryset().select_for_update().get(pk=pk)

            #1 guard against already processing/paid orders
            if order.order_status in ["paid", "processing"]:
                # order paid already
                return Response({
                    "error": f"order {order.id} paid already/processing"
                }, status=status.HTTP_400_BAD_REQUEST)

            #2 check stock availability withut deducting yet
            for item in order.items.select_related("product"):
                if item.product.stock < item.quantity:
                    return Response({
                        "error": f"Insufficient stock for item {item.product.name}"
                    }, status=status.HTTP_400_BAD_REQUEST)

            #3 reuse existing tx_ref for retrying payments
            if not order.tx_ref:
                order.tx_ref = f"{request.user}:{order.id}:{generate_txref()}"
                order.order_status = "pending"
                order.save(update_fields=["tx_ref", "order_status"])
            
            #4 construct payment payload
            name = str(order.user.first_name + " " + order.user.last_name)
            email = str(order.user.email)
            amount = str(order.total_amount())
            phone = "+234567890"
            redirect_callback = request.build_absolute_uri(f"/api/commerce/v1.1/payments/callback/{order.id}")        

            #4 request payment gateway link
            payment_url = initiate_payment(order.tx_ref, name, email, amount, phone, redirect_callback)

            # proceed to payment gateway and return payment url to frontend
            return Response({
                "payment_url": payment_url
            }, status=status.HTTP_200_OK)

    # override create to enforce ownership while creating
    def perform_create(self, serializer):
        # allow admin to specify target user in payload
        target_user_id = self.request.data.get("user")

        # admin is doing the work for someone
        if self.request.user.is_staff and target_user_id:
            serializer.save(user_id=target_user_id)
        else:
            # user doing it for themselves
            serializer.save(user=self.request.user)

    # do for pwerfome as well
    def perform_update(self, serializer):
        target_user_id = self.request.data.get("user")
        
        # Admin can explicitly reassign ownership during update if user is passed
        if self.request.user.is_staff and target_user_id:
            serializer.save(user_id=target_user_id)
        else:
            # Preserves existing order.user (does NOT override with admin's account)
            serializer.save()

# payment callback to present failure/success to the user 
class PaymentCallbackView(APIView):
    
    permission_classes = [permissions.AllowAny]

    def get(self, request, order_id=None):
        data = request.query_params.dict()
        reference = data.get("tx_ref")
        transaction_status = data.get("status")

        if transaction_status == "successful":
            # handover success key to frontend for user to see success page
            return Response({
                "success": True,
                "order_id": order_id,
                "data": data
                }, status=status.HTTP_200_OK)

        # else payment failed or cancelled, return error message to frontend for user to see failure page
        message = f"Payment failed/cancelled for order {order_id} with reference: {reference}"
        return Response({
            "success": False,
            "order_id": order_id,
            "data": data
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

    def post(self, request):
        """
        Handle payment gateway webhook notifications.
        This endpoint is used to update order status based on payment results.
        """

        # verify HMAC signature
        signature = request.headers.get("verif-hash")

        if not signature:
            return Response({"error": "Missing HMAc signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        if signature != getattr(settings, "FLUTTERWAVE_SECRET_HASH"):
            return Response({"error": "Invalid HMAC signature"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError as e:
            return Response({"error": "Invalid JSON in request body"}, status=status.HTTP_400_BAD_REQUEST)

        # get event and data from payload
        event_type = payload.get("event.type") or payload.get("event")
        payment_status = payload.get("status")
        valid_events = ["CARD_TRANSACTION", "charge.complete", None]

        # extract tx_ref and order_id
        tx_ref = payload.get("tx_ref") or payload.get("txRef")
        user_id = tx_ref.split(":")[0]

        if not tx_ref:
            return Response({""
            "error": "Missing transaction reference (tx_ref) in payload"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # get order by tx_ref
        try:
            order = Order.objects.get(tx_ref=tx_ref)

            # handle succesful payment
            if (event_type in valid_events) and payment_status == "successful":
                # avoid reprocessing order
                if order.order_status != "paid":
                    order.user = None
                    order.order_status = "paid"
                    order.save()            

                # TODO Trigger additional workflows (send email, grant access, logistics etc.)

                # create  a payment record
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=payload.get("charged_amount"),
                    status="paid",
                    tx_ref=tx_ref,
                    method=valid_events[0]
                )

                # seee what comes back
                return Response({
                    "success": True,
                    "message":"Webhook Processed !",
                    "payload": payload
                }, status=status.HTTP_200_OK)
        
        except Order.DoesNotExist:
            return Response({
                "error": f"Order not found for transaction reference: {tx_ref}"
            }, status=status.HTTP_404_NOT_FOUND)

# individula line items on reciept (Order)
class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    # + is owner & admin permission
    permission_classes = [IsAuthenticated]  

# payment table
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    # only admin can view all payments
    permission_classes = [IsAuthenticated]  

# admin analytics
class AdminDashboardViewSet(viewsets.GenericViewSet):

    # only IsAdminUser can view
    permission_classes = [IsAdminUser] 
    
    @action(detail=False, methods=["GET"], url_path="metrics")
    def metrics(self, request):
        today = timezone.now.date()

        # totla and daily revenue
        total_revenue = Payment.objects.filter(status="successfull").aggregate(
            total=sum("amount")
        )["total"] or 0

        # order breakdown by status
        order_counts = Order.objects.aggregate(
            pending=Count("id", filter=Q(order_status="pending")),
            processing=Count("id", filter=Q(order_status="processing")),
            paid=Count("id", filter=Q(order_status="paid")),
            cancelled=Count("id", filter=Q(order_status="cancelled")),   
        )

        # inventory warning
        low_stock_products = Product.objects.filter(stock__lte=5).values("id", "name", "stuck")

        return Response({
            "revenue": {
                "total": total_revenue
            },
            "order_summary": order_counts,
            "inventory_alerts": list(low_stock_products)
        })

class AdminOrderViewset(viewsets.ModelViewSet):

    @action(detail=False, methods=["GET"], url_path="orders")
    def orders(self, request):
        # queryset = Order.objects.all()
        queryset = Order.objects.prefetch_related("items__product").order_by("-created_at")
        paginator  = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # else fallback global pagination settings
        serializer = OrderSerializer(queryset, many=True)
        return Response({
            "orders": serializer.data
        })
    
    
    @action(detail=False, methods=["GET"], url_path="payments")
    def payments(self, request):
        payments = Payment.objects.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response({
            "payments": serializer.data
        })  
    
    # TODO add (users, products, orders, order items, payments) stats 
    # for the last 7 days, 30 days, and 1 year
    # and add privilege check for admin only to access this dashboard view
    