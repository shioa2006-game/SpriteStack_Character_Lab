"""Bake MAREN's idle eight directions with the shared engine's static renderer.

The standard CLI bakes idle, walk and attack together and writes nothing unless
every frame fits its cell. MAREN's retargeted overhead attack exceeds the 64 px
attack cell (see research/IMAGE_TO_CHARACTER_01.md), so this command renders
only the idle sheet. It reuses spritestack's loader, Renderer and
render_neutral unchanged and writes the CLI's metadata layout with no animations.
"""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from spritestack.bake import render_neutral, write_json
from spritestack.character import load_character
from spritestack.render import Renderer


HERE = Path(__file__).resolve().parent


def bake_idle(character, out):
    view = character.config["view"]
    renderer = Renderer(character)
    sheet, _ = render_neutral(character, renderer)
    grid = character.source_grid
    metadata = {
        "version": 3,
        "camera": view["camera"],
        "world_axes": {"X_positive": "anatomical left", "Y_positive": "front", "Z_positive": "up"},
        "volume_origin_xyz": grid.origin.tolist(),
        "volume_order": "Z,Y,X",
        "voxel_size_xyz": grid.spacing.tolist(),
        "neutral": {
            "layout": f"1 row, {len(view['directions'])} columns",
            "directions": list(view["directions"]),
            "cell": [view["neutral_cell"]] * 2,
            "anchor": renderer.anchor(view["neutral_cell"]),
        },
        "parts": character.parts,
        "animations": {},
    }
    sheet.save(out / "idle.png")
    np.savez_compressed(out / "rest_part_ids.npz", parts=character.part_ids)
    write_json(out / "metadata.json", metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, default=HERE / "character.json")
    parser.add_argument("--out", required=True, type=Path, help="new output directory")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("--out must be a new directory to preserve existing files")
    character = load_character(args.character)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".spritestack-", dir=out.parent) as workspace:
        staging = Path(workspace) / "output"
        staging.mkdir()
        bake_idle(character, staging)
        staging.rename(out)
    print(f"Baked idle eight directions to {args.out}")


if __name__ == "__main__":
    main()
