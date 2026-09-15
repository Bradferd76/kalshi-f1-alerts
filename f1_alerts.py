import json
import os
import re
from pathlib import Path

import requests


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

SEEN_TICKERS_FILE = Path("seen_tickers.json")
PRICE_ALERTS_FILE = Path("price_alerts.json")
PRICE_ALERT_STATE_FILE = Path("price_alert_state.json")


# These are the known F1 series used for new-market notifications.
NEW_MARKET_SERIES = [
    "KXF1RACE",
    "KXF1POLE",
    "KXF1TOPCONSTRUCTOR",
    "KXF1ACTION",
]


# Known driver ticker codes.
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
    "sainz": "SAI",
    "perez": "PER",
    "ocon": "OCO",
    "gasly": "GAS",
    "tsunoda": "TSU",
    "lawson": "LAW",
    "hadjar": "HAD",
    "bearman": "BEA",
    "bortoleto": "BOR",
    "colapinto": "COL",
    "lindblad": "LIN",
}


# Direct series mappings for market types that are known to work.
# Top 5 and Top 10 are intentionally not included here because
# Kalshi returned zero markets for the assumed series tickers.
KNOWN_SERIES = {
    "winner": "KXF1RACE",
    "pole": "KXF1POLE",
    "podium": "KXF1RACEPODIUM",
}


# Kalshi API endpoints.
EVENTS_URL = "https://api.elections.kalshi.com/v1/events/"
MARKETS_URL = "https://external-api.kalshi.com/trade-api/v2/markets"


# ------------------------------------------------------------
# General helpers
# ------------------------------------------------------------

def load_json_file(path, default):
    """Load JSON from a file, returning default if the file is missing."""
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"Could not read {path}: {error}")
        return default


