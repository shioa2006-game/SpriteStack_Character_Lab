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

    def render(self, volume, parts, grid, yaw, cell, rays, surface=None, fine=None):
        """Return material IDs alone for visibility passes, or RGBA plus ID maps.

        fine (optional, see fine_parts): parts drawn with several rays per pixel, such as
        a thin blade that one ray per pixel breaks into dots when seen edge-on. Around these
        parts, a pixel enough of whose rays meet one of them first shows it too (see
        _fine). What is in front of them still hides them."""
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
            if surface is not None or fine is not None:
                visible = pending & (ids > 0)
                hits[visible] = samples[material > 0]
                depth[visible] = distance
        if fine is not None:
            self._fine(volume, parts, grid, rays, fine, (right, eye, up), (pivot_x, pivot_y),
                       ids, hits, depth)
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
        # With fine seam "behind", a fine part in front of another surface keeps its tones
        # and the dark seam goes on the surface behind it (a 1 px blade would otherwise be
        # all seam, in its darkest tone).
        behind = fine is not None and fine.get("seam") == "behind"
        front_fine = np.isin(rendered_parts, fine["part_ids"]) if behind else np.zeros_like(selected)
        for axis, step in ((0, -1), (0, 1), (1, -1), (1, 1)):
            neighbor = np.roll(group, step, axis=axis)
            neighbor_depth = np.roll(depth, step, axis=axis)
            seam = selected & (neighbor > 0) & (group != neighbor) & (depth - neighbor_depth > 1.8)
            moved = np.roll(seam & front_fine, -step, axis=axis) & ~front_fine
            seam = (seam & ~front_fine) | moved
            rgba[seam, :3] = self.palette[ids[seam], 0]
        expanded = np.asarray(Image.fromarray(rgba).getchannel("A").filter(ImageFilter.MaxFilter(3))) > 0
        rgba[expanded & ~selected] = [*self.view["outline_rgb"], 255]
        return Image.fromarray(rgba), ids, rendered_parts

    def _fine(self, volume, parts, grid, rays, fine, basis, pivot, ids, hits, depth):
        """Add fine-part pixels around the fine parts (ids, hits and depth in place).

        Per pixel, from n x n rays: share, the rays on which a fine part is the first hit,
        and hidden, the rays that meet a fine part behind something else. Without a line
        share, a pixel is drawn when share reaches the coverage. With one, when the shape
        (share plus hidden) reaches the coverage, or is the largest across a thin blade
        (a ridge in x or y) and reaches the line share, and share reaches the line share.
        A drawn pixel shows the fine part when share is not below hidden: a fist around a
        grip keeps its pixels. Pixels the single ray already gives a fine part stay."""
        right, eye, up = basis
        part_ids, n, coverage = fine["part_ids"], fine["rays"], fine["coverage"]
        solid = volume > 0
        fine_solid = solid & np.isin(parts, part_ids)
        occupied = np.argwhere(fine_solid)[:, ::-1]
        if not len(occupied):
            return
        # Only the pixels around the fine parts are traced again.
        scale = self.camera["pixels_per_unit"]
        centers = grid.origin + (occupied + .5) * grid.spacing
        reach = np.linalg.norm(grid.spacing) * scale
        columns = pivot[0] + (centers @ right) * scale
        rows = pivot[1] - (centers @ up) * scale
        cell = ids.shape[0]
        x0, x1 = (int(np.clip(v, 0, cell)) for v in (np.floor(columns.min() - reach),
                                                      np.ceil(columns.max() + reach)))
        y0, y1 = (int(np.clip(v, 0, cell)) for v in (np.floor(rows.min() - reach),
                                                      np.ceil(rows.max() + reach)))
        if x0 >= x1 or y0 >= y1:
            return
        height, width = y1 - y0, x1 - x0
        size = grid.size_xyz

        def march(k):
            """For a k x k grid of rays per pixel of the window: whether a fine part is the
            first hit, whether a fine part is met at all, its first voxel and ray distance."""
            yy, xx = np.indices((height * k, width * k))
            origin = ((((xx + .5) / k + x0 - pivot[0]) / scale)[..., None] * right
                      + ((pivot[1] - (yy + .5) / k - y0) / scale)[..., None] * up)
            first = np.zeros(xx.shape, dtype=bool)
            visible = np.zeros_like(first)
            met = np.zeros_like(first)
            voxels = np.zeros((*xx.shape, 3), dtype=np.int16)
            distances = np.zeros(xx.shape, dtype=np.float32)
            for distance in np.arange(*rays):
                indices = np.floor((origin + distance * eye - grid.origin) / grid.spacing).astype(np.int16)
                inside = ((indices >= 0) & (indices < size)).all(axis=-1)
                pending = inside & ~met
                samples = indices[pending][:, ::-1]
                hit = fine_solid[tuple(samples.T)]
                pending[pending] = hit
                voxels[pending] = samples[hit]
                distances[pending] = distance
                visible |= pending & ~first
                met |= pending
                blocked = inside & ~first
                blocked[blocked] = solid[tuple(indices[blocked][:, ::-1].T)]
                first |= blocked
            return visible, met, voxels, distances

        visible, met, sub_voxels, sub_distances = march(n)
        _, center_met, center_voxels, center_distances = march(1)
        share = visible.reshape(height, n, width, n).mean(axis=(1, 3))
        hidden = (met & ~visible).reshape(height, n, width, n).mean(axis=(1, 3))
        drawn = share >= coverage
        line = fine.get("line")
        if line is not None:
            # The shape alone (what is in front does not count) decides the drawing.
            shape = share + hidden
            padded = np.pad(shape, 1)
            ridge = (((shape >= padded[1:-1, :-2]) & (shape >= padded[1:-1, 2:]))
                     | ((shape >= padded[:-2, 1:-1]) & (shape >= padded[2:, 1:-1])))
            drawn = ((shape >= coverage) | (ridge & (shape >= line))) & (share >= line)

        # The voxel shown on a new pixel depends on the fine parts alone, not on what is
        # in front of them, so a render of one part alone picks the same voxel: the first
        # fine voxel on the pixel's own ray, else on the ray nearest the pixel center.
        offset = (np.arange(n) + .5) / n - .5
        nearness = (offset[:, None] ** 2 + offset[None, :] ** 2).ravel()
        grouped = met.reshape(height, n, width, n).transpose(0, 2, 1, 3).reshape(height, width, n * n)
        sy, sx = np.divmod(np.where(grouped, nearness, np.inf).argmin(axis=-1), n)
        sy = np.arange(height)[:, None] * n + sy
        sx = np.arange(width)[None, :] * n + sx
        chosen = np.where(center_met[..., None], center_voxels, sub_voxels[sy, sx])
        chosen_depth = np.where(center_met, center_distances, sub_distances[sy, sx])

        window = (slice(y0, y1), slice(x0, x1))
        current = np.where(ids[window] > 0, parts[tuple(hits[window].transpose(2, 0, 1))], 0)
        take = drawn & (share >= hidden) & ~np.isin(current, part_ids)
        ids[window][take] = volume[tuple(chosen[take].T)]
        hits[window][take] = chosen[take]
        depth[window][take] = chosen_depth[take]


def fine_parts(character, mode):
    """The fine settings of a motion mode (config `<mode>.fine`), or None."""
    settings = character.config.get(mode, {}).get("fine")
    if not settings:
        return None
    unknown = set(settings) - {"description", "parts", "rays", "coverage", "line", "seam"}
    if unknown:
        raise ValueError(f"unknown {mode}.fine keys: {sorted(unknown)}")
    rays, coverage = int(settings["rays"]), float(settings["coverage"])
    line = settings.get("line")
    if not 2 <= rays <= 8 or not 0 < coverage <= 1 or (line is not None and not 0 < float(line) <= coverage):
        raise ValueError(f"{mode}.fine needs rays from 2 to 8, a coverage in (0, 1] and a line "
                         "share in (0, coverage]")
    seam = settings.get("seam", "front")
    if seam not in ("front", "behind"):
        raise ValueError(f"{mode}.fine seam must be front or behind")
    return {"part_ids": [character.parts[name] for name in settings["parts"]], "rays": rays,
            "coverage": coverage, "line": None if line is None else float(line), "seam": seam}
