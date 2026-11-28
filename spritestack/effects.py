"""A short emission of faceted particles attached to a posed marker."""

import numpy as np

from .rig import unit, vec


def crystal_burst(character, settings, key, joints, volume, parts, owner):
    grid = character.posed_grid
    forward = unit(vec(key["aim"]))
    right = unit(np.cross(forward, [0, 0, 1]))
    if np.linalg.norm(right) < .5:
        right = vec([1, 0, 0])
    up = np.cross(right, forward)
    for lateral, lift, distance, length, width in settings["shards"]:
        center = joints[settings["marker"]] + lateral*right + lift*up + distance*forward
        axis = unit(distance*forward + lateral*right + lift*up)
        across = unit(np.cross(up, axis))
        normal = np.cross(axis, across)
        extent = length + width
        lo = np.floor((center - extent - grid.origin)/grid.spacing).astype(int)
        hi = np.ceil((center + extent - grid.origin)/grid.spacing).astype(int)
        if np.any(lo < 0) or np.any(hi > grid.size_xyz):
            raise ValueError("crystal burst exceeds posed volume")
        box = tuple(slice(a,b) for a,b in zip(lo[::-1],hi[::-1]))
        indices = np.indices(volume[box].shape).transpose(1,2,3,0)[...,::-1]
        offset = grid.origin + (lo + indices + .5)*grid.spacing - center
        edge = np.abs(offset @ axis)/length + (np.abs(offset @ across) + np.abs(offset @ normal))/width
        fill = (edge <= 1) & (parts[box] == 0)
        volume[box][fill] = np.where((offset @ across)[fill] > .15, settings["highlight"], settings["material"])
        parts[box][fill] = owner
