"""Check BRAM's Phase 3 bake, including voxel contact and sprite layout."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from experiments.bram.build_model import build
from experiments.bram.retarget_attack import retarget
from research.verify_character import face_contacts
from spritestack.character import load_character


ROOT = Path(__file__).resolve().parents[1]
BRAM = ROOT / "experiments/bram/character.json"
LARK = ROOT / "experiments/lark/character.json"
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def read(path):
    return json.loads(path.read_bytes())


def check_sprites(output, metadata):
    base = metadata["neutral"]
    assert base["directions"] == DIRECTIONS
    assert base["cell"] == [48, 48]
    assert base["anchor"] == [24, 40]
    with Image.open(output / "idle.png") as sheet:
        assert sheet.mode == "RGBA" and sheet.size == (384, 48)
        idle = [sheet.crop((i * 48, 0, (i + 1) * 48, 48)) for i in range(8)]
    assert len({frame.tobytes() for frame in idle}) == 8
    all_frames = idle.copy()
    for mode, count, cell, anchor in (("walk", 6, 48, [24, 40]), ("attack", 9, 64, [32, 48])):
        clip = metadata["animations"][mode]
        assert clip["rows"] == DIRECTIONS and clip["columns"] == count
        assert clip["cell"] == [cell, cell] and clip["anchor"] == anchor
        assert clip["loop"] == (mode == "walk")
        with Image.open(output / f"{mode}.png") as sheet:
            assert sheet.mode == "RGBA" and sheet.size == (count * cell, 8 * cell)
            for row in range(8):
                frames = [sheet.crop((i * cell, row * cell, (i + 1) * cell, (row + 1) * cell))
                          for i in range(count)]
                assert len({frame.tobytes() for frame in frames}) == (8 if mode == "attack" else 6)
                if mode == "attack":
                    guard = Image.new("RGBA", (cell, cell))
                    guard.paste(idle[row], tuple(a - b for a, b in zip(anchor, base["anchor"])))
                    assert frames[0].tobytes() == frames[-1].tobytes() == guard.tobytes()
                all_frames.extend(frames)
    walk, attack = (metadata["animations"][name] for name in ("walk", "attack"))
    assert walk["fps"] == 9
    assert attack["durations_ms"] == [75, 85, 105, 105, 45, 50, 95, 100, 140]
    for frame in all_frames:
        assert set(np.unique(np.asarray(frame)[..., 3])) == {0, 255}
        x0, y0, x1, y1 = frame.getbbox()
        assert min(x0, y0, frame.width - x1, frame.height - y1) >= 1
    print(f"{len(all_frames)} RGBA frames, eight directions, margins, anchors and timing: passed")


def components(mask):
    remaining = set(map(tuple, np.argwhere(mask).tolist()))
    sizes = []
    neighbors = [(axis, step) for axis in range(3) for step in (-1, 1)]
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            point = stack.pop()
            size += 1
            for axis, step in neighbors:
                adjacent = list(point)
                adjacent[axis] += step
                adjacent = tuple(adjacent)
                if adjacent in remaining:
                    remaining.remove(adjacent)
                    stack.append(adjacent)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def check_geometry(output, character):
    joints = read(output / "joints.json")
    rest = joints["rest"][0]
    attachments = character.config["rig"]["attachments"]
    assert attachments == {"sword": {"hand": "hand_R", "marker": "sword_tip"},
                           "shield": {"hand": "hand_L", "marker": "shield_center"}}
    grid = character.posed_grid
    max_fragment = 0
    touch_min = {item: float("inf") for item in attachments}
    soles = {"R": [], "L": []}
    with np.load(output / "posed_part_ids.npz", allow_pickle=False) as poses:
        for mode, frames in joints.items():
            for index, frame in enumerate(frames):
                ids = poses[f"{mode}_{index:02}"]
                assert set(np.unique(ids)) == {0, *character.parts.values()}, (mode, index)
                sizes = components(ids > 0)
                max_fragment = max(max_fragment, *sizes[1:], 0)
                for item, attachment in attachments.items():
                    hand, marker = attachment["hand"], attachment["marker"]
                    rest_length = np.linalg.norm(np.subtract(rest[marker], rest[hand]))
                    current_length = np.linalg.norm(np.subtract(frame[marker], frame[hand]))
                    assert abs(rest_length - current_length) < 1e-6, (mode, index, item)
                    gear = ids == character.parts[item]
                    contacts = face_contacts(gear, ids == character.parts[hand])
                    assert contacts > 0, (mode, index, item, hand)
                    touch_min[item] = min(touch_min[item], contacts)
                    if mode == "rest":
                        x = grid.origin[0] + (np.where(gear)[2].mean() + .5) * grid.spacing[0]
                        side = -1 if hand == "hand_R" else 1
                        assert x * side > 0
                if mode == "walk":
                    for side in soles:
                        layer = np.where(ids == character.parts["boot_" + side])[0].min()
                        soles[side].append(float(grid.origin[2] + layer * grid.spacing[2]))
    print(f"All parts present in 16 poses; minimum face contacts with the configured hands: {touch_min}")
    print(f"Largest fragment outside the main face-connected component: {max_fragment} voxels")
    assert max_fragment <= 2

    clip = character.motions["walk"]
    for side, stance in clip["contact"]["inclusive_stance_cyclic"].items():
        marker = clip["contact"]["sole_markers"][side]
        step = clip["forward_each_frame"]
        world = np.array([joints["walk"][i][marker] for i in stance])
        world[:, 1] += step * np.arange(len(stance))
        assert np.max(np.linalg.norm(world - world[0], axis=1)) < 1e-6
        assert all(abs(z) < 1e-6 for z in world[:, 2])
        assert all(z == 0 if i in stance else z > 0 for i, z in enumerate(soles[side]))
    print(f"Walk contact markers have zero drift at frame boundaries; boot sole z: {soles}")

    normalized = []
    for index, key in enumerate(character.motions["attack"]["keys"]):
        if key:
            normalized.append(np.linalg.norm(np.subtract(joints["attack"][index]["hand_R"], key["hand_R"])))
    assert max(normalized) < 1e-6
    print(f"Maximum right-hand IK target error after retargeting: {max(normalized):.3g} model units")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    character = load_character(BRAM)
    lark = load_character(LARK)
    material_ids, part_ids = build(character.config)
    assert np.array_equal(material_ids, character.model)
    assert np.array_equal(part_ids, character.part_ids)
    assert character.motions["walk"] == lark.motions["walk"]
    assert character.motions["attack"] == retarget()
    source = lark.motions["attack"]
    derived = character.motions["attack"]
    assert {k: v for k, v in source.items() if k != "keys"} == {
        k: v for k, v in derived.items() if k != "keys"}
    for a, b in zip(source["keys"], derived["keys"], strict=True):
        assert {k: v for k, v in a.items() if k != "hand_R"} == {
            k: v for k, v in b.items() if k != "hand_R"}
    check_sprites(args.output, read(args.output / "metadata.json"))
    check_geometry(args.output, character)


if __name__ == "__main__":
    main()
