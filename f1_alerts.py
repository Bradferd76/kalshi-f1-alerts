import requests
import json
import os

WEBHOOK = "https://discord.com/api/webhooks/1517270620096692384/DZYAAeZuwQgKzh0IEwyX9ZNjmkwgxIoPFtliQi6mUPa-wmyD9iPpWkoMaxG70MSsJUpA"

SEEN_FILE = "seen_markets.json"

# Load previously seen markets
try:
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
except:
    seen = set()

url = "https://api.elections.kalshi.com/trade-api/v2/events"

try:
    r = requests.get(url, timeout=20)

    print("Kalshi status:", r.status_code)

    data = r.json()

    new_seen = set(seen)

    text = json.dumps(data).lower()

    keywords = [
        "formula 1",
        "f1",
        "grand prix",
        "verstappen",
        "norris",
        "piastri",
        "leclerc",
        "hamilton"
    ]

    if any(word in text for word in keywords):

        marker = str(hash(text))

        if marker not in seen:

            requests.post(
                WEBHOOK,
                json={
                    "content":
                    "🏎️ Possible new F1 market detected on Kalshi."
                }
            )

            new_seen.add(marker)

    with open(SEEN_FILE, "w") as f:
        json.dump(list(new_seen), f)

except Exception as e:
    print("ERROR:", e)
