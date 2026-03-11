#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "furl",
#     "pandas",
# ]
# ///

import pandas as pd
from furl import furl

URL = furl("https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/")

WAYBACK_URL = furl("https://web.archive.org/")
WAYBACK_CDX_SEARCH_ENDPOINT_URL = (WAYBACK_URL / "cdx/search/cdx").set(
    {
        "url": URL,
        "from": 2010,
        "to": 2026,
        "output": "json",
        "fl": ",".join(["timestamp", "original", "statuscode", "digest"]),
    }
)


def format_url(timestamp: str) -> str:
    return str(WAYBACK_URL / "web" / timestamp / str(URL))


def main() -> None:
    df = pd.read_json(str(WAYBACK_CDX_SEARCH_ENDPOINT_URL), dtype=False)
    df = df.fillna("").replace({"": None})
    df = df[1:].rename(columns=df.iloc[0])
    # remove snapshots with the same content (same digest)
    df = df[~df["digest"].duplicated(keep="first")]
    df = df.assign(url=df["timestamp"].apply(format_url))
    df = df.assign(timestamp=pd.to_datetime(df["timestamp"]))
    df = df.sort_values("timestamp", ascending=False)

    for url in df["url"]:
        print(url)


if __name__ == "__main__":
    main()
