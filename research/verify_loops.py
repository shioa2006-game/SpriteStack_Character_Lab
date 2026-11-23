"""Verify the animated idle, equipment visibility and exported looping sheets and GIFs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from research.verify_character import face_contacts
from research.verify_walk import frames_of
from research.walk.compare import strip
from spritestack.character import load_character


def require(test, message):
    if not test:
        raise ValueError(message)


def verify(manifest, out, published):
    character = load_character(manifest)
    rules = json.loads(manifest.with_name("quality.json").read_bytes())
    meta = json.loads((out / "metadata.json").read_bytes())
    qa = json.loads((out / "measurements.json").read_bytes())
    joints = json.loads((out / "joints.json").read_bytes())
    neutral = meta["neutral"]
    with Image.open(out / "idle.png") as image:
        rest = image.copy()
    for mode, layout in meta["animations"].items():
        if not layout["loop"]:
            continue
        count, rows = layout["columns"], layout["rows"]
        cell, height = layout["cell"]
        require(rows == neutral["directions"] and layout["anchor"] == neutral["anchor"]
                and [cell, height] == neutral["cell"], f"{mode}: incompatible anchors or layout")
        with Image.open(out / f"{mode}.png") as sheet:
            require(sheet.mode == "RGBA" and sheet.size == (count*cell, len(rows)*height),
                    f"{mode}: sheet format")
            require(hashlib.sha256(sheet.tobytes()).hexdigest() == layout["rgba_sha256"], f"{mode}: hash")
            sprites = frames_of(sheet, cell, len(rows), count)
            if published:
                with Image.open(published / f"{mode}.png") as saved:
                    require(saved.size == sheet.size and saved.convert("RGBA").tobytes() == sheet.tobytes(),
                            f"{mode}: published pixels")
        margins = []
        for i, row in enumerate(sprites):
            if mode == "breathe":
                initial = rest.crop((i*cell, 0, (i+1)*cell, height))
                require(initial.tobytes() == row[0].tobytes(), f"{mode} {rows[i]}: first pose differs from rest")
            require(len({f.tobytes() for f in row}) == count, f"{mode} {rows[i]}: repeated pose")
            for f in row:
                require(np.isin(np.asarray(f.getchannel("A")), [0, 255]).all(), f"{mode}: alpha")
                left, top, right, bottom = f.getbbox()
                margins.append(min(left, top, cell-right, height-bottom))
        require(min(margins) >= 1, f"{mode}: clipped")
        samples = qa["visibility_px_full_solo"][mode]
        checks = [dict(feature=k, min_px=v, rows=rows) for k,v in rules["walk"]["visibility_min_px"].items()]
        for check in checks + rules.get("loop_visibility", []):
            counts = [samples[f"{d}_{f+1}"][check["feature"]][0] for d in check["rows"] for f in range(count)]
            require(min(counts) >= check["min_px"], f"{mode}: {check['feature']} visibility {min(counts)}")
        if published:
            require(json.loads((published / f"{mode}.json").read_bytes()) == {"animations": {mode: layout}},
                    f"{mode}: published playback metadata")
            ticks = 0
            with Image.open(published / f"{mode}.gif") as gif:
                require(gif.n_frames == count and gif.info.get("loop") == 0, f"{mode}: GIF loop")
                for f in range(count):
                    gif.seek(f)
                    expected = strip([sprites], f, 1).convert("RGB")
                    require(gif.size == expected.size and gif.convert("RGB").tobytes() == expected.tobytes(),
                            f"{mode}: GIF frame {f+1}")
                    ticks += gif.info["duration"]
                    require(ticks == 10*round((f+1)*100/layout["fps"]), f"{mode}: GIF timing")
        print(f"{mode}: {len(rows)} x {count} unique poses; minimum margin {min(margins)} px")

    anchors = character.config["rig"]["attachments"]
    with np.load(out / "posed_part_ids.npz", allow_pickle=False) as volumes:
        rest_ids = volumes["rest_00"]
        for i, frame in enumerate(joints["breathe"]):
            ids = volumes[f"breathe_{i:02}"]
            for foot in ("boot_R", "boot_L"):
                require(np.array_equal(rest_ids == character.parts[foot], ids == character.parts[foot]),
                        f"breathe {i+1}: {foot} shifted")
            for part, grip in anchors.items():
                hand, marker = grip["hand"], grip["marker"]
                offsets = [np.subtract(j[marker], j[hand]) for j in (joints["rest"][0], frame)]
                require(abs(np.linalg.norm(offsets[0])-np.linalg.norm(offsets[1])) < 1e-6
                        and face_contacts(ids == character.parts[part], ids == character.parts[hand]) > 0,
                        f"breathe {i+1}: {part} grip")
            for label, floor in rules["walk"]["lowest_z_at_least"].items():
                require(qa["vol_ground"][f"breathe_{i:02}"][label] >= floor, f"breathe {i+1}: {label}")
    print("breathe: feet fixed, hands in contact, gear clear of floor")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--published", type=Path)
    args = parser.parse_args()
    verify(args.character, args.out, args.published)
