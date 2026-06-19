import requests

# Replace with your Discord webhook URL
WEBHOOK = "PASTE_YOUR_DISCORD_WEBHOOK_HERE"

# Get Kalshi events
r = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events",
    timeout=20
)

print("Status:", r.status_code)

data = r.json()

matches = []

# Find only F1 events
for event in data.get("events", []):

    ticker = event.get("event_ticker", "")

    if ticker.startswith("KXF1"):
        matches.append(event)

print("F1 MATCHES FOUND:", len(matches))

# Send Discord messages
for event in matches:

    title = event.get("title", "")
    subtitle = event.get("sub_title", "")
    ticker = event.get("event_ticker", "")

    print(f"{title} | {ticker}")

    message = (
        f"🏎️ F1 Market Found\n"
        f"Title: {title}\n"
        f"Subtitle: {subtitle}\n"
        f"Ticker: {ticker}"
    )

    response = requests.post(
        WEBHOOK,
        json={"content": message}
    )

    print(
        f"Discord status for {ticker}: "
        f"{response.status_code}"
    )
