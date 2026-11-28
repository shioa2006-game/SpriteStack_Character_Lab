"""Bake chapter-one object sheets, game-camera crops and placement coordinates."""
import argparse
from importlib import import_module
from pathlib import Path

import numpy as np

from objects.bake import DIRECTIONS, ROOT, bake, load, write_json
from research.objects01.game_projection import PROFILE, collect, game_camera, write_atlas
from spritestack.character import read_json

from . import IDS


def project(point, yaw, metric):
    pitch, density, z_scale = metric
    a, e = np.deg2rad([yaw,pitch])
    x,y,z = point
    u = x*np.cos(a) + y*np.sin(a)
    v = (-x*np.sin(a)+y*np.cos(a))*np.sin(e) - z*z_scale*np.cos(e)
    return np.around(np.array([u,v])*density, 4).tolist()


def export(out, ids):
    out.mkdir(parents=True, exist_ok=False)
    records, frames, placement = {}, [], {}
    profile = read_json(PROFILE)
    game = game_camera(profile,profile["step_model"])
    for name in ids:
        folder = ROOT/name
        spec = read_json(folder/"object.json")
        vol = import_module("objects."+name+".build_model").build(spec)
        npz = out/"models"/(name+".npz")
        npz.parent.mkdir(exist_ok=True)
        np.savez_compressed(npz,slices=vol.materials,parts=vol.parts)
        model = load(folder,npz)
        dest = out/"assets"/name
        bake(model,dest)
        collect(model,name,game,records,frames)
        for state,view in spec["views"].items():
            points = view["placement"]["points_xyz"]
            placement[name+"/"+state] = {
                "game_kind": spec["geometry"]["game_kind"], "points_xyz": points,
                "offsets_px_from_anchor": {camera:{d:{key:project(p,yaw,metric) for key,p in points.items()}
                                for d,yaw in DIRECTIONS.items()}
                                for camera,metric in (("lab",(24,1.5,1)),("game",game))}}
    write_atlas(out/"study","game",records,frames)
    write_json(out/"study"/"placement.json",placement)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--only",nargs="+",choices=IDS,default=IDS)
    args=parser.parse_args()
    export(args.out,args.only)
