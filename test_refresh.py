import requests
import sys

symbol = "ICICIBANK"
if len(sys.argv) > 1:
    symbol = sys.argv[1]

url = f"http://localhost:8000/api/master/{symbol}/refresh"
print(f"Calling {url}...")
try:
    response = requests.post(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}")
