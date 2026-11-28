"""Bake the configured character into PNG sheets, volumes and metadata."""

import copy
import dataclasses
from fractions import Fraction
import hashlib
import json

import numpy as np
from PIL import Image

from .bow import pose_bow, unstrung
from .effects import crystal_burst
from .render import Renderer, fine_parts, normals, reslice
from .rig import Biped, transform
from .secondary import Secondary


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


def neutral_layout(character, renderer):
    view = character.config["view"]
    return {
        "layout": f"1 row, {len(view['directions'])} columns",
        "directions": list(view["directions"]),
        "cell": [view["neutral_cell"], view["neutral_cell"]],
        "anchor": renderer.anchor(view["neutral_cell"]),
    }


def view_for_cell(character, cell):
    """Return the character as drawn in an idle cell of the given size.

    The configured view.neutral_cell uses the view unchanged. Another size uses the
    optional comparison_view: the same model and camera angle, with its own pixel
    density, cell and anchor. Nothing is scaled implicitly.
    """
    view = character.config["view"]
    if cell == view["neutral_cell"]:
        return character
    variant = character.config.get("comparison_view")
    if not variant or variant.get("neutral_cell") != cell:
        raise ValueError(f"no {cell}px idle view: character.json needs a comparison_view "
                         f"with neutral_cell {cell}")
    pivot = variant["base_pivot"]
    if (type(cell) is not int or cell <= 0 or variant["pixels_per_unit"] <= 0 or len(pivot) != 2
            or not all(0 <= coordinate < cell for coordinate in pivot)):
        raise ValueError("comparison_view needs a positive pixel density and an anchor inside its cell")
    config = copy.deepcopy(character.config)
    camera = config["view"]["camera"]
    camera["pixels_per_unit"] = variant["pixels_per_unit"]
    camera["base_pivot"] = pivot
    config["view"]["neutral_cell"] = config["view"]["render_cell"] = cell
    return dataclasses.replace(character, config=config)


def idle_cells(character):
    """The idle cell sizes a character declares: view.neutral_cell, then comparison_view if any."""
    cells = [character.config["view"]["neutral_cell"]]
    variant = character.config.get("comparison_view")
    if variant and variant.get("neutral_cell") not in cells:
        cells.append(variant["neutral_cell"])
    return cells


def bake_idle(character, out, cells=None):
    """Bake only the idle eight directions from the rest model; no poses are computed.

    cells defaults to every idle size the character declares (idle_cells). The
    standard cell writes idle.png, metadata.json (the CLI layout with no
    animations; the volume fields describe the rest grid of rest_part_ids.npz) and
    rest_part_ids.npz. Each other cell writes idle-<cell>.png and idle-<cell>.json.
    """
    standard = character.config["view"]["neutral_cell"]
    variants = [(cell, view_for_cell(character, cell)) for cell in (cells or idle_cells(character))]
    for cell, seen in variants:
        renderer = Renderer(seen)
        sheet, _ = render_neutral(seen, renderer)
        if cell == standard:
            grid = character.source_grid
            sheet.save(out / "idle.png")
            np.savez_compressed(out / "rest_part_ids.npz", parts=character.part_ids)
            write_json(out / "metadata.json", {
                "version": 3,
                "camera": character.config["view"]["camera"],
                "world_axes": {"X_positive": "anatomical left", "Y_positive": "front", "Z_positive": "up"},
                "volume_origin_xyz": grid.origin.tolist(),
                "volume_order": "Z,Y,X",
                "voxel_size_xyz": grid.spacing.tolist(),
                "neutral": neutral_layout(seen, renderer),
                "parts": character.parts,
                "animations": {},
            })
        else:
            sheet.save(out / f"idle-{cell}.png")
            write_json(out / f"idle-{cell}.json", {
                "description": "Comparison sheet: the same voxel model as idle.png "
                               f"at {Fraction(cell, standard)} the pixel density.",
                "camera": seen.config["view"]["camera"],
                "neutral": neutral_layout(seen, renderer),
                "rgba_sha256": hashlib.sha256(sheet.tobytes()).hexdigest(),
            })


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


