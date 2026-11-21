"""Build MAREN's comparison sheets and metrics for image-to-character experiment 01.

Tracked outputs use only the idle bake and the colors and coordinates derived
from the reference (characters/maren/reference_*.json). The side-by-side sheet
with the reference illustration is written only when --reference and
--local-out are given; keep it in an untracked folder such as .phase1/.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from spritestack.character import load_character
from spritestack.render import Renderer, normals


ROOT = Path(__file__).resolve().parents[2]
MAREN_DIR = ROOT / "characters/maren"
CONFIGS = {name: ROOT / f"characters/{name.lower()}/character.json" for name in ("MAREN", "LARK", "BRAM")}
SHEETS = {"LARK": ROOT / "docs/assets/idle.png", "BRAM": ROOT / "docs/assets/bram/idle.png"}
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
FRONT = ("S", "SW", "SE")
BACKGROUND = (38, 46, 62, 255)
PANEL = (48, 58, 78, 255)
TEXT = (226, 232, 240, 255)
MUTED = (150, 164, 186, 255)
FAMILY_COLORS = {"blue": "#53668c", "skin": "#f1bea8", "beige": "#b39d8a", "dark": "#40342f",
                 "metal": "#a89a90"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def split(sheet):
    return {direction: sheet.crop((i * 48, 0, (i + 1) * 48, 48)) for i, direction in enumerate(DIRECTIONS)}


def scaled(frame, zoom):
    return frame.resize((frame.width * zoom, frame.height * zoom), Image.NEAREST)


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def zoom_sheet(frames, sheet):
    zoom, cell = 6, 48 * 6
    image = Image.new("RGBA", (4 * cell + 50, 2 * (cell + 22) + 48 * 2 + 70), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for index, direction in enumerate(DIRECTIONS):
        x, y = 10 + (index % 4) * (cell + 10), 10 + (index // 4) * (cell + 22)
        draw.text((x + 4, y), direction, fill=TEXT)
        image.alpha_composite(scaled(frames[direction], zoom), (x, y + 14))
    y = 2 * (cell + 22) + 20
    draw.text((10, y), "native 1x", fill=MUTED)
    image.alpha_composite(sheet, (10, y + 14))
    draw.text((420, y), "2x", fill=MUTED)
    image.alpha_composite(scaled(sheet, 2), (420, y + 14))
    return image


def lineup(sheets):
    zoom, chosen = 4, ("S", "SW", "W", "N")
    row = 48 * zoom + 70
    image = Image.new("RGBA", (10 + len(chosen) * (48 * zoom + 8) + 400, len(sheets) * row + 10), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for index, (name, sheet) in enumerate(sheets.items()):
        y = 10 + index * row
        draw.text((10, y), name, fill=TEXT)
        frames = split(sheet)
        for column, direction in enumerate(chosen):
            x = 10 + column * (48 * zoom + 8)
            image.alpha_composite(scaled(frames[direction], zoom), (x, y + 14))
            draw.text((x + 4, y + 14 + 48 * zoom), direction, fill=MUTED)
        x = 10 + len(chosen) * (48 * zoom + 8)
        draw.text((x, y + 14), "native 1x, all eight directions", fill=MUTED)
        image.alpha_composite(sheet, (x, y + 30))
    return image


def family_map(maren):
    regions = read(MAREN_DIR / "reference_regions.json")
    provenance = read(MAREN_DIR / "palette_provenance.json")["materials"]
    family_of = {name: family for family, names in regions["families"].items() for name in names}
    lookup = np.zeros(len(maren.config["model"]["palette"]) + 1, dtype=object)
    lookup[0] = None
    for index, material in enumerate(maren.config["model"]["palette"], 1):
        lookup[index] = family_of[provenance[material["name"]]["source"]]
    return lookup, list(regions["families"])


def sprite_shares(maren):
    lookup, families = family_map(maren)
    renderer = Renderer(maren)
    view = maren.config["view"]
    surface = normals(maren.model, maren.source_grid)
    result = {}
    for direction in DIRECTIONS:
        frame, ids, parts = renderer.render(maren.model, maren.part_ids, maren.source_grid,
                                            view["directions"][direction], 48, view["neutral_rays"], surface)
        labels = lookup[ids[ids > 0]]
        result[direction] = {
            "bbox": list(frame.getbbox()),
            "figure_px": int((ids > 0).sum()),
            "family_share": {family: round(float(np.mean(labels == family)), 4) for family in families},
            "visible_px": {name: int((parts == maren.parts[name]).sum())
                           for name in ("head", "sword", "shield", "pelvis")},
        }
    mean = lambda keys: {family: round(float(np.mean([result[d]["family_share"][family] for d in keys])), 4)
                         for family in families}
    return result, mean(FRONT), mean(DIRECTIONS)


def proportions(characters, reference):
    result = {}
    for name, character in characters.items():
        occupied = np.argwhere(character.model > 0)
        grid = character.source_grid
        top = float(grid.origin[2] + (occupied[:, 0].max() + 1) * grid.spacing[2])
        rest = character.config["rig"]["rest"]
        result[name] = {
            "height_units": top,
            "shoulder": round(rest["shoulder_R"][2] / top, 3),
            "hip": round(rest["hip_R"][2] / top, 3),
            "knee": round(rest["knee_R"][2] / top, 3),
        }
    fractions = reference["height_fraction_above_sole"]
    result["reference"] = {
        "shoulder": fractions["shoulder"],
        "waist_belt": fractions["waist_belt"],
        "knee": fractions["knee"],
        "heads_tall": reference["heads_tall"],
    }
    return result


def features_sheet(maren, reference, shares, ratios):
    palette = maren.config["model"]["palette"]
    provenance = read(MAREN_DIR / "palette_provenance.json")["materials"]
    row = 22
    image = Image.new("RGBA", (1060, max(70 + len(palette) * row + 20, 600)), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Palette: sampled from the reference -> adopted for MAREN (shadow / base / light)",
              fill=TEXT)
    draw.text((150, 40), "reference sample", fill=MUTED)
    draw.text((290, 40), "adopted", fill=MUTED)
    for index, material in enumerate(palette):
        y = 58 + index * row
        source = provenance[material["name"]]
        draw.text((10, y + 4), material["name"], fill=TEXT)
        sampled = reference["materials"][source["source"]]
        for column, tone in enumerate(("shadow", "base", "light")):
            draw.rectangle((150 + column * 40, y, 186 + column * 40, y + row - 4), fill=rgb(sampled[tone]))
            draw.rectangle((290 + column * 40, y, 326 + column * 40, y + row - 4), fill=rgb(material[tone]))
        draw.text((420, y + 4), f"{source['method']} ({source['source']})", fill=MUTED)

    x0 = 600
    draw.text((x0, 40), "Approximate color-family area share", fill=TEXT)
    bars = (("reference", reference["family_area_share"]), ("MAREN S/SW/SE", shares["front"]),
            ("MAREN all 8", shares["all"]))
    for index, (label, share) in enumerate(bars):
        y = 62 + index * 44
        draw.text((x0, y), label, fill=MUTED)
        x = x0
        for family, value in share.items():
            width = round(360 * value)
            draw.rectangle((x, y + 14, x + width, y + 34), fill=FAMILY_COLORS[family])
            if value >= .07:
                draw.text((x + 3, y + 18), f"{value * 100:.0f}", fill=(16, 16, 20) if family != "dark" else TEXT)
            x += width
    y = 62 + len(bars) * 44
    for index, (family, color) in enumerate(FAMILY_COLORS.items()):
        draw.rectangle((x0 + index * 72, y, x0 + index * 72 + 12, y + 12), fill=color)
        draw.text((x0 + index * 72 + 16, y), family, fill=MUTED)

    top = y + 40
    draw.text((x0, top), "Height fractions above the sole", fill=TEXT)
    height = 300
    columns = [("reference", ratios["reference"], ("shoulder", "waist_belt", "knee")),
               ("MAREN", ratios["MAREN"], ("shoulder", "hip", "knee")),
               ("LARK", ratios["LARK"], ("shoulder", "hip", "knee")),
               ("BRAM", ratios["BRAM"], ("shoulder", "hip", "knee"))]
    for index, (label, values, keys) in enumerate(columns):
        x = x0 + index * 112
        base = top + 24 + height
        draw.rectangle((x, top + 24, x + 16, base), fill=PANEL)
        draw.text((x, base + 6), label, fill=TEXT)
        for key in keys:
            level = base - round(values[key] * height)
            draw.line((x - 2, level, x + 18, level), fill=TEXT, width=2)
            draw.text((x + 22, level - 6), f"{key.split('_')[0]} {values[key]:.2f}", fill=MUTED)
    return image


def local_comparison(reference_path, frames, sheet, out):
    with Image.open(reference_path) as source:
        reference = source.convert("RGBA")
    reference = reference.resize((round(reference.width * 480 / reference.height), 480), Image.LANCZOS)
    image = Image.new("RGBA", (reference.width + 3 * 490 + 20, 480 + 140), BACKGROUND)
    image.alpha_composite(reference, (0, 0))
    draw = ImageDraw.Draw(image)
    for index, direction in enumerate(FRONT):
        x = reference.width + 20 + index * 490
        image.alpha_composite(scaled(frames[direction], 10), (x, 0))
        draw.text((x + 6, 6), direction, fill=TEXT)
    draw.text((10, 492), "Local only: contains the untracked reference illustration. Do not commit or publish.",
              fill=MUTED)
    image.alpha_composite(scaled(sheet, 2), (10, 512))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle", type=Path, required=True, help="folder with MAREN's idle.png")
    parser.add_argument("--out", type=Path, required=True, help="folder for tracked sheets and metrics")
    parser.add_argument("--reference", type=Path, help="local reference image (untracked)")
    parser.add_argument("--local-out", type=Path, help="PNG path for the side-by-side with the reference")
    args = parser.parse_args()
    if bool(args.reference) != bool(args.local_out):
        parser.error("--reference and --local-out must be given together")

    characters = {name: load_character(path) for name, path in CONFIGS.items()}
    reference = read(MAREN_DIR / "reference_palette.json")
    with Image.open(args.idle / "idle.png") as image:
        sheet = image.convert("RGBA")
    sheets = {"MAREN": sheet}
    for name, path in SHEETS.items():
        with Image.open(path) as image:
            sheets[name] = image.convert("RGBA")
    frames = split(sheet)

    per_direction, front, everything = sprite_shares(characters["MAREN"])
    ratios = proportions(characters, reference)
    shares = {"front": front, "all": everything}
    args.out.mkdir(parents=True, exist_ok=True)
    zoom_sheet(frames, sheet).save(args.out / "idle_zoom.png")
    lineup(sheets).save(args.out / "lineup.png")
    features_sheet(characters["MAREN"], reference, shares, ratios).save(args.out / "reference_features.png")
    methods = [item["method"] for item in read(MAREN_DIR / "palette_provenance.json")["materials"].values()]
    metrics = {
        "reference_source_sha256": reference["source_sha256"],
        "family_area_share": {"reference": reference["family_area_share"], "maren_front_mean": front,
                              "maren_all_mean": everything},
        "proportions": ratios,
        "palette_methods": {method: methods.count(method) for method in ("extracted", "adjusted", "derived")},
        "idle": per_direction,
    }
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.reference:
        local_comparison(args.reference, frames, sheet, args.local_out)
    print(f"Wrote comparison sheets and metrics to {args.out}")


if __name__ == "__main__":
    main()
