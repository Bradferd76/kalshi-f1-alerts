import json
import os
import requests

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

SEEN_FILE = "seen_tickers.json"
PRICE_ALERTS_FILE = "price_alerts.json"
PRICE_STATE_FILE = "price_alert_state.json"

# These are the F1 series we already know how to monitor
F1_SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


# ---------------------------------------------------------
# Helper functions
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


def american_to_probability(odds):
    """
    Convert American odds to implied probability.
    """

    odds = float(odds)

    if odds < 0:
        return (-odds) / ((-odds) + 100)

    return 100 / (odds + 100)


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
        print(f"Failed to load {series}: {r.status_code}")
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


save_json(SEEN_FILE, sorted(list(updated_seen)))


# ---------------------------------------------------------
# PRICE ALERTS
# ---------------------------------------------------------

print("\nChecking price alerts...")


price_alerts = load_json(PRICE_ALERTS_FILE, [])
price_state = load_json(PRICE_STATE_FILE, {})


# ---------------------------------------------------------
# Find F1-related series
# ---------------------------------------------------------

def discover_f1_series():

    print("\nDiscovering F1 series...")

    series_list = []
    cursor = ""

    while True:

        url = f"{BASE_URL}/series?limit=1000"

        if cursor:
            url += f"&cursor={cursor}"

        try:
            r = requests.get(url, timeout=20)
        except Exception as e:
            print(f"Error loading series: {e}")
            break

        if r.status_code != 200:
            print(
                f"Failed to load series: "
                f"{r.status_code} {r.text[:200]}"
            )
            break

        data = r.json()

        for series in data.get("series", []):

            ticker = str(series.get("ticker", ""))
            title = str(series.get("title", ""))
            tags = str(series.get("tags", ""))

            search_text = (
                f"{ticker} {title} {tags}"
            ).lower()

            if (
                "f1" in search_text
                or "formula 1" in search_text
            ):
                series_list.append(series)

        cursor = data.get("cursor")

        if not cursor:
            break

    print(f"Found {len(series_list)} possible F1 series.")

    for series in series_list:
        print(
            f"  {series.get('ticker')} - "
            f"{series.get('title')}"
        )

    return series_list


# ---------------------------------------------------------
# Get markets for one series
# ---------------------------------------------------------

def get_markets_for_series(series_ticker):

    markets = []
    cursor = ""

    while True:

        url = (
            f"{BASE_URL}/markets"
            f"?series_ticker={series_ticker}"
            f"&status=open"
            f"&limit=1000"
        )

        if cursor:
            url += f"&cursor={cursor}"

        try:
            r = requests.get(url, timeout=20)
        except Exception as e:
            print(
                f"Error loading markets for "
                f"{series_ticker}: {e}"
            )
            break

        if r.status_code != 200:
            print(
                f"Failed to load markets for "
                f"{series_ticker}: "
                f"{r.status_code}"
            )
            break

        data = r.json()

        markets.extend(data.get("markets", []))

        cursor = data.get("cursor")

        if not cursor:
            break

    return markets


# ---------------------------------------------------------
# Match market to user's alert
# ---------------------------------------------------------

def market_matches_alert(market, alert):

    title = str(market.get("title", "")).lower()
    ticker = str(market.get("ticker", "")).lower()

    driver = alert.get("driver", "").strip().lower()
    market_type = alert.get("market_type", "").strip().lower()

    # Driver must appear in the market
    if driver not in title and driver not in ticker:
        return False

    # Market type matching
    if market_type == "podium":

        if not any(word in title for word in [
            "podium",
            "top 3",
            "top-three",
            "top three",
        ]):
            return False

    elif market_type in ["top 10", "top10"]:

        if not any(word in title for word in [
            "top 10",
            "top10",
            "top-ten",
            "top ten",
        ]):
            return False

    elif market_type == "winner":

        if not any(word in title for word in [
            "winner",
            "win the",
            "finish in first",
            "finish first",
        ]):
            return False

    elif market_type == "pole":

        if not any(word in title for word in [
            "pole",
            "pole position",
        ]):
            return False

    else:

        # For an unknown market type, simply search
        # for that text in the title.
        if market_type not in title:
            return False

    return True


# ---------------------------------------------------------
# Run price alerts
# ---------------------------------------------------------

f1_series = discover_f1_series()

all_markets = []

# Add the known F1 series too
known_tickers = {
    series.get("ticker")
    for series in f1_series
}

for series_ticker in F1_SERIES:
    known_tickers.add(series_ticker)


print("\nChecking F1 series for open markets...")


for series_ticker in known_tickers:

    markets = get_markets_for_series(series_ticker)

    print(
        f"{series_ticker}: "
        f"{len(markets)} open markets"
    )

    all_markets.extend(markets)


print(
    f"\nTotal F1 markets checked: "
    f"{len(all_markets)}"
)


# ---------------------------------------------------------
# Check each alert
# ---------------------------------------------------------

for alert_number, alert in enumerate(
    price_alerts,
    start=1
):

    market_type = alert.get(
        "market_type",
        ""
    )

    driver = alert.get(
        "driver",
        ""
    )

    side = alert.get(
        "side",
        "NO"
    ).upper()

    target_cents = float(
        alert.get("price_cents", 0)
    )

    american_odds = alert.get(
        "american_odds"
    )

    print(
        f"\nChecking alert #{alert_number}: "
        f"{driver} {market_type} "
        f"{side} at {target_cents}¢"
    )

    matching_markets = []

    for market in all_markets:

        if market_matches_alert(
            market,
            alert
        ):
            matching_markets.append(market)


    if not matching_markets:

        print("  Market not found.")
        continue


    print(
        f"  Found {len(matching_markets)} "
        f"matching market(s)."
    )


    for market in matching_markets:

        ticker = market.get(
            "ticker",
            "UNKNOWN"
        )

        title = market.get(
            "title",
            "Unknown market"
        )

        # Kalshi prices are returned as decimal dollars.
        if side == "NO":

            ask = market.get(
                "no_ask_dollars"
            )

        else:

            ask = market.get(
                "yes_ask_dollars"
            )


        if ask is None:

            print(
                f"  {ticker}: "
                f"No {side} ask available."
            )

            continue


        current_cents = float(ask) * 100


        print(
            f"  {ticker}: "
            f"{side} ask = "
            f"{current_cents:.1f}¢"
        )


        # Unique state key for this particular
        # alert + market.
        state_key = (
            f"{alert_number}:"
            f"{ticker}"
        )


        # Already alerted?
        if price_state.get(state_key):

            print(
                "    Already alerted."
            )

            continue


        # Trigger when price reaches or goes below
        # user's target.
        if current_cents <= target_cents:

            message = (
                f"🚨 **F1 PRICE ALERT** 🚨\n\n"
                f"**Driver:** {driver.title()}\n"
                f"**Market:** {title}\n\n"
                f"**Side:** {side}\n"
                f"**Current price:** "
                f"{current_cents:.1f}¢\n"
                f"**Your threshold:** "
                f"{target_cents:.0f}¢"
            )

            if american_odds is not None:

                message += (
                    f"\n**Target odds:** "
                    f"{american_odds:+}"
                )

            message += (
                f"\n\n**Ticker:** {ticker}"
            )

            send_discord(message)

            price_state[state_key] = True

            print(
                "    🚨 ALERT TRIGGERED!"
            )


# Save price alert state
save_json(
    PRICE_STATE_FILE,
    price_state
)


print("\nFinished.")
