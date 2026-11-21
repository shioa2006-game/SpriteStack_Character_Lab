"""Inverse-sampled voxel volumes and orthographic pixel rendering."""

import math

import numpy as np
from PIL import Image, ImageFilter

from .rig import unit, vec


def reslice(character, transforms):
    source = character.source_grid
    target = character.posed_grid
    volume = np.zeros(target.shape, dtype=np.uint8)
    part_ids = np.zeros_like(volume)

    # Later parts win at overlaps. Keeping this order is part of the bake contract.
    for name, part_id in character.parts.items():
        occupied = np.argwhere(character.part_ids == part_id)[:, ::-1]
        low = occupied.min(axis=0)
        high = occupied.max(axis=0) + 1
        corners = np.array([
            source.origin + np.array((x, y, z)) * source.spacing
            for x in (low[0], high[0])
            for y in (low[1], high[1])
            for z in (low[2], high[2])
        ])
        rotation, translation = transforms[name]
        bounds = (corners @ rotation.T + translation - target.origin) / target.spacing
        start = np.floor(bounds.min(axis=0)).astype(int)
        stop = np.ceil(bounds.max(axis=0)).astype(int) + 1
        if np.any(start <= 0) or np.any(stop >= target.size_xyz):
            raise ValueError(f"posed part {name} exceeds the padded volume bounds")

        coords = np.stack(np.meshgrid(*(np.arange(a, b) for a, b in zip(start, stop)),
                                      indexing="ij"), axis=-1)
        points = target.origin + (coords + .5) * target.spacing
        indices = np.floor(((points - translation) @ rotation - source.origin)
                           / source.spacing).astype(int)
        valid = ((indices >= 0) & (indices < source.size_xyz)).all(axis=-1)
        sampled = tuple(indices[valid][:, ::-1].T)
        owned = character.part_ids[sampled] == part_id
        destination = tuple(coords[valid][owned][:, ::-1].T)
        volume[destination] = character.model[sampled][owned]
        part_ids[destination] = part_id

    return volume, part_ids


def normals(volume, grid):
    density = (volume > 0).astype(np.float32)
    for axis in range(3):
        padding = [(0, 0)] * 3
        padding[axis] = (1, 1)
        padded = np.pad(density, padding)
        window = [slice(None)] * 3
        window[axis] = slice(None, -2)
        left = padded[tuple(window)]
        window[axis] = slice(2, None)
        right = padded[tuple(window)]
        density = .25 * left + .5 * density + .25 * right
    z, y, x = np.gradient(density, *grid.spacing[::-1])
    return np.stack((-x, -y, -z), axis=-1)


class Renderer:
    def __init__(self, character):
        self.view = character.config["view"]
        self.camera = self.view["camera"]
        self.palette = character.palette
        self.shade_groups = character.shade_groups

    def anchor(self, cell):
        pad = (cell - self.view["neutral_cell"]) // 2
        return [coordinate + pad for coordinate in self.camera["base_pivot"]]

    def render(self, volume, parts, grid, yaw, cell, rays, surface=None):
        """Return material IDs alone for visibility passes, or RGBA plus ID maps."""
        theta = math.radians(yaw)
        pitch = math.radians(self.camera["pitch_deg"])
        right = vec([math.cos(theta), math.sin(theta), 0])
        forward = vec([-math.sin(theta), math.cos(theta), 0])
        vertical = vec([0, 0, 1])
        eye = forward * math.cos(pitch) + vertical * math.sin(pitch)
        up = -forward * math.sin(pitch) + vertical * math.cos(pitch)
        pivot_x, pivot_y = self.anchor(cell)
        yy, xx = np.indices((cell, cell))
        scale = self.camera["pixels_per_unit"]
        origin = (((xx + .5 - pivot_x) / scale)[..., None] * right
                  + ((pivot_y - yy - .5) / scale)[..., None] * up)

        ids = np.zeros((cell, cell), dtype=np.uint8)
        hits = np.zeros((cell, cell, 3), dtype=np.int16)
        depth = np.full((cell, cell), -100., dtype=np.float32)
        size = grid.size_xyz
        for distance in np.arange(*rays):
            indices = np.floor((origin + distance * eye - grid.origin) / grid.spacing).astype(np.int16)
            pending = (ids == 0) & ((indices >= 0) & (indices < size)).all(axis=-1)
            samples = indices[pending][:, ::-1]
            material = volume[tuple(samples.T)]
            ids[pending] = material
            if surface is not None:
                visible = pending & (ids > 0)
                hits[visible] = samples[material > 0]
                depth[visible] = distance
        if surface is None:
            return ids

        hit_indices = tuple(hits.transpose(2, 0, 1))
        selected = ids > 0
        rendered_parts = parts[hit_indices]
        rendered_parts[~selected] = 0
        gradient = surface[hit_indices]
        light = unit(-.42 * right + .32 * forward + vec([0, 0, .85]))
        value = (gradient @ light) / np.maximum(np.linalg.norm(gradient, axis=-1), .001)
        tones = np.where(value > .45, 2, np.where(value < -.38, 0, 1))
        rgba = np.zeros((cell, cell, 4), dtype=np.uint8)
        rgba[selected, :3] = self.palette[ids[selected], tones[selected]]
        rgba[selected, 3] = 255

        group = self.shade_groups[ids]
        for axis, step in ((0, -1), (0, 1), (1, -1), (1, 1)):
            neighbor = np.roll(group, step, axis=axis)
            neighbor_depth = np.roll(depth, step, axis=axis)
            seam = selected & (neighbor > 0) & (group != neighbor) & (depth - neighbor_depth > 1.8)
            rgba[seam, :3] = self.palette[ids[seam], 0]
        expanded = np.asarray(Image.fromarray(rgba).getchannel("A").filter(ImageFilter.MaxFilter(3))) > 0
        rgba[expanded & ~selected] = [*self.view["outline_rgb"], 255]
        return Image.fromarray(rgba), ids, rendered_parts
