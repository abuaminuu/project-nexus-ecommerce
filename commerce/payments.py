import os
import requests
from rest_framework.response import Response
import uuid
from django.conf import settings

# initiate_payment function to initiate payment with Flutterwave API
def initiate_payment(tx_ref, name, email, amount, phone, redirect_callback):

    url = "https://api.flutterwave.com/v3/payments"
    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "NGN",
        "redirect_url": redirect_callback,
        "customer": {
            "email": email,
            "name": name,
            "phonenumber": phone,
        },
        "customizations": {
            "title": "Bektop Ecommerce Payment",
        },
    }

    # "Authorization": f"Bearer {os.environ.get('FLW_SECRET_KEY')}",
    # remove the above line and use the hardcoded token for testing purposes

    headers = {
        "Authorization": f"Bearer {getattr(settings, "FLUTTERWAVE_SECRET_KEY", None)}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        # raises HTTPError for 4xx/5xx
        response.raise_for_status()  
        # returns payment link
        data = response.json()
        if data["status"] == "success":
            # return data as url
            return data["data"]["link"]
    
    except requests.exceptions.RequestException as err:
        if err.response is not None:
            return (f"{err} -> {err.response.json()}")
        return f"Request error: {err}"

# mocking the initiate_payment function for testing purposes
def mock_initiate_payment(redirect_url):
    """
    Mock payment function - returns success URL directly
    """
    # Generate a unique transaction reference
    import uuid
    tx_ref = str(uuid.uuid4())  
    
    # Instead of making HTTP request, just return the redirect URL with success params
    separator = '&' if '?' in redirect_url else '?'
    mock_payment_url = f"{redirect_url}{separator}status=successful&tx_ref={tx_ref}&order_id={8}"
    
    return mock_payment_url  # Return the URL directly

def generate_txref():
    return uuid.uuid4()
