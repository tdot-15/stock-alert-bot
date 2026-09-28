import amazon_test
import os
import time
import requests

BASE_URL = "https://littlethingsme.com/products/"
PRODUCTS = [
    "pokemon-tcg-30th-anniversary-sylveon-ex-box",
    "pokemon-tcg-30th-anniversary-ex-tin-assortment",
    "pokemon-tcg-30th-anniversary-greninja-ex-box",
    "pokemon-tcg-30th-anniversary-elite-trainer-box",
    "pokemon-tcg-30th-anniversary-poster-collection",
    "pokemon-tcg-30th-anniversary-binder-collection",
    "pokemon-tcg-30th-anniversary-2-pack-blister",
]

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
        time.sleep(max(delay, 1))

    if not response.ok:
        raise RuntimeError(
            f"Discord returned status {response.status_code}"
        )


# Track each product separately. Stagger checks to spread requests.
now = time.monotonic()
states = {
    handle: {
        "available": None,
        "failures": 0,
        "next_check": now + index * CHECK_SECONDS / len(PRODUCTS),
    }
    for index, handle in enumerate(PRODUCTS)
}

startup_sent = False
startup_retry = 0

print("Starting monitor for 7 products.", flush=True)

while True:
    if not startup_sent and time.monotonic() >= startup_retry:
        try:
            notify(
                "✅ Monitor started for 7 products.\n"
                "Checking each approximately every 15 seconds.\n"
                "Alerts will include the product name and link."
            )
            startup_sent = True
        except Exception as error:
            print(
                f"Startup message failed: {type(error).__name__}",
                flush=True,
            )
            startup_retry = time.monotonic() + 60

    for handle, state in states.items():
        if time.monotonic() < state["next_check"]:
            continue

        started = time.monotonic()
        delay = CHECK_SECONDS
        url = BASE_URL + handle

        try:
            response = session.get(url + ".js", timeout=10)
            response.raise_for_status()
            product = response.json()

            available = product.get("available")
            if not isinstance(available, bool):
                raise ValueError("Product availability is missing")

            title = product.get("title", handle)

            if available and state["available"] is not True:
                notify(
                    f"🔔 AVAILABLE: {title}\n"
                    f"{url}\n"
                    "Check the page for purchase or preorder details."
                )

            # Save status only after any required alert succeeds.
            state["available"] = available
            state["failures"] = 0
            print(
                f"{handle}: available={available}",
                flush=True,
            )

        except Exception as error:
            state["failures"] += 1
            delay = min(
                300,
                CHECK_SECONDS * (2 ** min(state["failures"], 5)),
            )
            print(
                f"{handle}: {type(error).__name__}; "
                f"retry in {delay}s",
                flush=True,
            )

        state["next_check"] = max(
            started + delay,
            time.monotonic() + 1,
        )

    time.sleep(0.5)
