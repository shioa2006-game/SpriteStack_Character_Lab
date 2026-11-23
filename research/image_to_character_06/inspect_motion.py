"""Measure ear clearance and the club arc before voxel ownership hides intersections."""

import argparse
import json
from pathlib import Path

import numpy as np

from research.verify_attack import sample
from spritestack.character import load_character
from spritestack.rig import Biped


def centers(character, mask):
    grid = character.source_grid
    return grid.origin + (np.argwhere(mask)[:, ::-1] + .5) * grid.spacing


def intersections(character, world, part, transform):
    grid = character.source_grid
    rotation, shift = transform
    cells = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
    valid = ((cells >= 0) & (cells < grid.size_xyz)).all(axis=1)
    return int(np.count_nonzero(character.part_ids[tuple(cells[valid][:, ::-1].T)] == character.parts[part]))


def inspect(character):
    rig = Biped(character)
    head = centers(character, character.part_ids == character.parts["head"])
    # Outside the cheek and skull, all head-owned voxels belong to one of the ears.
    ears = head[np.abs(head[:, 0]) > 4.75]
    club = centers(character, character.part_ids == character.parts["club"])
    materials = character.config["measurements"]["visibility"]["club"]["materials"]
    barrel = centers(character, np.isin(character.model, materials))
    arm_parts = [name for name in character.parts if name.startswith(("upper_", "fore_", "hand_"))]
    report = {"head_centers": len(head), "ear_centers": len(ears), "club_centers": len(club),
              "barrel_centers": len(barrel)}
    for mode, sequence in (("walk", ((i, *rig.pose("walk", i)) for i in range(6))),
                           ("attack", ((i, j, t) for i, _, j, t in sample(character)))):
        contacts, samples, maximum_error, lowest = {}, 0, 0., float("inf")
        arc = []
        for i, joints, transforms in sequence:
            samples += 1
            ear_world = ears @ transforms["head"][0].T + transforms["head"][1]
            head_world = head @ transforms["head"][0].T + transforms["head"][1]
            rotation, shift = transforms["club"]
            club_world = club @ rotation.T + shift
            barrel_world = barrel @ rotation.T + shift
            lowest = min(lowest, float(club_world[:, 2].min()))
            for label, points, parts in (("ear", ear_world, [*arm_parts, "club"]),
                                         ("head", head_world, [*arm_parts, "club"]),
                                         ("barrel", barrel_world, [p for p in rig.parts if p not in ("club","hand_R")])):
                for part in parts:
                    overlap = intersections(character, points, part, transforms[part])
                    if overlap:
                        contacts.setdefault(f"{label}/{part}", []).append([i, overlap])
            length = np.linalg.norm(joints["club_end"] - joints["hand_R"])
            rest_length = np.linalg.norm(rig.rest["club_end"] - rig.rest["hand_R"])
            maximum_error = max(maximum_error, abs(length - rest_length))
            if mode == "walk" or i % 12 == 0:
                arc.append({name: np.round(joints[name], 2).tolist() for name in
                            ("club_end","hand_R","pelvis","toe_R","toe_L")})
        report[mode] = {"samples": samples, "intersections": contacts, "key_joints_xyz": arc,
                        "max_grip_length_error": round(float(maximum_error), 10),
                        "minimum_club_center_z": round(lowest, 3)}
    return report


def check_bake(character, bake, quality):
    data = json.loads((bake / "measurements.json").read_bytes())
    poses = character.motions["attack"]["poses"]
    visibility = data["visibility_px_full_solo"]["attack"]
    counts = {}
    for rule in [quality["attack"], *quality["additional_attack_phases"]]:
        phase = rule["phase"]
        index = poses.index(phase) + 1
        by_direction = {d: visibility[f"{d}_{index}"][rule["feature"]][0]
                        for d in character.config["view"]["directions"]}
        if min(by_direction.values()) < rule["minimum_visible_px"]:
            raise ValueError(f"{phase} visibility: {by_direction}")
        counts[phase] = by_direction
    floor_rule = quality["attack_ground"]
    ground = [data["vol_ground"][f"attack_{i:02}"][floor_rule["feature"]]
              for i in range(len(poses))]
    if min(ground) < 0 or ground[poses.index(floor_rule["phase"])] != floor_rule["z"]:
        raise ValueError(f"club floor: {ground}")
    return {"visible_px": counts, "club_head_floor_z": ground}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, default=Path("characters/goblin_brute/character.json"))
    parser.add_argument("--bake", type=Path, help="measure visibility and impact height in an all-mode bake")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    character = load_character(args.character)
    report = inspect(character)
    if args.bake:
        quality = json.loads(args.character.with_name("quality.json").read_bytes())
        report["attack_bake"] = check_bake(character, args.bake, quality)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for mode in ("walk", "attack"):
        if report[mode]["intersections"] or report[mode]["minimum_club_center_z"] < 0:
            raise SystemExit(f"{mode}: see intersections and ground height in {args.out}")
