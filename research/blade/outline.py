"""Compare the rasterized blade with its unchanged model-space centerline."""

from dataclasses import dataclass

import numpy as np
from PIL import Image

from research.overhead.analyze import blade_samples
from research.overhead.plots import camera_projection
from spritestack.render import Renderer, normals, reslice
from spritestack.rig import Biped, unit


TARGETS = (("W", 5), ("E", 5), ("NW", 4), ("NW", 5), ("SE", 4), ("SE", 5))


@dataclass
class BladeView:
    image: Image.Image
    visible: np.ndarray
    isolated: np.ndarray
    sword: np.ndarray
    centerline: np.ndarray


def blade_axis(character):
    points = blade_samples(character)
    center = points.mean(axis=0)
    _, _, axes = np.linalg.svd(points - center, full_matrices=False)
    axis = axes[0]
    rig = character.config["rig"]["rest"]
    tip = np.subtract(rig["sword_tip"], rig["hand_R"])
    if axis @ tip < 0:
        axis = -axis
    along = (points - center) @ axis
    return center + np.array([along.min(), along.max()])[:, None] * axis


def views(character, frame, directions):
    renderer = Renderer(character)
    view = character.config["view"]
    grid = character.posed_grid
    cell = view["render_cell"]
    _, transforms = Biped(character).pose("attack", frame)
    volume, parts = reslice(character, transforms)
    surface = normals(volume, grid)
    sword_id = character.parts["sword"]
    blade_ids = character.config["measurements"]["visibility"]["blade"]["materials"]
    solo = np.where(parts == sword_id, volume, 0)
    rotation, offset = transforms["sword"]
    axis = blade_axis(character) @ rotation.T + offset
    for direction in directions:
        yaw = view["directions"][direction]
        image, material, owners = renderer.render(volume, parts, grid, yaw, cell, view["posed_rays"], surface)
        sword = owners == sword_id
        visible = np.isin(material, blade_ids) & sword
        solo_material = renderer.render(solo, parts, grid, yaw, cell, view["posed_rays"])
        solo_blade = np.isin(solo_material, blade_ids)
        projection = camera_projection(yaw, renderer.camera["pitch_deg"])
        line = (axis @ projection * renderer.camera["pixels_per_unit"] * [1, -1]
                + renderer.anchor(cell))
        yield direction, BladeView(image, visible, solo_blade, sword, line)


def components(mask, *, diagonal=True):
    pixels = set(map(tuple, np.argwhere(mask).tolist()))
    offsets = ((-1, 0), (0, -1), (0, 1), (1, 0))
    if diagonal:
        offsets += ((-1, -1), (-1, 1), (1, -1), (1, 1))
    sizes = []
    while pixels:
        queue = [pixels.pop()]
        size = 0
        while queue:
            y, x = queue.pop()
            size += 1
            for dy, dx in offsets:
                neighbor = (y + dy, x + dx)
                if neighbor in pixels:
                    pixels.remove(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def measures(view):
    axis = unit(view.centerline[1] - view.centerline[0])
    normal = np.array([-axis[1], axis[0]])
    pixels = np.argwhere(view.visible)[:, ::-1] + .5 - view.centerline[0]
    along = pixels @ axis
    across = pixels @ normal
    # Mean signed deviation per axial pixel; the spread measures zigzag of the visible center.
    bins = np.floor(along)
    centers = np.array([across[bins == pos].mean() for pos in np.unique(bins)])
    intact = components(view.visible)
    solo = int(view.isolated.sum())
    return {
        "visible": len(pixels), "isolated": solo,
        "components": intact,
        "edge_components": components(view.visible, diagonal=False),
        "length_px": round(float(np.ptp(along)), 3) if len(along) else 0,
        "center_spread_px": round(float(np.ptp(centers)), 3) if len(centers) else 0,
        "area_fraction": round(len(pixels) / solo, 3) if solo else 0,
    }
