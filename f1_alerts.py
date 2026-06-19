import requests

WEBHOOK = "https://discord.com/api/webhooks/1517270620096692384/DZYAAeZuwQgKzh0IEwyX9ZNjmkwgxIoPFtliQi6mUPa-wmyD9iPpWkoMaxG70MSsJUpA"

r = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events",
    timeout=20
)

data = r.json()

keywords = [
    "formula",
    "f1",
    "grand prix",
    "verstappen",
    "norris",
    "piastri",
    "hamilton",
    "leclerc",
    "russell",
    "ferrari",
    "mclaren",
    "mercedes",
    "red bull"
]

matches = []

for event in data.get("events", []):

    title = event.get("title", "")
    subtitle = event.get("sub_title", "")

    text = (title + " " + subtitle).lower()

    if any(k in text for k in keywords):
        matches.append(event)

print("Matches found:", len(matches))

for event in matches:

    title = event.get("title", "")
    ticker = event.get("event_ticker", "")

    message = (
        f"🏎️ F1 Market Found\n"
        f"Title: {title}\n"
        f"Ticker: {ticker}"
    )

    requests.post(
        WEBHOOK,
        json={"content": message}
    )
