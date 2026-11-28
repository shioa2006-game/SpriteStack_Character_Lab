"""Hollow cedar coffer and barrel lid, with separate hinge knuckles."""
import numpy as np

from objects.volume import Volume, model_cli


def build(spec):
    v = Volume(spec)
    x, y, z = v.x, v.y, v.z
    ax, ay = abs(x), abs(y)
    outer = (ax < 8.5) & (ay < 5) & (z >= 0) & (z < 6) & (ax + ay < 13)
    cavity = (ax < 7) & (ay < 3.5) & (z >= 3.5)
    body = outer & ~cavity
    v.paint(body, "cedar", "coffer")
    v.finish((ax < 7.5) & (ay < 4) & (z >= 3), "lining")
    v.finish((z > 2) & (z < 2.65) & (ay > 4), "cut")
    v.finish(z > 5, "rim")
    arch = (y / 5)**2 + ((z - 6) / 4.5)**2
    hollow = ((y / 3.9)**2 + ((z - 6) / 3.4)**2 < 1) & (ax < 7.5)
    lid = (ax < 8.5) & (z >= 6) & (arch < 1) & ~hollow
    v.paint(lid, "copperwood", "lid")
    v.finish(lid & (arch < .75), "wine")
    # Slats run the length of the vault; their ends are visible on the cheeks.
    arc = np.arctan2((z-6)/4.5, y/5)
    v.finish(lid & (arc > 0) & (np.sin(arc*7) > .91), "cedar")
    v.finish(lid & (ax > 7.5) & (abs(z-7.75) < .3), "cut")
    band = abs(ax - 5.75) < 1
    v.finish(band & body & (ay >= 4.5), "bronze")
    hoop = band & (z >= 6) & (arch >= .70) & (arch < 1.18)
    v.paint(hoop, "brass", "lid")
    v.finish(hoop & (ax > 6), "bronze")
    v.finish(lid & (ax < 7) & (arch < .74), "wine")
    # The floor and inner rim frame an unoccupied, dark well.
    v.finish(body & (ax < 7) & (ay < 3.5) & (z < 3.5), "lining")
    v.finish(body & (ax < 7) & (ay < 3.5) & (z < 3.5) & (abs(y + 1.5) < .3), "cut")
    lock = (ax <= 2) & (y >= 4.5) & (y < 5.75) & (z >= 2.5) & (z < 6)
    v.paint(lock, "brass", "coffer")
    v.finish(lock & (ax < .6) & (z >= 3) & (z < 4.5), "iron")
    v.paint((ax <= 1) & (y >= 4.5) & (y < 5.5) & (z >= 6) & (z < 7.5), "bronze", "lid")
    # Back rail pins stay with the case. Two short lid knuckles occupy adjacent X spans.
    radius2 = (y + 5)**2 + (z - 6)**2
    seat = (ax >= 5.5) & (ax < 7)
    knuckle = (ax >= 4) & (ax < 5.5)
    relief = (radius2 < 1.45**2) & ((seat & (v.parts == v.owners["lid"])) |
                                    (knuckle & (v.parts == v.owners["coffer"])))
    v.materials[relief] = 0
    v.parts[relief] = 0
    barrel = radius2 <= .85**2
    v.paint(barrel & seat, "bronze", "coffer")
    v.paint(barrel & knuckle, "brass", "lid")
    return v


if __name__ == "__main__":
    model_cli(__file__, build)
