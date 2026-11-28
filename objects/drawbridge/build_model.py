from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v = Volume(spec)
    x,y,z = v.x,v.y,v.z
    ax = abs(x)
    # Six transverse planks. Flush end grain bears on both lips at deck grade.
    planks = (ax < 5.75) & (y >= 0) & (y < 14) & (z >= -1.5) & (z < 0)
    board = np.floor(y/2.5)
    v.paint(planks,"oak","deck")
    v.finish(planks & (board%3 == 0),"honey")
    v.finish(planks & ((y%2.5 < .85) | ((abs(y%2.5-1.25-.25*np.sin(x)) < .2) & (abs(x-1) < 2))),"grain")
    stringer = (abs(ax-4) < 1) & (y >= 0) & (y < 14) & (z >= -2.5) & (z < -1.5)
    v.paint(stringer,"grain","deck")
    brace = (ax < 4.5) & (abs(y-7-x*1.1) < .9) & (z >= -2.5) & (z < -1.5)
    v.paint(brace,"honey","deck")
    straps = planks & (abs(ax-4.25) < .7) & ((y < 3) | (y > 11))
    v.finish(straps,"iron")
    v.finish(straps & ((abs(y-1.25) < .35) | (abs(y-12.75) < .35)), "bronze")
    radial = np.hypot(y,z+1)
    wheel = (ax > 5.5) & (ax < 6.5) & (radial < 2.7) & (y >= -.5)
    v.paint(wheel,"iron","quadrant")
    v.finish(wheel & (radial > 1.7),"bronze")
    shoe = (ax >= 6.5) & (ax < 7.5) & (y > -3.5) & (y < 1) & (z >= -2.5) & (z < .5)
    # The pin sits below the tread. Only the two exterior heads flare outward.
    axle = (ax < 8) & ((radial < .68) | ((ax >= 6.5) & (radial < .83)))
    v.paint(shoe | axle,"iron","bearings")
    v.finish(axle & (ax > 6.8),"edge")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
