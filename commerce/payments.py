import os
import requests
from rest_framework.response import Response

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def generate_tx_ref():
    import uuid
    return str(uuid.uuid4())

# initiate_payment function to initiate payment with Flutterwave API
def initiate_payment(order_id, name, email, amount, phone, redirect_callback):
    url = "https://api.flutterwave.com/v3/payments"
    tx_ref = generate_tx_ref()
    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "NGN",
        "redirect_url": redirect_callback,
        "metadata": {
            "order_id": order_id,
        },
        "customer": {
            "email": email,
            "name": name,
            "phonenumber": phone,
        },
        "customizations": {
            "title": "Flutterwave Standard Payment Page",
        },
    }

    # "Authorization": f"Bearer {os.environ.get('FLW_SECRET_KEY')}",

    token = "FLWSECK_TEST-6ca15cf9d03c1d2f63f6bdf06a011007-X"

    headers = {
        "Authorization": f"Bearer {token}",
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
    tx_ref = generate_tx_ref()
    
    # Instead of making HTTP request, just return the redirect URL with success params
    separator = '&' if '?' in redirect_url else '?'
    mock_payment_url = f"{redirect_url}{separator}status=successful&tx_ref={tx_ref}&order_id={8}"
    
    return mock_payment_url  # Return the URL directly
