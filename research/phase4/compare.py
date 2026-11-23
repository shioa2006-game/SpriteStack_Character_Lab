"""Verify a rigid/weighted pair of BRAM bakes and render eight-view comparisons."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from research.phase4.skin import joints_for
from research.verify_bram import BRAM, ROOT, check_sprites, components, read
from research.verify_character import face_contacts
from spritestack.character import load_character


def rgba(path):
    with Image.open(path) as sheet:
        return sheet.convert("RGBA")


def check_layout(rigid, weighted):
    baseline = ROOT / "experiments/bram/baseline"
    metadata = read(rigid / "metadata.json")
    assert metadata == read(baseline / "metadata.json"), "rigid BRAM metadata regression"
    assert rgba(rigid / "idle.png").tobytes() == rgba(weighted / "idle.png").tobytes()
    for mode in ("idle", "walk", "attack"):
        actual = rgba(rigid / f"{mode}.png")
        reference = rgba(baseline / f"{mode}.png")
        assert actual.size == reference.size and actual.tobytes() == reference.tobytes(), mode

    trial = read(weighted / "metadata.json")
    layout = deepcopy(metadata)
    for mode, animation in trial["animations"].items():
        expected_hash = hashlib.sha256(rgba(weighted / f"{mode}.png").tobytes()).hexdigest()
        assert animation["rgba_sha256"] == expected_hash
        layout["animations"][mode]["rgba_sha256"] = expected_hash
    assert layout == trial, "weighted BRAM layout or timing changed"
    check_sprites(weighted, trial)
    return metadata


def compare_geometry(rigid, weighted, character, settings):
    joints = read(rigid / "joints.json")
    assert joints == read(weighted / "joints.json"), "an IK joint or attachment marker moved"
    rigid_ground = read(rigid / "measurements.json")["vol_ground"]
    weighted_ground = read(weighted / "measurements.json")["vol_ground"]
    assert rigid_ground == weighted_ground, "ground or blade clearance changed"
    protected = [character.parts[name] for name in ("boot_R", "boot_L", "hand_R", "hand_L", "sword", "shield")]
    parts = tuple(joints_for(character, settings))
    contacts = {joint.name: [[], []] for joint in parts}
    fragments = [[], []]
    boots = {"R": [], "L": []}
    ground = character.posed_grid
    with (np.load(rigid / "posed_slices.npz", allow_pickle=False) as rigid_volume,
          np.load(weighted / "posed_slices.npz", allow_pickle=False) as weighted_volume,
          np.load(rigid / "posed_part_ids.npz", allow_pickle=False) as rigid_parts,
          np.load(weighted / "posed_part_ids.npz", allow_pickle=False) as weighted_parts):
        assert rigid_parts.files == weighted_parts.files == rigid_volume.files == weighted_volume.files
        for key in rigid_parts.files:
            a, b = rigid_parts[key], weighted_parts[key]
            av, bv = rigid_volume[key], weighted_volume[key]
            locked = np.isin(a, protected)
            assert np.array_equal(locked, np.isin(b, protected)), key
            assert np.array_equal(a[locked], b[locked]) and np.array_equal(av[locked], bv[locked]), key
            assert set(np.unique(b)) == {0, *character.parts.values()}, key
            for gear, hand in (("sword", "hand_R"), ("shield", "hand_L")):
                assert face_contacts(b == character.parts[gear], b == character.parts[hand]) > 0, key
            if key in ("rest_00", "attack_00", "attack_08"):
                assert np.array_equal(a, b) and np.array_equal(av, bv), key
                continue
            for totals, volume in zip(fragments, (a, b), strict=True):
                totals.append(components(volume > 0)[1:])
            for joint in parts:
                parent, child = character.parts[joint.parent], character.parts[joint.child]
                for values, volume in zip(contacts[joint.name], (a, b), strict=True):
                    values.append(face_contacts(volume == parent, volume == child))
            if key.startswith("walk_"):
                for side in boots:
                    lowest = np.where(b == character.parts[f"boot_{side}"])[0].min()
                    boots[side].append(float(ground.origin[2] + ground.spacing[2] * lowest))

    clip = character.motions["walk"]
    for side, stance in clip["contact"]["inclusive_stance_cyclic"].items():
        marker = clip["contact"]["sole_markers"][side]
        points = np.array([joints["walk"][index][marker] for index in stance])
        points[:, 1] += clip["forward_each_frame"] * np.arange(len(stance))
        assert np.max(np.linalg.norm(points - points[0], axis=1)) < 1e-6
        assert np.all(np.abs(points[:, 2]) < 1e-6)
        assert all(z == 0 if i in stance else z > 0 for i, z in enumerate(boots[side]))
    assert all(min(pair[1]) > 0 for pair in contacts.values()), "a weighted seam detached"
    print("Identical joints and protected foot, hand, sword and shield voxels in all 16 poses")
    return {
        "walk_boot_min_z": boots,
        "seam_faces": {
            name: {
                label: {"min": min(samples), "mean": round(sum(samples) / len(samples), 2)}
                for label, samples in zip(("rigid", "weighted"), pair, strict=True)
            }
            for name, pair in contacts.items()
        },
        "fragments": {
            label: {
                "total_voxels": sum(sum(sizes) for sizes in poses),
                "largest_component": max((max(sizes, default=0) for sizes in poses), default=0),
            }
            for label, poses in zip(("rigid", "weighted"), fragments, strict=True)
        },
    }


def comparison_gif(rigid, weighted, mode, clip, out):
    cell, _ = clip["cell"]
    scale = 2
    width = cell * scale
    tile_width = 2 * width + 12
    tile_height = width + 33
    directions = clip["rows"]
    sheets = [rgba(folder / f"{mode}.png") for folder in (rigid, weighted)]
    frame_totals = {direction: {"rgba": 0, "alpha": 0} for direction in directions}
    frames = []
    for index in range(clip["columns"]):
        frame = Image.new("RGB", (tile_width * 4, tile_height * 2 + 24), "#253244")
        draw = ImageDraw.Draw(frame)
        font = ImageFont.load_default(size=12)
        draw.text((8, 4), f"BRAM / {mode.upper()}    {index + 1} / {clip['columns']}",
                  fill="#f2eee1", font=font)
        for row, direction in enumerate(directions):
            x, y = (row % 4) * tile_width, (row // 4) * tile_height + 24
            draw.text((x + 4, y), direction, fill="#c9e7fc", font=font)
            crop = (index * cell, row * cell, (index + 1) * cell, (row + 1) * cell)
            sprites = [sheet.crop(crop) for sheet in sheets]
            a, b = map(np.asarray, sprites)
            frame_totals[direction]["rgba"] += int(np.count_nonzero(np.any(a != b, axis=-1)))
            frame_totals[direction]["alpha"] += int(np.count_nonzero(a[..., 3] != b[..., 3]))
            for column, (label, sprite) in enumerate(zip(("RIGID", "WEIGHTED"), sprites, strict=True)):
                left = x + column * width + 4
                draw.text((left + 2, y + 14), label, fill="#dfe8eb", font=font)
                zoomed = sprite.resize((width, width), Image.Resampling.NEAREST)
                draw.line((left, y + 27 + clip["anchor"][1] * scale,
                           left + width - 1, y + 27 + clip["anchor"][1] * scale), fill="#415771")
                frame.paste(zoomed, (left, y + 27), zoomed)
        frames.append(frame)
    assert all(totals["rgba"] > 0 for totals in frame_totals.values()), f"{mode} lacked changes in a view"
    durations = clip.get("durations_ms", [1000 / clip["fps"]] * len(frames))
    # GIF uses centiseconds. Round the timeline, then derive frame durations from it.
    centiseconds = np.diff(np.r_[0, np.rint(np.cumsum(durations) / 10)]).astype(int)
    frames[0].save(out / f"{mode}.gif", save_all=True, append_images=frames[1:],
                   duration=(10 * centiseconds).tolist(), loop=0, disposal=2)
    return frame_totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rigid", required=True, type=Path)
    parser.add_argument("--weighted", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="new comparison output directory")
    parser.add_argument("--weights", type=Path, default=Path(__file__).with_name("weights.json"))
    args = parser.parse_args()
    metadata = check_layout(args.rigid, args.weighted)
    statistics = compare_geometry(args.rigid, args.weighted, load_character(BRAM), read(args.weights))
    args.out.mkdir(parents=True, exist_ok=False)
    statistics["changed_pixels"] = {
        mode: comparison_gif(args.rigid, args.weighted, mode, metadata["animations"][mode], args.out)
        for mode in ("walk", "attack")
    }
    report = json.dumps(statistics, indent=2)
    (args.out / "metrics.json").write_text(report + "\n", encoding="utf-8", newline="\n")
    print(report)


if __name__ == "__main__":
    main()
