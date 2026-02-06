from django.urls import path, include
from commerce import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r"users", views.USerViewSet, basename="users-viewset")
router.register(r"products", views.ProductViewSet, basename="products-viewset")
router.register(r"orders", views.OrderViewSet, basename="orders-viewset")
router.register(r"order_items", views.OrderItemViewSet, basename="order-items-viewset")
router.register(r"payments", views.PaymentViewSet, basename="payments-viewset")

urlpatterns = [
    path("", include(router.urls)),
]
