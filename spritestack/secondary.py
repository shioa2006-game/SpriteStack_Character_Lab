"""Secondary motion of cloth and hair in the walk.

A character opts in with a list of regions in walk.secondary of character.json.
Each region selects voxels of one part (by material and an optional box) and
gives every voxel a weight from 0 to 1. Voxels with weight 0 stay rigid with
their part and are drawn by the normal reslice. Every other voxel gets its own
transform from its weight. Its SUBSAMPLES points per axis are carried forward to
find the posed cells it may cover, and each such cell is sampled back through
the voxel's transform into the part (see posed_cells), so neighbouring voxels
that turn by slightly different angles leave no gaps and the cloth does not
thicken. Two kinds of region exist:

skirt
    Cloth hanging from the pelvis follows the leg on its own side. The leg's turn
    is the rotation that carries the rest line from hip to ankle onto the posed
    one, so a heel kicking back pushes the hem back even while the thigh still
    points forward. The weight grows from top_z down to hem_z and from the middle
    (x = 0) out to side_width, up to follow at the hem. The cloth turns about the
    hip joint by that fraction of the leg's turn, so the hem moves with the legs.
    drive "thigh" uses the thigh's own rotation instead, for cloth that hugs it.

pendulum
    A strand (hair, ponytail, scarf tail, cape) hangs from pivot towards tip, in
    the rest coordinates of its part. Its tip lags lag_frames behind the place the
    rigidly carried tip had earlier in the cycle, including the forward travel of
    the walk, scaled by follow (one number, or [x, y, z] gains in model axes; a
    larger z gain lets a hanging strand bounce with the root bob, which would
    otherwise run along the strand). The trail is read from driver, a part that
    defaults to the region's own part; long hair lying on the back is moved by
    the chest, for example. The strand turns about the pivot to point at the
    lagged place, by at most max_deg; a voxel turns by its weight times that
    angle, where the weight rises from 0 at the pivot to 1 at the tip (raised to
    exponent). Because the walk is a cycle, the lag reads the cycle backwards, so
    the first frame already trails the last one and the loop has no seam.

No physics state is integrated: the poses are a function of the walk clip alone.
Overlaps keep the reslice contract that later parts in rig.parts win.
"""

from dataclasses import replace
import math

import numpy as np

from .render import reslice
from .rig import about, align, cyclic, transform, vec

KINDS = ("skirt", "pendulum")
SUBSAMPLES = 3


def smoothstep(values):
    t = np.clip(values, 0, 1)
    return t * t * (3 - 2 * t)


def turn(points, axis, angles):
    """Rotate points (N x 3) about a unit axis through the origin by per-point degrees."""
    radians = np.radians(angles)[:, None]
    cosine, sine = np.cos(radians), np.sin(radians)
    return (points * cosine + np.cross(axis, points) * sine
            + np.outer(points @ axis, axis) * (1 - cosine))


def relative_turn(parent, child):
    """Axis (in the parent's rest frame) and degrees that turn parent into child."""
    relative = parent[0].T @ child[0]
    skew = np.array([relative[2, 1] - relative[1, 2],
                     relative[0, 2] - relative[2, 0],
                     relative[1, 0] - relative[0, 1]])
    sine = np.linalg.norm(skew) / 2
    cosine = (np.trace(relative) - 1) / 2
    if sine < 1e-9:
        return vec([1, 0, 0]), 0.
    return skew / (2 * sine), math.degrees(math.atan2(sine, cosine))


