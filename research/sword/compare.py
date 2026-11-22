"""Sword blade in the walk of MAREN and AZURE RONIN, before and after walk.fine.

"Before" is the walk published before walk.fine (research/sword/baseline/<name>:
walk.png, walk.json and the part atlas walk_part_ids.png of the same bake). "After" is
a --modes walk bake of each character (<after>/<name>). Outputs, per character:

    <name>_sword_before_after.gif  eight directions, before (top) and after (bottom), x3
    <name>_sword_zoom.gif          the sword area of NE, E, W and NW, before | after, x8
    <name>_sword_crops.png         the sword area of every frame, x6, before and after
                                   rows for each direction
and metrics.json. Per direction and frame, from the blade pixels (sword part pixels in a
blade color, read from the sheet and its part atlas):

    px          blade pixels
    pieces      8-connected pieces of the blade
    gaps        1 px steps along the projected blade (guard to tip) with no blade pixel
    deviation   largest distance, in px, between the blade's centre and the centre of the
                blade drawn from its build formula with 4x4 rays per pixel, per 1 px step
    width       blade pixels per px of projected length
    hand        whether a sword pixel touches a hand_R pixel

    python -m research.sword.compare --after output/sword --out research/sword/results
"""

import argparse
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.head.compare import load
from research.walk.compare import BACKGROUND, LABEL, save_gif
from spritestack.character import load_character
from spritestack.render import Renderer
from spritestack.rig import Biped, transform, unit, vec

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("maren", "azure_ronin")
BASELINE = ROOT / "research/sword/baseline"
ZOOM_DIRECTIONS = ("NE", "E", "W", "NW")


def blade_shape(name, rest):
    """The blade's build formula (characters/<name>/build_model.py) in rest coordinates:
    a test for points and the guard and tip ends of the blade."""
    hand, tip = rest["hand_R"], rest["sword_tip"]
    if name == "maren":
        axis = tip - hand
        side = unit(np.cross(axis, [0, 1, 0]))
        flat = np.cross(unit(axis), side)

        def inside(q):
            d = q - hand
            p, a, t = d @ axis / (axis @ axis), d @ side, d @ flat
            w = np.where(p < .86, .72 + .36 * p, 1.03 * np.clip((1 - p) / .14, 0, 1))
            return (p >= .1) & (p <= 1) & (np.abs(a) <= w) & (np.abs(t) <= .3)
        return inside, hand + .1 * axis, tip

    down = unit(tip - hand)
    guard = hand + .95 * down
    length = np.linalg.norm(tip - guard)
    bow = unit(vec([-1.0, 0, 0]) - down * (down @ [-1.0, 0, 0]))
    flat = np.cross(down, bow)

    def inside(q):
        local = q - guard
        s = np.clip((local @ down) / length, 0, 1)
        off = local - s[:, None] * length * down - (4 * .85 * s * (1 - s))[:, None] * bow
        a, t = off @ bow, off @ flat
        along = (local @ down) / length
        half = np.where(s < .88, .56 - .1 * s, .47 * np.clip((1 - s) / .12, 0, 1) + .05)
        return (along >= 0) & (along <= 1) & (np.abs(a) <= half) & (np.abs(t) <= .45)
    return inside, guard, tip


