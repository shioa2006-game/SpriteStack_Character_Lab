"""Build a single articulated skeleton, in anatomical-left / forward / up coordinates."""

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SHAPE = (68, 54, 80)  # Z, Y, X


def build(config):
    model, rig = config["model"], config["rig"]
    axes = [low + (np.arange(count) + .5) * step for low, count, step in
            zip(model["origin_xyz"][::-1], SHAPE, model["voxel_size_xyz"][::-1])]
    z, y, x = np.meshgrid(*axes, indexing="ij")
    xyz = np.stack((x, y, z), axis=-1)
    colors = {p["name"]: i for i, p in enumerate(model["palette"], 1)}
    parts = {name: i for i, name in enumerate(rig["parts"], 1)}
    joint = {name: np.array(point, float) for name, point in rig["rest"].items()}
    slices = np.zeros(SHAPE, dtype=np.uint8)
    owners = np.zeros_like(slices)

    def paint(mask, color, part):
        slices[mask] = colors[color]
        owners[mask] = parts[part]

    def oval(center, radii, power=2):
        return np.sum(np.abs((xyz - center) / radii) ** power, axis=-1) <= 1

    def shaft(a, b, ra, rb):
        a, b = np.asarray(a), np.asarray(b)
        axis = b - a
        t = np.clip((xyz - a) @ axis / (axis @ axis), 0, 1)
        off = xyz - a - t[..., None] * axis
        return (off * off).sum(axis=-1) <= (ra + t * (rb - ra)) ** 2

    for side, sign in (("R", -1), ("L", 1)):
        hip, knee, ankle = (joint[f"{n}_{side}"] for n in ("hip", "knee", "ankle"))
        thigh, shin, foot = (f"{n}_{side}" for n in ("thigh", "shin", "boot"))
        # Spherical ends meet at the knee; the narrow shaft leaves air on both sides.
        femur = shaft(hip, knee, .73, .58) & (z < 12.0)
        paint(femur | oval(knee + [0, 0, .46], (1.14, .91, .76)), "bone", thigh)
        tibia = shaft(knee, ankle, .71, .57)
        fibula = shaft(knee + [sign * .64, -.13, -.42], ankle + [sign * .42, -.2, .35], .45, .38)
        paint(tibia | fibula | oval(knee + [0, .3, -.15], (.87, .80, .76)), "bone", shin)
        wrap = shaft(knee, ankle, .92, .73) & (z < 4.4) & (z > 3.05)
        paint(wrap, "hide", shin)
        paint(wrap & (np.abs(z - 3.62 - .27 * (x-ankle[0]) * sign) < .21), "bronze", shin)
        heel = ankle + [0, -.23, -.67]
        paint(oval(heel, (.83, .96, 1.10)), "bone", foot)
        for digit in (-1, 0, 1):
            knuckle = ankle + [sign * (.18 + .49 * digit), 1.22, -.90]
            toe = ankle + [sign * (.65 + .82 * digit), 2.70 - .30 * abs(digit), -1.24]
            paint(shaft(heel, knuckle, .56, .46) | shaft(knuckle, toe, .48, .42), "bone", foot)

    # Sacrum and hip sockets bridge the femurs. Each concave wing has an actual hole.
    paint(oval((0, -.75, 12.65), (1.12, 1.20, 1.65)), "ilium", "pelvis")
    for sign in (-1, 1):
        outer = oval((sign * 1.73, -.10, 12.92), (1.96, 1.45, 1.75))
        window = ((x - sign * 1.83) / 1.04) ** 2 + ((z - 12.95 - .44*y) / .84) ** 2 < 1
        crest = shaft((sign * 1.6, -.4, 13.28), (sign * 3.17, -.42, 14.35), .86, .62)
        paint((outer & ~window) | crest, "ilium", "pelvis")
    # Leather sits low on the hips. Three separate red tails leave the femurs exposed.
    belt_radius = np.hypot(x / 3.23, (y + .12) / 1.74)
    belt = (belt_radius >= .72) & (belt_radius <= 1.12) & (np.abs(z - 11.77 + .07*x) < .55)
    paint(belt, "hide", "pelvis")
    buckle = (np.abs(x - .46) < .70) & (np.abs(z - 11.78) < .51) & (y >= 1.40) & (y <= 1.98)
    paint(buckle, "bronze", "pelvis")
    drop = np.clip((11.9 - z) / 6, 0, 1)
    for rear, offset, width, length in ((False, -.65, 1.32, 5.9), (True, .78, 1.72, 4.8),
                                        (False, 2.44, .83, 3.35)):
        center = offset + (-.50 if rear else -.84) * drop
        taper = width * (1 - .59 * drop)
        u = (x - center) / taper
        hem = 11.9 - length + 1.55 * np.abs(u + .23) + .60 * np.cos(5 * u)
        cloth_y = (-1 if rear else 1) * (1.78 + .85 * drop) - .12
        strip = (np.abs(u) < 1) & (z >= hem) & (z < 12.03) & (np.abs(y - cloth_y) < .51)
        paint(strip, "fold" if rear else "rag", "pelvis")
        paint(strip & (u > .44), "fold", "pelvis")

    # Exposed lumbar spine and neck. The processes read across the back of the cage.
    spine_y = -.85 + .12 * np.clip(z - 21, 0, 4)
    spine = (x/.63)**2 + ((y-spine_y)/.63)**2 <= 1
    paint(spine & (z > 13) & (z < 25.1), "spine", "chest")
    for level in np.arange(13.55, 24.9, 1.43):
        cy = -.85 + .12 * max(level - 21, 0)
        paint(oval((0, cy, level), (.90, .91, .56)), "bone", "chest")
        paint(oval((0, cy-.55, level+.17), (.53, .82, .44)), "spine", "chest")

    # Costal arches around an empty thorax. The lower arch is open at the sternum.
    for level, width, depth, open_front in ((16.58, 4.05, 1.92, True),
                                             (21.28, 4.54, 2.10, False)):
        u, v = x / width, (y + .22) / depth
        radius = np.hypot(u, v)
        mid = level + .44*y - (.94 if open_front else 2) * np.abs(u)**1.25
        tube = ((radius-1) * depth / .52)**2 + ((z-mid)/.46)**2 <= 1
        if open_front:
            tube &= (y < .65) | (np.abs(x) > 1.24)
        paint(tube, "rib", "chest")
        paint(shaft((0,-.85,level-.70), (0,-depth-.15,level-.96), .57,.50), "spine", "chest")
    paint(shaft((0, 1.66, 19.4), (0, 1.64, 22.32), .49, .67), "rib", "chest")
    for sign in (-1, 1):
        paint(shaft((0, .90, 22.3), (sign*4.48, .12, 21.84), .62,.73), "bone", "chest")
        paint(shaft((sign*.42, -.91, 21.78), (sign*4.1, -.32, 21.69), .63,.69), "spine", "chest")
    # Keep the sling across the upper ribs so the large lower openings remain visible.
    for depth in (1.51, -1.46):
        paint(shaft((-3.65, depth*.42, 22.28), (1.62, depth, 19.32), .52,.48), "hide", "chest")
    paint(oval((-.90, 1.43, 20.13), (.61,.49,.54)), "bronze", "chest")

    # Recess the orbital bowls in the dome, then add the brow, cheekbones and teeth.
    hx, hy, hz = joint["head"]
    dome = oval((hx, hy, hz), (4.03, 2.99, 3.42))
    socket = ((np.abs(x)-1.87)/1.38)**2 + ((y-2.96)/1.78)**2 + ((z-28.32)/1.48)**2
    paint(dome & (socket >= .68), "bone", "head")
    paint(dome & (socket >= .68) & (socket <= 1.64) & (y > 1.05), "socket", "head")
    for sign in (-1, 1):
        paint(oval((sign*1.87,1.90,28.19), (.60,.57,.59)), "eyes", "head")
        paint(shaft((sign*3.30,1.50,26.76), (sign*1.92,2.75,26.38), .65,.49), "bone", "head")
        paint(shaft((sign*2.53,.55,26.25), (sign*1.84,1.77,24.34), .55,.51), "bone", "head")
    muzzle = oval((0, 2.12, 26.17), (2.10,1.15,1.10))
    paint(muzzle, "bone", "head")
    paint(shaft((0, 2.90, 28.80), (0, 3.20, 27.00), .56, .49), "bone", "head")
    nose = (np.abs(x) < .65 + .21*np.clip(27.35-z,0,1.4)) & (z>=25.94) & (z<=27.47) & (y>2.43)
    paint(nose & (owners == parts["head"]), "socket", "head")
    paint(oval((0, 1.68, 24.44), (2.05, 1.14, .76)), "bone", "head")
    paint(oval((0, 2.21, 25.19), (1.91,.82,.55), 3), "socket", "head")
    for tooth in (-1.50,-.50,.50,1.50):
        low = .25 if abs(tooth) > 1 else 0
        paint(oval((tooth, 3.02-.15*abs(tooth),25.46-low), (.40,.44,.58), 3), "teeth", "head")

    for side, sign in (("R",-1),("L",1)):
        shoulder, elbow, hand = [joint[f"{p}_{side}"] for p in ("shoulder","elbow","hand")]
        upper, fore, fist = (f"{p}_{side}" for p in ("upper","fore","hand"))
        humerus = shaft(shoulder, elbow, .78,.60) | oval(shoulder, (.98,.96,1.04))
        paint(humerus, "bone", upper)
        radius = shaft(elbow, hand, .59,.51)
        ulna = shaft(elbow+[sign*.67,-.28,.15], hand+[sign*.35,-.19,.15], .47,.40)
        paint(radius | ulna | oval(elbow, (.81,.69,.70)), "bone", fore)
        cuff = shaft(elbow, hand, .86,.76) & (z < hand[2]+1.85) & (z > hand[2]+.73)
        paint(cuff,"hide",fore)
        if side == "R":
            shell = oval(shoulder + [-.29,0,.03], (2.0,1.74,1.68))
            bottom = shoulder[2]-.49+.24*(x-shoulder[0])
            paint(shell & (z >= bottom-.36), "bronze", upper)
            paint(shell & (z > bottom), "iron", upper)
            corrosion = np.sin(1.62*x+.75*y) + np.sin(1.7*z-.48*y) > .29
            paint(shell & (z > bottom) & corrosion, "oxide", upper)
            paint(oval(shoulder + [-1.39,1.05,.11], (.45,.42,.44)), "bronze", upper)
        paint(oval(hand,(.90,.91,1.00),2.5),"bone",fist)

    # One broad, straight, weathered blade with a bevel and a short recurved crossguard.
    hand = joint["hand_R"]
    axis = joint["sword_tip"] - hand
    length = np.linalg.norm(axis)
    axis /= length
    across = np.cross(axis,[0,1,0])
    across /= np.linalg.norm(across)
    normal = np.cross(axis,across)
    local = xyz-hand
    along, u, v = local@axis, local@across, local@normal
    width = np.interp(along,[2.36,3.3,length-2.45,length],[1.02,1.0,.86,.48])
    collar = (along>=1.37) & (along<2.36) & (np.abs(u)<=.66) & (np.abs(v)<=.58)
    paint(collar, "iron", "sword")
    blade = (along>=2.36) & (along<=length) & (np.abs(u)<=width) & (np.abs(v)<=.70)
    paint(blade,"blade","sword")
    paint(blade & (np.sin(along*1.25 + u*2.12) > .29), "blade rust", "sword")
    paint(blade & (u < -.37*width), "edge", "sword")
    guard = hand + 1.45*axis
    paint(shaft(guard-1.53*across+.21*axis, guard, .35,.45) |
          shaft(guard, guard+1.53*across+.21*axis, .45,.35), "bronze", "sword")
    paint(shaft(hand-1.78*axis, guard, .51,.48), "hide","sword")
    paint(oval(hand-1.78*axis, (.70,.67,.64)), "bronze","sword")
    paint(oval(hand,(.87,.93,1.0),2.4), "bone","hand_R")

    # Dish the circular face and keep rim, boss, device and rear handgrip on one wrist.
    normal = np.array([.48,.88,0])
    normal /= np.linalg.norm(normal)
    tangent = np.array([normal[1],-normal[0],0])
    center = joint["shield_center"]
    local = xyz-center
    u, v, depth = local@tangent, local[...,2], local@normal
    r = np.hypot(u,v)
    front = .6-.040*r*r
    disk = (r<=4.93) & (depth >= front-1.10) & (depth<=front)
    paint(shaft(joint["hand_L"],center-.30*normal,.59,.70),"hide","shield")
    paint(disk,"hide","shield")
    face = disk & (depth>=front-.61)
    paint(face,"blue","shield")
    paint(disk & (r>4.26),"iron","shield")
    rivets = np.cos(8*np.arctan2(v,u)) > .74
    paint(face & (r>4.28) & rivets,"bronze","shield")
    motif = ((np.abs(u)<.40) & (v>1) & (v<3.46)) | ((np.abs(np.abs(u)-.75*(2.45-v))<.34) & (v>1.15) & (v<2.55))
    paint(face & motif,"device","shield")
    boss = (r/1.31)**2 + ((depth-.55)/.84)**2 <= 1
    paint(boss,"bronze","shield")
    paint(boss & (r<1.02) & (depth>.78),"iron","shield")
    return slices, owners


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    model, parts = build(json.loads((HERE / "character.json").read_bytes()))
    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out / "materials.npz", slices=model)
    np.savez_compressed(args.out / "part_ids.npz", parts=parts)


if __name__ == "__main__":
    main()
