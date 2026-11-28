"""Check rigid-object contact, handoff, GIF timing and an independent model-to-PNG rebuild."""
import argparse
from importlib import import_module
from pathlib import Path

import numpy as np
from PIL import Image

from objects.bake import DIRECTIONS, ROOT, bake, load, pose
from spritestack.character import load_character, read_json
from spritestack.rig import transform


def check(ok, message):
    if not ok:
        raise ValueError(message)


def same(a, b, label):
    check(np.array_equal(a, b), label)


def centers(grid, mask):
    return grid.origin + (np.argwhere(mask)[:, ::-1] + .5) * grid.spacing


def sample(grid, volume, points):
    idx = np.floor((points-grid.origin)/grid.spacing).astype(int)
    valid = ((idx >= 0) & (idx < grid.size_xyz)).all(1)
    values = np.zeros(len(points), dtype=volume.dtype)
    values[valid] = volume[tuple(idx[valid][:, ::-1].T)]
    return values


def read_frames(folder, model, quality):
    result, min_margin, total = {}, 1000, 0
    for name, spec in model.spec["views"].items():
        moving = "durations_ms" in spec
        metadata = read_json(folder / ("metadata.json" if name == "idle" else name + ".json"))
        layout = metadata["animations"][name] if moving else metadata["neutral"]
        order = layout["rows"] if moving else layout["directions"]
        same(order, list(DIRECTIONS), name + " direction order")
        check(metadata["camera_yaw_deg"] == DIRECTIONS, name + " camera orientation")
        same(layout["anchor"], model.spec["anchor"], name + " anchor")
        w, h = layout["cell"]
        n = len(spec["angles_deg"])
        sheet = Image.open(folder / (name + ".png")).convert("RGBA")
        check(sheet.size == ((w*n, h*8) if moving else (w*8,h)), name + " dimensions")
        gif = Image.open(folder / (name + ".gif"))
        check(gif.n_frames == n, name + " GIF frame count")
        check((gif.info.get("loop") == 0) == spec.get("loop",False), name + " GIF loop")
        if moving:
            check(layout["columns"] == n and layout["loop"] == spec["loop"], name + " transport")
            same(layout["durations_ms"], spec["durations_ms"], name + " timing")
        frames = []
        for f in range(n):
            gif.seek(f)
            panel = gif.convert("RGB")
            check(panel.size == (4*w,2*h), name + " GIF contact sheet")
            if moving:
                check(gif.info["duration"] == layout["durations_ms"][f], name + " GIF time")
            row = []
            for d in range(8):
                x, y = (f*w,d*h) if moving else (d*w,0)
                image = sheet.crop((x,y,x+w,y+h))
                box = image.getbbox()
                check(box is not None, name + " empty cell")
                margin = min(box[0],box[1],w-box[2],h-box[3])
                min_margin = min(min_margin, margin)
                check(margin >= quality["minimum_margin_px"], f"{name}/{order[d]}/{f} margin {margin}")
                matte = Image.new("RGB", image.size, "#d3c8b3")
                matte.paste(image, mask=image.getchannel("A"))
                gx, gy = d%4*w, d//4*h
                same(matte, panel.crop((gx,gy,gx+w,gy+h)), f"{name} PNG/GIF {order[d]}/{f}")
                row.append(np.asarray(image))
            frames.append(row)
            total += 8
        result[name] = frames
    return result, total, min_margin


def check_art(model, quality, frames):
    for rule in quality["visible"]:
        palette = model.palette[list(model.spec["palette"]).index(rule["material"]) + 1]
        for d in rule.get("directions", DIRECTIONS):
            image = frames[rule["state"]][0][list(DIRECTIONS).index(d)]
            pixels = sum(np.all(image[:,:,:3] == rgb, axis=2).sum() for rgb in palette)
            check(pixels >= rule["min_pixels"], f"{rule['material']} {d}: {pixels}px")
    for motion, (start,end) in quality.get("endpoints", {}).items():
        same(frames[motion][0], frames[start][0], motion + " first frame")
        same(frames[motion][-1], frames[end][0], motion + " last frame")


