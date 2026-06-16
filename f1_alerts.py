import requests

WEBHOOK = "https://discord.com/api/webhooks/1516494102730899597/ced8oEr4YvTqjMt_PfnEh2_S9zCyR7MRRLevIP1tPNov4BqdkBwam2ovwsltHaEyfV_y"

r = requests.post(
    WEBHOOK,
    json={
        "content": "GitHub Actions successfully sent this message."
    }
)

print("Status code:", r.status_code)
print(r.text)
