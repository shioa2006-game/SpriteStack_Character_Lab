"""Verify a baked one-shot attack and optionally export an eight-direction GIF."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.overhead.analyze import guard_key
from research.verify_bram import face_contacts
from spritestack.bake import check_attachment, require_margin
from spritestack.character import load_character
from spritestack.rig import Biped
from spritestack.secondary import Secondary


def sample(character):
    rig = Biped(character)
    clip = character.motions["attack"]
    tuning = character.config["attack"]["tuning"]
    neutral = guard_key(rig)
    if any("aim" in key for key in clip["keys"]):
        neutral["aim"] = neutral.pop("blade")
        neutral["support_delta"] = neutral.pop("shield_delta")
        neutral["support_pitch"] = tuning["support_wrist_pitch"]
    keys = [{name: key.get(name, value) for name, value in neutral.items()} for key in clip["keys"]]
    sequence = []
    for start, end in zip(keys, keys[1:]):
        for fraction in np.arange(12) / 12:
            sequence.append({name: np.asarray(value) * (1 - fraction) + np.asarray(end[name]) * fraction
                             for name, value in start.items()})
    sequence.append(keys[-1])
    trial = Biped(replace(character, motions={**character.motions, "attack": {**clip, "keys": sequence}}))
    for i, key in enumerate(sequence):
        joints, transforms = rig.pose("attack", i // 12) if i % 12 == 0 else trial.pose("attack", i)
        yield i, key, joints, transforms


def check_path(character, feature):
    rig = Biped(character)
    tuning = character.config["attack"]["tuning"]
    # Check the working end against the other body parts before overlap ownership is resolved.
    visibility = character.config["measurements"]["visibility"]
    item = visibility[feature]
    main = item["part"]
    grid = character.source_grid
    coords = np.argwhere(np.isin(character.model, item["materials"]) &
                         (character.part_ids == character.parts[main]))[:, ::-1]
    centers = grid.origin + (coords + .5) * grid.spacing
    for i, key, joints, transforms in sample(character):
        check_attachment(rig, joints, transforms)
        for side in ("R", "L"):
            ankle = rig.rest["ankle_" + side].copy()
            if side == tuning["step_side"]:
                ankle += [0, key["front_step"], key["front_lift"]]
            assert np.linalg.norm(joints["ankle_" + side] - ankle) < 1e-6, (i, side, "ankle")
        off = key.get("support_delta", key.get("shield_delta"))
        left = rig.rest["hand_L"] + key["root"] + off + [
            0, key["yaw"] * tuning["support_yaw_offset"], tuning["support_hand_lift"]]
        for name, target in (("hand_R", key["hand_R"]), ("hand_L", left)):
            assert np.linalg.norm(joints[name] - target) < 1e-6, (i, name, "unreachable")
        rotation, shift = transforms[main]
        world = centers @ rotation.T + shift
        for part, pid in character.parts.items():
            if part in (main, "hand_R"):
                continue
            rotation, shift = transforms[part]
            xyz = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
            valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=1)
            assert not np.any(character.part_ids[tuple(xyz[valid][:, ::-1].T)] == pid), (i, main, part)


def check_cloth(character, main):
    rig = Biped(character)
    clip = character.motions["attack"]
    cloth = Secondary(character, clip, rig.rest, mode="attack")
    frames = [rig.pose("attack", i)[1] for i in range(len(clip["keys"]))]
    grid = character.source_grid
    for region in cloth.regions:
        swings = cloth._pendulum(region, frames) if region["kind"] == "pendulum" else [None] * len(frames)
        for i, (transforms, swing) in enumerate(zip(frames, swings)):
            cells, _ = cloth.posed_cells(character, region, transforms, swing)
            world = character.posed_grid.origin + (cells + .5) * character.posed_grid.spacing
            rotation, shift = transforms[main]
            xyz = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
            valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=1)
            assert not np.any(character.part_ids[tuple(xyz[valid][:, ::-1].T)] == character.parts[main]), (
                i, main, region["name"])


def verify(character, out, gif, rules):
    clip = character.motions["attack"]
    layout = json.loads((out / "metadata.json").read_bytes())["animations"]["attack"]
    sheet = Image.open(out / "attack.png")
    count = len(clip["keys"])
    cell = character.config["attack"]["cell"]
    dirs = "S SW W NW N NE E SE".split()
    assert layout["rows"] == dirs and layout["columns"] == count and layout["cell"] == [cell, cell]
    assert layout["durations_ms"] == clip["durations_ms"] and not layout["loop"]
    assert sheet.size == (count * cell, 8 * cell) and sheet.mode == "RGBA"
    assert hashlib.sha256(sheet.tobytes()).hexdigest() == layout["rgba_sha256"]
    feature = rules["feature"]
    check_path(character, feature)
    if character.config["attack"].get("follow_cloth"):
        check_cloth(character, character.config["measurements"]["visibility"][feature]["part"])
    measurements = json.loads((out / "measurements.json").read_bytes())
    phase = clip["poses"].index(rules["phase"]) + 1
    seen = measurements["visibility_px_full_solo"]["attack"]
    minimum = min(seen[f"{d}_{phase}"][feature][0] for d in dirs)
    assert minimum >= rules["minimum_visible_px"], (feature, minimum)
    print(f"{rules['phase']}: {feature} visible in at least {minimum} pixels in every direction")
    idle = Image.open(out / "idle.png")
    neutral = idle.height
    pad = (cell - neutral) // 2
    assert layout["anchor"] == [p + pad for p in character.config["view"]["camera"]["base_pivot"]]
    previews = []
    contacts = {}
    with np.load(out / "posed_part_ids.npz") as volumes:
        for col in range(count):
            ids = volumes[f"attack_{col:02}"]
            support = "boot_L" if character.config["attack"]["tuning"]["step_side"] == "R" else "boot_R"
            bottom = np.where((ids == character.parts[support]).any(axis=(1, 2)))[0].min()
            assert abs(character.posed_grid.origin[2] + bottom * character.posed_grid.spacing[2]) < 1e-6
            assert set(character.parts.values()) <= set(np.unique(ids)), ("missing part", col)
            for name, att in character.config["rig"]["attachments"].items():
                faces = face_contacts(ids == character.parts[name], ids == character.parts[att["hand"]])
                assert faces > 0, (name, col, "lost grip")
                contacts[name] = min(contacts.get(name, faces), faces)
            panel = Image.new("RGB", (cell * 4, (cell + 14) * 2), "#303640")
            for row, direction in enumerate(dirs):
                frame = sheet.crop((col * cell, row * cell, (col+1)*cell, (row+1)*cell))
                require_margin(frame, f"{direction} {col}")
                if col in (0, count-1):
                    guard = Image.new("RGBA", frame.size)
                    guard.paste(idle.crop((row*neutral, 0, (row+1)*neutral, neutral)), (pad, pad))
                    assert frame.tobytes() == guard.tobytes()
                x, y = row % 4 * cell, row // 4 * (cell + 14)
                panel.paste(frame, (x, y+14), frame)
                ImageDraw.Draw(panel).text((x+3, y), direction, fill="white")
            previews.append(panel.resize((panel.width*2, panel.height*2), Image.Resampling.NEAREST))
    if gif:
        previews[0].save(gif, save_all=True, append_images=previews[1:], duration=clip["durations_ms"],
                         loop=0, disposal=2)
    print(f"{count} frames x 8 directions; {(count-1)*12+1} sampled poses; minimum grip contacts {contacts}")


def check_published(output, published):
    layout = json.loads((output / "metadata.json").read_bytes())["animations"]["attack"]
    assert json.loads((published / "attack.json").read_bytes()) == {"animations": {"attack": layout}}
    with Image.open(published / "attack.png") as sheet:
        assert sheet.mode == "RGBA" and sheet.size == (
            layout["columns"] * layout["cell"][0], len(layout["rows"]) * layout["cell"][1])
        assert hashlib.sha256(sheet.tobytes()).hexdigest() == layout["rgba_sha256"]
    with Image.open(published / "attack.gif") as preview:
        assert preview.n_frames == layout["columns"]
        for i, duration in enumerate(layout["durations_ms"]):
            preview.seek(i)
            assert abs(preview.info["duration"] - duration) < 10  # GIF delays use 10 ms ticks.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gif", type=Path)
    parser.add_argument("--published", type=Path, help="compare the published attack PNG, JSON and GIF timing")
    args = parser.parse_args()
    rules = json.loads(args.character.with_name("quality.json").read_bytes())["attack"]
    verify(load_character(args.character), args.out, args.gif, rules)
    if args.published:
        check_published(args.out, args.published)
