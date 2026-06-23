import requests

urls = [
    "https://api.elections.kalshi.com/v1/cached/markets_by_ticker/KXF1RACE-AUTGP26-ANT",
]

for url in urls:

    print("\n====================")
    print(url)
    print("====================")

    r = requests.get(url, timeout=20)

    print("Status:", r.status_code)

    try:
        data = r.json()

        if isinstance(data, dict):
            print("Keys:")
            print(list(data.keys()))

            print("\nFirst 3000 chars:")
            print(str(data)[:3000])

    except Exception as e:
        print("JSON error:", e)
        print(r.text[:3000])
