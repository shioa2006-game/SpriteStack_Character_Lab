"""Build AZURE RONIN's material and part volumes from solid shapes read off one reference image.

AZURE RONIN is a lean young swordsman: dark navy hair tied in a high ponytail
with two blue ribbons, a charcoal scarf wrapped over the nose and mouth with a
long tail hanging behind, a pale beige sleeveless tunic crossed by a leather
strap, a belt with a blue sash knot, layered skirt panels (beige outside, blue
underneath, the back panels long), baggy charcoal trousers with knee guards and
blue shin wraps, brown boots, dark bracers, a short sword hilt at the left hip
and a slightly curved one-handed sword held low in the right hand. The left
hand is empty.

Hair, ponytail and the face part of the scarf belong to the head part; the
tunic, scarf collar and tail to the chest part; the belt, sash, skirt panels and
hip sword to the pelvis part. The rig is the shared biped with one attachment
slot (the sword in hand_R), so the parts are the 15 body parts plus the sword.
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

    def is_material(*names):
        return np.isin(material_ids, [materials[name] for name in names])

    # ---- Legs: baggy charcoal trousers, metal knee guards, blue shin wraps above
    # knee-high brown boots with two buckle straps.
    for side in ("R", "L"):
        hip, knee, ankle, toe = (joints[f"{name}_{side}"] for name in ("hip", "knee", "ankle", "toe"))
        paint(capsule(hip, knee, 1.32, 1.08), "trousers", f"thigh_{side}")
        shin = f"shin_{side}"
        paint(capsule(knee, ankle, 1.05, .9) & (z > 5.5), "trousers", shin)
        paint(capsule(knee, ankle, .98, .88) & (z <= 5.5), "boot", shin)
        paint(capsule(knee, ankle, 1.1) & (z > 4.8) & (z <= 5.5), "boot", shin)
        paint(capsule(knee, ankle, 1.14) & (z > 5.5) & (z <= 6.4), "blue cloth", shin)
        paint(capsule(knee, ankle, 1.03) & (np.abs(z - 3.4) <= .25), "belt", shin)
        paint(ellipsoid(knee + [0, .78, .15], (.98, .6, 1.05), 2.2), "metal", shin)
        boot = f"boot_{side}"
        forward = unit((toe - ankle) * [1, 1, 0])
        across = np.array([forward[1], -forward[0], 0])
        center = ankle * [1, 1, 0] + forward * .75
        local = xyz - center
        along, lateral = local @ forward, local @ across
        foot = ((along / 1.95) ** 2 + (lateral / 1.02) ** 2 + np.abs((z - .95) / 1.05) ** 2.4 <= 1) & (z >= .45)
        heel = ellipsoid(ankle * [1, 1, 0] + [0, 0, 1.4], (.98, .98, 1.4), 2.2) & (z >= .45)
        paint(foot | heel, "boot", boot)
        paint((foot | heel) & (np.abs(z - 1.7) <= .25) & (along > -.6), "belt", boot)
        sole = ((along / 2.05) ** 2 + (lateral / 1.08) ** 2 <= 1) & (z < .5)
        paint(sole | (ellipsoid(ankle * [1, 1, 0], (1.0, 1.0, .5)) & (z < .5)), "sole", boot)

    # ---- Pelvis: hidden trouser seat, then two layers of skirt panels hanging from the belt.
    paint(ellipsoid((0, -.1, 12.6), (2.4, 1.8, 1.4), 2.2), "trousers", "pelvis")
    angle = np.degrees(np.arctan2(x, y + .1))  # 0 at the front, positive toward the anatomical left
    turn = np.abs(angle)
    top = 15.0
    drop = np.clip(top - z, 0, None)
    # Blue underlayer: a full bell with pointed tips, open over the crotch at the front.
    blue_rx, blue_ry = 2.72 + .2 * drop, 2.06 + .14 * drop
    blue_radial = np.sqrt((x / blue_rx) ** 2 + ((y + .1) / blue_ry) ** 2)
    blue_scale = np.minimum(blue_rx, blue_ry)
    tips = np.abs(((angle + 180) / 36) % 1 - .5) * 2  # 0 at a tip, 1 between tips
    blue_hem = 7.6 + 1.5 * tips + 1.2 * np.clip((90 - turn) / 50, 0, 1)
    blue = ((blue_radial <= 1) & (blue_radial >= 1 - 1.15 / blue_scale) & (z <= top) & (z >= blue_hem)
            & ~((turn < 34 + 8 * np.clip(12.5 - z, 0, None)) & (z < 12.5)))
    paint(blue, "blue cloth", "pelvis")
    paint(blue & (blue_radial < 1 - .8 / blue_scale), "blue lining", "pelvis")
    # Beige outer panels, lined in blue: a pointed front apron, two side panels and
    # long back panels that flare out toward the left. Gaps between them show the blue.
    flare = np.clip((angle - 95) / 60, 0, 1) * .16 * drop
    outer_rx, outer_ry = blue_rx + .55 + flare, blue_ry + .55 + .5 * flare
    outer_radial = np.sqrt((x / outer_rx) ** 2 + ((y + .1) / outer_ry) ** 2)
    outer_scale = np.minimum(outer_rx, outer_ry)
    shell = (outer_radial <= 1) & (outer_radial >= 1 - 1.15 / outer_scale) & (z <= top)
    apron = (turn <= 24) & (z >= 10.4 + 2.4 * turn / 24)
    sides = (turn >= 50) & (turn <= 112) & (z >= 9.8 + 1.6 * np.abs(turn - 81) / 31)
    back = (turn >= 124) & (turn <= 168) & (z >= 6.6 + 1.2 * np.abs(((turn - 124) / 22) % 1 - .5) * 2)
    panels = shell & (apron | sides | back)
    paint(panels, "tunic", "pelvis")
    paint(panels & (outer_radial < 1 - .8 / outer_scale), "blue lining", "pelvis")
    # A darker seam line along each panel edge keeps the layers apart at 48 px.
    seam = panels & ((np.abs(turn - 24) < 4) | (np.abs(turn - 50) < 4) | (np.abs(turn - 112) < 4)
                     | (np.abs(turn - 124) < 4) | (np.abs(turn - 168) < 4))
    paint(seam & (outer_radial >= 1 - .8 / outer_scale), "tunic shade", "pelvis")
    # Belt with a steel buckle on the right of center, and a blue sash knot on the left
    # with two short tails over the apron.
    belt_radial = np.sqrt((x / 2.95) ** 2 + ((y + .1) / 2.25) ** 2)
    paint((belt_radial <= 1.04) & (z >= 14.55) & (z <= 15.25), "belt", "pelvis")
    paint(ellipsoid((-.75, 2.3, 14.9), (.5, .35, .42), 4), "buckle", "pelvis")
    paint(ellipsoid((1.05, 2.35, 14.75), (.62, .42, .55), 2.2), "blue cloth", "pelvis")
    paint(capsule((.9, 2.5, 14.4), (1.0, 2.95, 12.0), .42, .3), "blue cloth", "pelvis")
    paint(capsule((1.35, 2.4, 14.4), (1.75, 2.85, 12.6), .4, .3), "blue cloth", "pelvis")

    # ---- Short sword at the left hip: a dark hilt above the belt, the scabbard slung
    # back and down over the skirt panels.
    hilt_top, mouth, scabbard_end = np.array([2.55, 1.85, 16.9]), np.array([2.95, 1.0, 15.0]), np.array([4.5, -3.1, 10.9])
    paint(capsule(hilt_top, mouth, .42), "sword grip", "pelvis")
    paint(capsule(mouth, scabbard_end, .5, .45), "sheath", "pelvis")
    paint(ellipsoid(mouth, (.62, .62, .62)), "tsuba", "pelvis")

    # ---- Chest: sleeveless beige tunic with a blue inner collar and a leather strap
    # from the right shoulder to the left hip, front and back.
    torso = (ellipsoid((0, -.15, 17.0), (2.45, 1.75, 2.4), 2.3)
             | ellipsoid((0, -.2, 18.8), (3.15, 1.7, 1.05), 2.3)
             | ellipsoid((0, -.1, 15.3), (2.55, 1.95, 1.0), 2.3))
    paint(torso, "tunic", "chest")
    collar = torso & (y > .9) & (np.abs(z - (18.9 + 1.2 * (x + .2))) < .3) & (z < 19.4) & (x > -1.2)
    paint(collar, "blue cloth", "chest")
    strap = torso & (np.abs(z - (17.2 - .85 * x)) < .5) & (np.abs(y + .15) > .9)
    paint(strap, "belt", "chest")

    # ---- Scarf tail: a wide flat strip from the back of the collar on the right that
    # sways back and outward to below the waist. Two tubes side by side along the
    # body's surface make it about 2.4 units wide and 1.3 thick. Painted before the
    # arms so the right arm stays in front of it.
    tail = np.array([(-1.3, -2.2, 20.2), (-2.6, -3.4, 18.8), (-3.6, -4.4, 16.6), (-4.4, -5.2, 14.2),
                     (-5.0, -5.8, 11.8), (-5.3, -6.0, 10.2)])
    surface = unit(np.array([-1.0, 1.0, 0]))
    for shift, end_radius in ((-.55, .5), (.55, .4)):
        paint(tube(tail + shift * surface, .68, end_radius), "scarf", "chest")

    # ---- Arms: bare upper arms, a leather band on the left, long dark bracers with
    # metal plates, fingerless gloves.
    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "hand"))
        upper, fore, fist = (f"{name}_{side}" for name in ("upper", "fore", "hand"))
        paint(capsule(shoulder, elbow, .95, .85), "skin", upper)
        paint(ellipsoid(shoulder + [sign * .1, 0, -.45], (1.05, 1.05, .95), 2.2), "skin", upper)
        axis = hand - elbow
        paint(capsule(elbow + .12 * axis, hand - .18 * axis, .88, .82), "bracer", fore)
        outward = unit(np.array([sign, 0, 0]) - unit(axis) * (unit(axis) @ [sign, 0, 0]))
        paint(capsule(elbow + .25 * axis + .62 * outward, elbow + .6 * axis + .6 * outward, .42), "metal", fore)
        paint(capsule(elbow, elbow + .14 * axis, .82), "skin", fore)
    shoulder, elbow = joints["shoulder_L"], joints["elbow_L"]
    band = capsule(shoulder + .5 * (elbow - shoulder), shoulder + .62 * (elbow - shoulder), 1.03)
    paint(band, "belt", "upper_L")

    # ---- Scarf collar: a bulky wrap over the shoulders and around the neck, with folds.
    # Painted after the arms so it covers the shoulder tops.
    cowl = ellipsoid((0, -.25, 19.55), (3.75, 2.55, 1.25), 2.2) & (z >= 18.7)
    wrap = ellipsoid((0, .05, 20.6), (2.7, 2.55, 1.3), 2.2)
    paint(cowl | wrap, "scarf", "chest")

    # ---- Head: neck, skull, eyes, swept bangs and side locks, then the high ponytail.
    paint(capsule((0, 0, 19.4), (0, .3, 22.0), .85), "skin", "head")
    skull = ellipsoid((0, .3, 24.7), (2.95, 3.0, 3.35), 2.2)
    jaw = ellipsoid((0, .9, 22.3), (2.05, 2.05, 1.75))
    paint(skull | jaw, "skin", "head")
    # Hair is pulled back to the tie, so the back of the head is a tight, smooth shell.
    paint(ellipsoid((0, -.2, 24.9), (3.15, 3.05, 3.45), 2.2) & ~(y > .5) & (z > 22.4), "hair", "head")
    crown = ellipsoid((0, .1, 25.5), (3.3, 3.25, 3.2), 2.3)
    bangs = (25.5 - .9 * np.clip(1 - np.abs(x - .5) / .75, 0, None)
             - .8 * np.clip(1 - np.abs(x + 1.6) / .7, 0, None)
             - .6 * np.clip(1 - np.abs(x - 2.3) / .6, 0, None))
    paint(crown & ~((y > .5) & (z < bangs)), "hair", "head")
    locks = (
        ((-2.2, 1.4, 27.2), (-2.9, 2.7, 25.0), .85, .3),
        ((.4, 2.1, 27.6), (.6, 3.25, 24.9), .8, .3),
        ((2.1, 1.6, 27.3), (2.8, 2.7, 25.3), .8, .3),
    )
    for start, tip, start_radius, tip_radius in locks:
        paint(capsule(start, tip, start_radius, tip_radius), "hair", "head")
    for sign in (-1, 1):
        paint(capsule((sign * 2.95, .6, 25.6), (sign * 3.05, .9, 23.0), .75, .3), "hair", "head")
        paint(capsule((sign * 2.3, .4, 27.4), (sign * 3.7, -.2, 27.9), .7, .3), "hair", "head")
        paint(capsule((sign * 2.6, -1.2, 26.6), (sign * 3.75, -1.9, 25.6), .7, .3), "hair", "head")
    strands = np.sin(2.4 * x + 1.4 * z + .6 * y) > .8
    paint(is_material("hair") & (part_ids == parts["head"]) & strands, "hair shade", "head")
    for sign in (-1, 1):
        paint(ellipsoid((sign * 1.1, 2.95, 24.15), (.45, .55, .62), 2.2) & (skull | jaw), "eyes", "head")
    # Ponytail: tied high at the back of the crown, a short upward tuft at the tie,
    # then a thick tail that arcs up and back, clear of the head, and falls behind the
    # right shoulder. Its own shading group draws a line where it crosses the head.
    tie = np.array([0, -3.0, 27.7])
    for sign in (-1, 1):
        paint(capsule(tie + [0, .2, .1], tie + [sign * .9, -.9, .9], .62, .3), "ponytail", "head")
    tail = [tie, tie + [-.2, -1.4, .2], tie + [-.7, -2.4, -.9], tie + [-1.4, -2.75, -2.8],
            tie + [-2.2, -2.5, -4.8], tie + [-2.9, -2.0, -6.5], tie + [-3.4, -1.5, -7.9]]
    paint(tube(tail, 1.15, .45), "ponytail", "head")
    # Two blue ribbons from the knot, falling on both sides of the tail.
    ribbons = ([tie + [-.5, -.3, -.1], tie + [-1.6, -1.0, -1.4], tie + [-2.3, -1.1, -3.5]],
               [tie + [.4, -.4, -.2], tie + [.8, -1.6, -1.7], tie + [.8, -1.9, -3.9]])
    for points in ribbons:
        paint(tube(points, .42, .3), "hair ribbon", "head")
    paint(ellipsoid(tie, (.8, .75, .65), 2.2), "hair ribbon", "head")

    # ---- Scarf mask: covers the nose and mouth up to just below the eyes, bulging
    # forward over the nose. Part of the head so it would turn with the face.
    mask = (ellipsoid((0, .55, 21.9), (2.55, 2.6, 1.75), 2.2) | ellipsoid((0, 1.35, 22.3), (2.3, 1.85, 1.2), 2.2))
    paint(mask & (z <= 22.9 - .25 * np.clip(y - 2.0, 0, None)), "scarf", "head")
    # Fold lines across the whole scarf, keeping each voxel in its part.
    folds = is_material("scarf") & (np.sin(3.1 * z - 1.3 * x + .8 * y) > .72)
    for owner in ("head", "chest"):
        paint(folds & (part_ids == parts[owner]), "scarf shade", owner)

    # ---- Sword: a slightly curved single-edged blade held low and out, its edge on
    # the convex side, a round tsuba and a navy-wrapped grip through the right fist.
    hand, tip = joints["hand_R"], joints["sword_tip"]
    down = unit(tip - hand)
    tsuba = hand + .95 * down
    length = np.linalg.norm(tip - tsuba)
    bow = unit(np.array([-1.0, 0, 0]) - down * (down @ [-1.0, 0, 0]))  # outward and up
    flat = np.cross(down, bow)
    sagitta = .85  # about 7% of the blade: the reference's 2.6% is under one voxel
    local = xyz - tsuba
    s = np.clip((local @ down) / length, 0, 1)
    offset = local - s[..., None] * length * down - (4 * sagitta * s * (1 - s))[..., None] * bow
    across, thick = offset @ bow, offset @ flat
    along = (local @ down) / length
    half_width = np.where(s < .88, .56 - .1 * s, .47 * np.clip((1 - s) / .12, 0, 1) + .05)
    blade = (along >= 0) & (along <= 1) & (np.abs(across) <= half_width) & (np.abs(thick) <= .45)
    paint(blade, "blade", "sword")
    paint(blade & (across >= .35 * half_width), "blade edge", "sword")
    disc = local @ down
    radial = np.linalg.norm(local - disc[..., None] * down, axis=-1)
    paint((np.abs(disc + .05) <= .3) & (radial <= .95), "tsuba", "sword")
    pommel = hand - 2.3 * down
    paint(capsule(tsuba - .3 * down, pommel, .48, .44), "sword grip", "sword")
    paint(ellipsoid(pommel - .1 * down, (.5, .5, .5)), "tsuba", "sword")
    # The right fist closes around the grip: dark fingerless glove, bare fingers in front.
    paint(ellipsoid(hand + [-.05, 0, .1], (.8, .8, .9), 2.2), "bracer", "hand_R")
    paint(ellipsoid(hand + [.25, .5, 0], (.5, .42, .62), 2.2), "skin", "hand_R")
    # The empty left hand hangs open: glove over the palm, bare fingers below.
    hold = joints["hand_L"]
    paint(ellipsoid(hold + [0, 0, .15], (.62, .78, .8), 2.2), "bracer", "hand_L")
    paint(ellipsoid(hold + [.05, .15, -.75], (.5, .62, .6), 2.2), "skin", "hand_L")
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
