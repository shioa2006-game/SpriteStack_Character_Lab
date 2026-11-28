"""Pose a string and a single display arrow in the same voxel grid as the body."""

from dataclasses import replace

import numpy as np

from .render import reslice
from .rig import transform, unit, vec


def unstrung(character, bow):
    owner = character.parts[bow["part"]]
    selected = (character.part_ids == owner) & (character.model == bow["string_material"])
    if not selected.any():
        raise ValueError("bow.string_material must identify the resting string")
    return replace(character, model=np.where(selected, 0, character.model),
                   part_ids=np.where(selected, 0, character.part_ids))


def stroke(volume, parts, grid, a, b, radius, material, owner):
    """Fill empty cells along a capsule. Existing hands and solid limbs keep ownership."""
    delta = b - a
    low = np.floor((np.minimum(a, b) - radius - grid.origin) / grid.spacing).astype(int)
    high = np.ceil((np.maximum(a, b) + radius - grid.origin) / grid.spacing).astype(int)
    if np.any(low < 0) or np.any(high > grid.size_xyz):
        raise ValueError("bow or arrow exceeds posed volume")
    box = tuple(slice(lo, hi) for lo, hi in zip(low[::-1], high[::-1]))
    indices = np.indices(volume[box].shape).transpose(1, 2, 3, 0)[..., ::-1]
    points = grid.origin + (low + indices + .5) * grid.spacing
    t = np.clip((points - a) @ delta / max(delta @ delta, 1e-10), 0, 1)
    fill = (np.sum((points - a - t[..., None] * delta)**2, axis=-1) <= radius**2) & (parts[box] == 0)
    parts[box][fill] = owner
    volume[box][fill] = material


def pose_bow(character, poses, volumes):
    settings = character.config["attack"]
    bow = settings["bow"]
    keys = character.motions["attack"]["keys"]
    part = bow["part"]
    hand = character.config["rig"]["attachments"][part]["hand"]
    draw_hand = "hand_R" if hand == "hand_L" else "hand_L"
    arrow_id = max(character.parts.values()) + 1
    if arrow_id > 255:
        raise ValueError("the display arrow needs a free part ID")
    previous_shot = None
    for i, ((joints, transforms), (volume, parts), key) in enumerate(zip(poses, volumes, keys, strict=True)):
        if not key:
            # The unstrung copy is for posed frames only. Restore the exact rigid guard volume.
            volumes[i] = reslice(character, transforms)
            previous_shot = None
            continue
        tips = [transform(transforms[part], vec(tip)) for tip in bow["tips"]]
        nock = (tips[0] + tips[1]) / 2
        if key.get("nocked"):
            nock = joints[draw_hand]
        joints["string_center"] = nock
        for tip in tips:
            stroke(volume, parts, character.posed_grid, tip, nock, bow["string_radius"],
                   bow["string_material"], character.parts[part])
        if key.get("nocked"):
            direction = unit(joints[hand] + [0, 0, .65] - nock)
            previous_shot = (nock.copy(), direction)
        elif "flight_offset" in key:
            if previous_shot is None:
                raise ValueError("flight_offset needs a preceding nocked pose")
            origin, direction = previous_shot
            nock = origin + key["flight_offset"] * direction
        else:
            previous_shot = None
            continue
        tip = nock + bow["length"] * direction
        joints["arrow_nock"], joints["arrow_tip"] = nock, tip
        for a, b, r, material in (
                (tip - 1.2*direction, tip, .67, "point_material"),
                (nock, nock + 1.6*direction, .72, "feather_material"),
                (nock, tip, bow["shaft_radius"], "shaft_material")):
            stroke(volume, parts, character.posed_grid, a, b, r, bow[material], arrow_id)
