#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "furl",
#     "httpx",
#     "playwright",
# ]
# ///

from pathlib import Path

from playwright import sync_api as pw
from furl import furl
import httpx

URL = furl("https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/")
OUTPUT_DIR = Path(__file__).parent / "monde"


def main() -> None:
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(str(URL))
        image_locator = page.locator('img[src*="fcvregional_monde.jpg"]')
        image_path = image_locator.get_attribute("src")
        browser.close()

    if image_path is None:
        raise RuntimeError("Image not found")

    image_url = URL.remove(path=True) / image_path

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / Path(image_path).name

    response = httpx.get(image_url.url, follow_redirects=True).raise_for_status()

    if len(response.content) <= 10_000:
        raise ValueError("Suspicious image size")

    with output_path.open("wb") as f:
        f.write(response.content)

    print(f"Image saved to {output_path}")


if __name__ == "__main__":
    main()
