"""Draw 3D and camera-projected motion paths from the measured poses."""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from research.overhead.analyze import SUBSTEPS


COLORS = (("#a7aec2", "#e4a276"), ("#7ee2bd", "#7bc9ff"))


def camera_projection(yaw, pitch):
    yaw = math.radians(yaw)
    pitch = math.radians(pitch)
    forward = np.array([-math.sin(yaw), math.cos(yaw), 0])
    right = np.array([math.cos(yaw), math.sin(yaw), 0])
    up = -forward * math.sin(pitch) + [0, 0, math.cos(pitch)]
    return np.stack((right, up), axis=1)


def plot_paths(path, name, camera, directions, measurements, visibility):
    image = Image.new("RGB", (1440, 924), "#111b2b")
    draw = ImageDraw.Draw(image)
    small, regular, heading = (ImageFont.load_default(size=size) for size in (12, 16, 25))
    draw.text((22, 14), f"{name.upper()}   /   SWORD AND RIGHT HAND PATHS",
              font=heading, fill="#edf1f5")
    legends = (("Before: hand", COLORS[0][0]), ("Before: tip", COLORS[0][1]),
               ("Overhead: hand", COLORS[1][0]), ("Overhead: tip", COLORS[1][1]))
    for i, (label, color) in enumerate(legends):
        x = 23 + 150 * i
        draw.line((x, 59, x + 18, 59), fill=color, width=2)
        draw.text((x + 23, 50), label, font=regular, fill="#e4eaf3")
    draw.text((650, 52), "Hollow tip marker: at most half of isolated blade pixels visible",
              font=regular, fill="#b3c0d3")

    variants = [
        [np.array([point[target] for point in measurement["curve"]]) for target in ("hand", "tip")]
        for measurement in measurements
    ]

    def panel(box, title, matrix, direction=None, axes=False):
        x, y, width, height = box
        draw.rounded_rectangle((x, y, x + width, y + height), radius=7,
                               fill="#182639", outline="#364960")
        draw.text((x + 12, y + 8), title, font=regular, fill="#e3eaf6")
        curves = [[points @ matrix for points in variant] for variant in variants]
        points = np.concatenate([np.zeros((1, 2)), *curves[0], *curves[1]])
        low, high = points.min(axis=0), points.max(axis=0)
        middle = (low + high) / 2
        scale = min((width - 34) / (high[0] - low[0]), (height - 54) / (high[1] - low[1]))

        def point(value):
            offset = (value - middle) * scale
            return (round(x + width / 2 + offset[0]), round(y + (height + 24) / 2 - offset[1]))

        origin = point(np.zeros(2))
        draw.line((x + 6, origin[1], x + width - 6, origin[1]), fill="#314158")
        if axes:
            axis_units = 4 if direction is None else 1
            for direction3, text in zip(np.eye(3), ("+X left", "+Y front", "+Z up"), strict=True):
                end = point((direction3 * axis_units) @ matrix)
                if end != origin:
                    draw.line((origin, end), fill="#788aa2", width=1)
                    draw.text((end[0] + 2, end[1] + 2), text, font=small, fill="#b9c7d8")
        for variant_index, paths in enumerate(curves):
            for target_index, path_points in enumerate(paths):
                color = COLORS[variant_index][target_index]
                coords = [point(p) for p in path_points]
                draw.line(coords, fill=color, width=3 if target_index == 1 else 1)
                if target_index == 0 and direction is not None:
                    continue
                for i, (cx, cy) in enumerate(coords[::SUBSTEPS]):
                    hidden = False
                    if direction and target_index == 1:
                        visible, isolated = visibility[variant_index][f"{direction}_{i + 1}"]["blade"]
                        hidden = isolated == 0 or 2 * visible <= isolated
                    radius = 4 if target_index == 1 else 2
                    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                                 outline=color, fill="#182639" if hidden else color)
                    if not direction and target_index == 1 and variant_index == 1 and i in (0, 3, 4, 5, 7):
                        draw.text((cx + 5, cy - 9), str(i + 1), font=small, fill=color)

    panel((20, 82, 694, 294), "3D oblique view · model units", camera_projection(-34, 18), axes=True)
    panel((726, 82, 694, 294), "Side profile · forward / height", np.eye(3)[:, 1:], axes=True)
    for index, (direction, yaw) in enumerate(directions.items()):
        x, y = 20 + index % 4 * 352, 388 + index // 4 * 244
        matrix = camera_projection(yaw, camera["pitch_deg"]) * camera["pixels_per_unit"]
        panel((x, y, 344, 235), f"{direction} · sprite projection", matrix, direction)
    draw.text((22, 886), "Markers are baked keys. Lines sample 12 subdivisions per interval. Zero is the shared foot anchor.",
              font=regular, fill="#b3c0d3")
    image.save(path)
