import os
import requests
from rest_framework.response import Response

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def generate_tx_ref():
    import uuid
    return str(uuid.uuid4())

def initiate_payment(id, name, email, amount, phone, redirect_url):
    url = "https://api.flutterwave.com/v3/payments"
    tx_ref = generate_tx_ref()
    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "NGN",
        "redirect_url": redirect_url,
        "customer": {
            "email": email,
            "name": name,
            "phonenumber": phone,
        },
        "customizations": {
            "title": "Flutterwave Standard Payment Page",
        },
    }

    headers = {
        "Authorization": f"Bearer {os.environ.get('FLW_SECRET_KEY')}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # raises HTTPError for 4xx/5xx
        # returns payment link
        data = response.json()
        if data["status"] == "success":
            # return data as url
            return data["data"]["link"]
        

    except requests.exceptions.RequestException as err:
        if err.response is not None:
            return (f"{err} -> {err.response.json()}")
        return f"Request error: {err}"

def mock_initiate_payment(redirect_url):
    """
    Mock payment function - returns success URL directly
    """
    tx_ref = generate_tx_ref()
    
    # Instead of making HTTP request, just return the redirect URL with success params
    separator = '&' if '?' in redirect_url else '?'
    mock_payment_url = f"{redirect_url}{separator}status=successful&tx_ref={tx_ref}&order_id={8}"
    
    return mock_payment_url  # Return the URL directly

class Order():
    def __init__(self, id, name, email, amount, phone, redirect_url):
        self.id = id
        self.email = email
        self.name = name
        self.amount = amount
        self.phone = phone
        self.redirect_url = redirect_url


# redirect_url = f"http://127.0.0.1:8001/api/orders/{1}/confirm_payment/"
# init_pay = initiate_payment(1, "John Doe", "john.doe@example.com", 1800, "1234567890", redirect_url)
# print(init_pay if init_pay else "no response")
# print(init_pay if init_pay else "no response")
# print(init_pay["data"]["link"])
# for k, v in init_pay.items():
    # print(f"{k}: {v}")
