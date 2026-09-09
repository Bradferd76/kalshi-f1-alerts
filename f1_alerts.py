```python
import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"
PRICE_ALERTS_FILE = "price_alerts.json"
PRICE_STATE_FILE = "price_alert_state.json"

# ---------------------------------------------------------
# F1 SERIES USED FOR NEW MARKET ALERTS
# ---------------------------------------------------------

F1_SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]

# ---------------------------------------------------------
# SIMPLE NAMES -> KALSHI SERIES
# ---------------------------------------------------------

MARKET_SERIES = {
    "podium": "KXF1RACEPODIUM",
    "top 10": "KXF1RACETOP10",
    "top10": "KXF1RACETOP10",
    "top 5": "KXF1RACETOP5",
    "top5": "KXF1RACETOP5",
    "winner": "KXF1RACE",
    "pole": "KXF1POLE",
}

# ---------------------------------------------------------
# DRIVER LAST NAME -> KALSHI TICKER CODE
# ---------------------------------------------------------

DRIVER_CODES = {
    "verstappen": "VER",
    "norris": "NOR",
    "piastri": "PIA",
    "leclerc": "LEC",
    "hamilton": "HAM",
    "russell": "RUS",
    "alonso": "ALO",
    "stroll": "STR",
    "gasly": "GAS",
    "colapinto": "COL",
    "ocon": "OCO",
    "bearman": "BEA",
    "tsunoda": "TSU",
    "hadjar": "HAD",
    "lawson": "LAW",
    "bortoleto": "BOR",
    "hulkenberg": "HUL",
    "sainz": "SAI",
    "albon": "ALB",
    "antonelli": "ANT",
}

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def send_discord(message):
    response = requests.post(
        WEBHOOK,
        json={"content": message},
        timeout=20
    )

    print(f"Discord status: {response.status_code}")

    if response.status_code >= 400:
        print(response.text)


# ---------------------------------------------------------
# NEW F1 MARKET ALERTS
# ---------------------------------------------------------

seen = set(load_json(SEEN_FILE, []))
updated_seen = set(seen)

for series in F1_SERIES:

    url = (
        f"https://api.elections.kalshi.com/v1/events/"
        f"?series_tickers={series}"
        f"&page_size=100"
    )

    try:
        r = requests.get(url, timeout=20)
    except Exception as e:
        print(f"Error loading {series}: {e}")
        continue

    if r.status_code != 200:
        print(
            f"Failed to load {series}: "
            f"{r.status_code}"
        )
        continue

    data = r.json()
    events = data.get("events", [])

    print(f"{series}: {len(events)} events")

    for event in events:

        ticker = event.get("ticker", "")
        title = event.get("title", "")

        if ticker not in seen:

            print(f"NEW EVENT: {ticker}")

            message = (
                f"🏎️ **NEW F1 MARKET**\n\n"
                f"**Title:** {title}\n"
                f"**Ticker:** {ticker}\n"
                f"**Series:** {series}"
            )

            send_discord(message)

            updated_seen.add(ticker)


save_json(
    SEEN_FILE,
    sorted(list(updated_seen))
)


# ---------------------------------------------------------
# PRICE ALERTS
# ---------------------------------------------------------

print("\nChecking price alerts...")

price_alerts = load_json(
    PRICE_ALERTS_FILE,
    []
)

price_state = load_json(
    PRICE_STATE_FILE,
    {}
)


# ---------------------------------------------------------
# GET OPEN MARKETS FOR A SPECIFIC SERIES
# ---------------------------------------------------------

def get_markets_for_series(series_ticker):

    url = (
        f"{BASE_URL}/markets"
        f"?series_ticker={series_ticker}"
        f"&status=open"
        f"&limit=1000"
    )

    try:
        r = requests.get(
            url,
            timeout=20
        )
    except Exception as e:

        print(
            f"Error loading {series_ticker}: {e}"
        )

        return []

    if r.status_code != 200:

        print(
            f"Failed to load {series_ticker}: "
            f"{r.status_code}"
        )

        return []

    data = r.json()

    return data.get("markets", [])


# ---------------------------------------------------------
# PRICE ALERT CHECKING
# ---------------------------------------------------------

for alert_number, alert in enumerate(
    price_alerts,
    start=1
):

    market_type = (
        alert.get("market_type", "")
        .strip()
        .lower()
    )

    driver = (
        alert.get("driver", "")
        .strip()
        .lower()
    )

    side = (
        alert.get("side", "NO")
        .strip()
        .upper()
    )

    target_cents = float(
        alert.get("price_cents", 0)
    )

    print(
        f"\nChecking alert #{alert_number}: "
        f"{driver.title()} "
        f"{market_type} "
        f"{side} at "
        f"{target_cents:.0f}¢"
    )


    # -----------------------------------------------------
    # Validate market type
    # -----------------------------------------------------

    if market_type not in MARKET_SERIES:

        print(
            f"  Unknown market type: "
            f"{market_type}"
        )

        continue


    # -----------------------------------------------------
    # Validate driver
    # -----------------------------------------------------

    if driver not in DRIVER_CODES:

        print(
            f"  Unknown driver: "
            f"{driver}"
        )

        continue


    series_ticker = MARKET_SERIES[
        market_type
    ]

    driver_code = DRIVER_CODES[
        driver
    ]


    print(
        f"  Series: {series_ticker}"
    )

    print(
        f"  Driver code: {driver_code}"
    )


    # -----------------------------------------------------
    # Get only the relevant series
    # -----------------------------------------------------

    markets = get_markets_for_series(
        series_ticker
    )

    print(
        f"  Open markets in series: "
        f"{len(markets)}"
    )


    # -----------------------------------------------------
    # Find the driver's market
    # -----------------------------------------------------

    matching_markets = []

    for market in markets:

        ticker = str(
            market.get("ticker", "")
        )

        # The driver code should be at the end
        # of the Kalshi ticker.
        if ticker.endswith(
            f"-{driver_code}"
        ):

            matching_markets.append(
                market
            )


    if not matching_markets:

        print(
            f"  No {driver.title()} "
            f"{market_type} market found."
        )

        continue


    print(
        f"  Found "
        f"{len(matching_markets)} "
        f"matching market(s)."
    )


    # -----------------------------------------------------
    # Check each matching market
    # -----------------------------------------------------

    for market in matching_markets:

        ticker = market.get(
            "ticker",
            "UNKNOWN"
        )

        title = market.get(
            "title",
            "Unknown market"
        )


        # -------------------------------------------------
        # Get the price for the side we're buying
        # -------------------------------------------------

        if side == "NO":

            ask = market.get(
                "no_ask_dollars"
            )

        elif side == "YES":

            ask = market.get(
                "yes_ask_dollars"
            )

        else:

            print(
                f"  Invalid side: {side}"
            )

            continue


        if ask is None:

            print(
                f"  {ticker}: "
                f"No {side} ask available."
            )

            continue


        current_cents = (
            float(ask) * 100
        )


        print(
            f"  {ticker}: "
            f"{side} ask = "
            f"{current_cents:.1f}¢"
        )


        # -------------------------------------------------
        # Unique identifier for this alert
        # -------------------------------------------------

        state_key = (
            f"{alert_number}:"
            f"{ticker}"
        )


        # -------------------------------------------------
        # Don't alert repeatedly
        # -------------------------------------------------

        if price_state.get(state_key):

            print(
                "    Already alerted."
            )

            continue


        # -------------------------------------------------
        # PRICE TRIGGER
        #
        # Alert when the price reaches or goes BELOW
        # the user's threshold.
        # -------------------------------------------------

        if current_cents <= target_cents:

            message = (
                f"🚨 **F1 PRICE ALERT** 🚨\n\n"
                f"**Driver:** "
                f"{driver.title()}\n"
                f"**Market:** "
                f"{title}\n\n"
                f"**Side:** {side}\n"
                f"**Current price:** "
                f"{current_cents:.1f}¢\n"
                f"**Your threshold:** "
                f"{target_cents:.0f}¢\n\n"
                f"**Ticker:** "
                f"{ticker}"
            )

            send_discord(message)

            price_state[state_key] = True

            print(
                "    🚨 ALERT TRIGGERED!"
            )


# ---------------------------------------------------------
# SAVE ALERT STATE
# ---------------------------------------------------------

save_json(
    PRICE_STATE_FILE,
    price_state
)

print("\nFinished.")
```
