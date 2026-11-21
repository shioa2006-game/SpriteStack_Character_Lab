"""Bake the configured character into PNG sheets, volumes and metadata."""

import hashlib
import json

import numpy as np
from PIL import Image

from .render import Renderer, normals, reslice
from .rig import Biped, transform


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def require_margin(frame, label):
    box = frame.getbbox()
    if not box or min(box[0], box[1], frame.width - box[2], frame.height - box[3]) < 1:
        raise ValueError(f"{label} does not fit with a transparent margin in a {frame.width}px cell")


def check_attachment(rig, joints, transforms):
    for part, attachment in rig.attachments.items():
        hand, marker = attachment["hand"], attachment["marker"]
        matrix = transforms[part]
        position = transform(matrix, rig.rest[hand])
        offset = matrix[0].T @ (joints[marker] - joints[hand])
        if (np.linalg.norm(position - joints[hand]) >= 1e-6
                or np.linalg.norm(offset - (rig.rest[marker] - rig.rest[hand])) >= 1e-6):
            raise ValueError(f"{part} does not follow {hand}")


def render_neutral(character, renderer):
    view = character.config["view"]
    cell = view["neutral_cell"]
    surface = normals(character.model, character.source_grid)
    frames = {}
    sheet = Image.new("RGBA", (cell * len(view["directions"]), cell))
    for column, (direction, yaw) in enumerate(view["directions"].items()):
        frame, _, _ = renderer.render(character.model, character.part_ids, character.source_grid,
                                      yaw, cell, view["neutral_rays"], surface)
        require_margin(frame, direction)
        sheet.paste(frame, (column * cell, 0))
        frames[direction] = frame
    return sheet, frames


def render_motion(character, renderer, mode, poses, neutral):
    view = character.config["view"]
    directions = view["directions"]
    render_cell = view["render_cell"]
    cell = character.config[mode]["cell"]
    neutral_pad = (render_cell - view["neutral_cell"]) // 2
    crop = (render_cell - cell) // 2
    end = crop + cell
    count = len(poses)
    sheet = Image.new("RGBA", (count * cell, len(directions) * cell))
    part_atlas = np.zeros((sheet.height, sheet.width), dtype=np.uint8)
    measurements = {}
    visibility = character.config["measurements"]["visibility"]

    for index, (volume, parts) in enumerate(poses):
        surface = normals(volume, character.posed_grid)
        guard = mode == "attack" and not character.motions[mode]["keys"][index]
        for row, (direction, yaw) in enumerate(directions.items()):
            frame, ids, part_ids = renderer.render(volume, parts, character.posed_grid,
                                                    yaw, render_cell, view["posed_rays"], surface)
            if guard:
                # A neutral key uses the same static drawing and anchor as idle.
                frame = Image.new("RGBA", (render_cell, render_cell))
                frame.paste(neutral[direction], (neutral_pad, neutral_pad))
            require_margin(frame, f"{mode} {direction} frame {index + 1}")
            if visibility:
                items = {}
                for label, item in visibility.items():
                    part_id = character.parts[item["part"]]
                    materials = item["materials"]
                    solo = renderer.render(np.where(parts == part_id, volume, 0), parts,
                                           character.posed_grid, yaw, render_cell, view["posed_rays"])
                    seen = np.isin(ids, materials) & (part_ids == part_id)
                    isolated = np.isin(solo, materials)
                    if np.any(seen & ~isolated):
                        raise ValueError(f"inconsistent visibility for {mode} {direction} {label}")
                    items[label] = [int(seen.sum()), int(isolated.sum())]
                measurements[f"{direction}_{index + 1}"] = items

            frame = frame.crop((crop, crop, end, end))
            require_margin(frame, f"{mode} {direction} frame {index + 1}")
            x, y = index * cell, row * cell
            sheet.paste(frame, (x, y))
            part_atlas[y:y + cell, x:x + cell] = part_ids[crop:end, crop:end]

    return sheet, part_atlas, measurements


def bake(character, out, *, pose_volume=reslice):
    view = character.config["view"]
    directions = list(view["directions"])
    neutral_cell = view["neutral_cell"]
    renderer = Renderer(character)
    rig = Biped(character)
    clips = character.motions
    counts = {"rest": 1, "walk": len(clips["walk"]["poses"]), "attack": len(clips["attack"]["keys"])}
    pose_groups = {}
    joints = {}
    volumes = {}
    parts = {}
    ground = {}
    lowest_z = character.config["measurements"]["lowest_z"]

    for mode, count in counts.items():
        pose_groups[mode] = []
        joints[mode] = []
        for index in range(count):
            points, transforms = rig.pose(mode, index)
            check_attachment(rig, points, transforms)
            volume, part_ids = pose_volume(character, transforms)
            pose_groups[mode].append((volume, part_ids))
            key = f"{mode}_{index:02}"
            volumes[key], parts[key] = volume, part_ids
            joints[mode].append({name: point.tolist() for name, point in points.items()})
            z = np.arange(volume.shape[0]) * character.posed_grid.spacing[2] + character.posed_grid.origin[2]
            ground[key] = {
                label: float(z[np.isin(volume, materials).any(axis=(1, 2))].min())
                for label, materials in lowest_z.items()
            }

    neutral_sheet, neutral_frames = render_neutral(character, renderer)
    metadata = {
        "version": 3,
        "camera": view["camera"],
        "world_axes": {"X_positive": "anatomical left", "Y_positive": "front", "Z_positive": "up"},
        "volume_origin_xyz": character.posed_grid.origin.tolist(),
        "volume_order": "Z,Y,X",
        "voxel_size_xyz": character.posed_grid.spacing.tolist(),
        "neutral": {
            "layout": f"1 row, {len(directions)} columns",
            "directions": directions,
            "cell": [neutral_cell, neutral_cell],
            "anchor": renderer.anchor(neutral_cell),
        },
        "parts": character.parts,
        "animations": {},
    }
    motion_visibility = {}
    for mode, clip in clips.items():
        sheet, part_atlas, motion_visibility[mode] = render_motion(
            character, renderer, mode, pose_groups[mode], neutral_frames)
        cell = character.config[mode]["cell"]
        animation = {
            "rows": directions,
            "columns": counts[mode],
            "cell": [cell, cell],
            "anchor": renderer.anchor(cell),
            "fps": clip["fps"],
            "loop": mode == "walk",
            "rgba_sha256": hashlib.sha256(sheet.tobytes()).hexdigest(),
        }
        if mode == "walk":
            animation["suggested_forward_per_frame_model_units"] = clip["forward_each_frame"]
            animation.update((key, clip[key]) for key in ("poses", "contact"))
        else:
            animation["durations_ms"] = clip["durations_ms"]
            animation["phase_names"] = clip["poses"]
        metadata["animations"][mode] = animation
        sheet.save(out / f"{mode}.png")
        Image.fromarray(part_atlas).save(out / f"{mode}_part_ids.png")

    neutral_sheet.save(out / "idle.png")
    np.savez_compressed(out / "rest_part_ids.npz", parts=character.part_ids)
    np.savez_compressed(out / "posed_slices.npz", **volumes)
    np.savez_compressed(out / "posed_part_ids.npz", **parts)
    write_json(out / "joints.json", joints)
    write_json(out / "metadata.json", metadata)
    write_json(out / "measurements.json", {
        "vol_ground": ground,
        "visibility_px_full_solo": motion_visibility,
    })
