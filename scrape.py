#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "furl",
#     "httpx",
#     "playwright",
# ]
# ///

import sys
from pathlib import Path

from playwright import sync_api as pw
from furl import furl
import httpx

URL = furl("https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/")
OUTPUT_DIR = Path(__file__).parent / "monde"
PLAYWRIGHT_TIMEOUT_SEC = 60_000


def main(url: furl) -> None:
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.set_default_timeout(PLAYWRIGHT_TIMEOUT_SEC)
        page = context.new_page()
        page.goto(str(url))
        image_path = page.get_by_role("link", name="Monde").get_attribute("href")
        browser.close()

    if image_path is None:
        raise RuntimeError("Image URL not found")

    image_path, *_ = image_path.split("?")

    if not image_path.startswith("http"):
        image_url = url / image_path
    else:
        image_url = furl(image_path)

    image_url = URL.remove(path=True) / image_path

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / Path(image_path).name

    response = httpx.get(image_url.url, follow_redirects=True)
    response.raise_for_status()

    if len(response.content) <= 10_000:
        raise ValueError("Suspicious image size")

    with output_path.open("wb") as f:
        f.write(response.content)

    print(f"Image saved to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _, url, *_ = sys.argv
        url = furl(url)
    else:
        url = URL

    main(url)
