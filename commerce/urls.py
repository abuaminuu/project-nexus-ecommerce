from django.urls import path, include
from commerce import views
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter

user_router = DefaultRouter()

dashboard_router = DefaultRouter()
# register routes
# user_router.register(r"profile", views.ProfileViewSet, basename="profile-viewset")
user_router.register(r"products", views.ProductViewSet, basename="products-viewset")
user_router.register(r"dashboard", views.DashboardViewSet, basename="dashboard-viewset")
dashboard_router.register(r"orders", views.OrderViewSet, basename="orders-viewset") 


# add paths
urlpatterns = [
    # path("", include(router.urls)),  # include the registered routes
    path("", views.ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name="index"),
    path("payments/webhook/", views.payment_webhook, name="payment-webhook"),
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql-endpoint"),
]
