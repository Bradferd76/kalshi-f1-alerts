import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"
ALERT_FILE = "price_alerts.json"
STATE_FILE = "price_alert_state.json"

# Kalshi's current public API
BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


# ---------------------------------------------------------
# BASIC FILE FUNCTIONS
# ---------------------------------------------------------

def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------
# DISCORD
# ---------------------------------------------------------

def send_discord(message):
    response = requests.post(
        WEBHOOK,
        json={"content": message},
        timeout=20
    )

    print(f"Discord status: {response.status_code}")


# ---------------------------------------------------------
# PRICE FUNCTIONS
# ---------------------------------------------------------

def american_to_probability(american_odds):
    """
    Converts American odds into implied probability.
    """

    odds = float(american_odds)

    if odds < 0:
        return (-odds) / ((-odds) + 100)

    return 100 / (odds + 100)


def target_price_cents(american_odds):
    """
    Converts American odds into the price in cents
    that we want to buy at.

    Example:
        -125 -> approximately 55.6 cents
    """

    probability = american_to_probability(american_odds)

    return probability * 100


# ---------------------------------------------------------
# MARKET TYPE MATCHING
# ---------------------------------------------------------

def normalize_market_type(market_type):
    value = market_type.lower().strip()

    aliases = {
        "podium": "podium",
        "top 3": "podium",
        "top3": "podium",
        "finish top 3": "podium",
        "finishes top 3": "podium",

        "top 5": "top 5",
        "top5": "top 5",
        "finish top 5": "top 5",
        "finishes top 5": "top 5",

        "top 10": "top 10",
        "top10": "top 10",
        "finish top 10": "top 10",
        "finishes top 10": "top 10",

        "winner": "winner",
        "win": "winner",
        "race winner": "winner",
        "wins": "winner",

        "pole": "pole",
        "pole position": "pole",
        "qualifying": "pole",
    }

    return aliases.get(value, value)


def market_matches_type(title, market_type):
    """
    Determines whether a Kalshi market title matches
    the type requested by the user.
    """

    title = title.lower()
    market_type = normalize_market_type(market_type)

    if market_type == "podium":
        return (
            "podium" in title
            or "top 3" in title
            or "top three" in title
        )

    if market_type == "top 5":
        return (
            "top 5" in title
            or "top five" in title
        )

    if market_type == "top 10":
        return (
            "top 10" in title
            or "top ten" in title
        )

    if market_type == "winner":
        return (
            "winner" in title
            or "win the" in title
        )

    if market_type == "pole":
        return (
            "pole" in title
            or "pole position" in title
        )

    return market_type in title


# ---------------------------------------------------------
# DRIVER MATCHING
# ---------------------------------------------------------

def driver_matches(title, driver):
    """
    Match using the driver's last name.

    Example:
        "Leclerc"
        matches
        "Will Charles Leclerc finish on the podium?"
    """

    title = title.lower()
    last_name = driver.strip().lower()

    return last_name in title


# ---------------------------------------------------------
# GET ALL OPEN MARKETS
# ---------------------------------------------------------

def get_open_markets():
    """
    Retrieve open markets from Kalshi.

    We use pagination because Kalshi can return more than
    1,000 markets.
    """

    markets = []
    cursor = None

    while True:

        params = {
            "status": "open",
            "limit": 1000
        }

        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            f"{BASE_URL}/markets",
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"Failed to load markets: "
                f"{response.status_code}"
            )
            break

        data = response.json()

        batch = data.get("markets", [])

        markets.extend(batch)

        print(
            f"Loaded {len(batch)} markets "
            f"(total: {len(markets)})"
        )

        cursor = data.get("cursor")

        if not cursor or not batch:
            break

    return markets


# ---------------------------------------------------------
# FIND MARKET
# ---------------------------------------------------------

def find_market(markets, alert):
    """
    Search Kalshi's open markets for a market matching:

        market type
        driver last name

    We also require that the market appears to be
    Formula 1 related.
    """

    market_type = normalize_market_type(
        alert["market_type"]
    )

    driver = alert["driver"]

    print(
        f"Searching for: "
        f"{driver} {market_type}"
    )

    candidates = []

    for market in markets:

        title = market.get("title", "")
        subtitle = market.get("subtitle", "")
        event_ticker = market.get("event_ticker", "")
        ticker = market.get("ticker", "")

        searchable_text = (
            f"{title} "
            f"{subtitle} "
            f"{event_ticker} "
            f"{ticker}"
        ).lower()

        # Make sure this is an F1 market.
        f1_market = (
            "formula 1" in searchable_text
            or "f1" in searchable_text
            or ticker.upper().startswith("KXF1")
            or event_ticker.upper().startswith("KXF1")
        )

        if not f1_market:
            continue

        if not driver_matches(title, driver):
            continue

        if not market_matches_type(title, market_type):
            continue

        candidates.append(market)

    if not candidates:
        return None

    # Prefer markets whose title contains the exact
    # requested market type.
    candidates.sort(
        key=lambda m: len(m.get("title", ""))
    )

    return candidates[0]


