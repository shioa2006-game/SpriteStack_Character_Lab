"""Author labelled horizontal slices in object space (+Y front, +Z up)."""
import argparse
from pathlib import Path

import numpy as np

from spritestack.character import Grid, read_json


class Volume:
    def __init__(self, spec):
        self.grid = Grid.from_bounds(spec["source_grid"])
        z, y, x = np.indices(self.grid.shape)
        self.x, self.y, self.z = (
            origin + (indices + .5) * spacing
            for indices, origin, spacing in zip((x, y, z), self.grid.origin, self.grid.spacing)
        )
        self.materials = np.zeros(self.grid.shape, dtype=np.uint8)
        self.parts = np.zeros_like(self.materials)
        self.colors = {name: i for i, name in enumerate(spec["palette"], 1)}
        self.owners = {name: i for i, name in enumerate(spec["parts"], 1)}

    def paint(self, mask, material, part):
        self.materials[mask] = self.colors[material]
        self.parts[mask] = self.owners[part]

    def finish(self, mask, material):
        self.materials[mask & (self.parts != 0)] = self.colors[material]


def model_cli(source, build):
    folder = Path(source).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=folder / "model.npz")
    args = parser.parse_args()
    volume = build(read_json(folder / "object.json"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, slices=volume.materials, parts=volume.parts)
