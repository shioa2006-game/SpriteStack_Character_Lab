"""Oak plank case with flush top rails and corner battens."""
import numpy as np

from objects.volume import Volume, model_cli


def build(spec):
    v = Volume(spec)
    x, y, z = v.x, v.y, v.z
    ax, ay = abs(x), abs(y)
    height = spec["geometry"]["rest_dimensions_xyz"][2]
    sill, cap = 1, height - 1.5
    case = (ax < 6.5) & (ay < 6.5) & (z >= 0) & (z < height)
    v.paint(case, "oak", "case")
    # The boards run vertically on the sides and front-to-back on the lid.
    board = np.where((ay > ax) & (z < cap), x, y)
    stave = np.floor((board + 7) / 3.5).astype(int)
    v.finish(stave % 3 == 1, "heart")
    v.finish(stave % 3 == 2, "honey")
    v.finish((board + 7) % 3.5 < .5, "seam")
    length = np.where(z >= cap, x + 7, z)
    grain = (board + .35*np.sin(length*.55 + stave) + 7) % 3.5
    v.finish((grain < .65) & (np.cos(length*.65 + stave*3) > -.2), "grain")
    edge = np.maximum(ax, ay)
    frame = (edge < 7) & (ax + ay < 13.5) & (z >= 0) & (z < height)
    frame &= (edge >= 5.5) & ((z < sill) | (z >= cap) | (np.minimum(ax, ay) > 5))
    v.paint(frame, "rail", "battens")
    # A narrow shadow under the cap keeps the flat tread distinct from the brace.
    v.finish(frame & (z >= cap) & (z < cap + .5) & (np.minimum(ax, ay) < 5), "heart")
    # One diagonal brace sits proud of each face, between the top and sill.
    along = np.where(ay > ax, x*np.sign(y), -y*np.sign(x))
    brace = (edge >= 6) & (edge < 7) & (abs(along) < 5.5) & (z >= sill) & (z < cap)
    # Cut the brace to the clear opening. Hardware and grain retain their gauge.
    distance = z - (sill + cap)/2 - along*(cap - sill - 1)/10
    brace &= abs(distance) < .85
    v.paint(brace, "rail", "battens")
    v.finish(brace & (distance < -.34), "heart")
    nail = (abs(abs(along) - 5.5) < .65) & ((z < 1) | (abs(z - (height-1)) < .55))
    v.finish(frame & nail & (edge > 6), "iron")
    return v


if __name__ == "__main__":
    model_cli(__file__, build)
