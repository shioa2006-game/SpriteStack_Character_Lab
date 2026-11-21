"""Build the crystal mage's material and part volumes from solid shapes read off one reference image.

The mage is a slender young man: messy dark indigo hair, a beige hood rolled
around the neck, a slate-blue cape that covers the shoulders, closes with a
round clasp on the chest and flares out behind and to both sides, a long beige
robe split at the front over a blue lining, two leather belts, dark trousers and
knee-high boots. A tall staff with a twisted wooden head and a blue crystal is
in the right hand and a thick dark-blue book in the left.

Hair belongs to the head part, the hood and cape to the chest part and the robe
skirt to the pelvis part, so the shared 17-slot biped rig is used unchanged: the
two attachment slots that hold LARK's sword and shield hold the staff and book.
"""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SHAPE = (66, 44, 56)


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

    def tube(points, radius, radius_end):
        """A curved tube through sample points, tapering along its length."""
        mask = np.zeros(SHAPE, dtype=bool)
        radii = np.linspace(radius, radius_end, len(points))
        for a, b, ra, rb in zip(points[:-1], points[1:], radii[:-1], radii[1:]):
            mask |= capsule(a, b, ra, rb)
        return mask

    def unit(v):
        return v / np.linalg.norm(v)

    # ---- Legs: dark trousers tucked into knee-high boots with a strap under the cuff.
    for side in ("R", "L"):
        hip, knee, ankle, toe = (joints[f"{name}_{side}"] for name in ("hip", "knee", "ankle", "toe"))
        paint(capsule(hip, knee, 1.12, .95), "trousers", f"thigh_{side}")
        shin = f"shin_{side}"
        paint(capsule(knee, ankle, .95, .86) & (z > 5.6), "trousers", shin)
        paint(capsule(knee, ankle, .98, .88) & (z <= 5.6), "boot", shin)
        cuff = capsule(knee, ankle, 1.1) & (z > 4.9) & (z <= 5.8)
        paint(cuff, "boot", shin)
        paint(capsule(knee, ankle, 1.04) & (z > 4.35) & (z <= 4.75), "belt", shin)
        boot = f"boot_{side}"
        forward = unit((toe - ankle) * [1, 1, 0])
        across = np.array([forward[1], -forward[0], 0])
        center = ankle * [1, 1, 0] + forward * .75
        local = xyz - center
        along, lateral = local @ forward, local @ across
        foot = ((along / 1.95) ** 2 + (lateral / 1.02) ** 2 + np.abs((z - .95) / 1.05) ** 2.4 <= 1) & (z >= .45)
        heel = ellipsoid(ankle * [1, 1, 0] + [0, 0, 1.4], (.98, .98, 1.4), 2.2) & (z >= .45)
        paint(foot | heel, "boot", boot)
        sole = ((along / 2.05) ** 2 + (lateral / 1.08) ** 2 <= 1) & (z < .5)
        paint(sole | (ellipsoid(ankle * [1, 1, 0], (1.0, 1.0, .5)) & (z < .5)), "sole", boot)

    # ---- Pelvis: hidden trouser seat, the long robe skirt split at the front, two belts.
    paint(ellipsoid((0, -.1, 12.5), (2.3, 1.75, 1.3), 2.2), "trousers", "pelvis")
    angle = np.degrees(np.arctan2(x, y + .1))  # 0 at the front, positive toward the anatomical left
    turn = np.abs(angle)
    drop = np.clip(15.3 - z, 0, None)
    skirt_rx, skirt_ry = 2.78 + .24 * drop, 2.12 + .17 * drop
    pleats = 1 - .03 * np.clip(drop / 8, 0, 1) * np.cos(np.radians(angle) * 5)
    radial = np.sqrt((x / skirt_rx) ** 2 + ((y + .1) / skirt_ry) ** 2) * pleats
    hem = 7.3 + .3 * (1 - np.cos(np.radians(angle))) / 2
    slit = 2 + 1.9 * np.clip(11.4 - z, 0, None)
    skirt = (radial <= 1) & (radial >= 1 - .85 / np.minimum(skirt_rx, skirt_ry)) & (z <= 15.3) & (z >= hem)
    skirt &= turn >= slit
    paint(skirt, "robe", "pelvis")
    # Blue lining shows on the folded front edges and as one line above the split.
    paint(skirt & (turn < slit + 11) & (z < 14.2), "robe lining", "pelvis")
    # Belts: a wide waist belt with a steel buckle and a looser belt slung toward the left hip.
    waist = (radial <= 1.07) & (z >= 14.55) & (z <= 15.25)
    paint(waist, "belt", "pelvis")
    paint(ellipsoid((.6, 2.25, 14.9), (.55, .35, .42), 4), "buckle", "pelvis")
    slung = (radial <= 1.09) & (radial >= .9) & (np.abs(z - (13.75 - .16 * x)) <= .3)
    paint(slung, "belt", "pelvis")

    # ---- Chest: robe torso with the wrap line of its crossed front panels.
    torso = (ellipsoid((0, -.15, 17.0), (2.55, 1.85, 2.45), 2.3)
             | ellipsoid((0, -.2, 18.85), (3.3, 1.75, 1.05), 2.3)
             | ellipsoid((0, -.1, 15.3), (2.65, 2.0, 1.0), 2.3))
    paint(torso, "robe", "chest")
    wrap = torso & (y > .9) & (np.abs(z - (18.0 + 1.6 * (x - .5))) < .32) & (z < 18.1)
    paint(wrap, "robe shade", "chest")

    # ---- Cape, lower part: a bell that hangs behind the arms and flares out to the sides.
    # Painted before the arms so the sleeves stay in front of it.
    top = 17.4
    t = np.clip(top - z, 0, None)
    cape_rx = 5.0 + .30 * t + .013 * t ** 2
    cape_ry = 3.1 + .08 * t + .004 * t ** 2
    cape_cy = -.35 - .08 * t
    cape_angle = np.degrees(np.arctan2(x, y - cape_cy))
    cape_turn = np.abs(cape_angle)
    folds = 1 - .035 * np.clip(t / 10, 0, 1) * np.cos(np.radians(cape_angle) * 5)
    cape_radial = np.sqrt((x / cape_rx) ** 2 + ((y - cape_cy) / cape_ry) ** 2) * folds
    edge = 100 - 18 * np.clip((15 - z) / 8, 0, 1)
    back = np.clip((180 - cape_turn) / 90, 0, 1)
    cape_hem = (4.6 + 3.6 * back ** 1.3
                - 1.9 * np.exp(-((cape_turn - edge - 6) / 8) ** 2)
                + .6 * np.abs(np.sin(np.radians(cape_turn) * 9)))
    shell_scale = np.minimum(cape_rx, cape_ry)
    bell = ((cape_radial <= 1) & (cape_radial >= 1 - 1.15 / shell_scale)
            & (z <= top) & (z >= cape_hem))
    inner = cape_radial < 1 - .8 / shell_scale
    lower = bell & (cape_turn >= edge) & (z < 16.9)
    paint(lower, "cape", "chest")
    paint(lower & inner, "cape lining", "chest")

    # ---- Arms: wide beige sleeves, a strip of bare forearm, leather bracers, fingerless gloves.
    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "hand"))
        upper, fore, fist = (f"{name}_{side}" for name in ("upper", "fore", "hand"))
        paint(capsule(shoulder, elbow, 1.0, 1.1), "robe", upper)
        # The shoulder stays below the mantle shell so no sleeve voxel pokes through it.
        paint(ellipsoid(shoulder + [sign * .1, 0, -.55], (1.1, 1.1, 1.0), 2.2), "robe", upper)
        axis = hand - elbow
        cuff = elbow + .5 * axis
        sleeve = capsule(elbow, cuff, 1.12, 1.55)
        opening = capsule(elbow + .32 * axis, cuff + .2 * axis, .7, 1.2)
        paint(sleeve & ~opening, "robe", fore)
        paint(sleeve & opening & capsule(elbow, cuff, 1.12, 1.4), "robe shade", fore)
        paint(capsule(elbow + .3 * axis, elbow + .66 * axis, .55), "skin", fore)
        paint(capsule(elbow + .6 * axis, elbow + .9 * axis, .72), "bracer", fore)

    # ---- Cape, upper part: a mantle over the shoulders that meets at the clasp. It is
    # painted after the arms so it covers the tops of the sleeves.
    dome = ellipsoid((0, -.35, top), (5.0, 3.1, 3.1), 2.6) & (z >= top)
    dome &= ~ellipsoid((0, -.35, top), (4.3, 2.4, 2.4), 2.6)
    collar = (x ** 2 + (y + .35) ** 2 <= 1.6 ** 2)
    mantle_band = bell & (z >= 16.9)
    front = y > .3
    below_clasp = front & (z < 18.1 - .55 * np.abs(x - .5))
    above_clasp = front & (z > 18.35 + 1.0 * np.abs(x - .5))
    mantle = (dome & ~collar | mantle_band) & ~below_clasp & ~above_clasp
    paint(mantle, "cape", "chest")
    paint(mantle & ~dome & inner, "cape lining", "chest")
    paint(ellipsoid((.5, 2.75, 18.15), (.62, .45, .62), 2.2), "clasp", "chest")

    # ---- Hood: a beige roll around the back and sides of the neck, bunched up behind the head.
    ring = np.sqrt((x / 2.05) ** 2 + ((y + .5) / 1.85) ** 2)
    hood_turn = np.abs(np.degrees(np.arctan2(x, y + .5)))
    roll = ((ring - 1) * 1.95) ** 2 + ((z - 20.35) / .9) ** 2 <= .85 ** 2
    paint(roll & (hood_turn >= 42), "hood", "chest")
    paint(ellipsoid((0, -2.3, 21.0), (2.25, 1.2, 1.3), 2.2), "hood", "chest")

    # ---- Head: face, neck, eyes and messy hair with tufts, side flicks and nape locks.
    paint(capsule((0, 0, 19.4), (0, .3, 22.0), .85), "skin", "head")
    locks = (
        ((-.7, -.3, 27.4), (-1.3, -1.4, 30.0), 1.0, .35),
        ((.9, .3, 27.5), (1.9, -.3, 29.7), .95, .3),
        ((0, -1.6, 27.2), (.1, -3.6, 28.9), 1.0, .3),
        ((-2.8, -.9, 25.0), (-4.9, -2.0, 23.0), .85, .3),
        ((-2.9, -1.7, 26.3), (-5.1, -2.6, 25.6), .8, .3),
        ((2.8, -.8, 24.6), (4.4, -1.6, 22.8), .8, .3),
        ((2.8, -1.5, 26.1), (4.7, -2.1, 25.5), .7, .3),
    ) + tuple(((x0, -2.4, 24.6), (1.2 * x0, -3.4, 21.3), 1.0, .35) for x0 in (-2.2, -.75, .7, 2.1))
    for start, tip, start_radius, tip_radius in locks:
        paint(capsule(start, tip, start_radius, tip_radius), "hair", "head")
    for sign in (-1, 1):
        paint(capsule((sign * 2.85, .1, 26.0), (sign * 2.95, .3, 22.6), .85, .35), "hair", "head")
    paint(ellipsoid((0, -1.3, 23.6), (3.3, 2.6, 2.5), 2.2), "hair", "head")
    bangs = (25.6 - .9 * np.clip(1 - np.abs(x - .9) / .8, 0, None)
             - .7 * np.clip(1 - np.abs(x + 1.3) / .7, 0, None)
             - .5 * np.clip(1 - np.abs(x - 2.4) / .6, 0, None))
    face_front = (y > .5) & (z < bangs)
    crown = ellipsoid((0, -.2, 25.4), (3.45, 3.6, 3.45), 2.3)
    paint(crown & ~face_front, "hair", "head")
    strands = np.sin(2.2 * x + 1.3 * z + .7 * y) > .78
    paint((material_ids == materials["hair"]) & (part_ids == parts["head"]) & strands & (z < 27.2),
          "hair shade", "head")
    skull = ellipsoid((0, .3, 24.7), (2.95, 3.0, 3.35), 2.2)
    jaw = ellipsoid((0, .9, 22.3), (2.05, 2.05, 1.75))
    face = (skull | jaw) & ~((material_ids == materials["hair"]) | (material_ids == materials["hair shade"]))
    paint(face, "skin", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 1.1, 2.95, 23.8), (.42, .55, .62), 2.2) & (skull | jaw), "eyes", "head")

    # ---- Staff: a straight shaft through the right fist, planted near the right foot,
    # with a metal ferrule, carved rings and a three-pronged twisted head around a crystal.
    grip = joints["hand_R"]
    foot = np.array([-6.0, .5, 0.0])
    up = unit(grip - foot)
    shaft_top = foot + up * (26.8 / up[2])
    paint(capsule(foot + up * .3, shaft_top, .62, .68), "staff wood", "staff")
    paint(capsule(foot, foot + up * 2.4, .66, .64), "ferrule", "staff")
    for height in (24.4, 25.6):
        ring_center = foot + up * (height / up[2])
        paint(capsule(ring_center - up * .25, ring_center + up * .25, .82), "staff carving", "staff")
    side_a = unit(np.cross(up, [0, 1, 0]))
    side_b = np.cross(up, side_a)
    crystal_center = shaft_top + up * 2.25
    # Two prongs rise on the outer and inner sides and twist 40 degrees around the shaft,
    # so the crystal stays open to the front and back views.
    prongs = ((0, 31.2 - shaft_top[2], 2.1, 40), (180, 30.4 - shaft_top[2], 2.0, 40))
    for start_angle, rise, reach, twist in prongs:
        s = np.linspace(0, 1, 28)
        theta = np.radians(start_angle + twist * s)
        radius = reach * np.sin(np.pi * np.clip(s * .9 + .05, 0, 1)) ** .8 + .2 * s
        points = [shaft_top + up * (rise * si) + r * (np.cos(th) * side_a + np.sin(th) * side_b)
                  for si, r, th in zip(s, radius, theta)]
        paint(tube(points, .38, .2), "staff carving", "staff")
    spin = np.radians(20)
    u = np.cos(spin) * side_a + np.sin(spin) * side_b
    v = np.cross(up, u)
    local = xyz - crystal_center
    crystal = np.abs(local @ u) / 1.2 + np.abs(local @ v) / 1.2 + np.abs(local @ up) / 2.25 <= 1
    paint(crystal, "crystal", "staff")
    paint(crystal & (np.abs(local @ u) + np.abs(local @ v) < .45) & (local @ up > -.9), "crystal glow", "staff")
    # The right fist closes around the shaft, with bare fingers on the outer side.
    paint(ellipsoid(grip + [.12, .05, 0], (.82, .82, .95), 2.2), "glove", "hand_R")
    paint(ellipsoid(grip + [-.25, .55, .1], (.55, .4, .7), 2.2), "skin", "hand_R")

    # ---- Book: thick dark-blue cover, cream page block, spine toward the body, held
    # against the chest by the left hand on its lower front.
    center = joints["book_center"]
    lean, toward = np.radians(-8), np.radians(25)
    width_axis = np.array([np.cos(lean), 0, -np.sin(lean)])
    height_axis = np.array([np.sin(lean), 0, np.cos(lean)])
    height_axis = np.cos(toward) * height_axis + np.sin(toward) * np.array([0, 1, 0])
    depth_axis = np.cross(height_axis, width_axis)
    local = xyz - center
    du, dv, dw = local @ width_axis, local @ depth_axis, local @ height_axis
    book = (np.abs(du) / 1.65) ** 12 + (np.abs(dv) / .9) ** 12 + (np.abs(dw) / 2.05) ** 12 <= 1
    paint(book, "book cover", "book")
    paint(book & (np.abs(dv) <= .6) & (du > -1.25), "book pages", "book")
    hold = joints["hand_L"]
    paint(ellipsoid(hold, (.8, .75, .85), 2.2), "glove", "hand_L")
    paint(ellipsoid(hold + [-.8, .35, .1], (.75, .38, .5), 2.2), "skin", "hand_L")
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
