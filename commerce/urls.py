from django.urls import path, include
from commerce import views
from graphene_django.views import GraphQLView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# register routes
router.register(r"profile", views.ProfileViewSet, basename="profile-viewset")
router.register(r"products", views.ProductViewSet, basename="products-viewset")

# add paths
urlpatterns = [
    path("", include(router.urls)),
    path("payments/webhook/", views.payment_webhook, name="payment-webhook"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard-view"),
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql-endpoint"),
]
