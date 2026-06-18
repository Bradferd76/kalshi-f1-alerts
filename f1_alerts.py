import requests

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
    "leclerc"
]

matches = []

for event in data.get("events", []):

    title = event.get("title", "")
    subtitle = event.get("sub_title", "")

    text = (title + " " + subtitle).lower()

    if any(k in text for k in keywords):
        matches.append(f"{title} | {subtitle}")

print("F1 MATCHES FOUND:", len(matches))

for m in matches:
    print(m)
