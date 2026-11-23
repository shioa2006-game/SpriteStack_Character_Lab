"""Rebuild the archived right-hand targets from LARK's original attack."""

import argparse
import json
from pathlib import Path

import numpy as np

from spritestack.character import load_character
from spritestack.rig import Biped, about, rotate, transform, vec


HERE = Path(__file__).resolve().parent
LARK = HERE.parent / "lark" / "character.json"


def arm_reach(rest):
    shoulder, elbow, hand = (vec(rest[f"{name}_R"]) for name in ("shoulder", "elbow", "hand"))
    # Match the shared IK solver's small reserve at full extension.
    return np.linalg.norm(elbow - shoulder) + np.linalg.norm(hand - elbow) - .035


def retarget(target=HERE / "character.json"):
    lark = load_character(LARK)
    source = Biped(lark)
    clip = json.loads((LARK.parent / lark.config["attack"]["clip"]).read_bytes())
    rest = json.loads(target.read_bytes())["rig"]["rest"]
    pivot = vec(rest["pelvis"])
    ratio = arm_reach(rest) / arm_reach(source.rest)
    for index, key in enumerate(clip["keys"]):
        if not key:
            continue
        points, _ = source.pose("attack", index)
        offset = points["hand_R"] - points["shoulder_R"]
        chest = rotate([0, 0, 1], key["yaw"]) @ rotate([1, 0, 0], -key["lean"])
        target_shoulder = transform(about(chest, pivot, pivot + vec(key["root"])),
                                    vec(rest["shoulder_R"]))
        key["hand_R"] = (target_shoulder + offset * ratio).round(9).tolist()
    return clip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, default=HERE / "character.json",
                        help="target manifest (BRAM by default, or the original MAREN retarget)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(retarget(args.character), indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
