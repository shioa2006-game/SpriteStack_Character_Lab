"""Local two-part weighting for BRAM's existing biped poses."""

from dataclasses import dataclass, replace
import math

import numpy as np

from spritestack.render import reslice
from spritestack.rig import Biped, about, rotate, transform, unit


@dataclass(frozen=True)
class Joint:
    name: str
    parent: str
    child: str
    pivot: np.ndarray
    axis: np.ndarray
    radius: float
    half_width: float


def joints_for(character, settings):
    rest = Biped(character).rest
    for side in ("R", "L"):
        for name, previous, following, parent, child in (
            ("shoulder", "chest", f"elbow_{side}", "chest", f"upper_{side}"),
            ("elbow", f"shoulder_{side}", f"hand_{side}", f"upper_{side}", f"fore_{side}"),
            ("knee", f"hip_{side}", f"ankle_{side}", f"thigh_{side}", f"shin_{side}"),
        ):
            label = f"{name}_{side}"
            pivot = rest[label]
            axis = unit(unit(pivot - rest[previous]) + unit(rest[following] - pivot))
            yield Joint(label, parent, child, pivot, axis, **settings[name])


def smoothstep(values):
    t = np.clip(values, 0, 1)
    return t * t * (3 - 2 * t)


def blend_transform(parent, child, pivot, weight):
    """Interpolate rotations on SO(3) and mix the transformed pivot positions."""
    a, b = parent[0], child[0]
    relative = a.T @ b
    skew = np.array([relative[2, 1] - relative[1, 2],
                     relative[0, 2] - relative[2, 0],
                     relative[1, 0] - relative[0, 1]])
    sine = np.linalg.norm(skew) / 2
    cosine = (np.trace(relative) - 1) / 2
    if sine > 1e-8:
        rotation = a @ rotate(unit(skew), math.degrees(math.atan2(sine, cosine)) * weight)
    elif cosine < 0:
        # Near a half-turn, the skew vanishes. The rotation axis has eigenvalue 1.
        _, axes = np.linalg.eigh((relative + relative.T) / 2)
        rotation = a @ rotate(axes[:, -1], 180 * weight)
    else:
        rotation = a
    position = (1 - weight) * transform(parent, pivot) + weight * transform(child, pivot)
    return about(rotation, pivot, position)


class WeightedReslice:
    """Group nearby voxels by weight and inverse-sample with the normal voxel baker."""

    def __init__(self, character, settings):
        steps = settings["weight_steps"]
        if type(steps) is not int or steps < 2:
            raise ValueError("weight_steps must be an integer of at least 2")
        original = character.part_ids
        grid = character.source_grid
        coords = np.argwhere(original != 0)
        ijk = tuple(coords.T)
        centers = grid.origin + (coords[:, ::-1] + .5) * grid.spacing
        owners = original[ijk]
        assigned = np.zeros(len(owners), dtype=bool)
        blended_groups = {name: [] for name in character.parts}
        self.joints = tuple(joints_for(character, settings))

        for joint in self.joints:
            if min(joint.radius, joint.half_width) <= 0:
                raise ValueError(f"{joint.name} needs positive radius and half_width")
            offset = centers - joint.pivot
            distance = np.linalg.norm(offset, axis=1)
            # The inner half blends fully. Fade out to original ownership at the radius.
            strength = 1 - smoothstep(2 * distance / joint.radius - 1)
            fraction = smoothstep(.5 + (offset @ joint.axis) / (2 * joint.half_width))
            for name, rigid_weight in ((joint.parent, 0), (joint.child, 1)):
                bins = np.rint((rigid_weight + strength * (fraction - rigid_weight)) * steps)
                influenced = (owners == character.parts[name]) & (bins != rigid_weight * steps)
                if np.any(assigned & influenced):
                    raise ValueError(f"weight regions overlap for {joint.name} and {name}")
                assigned |= influenced
                for bin_value in np.unique(bins[influenced]):
                    group = influenced & (bins == bin_value)
                    blended_groups[name].append((joint, bin_value / steps, group))

        sample_parts = {}
        sample_ids = np.zeros_like(original)
        provenance = [0]
        self.sources = {}
        for name, part_id in character.parts.items():
            groups = [(None, 0, (owners == part_id) & ~assigned), *blended_groups[name]]
            for joint, weight, selected in groups:
                if not np.any(selected):
                    continue
                index = len(provenance)
                if index > 255:
                    raise ValueError("weight groups exceed the uint8 sampling ID range")
                group_name = f"sample_{index}"
                sample_parts[group_name] = index
                sample_ids[tuple(coords[selected].T)] = index
                provenance.append(part_id)
                self.sources[group_name] = (name, joint, weight)

        self.grouped = replace(character, parts=sample_parts, part_ids=sample_ids)
        self.provenance = np.array(provenance, dtype=np.uint8)
        self.blended_count = int(assigned.sum())

    def __call__(self, character, transforms):
        # Preserve the exact neutral volume for rest and the attack's guard frames.
        if all(np.array_equal(transforms[j.parent][0], transforms[j.child][0]) and
               np.array_equal(transforms[j.parent][1], transforms[j.child][1]) for j in self.joints):
            return reslice(character, transforms)

        grouped_transforms = {}
        for group_name, (owner, joint, weight) in self.sources.items():
            if joint is None:
                matrix = transforms[owner]
            elif weight == 0:
                matrix = transforms[joint.parent]
            elif weight == 1:
                matrix = transforms[joint.child]
            else:
                matrix = blend_transform(transforms[joint.parent], transforms[joint.child],
                                         joint.pivot, weight)
            grouped_transforms[group_name] = matrix
        volume, ids = reslice(self.grouped, grouped_transforms)
        return volume, self.provenance[ids]
