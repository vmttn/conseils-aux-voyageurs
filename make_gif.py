#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
# ]
# ///

from pathlib import Path
from PIL import Image
from datetime import date
from typing import TypedDict

INPUT_DIR = Path(__file__).parent / "monde"
OUTPUT_FILE = Path(__file__).parent / "animation.gif"


def normalize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
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
    timestamp: date
    image: Image.Image


def main() -> None:
    screen_time_per_year = 5  # second
    time_scale = screen_time_per_year / (365 * 24 * 3600)  # year per second
    fade_ms = 200
    fade_frame_rate = 10
    fade_steps = fade_frame_rate * fade_ms // 1000

    images = [
        ImageDict(
            timestamp=date.fromisoformat(path.stem[:8]),
            image=Image.open(path),
        )
        for path in sorted(INPUT_DIR.glob("*.jpg"))
    ]

    frames = []
    durations = []

    size = images[0]["image"].size

    images = [{**image, "image": normalize(image["image"], size)} for image in images]

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