# ---------------------------------------------------------
# PRICE
# ---------------------------------------------------------

def get_side_price(market, side):
    """
    Return the current ask price for the side we want
    to buy, in cents.

    Kalshi's API now provides both YES and NO ask prices.
    """

    side = side.upper()

    if side == "YES":
        value = market.get("yes_ask_dollars")

    elif side == "NO":
        value = market.get("no_ask_dollars")

    else:
        return None

    if value is None:
        return None

    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------
# PRICE ALERT
# ---------------------------------------------------------

def check_price_alert(markets, alert, alert_number, state):

    driver = alert["driver"]
    market_type = alert["market_type"]
    side = alert["side"].upper()
    american_odds = alert["american_odds"]

    print(
        f"Checking alert #{alert_number}: "
        f"{driver} {market_type} {side} {american_odds}"
    )

    market = find_market(
        markets,
        alert
    )

    if not market:

        print("  Market not found")

        return

    ticker = market.get("ticker", "")
    title = market.get("title", "")

    print(f"  Found market: {title}")
    print(f"  Ticker: {ticker}")

    current_price = get_side_price(
        market,
        side
    )

    if current_price is None:

        print("  Price unavailable")

        return

    target_price = target_price_cents(
        american_odds
    )

    print(
        f"  Current {side} ask: "
        f"{current_price:.1f}¢"
    )

    print(
        f"  Target price: "
        f"{target_price:.1f}¢"
    )

    # We want to be able to BUY at or below
    # our target price.
    if current_price <= target_price:

        # Create a unique key for this alert.
        alert_key = (
            f"{driver}|"
            f"{market_type}|"
            f"{side}|"
            f"{american_odds}|"
            f"{ticker}"
        )

        # Don't repeatedly alert every 5 minutes.
        if state.get(alert_key):

            print(
                "  Threshold reached previously - "
                "no repeat alert"
            )

            return

        message = (
            f"🚨 F1 PRICE ALERT 🚨\n\n"
            f"Driver: {driver}\n"
            f"Market: {title}\n"
            f"Side: {side}\n"
            f"Current price: {current_price:.1f}¢\n"
            f"Target: {american_odds:+g} "
            f"({target_price:.1f}¢)\n\n"
            f"Ticker: {ticker}"
        )

        send_discord(message)

        state[alert_key] = True

        print("  🚨 ALERT SENT!")

    else:

        print(
            "  Threshold not reached"
        )


# ---------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------

print("Loading files...")

seen = load_json(
    SEEN_FILE,
    []
)

price_alerts = load_json(
    ALERT_FILE,
    []
)

price_alert_state = load_json(
    STATE_FILE,
    {}
)

print(
    f"Loaded {len(price_alerts)} price alerts"
)

print(
    f"Loaded {len(seen)} previously seen markets"
)


# ---------------------------------------------------------
# NEW MARKET ALERTS
# ---------------------------------------------------------

# Keep your existing F1 series monitoring for
# new-market notifications.

SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]

updated_seen = set(seen)

for series in SERIES:

    url = (
        f"https://api.elections.kalshi.com/v1/events/"
        f"?series_tickers={series}"
        f"&page_size=100"
    )

    response = requests.get(
        url,
        timeout=20
    )

    if response.status_code != 200:

        print(
            f"Failed to load {series}"
        )

        continue

    data = response.json()

    events = data.get(
        "events",
        []
    )

    print(
        f"{series}: "
        f"{len(events)} events"
    )

    for event in events:

        ticker = event.get(
            "ticker",
            ""
        )

        title = event.get(
            "title",
            ""
        )

        if ticker not in seen:

            print(
                f"NEW EVENT: {ticker}"
            )

            message = (
                f"🏎️ NEW F1 MARKET\n\n"
                f"Title: {title}\n"
                f"Ticker: {ticker}\n"
                f"Series: {series}"
            )

            send_discord(message)

            updated_seen.add(
                ticker
            )


# ---------------------------------------------------------
# PRICE ALERTS
# ---------------------------------------------------------

print(
    "Loading open Kalshi markets..."
)

all_markets = get_open_markets()

print(
    f"Total open markets loaded: "
    f"{len(all_markets)}"
)

print(
    "Checking price alerts..."
)

for index, alert in enumerate(
    price_alerts,
    start=1
):

    check_price_alert(
        all_markets,
        alert,
        index,
        price_alert_state
    )


# ---------------------------------------------------------
# SAVE STATE
# ---------------------------------------------------------

save_json(
    SEEN_FILE,
    sorted(list(updated_seen))
)

save_json(
    STATE_FILE,
    price_alert_state
)

print("Finished.")
