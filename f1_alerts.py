import requests

urls = [
    "https://api.elections.kalshi.com/trade-api/v2/events",
    "https://api.elections.kalshi.com/trade-api/v2/markets"
]

for url in urls:

    print("\n====================")
    print(url)
    print("====================")

    try:
        r = requests.get(url, timeout=20)

        print("Status:", r.status_code)

        text = r.text.upper()

        count = text.count("KXF1")

        print("Occurrences of KXF1:", count)

        if count > 0:
            idx = text.find("KXF1")
            print(r.text[max(0, idx-200):idx+1000])

    except Exception as e:
        print("ERROR:", e)
