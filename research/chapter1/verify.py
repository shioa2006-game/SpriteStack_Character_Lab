"""Check handoff coordinates against actual voxels, native sheets and game atlas."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from objects.bake import DIRECTIONS, ROOT, load, pose
from research.verify_objects import check, compare_files, same, sample
from spritestack.character import read_json
from spritestack.rig import transform
from . import IDS
from .export import export


def fixtures():
    ring=load(ROOT/"iron_ring")
    points=ring.spec["views"]["idle"]["placement"]["points_xyz"]
    mount,hook,hole=sample(ring.source_grid,ring.part_ids,np.array([points[k] for k in ("mount","hook","aperture")]))
    check(mount==ring.parts["plate"] and hook==ring.parts["ring"] and hole==0,"ring connection sockets")

    bridge=load(ROOT/"drawbridge")
    deck=bridge.parts["deck"]
    for state,view in bridge.spec["views"].items():
        _,parts,grid,matrices,_=pose(bridge,view,view["angles_deg"][0])
        p=np.array(bridge.spec["rotation"]["pivot_xyz"])
        for matrix in matrices.values():
            check(np.allclose(transform(matrix,p),p),"bridge hinge")
        probes=np.array([[x,y,-.25] for x in (-3,0,3) for y in (.25,7,13.75)])
        if state=="lowered":
            same(sample(grid,parts,probes),np.full(len(probes),deck),"shore/deck/shore")
            check(not sample(grid,parts,probes+[0,0,.5]).any(),"level deck")
        else:
            check(not sample(grid,parts,probes[probes[:,1]>=7]).any(),"raised span open")
    target=load(ROOT/"archery_target")
    hit=target.spec["views"]["hit"]
    _,_,_,matrices,_=pose(target,hit,hit["angles_deg"][0])
    neutral=target.spec["views"]["idle"]["placement"]["points_xyz"]
    check(np.allclose(transform(matrices["board"],neutral["center"]),hit["placement"]["points_xyz"]["center"]),"folded bullseye")
    gate=load(ROOT/"ruin_gate")
    for name in ("idle","open"):
        vol,_,grid,_,_=pose(gate,gate.spec["views"][name],0)
        probe=np.array([[0,0,z] for z in (2,7,15,21)])
        check(bool(sample(grid,vol,probe).any())==(name=="idle"),"gate central passage")
        check(sample(grid,vol,np.array([[0,0,28]])).all(),"fixed lintel")
    print("PASS ring plate/hook/hole, bearing pivot, both lips, clear span, target hinge and gate passage")


def verify(out):
    export(out,IDS)
    docs=ROOT.parent/"docs"
    shipped=docs/"studies/chapter1"
    for id in IDS:
        compare_files(out/"assets"/id,docs/"assets"/id)
        with np.load(out/"models"/(id+".npz")) as a, np.load(ROOT/id/"model.npz") as b:
            for key in ("slices","parts"):
                same(a[key],b[key],id+" "+key)
    for name in ("game.json","placement.json"):
        check(read_json(out/"study"/name)==read_json(shipped/name),name+" rebuild")
    atlas=Image.open(shipped/"game.png").convert("RGBA")
    same(atlas,Image.open(out/"study/game.png").convert("RGBA"),"game atlas RGBA")
    crops=read_json(shipped/"game.json")
    coords=read_json(shipped/"placement.json")
    maps=read_json(shipped/"map-placement.json")
    for kind,rule in maps["state_mapping"].items():
        for flag in ("default","true","false"):
            if flag in rule:
                key=rule["asset"]+"/"+rule[flag]
                check(key in crops and coords[key]["game_kind"]==kind,"map state "+key)
    for site in maps["instances"]:
        check(site["heading_deg"]%45==0 and len(site["tile_origin_xy"])==2,"instance pose")
        if site["asset"]=="drawbridge":
            hinge=site["game_tile"]
            check(site["tile_origin_xy"]==[hinge[0]-.5,hinge[1]] and site["heading_deg"]==90
                  and site["origin_z_model"]==8*site["ground_steps"],"westbound level bridge")
    for key,rows in crops.items():
        same(list(rows),list(DIRECTIONS),key+" camera rows")
        for d,[entry] in rows.items():
            x,y,w,h=entry["rect"]
            crop=atlas.crop((x,y,x+w,y+h))
            check(crop.getbbox()==(0,0,w,h),key+" crop")
            if key=="iron_ring/idle" and d in ("S","SE","SW"):
                xy=coords[key]["offsets_px_from_anchor"]["game"][d]["aperture"]
                uv=np.rint(xy).astype(int)-entry["offset"]
                check(crop.getpixel(tuple(uv))[3]==0,d+" game aperture")
                native=Image.open(docs/"assets/iron_ring/idle.png")
                xy=coords[key]["offsets_px_from_anchor"]["lab"][d]["aperture"]
                layout=read_json(docs/"assets/iron_ring/metadata.json")["neutral"]
                uv=np.rint(xy).astype(int)+layout["anchor"]+[list(rows).index(d)*layout["cell"][0],0]
                check(native.getpixel(tuple(uv))[3]==0,d+" Lab aperture")
    fixtures()
    print("PASS independently rebuilt 6 models / 10 sheets / 80 views, native and game placements")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True,type=Path)
    verify(p.parse_args().out)
