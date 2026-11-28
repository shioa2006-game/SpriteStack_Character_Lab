"""Sena's embroidered robes, silver hair, folded witch hat and crystal-tipped staff."""

import numpy as np

from characters.voxel_shapes import Volume, model_cli


def build(config):
    v = Volume(config)
    oval, rod, paint, j = v.oval, v.rod, v.paint, v.joints
    x, y, z = v.x, v.y, v.z
    for side in ("R", "L"):
        v.limb(side, "hip", "knee", 1.16, .96, "underskirt", "thigh")
        v.limb(side, "knee", "ankle", 1.0, .87, "leather", "shin")
        v.shoe(side, 1.12, 1.82, "leather", "navy")
    # Open-front layered skirt. Its left and right panels follow the two legs.
    d = np.clip(14.4-z, 0, 12)
    angle = np.arctan2(x, y)
    a = np.abs(angle)
    rho = np.sqrt((x/(3+.24*d))**2 + (y/(2.15+.20*d))**2)
    rho *= 1+.048*np.cos(6*angle)
    hem = 5.4 + .35*np.cos(5*angle) - 1.0*np.cos(angle)
    skirt = (z > hem) & (z < 15.0) & (rho < 1) & (rho > .62)
    paint(oval((0, 0, 13.8), (3.12, 2.22, 2.40)), "underskirt", "pelvis")
    paint(skirt, "underskirt", "pelvis")
    opening = .29+.045*d
    panels = skirt & (a > opening)
    paint(panels, "indigo", "pelvis")
    paint(panels & (np.cos(6*angle) < -.66), "navy", "pelvis")
    paint(panels & ((a < opening+.16) | (z < hem+.58)), "embroidery", "pelvis")
    # Repeated paired leaves above the hem are large enough to resolve on diagonal views.
    paint(panels & (np.abs(z-hem-1.6-.88*np.cos(angle*11)) < .30), "embroidery", "pelvis")
    torso = oval((0, 0, 17.72), (3.48, 2.35, 4.20), 2.25) & (z > 14.45)
    paint(torso, "indigo", "chest")
    paint(torso & (y > .38) & (np.abs(x-.36*(z-18)) < .45), "embroidery", "chest")
    paint(oval((0, 0, 14.75), (3.0, 2.36, .75), 3.6), "leather", "pelvis")
    paint(oval((.1, 2.17, 14.77), (.80, .47, .54), 3.2), "embroidery", "pelvis")
    v.cloak(20.65, 7.3, 3.35, 4.5, -2.30, "indigo", "navy")
    for side in ("R", "L"):
        sh, el, ha = (j[n+"_"+side] for n in ("shoulder", "elbow", "hand"))
        upper, fore = "upper_"+side, "fore_"+side
        v.limb(side, "shoulder", "elbow", 1.36, 1.12, "indigo", "upper")
        v.limb(side, "elbow", "hand", 1.0, .66, "underskirt", "fore")
        sleeve = rod(el, el+.70*(ha-el), 1.14, 1.60)
        paint(sleeve, "indigo", fore)
        paint(sleeve & (z < (el+.69*(ha-el))[2]+.43), "embroidery", fore)
        paint(oval(ha, (.81, .83, .92)), "skin", "hand_"+side)
    paint(oval((0, -.1, 20.57), (4.20, 2.88, 1.57)), "navy", "chest")
    paint(oval((.15, 2.57, 20.68), (.91, .55, .95), 1.35), "crystal", "chest")
    # Long locks anchor into the coiffure under the brim and extend over the mantle.
    paint(oval((0, -.75, 24.07), (3.35, 2.62, 3.65)), "silver", "head")
    for dx, length in [(-2.5, 6.0), (-1.35, 8.7), (0, 9.7), (1.3, 8.2), (2.55, 7.0)]:
        a0 = (dx, -1.66, 24.7)
        mid = (1.17*dx+.31, -3.26, 21.5)
        end = (1.18*dx-.53, -3.76, 24.55-length)
        paint(rod(a0, mid, 1.36, 1.18) | rod(mid, end, 1.18, .43),
              "silver shade" if dx in (-1.35, 1.3) else "silver", "head")
    paint(oval((0, .36, 24.37), (2.91, 2.66, 3.16), 2.15), "skin", "head")
    # Seat both irises on the same forward surface beneath the sloping fringe.
    for side in (-1, 1):
        paint(oval((side*1.30, 3.00, 24.70), (.60, .45, .85), 2.5), "skin", "head")
        paint(oval((side*1.10, 2.85, 24.45), (.50, .46, .93), 2.5), "eyes", "head")
    paint(oval((0, 2.83, 23.88), (.52, .42, .63)), "skin", "head")
    fringe = oval((0, 0, 26.0), (3.17, 2.92, 2.47))
    paint(fringe & ((y < 1.12) | (z > 25.15-.52*x)), "silver", "head")
    for s in (-1, 1):
        paint(rod((s*2.7, 1.12, 25.55), (s*3.15, 1.02, 21.5), .95, .43), "silver", "head")
    # Elliptical, upturned brim with a gold welt. A crooked cone folds at the crown.
    r = np.sqrt((x/6.55)**2 + ((y+.25)/5.20)**2)
    brim_z = 26.63 - .16*x - .12*y + .77*r**2
    brim = (r <= 1) & (np.abs(z-brim_z) <= .55)
    paint(brim, "navy", "head")
    paint(brim & (r > .90), "embroidery", "head")
    t = np.clip((z-26.65)/8.8, 0, 1)
    width = 3.70*(1-t)+.63*t
    cone_r = np.sqrt(((x+2.6*t**1.55)/width)**2 + ((y+.3+.48*t)/(.90*width))**2)
    cone = (cone_r <= 1) & (z >= 26.4) & (z <= 35.48)
    paint(cone, "indigo", "head")
    paint(cone & (z > 28.16-.13*x) & (z < 29.05-.13*x), "embroidery", "head")
    paint(cone & (z > 30) & (z < 32.20) & (np.abs(z-31.10-.56*np.cos(3*angle)) < .35),
          "embroidery", "head")
    paint(rod((-2.45, -.75, 34.82), (-4.22, -.90, 33.9), 1.14, .81)
          | rod((-4.22, -.90, 33.9), (-5.28, -.78, 31.60), .81, .38), "navy", "head")
    paint(oval((-5.28, -.78, 31.24), (.54, .54, .80), 1.4), "embroidery", "head")

    grip = j["hand_R"]
    foot = np.array([-6.77, 1.83, 2.65])
    axis = (grip-foot)/(grip[2]-foot[2])
    crown = foot+axis*(28.0-foot[2])
    foot = foot + 1.8*axis
    paint(rod(foot, crown, .66, .83), "staff wood", "staff")
    paint(rod(foot, foot+axis*1.8, .74), "embroidery", "staff")
    for dz in (-.6, 1.65):
        q = crown+dz*axis
        paint(rod(q-axis*.38, q+axis*.38, 1.0), "embroidery", "staff")
    for s in (-1, 1):
        points = [crown, crown+[s*1.45, -.12, 1.25], crown+[s*2.03, .16, 2.7],
                  crown+[s*1.47, .37, 4.2]]
        v.path(points, .51, "embroidery", "staff")
    center = j["crystal_tip"] - [0, 0, 3.30]
    dx, dy, dz = (v.xyz-center).transpose(3, 0, 1, 2)
    gem = (np.abs(dx+.20*dy)/2.05 + np.abs(dy-.20*dx)/1.82 + np.abs(dz)/3.30 <= 1)
    paint(gem, "crystal", "staff")
    paint(gem & (dx > .06) & (dx < .63) & (dz > -1.10), "ice", "staff")
    paint(oval(grip, (.90, .90, .96), 2.45), "skin", "hand_R")
    return v.material, v.part


if __name__ == "__main__":
    model_cli(build, __file__)
