"""Place two MAREN attacks side by side at their original pixel density and timing."""

import argparse
from bisect import bisect_right
from itertools import accumulate
import json
from pathlib import Path

from PIL import Image, ImageDraw


def load(folder):
    layout = json.loads((folder / "attack.json").read_bytes())["animations"]["attack"]
    with Image.open(folder / "attack.png") as image:
        return image.convert("RGBA"), layout


def paste_tile(panel, version, direction, frame, x, y):
    image, layout = version
    w, h = layout["cell"]
    row = layout["rows"].index(direction)
    tile = image.crop((frame * w, row * h, (frame + 1) * w, (row + 1) * h))
    panel.paste(tile, (x, y), tile)


def compare(before, after, out):
    versions = [load(before), load(after)]
    old, new = (layout for _, layout in versions)
    for key in ("cell", "anchor", "rows", "phase_names"):
        assert old[key] == new[key], key
    w, h = new["cell"]
    ends = [list(accumulate(layout["durations_ms"])) for _, layout in versions]
    assert ends[0][-1] == ends[1][-1]
    bounds = sorted({0, *ends[0], *ends[1]})
    background = "#303640"
    frames = []
    for time in bounds[:-1]:
        panel = Image.new("RGB", (4 * w + 24, 4 * (h + 18)), background)
        label = ImageDraw.Draw(panel)
        for row, direction in enumerate(new["rows"]):
            x = (row % 2) * (2 * w + 12)
            y = (row // 2) * (h + 18)
            for i, version in enumerate(versions):
                label.text((x + i*w + 2, y), f"{direction}  {('Before', 'After')[i]}", fill="white")
                paste_tile(panel, version, direction, bisect_right(ends[i], time), x + i*w, y + 16)
        frames.append(panel)
    out.mkdir(parents=True, exist_ok=True)
    frames[0].save(out / "slash-comparison.gif", save_all=True, append_images=frames[1:],
                   duration=[b-a for a, b in zip(bounds, bounds[1:])], disposal=2, loop=0)

    panel = Image.new("RGB", (8*w + 34, 4*h + 36), background)
    label = ImageDraw.Draw(panel)
    directions = ("S", "W", "E", "NW")
    for row, direction in enumerate(directions):
        label.text((1, 36 + row*h + h//2), direction, fill="white")
    for i, version in enumerate(versions):
        left = 24 + i*(4*w + 8)
        label.text((left, 0), ("Before", "After")[i], fill="white")
        for col, phase in enumerate(("raise", "coil", "cut", "follow through")):
            x = left + col*w
            label.text((x, 16), phase, fill="#d2d7de")
            for row, direction in enumerate(directions):
                y = 36 + row*h
                paste_tile(panel, version, direction, new["phase_names"].index(phase), x, y)
    panel.resize((2*panel.width, 2*panel.height), Image.Resampling.NEAREST).save(out / "slash-poses.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("before", "after", "out"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args()
    compare(args.before, args.after, args.out)
