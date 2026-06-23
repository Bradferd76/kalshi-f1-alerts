import requests

urls = [
    "https://api.elections.kalshi.com/v1/cached/markets_by_ticker/KXF1RACE-AUTGP26-ANT",
    "https://api.elections.kalshi.com/v1/cached/markets_by_ticker/KXF1POLE-AUTGP26-ANT",
]

for url in urls:

    print("\n====================")
    print(url)
    print("====================")

    r = requests.get(url, timeout=20)

    print("Status:", r.status_code)

    data = r.json()

    market = data.get("market", {})

    print("\nKeys in market:")

    for key in sorted(market.keys()):
        print(key)
