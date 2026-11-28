"""Model-space projections of discrete attack markers. Distances use model units."""

import math

from PIL import Image, ImageDraw, ImageFont


COLORS = ("#a94a32", "#226284")
CONTEXT = ("#d9bfb3", "#a7c4cd")
INK = "#273938"
PAPER = "#faf8f2"
FONT = ImageFont.load_default(size=13)


def runs(points):
    """Only consecutive observations form a path. A single observation is still a point."""
    segment = []
    for point in points:
        if point is None:
            if segment:
                yield segment
            segment = []
        else:
            segment.append(point)
    if segment:
        yield segment


def projection(draw, series, highlights, event_frames, origin, axes, title):
    horizontal, vertical = axes
    x0, y0 = origin
    left, top = x0 + 59, y0 + 40
    size = 255
    points = [p for path in series for p in path if p is not None]
    xs = [p[horizontal] for p in points]
    ys = [p[vertical] for p in points]
    span = 1.16 * max(max(xs)-min(xs), max(ys)-min(ys), 1.0)
    low = (max(xs)+min(xs)-span)/2
    high = (max(ys)+min(ys)+span)/2

    def project(p):
        return left + (p[horizontal]-low)*size/span, top + (high-p[vertical])*size/span

    draw.text((left, y0+8), title, fill=INK, font=FONT)
    for i in range(5):
        offset = i * size / 4
        x, y = left + offset, top + offset
        draw.line((x, top, x, top+size), fill="#d7d9ce")
        draw.line((left, y, left+size, y), fill="#d7d9ce")
        draw.text((x, top+size+4), f"{low+i*span/4:.2f}", anchor="mt", fill=INK)
        draw.text((left-5, y), f"{high-i*span/4:.2f}", anchor="rm", fill=INK)
    # Keep the complete path for orientation. Emphasize only adjacent key poses.
    for version, path in enumerate(series):
        for segment in runs(path):
            if len(segment) > 1:
                draw.line([project(p) for p in segment], fill=CONTEXT[version], width=2)
    occupied = []
    for version, path in enumerate(series):
        selected = [point if i in highlights[version] else None for i, point in enumerate(path)]
        for segment in runs(selected):
            line = [project(point) for point in segment]
            if len(line) > 1:
                draw.line(line, fill=COLORS[version], width=4 if version == 0 else 2)
        for frame, point in enumerate(path):
            if point is None:
                continue
            x, y = project(point)
            r = 4 if version == 0 else 2
            color = COLORS[version] if frame in highlights[version] else CONTEXT[version]
            draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
            if frame in event_frames[version]:
                r = 9 if version == 0 else 7
                draw.ellipse((x-r, y-r, x+r, y+r), outline=color, width=2)
            if frame not in highlights[version]:
                continue
            # Separate labels for identical endpoints and near-coincident revisions.
            label = str(frame+1)
            for step in range(30):
                angle = (step % 8) * math.pi/4
                radius = 13 + (step//8) * 10
                tx, ty = x + radius*math.cos(angle), y - radius*math.sin(angle)
                box = draw.textbbox((tx, ty), label, anchor="mm")
                if (box[0] < left or box[1] < top or box[2] > left+size or box[3] > top+size
                        or any(box[0]-2 < b[2] and box[2]+2 > b[0] and box[1]-2 < b[3]
                               and box[3]+2 > b[1] for b in occupied)):
                    continue
                draw.line((x, y, tx, ty), fill=color)
                draw.text((tx, ty), label, fill=color, anchor="mm", stroke_width=1, stroke_fill=PAPER)
                occupied.append(box)
                break


def plot_trajectory(bakes, markers, pairs, front, out):
    views = [((1, 2), "Side   Y forward / Z up"), ((1, 0), "Top   Y forward / X left")]
    if front:
        views.append(((0, 2), "Front   X left / Z up"))
    series = [[pose.get(marker) for pose in b.joints] for b, marker in zip(bakes, markers)]
    events = [{i for i, names in enumerate(b.events) if names} for b in bakes]
    highlights = [set(column) | event for column, event in zip(zip(*pairs), events)]
    legend = []
    for version, bake in enumerate(bakes):
        labels = []
        for i in sorted(highlights[version]):
            phase = bake.layout["phase_names"][i]
            text = f"F{i+1}   {bake.bounds[i]} ms   {phase}"
            if bake.events[i]:
                text += "   [" + ", ".join(bake.events[i]) + "]"
            if series[version][i] is None:
                text += "   (absent)"
            labels.append(text)
        legend.append(labels)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    col_w = max(170, math.ceil(max(measure.textlength(s, font=FONT) for col in legend for s in col)) + 24)
    title = " / ".join(dict.fromkeys(markers)) + "   |   model units   |   ring = event   |   pale = other frames"
    width = max(len(views)*350, 2*col_w, math.ceil(measure.textlength(title, font=FONT))+24)
    page = Image.new("RGB", (width, 385 + max(map(len, legend))*19), PAPER)
    draw = ImageDraw.Draw(page)
    draw.text((12, 8), title, fill=INK, font=FONT)
    for col, (axes, heading) in enumerate(views):
        projection(draw, series, highlights, events, (350*col, 28), axes, heading)
    for version, col in enumerate(legend):
        x = 12 + version*col_w
        draw.text((x, 354), ("Before", "After")[version], fill=COLORS[version], font=FONT)
        for i, line in enumerate(col):
            draw.text((x, 376+i*19), line, fill=INK, font=FONT)
    page.save(out)