def check_support(model, quality):
    for name in quality.get("support_states", []):
        spec = model.spec["views"][name]
        volume, _, grid, _, _ = pose(model, spec, spec["angles_deg"][0])
        place = spec["placement"]
        supports = place.get("support_centers_xyz") or [place["support_center_xyz"]]
        for center in supports:
            # Sample both boot soles and the top centre. Test immediately above too.
            probes = np.array(center) + np.array([[0,0,-.25],[-2,1,-.25],[2,-1,-.25]])
            check(np.all(sample(grid,volume,probes) > 0), name + " foot support")
            check(np.all(sample(grid,volume,probes + [0,0,.5]) == 0), name + " floor height")
        if "stack_pitch_z" in place:
            check(place["stack_pitch_z"] == supports[0][2] == model.spec["geometry"]["rest_dimensions_xyz"][2],
                  name + " stack contact")


def check_platform(model, rule):
    state = model.spec["views"][rule["state"]]
    placement = state["placement"]
    center = np.array(placement["support_center_xyz"])
    half = np.array(placement["support_half_extents_xy"])
    geometry = model.spec["geometry"]
    profile = read_json(ROOT.parent / rule["scale_profile"])
    pitch = placement["stack_pitch_z"]
    check(pitch == center[2] - geometry["floor_z"] == placement["game_support_steps"] * profile["step_model"],
          "platform, terrain and stack must have the same rise")
    same(placement["occupied_tiles"], [[0, 0]], "single-cell occupancy")
    check(geometry["tile_pitch_model"] == profile["tile_model"] and
          np.all(np.abs(center[:2]) + half <= profile["tile_model"]/2), "support outside footprint")
    vol, _, grid, _, _ = pose(model, state, 0)
    points = centers(grid, vol != 0)
    check(points[:, 2].min() - grid.spacing[2]/2 == geometry["floor_z"], "platform off floor")
    # Sample the complete upper face at voxel centres, including both sole patches.
    xs, ys = (np.arange(-radius + dx/2, radius, dx) for radius, dx in zip(half, grid.spacing[:2]))
    xy = np.array(np.meshgrid(xs, ys)).reshape(2, -1).T + center[:2]
    probes = np.column_stack((xy, np.full(len(xy), center[2] - grid.spacing[2]/2)))
    check(sample(grid, vol, probes).all() and not sample(grid, vol, probes+[0,0,grid.spacing[2]]).any(),
          "support rectangle must be flat and clear")
    for hero in rule["standing_characters"]:
        actor = load_character(ROOT.parent / "characters" / hero / "character.json")
        for side in ("boot_L", "boot_R"):
            feet = centers(actor.source_grid, actor.part_ids == actor.parts[side])
            sole = feet[feet[:,2] == feet[:,2].min()]
            check(sole[0,2] - actor.source_grid.spacing[2]/2 == 0, hero + " foot anchor")
            check(np.all(np.abs(sole[:,:2]) + actor.source_grid.spacing[:2]/2 <= half), hero + " boot overhang")