def add_glint(rgba, visible):
    """Add a small flash in the empty space around a visible emitter."""
    ys, xs = np.nonzero(visible)
    if not len(xs):
        return
    x, y = round(xs.mean()), round(ys.mean())
    light = rgba[ys, xs, :3].mean(axis=0).round().astype(np.uint8)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        for distance in (3, 4):
            u, v = x + dx * distance, y + dy * distance
            if 0 <= v < rgba.shape[0] and 0 <= u < rgba.shape[1] and not rgba[v, u, 3]:
                rgba[v, u] = (*light, 255)


def release_attachments(clip, posed, rig, directions):
    """Keep the release socket on the wrist; independently pose the same item for the preview."""
    releases = [e for e in clip.get("events", []) if "released_part" in e]
    if not releases:
        return
    points = [joints for joints, _ in posed]
    occupied = set()
    for event in attack_events({**clip, "events": releases}, points, directions):
        part, start, end = event["released_part"], event["frame"], event["rearm_frame"]
        if part not in rig.attachments or rig.attachments[part]["marker"] != event["marker"]:
            raise ValueError("released_part needs its own attachment marker")
        if type(end) is not int or not 0 < start < end < len(posed):
            raise ValueError("release and rearm must be ordered between the two ready poses")
        distance = event.get("preview_distance", 0)
        if not np.isfinite(distance) or distance < 0:
            raise ValueError("preview_distance must be finite and nonnegative")
        for i in range(start, end):
            transforms = posed[i][1]
            if not clip["keys"][i] or (part, i) in occupied:
                raise ValueError("release overlaps a neutral pose or another release of this part")
            occupied.add((part, i))
            if i == start and distance:
                rotation, shift = transforms[part]
                transforms[part] = rotation, shift + distance * np.asarray(event["direction_model_xyz"])
            else:
                transforms[part] = None


def render_motion(character, renderer, mode, poses, neutral):
    view = character.config["view"]
    directions = view["directions"]
    cell = character.config[mode]["cell"]
    render_cell = max(view["render_cell"], cell)
    neutral_pad = (render_cell - view["neutral_cell"]) // 2
    crop = (render_cell - cell) // 2
    end = crop + cell
    count = len(poses)
    sheet = Image.new("RGBA", (count * cell, len(directions) * cell))
    part_atlas = np.zeros((sheet.height, sheet.width), dtype=np.uint8)
    measurements = {}
    visibility = character.config["measurements"]["visibility"]
    fine = fine_parts(character, mode)

    for index, (volume, parts) in enumerate(poses):
        grid = character.posed_grid
        rays = view["posed_rays"]
        if mode == "breathe":
            key = character.motions[mode]["keys"][index]
            if key["lift"] == key["lean"] == 0:
                # Match the neutral renderer exactly, including which side of a voxel edge a ray hits.
                volume, parts, grid = character.model, character.part_ids, character.source_grid
                rays = view["neutral_rays"]
        surface = normals(volume, grid)
        clip_key = character.motions[mode]["keys"][index] if mode == "attack" else {}
        guard = mode == "attack" and not clip_key
        for row, (direction, yaw) in enumerate(directions.items()):
            frame, ids, part_ids = renderer.render(volume, parts, grid, yaw, render_cell, rays, surface, fine)
            if glow := clip_key.get("glow", 0):
                # Use visible emitter pixels so an occluded source produces no light.
                materials = character.config[mode]["glow_materials"]
                mask = np.isin(ids, materials)
                if part := character.config[mode].get("glow_part"):
                    mask &= part_ids == character.parts[part]
                rgba = np.array(frame)
                color = np.asarray(character.config[mode].get("glow_rgb", 255))
                rgba[mask, :3] = np.rint((1 - glow) * rgba[mask, :3] + glow * color).astype(np.uint8)
                if clip_key.get("glint", False):
                    add_glint(rgba, mask)
                frame = Image.fromarray(rgba)
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
                                           grid, yaw, render_cell, rays,
                                           fine=fine)
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


