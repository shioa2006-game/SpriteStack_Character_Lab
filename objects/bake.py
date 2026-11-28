"""Bake labelled rigid objects with the same ray renderer used for the adventurers."""
import argparse
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

from spritestack.bake import require_margin, write_json
from spritestack.character import Grid, read_json
from spritestack.render import Renderer, normals, reslice
from spritestack.rig import about, rotate

DIRECTIONS = dict(zip(("S", "SW", "W", "NW", "N", "NE", "E", "SE"), range(0, -360, -45)))
ROOT = Path(__file__).resolve().parent


@dataclass
class ObjectModel:
    spec: dict
    config: dict
    model: np.ndarray
    part_ids: np.ndarray
    parts: dict
    palette: np.ndarray
    shade_groups: np.ndarray
    source_grid: Grid
    posed_grid: Grid


def load(folder, archive=None):
    spec = read_json(folder / "object.json")
    with np.load(archive or folder / "model.npz", allow_pickle=False) as data:
        material, parts = data["slices"], data["parts"]
    grid = Grid.from_bounds(spec["source_grid"])
    owners = {name: i for i, name in enumerate(spec["parts"], 1)}
    palette = np.array([[(0, 0, 0)] * 3] + [[tuple(bytes.fromhex(c)) for c in shades]
                       for shades in spec["palette"].values()], dtype=np.uint8)
    if (material.shape != grid.shape or parts.shape != grid.shape
            or material.dtype != np.uint8 or parts.dtype != np.uint8
            or not np.array_equal(material > 0, parts > 0) or material.max() >= len(palette)
            or set(np.unique(parts)) != {0, *owners.values()}):
        raise ValueError("material/part slices do not match the object manifest")
    cell, anchor = spec["cell"], spec["anchor"]
    camera = {"pitch_deg": 24, "pixels_per_unit": 1.5, "base_pivot": anchor}
    view = {"neutral_cell": cell, "camera": camera, "outline_rgb": [37, 29, 41]}
    return ObjectModel(spec, {"view": view}, material, parts, owners, palette,
                       np.arange(len(palette)), grid, grid)


def pose(model, state, angle):
    """Rotate selected parts around one model-space axis, optionally settle on Z=0."""
    joint = model.spec.get("rotation", {})
    pivot = np.array(joint.get("pivot_xyz", [0, 0, 0]))
    rotation, translation = about(rotate(joint.get("axis_xyz", [1, 0, 0]), angle), pivot, pivot)
    source = model.source_grid
    matrices, corners = {}, []
    lift = 0.
    if joint.get("settle"):
        centers = source.origin + (np.argwhere(model.model)[:, ::-1] + .5) * source.spacing
        # Exact support of rotated voxel cubes, including the half-voxel extent.
        bottom = (centers @ rotation[2] + translation[2]).min() - abs(rotation[2]) @ source.spacing / 2
        lift = -float(bottom)
        translation[2] += lift
    for name, part in model.parts.items():
        if name not in state.get("include", model.parts):
            matrices[name] = None
            continue
        r, t = (rotation, translation) if name in joint.get("parts", model.parts) else (np.eye(3), np.zeros(3))
        t = t + state.get("offset_xyz", [0, 0, 0])
        matrices[name] = (r, t)
        indices = np.argwhere(model.part_ids == part)[:, ::-1]
        bounds = np.stack((indices.min(0), indices.max(0) + 1), axis=1)
        points = source.origin + np.array(list(product(*bounds))) * source.spacing
        corners.extend(points @ r.T + t)
    corners = np.array(corners)
    start = np.floor(corners.min(0) / source.spacing) - 3
    stop = np.ceil(corners.max(0) / source.spacing) + 4
    grid = Grid(start * source.spacing, source.spacing, tuple((stop - start).astype(int)[::-1]))
    volume, parts = reslice(replace(model, posed_grid=grid), matrices)
    return volume, parts, grid, matrices, lift


def render_pose(model, volume, parts, grid, directions=DIRECTIONS):
    """Trace only the projected occupied window, then align it inside the delivery cell."""
    surface = normals(volume, grid)
    indices = np.argwhere(volume)[:, ::-1]
    limits = np.stack((indices.min(0), indices.max(0) + 1), axis=1)
    corners = grid.origin + np.array(list(product(*limits))) * grid.spacing
    view = model.config["view"]
    camera = view["camera"]
    cell, anchor = view["neutral_cell"], np.array(camera["base_pivot"])
    pitch = np.deg2rad(camera["pitch_deg"])
    scale = camera["pixels_per_unit"]
    frames = []
    for direction in directions:
        theta = np.deg2rad(DIRECTIONS[direction])
        right = np.array([np.cos(theta), np.sin(theta), 0])
        forward = np.array([-right[1], right[0], 0])
        up = -forward * np.sin(pitch) + [0, 0, np.cos(pitch)]
        eye = forward * np.cos(pitch) + [0, 0, np.sin(pitch)]
        screen = anchor + np.stack((corners @ right, -(corners @ up)), axis=1) * scale
        low = np.floor(screen.min(0)).astype(int) - 2
        size = int(max(np.ceil(screen.max(0)) - low)) + 3
        # Cardinal rays can lie exactly on a voxel boundary. Break those ties
        # consistently even when the same module is rendered at another origin.
        raster_pivot = anchor - low + 1e-7
        crop_view = dict(view, neutral_cell=size, camera=dict(camera, base_pivot=raster_pivot.tolist()))
        renderer = Renderer(replace(model, config={"view": crop_view}))
        depth = corners @ eye
        rays = [np.ceil(depth.max()) + .5, np.floor(depth.min()) - .5, -.18]
        frame, _, _ = renderer.render(volume, parts, grid, DIRECTIONS[direction], size, rays, surface)
        bbox = np.array(frame.getbbox()) + np.tile(low, 2)
        if min(bbox[:2]) < 1 or max(bbox[2:]) >= cell:
            raise ValueError(f"{direction} outside cell: {bbox}")
        aligned = Image.new("RGBA", (cell, cell))
        aligned.paste(frame, tuple(low))
        require_margin(aligned, direction)
        frames.append(aligned)
    return frames


