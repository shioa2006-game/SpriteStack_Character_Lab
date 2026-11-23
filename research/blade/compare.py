"""Validate the refined clip and export eight-way and blade-specific comparisons."""

import argparse
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from research.blade.outline import TARGETS, measures, views
from research.overhead.analyze import measure
from research.overhead.compare import BASELINES, attack_gif, check_layout, check_motion, frame_at, sprite_panel
from research.overhead.motion import MANIFESTS, ROOT, character_for
from research.overhead.plots import plot_paths
from research.verify_bram import DIRECTIONS, read
from spritestack.rig import Biped


CLIP_PATH = Path(__file__).with_name("clip.json")
LABELS = ("BEFORE", "REFINED")
BACKGROUND = "#172339"


def blade_checks(name, source, models, targets, clips, sheets):
    without_roll = deepcopy(source)
    for pose in without_roll["keys"]:
        pose.pop("wrist_roll", None)
    refined, unrolled = Biped(models[1]), Biped(character_for(name, without_roll))
    for index in range(9):
        turned, _ = refined.pose("attack", index)
        straight, _ = unrolled.pose("attack", index)
        for joint in ("hand_R", "sword_tip", "hand_L"):
            np.testing.assert_allclose(turned[joint], straight[joint], rtol=0, atol=1e-9)

    by_variant = []
    for model, clip, sheet in zip(models, clips, sheets, strict=True):
        renders = {}
        for index in (4, 5):
            directions = [direction for direction, key in targets if key == index]
            for direction, view in views(model, index, directions):
                expected = frame_at(sheet, clip, DIRECTIONS.index(direction), index)
                assert view.image.tobytes() == expected.tobytes(), (direction, index)
                renders[direction, index] = view
        by_variant.append(renders)

    rows = {}
    for direction, index in targets:
        before, after = (measures(renders[direction, index]) for renders in by_variant)
        assert len(after["edge_components"]) == 1, (direction, index, after)
        assert after["visible"] > before["visible"], (direction, index, after)
        # BRAM's SE follow-through swaps half a pixel of span for a fuller blade face.
        min_length = before["length_px"] - (.55 if (direction, index) == ("SE", 5) else 0)
        assert after["length_px"] >= min_length, (direction, index, after)
        rows[f"{direction}_{index + 1}"] = {"before": before, "after": after}
    return by_variant, rows


def focused_sheets(out, name, targets, renders, rows):
    poses = Image.new("RGB", (425, 57 + len(targets) * 243), BACKGROUND)
    detail = Image.new("RGB", (920, 96 + len(targets) * 238), BACKGROUND)
    pose_draw, detail_draw = ImageDraw.Draw(poses), ImageDraw.Draw(detail)
    label = ImageFont.load_default(size=15)
    title = ImageFont.load_default(size=23)
    ink = "#e8edf3"
    accent = "#9cdfca"
    pose_draw.text((12, 12), f"{name.upper()} / PRIORITY ATTACK POSES", fill=ink, font=title)
    detail_draw.text((12, 12), f"{name.upper()} / BLADE OUTLINE AT 8x", fill=ink, font=title)
    detail_draw.text((12, 46), "Rendered pixels on the left. Visible blade and projected 3D centerline on the right.",
                     fill=ink, font=label)
    for row, (direction, index) in enumerate(targets):
        caption = f"{direction} / " + ("C: Cut" if index == 4 else "D: Follow-through")
        pose_y, detail_y = 52 + row * 243, 76 + row * 238
        pose_draw.text((12, pose_y), caption, fill=accent, font=label)
        detail_draw.text((12, detail_y), caption, fill=accent, font=label)
        variants = [variant[direction, index] for variant in renders]
        # Put both versions in the same 24-pixel crop, centered on the combined sword bounds.
        pixels = np.argwhere(variants[0].sword | variants[1].sword)[:, ::-1]
        lo, hi = pixels.min(axis=0), pixels.max(axis=0) + 1
        origin = np.clip((lo + hi) // 2 - 12, 0, 40)
        crop = (*origin, *(origin + 24))
        for i, (variant, tag) in enumerate(zip(variants, LABELS, strict=True)):
            px, dx = 12 + i * 204, 12 + i * 454
            pose_draw.text((px, pose_y + 22), tag, fill=ink, font=label)
            sprite_panel(poses, pose_draw, variant.image, px, pose_y + 41, 3)
            detail_draw.text((dx, detail_y + 21), tag, fill=ink, font=label)
            patch = variant.image.crop(crop).resize((192, 192), Image.Resampling.NEAREST)
            detail.paste(patch, (dx, detail_y + 41), patch)
            mx, my = dx + 204, detail_y + 41
            detail_draw.rectangle((mx, my, mx + 191, my + 191), fill="#0d1728")
            for y, x in np.argwhere(variant.isolated):
                if origin[0] <= x < origin[0] + 24 and origin[1] <= y < origin[1] + 24:
                    sx, sy = mx + 8 * (x - origin[0]), my + 8 * (y - origin[1])
                    color = "#abe5eb" if variant.visible[y, x] else "#394a62"
                    detail_draw.rectangle((sx, sy, sx + 7, sy + 7), fill=color)
            axis = (variant.centerline - origin) * 8 + [mx, my]
            detail_draw.line([tuple(point) for point in axis], fill="#faad70", width=2)
            data = rows[f"{direction}_{index + 1}"][("before", "after")[i]]
            detail_draw.text((dx + 204, detail_y + 21),
                             f"{data['visible']}/{data['isolated']} px visible  ·  {data['length_px']:.1f} px span",
                             fill=ink, font=label)
    poses.save(out / "targets.png")
    detail.save(out / "blade-detail.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, choices=MANIFESTS)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    name = args.character
    source = read(CLIP_PATH)
    overhead = ROOT / "research/overhead/baseline" / name
    clips, sheets, camera = check_layout(args.before, args.after, BASELINES[name], overhead=overhead)
    models = character_for(name), character_for(name, source)
    baseline, refined = (measure(model) for model in models)
    tests = check_motion(models[1], refined, args.after)
    tests["min_sampled_tip_z"] = min(point["tip"][2] for point in refined["curve"])
    assert tests["min_sampled_tip_z"] > 0
    targets = TARGETS if name == "bram" else TARGETS[:-1]
    renders, outlines = blade_checks(name, source, models, targets, clips, sheets)
    visibility = [read(folder / "measurements.json")["visibility_px_full_solo"]["attack"]
                  for folder in (args.before, args.after)]
    assert all(visibility[1][f"{direction}_{index}"]["blade"][0] > 0
               for direction in DIRECTIONS for index in (4, 5, 6))
    args.out.mkdir(parents=True, exist_ok=False)
    attack_gif(args.out / "comparison.gif", name, clips, sheets, LABELS)
    focused_sheets(args.out, name, targets, renders, outlines)
    plot_paths(args.out / "trajectory.png", name, camera, models[1].config["view"]["directions"],
               (baseline, refined), visibility, variant_label="Refined")
    (args.out / "metrics.json").write_text(
        json.dumps({"before": baseline, "after": refined, "visibility": visibility,
                    "checks": tests, "outlines": outlines}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"{name}: 72 attack sprites; 97 sampled poses; idle and walk RGBA, grounding, and gear checks passed")
    print(json.dumps({"checks": tests, "outlines": outlines}, indent=2))


if __name__ == "__main__":
    main()
