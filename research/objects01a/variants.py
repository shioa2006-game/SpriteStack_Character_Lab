"""Rebuild the low crates from board geometry; preserve the original voxel specimen."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from objects.bake import ROOT, load
from objects.wooden_crate.build_model import build

BASELINE = Path(__file__).with_name("baseline")
HEIGHTS = (14, 8, 6)


def crate(height):
    if height not in HEIGHTS:
        raise ValueError(f"unknown study height {height}")
    if height == 14:
        return load(BASELINE)
    template = load(ROOT / "wooden_crate")
    spec = deepcopy(template.spec)
    spec["geometry"]["rest_dimensions_xyz"][2] = height
    spec["source_grid"]["limit_xyz"][2] = height + 1
    placement = spec["views"]["idle"]["placement"]
    placement["support_center_xyz"][2] = placement["stack_pitch_z"] = height
    volume = build(spec)
    return replace(template, spec=spec, model=volume.materials, part_ids=volume.parts,
                   source_grid=volume.grid, posed_grid=volume.grid)
