import threading
import requests
from bs4 import BeautifulSoup


def test_amazon():
    try:
        response = requests.get(
            "https://www.amazon.ae/dp/B0C8Y8MJ36",
            headers={"Accept-Language": "en-AE,en;q=0.9"},
            timeout=20,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.select_one("#productTitle")
        if title is None:
            print("AMAZON TEST: Product page not found.", flush=True)
            return

        print(
            "AMAZON PRODUCT: " + title.get_text(" ", strip=True),
            flush=True,
        )

        selectors = [
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
            "#corePrice_feature_div .a-price .a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "#buybox .a-price .a-offscreen",
        ]

        found = False
        for selector in selectors:
            prices = list(dict.fromkeys(
                element.get_text(" ", strip=True)
                for element in soup.select(selector)
            ))
            if prices:
                found = True
                print(
                    f"AMAZON PRICE: {selector} => {prices}",
                    flush=True,
                )

        if not found:
            print("AMAZON PRICE: No matching price found.", flush=True)

        for selector in [
            "#merchant-info",
            "#tabular-buybox",
            "#availability",
            "#aod-ingress-link",
        ]:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                print(
                    f"AMAZON DETAILS: {selector} => {text[:700]}",
                    flush=True,
                )

    except Exception as error:
        print(
            f"AMAZON TEST FAILED: {type(error).__name__}",
            flush=True,
        )


threading.Thread(target=test_amazon, daemon=True).start()
