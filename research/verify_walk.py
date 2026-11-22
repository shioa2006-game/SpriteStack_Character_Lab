"""Check any biped character's walk bake: layout, contact, items, cloth and hair.

Run it on the output of
    python -m spritestack --character <character.json> --modes walk --out <dir>
The checks are the same for every character. The thresholds that differ per
character live in the "walk" section of the quality file next to character.json
(default: quality.json); see README.md. Results use the statuses of
research.verify_character: PASS, WARNING, FAIL and SKIP. The exit code is 1 when
any check FAILs.

Technical checks only. Whether the walk looks natural is judged on the GIFs.
"""

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
from PIL import Image

from research.verify_character import DIRECTIONS, Report, components, resolve
from spritestack.character import load_character
from spritestack.render import reslice
from spritestack.rig import Biped
from spritestack.secondary import Secondary


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frames_of(sheet, cell, rows, columns):
    return [[sheet.crop((c * cell, r * cell, (c + 1) * cell, (r + 1) * cell)) for c in range(columns)]
            for r in range(rows)]


def check_layout(report, character, out, meta, rig):
    view = character.config["view"]
    walk = meta["animations"].get("walk")
    if walk is None:
        report.add("walk.layout", "FAIL", "metadata.json has no walk animation")
        return None
    cell = character.config["walk"]["cell"]
    count = len(rig.walk_clip["poses"])
    expected = {"rows": list(view["directions"]), "columns": count, "cell": [cell, cell],
                "anchor": [a + (cell - view["neutral_cell"]) // 2 for a in view["camera"]["base_pivot"]],
                "fps": rig.walk_clip["fps"], "loop": True}
    wrong = {key: walk.get(key) for key, value in expected.items() if walk.get(key) != value}
    with Image.open(out / "walk.png") as image:
        sheet = image.convert("RGBA") if image.mode == "RGBA" else None
        size = image.size
    if wrong or sheet is None or size != (count * cell, len(DIRECTIONS) * cell) or expected["rows"] != DIRECTIONS:
        report.add("walk.layout", "FAIL", "walk sheet layout differs from the contract",
                   wrong=wrong, size=size, rgba=sheet is not None)
        return None
    frames = frames_of(sheet, cell, len(DIRECTIONS), count)
    alpha_ok = all(set(np.unique(np.asarray(f)[..., 3])) <= {0, 255} for row in frames for f in row)
    margins = [min(f.getbbox()[0], f.getbbox()[1], cell - f.getbbox()[2], cell - f.getbbox()[3])
               for row in frames for f in row]
    distinct = [len({f.tobytes() for f in row}) for row in frames]
    ok = alpha_ok and min(margins) >= 1 and all(d == count for d in distinct)
    report.add("walk.layout", "PASS" if ok else "FAIL",
               f"{len(DIRECTIONS)} directions x {count} frames of {cell}x{cell}, anchor {expected['anchor']}, "
               f"{expected['fps']} fps, loop; binary alpha, margin >= {min(margins)} px, distinct frames per row",
               distinct_frames=distinct, minimum_margin_px=min(margins), binary_alpha=alpha_ok)
    return frames


def check_idle(report, out, published):
    if published is None or not (published / "idle.png").exists():
        report.add("walk.idle_kept", "SKIP", "no published idle.png to compare with")
        return
    with Image.open(out / "idle.png") as baked, Image.open(published / "idle.png") as kept:
        same = baked.size == kept.size and baked.convert("RGBA").tobytes() == kept.convert("RGBA").tobytes()
    report.add("walk.idle_kept", "PASS" if same else "FAIL",
               "idle.png of the walk bake has the same decoded RGBA as the published idle sheet" if same
               else "idle.png differs from the published idle sheet")


def check_contact(report, character, rig, joints, poses):
    clip = rig.walk_clip
    grid = character.posed_grid
    step = clip["forward_each_frame"]
    drift, sole_z, problems = {}, {}, []
    for side, stance in clip["contact"]["inclusive_stance_cyclic"].items():
        marker = clip["contact"]["sole_markers"][side]
        world = np.array([joints[i][marker] for i in stance])
        world[:, 1] += step * np.arange(len(stance))
        drift[side] = float(np.max(np.linalg.norm(world - world[0], axis=1)))
        soles = []
        for index in range(len(joints)):
            ids = poses[f"walk_{index:02}"]
            layer = np.where(ids == character.parts["boot_" + side])[0].min()
            soles.append(float(grid.origin[2] + layer * grid.spacing[2]))
        sole_z[side] = soles
        if drift[side] >= 1e-6 or any(abs(world[:, 2]) >= 1e-6):
            problems.append(f"{side} stance marker slides")
        if any((z != 0) if i in stance else (z <= 0) for i, z in enumerate(soles)):
            problems.append(f"{side} boot is off the ground in stance or touches it in swing")
    report.add("walk.contact", "FAIL" if problems else "PASS",
               "; ".join(problems) or f"stance sole markers move with the ground ({step:.3g} model units per "
               "frame, drift 0); boots touch z = 0 only in stance",
               drift=drift, boot_sole_z=sole_z)


def check_ground(report, character, quality, poses, measurements):
    grid = character.posed_grid
    lowest = []
    for index in range(len([k for k in poses.files if k.startswith("walk_")])):
        ids = poses[f"walk_{index:02}"]
        lowest.append(float(grid.origin[2] + np.where(ids > 0)[0].min() * grid.spacing[2]))
    floors = quality.get("lowest_z_at_least", {})
    measured = {label: [measurements["vol_ground"][f"walk_{i:02}"][label] for i in range(len(lowest))]
                for label in floors}
    below = {label: values for label, values in measured.items() if min(values) < floors[label]}
    ok = min(lowest) >= 0 and not below
    report.add("walk.ground", "PASS" if ok else "FAIL",
               f"nothing below z = 0 in any frame; item floors {floors or 'none'} held" if ok
               else "a voxel or an item goes below its floor", lowest_voxel_z=lowest, items=measured)


def check_parts(report, character, poses, quality):
    rest = {name: int((poses["rest_00"] == part_id).sum()) for name, part_id in character.parts.items()}
    worst, missing = {}, []
    for key in sorted(k for k in poses.files if k.startswith("walk_")):
        ids = poses[key]
        for name, part_id in character.parts.items():
            ratio = int((ids == part_id).sum()) / rest[name]
            worst[name] = min(worst.get(name, 9), ratio)
    limit = quality.get("part_voxel_ratio_at_least", .8)
    low = {name: round(ratio, 3) for name, ratio in worst.items() if ratio < limit}
    report.add("walk.parts", "FAIL" if low else "PASS",
               f"every part keeps at least {limit:.0%} of its posed rest voxel count in every frame" if not low
               else f"parts lost voxels: {low}", lowest_ratio={k: round(v, 3) for k, v in worst.items()})


def check_items(report, character, joints, poses):
    attachments = character.config["rig"]["attachments"]
    rest = Biped(character).rest
    contacts, problems = {}, []
    for item, attachment in attachments.items():
        hand, marker = attachment["hand"], attachment["marker"]
        length = np.linalg.norm(rest[marker] - rest[hand])
        counts = []
        for index, frame in enumerate(joints):
            if abs(np.linalg.norm(np.subtract(frame[marker], frame[hand])) - length) >= 1e-6:
                problems.append(f"{item} marker moves against {hand} in frame {index}")
            ids = poses[f"walk_{index:02}"]
            gear, held = ids == character.parts[item], ids == character.parts[hand]
            touching = 0
            for axis in range(3):
                a, b = np.moveaxis(gear, axis, 0), np.moveaxis(held, axis, 0)
                touching += int(np.count_nonzero(a[:-1] & b[1:]) + np.count_nonzero(b[:-1] & a[1:]))
            counts.append(touching)
            side = np.sign(np.mean(np.argwhere(gear)[:, 2]) * character.posed_grid.spacing[0]
                           + character.posed_grid.origin[0])
            if side != (-1 if hand == "hand_R" else 1):
                problems.append(f"{item} crosses to the other side in frame {index}")
        contacts[item] = min(counts)
        if min(counts) == 0:
            problems.append(f"{item} loses contact with {hand}")
    report.add("walk.items", "FAIL" if problems else "PASS",
               "; ".join(problems) or "held items keep their marker distance, touch their hand in every "
               "frame and stay on the hand's side", minimum_face_contacts=contacts)


def check_arm_phase(report, rig, joints, quality):
    """Each arm swings against the same-side leg: hand forward while that foot is back."""
    rule = quality.get("arm_swing", "contralateral")
    if rule == "none":
        report.add("walk.arm_phase", "SKIP", "the quality file does not check the arm phase")
        return
    phases = {}
    for side, other in (("R", "L"), ("L", "R")):
        hand = np.array([frame["hand_" + side][1] for frame in joints])
        ankle = np.array([frame["ankle_" + other][1] for frame in joints])
        if np.ptp(hand) < 1e-6:
            phases[side] = None
            continue
        phases[side] = float(np.corrcoef(hand, ankle)[0, 1])
    wrong = [side for side, value in phases.items() if value is not None and value <= .5]
    report.add("walk.arm_phase", "FAIL" if wrong else "PASS",
               f"hands move with the opposite foot (correlation {phases})" if not wrong
               else f"{wrong} hand swings with its own foot (correlation {phases})",
               correlation_with_opposite_ankle=phases)


def check_fragments(report, poses, quality):
    limit = quality.get("max_fragment_voxels", 2)
    largest = []
    for key in sorted(k for k in poses.files if k.startswith("walk_")):
        pieces = components(poses[key] > 0)
        largest.append(int(pieces[1].sum()) if len(pieces) > 1 else 0)
    report.add("walk.fragments", "PASS" if max(largest) <= limit else "FAIL",
               f"largest piece detached from the body: {max(largest)} voxels (limit {limit})",
               per_frame=largest)


def check_anchor(report, character, out, frames, poses, quality):
    """Boots are drawn where the camera puts their soles, and the figure does not drift.

    The stance sole stays on the ground, so a foot that steps towards the camera is
    drawn lower than in idle. The check projects the boot voxels on the ground layer
    with the bake's camera and compares the lowest boot row of the part atlas with it.
    """
    view = character.config["view"]
    camera = view["camera"]
    grid = character.posed_grid
    cell = character.config["walk"]["cell"]
    pivot_y = camera["base_pivot"][1] + (cell - view["neutral_cell"]) // 2
    pitch = np.radians(camera["pitch_deg"])
    boots = [character.parts["boot_R"], character.parts["boot_L"]]
    ground_layer = int(round(-grid.origin[2] / grid.spacing[2]))
    with Image.open(out / "walk_part_ids.png") as image:
        atlas = np.asarray(image)
    offsets, drift = {}, {}
    limit_x = quality.get("max_center_drift_px", 3)
    for row, (direction, yaw) in enumerate(view["directions"].items()):
        theta = np.radians(yaw)
        forward = np.array([-np.sin(theta), np.cos(theta), 0])
        up = -forward * np.sin(pitch) + np.array([0, 0, 1]) * np.cos(pitch)
        offsets[direction], centres = [], []
        for index, frame in enumerate(frames[row]):
            ids = poses[f"walk_{index:02}"]
            soles = np.argwhere(np.isin(ids[ground_layer], boots))
            centers = np.column_stack([grid.origin[0] + (soles[:, 1] + .5) * grid.spacing[0],
                                       grid.origin[1] + (soles[:, 0] + .5) * grid.spacing[1],
                                       np.full(len(soles), grid.origin[2] + (ground_layer + .5) * grid.spacing[2])])
            expected = int(np.floor(pivot_y - (centers @ up).min() * camera["pixels_per_unit"]))
            tile = atlas[row * cell:(row + 1) * cell, index * cell:(index + 1) * cell]
            drawn = np.where(np.isin(tile, boots).any(axis=1))[0]
            offsets[direction].append(int(drawn.max() - expected) if len(drawn) else None)
            centres.append(np.argwhere(np.asarray(frame)[..., 3] > 0)[:, 1].mean())
        drift[direction] = round(float(np.ptp(centres)), 2)
    values = [v for row in offsets.values() for v in row]
    worst = max(abs(v) for v in values if v is not None)
    ok = None not in values and worst <= 1 and max(drift.values()) <= limit_x
    report.add("walk.anchor", "PASS" if ok else "FAIL",
               f"lowest boot row within {worst} px of the projected sole in every frame; horizontal centre "
               f"moves {max(drift.values())} px at most (limit {limit_x})",
               boot_row_minus_projected_sole_px=offsets, centre_range_px=drift)


def check_visibility(report, character, measurements, quality):
    rules = quality.get("visibility_min_px", {})
    if not rules:
        report.add("walk.visibility", "SKIP", "no walk visibility rules in the quality file")
        return
    seen = measurements["visibility_px_full_solo"]["walk"]
    low = {}
    minimum = {}
    for label, threshold in rules.items():
        values = {key: item[label][0] for key, item in seen.items()}
        minimum[label] = min(values.values())
        under = sorted(key for key, value in values.items() if value < threshold)
        if under:
            low[label] = under
    report.add("walk.visibility", "FAIL" if low else "PASS",
               f"measured items stay visible in all 48 frames: {minimum} px at least (limits {rules})"
               if not low else f"items too small in {low}", minimum_px=minimum)


def check_secondary(report, character, rig, quality):
    regions = character.config["walk"].get("secondary", [])
    if not regions:
        report.add("walk.secondary", "SKIP", "character.json has no walk.secondary regions")
        return
    secondary = Secondary(character, rig.walk_clip, rig.rest)
    frames = [rig.pose("walk", index)[1] for index in range(len(rig.walk_clip["poses"]))]
    swings = [secondary._pendulum(region, frames) if region["kind"] == "pendulum" else None
              for region in secondary.regions]
    intrusion, angles = {}, {}
    for number, region in enumerate(secondary.regions):
        others = replace(character, parts={name: part_id for name, part_id in character.parts.items()
                                           if name != region["part"] and name not in character.config["rig"]["attachments"]})
        moved, rigid = [], []
        for index, transforms in enumerate(frames):
            occupied = reslice(others, transforms)[1] > 0
            swing = swings[number][index] if swings[number] else None
            for still, sink in ((False, moved), (True, rigid)):
                cells, _ = secondary.posed_cells(character, region, transforms, swing, rigid=still)
                cells = np.unique(cells, axis=0)
                sink.append(float(occupied[tuple(cells[:, ::-1].T)].mean()))
        intrusion[region["name"]] = {"rigid": round(max(rigid), 4), "secondary": round(max(moved), 4)}
        if swings[number]:
            values = [swing[2] for swing in swings[number]]
            angles[region["name"]] = [round(min(values), 2), round(max(values), 2), region["max_deg"]]
    slack = quality.get("intrusion_slack", .01)
    worse = {name: value for name, value in intrusion.items() if value["secondary"] > value["rigid"] + slack}
    report.add("walk.secondary.intrusion", "WARNING" if worse else "PASS",
               "moving cloth and hair do not enter other parts more than the rigid model does "
               f"(share of the region's posed cells inside other body parts, slack {slack})" if not worse
               else f"regions enter other parts more than rigid: {worse}", share_inside_other_parts=intrusion)
    still = {name: value for name, value in angles.items() if value[1] - value[0] < 1 and value[1] < 2}
    report.add("walk.secondary.motion", "WARNING" if still else "PASS",
               f"pendulum angles per region [min, max, max_deg] in degrees: {angles}" if not still
               else f"regions barely move: {still}", angles_deg=angles,
               moving_voxels=secondary.moving_count)


def check_published(report, out, meta, published):
    if published is None:
        report.add("walk.published", "SKIP", "no published folder in the quality file")
        return
    sheet, layout = published / "walk.png", published / "walk.json"
    if not sheet.exists() or not layout.exists():
        report.add("walk.published", "FAIL", f"walk.png or walk.json missing in {published}")
        return
    with Image.open(out / "walk.png") as a, Image.open(sheet) as b:
        same = a.size == b.size and a.convert("RGBA").tobytes() == b.convert("RGBA").tobytes()
    same_json = read(layout) == {"animations": {"walk": meta["animations"]["walk"]}}
    report.add("walk.published", "PASS" if same and same_json else "FAIL",
               f"walk.png decoded RGBA and walk.json match {published}" if same and same_json
               else f"published walk differs: RGBA equal {same}, JSON equal {same_json}")


def verify(character_path, out, quality_path=None, published="quality"):
    character_path = Path(character_path).resolve()
    character = load_character(character_path)
    quality_path = Path(quality_path) if quality_path else character_path.with_name("quality.json")
    quality_all = read(quality_path) if quality_path.exists() else {}
    quality = quality_all.get("walk", {})
    if published == "quality":
        published = resolve(quality_path.parent, quality.get("published") or quality_all.get("published"))
    out = Path(out)
    report = Report()
    rig = Biped(character)
    meta, joints = read(out / "metadata.json"), read(out / "joints.json")["walk"]
    measurements = read(out / "measurements.json")
    frames = check_layout(report, character, out, meta, rig)
    check_idle(report, out, published)
    with np.load(out / "posed_part_ids.npz", allow_pickle=False) as poses:
        check_contact(report, character, rig, joints, poses)
        check_ground(report, character, quality, poses, measurements)
        check_parts(report, character, poses, quality)
        check_items(report, character, joints, poses)
        check_fragments(report, poses, quality)
        if frames:
            check_anchor(report, character, out, frames, poses, quality)
    check_arm_phase(report, rig, joints, quality)
    check_visibility(report, character, measurements, quality)
    check_secondary(report, character, rig, quality)
    check_published(report, out, meta, published)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--character", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="output of spritestack --modes walk")
    parser.add_argument("--quality", type=Path, help="quality file (default: quality.json next to character.json)")
    parser.add_argument("--no-published", action="store_true", help="skip the comparison with the published copy")
    parser.add_argument("--json", type=Path, help="also write the results as JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    report = verify(args.character, args.out, args.quality, None if args.no_published else "quality")
    report.print(args.verbose)
    if args.json:
        args.json.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    raise SystemExit(1 if report.failed() else 0)


if __name__ == "__main__":
    main()
