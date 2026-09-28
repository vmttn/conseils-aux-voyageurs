#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = ["pydantic", "pydantic-yaml"]
# ///

import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    StringConstraints,
    ValidationError,
    model_validator,
)
from pydantic_yaml import parse_yaml_file_as

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "monde"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = ROOT / "_site"
CONTEXT_FILE = ROOT / "context.yaml"

EventId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Sentence = Annotated[str, StringConstraints(min_length=1)]


class Fact(BaseModel, extra="forbid"):
    """A precise, dated fact about an event: a single date, or a period."""

    fact: Sentence
    date: dt.date | None = None
    start: dt.date | None = None
    end: dt.date | None = None

    @model_validator(mode="after")
    def check_dates(self):
        if (self.date is None) == (self.start is None):
            raise ValueError("a fact needs either `date` or `start`")
        if self.end is not None and (self.start is None or self.end < self.start):
            raise ValueError("`end` needs a `start` before it")
        return self


class Event(BaseModel, extra="forbid"):
    title: Sentence
    facts: list[Fact] = []


class Change(BaseModel, extra="forbid"):
    change: Sentence
    explanation: Sentence
    sources: list[HttpUrl] = []
    event: EventId | None = None


class Context(BaseModel, extra="forbid"):
    events: dict[EventId, Event] = {}
    updates: dict[dt.date, Annotated[list[Change], Field(min_length=1)]] = {}

    @model_validator(mode="after")
    def check_events(self):
        for day, changes in self.updates.items():
            for change in changes:
                if change.event is not None and change.event not in self.events:
                    raise ValueError(f"updates/{day}: unknown event {change.event!r}")
        return self


def load_context(map_dates: set[dt.date]) -> Context:
    try:
        context = parse_yaml_file_as(Context, CONTEXT_FILE)
    except (
        ValidationError,
        ValueError,
    ) as e:  # ValueError: impossible date in the YAML
        sys.exit(f"{CONTEXT_FILE.name} is invalid:\n{e}")
    unknown = sorted(context.updates.keys() - map_dates)
    if unknown:
        sys.exit(
            f"{CONTEXT_FILE.name} has updates on dates with no map: {', '.join(map(str, unknown))}"
        )
    return context


def main() -> None:
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    (OUTPUT_DIR / "monde").mkdir(parents=True)

    maps = []
    for image in sorted(IMAGES_DIR.glob("*.jpg")):
        date = dt.datetime.strptime(image.name[:8], "%Y%m%d").date()
        shutil.copy(image, OUTPUT_DIR / "monde" / image.name)
        maps.append({"date": date, "src": f"monde/{image.name}"})

    maps.sort(key=lambda m: m["date"])
    context = load_context({m["date"] for m in maps})
    for m in maps:
        if changes := context.updates.get(m["date"]):
            m["changes"] = [
                c.model_dump(mode="json", exclude_none=True) for c in changes
            ]
        m["date"] = m["date"].isoformat()
    (OUTPUT_DIR / "maps.json").write_text(json.dumps(maps, indent=1) + "\n")
    events = {
        k: e.model_dump(mode="json", exclude_none=True)
        for k, e in context.events.items()
    }
    (OUTPUT_DIR / "events.json").write_text(json.dumps(events, indent=1) + "\n")
    shutil.copy(SITE_DIR / "index.html", OUTPUT_DIR / "index.html")

    print(f"Site built in {OUTPUT_DIR} ({len(maps)} maps)")


if __name__ == "__main__":
    main()
