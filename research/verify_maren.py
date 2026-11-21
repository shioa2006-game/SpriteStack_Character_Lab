"""Check MAREN's model sources and idle bake: rebuild, layout, margins, handedness, published copy."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from characters.maren.build_model import build
from characters.maren.retarget_attack import retarget
from spritestack.character import load_character
from spritestack.render import Renderer, normals


ROOT = Path(__file__).resolve().parents[1]
MAREN = ROOT / "characters/maren/character.json"
LARK = ROOT / "characters/lark/character.json"
PUBLISHED = ROOT / "docs/assets/maren"
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def read(path):
    return json.loads(path.read_bytes())


def check_sources(character):
    material_ids, part_ids = build(character.config)
    assert np.array_equal(material_ids, character.model), "materials.npz differs from build_model.py"
    assert np.array_equal(part_ids, character.part_ids), "part_ids.npz differs from build_model.py"
    used = set(np.unique(character.model[character.model > 0]).tolist())
    assert used == set(range(1, len(character.config["model"]["palette"]) + 1)), "unused palette entry"
    assert character.motions["walk"] == load_character(LARK).motions["walk"]
    assert character.motions["attack"] == retarget()
    provenance = read(ROOT / "characters/maren/palette_provenance.json")["materials"]
    assert set(provenance) == {item["name"] for item in character.config["model"]["palette"]}
    print(f"Model NPZ rebuilt from source ({len(used)} materials, {len(character.parts)} parts); "
          "walk clip shared with LARK; attack clip matches the retarget rule")


def check_handedness(character):
    grid = character.source_grid
    for part, expected in (("sword", -1), ("shield", 1)):
        voxels = np.argwhere(character.part_ids == character.parts[part])
        x = grid.origin[0] + (voxels[:, 2].mean() + .5) * grid.spacing[0]
        assert np.sign(x) == expected, part
    attachments = character.config["rig"]["attachments"]
    assert attachments["sword"]["hand"] == "hand_R" and attachments["shield"]["hand"] == "hand_L"
    print("Sword on the anatomical right hand (x < 0), shield on the left hand (x > 0)")


def check_sheet(output, character):
    metadata = read(output / "metadata.json")
    neutral = metadata["neutral"]
    assert neutral["directions"] == DIRECTIONS
    assert neutral["cell"] == [48, 48] and neutral["anchor"] == [24, 40]
    assert metadata["animations"] == {}
    with Image.open(output / "idle.png") as sheet:
        assert sheet.mode == "RGBA" and sheet.size == (384, 48)
        frames = [sheet.crop((i * 48, 0, (i + 1) * 48, 48)) for i in range(8)]
    assert len({frame.tobytes() for frame in frames}) == 8
    renderer = Renderer(character)
    view = character.config["view"]
    surface = normals(character.model, character.source_grid)
    visible = {}
    for direction, frame in zip(DIRECTIONS, frames):
        assert set(np.unique(np.asarray(frame)[..., 3])) == {0, 255}
        x0, y0, x1, y1 = frame.getbbox()
        assert min(x0, y0, 48 - x1, 48 - y1) >= 1, direction
        _, _, parts = renderer.render(character.model, character.part_ids, character.source_grid,
                                      view["directions"][direction], 48, view["neutral_rays"], surface)
        visible[direction] = {name: int((parts == character.parts[name]).sum())
                              for name in ("head", "sword", "shield")}
    for direction in ("S", "SW", "SE", "N"):
        assert all(count > 0 for count in visible[direction].values()), direction
    print("Idle 384x48 RGBA, eight distinct frames, S..SE order, anchor (24, 40), binary alpha, "
          "1 px margins: passed")
    print("Visible px of head/sword/shield per direction:", visible)
    return metadata


def check_published(output, metadata):
    with Image.open(output / "idle.png") as baked, Image.open(PUBLISHED / "idle.png") as published:
        same = baked.convert("RGBA").tobytes() == published.convert("RGBA").tobytes()
    assert same, "docs/assets/maren/idle.png differs from the bake"
    assert read(PUBLISHED / "metadata.json") == metadata, "published metadata differs from the bake"
    print("Published gallery idle PNG and metadata match the bake (decoded RGBA)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="folder written by characters.maren.bake_idle")
    args = parser.parse_args()
    character = load_character(MAREN)
    check_sources(character)
    check_handedness(character)
    metadata = check_sheet(args.output, character)
    check_published(args.output, metadata)


if __name__ == "__main__":
    main()
