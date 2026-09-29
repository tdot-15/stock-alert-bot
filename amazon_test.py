import threading
import requests
from bs4 import BeautifulSoup

URL = "https://www.amazon.ae/dp/B0C8Y8MJ36"


def diagnose():
    try:
        response = requests.get(
            URL,
            headers={"Accept-Language": "en-AE,en;q=0.9"},
            timeout=20,
        )
        print(
            f"AMAZON DIAG: HTTP {response.status_code}",
            flush=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.select_one("#productTitle")

        if title is None:
            page_title = soup.title
            text = (
                page_title.get_text(" ", strip=True)
                if page_title else "No title"
            )
            print(
                f"AMAZON DIAG: Product title missing; page={text[:200]}",
                flush=True,
            )
            return

        print(
            "AMAZON DIAG: Product="
            + title.get_text(" ", strip=True),
            flush=True,
        )

        selectors = [
            "#availability",
            "#aod-ingress-link",
            "#corePriceDisplay_desktop_feature_div",
            "#corePrice_feature_div",
            "#apex_desktop",
            "#buybox",
            "#olp_feature_div",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            text = (
                element.get_text(" ", strip=True)[:1200]
                if element else "NOT PRESENT"
            )
            print(
                f"AMAZON DIAG: {selector} => {text}",
                flush=True,
            )

        print("AMAZON DIAG: Finished.", flush=True)

    except Exception as error:
        print(
            f"AMAZON DIAG: Request failed ({type(error).__name__})",
            flush=True,
        )


threading.Thread(target=diagnose, daemon=True).start()
