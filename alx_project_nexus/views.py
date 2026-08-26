# project level views
from rest_framework import urls
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from commerce.models import User

import json

def index(request):
    # TODO check which user for specific app(auth will handle such for API external request)
    # get list of available app and return to FE
    return Response({
        "message": "Welcome to the Multi-App API Gateway",
        "apps": {
            "commerce": "/api/commerce/v1.1/",
            "second_app": "/api/v1.0/maahad/"
        }
    }, status=status.HTTP_200_OK)


# allow crsf_token, use email to validate user
@api_view(["POST"])
@permission_classes([AllowAny])
def recover_password(request):
    
    # get request data from POST
    email = request.data.get("email")
    password1 = request.data.get("password1")
    password2 = request.data.get("password2")
    code = request.data.get("code")

    # validate data, chech db for token and return appropriate error
    if password1 != password2:
        return Response({
            "message": "passowords donot match"
        }, status=status.HTTP_400_BAD_REQUEST)

    # get reset code from db and match with user supplied code
    db_code = None
    email_code = None
    if db_code != email_code:
        return Response({
           "message": "check email for code and try again!"
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message":"password reset successful",
        "success":True,
        "data": request.data,
    }, status=status.HTTP_201_CREATED)


# allow crsf_token, use email to validate user
@api_view(["POST"])
@permission_classes([AllowAny])
def recover_email(request):
    
    # get request data from POST
    email = request.data.get("email")
    
    # ask security questions

    return Response({
        "message":f"email: {email} recover successful",
        "success":True
    }, status=status.HTTP_201_CREATED)


def send_mail_confirmation(email, *kargs, **kwargs):
    """
    sends email confirmation code for user that:
    - register
    - reset password
    - any other security measure to confirm that user requesting resource has access to his email
    - generate password reset link
    """
    # verify email first
    if validate_email(email):
        return Response({
            "message":"please check your email for code: use: 'abc-fg1'"
        }, status=status.HTTP_200_OK)


def validate_email(request):
    email = request.data.get("email")
    if User.objects.get(email=email):
        return True
    return False
    