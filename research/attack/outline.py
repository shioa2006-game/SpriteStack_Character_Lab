"""Compare attack frames with the projected model blade and count isolated eye pixels."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from research.sword.compare import Blade, NAMES
from spritestack.character import load_character
from spritestack.render import Renderer


def measure(manifest, output):
    character = load_character(manifest)
    renderer = Renderer(character)
    view = character.config["view"]
    count = len(character.motions["attack"]["keys"])
    cell = character.config["attack"]["cell"]
    names = [m["name"] for m in character.config["model"]["palette"]]
    eye_id = names.index("eyes") + 1
    blade = Blade(manifest.parent.name, mode="attack") if manifest.parent.name in NAMES else None
    sheet = np.asarray(Image.open(output / "attack.png"))
    owners = np.asarray(Image.open(output / "attack_part_ids.png"))
    eyes = {direction: [] for direction in view["directions"]}
    metrics = {}
    with np.load(output / "posed_slices.npz") as volumes, np.load(output / "posed_part_ids.npz") as parts:
        for i in range(count):
            key = f"attack_{i:02}"
            ids = parts[key]
            head = np.where(ids == character.parts["head"], volumes[key], 0)
            for row, (direction, yaw) in enumerate(view["directions"].items()):
                visible = renderer.render(head, ids, character.posed_grid, yaw, cell, view["posed_rays"])
                eyes[direction].append(int((visible == eye_id).sum()))
                if blade and character.motions["attack"]["keys"][i]:
                    tile = np.s_[row * cell:(row + 1) * cell, i * cell:(i + 1) * cell]
                    metrics[f"{direction}_{i + 1}"] = blade.frame(i, yaw, sheet[tile][..., :3], owners[tile])
    return {"eyes": eyes, "blade": metrics}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(measure(args.character, args.out), indent=2))
