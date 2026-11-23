"""Sculpt GOBLIN BRUTE in rest space. +X is the goblin's left, +Y its front."""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SHAPE = (58, 51, 80)  # Z, Y, X


def primitives(xyz):
    def oval(center, radii, power=2):
        return (np.abs((xyz - center) / radii) ** power).sum(axis=-1) <= 1

    def limb(start, end, thick, thin):
        start, end = np.asarray(start), np.asarray(end)
        axis = end - start
        t = np.clip(((xyz - start) @ axis) / (axis @ axis), 0, 1)
        offset = xyz - start - t[..., None] * axis
        return (offset ** 2).sum(axis=-1) <= (thick + (thin - thick) * t) ** 2

    return oval, limb


def sculpt_head(xyz, paint):
    x, y, z = np.moveaxis(xyz, -1, 0)
    oval, limb = primitives(xyz)
    # Bald dome, broad lower jaw and forward-set nose. Eyes slope down towards the nose.
    dome = oval((0, 0, 0), (4.72, 3.52, 4.48))
    paint(dome, "skin", "head")
    scar = (y > .95) & (z > 1.65) & (z < 4.1) & (np.abs(x+.95-.45*(z-2.55)) < .29)
    paint(dome & scar, "snout", "head")
    paint(oval((0, 1.53, -2.0), (3.73, 2.83, 2.63), 2.22), "skin", "head")
    paint(oval((0, 3.25, -2.60), (2.92, 1.69, 1.25)), "skin", "head")
    paint(oval((0, 3.87, -2.05), (2.76, 1.19, .44)), "socket", "head")
    paint(oval((0, 3.73, -1.63), (2.64, 1.42, .77)), "skin", "head")
    for sign in (-1, 1):
        # Swept triangular ear. The inset stops below the rolled upper edge.
        distance = sign*x
        t = np.clip((distance-3.36)/9.24, 0, 1)
        mid_z = -.30 + 4.90*t
        high = mid_z + 2.12*(1-t)
        low = mid_z - 2.12*(1-t)**1.32
        mid_y = -.73 - 3.35*t
        half = 1.19*(1-t)**.69 + .19
        ear = (distance>=3.36) & (distance<=12.6) & (z>=low) & (z<=high) & (np.abs(y-mid_y)<=half)
        paint(ear, "skin", "head")
        cup = ear & (y > mid_y+.08) & (z > low+.65) & (z < high-.62) & (distance>4.25)
        paint(cup, "ear lining", "head")
        cheek = (sign*2.8,2.53,-1.47)
        paint(oval(cheek, (1.30,1.34,.89)), "skin", "head")
        socket = oval((sign*2.14, 3.13, .02), (1.65,1.30,1.20))
        paint(socket, "socket", "head")
        eye = oval((sign*2.16, 3.99, .08), (1.08,.70,.68))
        paint(eye, "eyes", "head")
        brow = limb((sign*.88,3.78,.46), (sign*3.52,2.75,1.51), .74,.83)
        paint(brow, "brow ridge", "head")
        tusk = limb((sign*2.37,4.11,-2.67), (sign*2.81,4.81,-.79), .66,.26)
        paint(tusk, "tusk", "head")
    paint(limb((0,3.10,.77),(0,4.37,-.61), .86,.99), "skin", "head")
    paint(oval((0,4.57,-.71), (1.35,1.22,.83)), "snout", "head")


