import json
import os
from pathlib import Path

import requests


# ============================================================
# Configuration
# ============================================================

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

SEEN_TICKERS_FILE = Path("seen_tickers.json")
PRICE_ALERTS_FILE = Path("price_alerts.json")
PRICE_ALERT_STATE_FILE = Path("price_alert_state.json")


# These are the currently known F1 series.
# The Top 10 and Top 5 entries may need to be corrected after
# reviewing the diagnostic output from this script.
MARKET_SERIES = {
    "podium": "KXF1RACEPODIUM",
    "top 10": "KXF1RACETOP10",
    "top10": "KXF1RACETOP10",
    "top 5": "KXF1RACETOP5",
    "top5": "KXF1RACETOP5",
    "winner": "KXF1RACE",
    "pole": "KXF1POLE",
}


# Series used for new-market notifications.
NEW_MARKET_SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]


# Driver name to ticker code.
DRIVER_CODES = {
    "antonelli": "ANT",
    "norris": "NOR",
    "verstappen": "VER",
    "hamilton": "HAM",
    "leclerc": "LEC",
    "russell": "RUS",
    "piastri": "PIA",
    "alonso": "ALO",
    "stroll": "STR",
    "gasly": "GAS",
    "ocon": "OCO",
    "bearman": "BEA",
    "tsunoda": "TSU",
    "lawson": "LAW",
    "hadjar": "HAD",
    "sainz": "SAI",
    "albon": "ALB",
    "bortoleto": "BOR",
    "hulkenberg": "HUL",
    "colapinto": "COL",
    "perez": "PER",
    "bottas": "BOT",
    "magnussen": "MAG",
    "zhou": "ZHO",
}


# ============================================================
# File helpers
# ============================================================

def load_json_file(path, default):
    """Load JSON from a file, or return a default value."""
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse {path}. Using default value.")
        return default