def check_sweep(model, quality):
    joint = model.spec["rotation"]
    pivot = np.array(joint["pivot_xyz"])
    hinge = quality.get("hinge")
    rule = hinge or quality["toppling"]
    s = model.spec["views"][rule["state"]]
    points = {name: centers(model.source_grid, model.part_ids == key) for name,key in model.parts.items()}
    if hinge:
        # Both knuckles actually reach the axle, independent of pose metadata.
        axis = np.array(joint["axis_xyz"])
        for part in (hinge["fixed"],hinge["moving"]):
            radial = np.linalg.norm(np.cross(points[part]-pivot,axis), axis=1)
            check(radial.min() < .5, part + " does not meet hinge")
    else:
        check(np.allclose(np.cross(joint["axis_xyz"], [0,0,1]), joint["travel_xyz"]), "fall direction")
        angles = np.array(s["angles_deg"])
        speeds = np.diff(angles) / s["durations_ms"][:-1]
        check(np.all(np.diff(speeds) > 0), "fall must accelerate towards impact")
    angles = np.unique(np.r_[s["angles_deg"], np.arange(0,s["angles_deg"][-1]+1,rule["sweep_step_deg"])])
    for a in angles:
        _, _, _, matrices, _ = pose(model, s, a)
        for name, matrix in matrices.items():
            check(np.linalg.norm(transform(matrix,pivot)-pivot) < 1e-9, f"pivot drift {a}")
        if hinge:
            r, t = matrices[hinge["moving"]]
            body = points[hinge["fixed"]]
            check(np.allclose(matrices[hinge["fixed"]][0], np.eye(3)) and
                  np.allclose(matrices[hinge["fixed"]][1], 0), "case moved")
            overlap = sample(model.source_grid,model.part_ids,(body-t) @ r) == model.parts[hinge["moving"]]
            check(not np.any(overlap), f"hinge intersects fixed case at {a} degrees")
        else:
            r,t = next(iter(matrices.values()))
            extent = abs(r[2]) @ model.source_grid.spacing / 2
            floor = min((pts @ r[2]).min() for pts in points.values()) + t[2] - extent
            check(abs(floor) < 1e-8, f"topple lost floor at {a}: {floor}")
    return len(angles)


def check_roll(model, rule, frames):
    joint = model.spec["rotation"]
    check(np.allclose(np.cross(joint["axis_xyz"],[0,0,1]),joint["travel_xyz"]), "roll handedness")
    state = model.spec["views"][rule["state"]]
    angles = state["angles_deg"]
    steps = np.diff(angles + [360])
    check(angles[0] == 0 and min(steps) > 0 and max(steps) == min(steps), "roll loop phase")
    check(joint["rolling_radius_model"] > 0, "roll radius")
    same(frames[rule["state"]][0], frames[rule["start"]][0], "roll neutral")
    source = centers(model.source_grid, model.model != 0)
    for angle in angles + [360]:
        vol, _, grid, matrices, lift = pose(model, state, angle)
        r,t = next(iter(matrices.values()))
        floor = (source @ r[2]).min() + t[2] - abs(r[2]) @ model.source_grid.spacing / 2
        check(abs(floor) < 1e-8 and abs(lift) <= rule["max_support_adjustment"], "rock support")
        baked_floor = centers(grid, vol!=0)[:,2].min() - grid.spacing[2]/2
        check(0 <= baked_floor <= rule["max_floor_gap"], "rock resliced floor")
        if angle == 0:
            rest_grid, rest = grid, vol
        if angle == 360:
            check(vol.astype(bool).sum() == rest.astype(bool).sum(), "roll seam volume")
            initial = centers(rest_grid, rest!=0)
            same(sample(grid,vol,initial), sample(rest_grid,rest,initial), "roll seam material")
    for d in range(8):
        images = [f[d].tobytes() for f in frames[rule["state"]]]
        check(len(set(images)) == len(images), "unreadable roll phases " + list(DIRECTIONS)[d])


