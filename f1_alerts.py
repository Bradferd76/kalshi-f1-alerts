import json
import requests

WEBHOOK = "https://discord.com/api/webhooks/1517270620096692384/DZYAAeZuwQgKzh0IEwyX9ZNjmkwgxIoPFtliQi6mUPa-wmyD9iPpWkoMaxG70MSsJUpA"

SEEN_FILE = "seen_tickers.json"

# Load previously seen tickers
with open(SEEN_FILE, "r") as f:
    seen = set(json.load(f))

# Get Kalshi events
r = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events",
    timeout=20
)

data = r.json()

updated_seen = set(seen)

for event in data.get("events", []):

    ticker = event.get("event_ticker", "")

    if not ticker.startswith("KXF1"):
        continue

    title = event.get("title", "")
    subtitle = event.get("sub_title", "")

    if ticker not in seen:

        print("NEW F1 MARKET:", ticker)

        message = (
            f"🏎️ NEW F1 MARKET\n"
            f"Title: {title}\n"
            f"Subtitle: {subtitle}\n"
            f"Ticker: {ticker}"
        )

        response = requests.post(
            WEBHOOK,
            json={"content": message}
        )

        print("Discord status:", response.status_code)

        updated_seen.add(ticker)

# Save updated list
with open(SEEN_FILE, "w") as f:
    json.dump(sorted(list(updated_seen)), f, indent=2)
