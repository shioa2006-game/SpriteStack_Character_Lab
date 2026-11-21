"""Validate two attack bakes and export matched 8-direction comparison assets."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from research.overhead.analyze import SUBSTEPS, angle, measure
from research.overhead.motion import MANIFESTS, ROOT, character_for
from research.overhead.plots import plot_paths
from research.verify_bram import DIRECTIONS, face_contacts, read
from spritestack.character import load_character
from spritestack.rig import Biped


def open_rgba(path):
    with Image.open(path) as source:
        return source.convert("RGBA")


def frame_at(sheet, layout, row, column):
    w, h = layout["cell"]
    return sheet.crop((w * column, h * row, w * (column + 1), h * (row + 1)))


def check_layout(before, improved, official_assets, *, attack_stem="attack"):
    current, new = (read(folder / "metadata.json") for folder in (before, improved))
    reference = read(official_assets / "metadata.json")
    if attack_stem != "attack":
        reference["animations"]["attack"] = read(official_assets / f"{attack_stem}.json")
    assert current == reference
    for mode in ("idle", "walk"):
        panes = [open_rgba(folder / f"{mode}.png") for folder in (official_assets, before, improved)]
        assert panes[0].size == panes[1].size == panes[2].size
        assert panes[0].tobytes() == panes[1].tobytes() == panes[2].tobytes(), mode
    assert current["neutral"] == new["neutral"]
    assert current["animations"]["walk"] == new["animations"]["walk"]
    poses = tuple(meta["animations"]["attack"] for meta in (current, new))
    sheets = tuple(open_rgba(folder / "attack.png") for folder in (before, improved))
    assert sheets[0].tobytes() == open_rgba(official_assets / f"{attack_stem}.png").tobytes()
    idle = open_rgba(improved / "idle.png")
    for clip, sheet in zip(poses, sheets, strict=True):
        assert clip["rows"] == DIRECTIONS and clip["columns"] == 9
        assert clip["cell"] == [64, 64] and clip["anchor"] == [32, 48]
        assert sum(clip["durations_ms"]) == 800 and not clip["loop"]
        assert sheet.size == (576, 512)
        assert hashlib.sha256(sheet.tobytes()).hexdigest() == clip["rgba_sha256"]
        for row in range(8):
            guard = Image.new("RGBA", (64, 64))
            guard.paste(idle.crop((48 * row, 0, 48 * (row + 1), 48)), (8, 8))
            frames = [frame_at(sheet, clip, row, index) for index in range(9)]
            assert frames[0].tobytes() == frames[-1].tobytes() == guard.tobytes()
            assert len({frame.tobytes() for frame in frames}) == 8
            for frame in frames:
                assert set(np.unique(np.asarray(frame)[..., 3])) == {0, 255}
                x, y, right, bottom = frame.getbbox()
                assert min(x, y, 64 - right, 64 - bottom) >= 1
    assert sheets[0].tobytes() != sheets[1].tobytes()
    return poses, sheets, current["camera"]


def check_motion(character, after, improved):
    assert not after["collisions"], after["collisions"]
    assert max(after[key] for key in ("right_hand_error", "left_hand_error", "ankle_error")) < 1e-6
    assert after["max_blade_key_angle"] < 90
    assert after["max_bend_plane_step"] < 15
    points, transforms = Biped(character).pose("attack", 3)
    grid = character.source_grid
    xyz = np.argwhere(character.part_ids == character.parts["head"])[:, ::-1]
    centers = grid.origin + (xyz + .5) * grid.spacing
    rotation, offset = transforms["head"]
    top = (centers @ rotation.T + offset)[:, 2].max() + abs(rotation[2]) @ (grid.spacing / 2)
    clearance = float(points["sword_tip"][2] - top)
    assert clearance >= .75
    curve = after["curve"]
    arc = np.array([point["tip"] for point in curve[3 * SUBSTEPS:5 * SUBSTEPS + 1]])
    assert np.all(np.diff(arc[:SUBSTEPS + 1, 1]) > 0), "sword reversed before the cut"
    assert np.all(np.diff(arc[SUBSTEPS:, 2]) < 0), "sword reversed through follow-through"
    assert all(abs(point["toe_left_z"]) < 1e-6 and
               abs(point["toe_right_z"] - point["lift"]) < 1e-6 for point in curve)
    assert abs(after["keys"][4]["toe_right_z"]) < 1e-6
    assert after["keys"][3]["toe_right_z"] > .5
    assert after["keys"][5]["tip"][2] < 5
    contacts = {"sword": [], "shield": []}
    grounds = {"R": [], "L": []}
    with np.load(improved / "posed_part_ids.npz", allow_pickle=False) as ids:
        for index in range(9):
            frame = ids[f"attack_{index:02}"]
            assert set(np.unique(frame)) == {0, *character.parts.values()}
            for gear, hand in (("sword", "hand_R"), ("shield", "hand_L")):
                faces = face_contacts(frame == character.parts[gear], frame == character.parts[hand])
                assert faces > 0, (index, gear)
                contacts[gear].append(faces)
            for side in grounds:
                floor = np.where(frame == character.parts[f"boot_{side}"])[0].min()
                grounds[side].append(float(character.posed_grid.origin[2]
                                           + floor * character.posed_grid.spacing[2]))
    assert grounds["L"] == [0] * 9 and min(grounds["R"]) >= 0
    assert all(grounds["R"][index] == 0 for index in (0, 1, 4, 5, 6, 8))
    assert all(grounds["R"][index] > 0 for index in (2, 3, 7))
    return {
        "apex_head_clearance": clearance,
        "step_at_cut": after["keys"][4]["step"],
        "min_attachment_faces": {gear: min(counts) for gear, counts in contacts.items()},
        "posed_boot_min_z": grounds,
        "forward_apex_to_cut": float(arc[SUBSTEPS, 1] - arc[0, 1]),
        "drop_cut_to_low": float(arc[SUBSTEPS, 2] - arc[-1, 2]),
        "max_sampled_arc_turn": max(angle(a, b) for a, b in zip(np.diff(arc, axis=0), np.diff(arc, axis=0)[1:])),
    }


def sprite_panel(canvas, draw, sprite, x, y, scale):
    baseline = y + 48 * scale
    draw.line((x, baseline, x + 64 * scale - 1, baseline), fill="#405570")
    enlarged = sprite.resize((64 * scale, 64 * scale), Image.Resampling.NEAREST)
    canvas.paste(enlarged, (x, y), enlarged)


def pose_table(filename, name, clips, sheets):
    names = ("A · Guard", "B · Raise / apex", "C · Cut", "D · Follow-through", "E · Recover")
    shown = ((0, 2, 4, 6, 7), (0, 3, 4, 5, 7))
    board = Image.new("RGB", (1370, 1145), "#172339")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default(size=15)
    draw.text((12, 10), f"{name.upper()}  /  ATTACK POSES  /  SAME ANCHOR & SCALE",
              fill="#f0efe8", font=ImageFont.load_default(size=24))
    for column, title in enumerate(names):
        x = 36 + 266 * column
        draw.text((x, 51), title, fill="#e8edf3", font=font)
        for variant, label in enumerate(("BEFORE", "OVERHEAD")):
            draw.text((x + variant * 132, 72), label, fill="#a9c8df", font=font)
            for row, direction in enumerate(DIRECTIONS):
                y = 99 + row * 130
                draw.text((5, y + 6), direction, fill="#a9c8df", font=font)
                sprite = frame_at(sheets[variant], clips[variant], row, shown[variant][column])
                sprite_panel(board, draw, sprite, x + variant * 132, y, 2)
    board.save(filename)


def attack_gif(filename, name, clips, sheets, labels):
    # Quantize each clip's cumulative boundaries once, then share the timeline.
    ends = [np.rint(np.cumsum(clip["durations_ms"]) / 10).astype(int) for clip in clips]
    cuts = sorted({0, *(cut for timeline in ends for cut in timeline)})
    frames = []
    font = ImageFont.load_default(size=13)
    tile = len(labels) * 130 + 8
    for start in cuts[:-1]:
        frame = Image.new("RGB", (4 * tile, 347), "#172339")
        draw = ImageDraw.Draw(frame)
        draw.text((8, 5), f"{name.upper()} / ALL EIGHT VIEWS / 800 ms AT 1x",
                  fill="#f0efe8", font=font)
        for row, direction in enumerate(DIRECTIONS):
            x, y = (row % 4) * tile, (row // 4) * 161 + 21
            draw.text((x + 3, y), direction, fill="#a9c8df", font=font)
            for variant, label in enumerate(labels):
                ix = x + variant * 130 + 3
                pose = int(np.searchsorted(ends[variant], start, side="right"))
                draw.text((ix, y + 15), label, fill="#e8edf3", font=font)
                sprite_panel(frame, draw, frame_at(sheets[variant], clips[variant], row, pose),
                             ix, y + 30, 2)
        frames.append(frame)
    frames[0].save(filename, save_all=True, append_images=frames[1:], loop=0,
                   duration=[10 * (b - a) for a, b in zip(cuts, cuts[1:])], disposal=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, choices=MANIFESTS)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    name = args.character
    official_assets = ROOT / "docs/assets" / ("bram" if name == "bram" else "")
    clips, sheets, camera = check_layout(args.before, args.after, official_assets)
    character = character_for(name)
    before, after = (measure(model) for model in (load_character(MANIFESTS[name]), character))
    tests = check_motion(character, after, args.after)
    visibility = [read(folder / "measurements.json")["visibility_px_full_solo"]["attack"]
                  for folder in (args.before, args.after)]
    assert all(visibility[1][f"{direction}_{frame}"]["blade"][0] > 0
               for direction in DIRECTIONS for frame in (4, 5, 6)), "a major pose lost the whole blade"
    args.out.mkdir(parents=True, exist_ok=False)
    pose_table(args.out / "poses.png", name, clips, sheets)
    attack_gif(args.out / "comparison.gif", name, clips, sheets, ("BEFORE", "OVERHEAD"))
    attack_gif(args.out / "before.gif", name, clips[:1], sheets[:1], ("BEFORE",))
    plot_paths(args.out / "trajectory.png", name, camera, character.config["view"]["directions"],
               (before, after), visibility)
    (args.out / "metrics.json").write_text(
        json.dumps({"before": before, "after": after, "visibility": visibility, "checks": tests}, indent=2)
        + "\n", encoding="utf-8", newline="\n")
    print(f"{name}: 72 attack sprites; 97 sampled poses; unchanged idle/walk; IK and attachments passed")
    print(json.dumps(tests, indent=2))


if __name__ == "__main__":
    main()
