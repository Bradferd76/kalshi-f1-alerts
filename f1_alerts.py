import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"
ALERT_FILE = "price_alerts.json"
STATE_FILE = "price_alert_state.json"

SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]


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

    if response.status_code >= 300:
        print(response.text)


def american_to_probability(american_odds):
    """
    Convert American odds to implied probability.
    """
    odds = float(american_odds)

    if odds < 0:
        return (-odds) / ((-odds) + 100)

    return 100 / (odds + 100)


def normalize_market_type(market_type):
    """
    Convert different ways of typing a market type
    into a standard format.
    """

    value = market_type.strip().lower()

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
    Check whether a market title matches the requested
    market type.
    """

    title = title.lower()
    market_type = normalize_market_type(market_type)

    if market_type == "podium":
        return (
            "podium" in title
            or "top 3" in title
            or "top3" in title
        )

    if market_type == "top 5":
        return (
            "top 5" in title
            or "top5" in title
        )

    if market_type == "top 10":
        return (
            "top 10" in title
            or "top10" in title
        )

    if market_type == "winner":
        return "winner" in title

    if market_type == "pole":
        return (
            "pole" in title
            or "pole position" in title
        )

    return False


def driver_matches(market_title, driver):
    """
    Match using the driver's last name.

    Example:
    "Leclerc" will match Charles Leclerc.
    """

    title = market_title.lower()
    last_name = driver.strip().lower()

    return last_name in title


def find_market(alert):
    """
    Search the F1 markets for the requested driver
    and market type.
    """

    driver = alert["driver"]
    market_type = alert["market_type"]

    for series in SERIES:

        url = (
            "https://api.elections.kalshi.com/v1/events/"
            f"?series_tickers={series}"
            "&page_size=100"
        )

        try:
            response = requests.get(
                url,
                timeout=20
            )
        except Exception as e:
            print(f"Error loading {series}: {e}")
            continue

        if response.status_code != 200:
            print(
                f"Failed to load {series}: "
                f"{response.status_code}"
            )
            continue

        data = response.json()

        events = data.get("events", [])

        for event in events:

            markets = event.get("markets", [])

            for market in markets:

                ticker = market.get(
                    "ticker_name",
                    market.get("ticker", "")
                )

                title = market.get(
                    "title",
                    ""
                )

                if not ticker:
                    continue

                if not title:
                    continue

                if not driver_matches(
                    title,
                    driver
                ):
                    continue

                if not market_matches_type(
                    title,
                    market_type
                ):
                    continue

                return market

    return None


def get_market(ticker):
    """
    Get current pricing for a specific market.
    """

    url = (
        "https://api.elections.kalshi.com/"
        "v1/cached/markets_by_ticker/"
        f"{ticker}"
    )

    try:
        response = requests.get(
            url,
            timeout=20
        )
    except Exception as e:
        print(f"Error loading market {ticker}: {e}")
        return None

    if response.status_code != 200:
        print(
            f"Failed to load market {ticker}: "
            f"{response.status_code}"
        )
        return None

    return response.json()


def get_side_price(market, side):
    """
    Return the current ASK price in cents
    for the side we want to buy.

    YES ask = yes_ask

    NO ask = 100 - yes_bid
    """

    side = side.upper()

    yes_bid = market.get("yes_bid")
    yes_ask = market.get("yes_ask")

    if side == "YES":

        if yes_ask is None:
            return None

        return float(yes_ask)

    if side == "NO":

        if yes_bid is None:
            return None

        return 100 - float(yes_bid)

    return None


def check_price_alert(alert, alert_index, state):
    """
    Check one price alert.
    """

    print(
        f"Checking alert #{alert_index + 1}: "
        f"{alert['driver']} "
        f"{alert['market_type']} "
        f"{alert['side']} "
        f"{alert['american_odds']}"
    )

    market = find_market(alert)

    if market is None:
        print("  Market not found")
        return

    ticker = market.get(
        "ticker_name",
        market.get("ticker", "")
    )

    title = market.get(
        "title",
        "Unknown market"
    )

    print(f"  Found: {title}")
    print(f"  Ticker: {ticker}")

    current_market = get_market(ticker)

    if current_market is None:
        return

    # Sometimes the API wraps the market in another object
    if "market" in current_market:
        current_market = current_market["market"]

    current_price = get_side_price(
        current_market,
        alert["side"]
    )

    if current_price is None:
        print("  Current price unavailable")
        return

    target_probability = american_to_probability(
        alert["american_odds"]
    )

    target_price = target_probability * 100

    print(
        f"  Current {alert['side']} ask: "
        f"{current_price:.1f}¢"
    )

    print(
        f"  Target: "
        f"{target_price:.1f}¢"
    )

    alert_key = str(alert_index)

    if state.get(alert_key):
        print("  Alert already sent")
        return

    # Alert when the current executable price
    # is at or below the target.
    if current_price <= target_price:

        message = (
            f"🚨 F1 PRICE ALERT 🚨\n\n"
            f"Driver: {alert['driver']}\n"
            f"Market: {alert['market_type']}\n"
            f"Side: {alert['side']}\n"
            f"Current price: {current_price:.1f}¢\n"
            f"Target odds: {alert['american_odds']:+}\n"
            f"Market: {title}\n"
            f"Ticker: {ticker}"
        )

        send_discord(message)

        state[alert_key] = True

        print("  🚨 ALERT SENT")

    else:
        print("  No alert")


# --------------------------------------------------
# Load existing state
# --------------------------------------------------

seen = set(
    load_json(
        SEEN_FILE,
        []
    )
)

updated_seen = set(seen)

price_alerts = load_json(
    ALERT_FILE,
    []
)

price_alert_state = load_json(
    STATE_FILE,
    {}
)


# --------------------------------------------------
# Check for NEW F1 markets
# --------------------------------------------------

for series in SERIES:

    url = (
        "https://api.elections.kalshi.com/v1/events/"
        f"?series_tickers={series}"
        "&page_size=100"
    )

    try:
        response = requests.get(
            url,
            timeout=20
        )
    except Exception as e:
        print(f"Error loading {series}: {e}")
        continue

    if response.status_code != 200:
        print(
            f"Failed to load {series}: "
            f"{response.status_code}"
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

            updated_seen.add(ticker)


# --------------------------------------------------
# Check PRICE alerts
# --------------------------------------------------

print("\nChecking price alerts...")

for index, alert in enumerate(price_alerts):

    try:
        check_price_alert(
            alert,
            index,
            price_alert_state
        )

    except Exception as e:

        print(
            f"Error checking alert "
            f"#{index + 1}: {e}"
        )


# --------------------------------------------------
# Save state
# --------------------------------------------------

save_json(
    SEEN_FILE,
    sorted(list(updated_seen))
)

save_json(
    STATE_FILE,
    price_alert_state
)

print("\nFinished.")
