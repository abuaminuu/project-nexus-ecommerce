from django import test
from django.urls import reverse
import os
import requests
import unittest
from .models import User, Product
# from .views import ProductSerializer
from rest_framework.test import APIClient
from rest_framework import status


# import pytest

# import view modules
# test models

def add(x, y):
    return x + y

class BasicTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2,4), 6)
        self.assertEqual(add(0,0), 0)
        self.assertEqual(add(-2,4), 2)


class TestProductViewSet(test.TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="admin")
        self.normal_user = User.objects.create_user(
            username="user1", email="user1@example.com", password="user1")
        
        self.product = Product.objects.create(
            owner=self.normal_user,
            name="Cushion",
            description="A nice cushion",
            category="Electronics",
            price=9.99, 
            stock=3,
        )
        # from router basename in urls.py
        # supports create/list
        self.list_url = reverse("products-viewset-list")
        self.detail_url = reverse("products-viewset-detail", kwargs={"pk": self.product.pk})

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Cushion")

    def test_product_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        # for paginated data
        self.assertEqual(response.data["results"][0]["name"], "Cushion")

    def test_product_detail(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Cushion")

    def test_product_create_unauthenticated(self):
        # structure serializer expects
        data = {
            "name": "New Product",
            "description": "New Description",
            "category": "Fashion",
            "price": 15.99,
            "stock": 4,
        }
        response = self.client.post(self.list_url, data)
        # Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_create_authenticated(self):
        data = {
            "name": "New Product",
            "description": "New Description",
            "category": "Fashion",
            "price": 15.99,
            "stock": 4,
        }
        self.client.login(username="user1", password="user1")
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Product")
        self.client.logout()
        