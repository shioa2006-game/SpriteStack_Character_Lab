"""Package verified static and animated bakes as sheets, per-motion JSON and real-time GIFs."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from research.verify_walk import frames_of
from research.walk.compare import strip


def export(neutral, animated, out):
    rest = json.loads((neutral / "metadata.json").read_bytes())
    meta = json.loads((animated / "metadata.json").read_bytes())
    if rest["animations"] or rest["neutral"] != meta["neutral"] or rest["camera"] != meta["camera"]:
        raise ValueError("neutral and animation cameras or layouts differ")
    with Image.open(neutral / "idle.png") as still, Image.open(animated / "idle.png") as other:
        if still.size != other.size or still.tobytes() != other.tobytes():
            raise ValueError("the two bakes have different neutral poses")
    out.mkdir(exist_ok=False, parents=True)
    for filename in ("metadata.json", "idle.png"):
        shutil.copyfile(neutral / filename, out / filename)
    preview = {"camera": rest["camera"], "clips": {}}
    for mode, layout in meta["animations"].items():
        if not layout["loop"]:
            continue
        cell, height = layout["cell"]
        source = animated / f"{mode}.png"
        with Image.open(source) as sheet:
            if (cell != height or sheet.size != (cell * layout["columns"], height * len(layout["rows"]))
                    or hashlib.sha256(sheet.tobytes()).hexdigest() != layout["rgba_sha256"]):
                raise ValueError(f"{mode} sheet differs from its metadata")
            rows = frames_of(sheet, cell, len(layout["rows"]), layout["columns"])
        pics = [strip([rows], i, 1).convert("RGB") for i in range(layout["columns"])]
        # GIF time is counted in centiseconds. Round cumulative boundaries to preserve cycle time.
        ticks = [round(i * 100 / layout["fps"]) for i in range(len(pics)+1)]
        pics[0].save(out / f"{mode}.gif", save_all=True, append_images=pics[1:], loop=0,
                     duration=[10*(b-a) for a, b in zip(ticks, ticks[1:])], disposal=1)
        shutil.copyfile(source, out / source.name)
        (out / f"{mode}.json").write_text(json.dumps({"animations": {mode: layout}}, indent=2)+"\n",
                                           encoding="utf-8")
        keys = ("rows", "columns", "cell", "anchor", "fps", "suggested_forward_per_frame_model_units")
        playback = {k: layout[k] for k in keys if k in layout}
        if "contact" in layout:
            playback["stance"] = layout["contact"]["inclusive_stance_cyclic"]
        preview["clips"][mode] = playback
    # A classic script can be loaded alongside local PNGs even when the page is opened from disk.
    (out / "preview.js").write_text(
        '"use strict";\nwindow.spriteStackLayouts ??= {};\n'
        'window.spriteStackLayouts[new URL(".", document.currentScript.src).href] = '
        + json.dumps(preview, indent=2) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("neutral", "animated", "out"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    args = parser.parse_args()
    export(args.neutral, args.animated, args.out)