def build(config):
    model, rig = config["model"], config["rig"]
    axes = [low + (np.arange(n) + .5) * step for low, n, step in
            zip(model["origin_xyz"][::-1], SHAPE, model["voxel_size_xyz"][::-1])]
    z, y, x = np.meshgrid(*axes, indexing="ij")
    xyz = np.stack((x, y, z), axis=-1)
    colors = {p["name"]: i for i, p in enumerate(model["palette"], 1)}
    parts = {part: i for i, part in enumerate(rig["parts"], 1)}
    joints = {name: np.array(point, float) for name, point in rig["rest"].items()}
    slices = np.zeros(SHAPE, dtype=np.uint8)
    owners = np.zeros_like(slices)

    def paint(mask, color, part):
        slices[mask] = colors[color]
        owners[mask] = parts[part]

    oval, limb = primitives(xyz)

    for side, sign in (("R", -1), ("L", 1)):
        hip, knee, ankle = [joints[f"{joint}_{side}"] for joint in ("hip", "knee", "ankle")]
        thigh = limb(hip, knee, 1.70, 1.19) & (z >= knee[2])
        haunch = oval(.48*hip + .52*knee + [sign*.33, .48, 0], (1.45, 1.52, 1.82))
        paint(thigh | haunch, "skin", "thigh_" + side)
        shin = limb(knee, ankle, 1.10, .95) & (z < knee[2] + .35)
        paint(shin, "skin", "shin_" + side)
        wrap = shin & (z < 4.7) & (z > 1.8)
        paint(wrap, "leather", "shin_" + side)
        paint(wrap & (np.mod(z + sign * x * .28, 1.65) < .52), "rawhide", "shin_" + side)
        # Bare, splayed toes and a broad heel share a rigid sole.
        heel = ankle + [0, .2, -.55]
        foot = oval(heel, (1.36, 1.65, 1.25))
        ball = heel + [sign * .56, 1.85, -.28]
        foot |= oval(ball, (1.78, 2.07, .89))
        for digit, reach in ((-1, 1.7), (0, 2.0), (1, 1.4)):
            toe = ball + [sign * (.25 + digit * 1.18), reach + .3, -.20]
            foot |= oval(toe, (.62, 1.12, .65))
        paint(foot, "skin", "boot_" + side)
        paint(foot & (z < .51), "sole", "boot_" + side)

    paint(oval((0, -.5, 9.5), (2.38, 1.84, 1.77)), "skin", "pelvis")
    # The shoulder girdle leans over a pinched waist. The back rises into the neck.
    belly = oval((0, -.05, 11.8), (2.32, 1.85, 3.7))
    ribs = (x / 3.75) ** 2 + ((y - .36 - .14 * (z-14.3)) / 2.15) ** 2 + ((z-14.3)/3.2) ** 2 <= 1
    back = limb((0, -.8, 14.4), (0, 1.5, 18.4), 2.08, 1.9)
    torso = (belly & (z > 10.22)) | ribs | back
    paint(torso, "skin", "chest")
    strap = torso & (np.abs(x + .89 * (z - 13.65)) < .72)
    paint(strap, "leather", "chest")
    paint(strap & (np.abs(z-13.5) < .45) & (y > 1.3), "stud", "chest")

    # Unequal wedges form one wrap around the hips. The longest tongue hangs in front.
    drop = np.clip((10.3 - z) / 5.8, 0, 1)
    rx, ry = 2.92 + 1.9 * drop, 2.08 + 1.52 * drop
    angle = np.arctan2(x / rx, (y + .4) / ry)
    radius = np.hypot(x / rx, (y + .4) / ry)
    hem = np.interp(angle, [-3.15,-2.5,-2.05,-1.6,-1.15,-.8,-.47,-.07,.32,.63,1,1.55,2,2.5,3.15],
                    [6.5,8.5,6.0,8.45,5.65,8.05,6.8,4.05,7.85,5.65,8.35,6.75,8.5,5.7,6.5])
    cloth = (z >= hem) & (z <= 10.55) & (radius < 1.18) & (radius > .72)
    paint(cloth, "rag", "pelvis")
    paint(cloth & (np.cos(7 * angle + drop * 1.2) > .68), "rag fold", "pelvis")
    belt = (np.hypot(x / 3.14, (y+.4) / 2.36) < 1.12) & (np.abs(z-10.35+.10*x) < .69)
    paint(belt, "leather", "pelvis")
    buckle = (np.abs(x+.25) < 1.0) & (np.abs(z-10.4) < .65) & (y > 1.87) & (y < 2.61)
    paint(buckle, "stud", "pelvis")
    paint(buckle & (np.abs(x+.25) < .5) & (np.abs(z-10.4) < .3), "leather", "pelvis")

    for side, sign in (("R", -1), ("L", 1)):
        shoulder, elbow, palm = [joints[f"{joint}_{side}"] for joint in ("shoulder", "elbow", "hand")]
        upper, fore = "upper_" + side, "fore_" + side
        paint(limb(shoulder, elbow, 1.58, 1.12), "skin", upper)
        arm = limb(elbow, palm, 1.27, .95)
        paint(arm, "skin", fore)
        band = arm & (z < elbow[2] - .42) & (z > palm[2] + .54)
        paint(band, "leather", fore)
        paint(band & (np.mod(z + .24 * y, 1.65) < .5), "rawhide", fore)
        if side == "R":
            plate = oval(shoulder + [-.48, -.15, .06], (2.58, 2.11, 2.12), 2.35)
            lip = shoulder[2] - .25 + .32 * (x - shoulder[0])
            paint(plate & (z >= lip - .57), "rawhide", upper)
            paint(plate & (z > lip), "iron", upper)
            for dy in (-1.48, 1.48):
                paint(oval(shoulder + [-1.68, dy, .40], (.57,.56,.54)), "stud", upper)
        else:
            paint(oval(palm, (1.45, 1.10, 1.65)), "skin", "hand_L")
            for i in range(3):
                base = palm + [sign * (i-.7)*.90, .35, -.70]
                end = base + [sign*(i-.65)*.36, .58, -1.8 + abs(i-1)*.5]
                paint(limb(base, end, .54, .34), "skin", "hand_L")
            paint(limb(palm + [-.95,.45,.42], palm + [-1.65,1.1,-.64], .68,.4), "skin", "hand_L")

    sculpt_head(xyz - joints["head"], paint)

    # Octagonal log with longitudinal bark, exposed end grain and two iron hoops.
    hand = joints["hand_R"]
    shaft = joints["club_end"] - hand
    length = np.linalg.norm(shaft)
    axis = shaft / length
    across = np.cross(axis, [0, 0, 1])
    across /= np.linalg.norm(across)
    normal = np.cross(axis, across)
    delta = xyz - hand
    along, u, v = delta @ axis, delta @ across, delta @ normal
    theta = np.arctan2(v, u)
    facet = np.cos(np.mod(theta + np.pi/8, np.pi/4) - np.pi/8)
    radial = np.hypot(u, v) * facet
    radius = np.interp(along, [-2.3,-1.9,2.15,3.1,5.3,8.2,length-.7,length],
                       [.66,.88,.77,1.19,1.98,2.64,2.73,2.37])
    log = (along >= -2.3) & (along <= length) & (radial <= radius)
    paint(log, "heartwood", "club")
    bark = log & (np.sin(4*theta + .16*along) > .02) & (along < length-.58)
    paint(bark, "bark", "club")
    paint(log & (along < 2.8), "grip", "club")
    paint(log & ((np.abs(along-5.45) < .49) | (np.abs(along-(length-1.35)) < .75)), "hoop", "club")
    # Paint the closing hand last: wood emerges on opposite sides of the knuckles.
    paint(oval(hand, (1.46,1.42,1.48), 2.6), "skin", "hand_R")
    paint(limb(hand + [1.0,.24,.62], hand + [.44,1.23,-.27], .61,.46), "skin", "hand_R")
    return slices, owners


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((HERE / "character.json").read_text(encoding="utf-8"))
    materials, parts = build(config)
    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out / "materials.npz", slices=materials)
    np.savez_compressed(args.out / "part_ids.npz", parts=parts)


if __name__ == "__main__":
    main()
