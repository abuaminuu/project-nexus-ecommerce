from django.urls import path, include
from commerce import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

# add swagger docs


router = DefaultRouter()

router.register(r"users", views.USerViewSet, basename="users")
router.register(r"products", views.ProductViewSet, basename="products")
router.register(r"orders", views.OrderViewSet, basename="orders")
router.register(r"order_items", views.OrderItemViewSet, basename="order-items")
router.register(r"payments", views.PaymentViewSet, basename="payments")

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("", include(router.urls)),
]