def save_json_file(path, data):
    """Save JSON with readable formatting."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def send_discord(message):
    """Send a message to Discord if the webhook is configured."""
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK is not configured.")
        return

    try:
        response = requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=20,
        )
        response.raise_for_status()
        print("Discord alert sent.")
    except Exception as error:
        print(f"Discord notification failed: {error}")


def get_driver_code(driver_name):
    """Convert a driver name into its Kalshi ticker code."""
    normalized_name = driver_name.strip().lower()

    if normalized_name in DRIVER_CODES:
        return DRIVER_CODES[normalized_name]

    # Fallback: use the first three letters.
    return normalized_name[:3].upper()


def get_market_text(market):
    """Combine useful market fields into one searchable lowercase string."""
    fields = [
        market.get("ticker"),
        market.get("title"),
        market.get("subtitle"),
        market.get("event_ticker"),
        market.get("series_ticker"),
    ]

    return " ".join(str(value) for value in fields if value).lower()


def get_market_status(market):
    """Return the market status from whichever field is available."""
    return str(
        market.get("status")
        or market.get("market_status")
        or ""
    ).lower()


def is_open_market(market):
    """Determine whether a market appears to be open/active."""
    status = get_market_status(market)

    if not status:
        # Some API responses omit status. Treat them as potentially usable.
        return True

    return status in {"open", "active"}


# ------------------------------------------------------------
# Kalshi API helpers
# ------------------------------------------------------------

def fetch_events_for_series(series_ticker):
    """Fetch events for a known Kalshi series."""
    try:
        response = requests.get(
            EVENTS_URL,
            params={
                "series_tickers": series_ticker,
                "page_size": 100,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("events", [])
    except Exception as error:
        print(f"Error fetching events for {series_ticker}: {error}")
        return []


def fetch_markets_for_series(series_ticker):
    """Fetch open markets for a specific series ticker."""
    try:
        response = requests.get(
            MARKETS_URL,
            params={
                "series_ticker": series_ticker,
                "status": "open",
                "limit": 1000,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("markets", [])
    except Exception as error:
        print(f"Error fetching markets for {series_ticker}: {error}")
        return []


def fetch_broad_market_sample():
    """
    Fetch a broad market sample.

    This is not guaranteed to contain every Kalshi market, but it can
    help discover markets whose series ticker is not known in advance.
    """
    try:
        response = requests.get(
            MARKETS_URL,
            params={
                "status": "open",
                "limit": 1000,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("markets", [])
    except Exception as error:
        print(f"Error fetching broad market sample: {error}")
        return []


# ------------------------------------------------------------
# New-market alerts
# ------------------------------------------------------------

def check_for_new_f1_markets():
    """Send Discord alerts for newly discovered events in known F1 series."""
    print("Checking for new F1 markets...")

    seen_tickers = set(load_json_file(SEEN_TICKERS_FILE, []))
    updated_seen_tickers = set(seen_tickers)

    for series_ticker in NEW_MARKET_SERIES:
        events = fetch_events_for_series(series_ticker)

        print(f"{series_ticker}: {len(events)} events")

        for event in events:
            event_ticker = event.get("event_ticker") or event.get("ticker")

            if not event_ticker:
                continue

            if event_ticker in seen_tickers:
                continue

            event_title = (
                event.get("title")
                or event.get("name")
                or event_ticker
            )

            message = (
                "🏎️ New F1 Kalshi market found!\n"
                f"Series: {series_ticker}\n"
                f"Event: {event_title}\n"
                f"Ticker: {event_ticker}"
            )

            print(message)
            send_discord(message)

            updated_seen_tickers.add(event_ticker)

    if updated_seen_tickers != seen_tickers:
        save_json_file(
            SEEN_TICKERS_FILE,
            sorted(updated_seen_tickers),
        )


# ------------------------------------------------------------
# Market classification
# ------------------------------------------------------------

def market_matches_type(market, market_type):
    """
    Determine whether a market appears to be a Top 5, Top 10, podium,
    winner, or pole market.

    The check uses the ticker, title, subtitle, event ticker, and series
    ticker because Kalshi may not expose series_ticker in the market object.
    """
    text = get_market_text(market)

    normalized_type = market_type.strip().lower()

    if normalized_type == "top 10":
        patterns = [
            r"\btop[\s_-]*10\b",
            r"\bfinish[\s_-]*in[\s_-]*the[\s_-]*top[\s_-]*10\b",
            r"\bfinish[\s_-]*top[\s_-]*10\b",
            r"top10",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    if normalized_type == "top 5":
        patterns = [
            r"\btop[\s_-]*5\b",
            r"\bfinish[\s_-]*in[\s_-]*the[\s_-]*top[\s_-]*5\b",
            r"\bfinish[\s_-]*top[\s_-]*5\b",
            r"top5",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    if normalized_type == "podium":
        return (
            "podium" in text
            or "finish" in text and "top 3" in text
            or "finish" in text and "top3" in text
        )

    if normalized_type == "winner":
        return (
            "finish in first" in text
            or "wins the race" in text
            or "race winner" in text
        )

    if normalized_type == "pole":
        return (
            "pole position" in text
            or "pole" in text
        )

    return False


def market_matches_driver(market, driver_code):
    """
    Match a driver using the final ticker segment or market text.
    """
    ticker = str(market.get("ticker") or "").upper()
    driver_code = driver_code.upper()

    # Most F1 tickers look like:
    # KXF1RACEPODIUM-AZEGP26-ANT
    if ticker.endswith(f"-{driver_code}"):
        return True

    # Fallback to searching the title/text.
    text = get_market_text(market)

    driver_name_by_code = {
        code.lower(): name
        for name, code in DRIVER_CODES.items()
    }

    driver_name = driver_name_by_code.get(driver_code.lower())

    if driver_name and driver_name in text:
        return True

    return False


def deduplicate_markets(markets):
    """Remove duplicate markets by ticker."""
    unique_markets = {}
    for market in markets:
        ticker = market.get("ticker")

        if ticker:
            unique_markets[ticker] = market

    return list(unique_markets.values())


def find_matching_markets(all_markets, market_type, driver_code):
    """Find markets matching both the market type and driver."""
    matches = []

    for market in all_markets:
        if not is_open_market(market):
            continue

        if not market_matches_type(market, market_type):
            continue

        if not market_matches_driver(market, driver_code):
            continue

        matches.append(market)

    return matches


# ------------------------------------------------------------
# Price alerts
# ------------------------------------------------------------

def get_yes_ask_cents(market):
    """Return the YES ask price in cents."""
    value = market.get("yes_ask_dollars")

    if value is None:
        value = market.get("yes_ask")

    if value is None:
        return None

    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None


def get_no_ask_cents(market):
    """Return the NO ask price in cents."""
    value = market.get("no_ask_dollars")

    if value is None:
        value = market.get("no_ask")

    if value is None:
        return None

    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None


def get_price_cents(market, side):
    """Get the requested YES or NO ask price in cents."""
    if side.upper() == "YES":
        return get_yes_ask_cents(market)

    if side.upper() == "NO":
        return get_no_ask_cents(market)

    return None


def check_price_alerts():
    """Check configured price alerts against discovered F1 markets."""
    print("\nChecking price alerts...")

    alerts = load_json_file(PRICE_ALERTS_FILE, [])
    alert_state = load_json_file(PRICE_ALERT_STATE_FILE, {})

    if not alerts:
        print("No price alerts configured.")
        return

    # Start with markets from known series.
    all_markets = []

    known_series_to_check = set(NEW_MARKET_SERIES)
    known_series_to_check.add("KXF1RACEPODIUM")

    for series_ticker in known_series_to_check:
        markets = fetch_markets_for_series(series_ticker)
        all_markets.extend(markets)

    # Add a broad sample so that unknown Top 5/Top 10 series can be found.
    broad_markets = fetch_broad_market_sample()
    all_markets.extend(broad_markets)

    all_markets = deduplicate_markets(all_markets)

    print(f"Total unique markets available for price checks: {len(all_markets)}")

    for alert_number, alert in enumerate(alerts, start=1):
        market_type = str(alert.get("market_type", "")).strip()
        driver = str(alert.get("driver", "")).strip()
        side = str(alert.get("side", "YES")).upper().strip()

        try:
            target_cents = float(alert["price_cents"])
        except (KeyError, TypeError, ValueError):
            print(f"Skipping alert #{alert_number}: invalid price_cents.")
            continue

        driver_code = get_driver_code(driver)

        print(
            f"\nChecking alert #{alert_number}: "
            f"{driver} {market_type} {side} at {target_cents:g}¢"
        )
        print(f"Driver code: {driver_code}")

        matching_markets = find_matching_markets(
            all_markets,
            market_type,
            driver_code,
        )

        if not matching_markets:
            print(
                f"No matching {driver} {market_type} market found "
                "in the available market sample."
            )

            # Print potentially relevant F1 markets for troubleshooting.
            possible_f1_markets = []

            for market in all_markets:
                text = get_market_text(market)

                if (
                    "f1" in text
                    or "formula 1" in text
                    or "grand prix" in text
                    or "gp26" in text
                ):
                    possible_f1_markets.append(market)

            if possible_f1_markets:
                print(
                    "Potential F1 markets available for inspection: "
                    f"{len(possible_f1_markets)}"
                )

                for market in possible_f1_markets[:15]:
                    print(
                        "  "
                        f"ticker={market.get('ticker')} | "
                        f"title={market.get('title')} | "
                        f"event_ticker={market.get('event_ticker')}"
                    )

            continue

        print(f"Found {len(matching_markets)} matching market(s).")

        for market in matching_markets:
            ticker = market.get("ticker", "unknown ticker")
            current_cents = get_price_cents(market, side)

            if current_cents is None:
                print(f"  {ticker}: no {side} ask price available.")
                continue

            print(
                f"  {ticker}: "
                f"{side} ask = {current_cents:.1f}¢"
            )

            # Current behavior: alert when the ask is at or below
            # the configured threshold.
            threshold_reached = current_cents <= target_cents

            state_key = f"{alert_number}:{ticker}"
            already_alerted = bool(alert_state.get(state_key, False))

            if threshold_reached and not already_alerted:
                title = market.get("title") or f"{driver} {market_type}"

                message = (
                    "🏎️ F1 price alert!\n"
                    f"{title}\n"
                    f"Ticker: {ticker}\n"
                    f"Side: {side}\n"
                    f"Current ask: {current_cents:.1f}¢\n"
                    f"Threshold: {target_cents:g}¢"
                )

                print(message)
                send_discord(message)

                alert_state[state_key] = True

    save_json_file(PRICE_ALERT_STATE_FILE, alert_state)


# ------------------------------------------------------------
# Main program
# ------------------------------------------------------------

def main():
    check_for_new_f1_markets()
    check_price_alerts()
    print("\nFinished.")


if __name__ == "__main__":
    main()
