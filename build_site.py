#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "monde"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = ROOT / "_site"


def main() -> None:
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    (OUTPUT_DIR / "monde").mkdir(parents=True)

    maps = []
    for image in sorted(IMAGES_DIR.glob("*.jpg")):
        date = datetime.strptime(image.name[:8], "%Y%m%d").date()
        shutil.copy(image, OUTPUT_DIR / "monde" / image.name)
        maps.append({"date": date.isoformat(), "src": f"monde/{image.name}"})

    maps.sort(key=lambda m: m["date"])
    (OUTPUT_DIR / "maps.json").write_text(json.dumps(maps, indent=1) + "\n")
    shutil.copy(SITE_DIR / "index.html", OUTPUT_DIR / "index.html")

    print(f"Site built in {OUTPUT_DIR} ({len(maps)} maps)")


if __name__ == "__main__":
    main()
