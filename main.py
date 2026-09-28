import os
import time
import requests

PRODUCT_URL = (
    "https://littlethingsme.com/products/"
    "pokemon-tcg-30th-anniversary-sylveon-ex-box"
)
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
CHECK_SECONDS = 15

session = requests.Session()
session.headers.update({"User-Agent": "PersonalStockMonitor/1.0"})


def notify(message):
    response = requests.post(
        WEBHOOK_URL,
        params={"wait": "true"},
        json={
            "content": message,
            "allowed_mentions": {"parse": []},
        },
        timeout=15,
    )
    if response.status_code == 429:
        try:
            delay = float(response.json().get("retry_after", 30))
        except (ValueError, TypeError):
            delay = 30
        time.sleep(min(max(delay, 1), 300))
    if not response.ok:
        # Do not expose the private webhook URL in logs.
        raise RuntimeError(
            f"Discord returned status {response.status_code}"
        )


last_available = None
startup_sent = False
failures = 0

print("Stock monitor starting.", flush=True)

while True:
    started = time.monotonic()
    delay = CHECK_SECONDS

    try:
        response = session.get(PRODUCT_URL + ".js", timeout=10)
        response.raise_for_status()
        product = response.json()

        available = product.get("available")
        if not isinstance(available, bool):
            raise ValueError("Product availability is missing")

        title = product.get("title", "Watched product")

        if not startup_sent:
            status = "AVAILABLE" if available else "out of stock"
            notify(
                f"✅ Monitor connected: {title}\n"
                f"Current status: {status}\n"
                f"Checking every {CHECK_SECONDS} seconds.\n"
                f"{PRODUCT_URL}"
            )
            startup_sent = True

        if available and last_available is not True:
            notify(
                f"🔔 AVAILABLE: {title}\n"
                f"{PRODUCT_URL}\n"
                "Check the page for purchase or preorder details."
            )

        # Update only after any required alert succeeds.
        last_available = available
        failures = 0
        print(
            f"Check OK — available={available}",
            flush=True,
        )

    except Exception as error:
        failures += 1
        delay = min(300, CHECK_SECONDS * (2 ** min(failures, 5)))
        # Log the error type only, keeping credentials private.
        print(
            f"Check/alert failed ({type(error).__name__}). "
            f"Retrying in {delay} seconds.",
            flush=True,
        )

    time.sleep(max(0, delay - (time.monotonic() - started)))
