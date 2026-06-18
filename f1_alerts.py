import requests

WEBHOOK = "https://discord.com/api/webhooks/1516494102730899597/ced8oEr4YvTqjMt_PfnEh2_S9zCyR7MRRLevIP1tPNov4BqdkBwam2ovwsltHaEyfV_y"

r = requests.post(
    WEBHOOK,
    json={"content": "Hello from GitHub Actions"}
)

print("Status:", r.status_code)
print("Response:", r.text)
