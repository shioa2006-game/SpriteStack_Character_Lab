"""Verify research specimens, stage conversion, the published crate and the three-BEAM handoff."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from objects.bake import DIRECTIONS, ROOT, load
from research.objects01 import game_projection
from research.verify_objects import centers, check, check_platform, same
from spritestack.character import read_json
from . import build_study
from .baseline.build_model import build as old_crate
from .variants import HEIGHTS, crate


class Atlas:
    def __init__(self, path):
        self.data = read_json(path.with_suffix(".json"))
        self.image = Image.open(path.with_suffix(".png")).convert("RGBA")

    def cell(self, key, direction, frame=0):
        record = self.data[key][direction][frame]
        x,y,w,h = record["rect"]
        return self.image.crop((x,y,x+w,y+h)), tuple(record["offset"])


def projected_cell(im, at, size=160):
    result = Image.new("RGBA", (size,size))
    result.paste(im, (size//2+at[0], size//2+at[1]))
    return result


def handoff(atlas, prefix, pitch, density, offsets):
    results = []
    for d,yaw in DIRECTIONS.items():
        def cell(state, frame=0):
            return atlas.cell(prefix+"/"+state, d, frame)
        for f, state in [(0,"idle"),(-1,"fallen")]:
            image, anchor = cell("topple", f)
            still, expected = cell(state)
            same(image,still,prefix+" endpoint "+d)
            check(anchor == expected, "moving pillar anchor")
        im, xy = cell("fallen")
        full = np.array(projected_cell(im,xy))[:,:,3] > 0
        beam, (bx,by) = cell("beam")
        assembled = Image.new("RGBA", (160,160))
        for x,y,_ in offsets:
            theta = np.deg2rad(yaw)
            dx = (x*np.cos(theta)+y*np.sin(theta))*density
            dy = (-x*np.sin(theta)+y*np.cos(theta))*density*np.sin(np.deg2rad(pitch))
            assembled.alpha_composite(beam,(80+round(dx)+bx,80+round(dy)+by))
        modules = np.asarray(assembled)[:,:,3] > 0
        results.append((full & modules).sum()/(full | modules).sum())
    check(min(results) >= .94, prefix+" adapted endpoint silhouette")
    return min(results)


def main(out):
    docs = ROOT.parent/"docs"
    profile = read_json(game_projection.PROFILE)
    step, tile = profile["step_model"], profile["tile_model"]
    expected = read_json(ROOT/"wooden_crate"/"quality.json")["platform"]
    out.mkdir(parents=True, exist_ok=False)
    build_study.build(out)
    game_projection.build(out)
    for stem,folder in [("scale-study","objects01a"),("game","objects01")]:
        baked, published = Atlas(out/stem), Atlas(docs/"studies"/folder/stem)
        same(baked.image,published.image,stem+" independent RGBA rebuild")
        check(baked.data == published.data,stem+" placement metadata rebuild")

    study, game = Atlas(out/"scale-study"), Atlas(out/"game")
    for h in HEIGHTS:
        model = crate(h)
        pts = centers(model.source_grid,model.model!=0)
        same(np.ptp(pts,axis=0)+model.source_grid.spacing,[tile,tile,h],f"measured H{h}")
        place = model.spec["views"]["idle"]["placement"]
        check(place["support_center_xyz"] == [0,0,h] and place["stack_pitch_z"] == h,
              "specimen support/stack height")
        if h == step:
            check_platform(model, expected)
            official = Image.open(docs/"assets/wooden_crate/idle.png")
        if h == 14:
            baseline = old_crate(model.spec)
            same(baseline.materials,model.model,"old crate material reconstruction")
            same(baseline.parts,model.part_ids,"old crate part reconstruction")
        for i,d in enumerate(DIRECTIONS):
            if h == step:
                w = model.spec["cell"]
                im, offset = study.cell(f"lab/{h}/idle",d)
                aligned = Image.new("RGBA",(w,w))
                aligned.paste(im,tuple(np.array(offset)+model.spec["anchor"]))
                same(aligned,official.crop((i*w,0,(i+1)*w,w)), "candidate vs published native "+d)
                a, ao = study.cell(f"game/{h}/idle",d)
                b, bo = game.cell("wooden_crate/idle",d)
                same(a,b,"candidate vs game"); check(ao == bo,"game anchor")
        pitch, density, gain = game_projection.game_camera(profile,step)
        px_per_unit = density*np.cos(np.deg2rad(pitch))*gain
        check(np.isclose(h*px_per_unit, h*profile["legacy_step_px"]/step), "world step conversion")
        legacy_gain = game_projection.game_camera(profile,h)[2]
        check(np.isclose(h*px_per_unit*legacy_gain/gain,profile["legacy_step_px"]), "per-specimen fit")
        print(f"H{h} SW native/game shared: {study.cell(f'lab/{h}/idle','SW')[0].size} / "
              f"{study.cell(f'game/{h}/idle','SW')[0].size}; tread {h*px_per_unit:.1f}px")

    pillar = load(ROOT/"stone_pillar")
    places = pillar.spec["views"]
    beam_height = places["beam"]["placement"]["support_center_xyz"][2]
    factor = step/profile["legacy_source_units_per_step"]["stone_pillar"]
    check(beam_height*factor == step and pillar.spec["geometry"]["rest_dimensions_xyz"][2]*factor == 3*step,
          "calibrated beam and standing pillar")
    spots = places["fallen"]["placement"]["support_centers_xyz"]
    same(np.array(spots)*[1,1,factor], [[0,i*tile,step] for i in range(1,4)], "three world platforms")
    for atlas,prefix,pitch,density in [(study,"lab/pillar-fit",24,1.5),(game,"stone_pillar",pitch,density)]:
        score = handoff(atlas,prefix,pitch,density,spots)
        print(f"{prefix} FALLEN vs three BEAMs, minimum 8-view silhouette IoU {score:.3f}")
    print("PASS independent atlases, candidates, both character soles, crate/terrain/BEAM support")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    main(parser.parse_args().out)
