from . import views
from django.urls import path

urlpatterns = [
    path("", views.index, name="maahad-index"),
    # Add more paths for your app's views here
]
