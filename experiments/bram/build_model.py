"""Build BRAM's material and part volumes from hand-authored solid shapes."""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def build(config):
    origin = np.array(config["model"]["origin_xyz"])
    spacing = np.array(config["model"]["voxel_size_xyz"])
    shape = (52, 56, 88)
    z, y, x = np.meshgrid(*[
        low + (np.arange(count) + .5) * step
        for low, count, step in zip(origin[::-1], shape, spacing[::-1])
    ], indexing="ij")
    xyz = np.stack((x, y, z), axis=-1)
    material_ids = np.zeros(shape, dtype=np.uint8)
    part_ids = np.zeros_like(material_ids)
    materials = {item["name"]: i for i, item in enumerate(config["model"]["palette"], 1)}
    parts = {name: i for i, name in enumerate(config["rig"]["parts"], 1)}
    joints = {name: np.array(point) for name, point in config["rig"]["rest"].items()}

    def paint(mask, material, part):
        material_ids[mask] = materials[material]
        part_ids[mask] = parts[part]

    def ellipsoid(center, radii, power=2):
        return np.sum(np.abs((xyz - center) / radii) ** power, axis=-1) <= 1

    def capsule(a, b, radius):
        a, b = np.asarray(a), np.asarray(b)
        axis = b - a
        position = np.clip(((xyz - a) @ axis) / (axis @ axis), 0, 1)
        return np.sum((xyz - a - position[..., None] * axis) ** 2, axis=-1) <= radius ** 2

    for side, sign in (("R", -1), ("L", 1)):
        hip, knee, ankle = (joints[f"{name}_{side}"] for name in ("hip", "knee", "ankle"))
        paint(capsule(hip, knee, 1.75), "trousers", f"thigh_{side}")
        paint(capsule(knee, ankle, 1.52), "trousers", f"shin_{side}")
        ax, ay, az = ankle
        sole = ellipsoid((ax, ay + .92, .72), (2.25, 3.02, 1.12), 3)
        upper = ellipsoid((ax, ay + .58, 1.55), (2.11, 2.6, 1.45), 2.8)
        cuff = ellipsoid((ax, ay, az + .32), (1.83, 1.63, 1.1), 2.7)
        boot = f"boot_{side}"
        paint(sole, "sole", boot)
        paint(upper & (z >= .5), "leather", boot)
        paint(cuff, "leather", boot)
        paint(cuff & (z > 2.85), "bronze", boot)

    paint(ellipsoid((0, 0, 6.95), (6.3, 3.65, 2.3), 2.8), "coat shade", "pelvis")
    chest = ellipsoid((0, -.24, 10.7), (7.65, 4.37, 4.42), 2.65)
    paint(chest, "quilt", "chest")
    paint(chest & (z > 7.7) & (z < 8.8), "leather", "chest")
    paint(ellipsoid((0, 4.05, 8.25), (1.56, .75, .89), 3.2), "bronze", "chest")
    paint(ellipsoid((0, 4.53, 8.26), (.73, .34, .40), 3), "leather", "chest")
    paint(chest & (abs(x) > 3) & (z > 9) & ((x + z) % 3.5 < .52), "coat shade", "chest")
    paint(ellipsoid((0, .05, 14.1), (3.35, 2.6, 1.34), 2.6), "scarf", "chest")

    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "hand"))
        upper, fore, fist = (f"{name}_{side}" for name in ("upper", "fore", "hand"))
        paint(capsule(shoulder, elbow, 1.7), "quilt", upper)
        paint(ellipsoid(shoulder + [sign * .08, -.12, .32], (2.0, 2.02, 1.63), 2.5),
              "leather", upper)
        paint(ellipsoid(shoulder + [sign * .12, -.08, .74], (1.88, 1.87, 1.13), 2.65),
              "bronze", upper)
        paint(capsule(elbow, hand, 1.38), "coat shade", fore)
        paint(ellipsoid((elbow + hand) / 2, (1.43, 1.24, 1.24), 2.7), "leather", fore)
        paint(ellipsoid(hand, (1.43, 1.44, 1.34), 2.7), "glove", fist)

    paint(ellipsoid((0, .2, 15.1), (2.54, 2.05, 1.55), 2.4), "skin", "head")
    paint(ellipsoid((0, .7, 18.25), (4.48, 3.62, 3.98), 2.5), "skin", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 4.3, .86, 17.97), (.78, 1.34, 1.03)), "skin", "head")
        paint(ellipsoid((sign * 3.75, 2.86, 17.18), (1.03, 1.53, 1.93)), "beard", "head")

    beard = (ellipsoid((0, 3.45, 15.83), (4.02, 2.0, 2.83), 2.6)
             & (abs(x) < 1.15 + np.maximum(z - 13.2, 0) * 1.12))
    paint(beard, "beard", "head")
    paint(beard & (y > 4.25) & ((abs(x) + .31 * z) % 2.3 < .83), "beard light", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 1.42, 4.05, 17.25), (1.67, 1.12, .63), 2.5),
              "beard light", "head")
        paint(ellipsoid((sign * 1.88, 4.1, 18.25), (.63, .44, .65), 2.4), "eyes", "head")
    paint(ellipsoid((0, 4.29, 17.99), (.94, .96, .72), 2.45), "skin", "head")

    crown = ellipsoid((0, -.04, 20.79), (4.76, 3.95, 3.81), 2.6) & (z >= 19.2)
    paint(crown, "helmet", "head")
    paint(crown & (abs(x) < .58) & (z > 20.1), "bronze", "head")
    rim = ellipsoid((0, .04, 19.85), (5.05, 4.17, .85), 3.25)
    paint(rim, "bronze", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 4.47, 2.0, 19.84), (.57, .60, .53)), "rivet", "head")

    hand = joints["hand_R"]
    tip = joints["sword_tip"]
    axis = tip - hand
    side = np.cross(axis, [0, 1, 0])
    side /= np.linalg.norm(side)
    thickness = np.cross(axis / np.linalg.norm(axis), side)
    delta = xyz - hand
    progress = delta @ axis / (axis @ axis)
    across = delta @ side
    depth = delta @ thickness
    taper = np.clip((1 - progress) / .23, 0, 1)
    blade = (progress >= .17) & (progress <= 1) & (abs(across) / 1.3 + abs(depth) / .82 <= taper)
    paint(blade, "steel", "sword")
    paint(blade & (abs(across) < .50 * taper), "steel ridge", "sword")
    paint(capsule(hand - .17 * axis, hand + .18 * axis, .62), "leather", "sword")
    guard = hand + .17 * axis
    paint(capsule(guard - 1.75 * side, guard + 1.75 * side, .51), "bronze", "sword")
    paint(ellipsoid(hand - .18 * axis, (.7, .65, .68)), "bronze", "sword")

    shield = joints["shield_center"]
    u = (x - shield[0]) * .86 - (y - shield[1]) * .51
    n = (x - shield[0]) * .51 + (y - shield[1]) * .86
    height = z - shield[2]
    radius = np.sqrt(u ** 2 + height ** 2)
    shell = (radius <= 4.02) & (n >= -.85) & (n <= 1.1 - .05 * radius ** 2)
    paint(capsule(joints["hand_L"], shield, .89), "leather", "shield")
    paint(shell, "bronze", "shield")
    paint(shell & (radius < 3.44) & (n > 0), "shield face", "shield")
    paint(ellipsoid(shield + [.54, .92, 0], (1.02, .83, 1.13)), "rivet", "shield")
    return material_ids, part_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="folder for the two model NPZ files")
    args = parser.parse_args()
    config = json.loads((HERE / "character.json").read_text(encoding="utf-8"))
    material_ids, part_ids = build(config)
    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out / "materials.npz", slices=material_ids)
    np.savez_compressed(args.out / "part_ids.npz", parts=part_ids)


if __name__ == "__main__":
    main()
