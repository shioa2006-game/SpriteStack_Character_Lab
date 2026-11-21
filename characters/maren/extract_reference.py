"""Sample MAREN's material colors and body proportions from the local reference image.

The reference illustration is not tracked. Pass its path with --image; the
annotated boxes and the derived colors are tracked so the palette can be audited.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent
TONES = {"shadow": (10, 30), "base": (45, 70), "light": (80, 95)}


def luminance(rgb):
    return rgb @ np.array([.299, .587, .114])


def keep(pixels, rule):
    """Drop the white backdrop, then apply an optional per-region filter."""
    spread = pixels.max(axis=1) - pixels.min(axis=1)
    pixels = pixels[~((pixels.min(axis=1) > 228) & (spread < 22))]
    value = luminance(pixels)
    if rule == "saturated_blue":
        pixels = pixels[(pixels[:, 2] - pixels[:, 0] > 25) & (value < 170)]
    elif rule == "dark":
        pixels = pixels[value <= np.percentile(value, 50)]
    elif rule == "bright":
        pixels = pixels[value >= np.percentile(value, 80)]
    elif rule is not None:
        raise ValueError(f"unknown filter {rule}")
    return pixels


def tones(pixels):
    order = np.argsort(luminance(pixels), kind="stable")
    ranked = pixels[order]
    result = {}
    for name, (low, high) in TONES.items():
        start = int(len(ranked) * low / 100)
        stop = max(start + 1, int(len(ranked) * high / 100))
        color = np.rint(np.median(ranked[start:stop], axis=0)).astype(int)
        result[name] = "".join(f"{channel:02x}" for channel in color)
    return result


def extract(image_path, regions):
    raw = image_path.read_bytes()
    with Image.open(image_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=float)
    if list(rgb.shape[1::-1]) != regions["image"]["size"]:
        raise ValueError(f"expected a {regions['image']['size']} image, got {rgb.shape[1::-1]}")

    materials = {}
    for name, region in regions["regions"].items():
        pixels = np.concatenate([rgb[y0:y1, x0:x1].reshape(-1, 3)
                                 for x0, y0, x1, y1 in region["boxes"]])
        pixels = keep(pixels, region.get("filter"))
        if len(pixels) < 20:
            raise ValueError(f"region {name} kept only {len(pixels)} pixels")
        materials[name] = {**tones(pixels), "pixels": int(len(pixels))}

    # Approximate area share of each color family: every figure pixel takes the family
    # of the nearest sampled tone. Anti-aliased edges and highlights add some noise.
    figure = np.ones(rgb.shape[:2], dtype=bool)
    for x0, y0, x1, y1 in regions["exclude_boxes"]:
        figure[y0:y1, x0:x1] = False
    pixels = rgb[figure]
    spread = pixels.max(axis=1) - pixels.min(axis=1)
    pixels = pixels[~((pixels.min(axis=1) > 228) & (spread < 22))]
    family_of = {name: family for family, names in regions["families"].items() for name in names}
    tones_rgb = np.array([[int(color[i:i + 2], 16) for i in (0, 2, 4)]
                          for item in materials.values() for color in (item["shadow"], item["base"], item["light"])])
    labels = [family_of[name] for name in materials for _ in range(3)]
    nearest = np.argmin(((pixels[:, None, :] - tones_rgb[None]) ** 2).sum(axis=-1), axis=1)
    counts = {family: 0 for family in regions["families"]}
    for index, count in zip(*np.unique(nearest, return_counts=True)):
        counts[labels[index]] += int(count)
    shares = {family: round(count / len(pixels), 4) for family, count in counts.items()}

    marks = regions["landmarks_y"]
    height = marks["sole"] - marks["hair_top"]
    proportions = {
        name: round((marks["sole"] - y) / height, 4) for name, y in marks.items()
    }
    head = marks["chin"] - marks["skull_top"]
    return {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "percentile_bands": TONES,
        "materials": materials,
        "family_area_share": shares,
        "figure_pixels": int(len(pixels)),
        "height_fraction_above_sole": proportions,
        "heads_tall": round((marks["sole"] - marks["skull_top"]) / head, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True, help="local reference image (untracked)")
    parser.add_argument("--regions", type=Path, default=HERE / "reference_regions.json")
    parser.add_argument("--out", type=Path, required=True, help="JSON file to write")
    args = parser.parse_args()
    regions = json.loads(args.regions.read_text(encoding="utf-8"))
    result = extract(args.image, regions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(result['materials'])} sampled materials to {args.out}")


if __name__ == "__main__":
    main()
