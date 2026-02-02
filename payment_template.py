import os
import requests

url = "https://api.flutterwave.com/v3/payments"

payload = {
    "tx_ref": "UNIQUE_TRANSACTION_REFERENCE",
    "amount": "7500",
    "currency": "NGN",
    "redirect_url": "https://example_company.com/success",
    "customer": {
        "email": "developers@flutterwavego.com",
        "name": "Flutterwave Developers",
        "phonenumber": "09012345678",
    },
    "customizations": {
        "title": "Flutterwave Standard Payment",
    },
}

headers = {
    "Authorization": f"Bearer {os.environ.get('FLW_SECRET_KEY')}",
    "Content-Type": "application/json",
}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()  # raises HTTPError for 4xx/5xx
    data = response.json()
    print(data)

except requests.exceptions.RequestException as err:
    print("Error:", err)
    if err.response is not None:
        print(err.response.json())
