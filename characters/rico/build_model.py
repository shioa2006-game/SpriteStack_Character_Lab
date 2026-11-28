"""Rico in a travel hood, carrying a strung bow, a hip rope and a back quiver."""

import numpy as np

from characters.voxel_shapes import Volume, model_cli


def build(config):
    v = Volume(config)
    oval, rod, paint, j = v.oval, v.rod, v.paint, v.joints
    x, y, z = v.x, v.y, v.z
    for side in ("R", "L"):
        knee, ankle = j["knee_"+side], j["ankle_"+side]
        v.limb(side, "hip", "knee", 1.34, 1.02, "shorts", "thigh")
        paint(oval(knee+[0, 0, .62], (1.27, 1.3, .73), 3.3), "suede", "thigh_"+side)
        v.limb(side, "knee", "ankle", .94, .69, "skin", "shin")
        boot_top = ankle+.62*(knee-ankle)
        paint(rod(ankle, boot_top, .89, 1.15), "leather", "shin_"+side)
        paint(oval(boot_top, (1.18, 1.27, .63), 3), "suede", "shin_"+side)
        v.shoe(side, 1.12, 1.67, "leather", "shorts")
    paint(oval((0, 0, 10.6), (2.84, 1.95, 2.0), 2.6), "shorts", "pelvis")
    tunic = oval((0, 0, 14.3), (3.26, 2.22, 3.7), 2.4)
    paint(tunic, "linen", "chest")
    paint(tunic & (np.abs(x-.65*(z-14.3)) < .56), "leather", "chest")
    paint(oval((0, .03, 11.25), (2.98, 2.22, .75), 3), "leather", "pelvis")
    paint(oval((.23, 2.1, 11.24), (.75, .40, .57), 4), "brass", "pelvis")
    paint(oval((-2.66, .52, 10.92), (1.27, 1.07, 1.32), 3.1), "suede", "pelvis")
    v.cloak(17.6, 7.25, 3.45, 4.52, -1.90, "moss", "forest")
    for side in ("R", "L"):
        sh, el, ha = (j[k+"_"+side] for k in ("shoulder", "elbow", "hand"))
        v.limb(side, "shoulder", "elbow", 1.16, .94, "linen", "upper")
        paint(oval(el+[0, 0, .35], (1.13, 1.16, .83), 2.5), "linen", "upper_"+side)
        v.limb(side, "elbow", "hand", .82, .59, "skin", "fore")
        paint(rod(el+.47*(ha-el), ha, .85, .68), "leather", "fore_"+side)
        paint(oval(ha, (.83, .84, .86)), "skin", "hand_"+side)
    # A loop on the belt faces forwards. A two-tined iron hook hangs from its knot.
    loop = (np.sqrt(((x+2.5)/1.53)**2 + ((z-9.20)/2.0)**2)-1)**2 + ((y-2.28)/1.6)**2 <= .34**2
    paint(loop, "rope", "pelvis")
    # Lead the loose end off the lower rim, leaving the middle of the coil open.
    v.path([(-2.50, 2.25, 7.20), (-3.16, 2.32, 7.30), (-3.43, 2.33, 6.95)], .45, "rope", "pelvis")
    # The hook hangs obliquely so its tips separate in both front and right profile.
    v.path([(-3.43, 2.33, 7.14), (-3.66, 2.38, 5.98), (-4.58, 2.95, 6.22),
            (-4.96, 3.21, 7.26)], .46, "iron", "pelvis")
    v.path([(-3.66, 2.38, 5.98), (-2.77, 1.83, 6.12), (-2.31, 1.55, 6.88)], .43, "iron", "pelvis")
    # Quiver below the right ear. Differing shaft lengths separate the fletchings from behind.
    bottom, mouth = np.array([1.55, -3.70, 10.3]), np.array([-3.10, -3.65, 18.42])
    paint(rod(bottom, mouth, 1.05, 1.32), "leather", "chest")
    paint(rod(mouth+[.17, 0, -.30], mouth, 1.49), "brass", "chest")
    for dx, dy, length in [(-.90, -.4, 3.85), (.06, -.72, 5.30), (.79, .25, 3.28)]:
        a = mouth + [dx, dy, -.32]
        b = a + [(-.64+.20*dx)*length, -.65, length]
        paint(rod(a, b, .34), "wood", "chest")
        paint(rod(b+[.64, 0, -1.48], b+[-.15, 0, .12], .70, .34), "fletching", "chest")
    collar = oval((0, -.1, 17.65), (3.69, 2.72, 1.55))
    paint(collar, "moss", "chest")
    paint(oval((0, .76, 17.45), (2.69, 2.55, 1.19)), "saffron", "chest")
    v.path([(.62, 2.18, 17.45), (1.85, 2.75, 16.1), (2.85, 3.35, 14.7),
            (3.15, 3.55, 13.7)], .78, "saffron", "chest")
    paint(oval((0, .15, 20.62), (2.98, 2.66, 3.02), 2.25), "skin", "head")
    for s in (-1, 1):
        paint(oval((s*2.66, .36, 20.55), (.71, .83, 1.03)), "skin", "head")
    hair = oval((0, -.10, 21.8), (3.27, 2.87, 3.0), 2.1)
    fringe = 22.24 + .19*x + .48*np.cos(x*2.1)
    paint(hair & ((y < .70) | (z > fringe)), "copper", "head")
    for s in (-1, 1):
        paint(rod((s*2.65, .75, 22.1), (s*3.46, .90, 19.9), .80, .33), "copper", "head")
    paint(oval((0, 2.62, 20.15), (.47, .47, .55)), "skin", "head")
    for sign, iris in ((-1, "right eye"), (1, "left eye")):
        paint(oval((sign*.75, 3.00, 21.65), (.76, .58, .85), 2.5), "skin", "head")
        # Round the outer corner so the side of the iris recedes into the cheek.
        cheek = oval((sign*1.75, 2.80, 21.25), (.50, .90, 1.10), 2.5)
        paint(cheek & (v.material == 0), "skin", "head")
        # Keep each iris one pixel wide and two pixels tall from the front.
        paint(oval((sign, 3.05, 21.20), (.38, .60, .70), 2.5), iris, "head")
    # The hood has an open, asymmetric front arch and a folded point at the nape.
    hood = oval((0, -.52, 22.02), (3.65, 3.30, 3.22), 2.25)
    opening = (y > .22) & (z < 23.08 + .47*y - .19*x)
    paint(hood & ~opening, "moss", "head")
    paint(hood & ~opening & (y > .65) & (z < 23.65 + .47*y - .19*x), "brass", "head")
    paint(rod((0, -2.25, 23.30), (.65, -4.0, 20.40), 1.77, .47), "forest", "head")

    grip = j["hand_L"]
    # The limb tips sweep backwards. The string lies inside the bow's side profile.
    points = [grip + offset for offset in [(2.90, -2.75, -7.30), (1.55, -.75, -6.55),
              (.22, 1.02, -4.45), (.04, .53, -1.6), (0, 0, 0), (-.06, .93, 2.65),
              (.30, 1.48, 4.90), (1.72, .10, 7.17), (3.75, -2.20, 8.60)]]
    v.path(points, .62, "wood", "bow")
    paint(rod(points[0], points[-1], .53), "string", "bow")
    paint(rod(points[3], grip+[.15, .30, 1.0], .78), "brass", "bow")
    paint(oval(grip, (.91, .94, .90), 2.6), "leather", "hand_L")
    return v.material, v.part


if __name__ == "__main__":
    model_cli(build, __file__)
