"""Inspect native rib openings, shield occlusion and pre-reslice equipment clearances."""

import argparse
import json
from pathlib import Path

import numpy as np

from research.image_to_character_04.check_shield import check_shield
from research.image_to_character_05.inspect_motion import blade
from research.image_to_character_06.inspect_motion import centers, intersections
from research.verify_attack import check_cloth, sample
from spritestack.character import load_character
from spritestack.render import Renderer, normals
from spritestack.rig import Biped
from spritestack.secondary import Secondary


def openings(character):
    renderer = Renderer(character)
    view = character.config["view"]
    grid = character.source_grid
    parts, model = character.part_ids, character.model
    no_shield = np.where(parts == character.parts["shield"], 0, model)
    rib_ids = character.config["measurements"]["visibility"]["ribs"]["materials"]
    costal = np.isin(model, rib_ids)
    surface = normals(model, grid)
    result = {}
    for direction, yaw in view["directions"].items():
        args = (parts, grid, yaw, view["neutral_cell"], view["neutral_rays"])
        image, full, _ = renderer.render(model, *args, surface)
        bare = renderer.render(no_shield, *args)
        ribs = renderer.render(costal.astype(np.uint8), *args) > 0
        # A pixel qualifies only between two rib hits in the same screen column.
        between = np.maximum.accumulate(ribs, axis=0) & np.maximum.accumulate(ribs[::-1], axis=0)[::-1] & ~ribs
        result[direction] = {
            "rib_gap_empty_rays": int((between & (full == 0)).sum()),
            "rib_gap_transparent_png_pixels": int((between & (np.asarray(image)[..., 3] == 0)).sum()),
            "ribs_visible_px": int(np.isin(full, rib_ids).sum()),
            "ribs_without_shield_px": int(np.isin(bare, rib_ids).sum()),
        }
    return result


def contacts(character):
    rig = Biped(character)
    visibility = character.config["measurements"]["visibility"]
    rib_ids = visibility["ribs"]["materials"]
    ribs = centers(character, np.isin(character.model, rib_ids))
    steel = centers(character, np.isin(character.model, visibility["blade"]["materials"]))
    armor = centers(character, character.part_ids == character.parts["upper_R"])
    limbs = [p for p in character.parts if p.startswith(("upper_", "fore_", "hand_"))]
    report = {}
    for mode in ("walk", "attack"):
        if mode == "walk":
            sequence = [rig.pose("walk", i)[1] for i in range(len(rig.walk_clip["poses"]))]
            clip = rig.walk_clip
        else:
            sequence = [t for _, _, _, t in sample(character)]
            clip = character.motions["attack"]
        shield_samples = check_shield(character, sequence)
        overlaps = []
        pairs = [("ribs", ribs, "chest", [*limbs, "sword", "shield"]),
                 ("sword shoulder", armor, "upper_R", ["head"])]
        if mode == "walk":
            others = [p for p in character.parts if p not in ("sword", "hand_R")]
            pairs.append(("steel", steel, "sword", others))
        for i, transforms in enumerate(sequence):
            for label, local, owner, targets in pairs:
                rotation, shift = transforms[owner]
                world = local @ rotation.T + shift
                for name in targets:
                    hits = intersections(character, world, name, transforms[name])
                    if hits:
                        overlaps.append([i, label, name, hits])
        # Count moving cloth cells at baked keys. The waist attachment stays with the pelvis.
        cloth = Secondary(character, clip, rig.rest, mode=mode)
        frames = [rig.pose(mode, i)[1] for i in range(len(clip["poses"]))]
        for i, transforms in enumerate(frames):
            for region in cloth.regions:
                cells, _ = cloth.posed_cells(character, region, transforms, None)
                grid = character.posed_grid
                world = grid.origin + (cells + .5) * grid.spacing
                for name in ("sword", "shield", "fore_R", "fore_L", "hand_R", "hand_L"):
                    hits = intersections(character, world, name, transforms[name])
                    if hits:
                        overlaps.append([i, region["name"], name, hits])
        report[mode] = {"samples": shield_samples, "cloth_keys": len(frames), "overlaps": overlaps}
    check_cloth(character, "shield")
    return report


def inspect(character, bake, quality):
    rig, renderer = Biped(character), Renderer(character)
    report = {"idle": openings(character), "contacts": contacts(character)}
    report["isolated_blade"] = {m: blade(character, rig, renderer, m) for m in ("idle", "walk", "attack")}
    visible = json.loads((bake / "measurements.json").read_bytes())["visibility_px_full_solo"]["attack"]
    report["attack_visibility"] = {}
    for rule in [quality["attack"], *quality["additional_attack_phases"]]:
        phase = rule["phase"]
        index = character.motions["attack"]["poses"].index(phase) + 1
        counts = {d: visible[f"{d}_{index}"][rule["feature"]][0] for d in character.config["view"]["directions"]}
        report["attack_visibility"][phase] = counts
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, default=Path("characters/skeleton_guard/character.json"))
    parser.add_argument("--bake", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    character = load_character(args.character)
    quality = json.loads(args.character.with_name("quality.json").read_bytes())
    result = inspect(character, args.bake, quality)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    rule = quality["rib_openings"]
    front = result["idle"][rule["direction"]]
    if (front["rib_gap_transparent_png_pixels"] < rule["minimum_transparent_pixels"] or
            front["ribs_visible_px"] < front["ribs_without_shield_px"] * rule["minimum_visible_fraction_with_shield"]):
        raise SystemExit(f"Rib cage opening or visibility below target: see {args.out}")
    if any(row["overlaps"] for row in result["contacts"].values()):
        raise SystemExit(f"Body or gear intersection: see {args.out}")
    if any(row["disconnected_or_missing"] for row in result["isolated_blade"].values()):
        raise SystemExit(f"Disconnected blade pixels: see {args.out}")
    for rule in [quality["attack"], *quality["additional_attack_phases"]]:
        if min(result["attack_visibility"][rule["phase"]].values()) < rule["minimum_visible_px"]:
            raise SystemExit(f"Insufficient {rule['phase']} visibility: see {args.out}")
