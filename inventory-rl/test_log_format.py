
import requests
import json
import time

url = "http://127.0.0.1:8000/predict"

# 1. Test standard request (no extra data)
print("\n--- TEST 1: Standard Request ---")
payload1 = {
    "inventory": 45.0,
    "day_index": 12,
    "day_of_week": 2,
    # No optional fields
}
try:
    response = requests.post(url, json=payload1)
    if response.status_code == 200:
        data = response.json()
        print("Response received!")
        print(f"formatted_log length: {len(data.get('formatted_log', ''))}")
        print("Log output received from API:")
        print(data.get('formatted_log'))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Connection failed: {e}")

# 2. Test request WITH demand/sold data
print("\n--- TEST 2: Request with Demand/Sold ---")
payload2 = {
    "inventory": 30.0,
    "day_index": 13,
    "day_of_week": 3,
    "previous_demand": 23.0,
    "previous_sold": 22.0
}
try:
    response = requests.post(url, json=payload2)
    if response.status_code == 200:
        data = response.json()
        print("Response received!")
        print("Log output received from API:")
        print(data.get('formatted_log'))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Connection failed: {e}")
