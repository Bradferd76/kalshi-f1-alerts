import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"

SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]

# Load previously seen events
with open(SEEN_FILE, "r") as f:
    seen = set(json.load(f))

updated_seen = set(seen)

for series in SERIES:

    url = (
        f"https://api.elections.kalshi.com/v1/events/"
        f"?series_tickers={series}"
        f"&page_size=100"
    )

    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        print(f"Failed to load {series}")
        continue

    data = r.json()

    events = data.get("events", [])

    print(f"{series}: {len(events)} events")

    for event in events:

        ticker = event.get("ticker", "")
        title = event.get("title", "")
        subtitle = event.get("sub_title", "")

        if ticker not in seen:

            print(f"NEW EVENT: {ticker}")

            kalshi_url = (
                f"https://kalshi.com/markets/"
                f"{ticker.lower()}"
            )

            message = (
                f"🏎️ NEW F1 MARKET\n\n"
                f"Title: {title}\n"
                f"Ticker: {ticker}\n"
                f"Series: {series}\n\n"
                f"{kalshi_url}"
            )

            response = requests.post(
                WEBHOOK,
                json={"content": message}
            )

            print(
                f"Discord status: "
                f"{response.status_code}"
            )

            updated_seen.add(ticker)

with open(SEEN_FILE, "w") as f:
    json.dump(
        sorted(list(updated_seen)),
        f,
        indent=2
    )