def save_json_file(path, data):
    """Save JSON to a file."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def send_discord_message(message):
    """Send a message to Discord."""
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK is not configured. Message was not sent.")
        print(message)
        return

    try:
        response = requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=20,
        )

        if response.status_code not in (200, 204):
            print(
                "Discord returned an unexpected status: "
                f"{response.status_code}"
            )
            print(response.text[:500])
        else:
            print("Discord notification sent.")

    except requests.RequestException as error:
        print(f"Discord request failed: {error}")


# ============================================================
# Kalshi API helpers
# ============================================================

def get_events_for_series(series_ticker):
    """Return events for a Kalshi series."""
    url = "https://api.elections.kalshi.com/v1/events/"

    params = {
        "series_tickers": series_ticker,
        "page_size": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("events", [])

    except requests.RequestException as error:
        print(f"Error retrieving events for {series_ticker}: {error}")
        return []


def get_markets_for_series(series_ticker, open_only=True):
    """Return markets for a Kalshi series."""
    url = "https://external-api.kalshi.com/trade-api/v2/markets"

    params = {
        "series_ticker": series_ticker,
        "limit": 1000,
    }

    if open_only:
        params["status"] = "open"

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("markets", [])

    except requests.RequestException as error:
        print(f"Error retrieving markets for {series_ticker}: {error}")
        return []


# ============================================================
# New-market alerts
# ============================================================

def check_for_new_markets():
    """Send Discord alerts for newly discovered F1 events."""
    print("Checking for new F1 markets...")

    seen_tickers = load_json_file(SEEN_TICKERS_FILE, [])
    seen_tickers = set(seen_tickers)

    newly_seen_tickers = set()

    for series_ticker in NEW_MARKET_SERIES:
        events = get_events_for_series(series_ticker)

        print(f"{series_ticker}: {len(events)} events")

        for event in events:
            event_ticker = event.get("event_ticker")

            if not event_ticker:
                continue

            newly_seen_tickers.add(event_ticker)

            if event_ticker in seen_tickers:
                continue

            title = (
                event.get("title")
                or event.get("name")
                or event_ticker
            )

            message = (
                "🏎️ New F1 market found!\n"
                f"Series: {series_ticker}\n"
                f"Event: {title}\n"
                f"Ticker: {event_ticker}"
            )

            send_discord_message(message)

    updated_seen_tickers = seen_tickers.union(newly_seen_tickers)
    save_json_file(
        SEEN_TICKERS_FILE,
        sorted(updated_seen_tickers),
    )


# ============================================================
# Diagnostic tools
# ============================================================

def inspect_f1_series():
    """
    Print market information for the known F1 series.

    This helps determine whether the Top 10 and Top 5 series
    tickers are valid and whether they currently contain markets.
    """
    series_to_check = [
        "KXF1RACE",
        "KXF1RACEPODIUM",
        "KXF1RACETOP10",
        "KXF1RACETOP5",
        "KXF1POLE",
    ]

    print("\nInspecting known F1 series...")

    for series_ticker in series_to_check:
        print(f"\n{series_ticker}")

        markets = get_markets_for_series(
            series_ticker,
            open_only=False,
        )

        print(f"Markets returned: {len(markets)}")

        if not markets:
            print("  No markets returned.")
            continue

        for market in markets[:10]:
            print(
                "  "
                f"ticker={market.get('ticker')} | "
                f"series_ticker={market.get('series_ticker')} | "
                f"event_ticker={market.get('event_ticker')} | "
                f"title={market.get('title')} | "
                f"subtitle={market.get('subtitle')} | "
                f"status={market.get('status')}"
            )


def inspect_possible_f1_markets():
    """
    Search a larger set of markets for possible F1-related
    Top 10 and Top 5 markets.

    This is diagnostic only. It does not place trades.
    """
    url = "https://external-api.kalshi.com/trade-api/v2/markets"

    params = {
        "limit": 1000,
    }

    print("\nInspecting a larger set of Kalshi markets...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print(f"Error retrieving broad market list: {error}")
        return

    markets = data.get("markets", [])
    print(f"Total markets returned: {len(markets)}")

    matches_found = 0

    for market in markets:
        searchable_text = " ".join(
            str(market.get(field, ""))
            for field in [
                "ticker",
                "title",
                "subtitle",
                "event_ticker",
                "series_ticker",
            ]
        ).lower()

        relevant_terms = [
            "formula",
            "f1",
            "top 10",
            "top10",
            "top 5",
            "top5",
        ]

        if not any(term in searchable_text for term in relevant_terms):
            continue

        matches_found += 1

        print(
            "  "
            f"ticker={market.get('ticker')} | "
            f"series_ticker={market.get('series_ticker')} | "
            f"event_ticker={market.get('event_ticker')} | "
            f"title={market.get('title')} | "
            f"subtitle={market.get('subtitle')} | "
            f"status={market.get('status')}"
        )

    print(f"Possible F1-related markets found: {matches_found}")


# ============================================================
# Price-alert helpers
# ============================================================

def get_series_for_market_type(market_type):
    """Return the configured series ticker for a market type."""
    normalized_type = market_type.strip().lower()

    series_ticker = MARKET_SERIES.get(normalized_type)

    if not series_ticker:
        print(
            f"Warning: No series configured for market type "
            f"'{market_type}'."
        )

    return series_ticker


def get_driver_code(driver_name):
    """Return the Kalshi driver code."""
    normalized_driver = driver_name.strip().lower()
    return DRIVER_CODES.get(normalized_driver)


def market_matches_driver(market, driver_code):
    """
    Determine whether a market appears to belong to a driver.

    The expected ticker format generally ends with -DRIVER_CODE.
    """
    ticker = str(market.get("ticker", "")).upper()

    return (
        ticker.endswith(f"-{driver_code}")
        or f"-{driver_code}-" in ticker
    )


def get_yes_ask_cents(market):
    """Return the YES ask price in cents."""
    yes_ask_dollars = market.get("yes_ask_dollars")

    if yes_ask_dollars is None:
        return None

    try:
        return float(yes_ask_dollars) * 100
    except (TypeError, ValueError):
        return None


def get_no_ask_cents(market):
    """Return the NO ask price in cents."""
    no_ask_dollars = market.get("no_ask_dollars")

    if no_ask_dollars is None:
        return None

    try:
        return float(no_ask_dollars) * 100
    except (TypeError, ValueError):
        return None


def get_requested_ask_cents(market, side):
    """Return the requested YES or NO ask price in cents."""
    normalized_side = side.strip().upper()

    if normalized_side == "YES":
        return get_yes_ask_cents(market)

    if normalized_side == "NO":
        return get_no_ask_cents(market)

    print(f"Warning: Unsupported side '{side}'.")
    return None


def check_price_alerts():
    """
    Check configured price alerts.

    Current behavior:
    - YES alerts trigger when YES ask <= target price.
    - NO alerts trigger when NO ask <= target price.
    - Each market/alert combination triggers only once.
    """
    print("\nChecking price alerts...")

    alerts = load_json_file(PRICE_ALERTS_FILE, [])
    alert_state = load_json_file(PRICE_ALERT_STATE_FILE, {})

    if not isinstance(alerts, list):
        print("Warning: price_alerts.json must contain a JSON list.")
        return

    if not isinstance(alert_state, dict):
        alert_state = {}

    for alert_number, alert in enumerate(alerts, start=1):
        market_type = str(alert.get("market_type", ""))
        driver_name = str(alert.get("driver", ""))
        side = str(alert.get("side", "YES")).upper()

        try:
            target_cents = float(alert["price_cents"])
        except (KeyError, TypeError, ValueError):
            print(
                f"Skipping alert #{alert_number}: "
                "price_cents is invalid."
            )
            continue

        series_ticker = get_series_for_market_type(market_type)
        driver_code = get_driver_code(driver_name)

        print(
            f"\nChecking alert #{alert_number}: "
            f"{driver_name} {market_type} {side} "
            f"at {target_cents:g}¢"
        )

        if not series_ticker:
            print("  No series ticker configured.")
            continue

        if not driver_code:
            print(f"  No driver code found for {driver_name}.")
            continue

        print(f"  Series: {series_ticker}")
        print(f"  Driver code: {driver_code}")

        markets = get_markets_for_series(
            series_ticker,
            open_only=True,
        )

        print(f"  Open markets in series: {len(markets)}")

        matching_markets = [
            market
            for market in markets
            if market_matches_driver(market, driver_code)
        ]

        if not matching_markets:
            print(
                f"  No {driver_name} {market_type} market found."
            )
            continue

        print(
            f"  Found {len(matching_markets)} "
            "matching market(s)."
        )

        for market in matching_markets:
            ticker = market.get("ticker")

            if not ticker:
                continue

            current_cents = get_requested_ask_cents(market, side)

            if current_cents is None:
                print(
                    f"  {ticker}: No usable {side} ask price."
                )
                continue

            print(
                f"  {ticker}: {side} ask = "
                f"{current_cents:.1f}¢"
            )

            state_key = f"{alert_number}:{ticker}"

            if current_cents <= target_cents:
                if alert_state.get(state_key):
                    print(
                        "    Threshold already alerted for this "
                        "market."
                    )
                    continue

                title = (
                    market.get("title")
                    or market.get("subtitle")
                    or ticker
                )

                message = (
                    "🏎️ F1 price alert!\n"
                    f"Market: {title}\n"
                    f"Ticker: {ticker}\n"
                    f"Side: {side}\n"
                    f"Current ask: {current_cents:.1f}¢\n"
                    f"Target: {target_cents:g}¢"
                )

                send_discord_message(message)

                alert_state[state_key] = True

    save_json_file(PRICE_ALERT_STATE_FILE, alert_state)


# ============================================================
# Main program
# ============================================================

def main():
    check_for_new_markets()
    check_price_alerts()


if __name__ == "__main__":
    inspect_f1_series()
    inspect_possible_f1_markets()
    main()
