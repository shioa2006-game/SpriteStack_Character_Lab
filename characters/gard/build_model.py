"""Gard's plate harness, raised warhammer and convex griffin shield."""

import numpy as np

from characters.voxel_shapes import Volume, model_cli


def build(config):
    v = Volume(config)
    x, y, z = v.x, v.y, v.z
    oval, rod, paint, j = v.oval, v.rod, v.paint, v.joints
    for side in ("R", "L"):
        thigh, shin = "thigh_" + side, "shin_" + side
        v.limb(side, "hip", "knee", 1.95, 1.44, "mail", "thigh")
        v.limb(side, "knee", "ankle", 1.55, 1.19, "plate", "shin")
        k = j["knee_" + side]
        paint(oval(k + [0, .75, -.24], (1.58, 1.48, 1.24), 1.65), "bright steel", shin)
        paint(rod(k + [0, 1.0, -1.2], j["ankle_" + side] + [0, 1.0, .3], .68, .47), "bright steel", shin)
        h = j["hip_" + side]
        paint(rod(h + [0, .75, .2], k + [0, .85, 1.6], 1.62, 1.3), "plate", thigh)
        v.shoe(side, 1.65, 2.37, "plate", "mail")

    paint(oval((0, 0, 13.4), (4.6, 2.9, 2.8)), "mail", "pelvis")
    tabard_hem = 8.1 + .24*np.abs(x)
    tabard = (oval((0, 1.65, 12), (3.8, 1.65, 4.1), 3) & (z > tabard_hem)
              & ((np.abs(x) > .43) | (z > 10.7)))
    paint(tabard, "crimson", "pelvis")
    paint(tabard & (z < tabard_hem+.55) & (y > 1.2), "gold", "pelvis")
    for level, w in [(11.1, 4.9), (12.8, 5.0), (14.3, 4.8)]:
        plates = oval((0, 0, level), (w, 3.0, 1.45), 2.6) & (np.abs(x) > 2.5)
        for side, sign in (("R", -1), ("L", 1)):
            panel = plates & (sign*x > 0)
            # The lowest articulated lame rides on the cuisse when the knee rises.
            owner = "thigh_"+side if level == 11.1 else "pelvis"
            paint(panel, "plate", owner)
            paint(panel & (z < level - .6), "bright steel", owner)
    torso = oval((0, 0, 19.15), (5.95, 3.55, 5.9), 2.35) & (z > 14.8)
    paint(torso, "plate", "chest")
    paint(torso & (y > 1) & (np.abs(z - 18 - .35*np.abs(x)) < .60), "bright steel", "chest")
    paint(torso & (np.abs(x) + .76*np.abs(z - 21.1) < 1.4) & (y > 2), "gold", "chest")
    belt = oval((0, .04, 15.15), (4.95, 3.38, 1.02), 3.2)
    paint(belt, "leather", "pelvis")
    paint(oval((0, 3.16, 15.15), (1.08, .52, .81), 5), "gold", "pelvis")
    v.cloak(24.5, 6.45, 5.45, 7.5, -2.65, "crimson", "wine")
    for side, s in (("R", -1), ("L", 1)):
        shoulder, elbow, hand = (j[n+"_"+side] for n in ("shoulder", "elbow", "hand"))
        paint(rod(shoulder, elbow+.10*(shoulder-elbow), 1.85, 1.39), "mail", "upper_"+side)
        for dz, width, metal in [(-1.45, 2.32, "mail"), (-.83, 2.56, "bright steel"), (.05, 2.78, "plate")]:
            paint(oval(shoulder+[s*.25, 0, dz], (width, 2.4, 1.6)), metal, "upper_"+side)
        v.limb(side, "elbow", "hand", 1.34, 1.05, "plate", "fore")
        paint(oval(elbow, (1.60, 1.60, 1.15)), "bright steel", "fore_"+side)
        paint(oval(hand, (1.21, 1.14, 1.22), 2.8), "mail", "hand_"+side)
        # The two cape fastenings meet at the brooch on his right collarbone.
        paint(rod((s*5.4, -.95, 23.65), (-2.4, 2.45, 22.6), 1.18), "crimson", "chest")
    paint(oval((-2.6, 2.72, 22.75), (1.12, .61, 1.12)), "gold", "chest")
    # A mass of white hair under an open nasal helm, with overlapping beard locks.
    paint(oval((0, -.7, 26.5), (3.83, 3.0, 3.4)), "silver hair", "head")
    paint(oval((0, .43, 27.6), (3.30, 3.02, 3.48), 2.35), "skin", "head")
    for s in (-1, 1):
        paint(rod((s*2.83, .66, 27.5), (s*3.14, 1.35, 24.6), .99, .50), "silver hair", "head")
    v.eyes((1.38, 3.1, 28.30), (1.20, 2.98, 28.30), (.61, .50, .52))
    for s in (-1, 1):
        paint(rod((s*.82, 3.16, 28.83), (s*2.18, 2.70, 29.20), .46), "silver hair", "head")
    paint(oval((0, 2.18, 25.45), (3.58, 2.32, 2.42)), "silver hair", "head")
    for dx in (-2.5, -1.15, .10, 1.42, 2.54):
        paint(rod((dx, 3.42, 25.35), (dx*1.12, 3.65, 21.75+.56*abs(dx)), .97, .36),
              "beard light" if abs(dx) < 1.5 else "silver hair", "head")
    # Swept white moustache in front of the darker beard, just below the nose.
    for s in (-1, 1):
        paint(rod((s*.35, 4.26, 26.36), (s*2.64, 3.48, 25.63), .73, .48),
              "beard light", "head")
    paint(oval((0, 3.55, 27.28), (.88, .81, .77)), "skin", "head")
    helm = oval((0, -.28, 29.47), (4.0, 3.58, 3.63), 2.0)
    brow = 28.6 + .32*y - .13*np.abs(x)
    paint(helm & (z >= brow), "plate", "head")
    paint(helm & (z >= brow) & (z <= brow + .76), "bright steel", "head")
    paint(helm & (y > .1) & (z > 30.1) & (z < 31.95) & (np.cos((x+.12*z)*3.65) > .08), "mail", "head")
    paint(oval((0, -.30, 31.53), (.66, 2.72, 2.02), 1.75), "bright steel", "head")

    grip, head = j["hand_R"], j["hammer_head"]
    axis = head - grip
    paint(rod(grip-.22*axis, head, .81, .91), "leather", "hammer")
    for t in (-.20, .39, .73):
        p = grip+t*axis
        paint(rod(p-.03*axis, p+.03*axis, 1.03), "gold", "hammer")
    delta = v.xyz - head
    # The striking faces flare out from the gilt central socket.
    u = delta @ np.array([.91, -.36, -.20])
    w = delta @ np.array([.37, .93, 0])
    h = delta @ np.array([.186, -.074, .98])
    spread = 1.73 + .15*np.abs(u)
    block = (np.abs(u) <= 4.28) & ((np.abs(w)/spread)**4 + (np.abs(h)/(spread+.25))**4 <= 1)
    paint(block, "hammer iron", "hammer")
    paint(block & (np.abs(u) > 3.15), "bright steel", "hammer")
    paint(block & (np.abs(u) < .66), "gold", "hammer")

    normal = np.array([.55, .835, 0])
    tangent = np.array([.835, -.55, 0])
    delta = v.xyz - j["shield_center"]
    u, h, d = delta @ tangent, delta[..., 2], delta @ normal
    width = np.interp(h, [-10, -7, -2, 6.5, 9.6], [.3, 2.8, 5.2, 5.6, .25])
    face = .85 - .045*u**2
    body = (np.abs(u) <= width) & (h >= -10) & (h <= 9.6) & (d < face) & (d > face-1.75)
    paint(rod(j["hand_L"], j["shield_center"], .88), "leather", "shield")
    paint(body, "leather", "shield")
    front = body & (d > face-.95)
    paint(front, "bronze", "shield")
    paint(body & (np.abs(u) > width-.80), "gold", "shield")
    wing = (np.abs(u) < 3.8) & (np.abs(u) > .48) & (h > .55*np.abs(u)-1.3) & (h < 1.30*np.abs(u)+1.35)
    feathers = (np.abs(u) < 2.35) | (np.cos(3.8*h-3.4*np.abs(u)) > -.36)
    bird = (np.abs(u-.25) + .31*np.abs(h-.3) < 1) | ((u > -.2) & (u < 1.77) & (np.abs(h-2.2) < .59))
    tail = (np.abs(u+.3*np.sin(h)) < .76) & (h > -4.8) & (h < 0)
    paint(front & ((wing & feathers) | bird | tail), "gold", "shield")
    for side in ("L", "R"):
        paint(oval(j["hand_"+side], (1.20, 1.16, 1.14), 2.7), "mail", "hand_"+side)
    return v.material, v.part


if __name__ == "__main__":
    model_cli(build, __file__)
