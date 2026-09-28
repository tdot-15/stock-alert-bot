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


def send_alert(message):
    webhook = os.environ["AMAZON_DISCORD_WEBHOOK_URL"]
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


def read_price(session):
    response = session.get(URL, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one("#productTitle")
    if not title or "alakazam" not in title.get_text().lower():
        raise ValueError("Expected product page not found")

    summary = soup.select_one("#aod-ingress-link")
    if summary is None:
        raise ValueError("New-offer summary missing")

    text = summary.get_text(" ", strip=True)
    text = text.replace("\u00a0", " ")

    # Read only the new-offer starting price, not unrelated prices.
    match = re.search(
        r"\bNew\b.*?\bfrom\s*AED\s*"
        r"([0-9][0-9,]*\s*\.\s*[0-9]{2})(?![0-9])",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError("New-offer AED price not recognized")

    amount = re.sub(r"[\s,]", "", match.group(1))
    price = Decimal(amount)
    if price <= 0:
        raise ValueError("Invalid price")

    return price


def monitor():
    session = requests.Session()
    session.headers.update({"Accept-Language": "en-AE,en;q=0.9"})

    connected = False
    previously_below = False
    failures = 0

    while True:
        delay = INTERVAL
        try:
            price = read_price(session)
            below = price < TARGET

            if not connected:
                send_alert(
                    "✅ Amazon price monitor connected.\n"
                    "Pokémon 151 Alakazam ex Box\n"
                    f"New offers currently from AED {price:.2f}.\n"
                    "Alert threshold: below AED 400.\n"
                    "Checking every 60 seconds."
                )
                connected = True

            if below and not previously_below:
                send_alert(
                    "🔔 PRICE ALERT: Pokémon 151 Alakazam ex Box\n"
                    f"New offers from AED {price:.2f} "
                    "— below AED 400!\n"
                    f"{URL}\n"
                    "Open Other sellers to check the offer, "
                    "delivery charges, and availability."
                )

            # Update only after any required message succeeds.
            previously_below = below
            failures = 0
            print(
                f"AMAZON: new offers from AED {price:.2f}; "
                f"below_target={below}",
                flush=True,
            )

        except Exception as error:
            failures += 1
            delay = min(900, INTERVAL * (2 ** min(failures, 4)))
            print(
                f"AMAZON: check/alert failed "
                f"({type(error).__name__}); retry in {delay}s",
                flush=True,
            )

        time.sleep(delay)


threading.Thread(target=monitor, daemon=True).start()
