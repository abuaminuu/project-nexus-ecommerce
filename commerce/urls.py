from django.urls import path, include
from commerce import views
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter

# router object
router = DefaultRouter()

# register user facing endpoints
# user_router.register(r"profile", views.ProfileViewSet, basename="profile-viewset")
router.register(r"orders", views.OrderViewSet, basename="orders-viewset")
router.register(r"order-items", views.OrderItemViewSet, basename="ordersitems-viewset")

# admin dashboard endpoints for admin users
router.register(r"dashboard/orders", views.OrderViewSet, basename="dashboard-orders-viewset") 
router.register(r"dashboard/payments", views.PaymentViewSet, basename="dashboard-payment-viewset") 

# add paths
urlpatterns = [
    path("products/", views.ProductViewSet.as_view(), name="index"),
    path("products/<int:pk>/", views.ProductViewSet.as_view(), name="product-detail"),
    path("payments/callback/<str:order_id>", views.PaymentCallbackView.as_view(), name="payments-callback-view"),
    path("payments/webhook/", views.PaymentWebhookView.as_view(), name="payments-webhook-view"),
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql-endpoint"),
]

urlpatterns += router.urls
