"""Walk GIFs and before/after figures for characters that tune the shared walk.

"Before" is the shared walk as the character had it before tuning: LARK's walk
block (clip and tuning, no walk.secondary) baked on the character's own model.
"After" is a --modes walk bake with the character's own walk block, for example
the published copy. Outputs, per character:

    <name>_walk_x3.gif         eight directions side by side, three times enlarged
    <name>_walk_x1.gif         the same at native size (48 px cells)
    <name>_before_after.gif    before (top) and after (bottom), three times enlarged
    <name>_before_after.png    every frame of both, one row per direction and version
and metrics.json with the stride, the secondary-motion angles and how much of each
cloth or hair region overlaps other body parts in both versions.

    python -m research.walk.compare --after output/walk --out research/walk/results
"""

import argparse
import copy
import dataclasses
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from spritestack.bake import bake
from spritestack.character import load_character
from spritestack.rig import Biped

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("maren", "crystal_mage", "azure_ronin")
BACKGROUND = (86, 98, 92, 255)
LABEL = (232, 232, 224, 255)


def sheet_frames(folder):
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    walk = meta["animations"]["walk"]
    cell = walk["cell"][0]
    with Image.open(folder / "walk.png") as image:
        sheet = image.convert("RGBA")
    return walk, [[sheet.crop((c * cell, r * cell, (c + 1) * cell, (r + 1) * cell))
                   for c in range(walk["columns"])] for r in range(len(walk["rows"]))]


def strip(rows, frame, scale):
    """One animation frame: the eight directions of each version side by side."""
    cell = rows[0][0][0].width
    canvas = Image.new("RGBA", (8 * cell, len(rows) * cell), BACKGROUND)
    for version, frames in enumerate(rows):
        for direction in range(8):
            canvas.alpha_composite(frames[direction][frame], (direction * cell, version * cell))
    return canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)


def save_gif(path, rows, fps, scale):
    count = len(rows[0][0])
    pictures = [strip(rows, frame, scale).convert("RGB").quantize(colors=255, dither=Image.NONE)
                for frame in range(count)]
    pictures[0].save(path, save_all=True, append_images=pictures[1:], loop=0,
                     duration=round(1000 / fps), disposal=1, optimize=False)


def contact_sheet(path, before, after, directions, scale=3):
    cell = before[0][0].width
    count = len(before[0])
    gap = 4
    label_width = 70
    height = len(directions) * 2 * (cell * scale + gap)
    canvas = Image.new("RGBA", (label_width + count * cell * scale, height), (34, 34, 38, 255))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for row, direction in enumerate(directions):
        for name, frames in (("before", before), ("after", after)):
            tile = Image.new("RGBA", (count * cell, cell), BACKGROUND)
            for index in range(count):
                tile.alpha_composite(frames[row][index], (index * cell, 0))
            canvas.paste(tile.resize((tile.width * scale, cell * scale), Image.NEAREST), (label_width, y))
            draw.text((6, y + 6), f"{direction}\n{name}", fill=LABEL)
            y += cell * scale + gap
    canvas.convert("RGB").save(path, optimize=True)


def baseline(name):
    """The character with LARK's walk block, as before this tuning."""
    character = load_character(ROOT / f"characters/{name}/character.json")
    lark = json.loads((ROOT / "characters/lark/character.json").read_text(encoding="utf-8"))
    config = copy.deepcopy(character.config)
    config["walk"] = lark["walk"]
    clip = (ROOT / "characters/lark" / lark["walk"]["clip"]).resolve()
    config["walk"]["clip"] = str(clip)
    return dataclasses.replace(character, config=config)


def measure(name, after):
    from research.verify_walk import verify
    character = load_character(ROOT / f"characters/{name}/character.json")
    rig = Biped(character)
    report = verify(ROOT / f"characters/{name}/character.json", after, published=None)
    details = {r.check: r.details for r in report.results}
    walk = character.config["walk"]
    return {
        "stride_model_units_per_frame": rig.walk_clip["forward_each_frame"],
        "stance_start_y": walk["tuning"]["stance_start_y"],
        "arm_swing_scale": walk["tuning"]["arm_swing_scale"],
        "secondary_regions": [region["name"] for region in walk.get("secondary", [])],
        "secondary_angles_deg_min_max_limit": details.get("walk.secondary.motion", {}).get("angles_deg"),
        "share_inside_other_parts": details.get("walk.secondary.intrusion", {}).get("share_inside_other_parts"),
        "arm_phase_correlation": details.get("walk.arm_phase", {}).get("correlation_with_opposite_ankle"),
        "verify_walk_summary": report.counts(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--after", type=Path, required=True,
                        help="folder with one --modes walk bake per character (<folder>/<name>)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--characters", nargs="+", default=list(NAMES))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {}
    with TemporaryDirectory(prefix=".walk-before-") as temporary:
        for name in args.characters:
            before_dir = Path(temporary) / name
            before_dir.mkdir()
            bake(baseline(name), before_dir, motions=("walk",))
            walk, after = sheet_frames(args.after / name)
            _, before = sheet_frames(before_dir)
            save_gif(args.out / f"{name}_walk_x3.gif", [after], walk["fps"], 3)
            save_gif(args.out / f"{name}_walk_x1.gif", [after], walk["fps"], 1)
            save_gif(args.out / f"{name}_before_after.gif", [before, after], walk["fps"], 3)
            contact_sheet(args.out / f"{name}_before_after.png", before, after, walk["rows"])
            metrics[name] = measure(name, args.after / name)
            metrics[name]["before_stride_model_units_per_frame"] = Biped(baseline(name)).walk_clip["forward_each_frame"]
            print(f"{name}: figures written", flush=True)
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
