from django.urls import path
from commerce import views
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter


# router object
router = DefaultRouter()

# admin dashboard endpoints for admin users
router.register(r"dashboard/orders", views.AdminOrderViewset, basename="admin-orders") 
router.register(r"dashboard/payments", views.PaymentViewSet, basename="admin-payment") 
router.register(r"dashboard/analytics", views.AdminDashboardViewSet, basename="admin-analytics")

# register user facing endpoints
router.register(r"orders", views.OrderViewSet, basename="orders-viewset")
router.register(r"order-items", views.OrderItemViewSet, basename="ordersitems-viewset")


# add paths
urlpatterns = [
    path("profile/", views.UserProfileViewSet.as_view(), name="user-profile"),
    path("products/", views.ProductViewSet.as_view(), name="products-view"),
    path("products/<int:pk>/", views.ProductViewSet.as_view(), name="product-detail"),
    path("products/<int:pk>/recommendations", views.ProductRecommendationView.as_view(), name="product-recommendations"),
    path("payments/callback/<str:order_id>", views.PaymentCallbackView.as_view(), name="payments-callback-view"),
    path("payments/webhook/", views.PaymentWebhookView.as_view(), name="payments-webhook-view"),
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql-endpoint"),
]

# add router urls
urlpatterns += router.urls
