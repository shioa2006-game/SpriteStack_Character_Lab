"""Bake the crystal mage's idle eight directions at 48x48 and, for comparison, 64x64.

The standard CLI bakes idle, walk and attack together. The mage has no staff
walk or attack yet, so this command renders only the idle sheets with the
shared engine's loader, Renderer and render_neutral, unchanged.

- idle.png / metadata.json: the project's idle contract (48x48 cells, anchor
  (24, 40), 1.19 px per model unit) in the CLI's metadata layout, with no
  animations.
- idle-64.png / idle-64.json: the same voxel model and camera angle at 4/3 the
  pixel density (character.json "comparison_view"), for the 48 vs 64 study.
"""

import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from spritestack.bake import render_neutral, write_json
from spritestack.character import load_character
from spritestack.render import Renderer


HERE = Path(__file__).resolve().parent


def comparison_character(character):
    """Return the character with the 64 px comparison view swapped into its config."""
    config = copy.deepcopy(character.config)
    variant = config["comparison_view"]
    view = config["view"]
    view["camera"]["pixels_per_unit"] = variant["pixels_per_unit"]
    view["camera"]["base_pivot"] = variant["base_pivot"]
    view["neutral_cell"] = view["render_cell"] = variant["neutral_cell"]
    return dataclasses.replace(character, config=config)


def neutral_layout(character, renderer):
    view = character.config["view"]
    return {
        "layout": f"1 row, {len(view['directions'])} columns",
        "directions": list(view["directions"]),
        "cell": [view["neutral_cell"]] * 2,
        "anchor": renderer.anchor(view["neutral_cell"]),
    }


def bake_idle(character, out):
    renderer = Renderer(character)
    sheet, _ = render_neutral(character, renderer)
    grid = character.source_grid
    metadata = {
        "version": 3,
        "camera": character.config["view"]["camera"],
        "world_axes": {"X_positive": "anatomical left", "Y_positive": "front", "Z_positive": "up"},
        "volume_origin_xyz": grid.origin.tolist(),
        "volume_order": "Z,Y,X",
        "voxel_size_xyz": grid.spacing.tolist(),
        "neutral": neutral_layout(character, renderer),
        "parts": character.parts,
        "animations": {},
    }
    sheet.save(out / "idle.png")
    np.savez_compressed(out / "rest_part_ids.npz", parts=character.part_ids)
    write_json(out / "metadata.json", metadata)

    large = comparison_character(character)
    large_renderer = Renderer(large)
    large_sheet, _ = render_neutral(large, large_renderer)
    large_sheet.save(out / "idle-64.png")
    write_json(out / "idle-64.json", {
        "description": "Comparison sheet: the same voxel model as idle.png at 4/3 the pixel density.",
        "camera": large.config["view"]["camera"],
        "neutral": neutral_layout(large, large_renderer),
        "rgba_sha256": hashlib.sha256(large_sheet.tobytes()).hexdigest(),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    print(f"Baked idle eight directions (48 and 64 px) to {args.out}")


if __name__ == "__main__":
    main()
