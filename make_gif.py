#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pendulum",
#     "pillow",
#     "plotnine",
#     "polars",
#     "pyarrow",
# ]
# ///

import io
import textwrap
from pathlib import Path
from typing import TypedDict
from functools import cache

import pendulum
import plotnine as gg
import polars as pl
from PIL import Image

INPUT_DIR = Path(__file__).parent / "monde"
OUTPUT_FILE = Path(__file__).parent / "animation.gif"


EVENTS_DF = pl.DataFrame(
    [
        {"date": pendulum.Date(2020, 3, 11), "label": "Pandémie de COVID-19"},
        {"date": pendulum.Date(2022, 2, 24), "label": "Invasion de l’Ukraine"},
    ]
).with_columns(
    pl.col("label").map_elements(
        lambda label: "\n".join(textwrap.wrap(label, width=15)),
    )
)


@cache
def make_timeline_base_plot(
    range_: tuple[pendulum.Date, pendulum.Date],
    color: str,
):
    data = (
        pl.date_range(
            start=range_[0],
            end=range_[1],
            interval="1y",
            eager=True,
        )
        .alias("date")
        .to_frame()
    )
    return (
        gg.ggplot(data=data)
        + gg.geom_rect(
            data=data.select(
                pl.col("date").alias("start"),
                pl.col("date").shift(-1).alias("end"),
            ).filter(pl.col("end").is_not_null()),
            mapping=gg.aes(
                xmin="start",
                xmax="end",
                ymin=0,
                ymax=30,
            ),
            color=color,
            fill=None,
        )
        + gg.geom_text(
            data=data,
            mapping=gg.aes(
                x="date",
                y=-30,
                label="date.dt.year",
            ),
            size=6,
            color=color,
            va="baseline",
        )
        + gg.geom_segment(
            data=EVENTS_DF,
            mapping=gg.aes(
                x="date",
                xend="date",
                y=40,
                yend=100,
            ),
            color=color,
        )
        + gg.geom_text(
            data=EVENTS_DF,
            mapping=gg.aes(
                x="date",
                y=110,
                label="label",
            ),
            position=gg.position_nudge(x=20),
            color=color,
            size=6,
            ha="left",
            va="top",
        )
        + gg.theme_void()
    )


def make_timeline(
    range_: tuple[pendulum.Date, pendulum.Date],
    highlight: tuple[pendulum.Date, pendulum.Date],
    width_px: int,
    height_px: int,
    color: str,
) -> Image:
    plot = make_timeline_base_plot(
        range_=range_,
        color=color,
    ) + gg.annotate(
        "rect",
        xmin=highlight[0],
        xmax=highlight[1],
        ymin=0,
        ymax=30,
        fill=color,
        alpha=0.5,
    )

    dpi = 150

    fig = plot.draw()
    fig.set_size_inches(w=width_px / dpi, h=height_px / dpi, forward=False)

    with io.BytesIO() as buf:
        fig.savefig(
            buf,
            dpi=dpi,
            transparent=True,
        )
        buf.seek(0)
        image = Image.open(buf).convert("RGBA")
        image.load()

    return image


def insert_timeline(
    image: Image.Image,
    range_: tuple[pendulum.DateTime, pendulum.DateTime],
    highlight: tuple[pendulum.DateTime, pendulum.DateTime],
) -> Image.Image:
    background = image.copy()

    timeline = make_timeline(
        range_=range_,
        highlight=highlight,
        width_px=background.width // 2,
        height_px=background.height // 10,
        color="#{:02x}{:02x}{:02x}".format(*background.getpixel((1, 1))),
    )

    background.paste(
        im=timeline,
        box=(
            int(0.35 * background.width),
            int(0.80 * background.height),
        ),
        mask=timeline,
    )
    return background


def normalize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.copy()
    image = image.resize(size, resample=Image.Resampling.LANCZOS)
    image = image.convert("RGBA")
    return image


def fade(before: Image.Image, after: Image.Image, steps: int) -> list[Image.Image]:
    frames = []
    for i in range(steps + 1):
        alpha = i / steps
        blended = Image.blend(before, after, alpha)
        frames.append(blended)
    return frames


class ImageDict(TypedDict):
    timestamp: pendulum.Date
    image: Image.Image


def main() -> None:
    screen_time_per_year = 5  # second
    time_scale = screen_time_per_year / (365 * 24 * 3600)  # year per second
    fade_ms = 200
    fade_frame_rate = 10
    fade_steps = fade_frame_rate * fade_ms // 1000

    images = [
        ImageDict(
            timestamp=pendulum.Date.fromisoformat(path.stem[:8]),
            image=Image.open(path),
        )
        for path in sorted(INPUT_DIR.glob("*.jpg"))
    ]

    frames = []
    durations = []

    size = images[0]["image"].size

    for image in images:
        image["image"] = normalize(
            image=image["image"],
            size=size,
        )

    range_ = (
        images[0]["timestamp"].start_of("year"),
        images[-1]["timestamp"].start_of("year") + pendulum.Duration(years=1),
    )
    for image, next_image in zip(images, [*images[1:], None]):
        if next_image is not None:
            highlight = (image["timestamp"], next_image["timestamp"])
        else:
            highlight = (image["timestamp"], range_[1])
        image["image"] = insert_timeline(
            image=image["image"],
            range_=range_,
            highlight=highlight,
        )

    black = Image.new("RGBA", size, (0, 0, 0, 0))

    # fade in
    for frame in fade(black, images[0]["image"], fade_steps):
        frames.append(frame)
        durations.append(fade_ms // fade_steps)

    for image, next_image in zip(images, [*images[1:], None]):
        frames.append(image["image"])

        if next_image is None:
            durations.append(2000)
            break

        delta = next_image["timestamp"] - image["timestamp"]
        hold_ms = int(delta.total_seconds() * time_scale) * 1000
        durations.append(hold_ms)

        for frame in fade(image["image"], next_image["image"], fade_steps):
            frames.append(frame)
            durations.append(fade_ms // fade_steps)

    # fade out
    for frame in fade(images[-1]["image"], black, fade_steps):
        frames.append(frame)
        durations.append(fade_ms // fade_steps)

    durations[-1] = 2000

    frames[0].save(
        OUTPUT_FILE,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
    )


if __name__ == "__main__":
    main()