def save_gif(path, strips, times, loop):
    # All eight directions in a 4 x 2 contact sheet per instant. A fixed matte
    # makes single-play GIFs portable across decoders with different disposal rules.
    cell = strips[0][0].width
    panels = []
    for strip in strips:
        panel = Image.new("RGB", (cell * 4, cell * 2), "#d3c8b3")
        for i, frame in enumerate(strip):
            panel.paste(frame, (i % 4 * cell, i // 4 * cell), frame)
        panels.append(panel)
    panels[0].save(path, save_all=True, append_images=panels[1:], duration=times,
                   optimize=False, **({"loop": 0} if loop else {}))


def bake(model, out):
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent, prefix="object-bake-") as scratch:
        staged = Path(scratch) / "sheets"
        staged.mkdir()
        write_sheets(model, staged)
        staged.rename(out)


def write_sheets(model, out):
    spec = model.spec
    cell, anchor = spec["cell"], spec["anchor"]
    cache = {}
    for name, state in spec["views"].items():
        animated = "durations_ms" in state
        angles = state["angles_deg"]
        if not len(angles) or not np.all(np.isfinite(angles)):
            raise ValueError(f"{name} needs finite pose angles")
        if animated:
            times = state["durations_ms"]
            if len(times) != len(angles) or any(type(t) is not int or t <= 0 or t % 10 for t in times):
                raise ValueError(f"{name} needs one positive, GIF-representable duration per pose")
        elif len(angles) != 1:
            raise ValueError(f"{name} needs one pose for a neutral strip")
        strips, lifts, bounds = [], [], []
        for angle in state["angles_deg"]:
            key = (angle, tuple(state.get("include", ())), tuple(state.get("offset_xyz", ())))
            if key not in cache:
                vol, parts, grid, _, lift = pose(model, state, angle)
                indices = np.argwhere(vol)[:, ::-1]
                box = grid.origin + np.stack((indices.min(0), indices.max(0)+1)) * grid.spacing
                cache[key] = render_pose(model, vol, parts, grid), round(lift, 6), box.tolist()
            frames, lift, box = cache[key]
            strips.append(frames)
            lifts.append(lift)
            bounds.append(box)
        cols, rows = (len(strips), len(DIRECTIONS)) if animated else (len(DIRECTIONS), 1)
        sheet = Image.new("RGBA", (cols * cell, rows * cell))
        for i, strip in enumerate(strips):
            for j, frame in enumerate(strip):
                pos = (i, j) if animated else (j, 0)
                sheet.paste(frame, (pos[0] * cell, pos[1] * cell))
        sheet.save(out / (name + ".png"))
        layout = {"cell": [cell, cell], "anchor": anchor, "angles_deg": state["angles_deg"],
                  "bounds_xyz_by_frame": bounds}
        meta = {"object": spec["id"], "state": state.get("name", name),
                "camera": model.config["view"]["camera"], "camera_yaw_deg": DIRECTIONS,
                "geometry": spec["geometry"], "placement": state["placement"]}
        if "rotation" in spec:
            meta["rotation"] = spec["rotation"]
        if "include" in state:
            meta["module"] = {"parts": state["include"], "offset_xyz": state["offset_xyz"]}
        if spec.get("rotation", {}).get("settle"):
            layout["floor_adjustment_z"] = lifts
        if animated:
            layout.update(rows=list(DIRECTIONS), columns=cols, durations_ms=state["durations_ms"],
                          loop=state["loop"])
            if "next" in state:
                layout["next"] = state["next"]
            meta["animations"] = {name: layout}
            save_gif(out / (name + ".gif"), strips, state["durations_ms"], state["loop"])
        else:
            layout.update(directions=list(DIRECTIONS), layout="1 row, 8 columns")
            meta["neutral"] = layout
            save_gif(out / (name + ".gif"), strips, [0], False)
            if name == "idle" and spec.get("thumbnail_direction"):
                frame = strips[0][list(DIRECTIONS).index(spec["thumbnail_direction"])]
                frame.crop(frame.getbbox()).save(out / "cover.png")
        write_json(out / ("metadata.json" if name == "idle" else name + ".json"), meta)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("object", help="object ID in objects/")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", type=Path, help="test an independently rebuilt NPZ")
    args = parser.parse_args()
    bake(load(ROOT / args.object, args.model), args.out)


if __name__ == "__main__":
    main()
