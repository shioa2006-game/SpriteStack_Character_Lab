"""Compare two complete attack bakes at their recorded anchors and elapsed times."""

import argparse
import csv
import hashlib
import json
import math
import tempfile
from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate, pairwise
from pathlib import Path

from PIL import Image, ImageDraw

from research.attack.trajectory_plot import plot_trajectory
from research.maren_slash.compare import paste_tile


DIRECTIONS = ("S", "SW", "W", "NW", "N", "NE", "E", "SE")
VERSIONS = ("before", "after")
FLOOR = "#afb9a7"
PAPER = "#f6f3ec"
INK = "#283b39"


@dataclass
class Bake:
    sheet: Image.Image
    layout: dict
    joints: list
    bounds: list
    events: list

    @classmethod
    def read(cls, folder):
        try:
            layout = json.loads((folder / "metadata.json").read_bytes())["animations"]["attack"]
            joints = json.loads((folder / "joints.json").read_bytes())["attack"]
            n = layout["columns"]
            if type(n) is not int or n <= 0:
                raise ValueError("columns must be a positive integer")
            w, h = layout["cell"]
            ax, ay = layout["anchor"]
            if not all(type(v) is int for v in (w, h, ax, ay)) or not (0 <= ax < w and 0 <= ay < h):
                raise ValueError("invalid cell or anchor outside cell")
            rows = layout["rows"]
            if not isinstance(rows, list) or sorted(rows) != sorted(DIRECTIONS):
                raise ValueError("rows must contain each compass direction once")
            phases, times = layout["phase_names"], layout["durations_ms"]
            if not all(isinstance(v, list) and len(v) == n for v in (joints, phases, times)):
                raise ValueError("joints, phase_names and durations_ms must match columns")
            if not all(isinstance(p, str) and p for p in phases):
                raise ValueError("expected nonempty phase names")
            if not all(type(t) is int and t > 0 for t in times):
                raise ValueError("durations_ms must contain positive integers")
            bounds = list(accumulate(times, initial=0))
            events = [[] for _ in times]
            recorded = layout.get("events", [])
            if not isinstance(recorded, list):
                raise ValueError("events must be a list")
            for event in recorded:
                i = event["frame"]
                if type(i) is not int or not 0 <= i < n or event["time_ms"] != bounds[i]:
                    raise ValueError("event frame/time_ms differs from frame boundaries")
                if not isinstance(event["name"], str) or not event["name"]:
                    raise ValueError("invalid event name")
                events[i].append(event["name"])
            for frame, pose in enumerate(joints, 1):
                if not isinstance(pose, dict):
                    raise ValueError(f"F{frame}: expected a marker dictionary")
                for marker, point in pose.items():
                    if point is None:
                        continue
                    if (not isinstance(point, list) or len(point) != 3
                            or not all(type(v) in (int, float) and math.isfinite(v) for v in point)):
                        raise ValueError(f"F{frame} {marker}: expected finite XYZ or null")
            with Image.open(folder / "attack.png") as source:
                if source.mode != "RGBA":
                    raise ValueError("attack.png must be RGBA")
                if source.size != (w * n, h * len(DIRECTIONS)):
                    raise ValueError("attack.png dimensions differ from cell, rows or columns")
                sheet = source.convert("RGBA")
            if "rgba_sha256" in layout and hashlib.sha256(sheet.tobytes()).hexdigest() != layout["rgba_sha256"]:
                raise ValueError("attack.png differs from rgba_sha256")
            return cls(sheet, layout, joints, bounds, events)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise ValueError(f"{folder}: {exc}") from exc

    def frame_at(self, ms):
        return min(len(self.joints) - 1, bisect_right(self.bounds, ms) - 1)

    def markers(self):
        return {name for pose in self.joints for name, xyz in pose.items() if xyz is not None}


def geometry(bakes):
    """Union of the two pixel rectangles, measured from their respective floor anchors."""
    anchors = [b.layout["anchor"] for b in bakes]
    cells = [b.layout["cell"] for b in bakes]
    anchor = tuple(map(max, zip(*anchors)))
    size = tuple(anchor[k] + max(c[k] - a[k] for c, a in zip(cells, anchors)) for k in (0, 1))
    return size, anchor


def sprite(page, bake, direction, frame, xy, anchor):
    x, y = (p + a - orig for p, a, orig in zip(xy, anchor, bake.layout["anchor"]))
    paste_tile(page, (bake.sheet, bake.layout), direction, frame, x, y)


def timeline(bakes):
    boundaries = sorted(set().union(*(b.bounds for b in bakes)))
    for start, end in pairwise(boundaries):
        # GIF stores centiseconds. Round absolute boundaries so the error does not accumulate.
        ticks = (end + 5) // 10 - (start + 5) // 10
        if ticks:
            yield start, ticks * 10


