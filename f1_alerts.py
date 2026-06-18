import requests
import json

r = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events",
    timeout=20
)

print("Status:", r.status_code)

try:
    data = r.json()

    print("Top-level keys:")
    print(list(data.keys())[:20])

    print(json.dumps(data, indent=2)[:5000])

except Exception as e:
    print("JSON ERROR:", e)
    print(r.text[:5000])
