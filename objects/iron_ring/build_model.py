from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v = Volume(spec)
    x,y,z = v.x,v.y,v.z
    # A diamond-ended strap holds the staple above the open eye.
    plate = (abs(x) < 2.75) & (abs(z-13.5)+.62*abs(x) < 3.5) & (y >= 0) & (y < 1)
    v.paint(plate, "iron", "plate")
    v.finish(plate & (abs(x) > 2), "rust")
    for level in (11.5,15.5):
        rivet = (x*x+(z-level)**2 < .8) & (y >= 1) & (y < 1.8)
        v.paint(rivet,"bronze","plate")
    staple = (abs(x) < 1.3) & (y >= 1) & (y < 4) & (abs(z-13) < 1)
    v.paint(staple,"edge","staple")
    radius = np.hypot(x, z-7.5)
    eye = (radius-5.1)**2+(y-3.5)**2 < 1.12**2
    v.paint(eye,"iron","ring")
    v.finish(eye & (z > 9) & (x < .5), "edge")
    v.finish(eye & (radius < 4.55) & (z < 6), "edge")
    v.finish(eye & (x > 2.5) & (z < 6.5), "rust")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
