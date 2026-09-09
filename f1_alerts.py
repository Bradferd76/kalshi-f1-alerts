import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"
PRICE_ALERTS_FILE = "price_alerts.json"
PRICE_STATE_FILE = "price_alert_state.json"

# F1 series used for new-market alerts
F1_SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]

# Simple names you can use in price_alerts.json
MARKET_SERIES = {
    "podium": "KXF1RACEPODIUM",
    "top 10": "KXF1RACETOP10",
    "top10": "KXF1RACETOP10",
    "top 5": "KXF1RACETOP5",
    "top5": "KXF1RACETOP5",
    "winner": "KXF1RACE",
    "pole": "KXF1POLE",
}

# Driver last names -> Kalshi ticker codes
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
    try:
        response = requests.post(
            WEBHOOK,
            json={"content": message},
            timeout=20
        )

        print(f"Discord status: {response.status_code}")

        if response.status_code >= 400:
            print(response.text)

    except Exception as e:
        print(f"Discord error: {e}")


def get_markets_for_series(series_ticker):
    url = (
        f"{BASE_URL}/markets"
        f"?series_ticker={series_ticker}"
        f"&status=open"
        f"&limit=1000"
    )

    try:
        response = requests.get(url, timeout=20)

    except Exception as e:
        print(f"Error loading {series_ticker}: {e}")
        return []

    if response.status_code != 200:
        print(
            f"Failed to load {series_ticker}: "
            f"{response.status_code}"
        )
        return []

    try:
        data = response.json()
        return data.get("markets", [])

    except Exception as e:
        print(f"Error reading {series_ticker}: {e}")
        return []


# ============================================================
# NEW F1 MARKET ALERTS
# ============================================================

seen = set(load_json(SEEN_FILE, []))
updated_seen = set(seen)

print("Checking for new F1 markets...")

for series in F1_SERIES:

    url = (
        f"https://api.elections.kalshi.com/v1/events/"
        f"?series_tickers={series}"
        f"&page_size=100"
    )

    try:
        response = requests.get(url, timeout=20)

    except Exception as e:
        print(f"Error loading {series}: {e}")
        continue

    if response.status_code != 200:
        print(
            f"Failed to load {series}: "
            f"{response.status_code}"
        )
        continue

    try:
        data = response.json()

    except Exception as e:
        print(f"Error reading {series}: {e}")
        continue

    events = data.get("events", [])

    print(f"{series}: {len(events)} events")

    for event in events:

        ticker = event.get("ticker", "")
        title = event.get("title", "")

        if not ticker:
            continue

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


# ============================================================
# PRICE ALERTS
# ============================================================

print("\nChecking price alerts...")

price_alerts = load_json(
    PRICE_ALERTS_FILE,
    []
)

price_state = load_json(
    PRICE_STATE_FILE,
    {}
)


for alert_number, alert in enumerate(
    price_alerts,
    start=1
):

    market_type = str(
        alert.get("market_type", "")
    ).strip().lower()

    driver = str(
        alert.get("driver", "")
    ).strip().lower()

    side = str(
        alert.get("side", "NO")
    ).strip().upper()

    try:
        target_cents = float(
            alert.get("price_cents", 0)
        )

    except (TypeError, ValueError):
        print(
            f"\nAlert #{alert_number}: "
            f"Invalid price_cents"
        )
        continue


    print(
        f"\nChecking alert #{alert_number}: "
        f"{driver.title()} "
        f"{market_type} "
        f"{side} "
        f"at {target_cents:.0f}¢"
    )


    # Check market type
    if market_type not in MARKET_SERIES:

        print(
            f"  Unknown market type: "
            f"{market_type}"
        )

        continue


    # Check driver
    if driver not in DRIVER_CODES:

        print(
            f"  Unknown driver: "
            f"{driver}"
        )

        continue


    # Check side
    if side not in ["YES", "NO"]:

        print(
            f"  Invalid side: "
            f"{side}"
        )

        continue


    series_ticker = MARKET_SERIES[
        market_type
    ]

    driver_code = DRIVER_CODES[
        driver
    ]


    print(
        f"  Series: "
        f"{series_ticker}"
    )

    print(
        f"  Driver code: "
        f"{driver_code}"
    )


    # Get all currently open markets
    markets = get_markets_for_series(
        series_ticker
    )


    print(
        f"  Open markets in series: "
        f"{len(markets)}"
    )


    # Find markets whose ticker ends
    # with the driver's code.
    matching_markets = []

    for market in markets:

        ticker = str(
            market.get("ticker", "")
        )

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


    # Check each matching market
    for market in matching_markets:

        ticker = market.get(
            "ticker",
            "UNKNOWN"
        )

        title = market.get(
            "title",
            "F1 market"
        )


        # If we are buying NO,
        # we care about the NO ASK price.
        if side == "NO":

            ask = market.get(
                "no_ask_dollars"
            )

        else:

            # If we are buying YES,
            # we care about the YES ASK price.
            ask = market.get(
                "yes_ask_dollars"
            )


        if ask is None:

            print(
                f"  {ticker}: "
                f"No {side} ask available."
            )

            continue


        try:

            current_cents = (
                float(ask) * 100
            )

        except (TypeError, ValueError):

            print(
                f"  {ticker}: "
                f"Invalid price: {ask}"
            )

            continue


        print(
            f"  {ticker}: "
            f"{side} ask = "
            f"{current_cents:.1f}¢"
        )


        # Each alert/market gets its own state.
        state_key = (
            f"{alert_number}:{ticker}"
        )


        # Don't repeatedly alert for the
        # same market once the threshold
        # has been reached.
        if price_state.get(state_key):

            print(
                "    Already alerted."
            )

            continue


        # ====================================================
        # TRIGGER ALERT
        # ====================================================

        if current_cents <= target_cents:

            message = (
                f"🚨 **F1 PRICE ALERT** 🚨\n\n"
                f"**Driver:** "
                f"{driver.title()}\n"
                f"**Market:** "
                f"{title}\n\n"
                f"**Side:** "
                f"{side}\n"
                f"**Current price:** "
                f"{current_cents:.1f}¢\n"
                f"**Your threshold:** "
                f"{target_cents:.0f}¢\n\n"
                f"**Ticker:** "
                f"{ticker}"
            )


            send_discord(message)

            price_state[
                state_key
            ] = True


            print(
                "    🚨 ALERT TRIGGERED!"
            )


save_json(
    PRICE_STATE_FILE,
    price_state
)


print("\nFinished.")
