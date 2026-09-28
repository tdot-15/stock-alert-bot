import re
import threading
import requests


def test_amazon():
    try:
        response = requests.get(
            "https://www.amazon.ae/dp/B0C8Y8MJ36",
            headers={"Accept-Language": "en-AE,en;q=0.9"},
            timeout=20,
        )

        html = response.text
        title = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        title_text = (
            re.sub(r"\s+", " ", title.group(1)).strip()
            if title else "No page title"
        )

        blocked = any(
            phrase in html.lower()
            for phrase in [
                "enter the characters you see",
                "sorry, we just need to make sure",
                "robot check",
            ]
        )

        print(
            f"AMAZON TEST: HTTP {response.status_code}; "
            f"title={title_text[:180]}; "
            f"robot_check={blocked}; "
            f"price_markup={'a-price' in html}",
            flush=True,
        )

    except requests.RequestException as error:
        print(
            f"AMAZON TEST: {type(error).__name__}",
            flush=True,
        )


threading.Thread(target=test_amazon, daemon=True).start()
