"""Solid modelling tools for biped builders. Geometry is specified in XYZ model units."""

import argparse
import json
from pathlib import Path

import numpy as np


class Volume:
    def __init__(self, config):
        model = config["model"]
        shape = model["shape_zyx"]
        axes = [start + (np.arange(n) + .5) * step for start, step, n in
                zip(model["origin_xyz"], model["voxel_size_xyz"], reversed(shape))]
        self.z, self.y, self.x = np.meshgrid(*reversed(axes), indexing="ij")
        self.xyz = np.stack((self.x, self.y, self.z), axis=-1)
        self.material = np.zeros(shape, dtype=np.uint8)
        self.part = np.zeros_like(self.material)
        self.colors = {c["name"]: i for i, c in enumerate(model["palette"], 1)}
        self.parts = {p: i for i, p in enumerate(config["rig"]["parts"], 1)}
        self.joints = {k: np.array(v, dtype=float) for k, v in config["rig"]["rest"].items()}

    def paint(self, mask, color, part):
        self.material[mask] = self.colors[color]
        self.part[mask] = self.parts[part]

    def oval(self, center, radii, power=2):
        return np.sum(np.abs((self.xyz - center) / radii) ** power, axis=-1) <= 1

    def rod(self, start, end, radius, tip=None):
        start, end = np.asarray(start), np.asarray(end)
        axis = end - start
        delta = self.xyz - start
        t = np.clip((delta @ axis) / (axis @ axis), 0, 1)
        width = radius if tip is None else radius + (tip - radius) * t
        return np.sum((delta - t[..., None] * axis) ** 2, axis=-1) <= width ** 2

    def path(self, points, width, color, part):
        for start, end in zip(points, points[1:]):
            self.paint(self.rod(start, end, width), color, part)

    def limb(self, side, start, end, radius, tip, color, part):
        self.paint(self.rod(self.joints[f"{start}_{side}"], self.joints[f"{end}_{side}"], radius, tip),
                   color, f"{part}_{side}")

    def shoe(self, side, width, depth, color, sole):
        ax, ay, az = self.joints[f"ankle_{side}"]
        part = "boot_" + side
        self.paint(self.oval((ax, ay, az), (width * .84, width * .86, az * .8)), color, part)
        toe = self.oval((ax, ay + .68, 1.02), (width, depth, 1.20), 2.8)
        self.paint(toe, color, part)
        self.paint(toe & (self.z < .57), sole, part)

    def eyes(self, socket, iris, radii):
        for sign in (-1, 1):
            sx, sy, sz = socket
            ix, iy, iz = iris
            self.paint(self.oval((sign*sx, sy, sz), (.60, .58, .65), 2.5), "skin", "head")
            eye = self.oval((sign*ix, iy, iz), radii, 2.5)
            self.paint(eye & (self.material == self.colors["skin"]), "eyes", "head")

    def cloak(self, shoulder_z, hem_z, shoulders, hem_width, back_y, cloth, fold, part="chest"):
        """A curved back panel, wide at the hem and turned forward around the shoulders."""
        t = np.clip((shoulder_z - self.z) / (shoulder_z - hem_z), 0, 1)
        width = shoulders + (hem_width - shoulders) * t
        u = self.x / width
        pleat = np.cos(u * np.pi * 3)
        surface = back_y - 1.7 * t + 2.4 * u ** 2 + .48 * pleat * t
        hem = hem_z + 1.35 * u ** 2 + .50 * pleat
        panel = ((np.abs(u) <= 1) & (self.z >= hem) & (self.z < shoulder_z - 1.1*u**2)
                 & (np.abs(self.y - surface) < .80))
        self.paint(panel, cloth, part)
        self.paint(panel & (pleat < -.77), fold, part)
        return panel


def model_cli(build, module_path):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    out = parser.parse_args().out
    config = json.loads(Path(module_path).with_name("character.json").read_bytes())
    materials, parts = build(config)
    out.mkdir(exist_ok=True, parents=True)
    np.savez_compressed(out / "materials.npz", slices=materials)
    np.savez_compressed(out / "part_ids.npz", parts=parts)
