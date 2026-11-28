"""Round fieldstone fractured along irregular planar faces in model space."""
import numpy as np

from objects.volume import Volume, model_cli


def build(spec):
    v = Volume(spec)
    x, y, z = v.x, v.y, v.z - 8.5
    # Unequal tangent planes cut a rounded core. Faces and pigment rotate together.
    q = np.stack((x / 9, y / 8.5, z / 8.5), axis=-1)
    n = np.arange(30)
    h = 1 - 2 * (n + .5) / len(n)
    phi = n * 2.399963
    radial = np.sqrt(1 - h*h)
    directions = np.stack((radial*np.cos(phi), radial*np.sin(phi), h), axis=1)
    distances = (q @ directions.T) / (.89 + .055*np.sin(n * 5.17))
    faces = distances.argmax(axis=-1)
    rock = (distances.max(axis=-1) < 1) & ((q*q).sum(axis=-1) < 1.02)
    v.paint(rock, "basalt", "stone")
    v.finish(faces % 4 == 1, "slate")
    v.finish(faces % 4 == 2, "plum")
    v.finish(faces % 7 == 3, "light")
    # Two displaced beds and a forked fissure wrap around the stone. Limit the
    # length of each exposure so it reads as a broken face rather than a belt.
    bed = z - .37*x + .22*y + .65*np.sin(.48*y + .27*x)
    seam = bed + .65*np.maximum(0, x-1)
    v.finish((abs(seam+1) < .68) & (x + .55*y > -1.7), "split")
    v.finish((seam > -.4) & (seam < .55) & (x + .55*y > 2), "light")
    v.finish((abs(z - 1.8 + .92*x - .16*y) < .58) & (seam > -.8) & (seam < 3) & (y > 0), "split")
    v.finish((abs(bed-4) < .62) & (x - .42*y < -1), "vein")
    v.finish((bed < -3) & (faces % 9 == 5), "lichen")
    return v


if __name__ == "__main__":
    model_cli(__file__, build)
