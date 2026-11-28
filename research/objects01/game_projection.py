"""Reproject the study's poses into the game tile metric at eight camera yaws."""
import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from objects.bake import DIRECTIONS, ROOT, load, pose, render_pose, write_json
from spritestack.character import read_json

ASSETS = ("wooden_crate", "treasure_chest", "boulder", "stone_pillar")
PROFILE = ROOT.parent / "docs/studies/objects01/guildward-scale.json"


def game_camera(profile, source_step):
    width, height = profile["legacy_tile_px"]
    pitch = np.rad2deg(np.arcsin(height / width))
    density = width / (np.sqrt(2) * profile["tile_model"])
    z_scale = profile["legacy_step_px"] / (source_step * density * np.cos(np.deg2rad(pitch)))
    return float(pitch), density, z_scale


def collect(model, prefix, camera_metric, entries, frames):
    """Apply the axis conversion once, after the rigid pose, before ray tracing."""
    pitch, density, z_scale = camera_metric
    scale = np.array([1, 1, z_scale])
    view = model.config["view"]
    anchor = np.array(view["camera"]["base_pivot"]) + 8
    camera = dict(view["camera"], pitch_deg=pitch, pixels_per_unit=density, base_pivot=anchor.tolist())
    target = replace(model, config={"view": dict(view, camera=camera, neutral_cell=view["neutral_cell"]+16)})
    for state, clip in model.spec["views"].items():
        entry = {d: [] for d in DIRECTIONS}
        for angle in clip["angles_deg"]:
            vol, parts, grid, _, _ = pose(model, clip, angle)
            scaled = replace(grid, origin=grid.origin*scale, spacing=grid.spacing*scale)
            for direction, frame in zip(DIRECTIONS, render_pose(target, vol, parts, scaled)):
                box = frame.getbbox()
                record = {"offset": (np.array(box[:2]) - anchor).tolist()}
                entry[direction].append(record)
                frames.append((record, frame.crop(box)))
        entries[prefix + "/" + state] = entry


def write_atlas(out, stem, entries, frames):
    width = 512
    x = y = row_height = 0
    for record, frame in frames:
        if x + frame.width > width:
            x, y, row_height = 0, y + row_height + 1, 0
        record["rect"] = [x, y, frame.width, frame.height]
        x += frame.width + 1
        row_height = max(row_height, frame.height)
    atlas = Image.new("RGBA", (width, y + row_height))
    for record, frame in frames:
        atlas.paste(frame, record["rect"][:2])
    out.mkdir(parents=True, exist_ok=True)
    atlas.save(out / (stem + ".png"))
    write_json(out / (stem + ".json"), entries)


def build(out):
    profile = read_json(PROFILE)
    entries, frames = {}, []
    for name in ASSETS:
        units = profile["legacy_source_units_per_step"].get(name, profile["step_model"])
        collect(load(ROOT / name), name, game_camera(profile, units), entries, frames)
    write_atlas(out, "game", entries, frames)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    build(parser.parse_args().out)
