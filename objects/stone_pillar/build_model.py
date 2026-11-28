"""Three dressed ashlar drums. The middle drum also supplies the bridge module."""
import numpy as np

from objects.volume import Volume, model_cli


def build(spec):
    v = Volume(spec)
    x, y, z = v.x, v.y, v.z
    ax, ay = abs(x), abs(y)
    height = z % 14
    edge = np.maximum(ax, ay)
    chamfer = ax + ay
    # Flat bearing lands at both ends; bevel the four longitudinal corners.
    stone = (edge < 7) & (chamfer < 12.5) & (z >= 0) & (z < 42)
    along = np.where(ay >= ax, x*np.sign(y), -y*np.sign(x))
    # Shallow lancet-shaped recesses leave broad stone bearing strips on all
    # four sides. After a fall, the strips become the walking surface.
    arch = (abs(along) < 4.6) & (height > 2.2) & (height < 11.9 - .44*abs(along))
    stone &= ~(arch & (edge > 6.45) & ((y >= 0) | (ax > ay)))
    chipped = ((along > 3.4) & (z > 33) & (z < 37) & (chamfer > 11.7 + .22*abs(z-35)))
    stone &= ~chipped
    for i, part in enumerate(spec["parts"]):
        block = stone & (z >= 14*i) & (z < 14*(i+1))
        v.paint(block, "ash" if i != 1 else "mauve", part)
    v.finish((height < .55) & (edge > 5.5), "joint")
    v.finish((height >= .55) & (height < 1.5), "pale")
    v.finish((height > 12.5) & (height < 13.5), "wear")
    v.finish((height >= 1.5) & (height < 2.1) & (edge > 6), "carving")
    field = arch & (edge > 5.5)
    v.finish(field, "mauve")
    v.finish(field & ((abs(along) > 3.8) | (height > 10.7 - .44*abs(along))), "carving")
    # A split lozenge, cut through one ledge. Highlights use the quarry's
    # pale stone rather than a separate metal inlay.
    lozenge = abs(along + .5) + .66*abs(height - 7.3)
    v.finish(field & (lozenge < 2.3), "carving")
    v.finish(field & (lozenge < 1.3) & (along < 0), "wear")
    v.finish((edge > 6) & (abs(along + 4.5 - .48*(z-29)) < .4) & (z > 27) & (z < 32), "joint")
    v.finish(chamfer > 11.4, "wear")
    # A dressed square around the top face is visible from every camera yaw.
    v.finish((z > 41.5) & (edge > 4) & (edge < 5.2), "carving")
    return v


if __name__ == "__main__":
    model_cli(__file__, build)