class Blade:
    def __init__(self, name, rig=None):
        self.character = load_character(ROOT / f"characters/{name}/character.json")
        self.rig = rig or Biped(self.character)
        config = self.character.config
        self.view = config["view"]
        camera = self.view["camera"]
        self.scale, self.pitch = camera["pixels_per_unit"], math.radians(camera["pitch_deg"])
        self.cell = self.view["render_cell"]
        self.crop = (self.cell - config["walk"]["cell"]) // 2
        self.pivot = Renderer(self.character).anchor(self.cell)
        self.inside, self.start, self.end = blade_shape(name, self.rig.rest)
        names = [material["name"] for material in config["model"]["palette"]]
        self.colors = np.concatenate([self.character.palette[names.index(m) + 1, :, :3]
                                      for m in ("blade", "blade edge")])
        self.sword, self.hand = self.character.parts["sword"], self.character.parts["hand_R"]
        self.references = {}

    def basis(self, yaw):
        theta = math.radians(yaw)
        right = vec([math.cos(theta), math.sin(theta), 0])
        forward = vec([-math.sin(theta), math.cos(theta), 0])
        eye = forward * math.cos(self.pitch) + vec([0, 0, 1]) * math.sin(self.pitch)
        up = -forward * math.sin(self.pitch) + vec([0, 0, 1]) * math.cos(self.pitch)
        return right, eye, up

    def project(self, point, yaw):
        right, _, up = self.basis(yaw)
        return np.array([self.pivot[0] + (point @ right) * self.scale - .5 - self.crop,
                         self.pivot[1] - (point @ up) * self.scale - .5 - self.crop])

    def reference(self, index, yaw):
        """Points (cell px) of the blade drawn from its formula, 4x4 rays per pixel."""
        key = (index, yaw)
        if key not in self.references:
            rotation, translation = self.rig.pose("walk", index)[1]["sword"]
            right, eye, up = self.basis(yaw)
            # Rays only in a box around the projected blade (its ends plus its width).
            ends = [transform((rotation, translation), p) for p in (self.start, self.end)]
            columns = [self.pivot[0] + (p @ right) * self.scale for p in ends]
            rows = [self.pivot[1] - (p @ up) * self.scale for p in ends]
            x0, x1 = int(min(columns)) - 4, int(max(columns)) + 5
            y0, y1 = int(min(rows)) - 4, int(max(rows)) + 5
            n = 4
            yy, xx = np.indices(((y1 - y0) * n, (x1 - x0) * n))
            origin = ((((xx + .5) / n + x0 - self.pivot[0]) / self.scale)[..., None] * right
                      + ((self.pivot[1] - (yy + .5) / n - y0) / self.scale)[..., None] * up)
            hit = np.zeros(xx.shape, bool)
            for distance in np.arange(*self.view["posed_rays"]):
                pending = ~hit
                hit[pending] = self.inside((origin[pending] + distance * eye - translation) @ rotation)
            ys, xs = np.nonzero(hit)
            self.references[key] = (np.column_stack([(xs + .5) / n + x0 - .5 - self.crop,
                                                      (ys + .5) / n + y0 - .5 - self.crop]),
                                    (rotation, translation))
        return self.references[key]

    def frame(self, index, yaw, rgb, atlas):
        points, sword = self.reference(index, yaw)
        a, b = self.project(transform(sword, self.start), yaw), self.project(transform(sword, self.end), yaw)
        mask = (atlas == self.sword) & is_color(rgb, self.colors)
        reference, length = centreline(points, a, b)
        ys, xs = np.nonzero(mask)
        line, _ = centreline(np.column_stack([xs, ys]).astype(float), a, b)
        common = [k for k in line if k in reference and 0 <= k <= length - 1]
        inner = [k for k in range(1, length - 1) if k in reference]
        swords = atlas == self.sword
        near_hand = np.zeros_like(swords)
        hands = atlas == self.hand
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near_hand |= np.roll(np.roll(hands, dy, 0), dx, 1)
        return {
            "px": int(mask.sum()),
            "pieces": pieces(mask),
            "gaps": sum(1 for k in inner if k not in line),
            "deviation": round(max((abs(line[k] - reference[k]) for k in common), default=0.0), 2),
            "width": round(float(mask.sum()) / max(float(np.linalg.norm(b - a)), 1.0), 2),
            "hand": bool((swords & near_hand).any()),
            "hand_px": int(hands.sum()),
        }

    def measure(self, folder):
        walk, frames, atlas = load(folder)
        cell = walk["cell"][0]
        result = {}
        for row, direction in enumerate(walk["rows"]):
            yaw = self.view["directions"][direction]
            result[direction] = []
            for column in range(walk["columns"]):
                rgb = np.asarray(frames[row][column])[..., :3]
                tile = atlas[row * cell:(row + 1) * cell, column * cell:(column + 1) * cell]
                result[direction].append(self.frame(column, yaw, rgb, tile))
        return result


def is_color(rgb, colors):
    return (rgb[:, :, None, :] == colors[None, None]).all(axis=-1).any(axis=-1)


def pieces(mask):
    seen = np.zeros_like(mask, bool)
    count = 0
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        count += 1
        queue = deque([(y, x)])
        seen[y, x] = True
        while queue:
            a, b = queue.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    u, v = a + dy, b + dx
                    if 0 <= u < mask.shape[0] and 0 <= v < mask.shape[1] and mask[u, v] and not seen[u, v]:
                        seen[u, v] = True
                        queue.append((u, v))
    return count


def centreline(points, a, b):
    """Per 1 px step along a -> b, the mean offset of the points across the line."""
    d = b - a
    length = np.linalg.norm(d)
    u = d / length
    n = vec([-u[1], u[0]])
    steps = np.floor((points - a) @ u).astype(int)
    offsets = (points - a) @ n
    bins = {}
    for k, off in zip(steps, offsets):
        if -1 <= k <= math.ceil(length):
            bins.setdefault(int(k), []).append(off)
    return {k: float(np.mean(v)) for k, v in bins.items()}, int(math.ceil(length))


