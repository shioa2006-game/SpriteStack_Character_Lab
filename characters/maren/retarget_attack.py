"""Derive MAREN's right-hand attack targets from LARK's evaluated attack.

This applies BRAM's Phase 3 rule unchanged: keep LARK's shoulder-to-hand
direction for every key and scale it by the ratio of arm reach.
"""

import argparse
import json
from pathlib import Path

from characters.bram.retarget_attack import arm_reach
from spritestack.character import load_character
from spritestack.rig import Biped, about, rotate, transform, vec


HERE = Path(__file__).resolve().parent
LARK = HERE.parent / "lark" / "character.json"


def retarget():
    lark = load_character(LARK)
    source = Biped(lark)
    clip = json.loads((LARK.parent / lark.config["attack"]["clip"]).read_bytes())
    rest = json.loads((HERE / "character.json").read_bytes())["rig"]["rest"]
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(retarget(), indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
