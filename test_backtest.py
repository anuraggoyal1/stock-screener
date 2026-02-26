import requests
import json

url = "http://localhost:8000/api/backtest/run"
params = {
    "symbol": "INFY",
    "up_candle_pct": 2.0,
    "years": 5 # Start with 5 years to test speed
}

print(f"Running backtest for {params['symbol']}...")
try:
    response = requests.get(url, params=params, timeout=60)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total Setups: {data['total_setups']}")
        print(f"Overall Success: {data['overall_success']}")
        print(f"Recent Period: {data['periods'][-1] if data['periods'] else 'None'}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
