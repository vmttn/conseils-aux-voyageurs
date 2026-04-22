#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "furl",
#     "httpx",
#     "polars",
#     "tenacity",
#     "tqdm",
# ]
# ///

from pathlib import Path
from time import sleep

import httpx
import polars as pl
from furl import furl
from tqdm import tqdm
import tenacity

URL = furl("https://www.diplomatie.gouv.fr/local/cache-vignettes/")


WAYBACK_URL = furl("https://web.archive.org/")
TIMEOUT = 180
# https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md
FIELDS = ["timestamp", "original", "statuscode", "digest"]
WAYBACK_CDX_SEARCH_ENDPOINT_URL = (WAYBACK_URL / "cdx/search/cdx").set(
    {
        "url": URL,
        "from": 2015,
        "to": 2025,
        "matchType": "prefix",
        "fl": ",".join(FIELDS),
        # "filter": "statuscode:200",
        "collapse": "digest",
    }
)

OUTPUT_DIR = Path(__file__).parent / "monde"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    response = httpx.get(
        WAYBACK_CDX_SEARCH_ENDPOINT_URL.url,
        timeout=TIMEOUT,
    ).raise_for_status()

    df = pl.read_csv(
        response.content,
        separator=" ",
        has_header=False,
        new_columns=FIELDS,
        infer_schema_length=None,
    )

    df = (
        df.filter(pl.col("original").str.contains("fcvregional_monde"))
        .filter(pl.col("statuscode").is_in(["200", "302"]))
        .sort("timestamp", descending=False)
    )

    for row in tqdm(df.iter_rows(named=True), total=len(df)):
        image_url = (
            furl(WAYBACK_URL) / "web" / f"{row['timestamp']}if_" / row["original"]
        )

        try:
            for attempt in tenacity.Retrying(
                wait=tenacity.wait_exponential(min=10, max=120),
                stop=tenacity.stop_after_attempt(5),
            ):
                with attempt:
                    response = httpx.get(
                        url=image_url.url,
                        follow_redirects=True,
                    ).raise_for_status()
        except tenacity.RetryError:
            print(f"Failed to fetch {image_url} after multiple attempts")
            continue

        if len(response.content) <= 10_000:
            print(f"Suspicious image size for {image_url}")
            continue

        filename = Path(Path(str(image_url.path)).name[:26]).with_suffix(".jpg").name
        if not filename.endswith("fcvregional_monde.jpg"):
            print(f"Unexpected filename {filename} for {image_url}")
            continue

        output_path = OUTPUT_DIR / filename
        with output_path.open("wb") as f:
            f.write(response.content)

        sleep(5)


if __name__ == "__main__":
    main()
