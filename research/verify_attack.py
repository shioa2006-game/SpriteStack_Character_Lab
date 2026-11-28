"""Verify a baked one-shot attack and optionally export an eight-direction GIF."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.overhead.analyze import guard_key
from research.verify_character import face_contacts
from research.verify_walk import frames_of
from research.walk.compare import strip
from spritestack.bake import check_attachment, require_margin
from spritestack.character import load_character
from spritestack.render import reslice
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


def check_path(character, feature, path_materials=None):
    rig = Biped(character)
    tuning = character.config["attack"]["tuning"]
    # Check the working end against the other body parts before overlap ownership is resolved.
    visibility = character.config["measurements"]["visibility"]
    item = visibility[feature]
    main = item["part"]
    side = tuning["main_hand_side"]
    main_hand = "hand_" + side
    support_hand = "hand_L" if side == "R" else "hand_R"
    assert rig.attachments[main]["hand"] == main_hand
    grid = character.source_grid
    coords = np.argwhere(np.isin(character.model, path_materials or item["materials"]) &
                         (character.part_ids == character.parts[main]))[:, ::-1]
    centers = grid.origin + (coords + .5) * grid.spacing
    for i, key, joints, transforms in sample(character):
        check_attachment(rig, joints, transforms)
        for side in ("R", "L"):
            ankle = rig.rest["ankle_" + side].copy()
            if side == tuning["step_side"]:
                outward = -key["front_outward"] if side == "R" else key["front_outward"]
                ankle += [outward, key["front_step"], key["front_lift"]]
            assert np.linalg.norm(joints["ankle_" + side] - ankle) < 1e-6, (i, side, "ankle")
        off = key.get("support_delta", key.get("shield_delta"))
        support = rig.rest[support_hand] + key["root"] + off + [
            0, key["yaw"] * tuning["support_yaw_offset"], tuning["support_hand_lift"]]
        for name, target in ((main_hand, key[main_hand]), (support_hand, support)):
            assert np.linalg.norm(joints[name] - target) < 1e-6, (i, name, "unreachable")
        if released_at(character.motions["attack"], main, i / 12):
            continue  # The socket still follows the hand; the item no longer follows the socket.
        rotation, shift = transforms[main]
        world = centers @ rotation.T + shift
        for part, pid in character.parts.items():
            if part in (main, main_hand):
                continue
            rotation, shift = transforms[part]
            xyz = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
            valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=1)
            assert not np.any(character.part_ids[tuple(xyz[valid][:, ::-1].T)] == pid), (i, main, part)


def released_at(clip, part, frame):
    return next((e for e in clip.get("events", []) if e.get("released_part") == part
                 and e["frame"] <= frame < e["rearm_frame"]), None)


def check_cloth(character, main):
    rig = Biped(character)
    clip = character.motions["attack"]
    cloth = Secondary(character, clip, rig.rest, mode="attack")
    frames = [rig.pose("attack", i)[1] for i in range(len(clip["keys"]))]
    grid = character.source_grid
    for region in cloth.regions:
        swings = cloth._pendulum(region, frames) if region["kind"] == "pendulum" else [None] * len(frames)
        for i, (transforms, swing) in enumerate(zip(frames, swings)):
            if released_at(clip, main, i):
                continue
            cells, _ = cloth.posed_cells(character, region, transforms, swing)
            world = character.posed_grid.origin + (cells + .5) * character.posed_grid.spacing
            rotation, shift = transforms[main]
            xyz = np.floor(((world - shift) @ rotation - grid.origin) / grid.spacing).astype(int)
            valid = ((xyz >= 0) & (xyz < grid.size_xyz)).all(axis=1)
            assert not np.any(character.part_ids[tuple(xyz[valid][:, ::-1].T)] == character.parts[main]), (
                i, main, region["name"])


def verify(character, out, gif, rules):
    character = character.for_motion("attack")
    clip = character.motions["attack"]
    layout = json.loads((out / "metadata.json").read_bytes())["animations"]["attack"]
    sheet = Image.open(out / "attack.png")
    count = len(clip["keys"])
    cell = character.config["attack"]["cell"]
    dirs = "S SW W NW N NE E SE".split()
    assert layout["rows"] == dirs and layout["columns"] == count and layout["cell"] == [cell, cell]
    assert layout["durations_ms"] == clip["durations_ms"] and not layout["loop"]
    assert layout["phase_names"] == clip["poses"]
    assert sheet.size == (count * cell, 8 * cell) and sheet.mode == "RGBA"
    assert hashlib.sha256(sheet.tobytes()).hexdigest() == layout["rgba_sha256"]
    feature = rules["feature"]
    check_path(character, feature, rules.get("path_materials"))
    if character.config["attack"].get("follow_cloth"):
        check_cloth(character, character.config["measurements"]["visibility"][feature]["part"])
    measurements = json.loads((out / "measurements.json").read_bytes())
    phase = clip["poses"].index(rules["phase"]) + 1
    seen = measurements["visibility_px_full_solo"]["attack"]
    for check in rules.get("visibility", []):
        for name in check["phases"]:
            col = clip["poses"].index(name) + 1
            for row in check.get("rows", dirs):
                px = seen[f"{row}_{col}"][check["feature"]][0]
                assert px >= check["min_px"], (name, row, check["feature"], px)
    if rules.get("transient_visibility"):
        with Image.open(out / "attack_part_ids.png") as atlas:
            owners = np.asarray(atlas).reshape(len(dirs), cell, count, cell)
        for check in rules["transient_visibility"]:
            col = clip["poses"].index(check["phase"])
            owner = layout["transient_parts"][check["part"]]
            for row, direction in enumerate(dirs):
                px = int(np.count_nonzero(owners[row, :, col, :] == owner))
                assert px >= check["min_px"], (direction, col, check["part"], px)
    minimum = min(seen[f"{d}_{phase}"][feature][0] for d in dirs)
    assert minimum >= rules["minimum_visible_px"], (feature, minimum)
    print(f"{rules['phase']}: {feature} visible in at least {minimum} pixels in every direction")
    idle = Image.open(out / "idle.png")
    neutral = idle.height
    pad = (cell - neutral) // 2
    assert layout["anchor"] == [p + pad for p in character.config["view"]["camera"]["base_pivot"]]
    previews = []
    contacts = {}
    joints = json.loads((out / "joints.json").read_bytes())["attack"]
    events = layout.get("events", [])
    assert len(events) == len(clip.get("events", []))
    for event, source in zip(events, clip.get("events", [])):
        col = source["frame"]
        assert all(event[k] == v for k,v in source.items())
        assert event["time_ms"] == sum(clip["durations_ms"][:col])
        assert event["position_model_xyz"] == joints[col][source["marker"]]
        assert np.isclose(np.linalg.norm(event["direction_model_xyz"]), 1)
        assert list(event["direction_by_row"]) == dirs
        if event.get("released_part") in rules.get("release_clearance_px", {}):
            part = event["released_part"]
            limit = rules["release_clearance_px"][part]
            with Image.open(out / "attack_part_ids.png") as atlas:
                owners = np.asarray(atlas).reshape(len(dirs), cell, count, cell)
            for row, tile in zip(dirs, owners[:, :, col, :]):
                item = tile == character.parts[part]
                points = np.argwhere(item)
                body = np.argwhere((tile != 0) & ~item)
                assert len(points) and len(body), (row, part, "missing release image")
                distances = np.sum((points[:, None] - body) ** 2, axis=2)
                assert distances.min() >= limit**2, (row, part, "release clearance")
        if source.get("direction_source") == "marker_travel":
            axis = np.subtract(joints[col][source["marker"]], joints[col-1][source["marker"]])
        elif source["marker"] == "arrow_tip":
            axis = np.subtract(joints[col]["arrow_tip"], joints[col]["arrow_nock"])
            if "baked_projectile_frames" in event:
                flight = 0
                while col + flight < count and "flight_offset" in clip["keys"][col + flight]:
                    flight += 1
                assert event["baked_projectile_frames"] == flight
        else:
            axis = np.asarray(clip["keys"][col]["aim"])
        forward = axis / np.linalg.norm(axis)
        assert np.allclose(forward, event["direction_model_xyz"])
        for row, yaw in character.config["view"]["directions"].items():
            angle = np.deg2rad(yaw)
            heading = np.array([np.sin(angle), np.cos(angle), 0])
            lateral = np.array([np.cos(angle), -np.sin(angle), 0])
            vector = event["direction_by_row"][row]
            assert np.allclose([vector @ lateral, vector @ heading, vector[2]], forward)
    with np.load(out / "posed_part_ids.npz") as volumes, np.load(out / "posed_slices.npz") as materials:
        for col in range(count):
            ids = volumes[f"attack_{col:02}"]
            key = clip["keys"][col]
            if bow := character.config["attack"].get("bow"):
                arrow = ids == layout["transient_parts"]["arrow"]
                assert arrow.any() == bool(key.get("nocked") or "flight_offset" in key)
                if key.get("nocked"):
                    draw = "hand_R" if character.config["rig"]["attachments"][bow["part"]]["hand"] == "hand_L" else "hand_L"
                    string = (ids == character.parts[bow["part"]]) & (materials[f"attack_{col:02}"] == bow["string_material"])
                    assert np.allclose(joints[col]["string_center"], joints[col][draw])
                    assert np.allclose(joints[col]["arrow_nock"], joints[col][draw])
                    assert face_contacts(string, ids == character.parts[draw]) > 0, (col, "lost string")
                if "flight_offset" in key:
                    assert not key.get("nocked") and clip["keys"][col-1].get("nocked")
                    last = joints[col-1]
                    ray = np.subtract(last["arrow_tip"], last["arrow_nock"])/bow["length"]
                    assert np.allclose(joints[col]["arrow_nock"], last["arrow_nock"] + key["flight_offset"]*ray)
                    assert not face_contacts(arrow, ids == character.parts[bow["part"]]), (col, "arrow still on bow")
            if "burst" in layout.get("transient_parts", {}):
                assert (ids == layout["transient_parts"]["burst"]).any() == bool(key.get("burst"))
            support = "boot_L" if character.config["attack"]["tuning"]["step_side"] == "R" else "boot_R"
            bottom = np.where((ids == character.parts[support]).any(axis=(1, 2)))[0].min()
            assert abs(character.posed_grid.origin[2] + bottom * character.posed_grid.spacing[2]) < 1e-6
            if rules.get("planted_feet"):
                for side in ("R", "L"):
                    toe = np.array(joints[col]["toe_"+side])
                    occupied = (ids == character.parts["boot_"+side]).any(axis=(1, 2))
                    grid = character.posed_grid
                    floor = grid.origin[2] + np.flatnonzero(occupied)[0]*grid.spacing[2]
                    assert floor >= 0 and abs(floor-toe[2]) <= grid.spacing[2]+1e-6, (col, side, floor)
                    if col:
                        previous = joints[col-1]["toe_"+side]
                        if abs(toe[2]) < 1e-6 and abs(previous[2]) < 1e-6:
                            assert np.allclose(previous, toe), (col, side, "grounded boot slid")
            missing = set(character.parts.values()) - set(np.unique(ids))
            expected_missing = set()
            for name, att in character.config["rig"]["attachments"].items():
                owned = ids == character.parts[name]
                faces = face_contacts(owned, ids == character.parts[att["hand"]])
                release = released_at(clip, name, col)
                if release:
                    event = next(e for e in events if e["frame"] == release["frame"]
                                 and e.get("released_part") == name)
                    preview = event.get("preview_distance", 0)
                    assert event["baked_projectile_frames"] == int(preview > 0)
                    if col == event["frame"] and preview:
                        # The complete item appears exactly once at its independent pose.
                        _, transforms = Biped(character).pose("attack", col)
                        rotation, shift = transforms[name]
                        shift = shift + np.asarray(event["direction_model_xyz"]) * preview
                        item = replace(character, parts={name: character.parts[name]})
                        model, expected = reslice(item, {name: (rotation, shift)})
                        assert owned.any() and faces == 0, (name, col, "still in hand")
                        assert np.array_equal(owned, expected != 0), (name, col, "release position")
                        assert np.array_equal(model[owned], materials[f"attack_{col:02}"][owned])
                    else:
                        expected_missing.add(character.parts[name])
                    continue
                assert faces > 0, (name, col, "lost grip")
                contacts[name] = min(contacts.get(name, faces), faces)
            assert missing == expected_missing, ("unexpected part presence", col, missing, expected_missing)
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
        rows = frames_of(sheet, layout["cell"][0], len(layout["rows"]), layout["columns"])
    with Image.open(published / "attack.gif") as preview:
        assert preview.n_frames == layout["columns"]
        for i, duration in enumerate(layout["durations_ms"]):
            preview.seek(i)
            assert abs(preview.info["duration"] - duration) < 10  # GIF delays use 10 ms ticks.
            if preview.size == (layout["cell"][0]*len(rows), layout["cell"][1]):
                assert preview.convert("RGB").tobytes() == strip([rows], i, 1).convert("RGB").tobytes()


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