def bake(character, out, *, pose_volume=reslice, motions=None):
    """Bake neutral and the requested (by default all configured) motion sheets."""
    if motions is None:
        motions = tuple(character.motions)
    if not motions or set(motions) - character.motions.keys() or len(set(motions)) != len(motions):
        raise ValueError("requested motions must be distinct and present in the manifest")
    view = character.config["view"]
    directions = list(view["directions"])
    renderer = Renderer(character)
    rig = Biped(character)
    clips = {mode: clip for mode, clip in character.motions.items() if mode in motions}
    counts = {"rest": 1, **{mode: len(clip["poses"]) for mode, clip in clips.items()}}
    pose_groups = {}
    joints = {}
    volumes = {}
    parts = {}
    ground = {}
    lowest_z = character.config["measurements"]["lowest_z"]

    secondary = None
    if "walk" in clips and character.config["walk"].get("secondary"):
        if pose_volume is not reslice:
            raise ValueError("walk.secondary cannot be combined with another pose_volume")
        secondary = Secondary(character, rig.walk_clip, rig.rest)

    for mode, count in counts.items():
        posed_character = character.for_motion(mode)
        pose_groups[mode] = []
        joints[mode] = []
        posed = [rig.pose(mode, index) for index in range(count)]
        for points, transforms in posed:
            check_attachment(rig, points, transforms)
        if mode == "attack":
            release_attachments(clips[mode], posed, rig, view["directions"])
        bow = character.config["attack"].get("bow") if mode == "attack" else None
        body = unstrung(posed_character, bow) if bow else posed_character
        if mode == "attack" and character.config["attack"].get("follow_cloth"):
            if pose_volume is not reslice:
                raise ValueError("attack.follow_cloth requires the rigid pose volume")
            cloth = Secondary(body, clips[mode], rig.rest, mode=mode)
            volumes_of_mode = cloth.pose_volumes(body, [t for _, t in posed])
        elif mode == "walk" and secondary:
            volumes_of_mode = secondary.pose_volumes(character, [t for _, t in posed])
        elif mode == "breathe" and character.config[mode].get("secondary"):
            cloth = Secondary(body, clips[mode], rig.rest, mode=mode)
            volumes_of_mode = cloth.pose_volumes(body, [t for _, t in posed])
        else:
            volumes_of_mode = [pose_volume(body, transforms) for _, transforms in posed]
        if bow:
            pose_bow(posed_character, posed, volumes_of_mode)
        for index, ((points, transforms), (volume, part_ids)) in enumerate(zip(posed, volumes_of_mode)):
            if mode == "attack" and clips[mode]["keys"][index].get("burst"):
                owner = max(character.parts.values()) + 1 + int(bool(bow))
                if owner > 255:
                    raise ValueError("the burst needs a free part ID")
                crystal_burst(posed_character, character.config[mode]["burst"], clips[mode]["keys"][index],
                              points, volume, part_ids, owner)
            pose_groups[mode].append((volume, part_ids))
            key = f"{mode}_{index:02}"
            volumes[key], parts[key] = volume, part_ids
            joints[mode].append({name: point.tolist() for name, point in points.items()})
            grid = posed_character.posed_grid
            z = np.arange(volume.shape[0]) * grid.spacing[2] + grid.origin[2]
            ground[key] = {}
            for label, materials in lowest_z.items():
                occupied_z = z[np.isin(volume, materials).any(axis=(1, 2))]
                ground[key][label] = float(occupied_z.min()) if occupied_z.size else None

    neutral_sheet, neutral_frames = render_neutral(character, renderer)
    metadata = {
        "version": 3,
        "camera": view["camera"],
        "world_axes": {"X_positive": "anatomical left", "Y_positive": "front", "Z_positive": "up"},
        "volume_origin_xyz": character.posed_grid.origin.tolist(),
        "volume_order": "Z,Y,X",
        "voxel_size_xyz": character.posed_grid.spacing.tolist(),
        "neutral": neutral_layout(character, renderer),
        "parts": character.parts,
        "animations": {},
    }
    motion_visibility = {}
    for mode, clip in clips.items():
        sheet, part_atlas, motion_visibility[mode] = render_motion(
            character.for_motion(mode), renderer, mode, pose_groups[mode], neutral_frames)
        cell = character.config[mode]["cell"]
        animation = {
            "rows": directions,
            "columns": counts[mode],
            "cell": [cell, cell],
            "anchor": renderer.anchor(cell),
            "fps": rig.walk_clip["fps"] if mode == "walk" else clip["fps"],
            "loop": mode != "attack",
            "rgba_sha256": hashlib.sha256(sheet.tobytes()).hexdigest(),
        }
        if mode == "walk":
            animation["suggested_forward_per_frame_model_units"] = rig.walk_clip["forward_each_frame"]
            animation.update((key, clip[key]) for key in ("poses", "contact"))
            if note := character.config["walk"].get("stance_note"):
                animation["contact"] = {**clip["contact"], "stance_note": note}
        elif mode == "breathe":
            animation["poses"] = clip["poses"]
        else:
            animation["durations_ms"] = clip["durations_ms"]
            animation["phase_names"] = clip["poses"]
            if clip.get("events"):
                animation["events"] = attack_events(clip, joints[mode], view["directions"])
            if "posed_volume" in character.config[mode]:
                animation["posed_volume"] = character.config[mode]["posed_volume"]
            if character.config[mode].get("bow"):
                animation["transient_parts"] = {"arrow": max(character.parts.values()) + 1}
            if character.config[mode].get("burst"):
                extras = animation.setdefault("transient_parts", {})
                extras["burst"] = max(character.parts.values()) + 1 + len(extras)
        metadata["animations"][mode] = animation
        sheet.save(out / f"{mode}.png")
        Image.fromarray(part_atlas).save(out / f"{mode}_part_ids.png")

    neutral_sheet.save(out / "idle.png")
    np.savez_compressed(out / "rest_part_ids.npz", parts=character.part_ids)
    np.savez_compressed(out / "posed_slices.npz", **volumes)
    np.savez_compressed(out / "posed_part_ids.npz", **parts)
    write_json(out / "joints.json", joints)
    write_json(out / "metadata.json", metadata)
    measurements = {
        "vol_ground": ground,
        "visibility_px_full_solo": motion_visibility,
    }
    if secondary:
        measurements["walk_secondary_deg"] = secondary.angles
    write_json(out / "measurements.json", measurements)


