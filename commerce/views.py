from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    # TODO show all products here later, login, signup
    return HttpResponse(f" Home...{request.method}")