def summary(metrics):
    """Per direction: largest deviation and pieces, total gaps, mean px and width, frames
    without hand contact."""
    rows = {}
    for direction, frames in metrics.items():
        rows[direction] = {
            "deviation": max(f["deviation"] for f in frames),
            "pieces": max(f["pieces"] for f in frames),
            "gaps": sum(f["gaps"] for f in frames),
            "px": round(sum(f["px"] for f in frames) / len(frames), 1),
            "width": round(sum(f["width"] for f in frames) / len(frames), 2),
            "no_hand": sum(1 for f in frames if not f["hand"]),
            "hand_px": round(sum(f["hand_px"] for f in frames) / len(frames), 1),
        }
    return rows


def sword_box(atlases, part_id, walk, row, pad=3):
    """One box (cell px) around the sword in every frame of a direction, both versions."""
    cell = walk["cell"][0]
    boxes = []
    for atlas in atlases:
        tile = atlas[row * cell:(row + 1) * cell]
        ys, xs = np.nonzero(tile == part_id)
        if len(xs):
            xs = xs % cell
            boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
    x0 = max(min(b[0] for b in boxes) - pad, 0)
    y0 = max(min(b[1] for b in boxes) - pad, 0)
    x1 = min(max(b[2] for b in boxes) + pad + 1, cell)
    y1 = min(max(b[3] for b in boxes) + pad + 1, cell)
    return x0, y0, x1, y1


def tile(frame, box, scale):
    picture = Image.new("RGBA", frame.size, BACKGROUND)
    picture.alpha_composite(frame)
    x0, y0, x1, y1 = box
    return picture.crop(box).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)


def crops(path, walk, versions, boxes, scale=6):
    columns = walk["columns"]
    label = 54
    rows = [row for row, direction in enumerate(walk["rows"])]
    width = max(b[2] - b[0] for b in boxes.values()) * scale
    height = sum((boxes[r][3] - boxes[r][1]) * scale + 4 for r in rows) * len(versions) + 10 * len(rows)
    canvas = Image.new("RGB", (label + columns * (width + 4), height), (30, 30, 34))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for row in rows:
        box = boxes[row]
        for name, frames in versions:
            for column in range(columns):
                canvas.paste(tile(frames[row][column], box, scale).convert("RGB"),
                             (label + column * (width + 4), y))
            draw.text((6, y + 6), f"{walk['rows'][row]}\n{name}", fill=LABEL)
            y += (box[3] - box[1]) * scale + 4
        y += 10
    canvas.save(path, optimize=True)


def zoom_gif(path, walk, before, after, boxes, scale=8):
    rows = [walk["rows"].index(d) for d in ZOOM_DIRECTIONS]
    gap, label = 6, 16
    widths = [(boxes[r][2] - boxes[r][0]) * scale for r in rows]
    height = max((boxes[r][3] - boxes[r][1]) * scale for r in rows)
    pictures = []
    for column in range(walk["columns"]):
        canvas = Image.new("RGB", (sum(2 * w + 3 * gap for w in widths), height + label), (30, 30, 34))
        draw = ImageDraw.Draw(canvas)
        x = 0
        for row, width in zip(rows, widths):
            box = boxes[row]
            draw.text((x + 2, 2), f"{walk['rows'][row]} before | after", fill=LABEL)
            canvas.paste(tile(before[row][column], box, scale).convert("RGB"), (x, label))
            canvas.paste(tile(after[row][column], box, scale).convert("RGB"), (x + width + gap, label))
            x += 2 * width + 3 * gap
        pictures.append(canvas.quantize(colors=255, dither=Image.NONE))
    pictures[0].save(path, save_all=True, append_images=pictures[1:], duration=round(1000 / walk["fps"]),
                     loop=0, optimize=False, disposal=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--after", type=Path, required=True,
                        help="folder with one --modes walk bake per character (<folder>/<name>)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--characters", nargs="+", default=list(NAMES))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for name in args.characters:
        blade = Blade(name)
        walk, before, before_atlas = load(BASELINE / name)
        _, after, after_atlas = load(args.after / name)
        save_gif(args.out / f"{name}_sword_before_after.gif", [before, after], walk["fps"], 3)
        boxes = {row: sword_box([before_atlas, after_atlas], blade.sword, walk, row)
                 for row in range(len(walk["rows"]))}
        zoom_gif(args.out / f"{name}_sword_zoom.gif", walk, before, after, boxes)
        crops(args.out / f"{name}_sword_crops.png", walk, [("before", before), ("after", after)], boxes)
        before_metrics, after_metrics = blade.measure(BASELINE / name), blade.measure(args.after / name)
        metrics[name] = {
            "walk_fine": blade.character.config["walk"].get("fine"),
            "summary": {"before": summary(before_metrics), "after": summary(after_metrics)},
            "frames": {"before": before_metrics, "after": after_metrics},
        }
        print(f"{name}: figures written", flush=True)
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
