"""Tobi's rolled sleeves, brass goggles and quarry belt, in anatomical XYZ."""
import numpy as np

from characters.voxel_shapes import Volume, model_cli


def build(config):
    v = Volume(config)
    oval, rod, paint, j = v.oval, v.rod, v.paint, v.joints
    x, y, z = v.x, v.y, v.z

    for side in ("R", "L"):
        ankle = j["ankle_" + side]
        shin = "shin_" + side
        v.limb(side, "hip", "knee", 1.85, 1.35, "trousers", "thigh")
        v.limb(side, "knee", "ankle", 1.46, 1.04, "trousers", "shin")
        paint(rod(ankle, ankle + [0, .12, 4.05], 1.25, 1.48), "oiled hide", shin)
        cuff = oval(ankle + [0, .14, 3.96], (1.6, 1.46, .79), 3)
        paint(cuff, "saddle", shin)
        paint(oval(ankle + [.72, 1.26, 3.98], (.54, .40, .52)), "brass", shin)
        v.shoe(side, 1.49, 2.17, "oiled hide", "trousers")

    paint(oval((0, 0, 13.35), (3.48, 2.25, 2.7)), "trousers", "pelvis")
    torso = oval((0, -.02, 18.2), (4.10, 2.68, 5.48), 2.35) & (z >= 13.5)
    paint(torso, "linen", "chest")
    # Open leather jerkin, broad shoulder straps and a diagonal tool sling.
    open_front = (y > 0) & (np.abs(x) < .95 + .27*np.maximum(z-18, 0))
    paint(torso & ~open_front, "saddle", "chest")
    strap = torso & (np.abs(x - .77*(z-18.65)) < .64) & (y > .1)
    paint(strap, "oiled hide", "chest")
    paint(strap & (np.abs(z-19.75) < .52), "brass", "chest")
    paint(rod((-2.4, 1.54, 16.63), (2.21, 2.05, 21.10), .60), "oiled hide", "chest")
    paint(oval((1.09, 2.53, 20.17), (.77, .48, .75), 3), "brass", "chest")
    paint(torso & (y < -.8) & (np.abs(x+.66*(z-18.2)) < .72), "oiled hide", "chest")
    paint(oval((0, .12, 22.65), (1.65, 1.55, 2.02)), "skin", "chest")
    for sign in (-1, 1):
        paint(rod((sign*1.48, .57, 22.93), (sign*.70, 2.12, 21.19), .68, .34), "linen", "chest")
    sash = oval((0, 0, 14.15), (3.7, 2.62, 1.4), 3)
    paint(sash, "amethyst", "pelvis")
    # The sash end and its woven border share a fixed knot on the left hip.
    flap = rod((2.30, 2.26, 14.5), (3.02, 2.47, 8.46), 1.48, 1.22) & (y > 1.37)
    paint(flap, "amethyst", "pelvis")
    paint(flap & (np.abs(z-9.43-.32*x) < .35), "lilac", "pelvis")
    belt = oval((0, .02, 14.9), (3.86, 2.76, .73), 3.2)
    paint(belt, "oiled hide", "pelvis")
    paint(oval((.6, 2.66, 14.92), (.91, .47, .7), 4), "brass", "pelvis")
    # Three iron spheres on a curved leather band. The open pouch sits just behind them.
    for cx, cy, cz in [(-3.76, 1.75, 12.53), (-2.26, 3.35, 13.22), (-.10, 3.43, 13.90)]:
        paint(rod((cx*.88, cy*.81, 14.61), (cx, cy, cz+.67), .48), "brass", "pelvis")
        paint(oval((cx, cy+.20, cz-.26), (1.16, 1.13, 1.27)), "black iron", "pelvis")
    pouch = oval((-3.25, -.93, 13.02), (1.76, 1.75, 2.04), 3.1)
    paint(pouch, "saddle", "pelvis")
    paint(pouch & (z > 14.14), "oiled hide", "pelvis")
    # A coiled rope and a stone chisel hang on opposite sides of the small of the back.
    for level in (12.0, 12.7):
        angle = np.linspace(0, 2*np.pi, 21)
        loop = list(zip(1.70+1.51*np.cos(angle), -2.0+.29*np.sin(angle),
                        level+2.24*np.sin(angle)))
        v.path(loop, .44, "hemp", "pelvis")
    paint(rod((-1.3, -2.07, 11.9), (-2.84, -2.24, 16.9), .58, .52), "oiled hide", "pelvis")
    paint(rod((-2.84, -2.24, 16.9), (-3.26, -2.34, 18.18), .59, .5), "tool steel", "pelvis")
    paint(rod((-3.32, -2.36, 18.21), (-2.67, -2.21, 17.99), .63), "tool steel", "pelvis")

    for side in ("R", "L"):
        sh, el, hand = (j[f"{joint}_{side}"] for joint in ("shoulder", "elbow", "hand"))
        upper, fore = "upper_"+side, "fore_"+side
        sleeve = rod(sh, el, 1.77, 1.26)
        paint(sleeve, "linen", upper)
        paint(rod(sh+.67*(el-sh), sh+.85*(el-sh), 1.65), "rolled linen", upper)
        paint(rod(el, hand, 1.19, .90), "skin", fore)
        paint(rod(el+.59*(hand-el), hand, 1.16, 1.02), "oiled hide", fore)
        paint(oval(hand, (1.18, 1.13, 1.18), 2.6), "saddle", "hand_"+side)

    paint(oval((0, .15, 25.23), (3.14, 2.75, 3.34), 2.28), "skin", "head")
    hair = oval((0, -.27, 26.34), (3.50, 3.03, 3.91))
    fringe = 26.42+.17*x+.24*np.cos(x*1.75)
    paint(hair & ((y < .54) | (z > fringe)), "chestnut", "head")
    for sign in (-1, 1):
        paint(rod((sign*2.85, .2, 26.45), (sign*3.22, 1.09, 24.40), .85, .44), "chestnut", "head")
    # Locks taper in different directions along the crown.
    for base, tip in [((-2.3, -.75, 28.0), (-3.65, -1.0, 29.71)),
                      ((-1.2, -.4, 28.9), (-2.38, -.85, 30.89)),
                      ((.55, -.7, 29.25), (1.87, -1.67, 31.35)),
                      ((2.08, -.49, 28.46), (3.70, -1.45, 30.13)),
                      ((1.2, -2.05, 27.71), (2.53, -3.72, 28.69))]:
        paint(rod(base, tip, 1.16, .37), "chestnut", "head")
    band = oval((0, -.13, 27.35), (3.67, 3.24, 2.02), 2.6)
    stripe = z-(27.13+.12*x+.18*y)
    paint(band & (np.abs(stripe) < 1.15), "amethyst", "head")
    paint(oval((2.60, -2.49, 27.0), (1.20, 1.06, .96)), "lilac", "head")
    v.path([(2.54,-2.36,27.0), (3.62,-3.48,26.3), (4.50,-4.28,24.11),
            (5.62,-4.89,23.64)], .78, "amethyst", "head")
    v.path([(2.77,-2.52,27.1), (3.54,-4.12,27.17), (4.64,-5.45,26.16)],
           .66, "lilac", "head")
    for sign, iris in ((-1, "right eye"), (1, "left eye")):
        paint(oval((sign*1, 2.59, 25.45), (.89, .67, .98), 2.5), "skin", "head")
        paint(oval((sign, 3.10, 25.42), (.42, .69, .78), 2.6), "skin", "head")
        iris_patch = oval((sign, 3.15, 25.15), (.34, .37, .84), 2.6)
        paint(iris_patch & (v.material == v.colors["skin"]), iris, "head")
        paint(oval((sign*1.49, 2.35, 28.19+.15*sign), (1.32, 1.07, 1.26), 2.4), "brass", "head")
        paint(oval((sign*1.56, 3.11, 28.52+.15*sign), (.84, .68, .75)), "aqua glass", "head")
    paint(rod((-.50, 2.85, 28.18), (.50, 2.85, 28.26), .43), "brass", "head")
    paint(oval((0, 2.91, 24.65), (.53, .62, .61)), "skin", "head")

    center = j["bomb_center"]
    paint(oval(center, (2.13, 2.08, 2.16)), "black iron", "bomb")
    paint(rod(center+[0,0,1.72], center+[.12,0,2.22], .78), "brass", "bomb")
    v.path([center+[.12,0,2.08], center+[.34,.12,2.93], center+[1.30,.12,3.55]],
           .43, "hemp", "bomb")
    paint(oval(center+[1.33,.12,3.58], (.55,.53,.55)), "ember", "bomb")
    # Keep a visible palm under the sphere. The hand retains its full solid after release.
    paint(oval(j["hand_R"], (1.23, 1.15, 1.15), 2.6), "saddle", "hand_R")
    return v.material, v.part


if __name__ == "__main__":
    model_cli(build, __file__)
