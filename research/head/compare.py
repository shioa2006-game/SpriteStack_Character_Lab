"""Before/after figures for the walk.head standard.

"Before" is the walk published before walk.head (research/head/baseline/<name>:
walk.png, walk.json and the part atlas walk_part_ids.png of the same bake). "After"
is a --modes walk bake with walk.head, for example the published copy. Outputs, per
character:

    <name>_head_before_after.gif   eight directions, before (top) and after (bottom), x3
    <name>_head_crops.png          head and shoulders of every frame, x6, before and
                                   after rows for each direction, a tick every 4 px
and metrics.json with, per direction, the topmost row of the head and of the chest
(from the part atlases) and the eye pixels drawn in each frame (from the RGBA sheets,
so a hand or item in front of the face counts as well).

    python -m research.head.compare --after output/head --out research/head/results
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.walk.compare import BACKGROUND, LABEL, save_gif
from spritestack.character import load_character

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("maren", "azure_ronin", "crystal_mage")
BASELINE = ROOT / "research/head/baseline"


def load(folder):
    """Walk layout, frames [direction][frame] and the part atlas of a bake or baseline folder."""
    layout = folder / "walk.json" if (folder / "walk.json").exists() else folder / "metadata.json"
    walk = json.loads(layout.read_text(encoding="utf-8"))["animations"]["walk"]
    cell = walk["cell"][0]
    with Image.open(folder / "walk.png") as image:
        sheet = image.convert("RGBA")
    with Image.open(folder / "walk_part_ids.png") as image:
        atlas = np.asarray(image)
    frames = [[sheet.crop((c * cell, r * cell, (c + 1) * cell, (r + 1) * cell))
               for c in range(walk["columns"])] for r in range(len(walk["rows"]))]
    return walk, frames, atlas


def top_rows(atlas, part_id, walk):
    cell = walk["cell"][0]
    result = {}
    for row, direction in enumerate(walk["rows"]):
        result[direction] = []
        for column in range(walk["columns"]):
            tile = atlas[row * cell:(row + 1) * cell, column * cell:(column + 1) * cell]
            rows = np.where((tile == part_id).any(axis=1))[0]
            result[direction].append(int(rows.min()) if len(rows) else None)
    return result


def eye_pixels(frames, walk, character):
    names = [material["name"] for material in character.config["model"]["palette"]]
    if "eyes" not in names:
        return None
    colors = character.palette[names.index("eyes") + 1, :3]
    return {direction: [int(np.isin(np.asarray(frame)[..., :3].reshape(-1, 3).view([("", np.uint8)] * 3),
                                     np.ascontiguousarray(colors).view([("", np.uint8)] * 3)).sum())
                        for frame in frames[row]]
            for row, direction in enumerate(walk["rows"])}


def crops(path, walk, versions, scale=6, box=(10, 2, 38, 26)):
    x0, y0, x1, y1 = box
    width, height = (x1 - x0) * scale, (y1 - y0) * scale
    columns = walk["columns"]
    label = 54
    canvas = Image.new("RGB", (label + columns * (width + 4),
                               len(walk["rows"]) * (len(versions) * (height + 4) + 10)), (30, 30, 34))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for row, direction in enumerate(walk["rows"]):
        for name, frames in versions:
            for column in range(columns):
                tile = Image.new("RGBA", frames[row][column].size, BACKGROUND)
                tile.alpha_composite(frames[row][column])
                tile = tile.crop(box).resize((width, height), Image.NEAREST).convert("RGB")
                x = label + column * (width + 4)
                canvas.paste(tile, (x, y))
                for tick in range(0, height, 4 * scale):
                    draw.line([(x, y + tick), (x + 4, y + tick)], fill=(255, 214, 0))
            draw.text((6, y + 6), f"{direction}\n{name}", fill=LABEL)
            y += height + 4
        y += 10
    canvas.save(path, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--after", type=Path, required=True,
                        help="folder with one --modes walk bake per character (<folder>/<name>)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--characters", nargs="+", default=list(NAMES))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for name in args.characters:
        character = load_character(ROOT / f"characters/{name}/character.json")
        walk, before, before_atlas = load(BASELINE / name)
        _, after, after_atlas = load(args.after / name)
        save_gif(args.out / f"{name}_head_before_after.gif", [before, after], walk["fps"], 3)
        crops(args.out / f"{name}_head_crops.png", walk, [("before", before), ("after", after)])
        metrics[name] = {
            "walk_head": character.config["walk"].get("head"),
            "root_bob_scale": character.config["walk"]["tuning"].get("root_bob_scale", 1.0),
        }
        for label, frames, atlas in (("before", before, before_atlas), ("after", after, after_atlas)):
            metrics[name][label] = {
                "head_top_row": top_rows(atlas, character.parts["head"], walk),
                "chest_top_row": top_rows(atlas, character.parts["chest"], walk),
                "eye_px": eye_pixels(frames, walk, character),
            }
        print(f"{name}: figures written", flush=True)
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
