"""Reproject the study's poses into the game tile metric at eight camera yaws."""
import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from objects.bake import DIRECTIONS, ROOT, load, pose, render_pose, write_json

ASSETS = ("wooden_crate", "treasure_chest", "boulder", "stone_pillar")


def build(out):
    # SW: (X-Y)*16/pitch, (X+Y)*8/pitch - Z*8/pitch. Change the
    # Z spacing AFTER posing, so hinge/rolling mechanics remain in object space.
    entries, frames = {}, []
    for name in ASSETS:
        model = load(ROOT / name)
        pitch = model.spec["geometry"]["tile_pitch_model"]
        density = 16*np.sqrt(2)/pitch
        z_scale = (8/pitch) / (density*np.cos(np.deg2rad(30)))
        scale = np.array([1, 1, z_scale])
        view = model.config["view"]
        anchor = np.array(view["camera"]["base_pivot"]) + 8
        camera = dict(view["camera"], pitch_deg=30, pixels_per_unit=density, base_pivot=anchor.tolist())
        game = replace(model, config={"view": dict(view, camera=camera, neutral_cell=view["neutral_cell"]+16)})
        for state, clip in model.spec["views"].items():
            entry = {d: [] for d in DIRECTIONS}
            for angle in clip["angles_deg"]:
                vol, parts, grid, _, _ = pose(model, clip, angle)
                scaled = replace(grid, origin=grid.origin*scale, spacing=grid.spacing*scale)
                for direction, frame in zip(DIRECTIONS, render_pose(game, vol, parts, scaled)):
                    box = frame.getbbox()
                    offset = np.array(box[:2]) - anchor
                    record = {"offset": offset.tolist()}
                    entry[direction].append(record)
                    frames.append((record, frame.crop(box)))
            entries[name + "/" + state] = entry
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
    atlas.save(out / "game.png")
    write_json(out / "game.json", entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    build(parser.parse_args().out)
