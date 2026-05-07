"""
URL configuration for alx_project_nexus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from commerce import views
from . import views as root_views
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.conf import settings
import debug_toolbar

# add swagger docs: schema view config
schema_view = get_schema_view(
    openapi.Info(
        title="E-commerce API",
        default_version="v1",
        description="API documentation for the E-commerce application",
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[]
)

urlpatterns = [
    path("", root_views.index, name="root"),
    path("admin/", admin.site.urls),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("reset-password/", views.UserManagementViewSet, name="reset-password"),

    # for commerce app
    path("api/", include("commerce.urls")),
    path("api/v1.1/", include("commerce.urls")),
    path("api/swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),

    # for other apps(with their documentation)
    # TODO

    # for login route
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'), name="api-auth"),
    path('__debug__/', include(debug_toolbar.urls)),
]

# debug in dev only
# if settings.DEBUG:
#     import debug_toolbar
