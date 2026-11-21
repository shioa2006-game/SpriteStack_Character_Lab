"""Fit one authored overhead clip to the two existing biped proportions."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from characters.bram.retarget_attack import arm_reach
from spritestack.character import check_motion_lengths, load_character, read_json
from spritestack.rig import about, rotate, transform, unit, vec


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFESTS = {name: ROOT / "characters" / name / "character.json" for name in ("lark", "bram")}


def leg_length(rest):
    hip, knee, ankle = (vec(rest[name]) for name in ("hip_R", "knee_R", "ankle_R"))
    return np.linalg.norm(knee - hip) + np.linalg.norm(ankle - knee)


def shoulder(rest, key, side):
    pivot = vec(rest["pelvis"])
    rotation = rotate([0, 0, 1], key["yaw"]) @ rotate([1, 0, 0], -key["lean"])
    return transform(about(rotation, pivot, pivot + vec(key["root"])), vec(rest[f"shoulder_{side}"]))


def overhead(character, source):
    config = deepcopy(character.config)
    rest = config["rig"]["rest"]
    tip_axis = vec(rest["sword_tip"]) - vec(rest["hand_R"])
    tuning = config["attack"]["tuning"]
    tuning["weapon_axis"] = tip_axis.tolist()
    scale = leg_length(rest) / leg_length(read_json(MANIFESTS["lark"])["rig"]["rest"])
    reach = arm_reach(rest)
    support_length = (np.linalg.norm(vec(rest["elbow_L"]) - vec(rest["shoulder_L"]))
                      + np.linalg.norm(vec(rest["hand_L"]) - vec(rest["elbow_L"])))
    clip = {
        "poses": source["poses"],
        "durations_ms": source["durations_ms"],
        "fps": character.motions["attack"]["fps"],
        "keys": [],
    }
    for pose in source["keys"]:
        if not pose:
            clip["keys"].append({})
            continue
        key = {
            "root": (vec(pose["root"]) * scale).tolist(),
            "yaw": pose["yaw"],
            "lean": pose["lean"],
            "blade": unit(vec(pose["blade"])).tolist(),
            "front_step": pose["front_step"] * scale,
            "front_lift": pose["front_lift"] * scale,
            "elbow_pole_R": (vec(pose["pole"]) * scale).tolist(),
            "shield_delta": (vec(pose["shield_delta"]) * scale).tolist(),
        }
        if "wrist_roll" in pose:
            key["wrist_roll"] = pose["wrist_roll"]
        # Same shoulder-relative reach normalization as the Phase 3 retarget.
        key["hand_R"] = (shoulder(rest, key, "R") + vec(pose["hand"]) * reach).tolist()
        support_base = (vec(rest["hand_L"]) + key["root"]
                        + [0, key["yaw"] * tuning["support_yaw_offset"], tuning["support_hand_lift"]])
        support_shoulder = shoulder(rest, key, "L")
        support_offset = support_base + key["shield_delta"] - support_shoulder
        if np.linalg.norm(support_offset) > .94 * support_length:
            # Leave room to bend the shorter shield arm as the chest untwists.
            key["shield_delta"] = (support_shoulder + unit(support_offset) * .94 * support_length
                                   - support_base).tolist()
        clip["keys"].append(key)
    motions = {**character.motions, "attack": clip}
    check_motion_lengths(motions)
    return replace(character, config=config, motions=motions)


def character_for(name, source=None):
    character = load_character(MANIFESTS[name])
    return overhead(character, source if source is not None else read_json(HERE / "clip.json"))
