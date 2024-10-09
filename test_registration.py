import requests
import json
url = "http://localhost:5000/register"

data = {
    "username": "roschlynnmichael",
    "email": "roschlynn@outlook.com",
    "mobile_number": "13142291037",
    "password": "roschlynn321"
}

response = requests.post(url, json = data)
print(response.status_code)
print(response.json())
