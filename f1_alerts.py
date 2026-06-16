import requests

WEBHOOK = "https://discord.com/channels/1516493939220152420/1516494032019390515"

response = requests.get(
    "https://api.elections.kalshi.com/trade-api/v2/events"
)

if response.status_code == 200:
    requests.post(
        WEBHOOK,
        json={
            "content": "Kalshi checker is running."
        }
    )
