import json
import os
import requests

WEBHOOK = os.environ["https://discord.com/api/webhooks/1518981667128344646/82IgKJuNzpLzIXZQXCFNo5WlpR94F5ZcSmKaqqgd1EUy0gxuiAa1rfFSBBO1UmNnfmG9"]

SEEN_FILE = "seen_tickers.json"

# Load previously seen tickers
with open(SEEN_FILE, "r") as f:
    seen = set(json.load(f))

# Get Kalshi events
r = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events",
    timeout=20
)

print("Status:", r.status_code)

data = r.json()

print(f"Total events returned: {len(data.get('events', []))}")
print(f"Seen tickers: {len(seen)}")
print("Cursor:", data.get("cursor"))

print("\n=== F1 TICKERS FOUND IN RESPONSE ===")

f1_count = 0

for event in data.get("events", []):

    ticker = event.get("event_ticker", "")
    title = event.get("title", "")

    if "F1" in ticker.upper():
        f1_count += 1
        print(f"{ticker} | {title}")

print(f"\nTotal F1 tickers found: {f1_count}")
