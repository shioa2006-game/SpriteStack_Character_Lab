"""Build CRIMSON BLADE's rest slices. Axes are anatomical left, forward, up."""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SHAPE = (66, 56, 64)


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

    # Each greave has a kicked-out knee, a dark underplate and a raised gold spine.
    for side, sign in (("R", -1), ("L", 1)):
        hip, knee, ankle, toe = (joints[f"{name}_{side}"] for name in ("hip", "knee", "ankle", "toe"))
        thigh, shin = f"thigh_{side}", f"shin_{side}"
        breeches = capsule(hip, knee, 1.73, 1.18) & (z <= hip[2] + .35)
        paint(breeches, "crimson", thigh)
        fold = (y < -.42) & (np.sin(z * .78 + sign * x * 1.35) > .46)
        paint(breeches & fold, "garnet", thigh)
        paint(capsule(knee, ankle, 1.02, .77), "boot", shin)
        plate = capsule(knee + [0, .18, -.28], ankle + [0, .26, .35], 1.1, .88)
        paint(plate, "plate", shin)
        paint(plate & (np.abs(z - (4.15 + sign * x * .25)) < .28), "gilt", shin)
        cap = ellipsoid(knee + [0, .43, .1], (1.25, 1, 1.25), 2.4)
        paint(cap, "lame", shin)
        paint(cap & (z > knee[2] - .38 + .22 * np.abs(x - knee[0])), "plate", shin)
        paint(cap & (y > knee[1] + .8) & (np.abs(x - knee[0]) < .30), "gilt", shin)
        boot = f"boot_{side}"
        forward = unit((toe - ankle) * [1, 1, 0])
        across = np.array([forward[1], -forward[0], 0])
        center = ankle * [1, 1, 0] + forward * .75
        local = xyz - center
        along, lateral = local @ forward, local @ across
        foot = ((along / 1.95) ** 2 + (lateral / 1.02) ** 2 + np.abs((z - .95) / 1.05) ** 2.4 <= 1) & (z >= .45)
        heel = ellipsoid(ankle * [1, 1, 0] + [0, 0, 1.4], (.98, .98, 1.4), 2.2) & (z >= .45)
        paint(foot | heel, "boot", boot)
        paint((foot | heel) & (np.abs(z - 1.7) <= .25) & (along > -.6), "garnet", boot)
        sole = ((along / 2.05) ** 2 + (lateral / 1.08) ** 2 <= 1) & (z < .5)
        paint(sole | (ellipsoid(ankle * [1, 1, 0], (1.0, 1.0, .5)) & (z < .5)), "sole", boot)

    # Fitted crossover red jacket above a dark waist cincher and separate hip lames.
    paint(ellipsoid((0, -.08, 12.75), (2.45, 1.68, 1.7), 2.3), "garnet", "pelvis")
    rib = ellipsoid((0, -.08, 17.75), (3.12, 1.96, 2.74), 2.25)
    waist = ellipsoid((0, -.1, 15.5), (2.29, 1.65, 1.85), 2.4)
    torso = rib | waist
    paint(torso, "crimson", "chest")
    cross = z - (17.65 + .91 * x)
    paint(torso & (np.abs(cross) < .53) & (y > .25), "garnet", "chest")
    paint(torso & (np.abs(cross - .44) < .19) & (y > .75), "gilt", "chest")
    paint(ellipsoid((0, .04, 20), (1.44, 1.26, 1.03)), "garnet", "chest")
    drop = np.clip(14.5 - z, 0, 4)
    radius = np.sqrt((x / (2.55 + .24 * drop))**2 + ((y + .12) / (1.8 + .16 * drop))**2)
    lames = (radius <= 1) & (radius > .53) & (z < 14.85) & (z > 11.7 + .48 * np.abs(y))
    lames &= (np.abs(x) > 1.5) | (y < -.4)
    paint(lames, "lame", "pelvis")
    paint(lames & (z >= 12.85 + .22 * np.abs(y)), "plate", "pelvis")
    paint(lames & (np.abs(z - (12.9 + .22 * np.abs(y))) < .24), "gilt", "pelvis")
    girdle = ellipsoid((0, -.1, 14.85), (2.85, 2.0, 1.12), 3.2)
    paint(girdle, "obi", "pelvis")
    paint(girdle & (np.abs(z - 15.4) < .24), "lame", "pelvis")
    paint(ellipsoid((-.65, 1.76, 14.85), (.72, .50, .53), 3.7), "gilt", "pelvis")

    # Flat, tapered woven lengths. A local width coordinate keeps the ivory selvage
    # and gold chevron attached to the blue face even where the ribbon curls.
    def streamer(points, widths, facing, lining):
        points = np.array(points, dtype=float)
        for i, (a, b) in enumerate(zip(points, points[1:])):
            axis = b - a
            tangent = unit(axis)
            across = unit(np.asarray(facing) - tangent * (tangent @ facing))
            normal = np.cross(tangent, across)
            along = np.clip(((xyz - a) @ axis) / (axis @ axis), 0, 1)
            local = xyz - a - along[..., None] * axis
            u, v = local @ across, local @ normal
            width = widths[i] + along * (widths[i + 1] - widths[i])
            sheet = (np.abs(u) < width) & (np.abs(v) < .42) & (np.abs(local @ tangent) < .42)
            paint(sheet, "blue silk", "pelvis")
            paint(sheet & (u < -(1 - lining) * width), "ivory", "pelvis")
            if i == len(widths) - 3:
                paint(sheet & (np.abs(along - .48 - .28 * np.abs(u) / width) < .13), "gilt", "pelvis")
    streamer([(1.15, 1.55, 14.55), (2.45, 3.20, 12.2), (4.85, 4.55, 10.2), (6.22, 4.3, 7.55), (6.65, 3.85, 5.24)],
             [.68, 1.42, 1.55, 1.12, .36], [1, -.33, 0], .75)
    streamer([(-1.5, -1.27, 14.4), (-2.65, -2.8, 12.55), (-4.15, -4.7, 11.85), (-6.25, -6.2, 9.65), (-7.2, -6.45, 7.2)],
             [.71, 1.14, 1.34, 1.04, .32], [1, -.45, 0], .32)
    paint(ellipsoid((1.18, 1.90, 14.75), (.94, .75, .88), 2.2), "blue silk", "pelvis")
    paint(ellipsoid((1.17, 2.52, 14.85), (.38, .33, .39)), "gilt", "pelvis")

    # Empty scabbard slants into depth behind the anatomical left hip.
    mouth, end = np.array([2.65, .9, 15.15]), np.array([6.25, -8.1, 9.6])
    case = capsule(mouth, end, .69, .54)
    paint(case, "sheath", "pelvis")
    t = ((xyz - mouth) @ (end - mouth)) / np.sum((end - mouth)**2)
    paint(case & ((t < .075) | (np.abs(t - .28) < .036) | (t > .94)), "gilt", "pelvis")
    paint(ellipsoid(mouth + [-.08, .23, .12], (.43, .48, .36)), "sheath", "pelvis")

    # Small shoulder pauldrons leave the upper arms bare. Gold borders trace
    # overlapping courses; the palette keeps the blue field larger than the edging.
    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (joints[f"{name}_{side}"] for name in ("shoulder", "elbow", "hand"))
        upper, fore = f"upper_{side}", f"fore_{side}"
        paint(capsule(shoulder, elbow, .98, .86), "skin", upper)
        plate_center = shoulder + [sign * .14, 0, .01]
        shoulder_plate = ellipsoid(plate_center, (1.72, 1.78, 1.43), 2.5)
        course = z - (plate_center[2] + .35 * sign * (shoulder[0] - x))
        paint(shoulder_plate, "lame", upper)
        paint(shoulder_plate & (course > -.53), "plate", upper)
        paint(shoulder_plate & (np.abs(course + .56) < .18), "gilt", upper)
        paint(shoulder_plate & (course > 1.02) & (np.abs(y - shoulder[1]) < .35), "gilt", upper)
        if side == "L":
            inlay = shoulder_plate & (course > .65) & (y > -.45) & (x < shoulder[0] + .6)
            paint(inlay, "ivory", upper)
        axis = hand - elbow
        f = ((xyz - elbow) @ axis) / (axis @ axis)
        bracer = capsule(elbow, hand - .20 * axis, .98, .82)
        paint(bracer, "lame", fore)
        paint(bracer & (f > .07) & (f < .72), "plate", fore)
        paint(bracer & ((np.abs(f - .13) < .07) | (np.abs(f - .67) < .055)), "gilt", fore)
        paint(ellipsoid(hand + [0, .02, .08], (.78, .75, .85), 2.3), "garnet", f"hand_{side}")
        paint(ellipsoid(hand + [0, .3, -.32], (.62, .6, .68), 2.15), "skin", f"hand_{side}")

    # Uncovered face, angular fringe and tapered cheek locks.
    paint(capsule((0, 0, 19.9), (0, .28, 22.45), .94), "skin", "head")
    skull = ellipsoid((0, .20, 24.15), (2.88, 2.78, 3.36), 2.2)
    jaw = ellipsoid((0, .62, 22.55), (2.26, 2.36, 1.86))
    paint(skull | jaw, "skin", "head")
    paint(ellipsoid((0, 2.65, 23.2), (.53, .46, .57)), "skin", "head")
    crown = ellipsoid((0, -.20, 25), (3.14, 3.07, 3.30), 2.1)
    hairline = 25.58 + .28 * x - .58 * np.clip(1 - np.abs(x + 2.2), 0, 1)
    paint(crown & ((y < .34) | (z > hairline)), "hair", "head")
    for sign in (-1, 1):
        lock = [(sign * 2.24, 1.13, 26.0), (sign * 2.68, 1.47, 24), (sign * 2.72, 1.78, 22.5), (sign * 2.39, 2.07, 20.35)]
        paint(tube(lock, .82, .30), "hair", "head")
        eye = ellipsoid((sign * 1.18, 2.78, 24.08), (.64, .63, .61), 2.5)
        brow = capsule((sign * .74, 2.74, 24.58), (sign * 1.81, 2.38, 24.94), .26)
        paint((eye | brow) & skull, "eyes", "head")
    paint(tube([(-.6, 1.2, 27.65), (-1.65, 2.21, 26.25), (-2.2, 2.16, 24.85)], .77, .31), "hair", "head")

    # Arc away from the head before falling. Two tapering locks open at the tip.
    tie = np.array([-.35, -2.25, 27.65])
    fall = [tie, (-1.15, -3.55, 28.65), (-2.7, -4.85, 28.15), (-4.55, -5.85, 27.3),
            (-6.05, -6.75, 24.20), (-7.85, -7.05, 20.85), (-9.5, -6.65, 20.15)]
    paint(tube(fall, 1.55, .47), "ponytail", "head")
    curl = [(-2.48, -4.58, 28.32), (-4.4, -5.25, 28.05), (-6.63, -5.84, 26.4),
            (-8.05, -5.9, 25.98), (-9.1, -5.65, 26.78)]
    paint(tube(curl, 1.05, .37), "ponytail", "head")
    ridge = [np.asarray(p) + [-.28, -.67, .53] for p in fall[1:-1]]
    paint(tube(ridge, .43, .28), "strand", "head")
    tie_axis = unit(np.asarray(fall[1]) - tie)
    clasp = xyz - (tie + .72 * tie_axis)
    along_tie = clasp @ tie_axis
    band = np.linalg.norm(clasp - along_tie[..., None] * tie_axis, axis=-1) <= 1.56
    paint(band & (np.abs(along_tie) <= .42), "gilt", "head")

    # ---- Sword: a slightly curved single-edged blade held low and out, its edge on
    # the convex side, a round tsuba and a leather-wrapped grip through the right fist.
    hand, tip = joints["hand_R"], joints["sword_tip"]
    down = unit(tip - hand)
    tsuba = hand + 1.35 * down
    length = np.linalg.norm(tip - tsuba)
    bow = unit(np.array([-1.0, 0, 0]) - down * (down @ [-1.0, 0, 0]))  # outward and up
    flat = np.cross(down, bow)
    sagitta = 1.05  # Exaggerate the shallow curve for the native projection.
    local = xyz - tsuba
    s = np.clip((local @ down) / length, 0, 1)
    offset = local - s[..., None] * length * down - (4 * sagitta * s * (1 - s))[..., None] * bow
    across, thick = offset @ bow, offset @ flat
    along = (local @ down) / length
    half_width = np.where(s < .88, .61 - .1 * s, .47 * np.clip((1 - s) / .12, 0, 1) + .05)
    blade = (along >= 0) & (along <= 1) & (np.abs(across) <= half_width) & (np.abs(thick) <= .59)
    paint(blade, "blade", "sword")
    paint(blade & (across >= .35 * half_width), "blade edge", "sword")
    disc = local @ down
    radial = np.linalg.norm(local - disc[..., None] * down, axis=-1)
    paint((np.abs(disc + .05) <= .3) & (radial <= 1.05), "gilt", "sword")
    pommel = hand - 2.3 * down
    paint(capsule(tsuba - .3 * down, pommel, .48, .44), "grip", "sword")
    paint(ellipsoid(pommel - .1 * down, (.5, .5, .5)), "gilt", "sword")

    paint(ellipsoid(hand + [-.04, 0, .1], (.80, .77, .9), 2.2), "garnet", "hand_R")
    paint(ellipsoid(hand + [.14, .48, 0], (.65, .47, .68), 2.3), "skin", "hand_R")
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