def attack_events(clip, joints, directions):
    events = []
    for event in clip["events"]:
        frame = event["frame"]
        if type(frame) is not int or not 0 <= frame < len(joints):
            raise ValueError("attack event frame outside clip")
        pose = joints[frame]
        position = pose[event["marker"]]
        if event.get("direction_source") == "marker_travel":
            if frame == 0:
                raise ValueError("marker travel needs a preceding frame")
            direction = np.subtract(position, joints[frame-1][event["marker"]])
        elif "arrow_tip" in pose:
            direction = np.subtract(pose["arrow_tip"], pose["arrow_nock"])
        else:
            direction = np.asarray(clip["keys"][frame]["aim"], dtype=float)
        length = np.linalg.norm(direction)
        if length < 1e-8:
            raise ValueError("attack event needs a nonzero direction")
        direction = direction / length
        by_row = {}
        for row, yaw in directions.items():
            angle = np.deg2rad(yaw)
            x, y, z = direction
            by_row[row] = [x*np.cos(angle) + y*np.sin(angle), -x*np.sin(angle) + y*np.cos(angle), z]
        fields = dict(event)
        if "released_part" in event:
            fields["baked_projectile_frames"] = int(event.get("preview_distance", 0) > 0)
        events.append({**fields, "time_ms": sum(clip["durations_ms"][:frame]),
                       "position_model_xyz": position,
                       "direction_model_xyz": direction.tolist(), "direction_by_row": by_row})
    return events
