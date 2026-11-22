"""Measure the attack trajectory and check sampled poses with the original voxel models."""

from dataclasses import replace
import math

import numpy as np

from spritestack.bake import check_attachment
from spritestack.rig import Biped, unit, vec


SUBSTEPS = 12


def angle(a, b):
    return math.degrees(math.acos(np.clip(unit(a) @ unit(b), -1, 1)))


def guard_key(rig):
    rest = rig.rest
    tuning = rig.config["attack"]["tuning"]
    return {
        "root": [0, 0, 0], "yaw": 0, "lean": 0, "front_step": 0, "front_lift": 0, "wrist_roll": 0,
        "front_outward": 0,
        "hand_R": rest["hand_R"],
        "elbow_pole_R": rest["elbow_R"] - rest["shoulder_R"],
        "blade": unit(vec(tuning["weapon_axis"])),
        "shield_delta": [0, 0, -tuning["support_hand_lift"]],
    }


def sampled_poses(character, substeps=SUBSTEPS):
    clip = character.motions["attack"]
    rig = Biped(character)
    keys = [{**guard_key(rig), **key} for key in clip["keys"]]
    with_intermediates = []
    for start, end in zip(keys, keys[1:]):
        for step in range(substeps):
            blend = step / substeps
            key = {name: (1 - blend) * vec(start[name]) + blend * vec(end[name]) for name in start}
            with_intermediates.append(key)
    with_intermediates.append(keys[-1])
    trial = Biped(replace(character, motions={**character.motions,
                                              "attack": {**clip, "keys": with_intermediates}}))
    for index, key in enumerate(with_intermediates):
        key_index, step = divmod(index, substeps)
        points, transforms = (rig.pose("attack", key_index) if step == 0
                              else trial.pose("attack", index))
        yield key_index, step, key, points, transforms


def blade_samples(character):
    materials = character.config["measurements"]["visibility"]["blade"]["materials"]
    coords = np.argwhere(np.isin(character.model, materials))[:, ::-1]
    grid = character.source_grid
    return grid.origin + (coords + .5) * grid.spacing


def blade_intersections(character, transforms, centers):
    grid = character.source_grid
    rotation, translation = transforms["sword"]
    posed = centers @ rotation.T + translation
    collisions = {}
    for part, part_id in character.parts.items():
        if part in ("sword", "hand_R"):
            continue
        matrix, offset = transforms[part]
        xyz = np.floor(((posed - offset) @ matrix - grid.origin) / grid.spacing).astype(int)
        valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=-1)
        overlap = int(np.count_nonzero(character.part_ids[tuple(xyz[valid][:, ::-1].T)] == part_id))
        if overlap:
            collisions[part] = overlap
    return collisions


def measure(character):
    rig = Biped(character)
    curve = []
    collisions = []
    arm_errors = []
    support_errors = []
    ankle_errors = []
    poles = []
    centers = blade_samples(character)
    for frame, step, key, points, transforms in sampled_poses(character):
        check_attachment(rig, points, transforms)
        assert all(np.array_equal(a, b) for gear, hand in (("sword", "hand_R"), ("shield", "hand_L"))
                   for a, b in zip(transforms[gear], transforms[hand]))
        overlap = blade_intersections(character, transforms, centers)
        if overlap:
            collisions.append([frame + 1, step, overlap])
        right = points["hand_R"] - points["shoulder_R"]
        elbow = points["elbow_R"] - points["shoulder_R"]
        pole = elbow - unit(right) * (elbow @ unit(right))
        poles.append(unit(pole))
        blade = points["sword_tip"] - points["hand_R"]
        arm_errors.append(float(np.linalg.norm(points["hand_R"] - key["hand_R"])))
        tuning = rig.config["attack"]["tuning"]
        left_target = (rig.rest["hand_L"] + key["root"] + key["shield_delta"]
                       + [0, float(key["yaw"]) * tuning["support_yaw_offset"], tuning["support_hand_lift"]])
        support_errors.append(float(np.linalg.norm(points["hand_L"] - left_target)))
        step_target = rig.rest["ankle_R"] + [-float(key["front_outward"]), float(key["front_step"]),
                                              float(key["front_lift"])]
        ankle_errors.append(float(max(np.linalg.norm(points["ankle_R"] - step_target),
                                      np.linalg.norm(points["ankle_L"] - rig.rest["ankle_L"]))))
        curve.append({
            "hand": points["hand_R"].tolist(), "tip": points["sword_tip"].tolist(),
            "blade": unit(blade).tolist(),
            "body_yaw": float(key["yaw"]), "hip_yaw": float(key["yaw"]) * tuning["hip_yaw_scale"],
            "lean": float(key["lean"]), "step": float(key["front_step"]), "lift": float(key["front_lift"]),
            "toe_left_z": float(points["toe_L"][2]), "toe_right_z": float(points["toe_R"][2]),
            "wrist_angle": math.degrees(math.acos(np.clip((np.trace(transforms["hand_R"][0]) - 1) / 2, -1, 1))),
            "upper_arm_angle": angle(rig.rest["elbow_R"] - rig.rest["shoulder_R"], elbow),
            "elbow_angle": angle(-elbow, points["hand_R"] - points["elbow_R"]),
        })
    return {
        "curve": curve,
        "keys": curve[::SUBSTEPS],
        "blade_samples": len(centers),
        "collisions": collisions,
        "right_hand_error": max(arm_errors),
        "left_hand_error": max(support_errors),
        "ankle_error": max(ankle_errors),
        "max_blade_key_angle": max(angle(a["blade"], b["blade"])
                                   for a, b in zip(curve[::SUBSTEPS], curve[SUBSTEPS::SUBSTEPS])),
        "max_bend_plane_step": max(angle(a, b) for a, b in zip(poles, poles[1:])),
    }
