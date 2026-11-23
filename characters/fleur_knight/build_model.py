"""Voxel model of an open-helmed knight in articulated plate with a fleur-de-lis shield."""

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

    # Plate follows each limb. Dark joints and exposed leather separate the lames.
    for side in ("R", "L"):
        hip, knee, ankle = (joints[f"{k}_{side}"] for k in ("hip", "knee", "ankle"))
        thigh, shin, foot = (f"{p}_{side}" for p in ("thigh", "shin", "boot"))
        paint(capsule(hip, knee, 1.48, 1.17), "mail", thigh)
        paint(capsule(hip + [0, .2, -.6], knee + [0, .24, .8], 1.43, 1.13), "lame", thigh)
        paint(capsule(knee, ankle, 1.41, 1.08), "lame", shin)
        greave = capsule(knee + [0, .32, -.5], ankle + [0, .25, .1], 1.42, 1.1)
        paint(greave, "plate", shin)
        paint(greave & (np.abs(x - ankle[0]) < .35) & (y > ankle[1] + .6), "ridge", shin)
        paint(ellipsoid(knee + [0, .35, .15], (1.65, 1.52, 1.32), 1.65), "ridge", shin)
        ax, ay, az = ankle
        paint(ellipsoid((ax, ay, az), (1.23, 1.21, 1.26)), "mail", foot)
        shoe = ellipsoid((ax, ay + .76, .98), (1.44, 2.17, 1.22), 2.6)
        paint(shoe, "plate", foot)
        paint(shoe & ((z < .55) | (np.abs(y - ay - .7) < .27)), "lame", foot)

    # Split surcoat, rear apron and articulated hip plates over a fitted belt.
    paint(ellipsoid((0, 0, 14), (3.9, 2.4, 2.25)), "mail", "pelvis")
    drop = np.clip(14.5 - z, 0, 7)
    radius = (x / (3.85 + .22 * drop)) ** 2 + (y / (2.62 + .18 * drop)) ** 2
    hem = 8.3 + .23 * np.abs(x)
    skirt = ((radius <= 1) & (radius > .48) & (z > hem) & (z < 14.8)
             & ((np.abs(x) > .48) | (y < 0)))
    paint(skirt, "navy", "pelvis")
    paint(skirt & ((z < hem + .55) | ((np.abs(x) < 1.02) & (y > 0))), "gilt", "pelvis")
    for level, breadth in [(12.1, 4.15), (13.1, 4.02), (14.1, 3.88)]:
        hip_plate = ellipsoid((0, -.1, level), (breadth, 2.72, 1.04), 2.6)
        paint(hip_plate & (np.abs(x) > 2.4), "lame" if level == 13.1 else "plate", "pelvis")

    # A keeled breastplate, gorget and backplate over a dark arming doublet.
    torso = ellipsoid((0, -.05, 18.25), (4.55, 2.83, 4.0), 2.35)
    paint(torso, "plate", "chest")
    paint(torso & (np.abs(x) < .52) & (y > 1.7), "ridge", "chest")
    breast = torso & (y > .6)
    chevron = 17.7 + .39 * np.abs(x)
    paint(breast & (np.abs(z - chevron) < .38), "lame", "chest")
    paint(breast & (np.abs(x) + .8*np.abs(z - 20.3) < 1.05), "gilt", "chest")
    paint(torso & (z < 16.3 + .17 * np.abs(x)), "lame", "chest")
    paint(ellipsoid((0, .0, 21.95), (2.75, 2.32, 1.12)), "lame", "chest")
    paint(ellipsoid((0, .04, 22.42), (2.18, 1.94, 1.03)), "mail", "chest")
    belt = ellipsoid((0, .0, 14.99), (3.75, 2.67, .89), 3.7)
    paint(belt, "leather", "pelvis")
    paint(ellipsoid((.4, 2.48, 15), (.86, .46, .65), 4), "gilt", "pelvis")

    # Raised visor, neck curtain and cheeks expose the face in front. The brow
    # rises in the middle. The cooling slits are cut into the visor surface.
    paint(ellipsoid((0, .25, 26.15), (3.36, 2.76, 3.74)), "skin", "head")
    hood = ellipsoid((0, -.17, 26.75), (3.78, 3.16, 3.72), 2.2)
    paint(hood & ((y < -.25) | ((np.abs(x) > 2.66) & (y < 1.7))), "lame", "head")
    bevor = ellipsoid((0, -.55, 25.48), (3.55, 2.81, 2.65), 2.6)
    paint(bevor & ((y < -.55) | ((np.abs(x) > 2.55) & (y < 1.88))), "plate", "head")
    nape = ellipsoid((0, -1.02, 24.32), (3.54, 2.48, .75))
    paint(nape & (y < .72), "lame", "head")
    fringe = ellipsoid((0, .45, 28.16), (3.38, 2.94, 2.18))
    paint(fringe & (z > 27.05 + .42*x), "hair", "head")
    for sign in (-1, 1):
        socket = ellipsoid((sign * 1.31, 2.82, 26.71), (.61, .53, .49))
        paint(socket, "skin", "head")
        eye = ellipsoid((sign * 1.48, 2.90, 26.80), (.61, .53, .49))
        paint(eye & (material_ids == materials["skin"]), "eyes", "head")
    paint(ellipsoid((0, 2.83, 25.98), (.55, .65, .67)), "skin", "head")
    helm = ellipsoid((0, -.16, 28.12), (3.86, 3.25, 3.22), 2.1)
    brow = 27.55 + .31 * y - .14 * np.abs(x)
    paint(helm & (z >= brow), "plate", "head")
    visor = ellipsoid((0, .30, 28.94), (3.95, 3.52, 2.03), 2.25) & (z > brow + .37)
    paint(visor, "ridge", "head")
    paint(visor & (y > 1.72) & (np.abs(x) < 2.85)
          & (np.cos((x + .23*z)*4.4) > .36) & (z > 29.0) & (z < 30.26), "lame", "head")
    # Visor lip and recessed ventilation slots span several source voxels.
    paint(visor & (z < 29.0 + .22*y) & (y > .5), "lame", "head")
    vents = (np.abs(np.abs(x + .22*(z - 30)) - 1.48) < .47)
    paint(visor & vents & (y > 1.25) & (z > 28.92) & (z < 30.75), "mail", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign*3.34, .15, 27.34), (.65, .88, .87)), "gilt", "head")
    comb = ellipsoid((0, -.2, 29.93), (.66, 2.75, 1.7), 1.6)
    paint(comb, "ridge", "head")

    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{k}_{side}"] for k in ("shoulder", "elbow", "hand"))
        upper, fore, fist = (f"{k}_{side}" for k in ("upper", "fore", "hand"))
        paint(capsule(shoulder, elbow + .14*(shoulder-elbow), 1.47, 1.12), "mail", upper)
        for distance, width, metal in [(1.65, 1.69, "lame"), (.94, 2.04, "lame"), (0, 2.28, "plate")]:
            center = shoulder + [sign * .16, 0, .42 - distance]
            paint(ellipsoid(center, (width, 1.98, 1.26)), metal, upper)
        paint(capsule(elbow, hand, 1.09, .96), "mail", fore)
        paint(capsule(elbow + .17*(hand-elbow), elbow + .87*(hand-elbow), 1.23, 1.04), "plate", fore)
        paint(ellipsoid(elbow, (1.3, 1.25, .85)), "lame", fore)
        paint(ellipsoid(hand, (1.14, 1.04, 1.09), 2.5), "lame", fist)

    # Sword: double-edged blade with a tapered point, curved guard.
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
    blade = (progress >= .1) & (progress <= 1) & (np.abs(across) <= width) & (np.abs(thick) <= .48)
    paint(blade, "blade", "sword")
    paint(blade & (np.abs(across) >= .55 * width), "edge", "sword")
    paint(capsule(hand - .12 * axis, hand + .08 * axis, .45), "leather", "sword")
    guard = hand + .09 * axis
    curl = .05 * axis
    paint(capsule(guard - 1.4 * side + curl, guard, .36) | capsule(guard, guard + 1.4 * side - curl, .36),
          "gilt", "sword")
    paint(ellipsoid(hand - .14 * axis, (.55, .55, .55)), "gilt", "sword")

    # Convex kite shield. Coordinates (u, v) lie on its own surface, so
    # rim, charge and rear lining all follow the left wrist in every view.
    normal = np.array([.33, .944, 0])
    normal /= np.linalg.norm(normal)
    tangent = np.array([normal[1], -normal[0], 0])
    local = xyz - joints["shield_center"]
    u, v, depth = local @ tangent, local[..., 2], local @ normal
    widths_z = [-8.55, -6.9, -3.8, 1.5, 5.7, 8.45]
    widths = [.18, 2.4, 4.5, 5.77, 5.92, .15]
    half = np.interp(v, widths_z, widths)
    front = .67 - .044 * u**2
    shield = ((np.abs(u) <= half) & (v >= widths_z[0]) & (v <= widths_z[-1])
              & (depth <= front) & (depth >= front - 1.86))
    paint(capsule(joints["hand_L"], joints["shield_center"] - .35*normal, .83), "leather", "shield")
    paint(shield, "leather", "shield")
    # Enarmes cross the lined back; the charge is confined to the outward ply.
    straps = (np.abs(v - .28*u - 2.3) < .48) | (np.abs(v - .28*u + 2.4) < .48)
    paint(shield & straps & (depth < front - 1.0), "mail", "shield")
    face = shield & (depth > front - .98)
    paint(face, "field", "shield")
    paint(shield & ((np.abs(u) > half - .70) | (v < -7.8) | (v > 7.65)), "rim", "shield")

    # Heraldic lily: spear-shaped centre petal, two returning lateral petals,
    # a cross-band and a three-point foot. Thickness survives 48 px projection.
    charge = [
        "....#....",
        "...###...",
        "....#....",
        ".#..#..#.",
        "##..#..##",
        ".##.#.##.",
        "#.#####.#",
        "...###...",
        "..#####..",
        "....#....",
        "...###...",
        "..#.#.#..",
        "....#....",
    ]
    inlay = np.array([list(row) for row in charge]) == "#"
    col = np.floor(u / .99 + 4.5).astype(int)
    row = np.floor((6.1 - v) / .90).astype(int)
    inside = (row >= 0) & (row < len(charge)) & (col >= 0) & (col < len(charge[0]))
    motif = inlay[row.clip(0, len(charge) - 1), col.clip(0, len(charge[0]) - 1)]
    paint(face & inside & motif, "lily", "shield")
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
