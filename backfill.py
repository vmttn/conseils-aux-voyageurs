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

SCHEMES = [
    {
        "url": furl("https://www.diplomatie.gouv.fr/local/cache-vignettes/"),
        "filename": "{}_fcvregional_monde.jpg",  # pre-April 2026
    },
    {
        "url": furl("https://www.diplomatie.gouv.fr/files/files/cav/"),
        "filename": "{}_fcv_monde.jpg",  # post-redesign
    },
]

WAYBACK_URL = furl("https://web.archive.org/")
TIMEOUT = 180
# https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md
FIELDS = ["timestamp", "original", "statuscode", "digest"]

OUTPUT_DIR = Path(__file__).parent / "monde"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def search_cdx(url: furl) -> pl.DataFrame:
    endpoint = (WAYBACK_URL / "cdx/search/cdx").set(
        {
            "url": url,
            "from": 2015,
            "matchType": "prefix",
            "fl": ",".join(FIELDS),
            "collapse": "digest",
        }
    )
    response = httpx.get(endpoint.url, timeout=TIMEOUT).raise_for_status()

    return pl.read_csv(
        response.content,
        separator=" ",
        has_header=False,
        new_columns=FIELDS,
        infer_schema_length=None,
        schema_overrides={"statuscode": pl.String},
    )


def main():
    name = pl.col("original").str.split("/").list.last()
    # The date normally leads the filename, but some legacy captures have a
    # stray prefix before it (e.g. "a20180918_fcvregional_monde_3_..."), so
    # pull the 8 digits right before "_fcv" rather than assuming position 0.
    date = name.str.extract(r"(\d{8})_fcv")

    frames = []
    for scheme in SCHEMES:
        print(f"Querying CDX for {scheme['url'].url} ...")
        matched = (
            search_cdx(scheme["url"])
            .filter(
                name.str.contains(
                    scheme["filename"].format("").removesuffix(".jpg"), literal=True
                )
            )
            .with_columns(filename=pl.format(scheme["filename"], date))
        )
        print(f"  -> {len(matched)} matching capture(s)")
        frames.append(matched)

    df = pl.concat(frames)

    existing = {path.name for path in OUTPUT_DIR.glob("*.jpg")}

    df = (
        df.filter(pl.col("statuscode").is_in(["200", "302"]))
        .drop_nulls("filename")
        .filter(~pl.col("filename").is_in(existing))
        .sort("timestamp", descending=False)
        .unique("filename", keep="last", maintain_order=True)
    )

    print(f"{len(df)} new map(s) to fetch ({len(existing)} already in {OUTPUT_DIR})")

    saved = suspicious = failed = 0
    progress = tqdm(df.iter_rows(named=True), total=len(df))
    for row in progress:
        image_url = (
            furl(WAYBACK_URL) / "web" / f"{row['timestamp']}if_" / row["original"]
        )
        progress.set_description(image_url.url)

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
            tqdm.write(f"✗ failed to fetch {image_url} after multiple attempts")
            failed += 1
            continue

        if len(response.content) <= 10_000:
            tqdm.write(
                f"⚠ suspicious image size ({len(response.content)} bytes) for {image_url}"
            )
            suspicious += 1
            continue

        output_path = OUTPUT_DIR / row["filename"]
        with output_path.open("wb") as f:
            f.write(response.content)
        tqdm.write(f"✓ saved {row['filename']} ({len(response.content)} bytes)")
        saved += 1

        sleep(5)

    print(f"Done: {saved} saved, {suspicious} suspicious, {failed} failed")


if __name__ == "__main__":
    main()
