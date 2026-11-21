"""Load the assets referenced by a character manifest."""

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Grid:
    """A Z/Y/X array in model space, with origin and spacing in X/Y/Z order."""

    origin: np.ndarray
    spacing: np.ndarray
    shape: tuple[int, int, int]

    @property
    def size_xyz(self):
        return np.array(self.shape[::-1])


@dataclass(frozen=True)
class Character:
    config: dict
    model: np.ndarray
    part_ids: np.ndarray
    parts: dict[str, int]
    palette: np.ndarray
    shade_groups: np.ndarray
    source_grid: Grid
    posed_grid: Grid
    motions: dict


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_motion_lengths(motions):
    walk = motions["walk"]
    cycle = len(walk["poses"])
    if cycle < 1 or any(len(walk[key]) != cycle for key in (
            "root_bob", "root_sway", "twist", "right_arm_swing")):
        raise ValueError("walk frame arrays must match the number of poses")
    for side in ("R", "L"):
        stance = walk["contact"]["inclusive_stance_cyclic"][side]
        if (not stance or len(stance) > cycle or
                stance != [(stance[0] + offset) % cycle for offset in range(len(stance))]):
            raise ValueError(f"walk stance for {side} must be a contiguous cyclic interval")
        if any(len(walk[key]) != cycle - len(stance) for key in (
                "swing_forward", "swing_lift", "swing_pitch")):
            raise ValueError("walk swing arrays must match the number of non-stance frames")

    attack = motions["attack"]
    count = len(attack["keys"])
    if count < 1 or len(attack["poses"]) != count or len(attack["durations_ms"]) != count:
        raise ValueError("attack keys, pose names and frame durations must have the same length")
    if any(duration <= 0 for duration in attack["durations_ms"]):
        raise ValueError("attack frame durations must be positive")
    if any(clip["fps"] <= 0 for clip in motions.values()):
        raise ValueError("fps must be positive")


def load_character(path: Path):
    config = read_json(path)
    folder = path.parent
    if config["version"] != 1:
        raise ValueError("expected a version 1 character manifest")

    source = config["model"]
    with np.load(folder / source["materials"], allow_pickle=False) as archive:
        model = archive["slices"]
    with np.load(folder / source["part_ids"], allow_pickle=False) as archive:
        part_ids = archive["parts"]
    if model.ndim != 3 or min(model.shape) < 2 or model.dtype != np.uint8:
        raise ValueError("slices must be a uint8 Z/Y/X array of at least 2 voxels along each axis")
    if part_ids.shape != model.shape or part_ids.dtype != np.uint8:
        raise ValueError("parts must be a uint8 array with the same shape as slices")
    if not np.array_equal(model != 0, part_ids != 0):
        raise ValueError("parts must assign exactly the occupied voxels")

    part_names = config["rig"]["parts"]
    parts = {name: index for index, name in enumerate(part_names, start=1)}
    if len(parts) != len(part_names) or len(parts) > 255:
        raise ValueError("rig.parts must have distinct names and at most 255 entries")
    if set(np.unique(part_ids[model != 0])) != set(parts.values()):
        raise ValueError("every part must have voxels and its ID must match rig.parts")

    colors = source["palette"]
    if len(colors) > 255 or model.max() > len(colors):
        raise ValueError("palette must cover the model's nonzero material IDs")
    palette = np.array([[(0, 0, 0)] * 3] + [
        [tuple(bytes.fromhex(material[shade])) for shade in ("shadow", "base", "light")]
        for material in colors
    ], dtype=np.uint8)
    if palette.shape != (len(colors) + 1, 3, 3):
        raise ValueError("each palette shade must be a six-digit RGB color")
    groups = list(dict.fromkeys(material["group"] for material in colors))
    shade_groups = np.array([0] + [groups.index(material["group"]) + 1 for material in colors],
                            dtype=np.uint8)

    source_grid = Grid(np.array(source["origin_xyz"], dtype=float),
                       np.array(source["voxel_size_xyz"], dtype=float), model.shape)
    target = config["posed_volume"]
    origin = np.array(target["origin_xyz"], dtype=float)
    spacing = np.full(3, target["voxel_size"], dtype=float)
    size_xyz = (np.array(target["limit_xyz"], dtype=float) - origin) / spacing
    if (not np.all(source_grid.spacing > 0) or not np.all(spacing > 0)
            or not np.all(size_xyz > 0) or not np.allclose(size_xyz, np.rint(size_xyz))):
        raise ValueError("voxel sizes must be positive and posed bounds grid-aligned")
    posed_grid = Grid(origin, spacing, tuple(np.rint(size_xyz[::-1]).astype(int)))

    view = config["view"]
    directions = view["directions"]
    if len(directions) != 8 or len(set(directions.values())) != 8:
        raise ValueError("view.directions must define eight distinct yaw angles")
    cells = [view["neutral_cell"], config["walk"]["cell"], config["attack"]["cell"]]
    render_cell = view["render_cell"]
    if (type(render_cell) is not int or
            any(type(cell) is not int or not 0 < cell <= render_cell
                or (render_cell - cell) % 2 for cell in cells)):
        raise ValueError("cells must be positive integers with even, nonnegative padding")
    if view["camera"]["pixels_per_unit"] <= 0:
        raise ValueError("camera pixels_per_unit must be positive")

    motions = {mode: read_json(folder / config[mode]["clip"]) for mode in ("walk", "attack")}
    check_motion_lengths(motions)
    return Character(config, model, part_ids, parts, palette, shade_groups,
                     source_grid, posed_grid, motions)