def comparison_gif(bakes, out):
    (w, h), anchor = geometry(bakes)
    label = 85
    frames, durations = [], []
    for start, duration in timeline(bakes):
        page = Image.new("RGB", (label + 8 * w, 20 + 2 * h), FLOOR)
        draw = ImageDraw.Draw(page)
        draw.rectangle((0, 0, page.width, 19), fill=PAPER)
        for j, direction in enumerate(DIRECTIONS):
            draw.text((label + (j + .5) * w, 10), direction, fill=INK, anchor="mm")
        for row, bake in enumerate(bakes):
            frame = bake.frame_at(start)
            top = 20 + row * h
            state = " (held)" if start >= bake.bounds[-1] else ""
            draw.text((3, top + h // 2), f"{VERSIONS[row]} F{frame+1}{state}", fill=INK, anchor="lm")
            for col, direction in enumerate(DIRECTIONS):
                sprite(page, bake, direction, frame, (label + col * w, top), anchor)
        frames.append(page)
        durations.append(duration)
    if not frames:
        raise ValueError("clip is shorter than one representable GIF interval")
    frames[0].save(out, save_all=True, append_images=frames[1:], loop=0, duration=durations, disposal=1)


def pose_selection(bakes, frames, phases):
    """A column can pair different frame numbers or phase names across revisions."""
    if not frames and not phases:
        return [
            tuple(b.frame_at(t) for b in bakes)
            for t in sorted(set().union(*(b.bounds[:-1] for b in bakes)))]
    result = []
    for token in frames or phases:
        names = token.split("=")
        if len(names) == 1:
            names *= 2
        if len(names) != 2:
            raise ValueError(f"invalid frame/phase pair: {token}")
        pair = []
        for version, bake, name in zip(VERSIONS, bakes, names):
            if frames:
                index = int(name) - 1
                if not 0 <= index < len(bake.joints):
                    raise ValueError(f"{version}: frame {name} outside clip")
            else:
                phase_names = bake.layout["phase_names"]
                if phase_names.count(name) != 1:
                    raise ValueError(f"{version}: phase {name!r} missing or ambiguous; use --frames")
                index = phase_names.index(name)
            pair.append(index)
        result.append(tuple(pair))
    return result


def marker_pair(token, available):
    names = token.split("=")
    if len(names) == 1:
        if token in available[0] or token in available[1]:
            return (token, token)
    elif len(names) == 2 and all(name in choices for name, choices in zip(names, available)):
        return tuple(names)
    raise ValueError(f"unknown marker or invalid before=after pair: {token!r}; "
                     f"available markers: {sorted(set.union(*available))}")


def pose_sheet(bakes, pairs, directions, out):
    (w, h), anchor = geometry(bakes)
    gutter = 85
    labels = [[f"F{i+1}  {b.layout['phase_names'][i]}" for b, i in zip(bakes, pair)] for pair in pairs]
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [max(w, math.ceil(max(measure.textlength(s) for s in col)) + 8) for col in labels]
    page = Image.new("RGB", (gutter + sum(widths), len(directions) * 2 * (h + 20)), PAPER)
    draw = ImageDraw.Draw(page)
    for row, direction in enumerate(directions):
        for version, bake in enumerate(bakes):
            y = (2 * row + version) * (h + 20)
            draw.text((4, y + 20 + h // 2), f"{direction} / {VERSIONS[version]}", fill=INK, anchor="lm")
            x = gutter
            for pair, names, width in zip(pairs, labels, widths):
                draw.text((x + width // 2, y + 10), names[version], fill=INK, anchor="mm")
                draw.rectangle((x, y+20, x+width-1, y+19+h), fill=FLOOR)
                sprite(page, bake, direction, pair[version], (x + (width-w)//2, y+20), anchor)
                x += width
    page.save(out)


def difference(point, base):
    if point is None or base is None:
        return (None,) * 3
    return tuple(a - b for a, b in zip(point, base))


def coordinates(bakes, markers, relative_to, out):
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("version", "frame", "start_ms", "duration_ms", "phase", "events", "marker",
                         "x", "y", "z", "dx", "dy", "dz", "relative_to", "relative_x", "relative_y", "relative_z"))
        for index, (version, bake) in enumerate(zip(VERSIONS, bakes)):
            previous = {}
            base = relative_to[index]
            names = [pair[index] for pair in markers]
            for i, pose in enumerate(bake.joints):
                for marker in names:
                    xyz = pose.get(marker)
                    writer.writerow((version, i+1, bake.bounds[i], bake.layout["durations_ms"][i],
                                     bake.layout["phase_names"][i], "|".join(bake.events[i]), marker,
                                     *(xyz or (None,) * 3), *difference(xyz, previous.get(marker)),
                                     base, *difference(xyz, pose.get(base))))
                previous = pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "out"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--markers", nargs="+", required=True, help="CSV markers (name or before=after); first is plotted")
    parser.add_argument("--relative-to", help="also export marker minus this joint (name or before=after)")
    parser.add_argument("--directions", choices=DIRECTIONS, nargs="+", default=DIRECTIONS, help="rows in poses.png")
    select = parser.add_mutually_exclusive_group()
    select.add_argument("--frames", nargs="+", help="1-based columns, e.g. 4 5 6 or 4=3")
    select.add_argument("--phases", nargs="+", help="unique phase names; use old=new if renamed")
    parser.add_argument("--front", action="store_true", help="add X/Z front view to the side and top plots")
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError(f"output already exists: {args.out}")
        bakes = [Bake.read(folder) for folder in (args.before, args.after)]
        available = [b.markers() for b in bakes]
        markers = [marker_pair(token, available) for token in args.markers]
        relative_to = marker_pair(args.relative_to, available) if args.relative_to else (None, None)
        pairs = pose_selection(bakes, args.frames, args.phases)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.out.parent) as tmp:
            result = Path(tmp) / "result"
            result.mkdir()
            comparison_gif(bakes, result / "comparison.gif")
            pose_sheet(bakes, pairs, args.directions, result / "poses.png")
            coordinates(bakes, markers, relative_to, result / "trajectory.csv")
            plot_trajectory(bakes, markers[0], pairs, args.front, result / "trajectory.png")
            result.rename(args.out)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
