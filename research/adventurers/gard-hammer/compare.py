"""Build matched sprite comparisons and export the baked rig markers in model units."""

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAPER = "#f5f2e9"
FLOOR = "#afb9a7"
INK = "#293b35"
FONT = ImageFont.load_default(size=15)
PHASES = ("Wind-up", "Swing", "Impact", "Follow-through")
MARKERS = ("hammer_head", "hand_R", "elbow_R", "shoulder_R", "pelvis", "toe_R", "toe_L")


class Bake:
    def __init__(self, path):
        self.layout = json.loads((path / "metadata.json").read_bytes())["animations"]["attack"]
        self.joints = json.loads((path / "joints.json").read_bytes())["attack"]
        with Image.open(path / "attack.png") as sheet:
            self.sheet = sheet.convert("RGBA")

    def tile(self, row, frame, extent, anchor):
        size, height = self.layout["cell"]
        region = self.sheet.crop((frame*size, row*height, (frame+1)*size, (row+1)*height))
        ax, ay = self.layout["anchor"]
        panel = Image.new("RGB", extent, FLOOR)
        panel.paste(region, (anchor[0]-ax, anchor[1]-ay), region)
        return panel


def sprite_comparisons(bakes, out):
    old, new = bakes
    rows = new.layout["rows"]
    times = new.layout["durations_ms"]
    if rows != old.layout["rows"] or times != old.layout["durations_ms"]:
        raise ValueError("synchronized comparison needs matching direction order and frame durations")
    w, h = new.layout["cell"]
    anchor = new.layout["anchor"]
    frames = []
    for frame in range(len(times)):
        page = Image.new("RGB", (80+len(rows)*w, 28+2*h), PAPER)
        draw = ImageDraw.Draw(page)
        for row, direction in enumerate(rows):
            x = 80 + w*row
            draw.text((x+w//2, 14), direction, anchor="mm", fill=INK, font=FONT)
            for version, bake in enumerate(bakes):
                page.paste(bake.tile(row, frame, (w,h), anchor), (x,28+version*h))
        for version, name in enumerate(("Before", "After")):
            draw.text((12,28+h//2+version*h), name, anchor="lm", fill=INK, font=FONT)
        frames.append(page)
    frames[0].save(out/"comparison.gif", save_all=True, append_images=frames[1:],
                   loop=0, duration=times, disposal=1)

    # Fixed 2x magnification and one anchor even for the shorter original cell.
    tile_w, tile_h = w*2, 138
    gutter = 104
    page = Image.new("RGB", (gutter+4*(tile_w+2), 40+3*(2*tile_h+10)), PAPER)
    draw = ImageDraw.Draw(page)
    for col, name in enumerate(PHASES):
        draw.text((gutter+col*(tile_w+2)+tile_w//2,20), f"F{col+4}  {name}",
                  anchor="mm", fill=INK, font=FONT)
    for group, direction in enumerate(("E", "S", "NW")):
        for version, bake in enumerate(bakes):
            y = 40 + group*(2*tile_h+10) + version*(tile_h+2)
            draw.text((10,y+tile_h//2), direction+" / "+("Before","After")[version],
                      anchor="lm", fill=INK, font=FONT)
            for col in range(4):
                tile = bake.tile(rows.index(direction), col+3, (w,tile_h//2), (w//2,63))
                page.paste(tile.resize((tile_w,tile_h), Image.Resampling.NEAREST), (gutter+col*(tile_w+2),y))
    page.save(out/"poses.png", optimize=True)


def trajectory(bakes, out):
    with (out/"trajectory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["version","frame","start_ms"] + [f"{marker}_{axis}" for marker in MARKERS for axis in "xyz"])
        for name, bake in zip(("before","after"), bakes):
            ms = 0
            for frame, joints in enumerate(bake.joints):
                writer.writerow([name, frame+1, ms] + [round(v,6) for marker in MARKERS for v in joints[marker]])
                ms += bake.layout["durations_ms"][frame]

    page = Image.new("RGB", (840,295), PAPER)
    draw = ImageDraw.Draw(page)
    for panel, (label, axis, bottom) in enumerate((("Side  /  height Z",2,5), ("Top  /  lateral X",0,-25))):
        left, floor = 54+panel*420, 235
        def point(y, other):
            return left+(y+10)*8, floor-(other-bottom)*6
        draw.text((left,12), label, font=FONT, fill=INK)
        for y in (-10,0,10,20,30):
            x, _ = point(y,bottom)
            draw.line((x,48,x,floor),fill="#d5d7ca")
            draw.text((x,floor+5),str(y),anchor="mt",fill=INK)
        for height in range(bottom,bottom+31,5):
            _, sy = point(0,height)
            draw.text((left-10,sy),str(height),anchor="rm",fill=INK)
            draw.line((left,sy,left+320,sy),fill="#d5d7ca")
        for bake, color in zip(bakes, ("#8b6354","#236965")):
            markers = [j["hammer_head"] for j in bake.joints[3:7]]
            coords = [point(v[1],v[axis]) for v in markers]
            draw.line(coords, fill=color, width=3)
            for index,(x,y) in enumerate(coords):
                draw.ellipse((x-3,y-3,x+3,y+3),fill=color)
                if bake is bakes[1]:
                    draw.text((x+3,y-14), f"F{index+4}", fill=color)
                elif index == 2:
                    draw.text((x+7,y-1), "F6", fill=color)
                elif index == 3:
                    draw.text((x-16,y+6), "F7", fill=color)
        draw.text((left+160,264),"Forward +Y  (model units)",anchor="mm",fill=INK,font=FONT)
    draw.text((222,13),"Before",fill="#8b6354",font=FONT)
    draw.text((287,13),"After",fill="#236965",font=FONT)
    page.save(out/"trajectory.png", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before","after","out"):
        parser.add_argument(name,type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    pair = (Bake(args.before),Bake(args.after))
    sprite_comparisons(pair,args.out)
    trajectory(pair,args.out)
