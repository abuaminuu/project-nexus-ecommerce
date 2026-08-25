# project level views
from rest_framework import urls
from django.http import JsonResponse

def index(request):
    # TODO check which user for specific app(auth will handle such for API external request)
    # get list of available app and return to FE
    return JsonResponse({
        "message": "Welcome to the Multi-App API Gateway",
        "apps": {
            "commerce": "/api/commerce/v1.1/",
            "second_app": "/api/v1.0/maahad/"
        }
    })
