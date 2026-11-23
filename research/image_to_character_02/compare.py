"""Build the crystal mage's comparison sheets and metrics for image-to-character experiment 02.

Tracked outputs use only the idle bakes and the colors and coordinates derived
from the reference (characters/crystal_mage/reference_*.json). The side-by-side
sheet with the reference illustration is written only when --reference and
--local-out are given; keep it in an untracked folder such as .phase1/.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from characters.crystal_mage.bake_idle import comparison_character
from spritestack.character import load_character
from spritestack.render import Renderer, normals


ROOT = Path(__file__).resolve().parents[2]
MAGE_DIR = ROOT / "characters/crystal_mage"
CONFIGS = {
    "MAGE": ROOT / "characters/crystal_mage/character.json",
    "MAREN": ROOT / "characters/maren/character.json",
    "LARK": ROOT / "experiments/lark/character.json",
    "BRAM": ROOT / "experiments/bram/character.json",
}
SHEETS = {"MAREN": ROOT / "docs/assets/maren/idle.png", "LARK": ROOT / "experiments/lark_stage3/output/idle.png",
          "BRAM": ROOT / "experiments/bram/baseline/idle.png"}
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
FRONT = ("S", "SW", "SE")
BACKGROUND = (38, 46, 62, 255)
PANEL = (48, 58, 78, 255)
TEXT = (226, 232, 240, 255)
MUTED = (150, 164, 186, 255)
FAMILY_COLORS = {"indigo hair": "#44426a", "skin": "#f0bfa7", "beige cloth and paper": "#d4c3ae",
                 "slate blue": "#5a6490", "brown leather and wood": "#5d4945", "crystal blue": "#4f84f2"}
VISIBLE = {"staff": ("staff", [19, 20, 21]), "crystal": ("staff", [22, 23]), "book": ("book", [24, 25])}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def split(sheet, cell):
    return {direction: sheet.crop((i * cell, 0, (i + 1) * cell, cell)) for i, direction in enumerate(DIRECTIONS)}


def scaled(frame, zoom):
    return frame.resize((round(frame.width * zoom), round(frame.height * zoom)), Image.NEAREST)


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def zoom_sheet(sheet, cell, zoom, title):
    """Eight directions enlarged to the same on-screen size, with the native sheet below."""
    frames = split(sheet, cell)
    size = round(cell * zoom)
    image = Image.new("RGBA", (max(4 * size + 50, sheet.width * 3 + 60), 2 * (size + 22) + cell * 2 + 84),
                      BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((10, 6), title, fill=TEXT)
    for index, direction in enumerate(DIRECTIONS):
        x, y = 10 + (index % 4) * (size + 10), 26 + (index // 4) * (size + 22)
        draw.text((x + 4, y), direction, fill=TEXT)
        image.alpha_composite(scaled(frames[direction], zoom), (x, y + 14))
    y = 26 + 2 * (size + 22) + 8
    draw.text((10, y), "native 1x", fill=MUTED)
    image.alpha_composite(sheet, (10, y + 14))
    draw.text((sheet.width + 40, y), "2x", fill=MUTED)
    image.alpha_composite(scaled(sheet, 2), (sheet.width + 40, y + 14))
    return image


def native_sheet(sheets):
    """Every sheet at 1x and 2x on one canvas, to judge readability at the size a game draws them."""
    rows = [("MAGE 48x48", sheets["MAGE"]), ("MAGE 64x64 (same model, 4/3 px per unit)", sheets["MAGE 64"]),
            ("MAREN 48x48", sheets["MAREN"]), ("LARK 48x48", sheets["LARK"]), ("BRAM 48x48", sheets["BRAM"])]
    width = 20 + 64 * 8 + 30 + 64 * 8 * 2
    height = 20 + sum(sheet.height * 2 + 30 for _, sheet in rows)
    image = Image.new("RGBA", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    y = 10
    for label, sheet in rows:
        draw.text((10, y), label + "  (1x | 2x)", fill=TEXT)
        image.alpha_composite(sheet, (10, y + 16 + sheet.height // 2))
        image.alpha_composite(scaled(sheet, 2), (10 + 64 * 8 + 30, y + 16))
        y += sheet.height * 2 + 30
    return image


def lineup(sheets):
    zoom, chosen = 4, ("S", "SW", "W", "N")
    names = ("MAGE", "MAREN", "LARK", "BRAM")
    row = 48 * zoom + 70
    image = Image.new("RGBA", (10 + len(chosen) * (48 * zoom + 8) + 400, len(names) * row + 10), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for index, name in enumerate(names):
        y = 10 + index * row
        draw.text((10, y), name, fill=TEXT)
        frames = split(sheets[name], 48)
        for column, direction in enumerate(chosen):
            x = 10 + column * (48 * zoom + 8)
            image.alpha_composite(scaled(frames[direction], zoom), (x, y + 14))
            draw.text((x + 4, y + 14 + 48 * zoom), direction, fill=MUTED)
        x = 10 + len(chosen) * (48 * zoom + 8)
        draw.text((x, y + 14), "native 1x, all eight directions", fill=MUTED)
        image.alpha_composite(sheets[name], (x, y + 30))
    return image


def family_lookup(mage):
    regions = read(MAGE_DIR / "reference_regions.json")
    provenance = read(MAGE_DIR / "palette_provenance.json")["materials"]
    family_of = {name: family for family, names in regions["families"].items() for name in names}
    lookup = np.zeros(len(mage.config["model"]["palette"]) + 1, dtype=object)
    lookup[0] = None
    for index, material in enumerate(mage.config["model"]["palette"], 1):
        lookup[index] = family_of[provenance[material["name"]]["source"]]
    return lookup, list(regions["families"])


def measure(character):
    """Per-direction bounding box, visible pixels of key items and color-family shares."""
    lookup, families = family_lookup(character)
    renderer = Renderer(character)
    view = character.config["view"]
    cell = view["neutral_cell"]
    surface = normals(character.model, character.source_grid)
    result = {}
    for direction in DIRECTIONS:
        frame, ids, parts = renderer.render(character.model, character.part_ids, character.source_grid,
                                            view["directions"][direction], cell, view["neutral_rays"], surface)
        labels = lookup[ids[ids > 0]]
        visible = {name: int(((parts == character.parts[part]) & np.isin(ids, materials)).sum())
                   for name, (part, materials) in VISIBLE.items()}
        visible["head"] = int((parts == character.parts["head"]).sum())
        result[direction] = {
            "bbox": list(frame.getbbox()),
            "figure_px": int((ids > 0).sum()),
            "family_share": {family: round(float(np.mean(labels == family)), 4) for family in families},
            "visible_px": visible,
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
        entry = {
            "height_units": top,
            "shoulder": round(rest["shoulder_R"][2] / top, 3),
            "hip": round(rest["hip_R"][2] / top, 3),
            "knee": round(rest["knee_R"][2] / top, 3),
        }
        if name == "MAGE":
            head = character.part_ids == character.parts["head"]
            hair_top = float(grid.origin[2] + (np.argwhere(head)[:, 0].max() + 1) * grid.spacing[2])
            entry.update(height_units=hair_top, top_of_staff_units=top,
                         shoulder=round(rest["shoulder_R"][2] / hair_top, 3),
                         hip=round(rest["hip_R"][2] / hair_top, 3),
                         knee=round(rest["knee_R"][2] / hair_top, 3),
                         staff_over_figure_height=round(top / hair_top, 3))
        result[name] = entry
    fractions = reference["height_fraction_above_sole"]
    result["reference"] = {
        "shoulder": fractions["shoulder"],
        "waist_belt": fractions["waist_belt"],
        "knee": fractions["knee"],
        "heads_tall": reference["heads_tall"],
        "staff_over_figure_height": reference["staff_length_over_figure_height"],
    }
    return result


def features_sheet(mage, reference, shares, ratios):
    palette = mage.config["model"]["palette"]
    provenance = read(MAGE_DIR / "palette_provenance.json")["materials"]
    row = 22
    image = Image.new("RGBA", (1100, max(70 + len(palette) * row + 20, 660)), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Palette: sampled from the reference -> adopted for the crystal mage (shadow / base / light)",
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

    x0 = 620
    draw.text((x0, 40), "Approximate color-family area share", fill=TEXT)
    bars = (("reference", reference["family_area_share"]), ("MAGE 48 S/SW/SE", shares["front"]),
            ("MAGE 48 all 8", shares["all"]))
    for index, (label, share) in enumerate(bars):
        y = 62 + index * 44
        draw.text((x0, y), label, fill=MUTED)
        x = x0
        for family, value in share.items():
            width = round(400 * value)
            draw.rectangle((x, y + 14, x + width, y + 34), fill=FAMILY_COLORS[family])
            if value >= .07:
                dark = family in ("indigo hair", "slate blue", "brown leather and wood")
                draw.text((x + 3, y + 18), f"{value * 100:.0f}", fill=TEXT if dark else (16, 16, 20))
            x += width
    y = 62 + len(bars) * 44
    for index, (family, color) in enumerate(FAMILY_COLORS.items()):
        x = x0 + (index % 3) * 150
        yy = y + (index // 3) * 16
        draw.rectangle((x, yy, x + 12, yy + 12), fill=color)
        draw.text((x + 16, yy), family, fill=MUTED)

    top = y + 50
    draw.text((x0, top), "Height fractions above the sole (MAGE: of the hair top)", fill=TEXT)
    height = 300
    columns = [("reference", ratios["reference"], ("shoulder", "waist_belt", "knee")),
               ("MAGE", ratios["MAGE"], ("shoulder", "hip", "knee")),
               ("MAREN", ratios["MAREN"], ("shoulder", "hip", "knee")),
               ("LARK", ratios["LARK"], ("shoulder", "hip", "knee"))]
    for index, (label, values, keys) in enumerate(columns):
        x = x0 + index * 112
        base = top + 44 + height
        draw.rectangle((x, top + 44, x + 16, base), fill=PANEL)
        draw.text((x, base + 6), label, fill=TEXT)
        for key in keys:
            level = base - round(values[key] * height)
            draw.line((x - 2, level, x + 18, level), fill=TEXT, width=2)
            draw.text((x + 22, level - 6), f"{key.split('_')[0]} {values[key]:.2f}", fill=MUTED)
        if "staff_over_figure_height" in values:
            level = base - round(values["staff_over_figure_height"] * height)
            draw.line((x - 2, level, x + 18, level), fill=FAMILY_COLORS["crystal blue"], width=2)
            draw.text((x + 22, level - 6), f"staff {values['staff_over_figure_height']:.2f}",
                      fill=FAMILY_COLORS["crystal blue"])
    return image


def local_comparison(reference_path, small, large, out):
    with Image.open(reference_path) as source:
        reference = source.convert("RGBA")
    reference = reference.resize((round(reference.width * 480 / reference.height), 480), Image.LANCZOS)
    width = reference.width + 20 + 3 * 490
    image = Image.new("RGBA", (width, 480 * 2 + 200), BACKGROUND)
    image.alpha_composite(reference, (0, 0))
    draw = ImageDraw.Draw(image)
    frames_small, frames_large = split(small, 48), split(large, 64)
    for index, direction in enumerate(FRONT):
        x = reference.width + 20 + index * 490
        image.alpha_composite(scaled(frames_small[direction], 10), (x, 0))
        draw.text((x + 6, 6), f"{direction} 48x48 at 10x", fill=TEXT)
        image.alpha_composite(scaled(frames_large[direction], 7.5), (x, 500))
        draw.text((x + 6, 506), f"{direction} 64x64 at 7.5x", fill=TEXT)
    draw.text((10, 500), "Local only: contains the untracked reference", fill=MUTED)
    draw.text((10, 516), "illustration. Do not commit or publish.", fill=MUTED)
    image.alpha_composite(small, (10, 990))
    image.alpha_composite(large, (10, 1050))
    image.alpha_composite(scaled(small, 2), (560, 990))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle", type=Path, required=True, help="folder written by characters.crystal_mage.bake_idle")
    parser.add_argument("--out", type=Path, required=True, help="folder for tracked sheets and metrics")
    parser.add_argument("--reference", type=Path, help="local reference image (untracked)")
    parser.add_argument("--local-out", type=Path, help="PNG path for the side-by-side with the reference")
    args = parser.parse_args()
    if bool(args.reference) != bool(args.local_out):
        parser.error("--reference and --local-out must be given together")

    characters = {name: load_character(path) for name, path in CONFIGS.items()}
    mage = characters["MAGE"]
    reference = read(MAGE_DIR / "reference_palette.json")
    sheets = {}
    for name, path in {"MAGE": args.idle / "idle.png", "MAGE 64": args.idle / "idle-64.png", **SHEETS}.items():
        with Image.open(path) as image:
            sheets[name] = image.convert("RGBA")

    per_direction, front, everything = measure(mage)
    per_direction_64, _, _ = measure(comparison_character(mage))
    ratios = proportions(characters, reference)
    args.out.mkdir(parents=True, exist_ok=True)
    zoom_sheet(sheets["MAGE"], 48, 6, "48x48 standard cell, shown at 6x").save(args.out / "idle_zoom_48.png")
    zoom_sheet(sheets["MAGE 64"], 64, 4.5,
               "64x64 comparison cell (same model, 4/3 px per unit), shown at 4.5x").save(args.out / "idle_zoom_64.png")
    native_sheet(sheets).save(args.out / "native_scale.png")
    lineup(sheets).save(args.out / "lineup.png")
    shares = {"front": front, "all": everything}
    features_sheet(mage, reference, shares, ratios).save(args.out / "reference_features.png")
    methods = [item["method"] for item in read(MAGE_DIR / "palette_provenance.json")["materials"].values()]
    metrics = {
        "reference_source_sha256": reference["source_sha256"],
        "family_area_share": {"reference": reference["family_area_share"], "mage_48_front_mean": front,
                              "mage_48_all_mean": everything},
        "proportions": ratios,
        "palette_methods": {method: methods.count(method) for method in ("extracted", "adjusted", "derived")},
        "idle_48": per_direction,
        "idle_64": per_direction_64,
    }
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.reference:
        local_comparison(args.reference, sheets["MAGE"], sheets["MAGE 64"], args.local_out)
    print(f"Wrote comparison sheets and metrics to {args.out}")


if __name__ == "__main__":
    main()