def check_module(model, rule, frames):
    views = model.spec["views"]
    full, single = views[rule["full"]], views[rule["single"]]
    beam, _, bg, _, _ = pose(model,single,single["angles_deg"][0])
    column, ids, cg, _, _ = pose(model,full,full["angles_deg"][0])
    unit = model.spec["geometry"]["module_length"]
    spots = np.array(full["placement"]["support_centers_xyz"])
    shift = spots[rule["center_index"]].copy()
    shift[2] = 0
    middle = ids == model.parts[rule["part"]]
    p = centers(cg,middle)
    check(len(p) == np.count_nonzero(beam), "module volume")
    same(sample(bg,beam,p-shift), sample(cg,column,p), "middle module materials")
    points = centers(bg,beam!=0)
    low, high = points[:,1].min()-bg.spacing[1]/2, points[:,1].max()+bg.spacing[1]/2
    for n,(_,y,z) in enumerate(spots,1):
        check(y == n*unit and z == single["placement"]["support_center_xyz"][2], "module pitch")
        check(np.allclose([y+low,y+high],[(n-.5)*unit,(n+.5)*unit]), "module joint")
    overlap = []
    for i,yaw in enumerate(DIRECTIONS.values()):
        face = Image.fromarray(frames[rule["single"]][0][i])
        assembly = Image.new("RGBA",face.size)
        offsets = np.stack((np.sin(np.deg2rad(yaw))*spots[:,1]*1.5,
                            np.cos(np.deg2rad(yaw))*spots[:,1]*1.5*np.sin(np.deg2rad(24))),axis=1)
        for xy in sorted(np.rint(offsets).astype(int),key=lambda p:p[1]):
            assembly.alpha_composite(face,tuple(xy))
        a = np.asarray(assembly)[:,:,3] > 0
        b = frames[rule["full"]][0][i][:,:,3] > 0
        overlap.append(float((a & b).sum() / (a | b).sum()))
    check(min(overlap) >= rule["min_silhouette_iou"], "FALLEN/BEAM silhouette discontinuity")
    return min(overlap)


def compare_files(folder, other):
    same(sorted(p.name for p in folder.iterdir()), sorted(p.name for p in other.iterdir()), "file list")
    for path in folder.iterdir():
        ref = other / path.name
        if path.suffix == ".json":
            check(read_json(path) == read_json(ref), path.name)
        elif path.suffix == ".gif":
            a,b = Image.open(path),Image.open(ref)
            check(a.n_frames == b.n_frames and a.info.get("loop") == b.info.get("loop"), path.name)
            for f in range(a.n_frames):
                a.seek(f); b.seek(f)
                same(a.convert("RGB"),b.convert("RGB"),path.name)
                check(a.info.get("duration") == b.info.get("duration"),path.name)
        else:
            same(Image.open(path).convert("RGBA"),Image.open(ref).convert("RGBA"),path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="fresh rebuild root")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    for config in sorted(ROOT.glob("*/quality.json")):
        folder, quality = config.parent, read_json(config)
        name = folder.name
        model = load(folder)
        rebuilt = import_module(f"objects.{name}.build_model").build(model.spec)
        same(rebuilt.materials,model.model,name + " rebuilt material slices")
        same(rebuilt.parts,model.part_ids,name + " rebuilt part slices")
        model_file = args.out / (name + ".npz")
        np.savez_compressed(model_file, slices=rebuilt.materials, parts=rebuilt.parts)
        bake(load(folder,model_file), args.out / name)
        published = ROOT.parent / "docs" / "assets" / name
        compare_files(args.out / name, published)
        frames,count,margin = read_frames(published,model,quality)
        check_art(model,quality,frames)
        check_support(model,quality)
        if "platform" in quality:
            check_platform(model,quality["platform"])
        geometry = model.spec["geometry"]
        points = centers(model.source_grid,model.model!=0)
        same(np.ptp(points,axis=0)+model.source_grid.spacing,geometry["rest_dimensions_xyz"],"rest dimensions")
        observations = []
        if "hinge" in quality or "toppling" in quality:
            observations.append(f"{check_sweep(model,quality)} sweep poses")
        if "rolling" in quality:
            check_roll(model,quality["rolling"],frames)
        if "module" in quality:
            observations.append(f"full/3-module min silhouette IoU {check_module(model,quality['module'],frames):.3f}")
        print(f"PASS {name}: {count} cells, min margin {margin}px", *observations, sep=" | ")


if __name__ == "__main__":
    main()
