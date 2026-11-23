"""Check the knight's shield volume against the body between exported attack keys."""

from pathlib import Path

import numpy as np

from research.verify_attack import check_cloth, sample
from spritestack.character import load_character
from spritestack.rig import Biped


def check_shield(character, poses):
    grid = character.source_grid
    indices = np.argwhere(character.part_ids == character.parts["shield"])[:, ::-1]
    centers = grid.origin + (indices + .5) * grid.spacing
    count = 0
    for count, transforms in enumerate(poses, 1):
        rotation, offset = transforms["shield"]
        world = centers @ rotation.T + offset
        for name, part_id in character.parts.items():
            if name in ("shield", "hand_L"):
                continue
            rotation, offset = transforms[name]
            local = (world - offset) @ rotation
            xyz = np.floor((local - grid.origin) / grid.spacing).astype(int)
            valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=1)
            hits = character.part_ids[tuple(xyz[valid][:, ::-1].T)] == part_id
            if hits.any():
                raise ValueError(f"pose {count}: shield intersects {name} at {hits.sum()} centers")
    return count


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    knight = load_character(root / "characters/fleur_knight/character.json")
    rig = Biped(knight)
    walk_count = len(knight.motions["walk"]["poses"])
    walk = check_shield(knight, (rig.pose("walk", i)[1] for i in range(walk_count)))
    attack = check_shield(knight, (pose[3] for pose in sample(knight)))
    check_cloth(knight, "shield")
    print(f"No shield interference in {walk} walk keys, {attack} attack samples or posed attack cloth.")
