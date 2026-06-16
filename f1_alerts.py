import requests

WEBHOOK = "https://discord.com/api/webhooks/1516494102730899597/ced8oEr4YvTqjMt_PfnEh2_S9zCyR7MRRLevIP1tPNov4BqdkBwam2ovwsltHaEyfV_y"

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
