import os
import re
import time
import threading
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

URL = "https://www.amazon.ae/dp/B0C8Y8MJ36"
TARGET = Decimal("400")
INTERVAL = 60


class PriceUnavailable(Exception):
    pass


def notify(message):
    webhook = os.environ.get("AMAZON_DISCORD_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("Amazon webhook variable missing")

    response = requests.post(
        webhook,
        params={"wait": "true"},
        json={
            "content": message,
            "allowed_mentions": {"parse": []},
        },
        timeout=15,
    )
    if not response.ok:
        raise RuntimeError(
            f"Discord returned HTTP {response.status_code}"
        )


def read_price():
    # Fetch independently so a previous response's cookies
    # do not persist between checks.
    response = requests.get(
        URL,
        headers={"Accept-Language": "en-AE,en;q=0.9"},
        timeout=20,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one("#productTitle")
    if not title or "alakazam" not in title.get_text().lower():
        raise PriceUnavailable("Expected product page missing")

    summary = soup.select_one("#aod-ingress-link")
    if summary is None:
        raise PriceUnavailable("New-offer summary missing")

    text = summary.get_text(" ", strip=True)
    match = re.search(
        r"\bNew\b.*?\bfrom\s*AED\s*"
        r"([0-9][0-9,]*\s*\.\s*[0-9]{2})(?![0-9])",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise PriceUnavailable("New-offer price not recognized")

    price = Decimal(re.sub(r"[\s,]", "", match.group(1)))
    if price <= 0:
        raise PriceUnavailable("Invalid price")

    return price


def monitor():
    started = False
    previously_below = False
    failures = 0
    warned = False

    while True:
        delay = INTERVAL

        try:
            price = read_price()
            below = price < TARGET

            if not started:
                notify(
                    "✅ Amazon monitor connected.\n"
                    "Pokémon 151 Alakazam ex Box\n"
                    f"New offers from AED {price:.2f}.\n"
                    "Alert: below AED 400.\n"
                    "Checks approximately every 60 seconds."
                )
                started = True

            if below and not previously_below:
                notify(
                    "🔔 Alakazam ex Box price alert!\n"
                    f"New offers from AED {price:.2f}.\n"
                    f"{URL}\n"
                    "Check Other sellers, delivery costs, "
                    "and checkout availability."
                )

            # Preserve the previous state if an alert fails.
            previously_below = below

            if warned:
                notify(
                    "✅ Amazon monitoring recovered.\n"
                    f"New offers from AED {price:.2f}."
                )
                warned = False

            failures = 0
            print(
                f"AMAZON OK: AED {price:.2f}; "
                f"below_target={below}",
                flush=True,
            )

        except Exception as error:
            failures += 1
            delay = min(900, INTERVAL * (2 ** min(failures, 4)))

            # Only expose our own safe error descriptions.
            detail = (
                str(error)
                if isinstance(error, (PriceUnavailable, RuntimeError))
                else type(error).__name__
            )
            print(
                f"AMAZON FAILED: {detail}; retry in {delay}s",
                flush=True,
            )

            if failures >= 3 and not warned:
                try:
                    notify(
                        "⚠️ Amazon monitor needs attention.\n"
                        "Three consecutive checks or alerts failed.\n"
                        "Price alerts may be missed. Retrying "
                        "automatically; check Railway logs.\n"
                        f"{URL}"
                    )
                    warned = True
                except Exception:
                    print(
                        "AMAZON: Could not deliver failure warning.",
                        flush=True,
                    )

        time.sleep(delay)


threading.Thread(target=monitor, daemon=True).start()
