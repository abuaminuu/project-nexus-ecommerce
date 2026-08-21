from django.urls import path, include
from commerce import views
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter

user_router = DefaultRouter()
# register routes
# user_router.register(r"profile", views.ProfileViewSet, basename="profile-viewset")
user_router.register(r"orders", views.OrderViewSet, basename="orders-viewset")
user_router.register(r"dashboard", views.DashboardViewSet, basename="dashboard-viewset")
# user_router.register(r"payments", views.PaymentViewSet, basename="payments-viewset")
# admin dashboard router for admin users
dashboard_router = DefaultRouter()
dashboard_router.register(r"orders", views.OrderViewSet, basename="orders-viewset") 

# add paths
urlpatterns = [
    # path("", include(router.urls)),  # include the registered routes
    path("products/", views.ProductViewSet.as_view(), name="index"),
    path("products/<int:pk>/", views.ProductViewSet.as_view(), name="product-detail"),
    path("payments/callback/<str:order_id>", views.PaymentCallbackView.as_view(), name="payments-callback-view"),
    path("payments/webhook/", views.PaymentWebhookView.as_view(), name="payments-webhook-view"),
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql-endpoint"),
]

urlpatterns += user_router.urls
