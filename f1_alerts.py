import requests
import json

url = "https://api.elections.kalshi.com/v1/events/?series_tickers=KXF1RACE&page_size=50"

r = requests.get(url, timeout=20)

print("Status:", r.status_code)

try:
    data = r.json()

    print("Top-level keys:")
    print(list(data.keys()))

    print("\nFirst 5000 chars:")
    print(json.dumps(data, indent=2)[:5000])

except Exception as e:
    print("ERROR:", e)
    print(r.text[:5000])
