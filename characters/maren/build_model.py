"""Build MAREN's material and part volumes from solid shapes read off one reference image.

MAREN is a tall, long-legged swordswoman: long wavy blue hair, a dark scarf,
a sleeveless ribbed beige tunic with a diagonal strap and two belts, an
open-front dark coat skirt with blue lining, dark tights, knee-high boots with
metal knee guards, a long sword in the right hand and a round shield in the left.
Hair belongs to the head part and the coat skirt to the pelvis part, so the
shared 17-part biped rig is used unchanged.
"""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SHAPE = (72, 56, 88)


def build(config):
    origin = np.array(config["model"]["origin_xyz"], dtype=float)
    spacing = np.array(config["model"]["voxel_size_xyz"], dtype=float)
    z, y, x = np.meshgrid(*[
        low + (np.arange(count) + .5) * step
        for low, count, step in zip(origin[::-1], SHAPE, spacing[::-1])
    ], indexing="ij")
    xyz = np.stack((x, y, z), axis=-1)
    material_ids = np.zeros(SHAPE, dtype=np.uint8)
    part_ids = np.zeros_like(material_ids)
    materials = {item["name"]: i for i, item in enumerate(config["model"]["palette"], 1)}
    parts = {name: i for i, name in enumerate(config["rig"]["parts"], 1)}
    joints = {name: np.array(point, dtype=float) for name, point in config["rig"]["rest"].items()}

    def paint(mask, material, part):
        material_ids[mask] = materials[material]
        part_ids[mask] = parts[part]

    def ellipsoid(center, radii, power=2):
        return np.sum(np.abs((xyz - center) / radii) ** power, axis=-1) <= 1

    def capsule(a, b, radius, radius_b=None):
        """A segment swept by a sphere whose radius may taper from a to b."""
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        axis = b - a
        t = np.clip(((xyz - a) @ axis) / (axis @ axis), 0, 1)
        r = radius if radius_b is None else radius + (radius_b - radius) * t
        return np.sum((xyz - a - t[..., None] * axis) ** 2, axis=-1) <= r ** 2

    angle = np.arctan2(x, y)  # 0 at the front, positive toward the anatomical left

    # Legs: dark tights, knee-high boots, metal knee guards.
    for side in ("R", "L"):
        hip, knee, ankle = (joints[f"{name}_{side}"] for name in ("hip", "knee", "ankle"))
        paint(capsule(hip, knee, 1.28, 1.02), "tights", f"thigh_{side}")
        shin = f"shin_{side}"
        paint(capsule(knee, ankle, 1.02, .9), "boot", shin)
        paint(ellipsoid(knee + [0, .05, -.75], (1.32, 1.3, .6), 2.6), "boot", shin)
        paint(ellipsoid(knee + [0, .72, .1], (.98, .62, 1.05), 2.2), "knee guard", shin)
        paint(ellipsoid(knee + [0, .86, -1.1], (.5, .42, .95), 2.0), "knee guard", shin)
        ax, ay, az = ankle
        boot = f"boot_{side}"
        paint(ellipsoid((ax, ay + .3, az + .1), (1.05, 1.05, 1.1), 2.4), "boot", boot)
        paint(ellipsoid((ax, ay + .75, 1.25), (1.12, 1.9, 1.1), 2.6) & (z >= .5), "boot", boot)
        paint(ellipsoid((ax, ay + .95, .5), (1.22, 2.18, .55), 3), "sole", boot)

    # Pelvis: tunic skirt and the open-front coat skirt with its lining.
    paint(ellipsoid((0, 0, 14.0), (3.05, 2.15, 1.6), 2.4), "tunic", "pelvis")
    drop = 14.7 - z
    skirt = (((x / (3.0 + .2 * drop)) ** 2 + (y / (2.15 + .15 * drop)) ** 2 <= 1)
             & (z >= 12.3) & (z <= 14.7))
    paint(skirt, "tunic", "pelvis")

    top = 15.2
    depth = top - z
    rx, ry = 3.45 + .3 * depth, 2.6 + .25 * depth
    # Shallow pleats vary the surface normal so the dark cloth reads as folds.
    radial = np.sqrt((x / rx) ** 2 + (y / ry) ** 2) * (1 - .035 * depth / 10 * np.cos(angle * 6))
    outer = .75 / np.minimum(rx, ry)
    lined = outer + .55 / np.minimum(rx, ry)
    opening = np.radians(40 + 3.5 * depth)
    turn = np.abs(angle)
    hem = 5.2 + 2.4 * (1 + np.cos(angle)) / 2 + .5 * np.abs(np.sin(angle * 3.5))
    coat = (radial <= 1) & (radial >= 1 - lined) & (turn >= opening) & (z <= top) & (z >= hem)
    paint(coat, "coat", "pelvis")
    # The inner layer is lined; the front edges are folded back so the lining shows outside.
    lapel = turn < opening + np.radians(22)
    paint(coat & ((radial < 1 - outer) | lapel), "coat lining", "pelvis")

    # Hair: crown, side-swept bangs, side locks and five tapered back locks. The locks
    # merge under the crown and separate into curled tips; the outer right lock reaches
    # farther out, a static hint of the windblown hair in the reference.
    locks = (
        ((0, -3.0, 27.5), (-.5, -3.9, 16.6), 2.0, 1.05),
        ((-1.9, -2.7, 27.5), (-3.6, -3.5, 17.1), 1.75, .9),
        ((1.9, -2.7, 27.5), (3.2, -3.4, 17.5), 1.75, .9),
        ((-3.2, -1.5, 26.5), (-5.6, -2.6, 18.6), 1.35, .7),
        ((3.2, -1.5, 26.5), (4.6, -2.2, 19.4), 1.35, .7),
    )
    for top_point, tip, top_radius, tip_radius in locks:
        tip = np.array(tip)
        curl = tip + [np.sign(tip[0]) * .9, -.2, .6]
        paint(capsule(top_point, tip, top_radius, tip_radius) | capsule(tip, curl, tip_radius * .8),
              "hair", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 3.4, -.6, 25.8), (1.5, 2.2, 2.6), 2.2), "hair", "head")
    face_front = (y > .6) & (z < 27.55 + .3 * x)
    crown = ellipsoid((0, -.05, 27.95), (4.0, 3.95, 4.0), 2.3)
    volume = ellipsoid((0, -.45, 28.6), (3.7, 4.05, 3.3), 2.0)
    paint((crown | volume) & ~face_front, "hair", "head")
    strands = np.sin(1.9 * x + .6 * np.sin(.8 * z)) > .8
    paint((material_ids == materials["hair"]) & (z < 26.5) & (y < -.8) & strands, "hair shade", "head")

    # Face: skull, jaw and neck in skin; the carved crown leaves side-swept bangs.
    skull = ellipsoid((0, .3, 27.2), (3.35, 3.4, 3.6), 2.2)
    jaw = ellipsoid((0, 1.0, 24.6), (2.45, 2.4, 1.9), 2.2)
    paint((skull | jaw) & (material_ids != materials["hair"]), "skin", "head")
    paint(capsule((0, .1, 21.0), (0, .4, 24.0), 1.15), "skin", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 1.35, 3.15, 26.0), (.5, .6, .8), 2.2) & (skull | jaw), "eyes", "head")
    for sign in (-1, 1):
        paint(capsule((sign * 3.25, .45, 28.0), (sign * 3.45, .2 - .45 * (sign < 0), 22.9), .85, .6),
              "hair", "head")
    paint(capsule((.15, .9, 31.7), (.4, 1.6, 32.8), .34) | capsule((.4, 1.6, 32.8), (.8, 2.5, 32.5), .3),
          "hair", "head")

    # Chest: tunic torso, diagonal strap from right shoulder to left hip, scarf.
    torso = (ellipsoid((0, -.1, 18.4), (3.15, 2.2, 3.0), 2.4)
             | ellipsoid((0, -.05, 15.9), (2.75, 1.95, 1.5), 2.4)
             | ellipsoid((0, .9, 18.3), (2.5, 1.6, 1.25), 2.2)
             | ellipsoid((0, -.2, 20.4), (3.95, 1.8, .9), 2.4))
    paint(torso, "tunic", "chest")
    padded = (ellipsoid((0, -.1, 18.4), (3.6, 2.65, 3.4), 2.4)
              | ellipsoid((0, -.2, 20.5), (4.1, 2.2, 1.25), 2.4))
    paint(padded & (np.abs(z - 18.4 + .95 * x) < .42) & (z > 14.8), "belt", "chest")
    paint(ellipsoid((1.45, 2.35, 17.05), (.55, .4, .55), 2.2), "buckle", "chest")
    paint(ellipsoid((0, .3, 21.8), (2.8, 2.65, 1.4), 2.2), "scarf", "chest")
    paint(ellipsoid((0, 1.3, 20.9), (2.4, 1.7, .9), 2.2), "scarf", "chest")
    paint(capsule((-1.5, 2.3, 20.6), (-1.8, 2.5, 18.4), .75, .55), "scarf", "chest")

    # Belts are painted after the torso so they stay visible, but move with the pelvis.
    ring = lambda rx, ry: (x / rx) ** 2 + (y / ry) ** 2 <= 1
    paint(ring(3.1, 2.3) & (z >= 15.1) & (z <= 15.55), "belt", "pelvis")
    slung = np.abs(z - (14.2 + .13 * x)) <= .42
    paint(ring(3.3, 2.45) & slung, "belt", "pelvis")
    paint(ellipsoid((-.6, 2.45, 14.12), (.72, .38, .62), 4), "buckle", "pelvis")

    # Arms: bare muscular arms, leather gloves to mid-forearm.
    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "hand"))
        upper, fore, fist = (f"{name}_{side}" for name in ("upper", "fore", "hand"))
        paint(capsule(shoulder, elbow, 1.08, .9), "skin", upper)
        paint(ellipsoid(shoulder + [sign * .15, 0, -.25], (1.35, 1.3, 1.45), 2.2), "skin", upper)
        paint(ellipsoid(shoulder + .38 * (elbow - shoulder), (1.15, 1.2, 1.3), 2.2), "skin", upper)
        cuff = elbow + .42 * (hand - elbow)
        paint(capsule(elbow, hand, .8), "skin", fore)
        paint(capsule(cuff, hand, .92), "glove", fore)
        paint(capsule(cuff, cuff + .08 * (hand - elbow), 1.02), "glove", fore)
        paint(ellipsoid(hand, (.95, .95, 1.0), 2.2), "glove", fist)

    # Sword: long straight blade that widens toward a tapered point, curved guard.
    hand, tip = joints["hand_R"], joints["sword_tip"]
    axis = tip - hand
    side = np.cross(axis, [0, 1, 0])
    side /= np.linalg.norm(side)
    flat = np.cross(axis / np.linalg.norm(axis), side)
    delta = xyz - hand
    progress = delta @ axis / (axis @ axis)
    across = delta @ side
    thick = delta @ flat
    width = np.where(progress < .86, .72 + .36 * progress, 1.03 * np.clip((1 - progress) / .14, 0, 1))
    blade = (progress >= .1) & (progress <= 1) & (np.abs(across) <= width) & (np.abs(thick) <= .3)
    paint(blade, "blade", "sword")
    paint(blade & (np.abs(across) >= .55 * width), "blade edge", "sword")
    paint(capsule(hand - .12 * axis, hand + .08 * axis, .45), "grip", "sword")
    guard = hand + .09 * axis
    curl = .05 * axis
    paint(capsule(guard - 1.4 * side + curl, guard, .36) | capsule(guard, guard + 1.4 * side - curl, .36),
          "guard", "sword")
    paint(ellipsoid(hand - .14 * axis, (.55, .55, .55)), "guard", "sword")

    # Round shield on the left forearm, slightly domed, facing outward and forward.
    center = joints["shield_center"]
    normal = np.array([.55, .835, 0])
    normal /= np.linalg.norm(normal)
    tangent = np.array([normal[1], -normal[0], 0])
    offset = xyz - center
    n = offset @ normal
    radius = np.sqrt((offset @ tangent) ** 2 + offset[..., 2] ** 2)
    shell = (radius <= 4.1) & (n >= -.45) & (n <= .7 - .045 * radius ** 2)
    paint(capsule(joints["hand_L"], center - .3 * normal, .7), "grip", "shield")
    paint(shell, "shield face", "shield")
    paint(shell & (radius >= 3.5), "shield rim", "shield")
    paint(ellipsoid(center + .62 * normal, (.95, .95, .95)), "shield boss", "shield")
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
