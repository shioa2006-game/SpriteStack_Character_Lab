"""Inspect the free ends of the sash and hair and the isolated katana at sprite scale."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from research.verify_character import components
from research.verify_attack import sample, verify
from spritestack.character import load_character
from spritestack.render import Renderer, fine_parts, reslice
from spritestack.rig import Biped
from spritestack.secondary import Secondary


def source_indices(grid, world, pose):
    rotation, shift = pose
    indices = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
    inside = ((indices >= 0) & (indices < grid.size_xyz)).all(axis=1)
    return tuple(indices[inside, ::-1].T)


def drapery(character, rig, motion, lacquer):
    clip = rig.walk_clip if motion == "walk" else character.motions[motion]
    secondary = Secondary(character, clip, rig.rest, mode=motion)
    frames = [rig.pose(motion, i)[1] for i in range(len(clip["poses"]))]
    grid = character.source_grid
    result = {}
    for region in secondary.regions:
        swings = (secondary._pendulum(region, frames) if region["kind"] == "pendulum"
                  else [None] * len(frames))
        # Use the half with the highest motion weights, away from sewn and tied roots.
        indices = np.flatnonzero(region["weights"] >= .5 * region["weights"].max())
        overlaps = []
        for poses, swing in zip(frames, swings):
            forward, _ = secondary._mapping(region, poses, swing)
            world = forward(region["centers"][indices], indices)
            hits = {}
            for name, part_id in character.parts.items():
                if name != region["part"]:
                    occupied = character.part_ids[source_indices(grid, world, poses[name])] == part_id
                    if occupied.any():
                        hits[name] = int(occupied.sum())
            # The scabbard and the two sashes share the pelvis part.
            occupied = character.model[source_indices(grid, world, poses["pelvis"])] == lacquer
            if occupied.any():
                hits["scabbard lacquer"] = int(occupied.sum())
            overlaps.append(hits)
        result[region["name"]] = {"free_centers": len(indices), "overlap_by_frame": overlaps}
    return result


def scabbard(character, rig, lacquer):
    grid = character.source_grid
    centers = grid.origin + (np.argwhere(character.model == lacquer)[:, ::-1] + .5) * grid.spacing
    frames = {
        "walk": [rig.pose("walk", i)[1] for i in range(len(rig.walk_clip["poses"]))],
        "attack": [poses for _, _, _, poses in sample(character)],
    }
    result = {}
    for motion, sequence in frames.items():
        overlaps = []
        for index, poses in enumerate(sequence):
            rotation, shift = poses["pelvis"]
            world = centers @ rotation.T + shift
            for name, part_id in character.parts.items():
                if name == "pelvis":
                    continue
                occupied = character.part_ids[source_indices(grid, world, poses[name])] == part_id
                if occupied.any():
                    overlaps.append([index, name, int(occupied.sum())])
        result[motion] = {"centers": len(centers), "poses": len(sequence), "overlaps": overlaps}
    return result


def blade(character, rig, renderer, motion):
    """Count 8-connected steel pixels in the isolated weapon before body occlusion."""
    view = character.config["view"]
    feature = character.config["measurements"]["visibility"]["blade"]
    part = feature["part"]
    weapon = replace(character, parts={part: character.parts[part]})
    count = 1 if motion == "idle" else len(character.motions[motion]["poses"])
    failures = []
    for frame in range(count):
        guard = motion == "idle" or (motion == "attack" and not character.motions[motion]["keys"][frame])
        if guard:
            volume = np.where(character.part_ids == character.parts[part], character.model, 0)
            parts, grid = character.part_ids, character.source_grid
            cell, rays, fine = view["neutral_cell"], view["neutral_rays"], None
        else:
            volume, parts = reslice(weapon, rig.pose(motion, frame)[1])
            grid = character.posed_grid
            cell, rays, fine = view["render_cell"], view["posed_rays"], fine_parts(character, motion)
        for direction, yaw in view["directions"].items():
            materials = renderer.render(volume, parts, grid, yaw, cell, rays, fine=fine)
            pieces = components(np.isin(materials, feature["materials"])[None])
            if len(pieces) != 1:
                failures.append([direction, frame + 1, [int(piece.sum()) for piece in pieces]])
    return {"cells_checked": count * len(view["directions"]), "disconnected_or_missing": failures}


def inspect(bake=None):
    root = Path(__file__).resolve().parents[2]
    folder = root / "characters/crimson_blade"
    character = load_character(folder / "character.json")
    rig, renderer = Biped(character), Renderer(character)
    names = [item["name"] for item in character.config["model"]["palette"]]
    lacquer = names.index("sheath") + 1
    if bake is not None:
        quality = json.loads((folder / "quality.json").read_bytes())
        for rule in quality["additional_attack_phases"]:
            verify(character, bake, None, rule)
    return {
        "drapery": {mode: drapery(character, rig, mode, lacquer) for mode in ("walk", "attack")},
        "scabbard_lacquer": scabbard(character, rig, lacquer),
        "isolated_blade": {mode: blade(character, rig, renderer, mode) for mode in ("idle", "walk", "attack")},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bake", type=Path, help="all-mode bake to check the two additional slash phases")
    print(json.dumps(inspect(parser.parse_args().bake), indent=2))