class Secondary:
    """Per-voxel weights of the walk.secondary regions and the posing of each frame."""

    def __init__(self, character, clip, rest, *, mode="walk"):
        self.mode = mode
        regions = character.config["walk"].get("secondary", [])  # The same garment masks in either motion.
        names = [material["name"] for material in character.config["model"]["palette"]]
        grid = character.source_grid
        coords = np.argwhere(character.part_ids != 0)
        centers = grid.origin + (coords[:, ::-1] + .5) * grid.spacing
        owners = character.part_ids[tuple(coords.T)]
        materials = character.model[tuple(coords.T)]
        claimed = np.zeros(len(coords), dtype=bool)
        self.clip, self.rest, self.regions = clip, rest, []

        for region in regions:
            label = region.get("name")
            kind = region.get("kind")
            if kind not in KINDS:
                raise ValueError(f"walk.secondary {label}: kind must be one of {KINDS}")
            part = region["part"]
            if part not in character.parts or region.get("driver", part) not in character.parts:
                raise ValueError(f"walk.secondary {label}: unknown part or driver")
            selected = owners == character.parts[part]
            if "materials" in region:
                unknown = set(region["materials"]) - set(names)
                if unknown:
                    raise ValueError(f"walk.secondary {label}: unknown materials {sorted(unknown)}")
                selected &= np.isin(materials, [names.index(name) + 1 for name in region["materials"]])
            for axis, key in enumerate("xyz"):
                if key in region.get("box", {}):
                    low, high = region["box"][key]
                    selected &= (centers[:, axis] >= low) & (centers[:, axis] <= high)

            if kind == "skirt":
                top, hem = float(region["top_z"]), float(region["hem_z"])
                follow, width = float(region["follow"]), float(region.get("side_width", 1.5))
                if not (top > hem and 0 < follow <= 1 and width > 0
                        and region.get("drive", "leg") in ("leg", "thigh")):
                    raise ValueError(f"walk.secondary {label}: needs top_z > hem_z, "
                                     "0 < follow <= 1, side_width > 0 and drive leg or thigh")
                weight = (follow * smoothstep((top - centers[:, 2]) / (top - hem))
                          * np.clip(np.abs(centers[:, 0]) / width, 0, 1))
            else:
                pivot, tip = vec(region["pivot"]), vec(region["tip"])
                axis = tip - pivot
                length = np.linalg.norm(axis)
                follow = np.broadcast_to(np.asarray(region["follow"], dtype=float), 3)
                if (length <= 0 or float(region["lag_frames"]) < 0 or not np.all(follow >= 0) or not np.any(follow > 0)
                        or not 0 < float(region["max_deg"]) <= 90 or float(region.get("exponent", 1)) <= 0):
                    raise ValueError(f"walk.secondary {label}: needs tip != pivot, lag_frames >= 0, "
                                     "follow >= 0 (not all 0), 0 < max_deg <= 90 and exponent > 0")
                along = (centers - pivot) @ axis / (length * length)
                weight = np.clip(along, 0, 1) ** float(region.get("exponent", 1))

            moving = selected & (weight > 1e-6)
            if np.any(claimed & moving):
                raise ValueError(f"walk.secondary {label} overlaps another region")
            claimed |= moving
            self.regions.append(dict(region, voxels=coords[moving], centers=centers[moving],
                                     weights=weight[moving], materials=materials[moving],
                                     part_id=character.parts[part], count=int(moving.sum())))

        rigid_ids = character.part_ids.copy()
        rigid_ids[tuple(coords[claimed].T)] = 0
        kept = {name: part_id for name, part_id in character.parts.items() if np.any(rigid_ids == part_id)}
        self.rigid = replace(character, parts=kept, part_ids=rigid_ids)
        self.rank = np.zeros(256, dtype=int)
        for rank, part_id in enumerate(character.parts.values(), start=1):
            self.rank[part_id] = rank
        offsets = (np.arange(SUBSAMPLES) + .5) / SUBSAMPLES - .5
        self.offsets = np.stack(np.meshgrid(offsets, offsets, offsets, indexing="ij"),
                                axis=-1).reshape(-1, 3) * grid.spacing
        self.moving_count = int(claimed.sum())

    def _pendulum(self, region, frames):
        """The hinge, axis and full angle of the strand in each frame."""
        part = region["part"]
        pivot, tip = vec(region["pivot"]), vec(region["tip"])
        travel = self.clip.get("forward_each_frame", 0) * float(region.get("travel", 1))
        lag = float(region["lag_frames"])
        follow = np.broadcast_to(np.asarray(region["follow"], dtype=float), 3)
        driver = region.get("driver", part)
        carried = [transform(transforms[driver], tip) for transforms in frames]
        result = []
        if self.mode == "attack":
            durations = self.clip["durations_ms"]
            times = np.r_[0, np.cumsum(durations[:-1])]
            delay_ms = lag * np.mean(durations)
        for index, transforms in enumerate(frames):
            hinge = transform(transforms[part], pivot)
            direction = transform(transforms[part], tip) - hinge
            # The tip trails where it was lag frames ago; the ground moved on since then.
            if self.mode == "attack":
                previous = np.interp(times[index] - delay_ms,
                                     times, np.arange(len(frames)))
                trail = cyclic(carried, previous) - carried[index]
                if not self.clip["keys"][index]:
                    trail = np.zeros(3)
            else:
                trail = cyclic(carried, index - lag) - carried[index] - vec([0, travel * lag, 0])
            target = direction + follow * trail
            axis = np.cross(direction, target)
            sine = np.linalg.norm(axis)
            angle = min(math.degrees(math.atan2(sine, direction @ target)), float(region["max_deg"]))
            result.append((hinge, axis / sine if sine > 1e-9 else vec([1, 0, 0]),
                           angle if sine > 1e-9 else 0.))
        return result

    def _mapping(self, region, transforms, swing):
        """Forward and inverse maps of a region's voxels: (points, voxel index) -> points."""
        owner = transforms[region["part"]]
        weights = region["weights"]
        if region["kind"] == "pendulum":
            hinge, axis, angle = swing

            def forward(points, index):
                return turn(points @ owner[0].T + owner[1] - hinge, axis, angle * weights[index]) + hinge

            def inverse(points, index):
                return (turn(points - hinge, axis, -angle * weights[index]) + hinge - owner[1]) @ owner[0]
            return forward, inverse

        sides = np.where(region["centers"][:, 0] < 0, "R", "L")
        legs = {}
        for name in ("R", "L"):
            pivot = self.rest["hip_" + name]
            hip = transform(transforms["thigh_" + name], pivot)
            if region.get("drive", "leg") == "thigh":
                leg = transforms["thigh_" + name]
            else:
                ankle = transform(transforms["shin_" + name], self.rest["ankle_" + name])
                leg = about(align(self.rest["ankle_" + name] - pivot, ankle - hip), pivot, hip)
            axis, angle = relative_turn(owner, leg)
            legs[name] = (pivot, axis, angle, transform(owner, pivot), hip)

        def apply(points, index, backwards):
            result = np.empty_like(points)
            for name, (pivot, axis, angle, start, end) in legs.items():
                chosen = sides[index] == name
                w = weights[index[chosen]]
                shift = start + w[:, None] * (end - start)
                if backwards:
                    result[chosen] = turn((points[chosen] - shift) @ owner[0], axis, -angle * w) + pivot
                else:
                    result[chosen] = turn(points[chosen] - pivot, axis, angle * w) @ owner[0].T + shift
            return result
        return (lambda points, index: apply(points, index, False),
                lambda points, index: apply(points, index, True))

    def posed_cells(self, character, region, transforms, swing, rigid=False):
        """Posed-grid cells (X, Y, Z indices) of a region and the material of each.

        Candidate cells are those hit by SUBSAMPLES^3 points of each voxel. Each
        candidate is sampled back through that voxel's own transform, like reslice
        does with a part's transform: it is kept with the source material found
        there when the source voxel belongs to the region's part. So the region
        keeps its volume, and where neighbouring voxels turn by slightly different
        angles, each fills the seam from its neighbour. rigid=True poses the region
        with its part's own transform, for comparisons.
        """
        if rigid:
            owner = transforms[region["part"]]
            forward = lambda points, index: points @ owner[0].T + owner[1]
            inverse = lambda points, index: (points - owner[1]) @ owner[0]
        else:
            forward, inverse = self._mapping(region, transforms, swing)
        target, source = character.posed_grid, character.source_grid
        count = len(self.offsets)
        index = np.repeat(np.arange(len(region["centers"])), count)
        points = (region["centers"][:, None, :] + self.offsets[None]).reshape(-1, 3)
        cells = np.floor((forward(points, index) - target.origin) / target.spacing).astype(int)
        pairs = np.unique(np.column_stack([cells, index]), axis=0)
        cells, index = pairs[:, :3], pairs[:, 3]
        back = inverse(target.origin + (cells + .5) * target.spacing, index)
        voxels = np.floor((back - source.origin) / source.spacing).astype(int)
        inside = np.all((voxels >= 0) & (voxels < source.size_xyz), axis=1)
        cells, voxels = cells[inside], tuple(voxels[inside][:, ::-1].T)
        keep = character.part_ids[voxels] == region["part_id"]
        materials = character.model[voxels][keep]
        cells, order = np.unique(cells[keep], axis=0, return_index=True)
        return cells, materials[order]

    def pose_volumes(self, character, frames):
        """Pose every walk frame; frames are the rigid part transforms of each frame."""
        swings = [self._pendulum(region, frames) if region["kind"] == "pendulum" else None
                  for region in self.regions]
        target = character.posed_grid
        order = sorted(range(len(self.regions)), key=lambda i: self.rank[self.regions[i]["part_id"]])
        self.angles, results = [], []
        for index, transforms in enumerate(frames):
            volume, part_ids = reslice(self.rigid, {name: transforms[name] for name in self.rigid.parts})
            for number in order:
                region = self.regions[number]
                swing = swings[number][index] if swings[number] else None
                cells, materials = self.posed_cells(character, region, transforms, swing)
                if np.any(cells <= 0) or np.any(cells >= target.size_xyz - 1):
                    raise ValueError(f"walk.secondary {region['name']} exceeds the padded volume bounds")
                cells = tuple(cells[:, ::-1].T)
                # A later part already drawn there keeps its voxel, as in reslice.
                free = self.rank[part_ids[cells]] <= self.rank[region["part_id"]]
                chosen = tuple(axis[free] for axis in cells)
                volume[chosen] = materials[free]
                part_ids[chosen] = region["part_id"]
            results.append((volume, part_ids))
            self.angles.append({region["name"]: round(swings[i][index][2], 3)
                                for i, region in enumerate(self.regions) if swings[i]})
        return results
