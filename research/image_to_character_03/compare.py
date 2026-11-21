"""Build AZURE RONIN's comparison sheets and metrics for image-to-character experiment 03.

Tracked outputs use only the idle bakes and the colors and coordinates derived
from the reference (characters/azure_ronin/reference_*.json). The side-by-side
sheet with the reference illustration is written only when --reference and
--local-out are given; keep it in an untracked folder such as .phase1/.

Besides the measurements of experiment 02, this script counts how many separate
pieces the drawn blade falls into in each direction (a thin curved blade must not
break up) and how far the ponytail reaches behind the head.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from spritestack.bake import view_for_cell
from spritestack.character import load_character
from spritestack.render import Renderer, normals


ROOT = Path(__file__).resolve().parents[2]
RONIN_DIR = ROOT / "characters/azure_ronin"
CONFIGS = {name: ROOT / f"characters/{folder}/character.json" for name, folder in (
    ("RONIN", "azure_ronin"), ("MAGE", "crystal_mage"), ("MAREN", "maren"), ("LARK", "lark"), ("BRAM", "bram"))}
SHEETS = {"MAGE": ROOT / "docs/assets/crystal_mage/idle.png", "MAREN": ROOT / "docs/assets/maren/idle.png",
          "LARK": ROOT / "docs/assets/idle.png", "BRAM": ROOT / "docs/assets/bram/idle.png"}
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
FRONT = ("S", "SW", "SE")
BACKGROUND = (38, 46, 62, 255)
PANEL = (48, 58, 78, 255)
TEXT = (226, 232, 240, 255)
MUTED = (150, 164, 186, 255)
FAMILY_COLORS = {"navy hair": "#2b3150", "skin": "#e8baa2", "beige tunic": "#cdbfac", "blue cloth": "#3c4f92",
                 "charcoal scarf and trousers": "#52494c", "brown leather": "#5a463d",
                 "steel and bronze": "#bfc0cc"}
DARK_FAMILIES = ("navy hair", "blue cloth", "charcoal scarf and trousers", "brown leather")
# Visible-pixel items: (part, material names).
VISIBLE = {
    "blade": ("sword", ["blade", "blade edge"]),
    "hilt": ("sword", ["tsuba", "sword grip"]),
    "ponytail": ("head", ["ponytail"]),
    "hair ribbon": ("head", ["hair ribbon"]),
    "eyes": ("head", ["eyes"]),
    "scarf mask": ("head", ["scarf", "scarf shade"]),
    "scarf collar and tail": ("chest", ["scarf", "scarf shade"]),
    "beige tunic": ("chest", ["tunic"]),
    "skirt beige": ("pelvis", ["tunic", "tunic shade"]),
    "skirt blue": ("pelvis", ["blue cloth", "blue lining"]),
    "hip sword": ("pelvis", ["sheath", "sword grip", "tsuba"]),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def split(sheet, cell):
    return {direction: sheet.crop((i * cell, 0, (i + 1) * cell, cell)) for i, direction in enumerate(DIRECTIONS)}


def scaled(frame, zoom):
    return frame.resize((round(frame.width * zoom), round(frame.height * zoom)), Image.NEAREST)


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def pieces(mask):
    """Number of 8-connected pieces in a 2D pixel mask."""
    seen = np.zeros_like(mask)
    count = 0
    for start in zip(*np.nonzero(mask)):
        if seen[start]:
            continue
        count += 1
        stack = [start]
        seen[start] = True
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
    return count


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
    rows = [("AZURE RONIN 48x48", sheets["RONIN"]),
            ("AZURE RONIN 64x64 (same model, 4/3 px per unit)", sheets["RONIN 64"]),
            ("CRYSTAL MAGE 48x48", sheets["MAGE"]), ("MAREN 48x48", sheets["MAREN"]),
            ("LARK 48x48", sheets["LARK"]), ("BRAM 48x48", sheets["BRAM"])]
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
    names = (("RONIN", "AZURE RONIN"), ("MAGE", "CRYSTAL MAGE"), ("MAREN", "MAREN"), ("LARK", "LARK"),
             ("BRAM", "BRAM"))
    row = 48 * zoom + 70
    image = Image.new("RGBA", (10 + len(chosen) * (48 * zoom + 8) + 400, len(names) * row + 10), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for index, (key, label) in enumerate(names):
        y = 10 + index * row
        draw.text((10, y), label, fill=TEXT)
        frames = split(sheets[key], 48)
        for column, direction in enumerate(chosen):
            x = 10 + column * (48 * zoom + 8)
            image.alpha_composite(scaled(frames[direction], zoom), (x, y + 14))
            draw.text((x + 4, y + 14 + 48 * zoom), direction, fill=MUTED)
        x = 10 + len(chosen) * (48 * zoom + 8)
        draw.text((x, y + 14), "native 1x, all eight directions", fill=MUTED)
        image.alpha_composite(sheets[key], (x, y + 30))
    return image


def family_lookup(character):
    regions = read(RONIN_DIR / "reference_regions.json")
    provenance = read(RONIN_DIR / "palette_provenance.json")["materials"]
    family_of = {name: family for family, names in regions["families"].items() for name in names}
    lookup = np.zeros(len(character.config["model"]["palette"]) + 1, dtype=object)
    lookup[0] = None
    for index, material in enumerate(character.config["model"]["palette"], 1):
        lookup[index] = family_of[provenance[material["name"]]["source"]]
    return lookup, list(regions["families"])


def measure(character):
    """Per-direction bounding box, visible pixels, blade pieces and color-family shares."""
    lookup, families = family_lookup(character)
    names = {item["name"]: index for index, item in enumerate(character.config["model"]["palette"], 1)}
    renderer = Renderer(character)
    view = character.config["view"]
    cell = view["neutral_cell"]
    surface = normals(character.model, character.source_grid)
    result = {}
    for direction in DIRECTIONS:
        frame, ids, parts = renderer.render(character.model, character.part_ids, character.source_grid,
                                            view["directions"][direction], cell, view["neutral_rays"], surface)
        labels = lookup[ids[ids > 0]]
        masks = {name: (parts == character.parts[part]) & np.isin(ids, [names[m] for m in materials])
                 for name, (part, materials) in VISIBLE.items()}
        result[direction] = {
            "bbox": list(frame.getbbox()),
            "figure_px": int((ids > 0).sum()),
            "family_share": {family: round(float(np.mean(labels == family)), 4) for family in families},
            "visible_px": {name: int(mask.sum()) for name, mask in masks.items()},
            "blade_pieces": pieces(masks["blade"]),
            "sword_pieces": pieces(parts == character.parts["sword"]),
        }
    mean = lambda keys: {family: round(float(np.mean([result[d]["family_share"][family] for d in keys])), 4)
                         for family in families}
    return result, mean(FRONT), mean(DIRECTIONS)


def shape_measures(character):
    """Lengths of the sword, ponytail and long cloth in model units."""
    grid = character.source_grid
    names = {item["name"]: index for index, item in enumerate(character.config["model"]["palette"], 1)}
    head = character.part_ids == character.parts["head"]

    def points(mask):
        return grid.origin + (np.argwhere(mask)[:, ::-1] + .5) * grid.spacing

    hair_top = float(grid.origin[2] + (np.argwhere(head)[:, 0].max() + 1) * grid.spacing[2])
    rest = character.config["rig"]["rest"]
    blade = points((character.part_ids == character.parts["sword"])
                   & np.isin(character.model, [names["blade"], names["blade edge"]]))
    tsuba = np.asarray(rest["hand_R"]) + .95 * (np.asarray(rest["sword_tip"]) - rest["hand_R"]) / np.linalg.norm(
        np.asarray(rest["sword_tip"]) - rest["hand_R"])
    blade_length = float(np.linalg.norm(blade - tsuba, axis=1).max())
    ponytail = points(head & (character.model == names["ponytail"]))
    hair = points(head & np.isin(character.model, [names["hair"], names["hair shade"]]))
    scarf = points((character.part_ids == character.parts["chest"])
                   & np.isin(character.model, [names["scarf"], names["scarf shade"]]))
    panels = points((character.part_ids == character.parts["pelvis"])
                    & np.isin(character.model, [names["tunic"], names["tunic shade"]]))
    return {
        "hair_top_units": hair_top,
        "blade_length_units": round(blade_length, 2),
        "blade_over_figure_height": round(blade_length / hair_top, 3),
        "blade_sagitta_design_units": .85,
        "ponytail_z_range": [float(ponytail[:, 2].min() - .25), float(ponytail[:, 2].max() + .25)],
        "ponytail_behind_hair_units": round(float(hair[:, 1].min() - ponytail[:, 1].min()), 2),
        "scarf_tail_lowest_z": float(scarf[:, 2].min() - .25),
        "back_panel_lowest_z": float(panels[:, 2].min() - .25),
    }


def proportions(characters, reference):
    result = {}
    for name, character in characters.items():
        head = character.part_ids == character.parts["head"]
        grid = character.source_grid
        top = float(grid.origin[2] + (np.argwhere(head)[:, 0].max() + 1) * grid.spacing[2])
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
        "blade_over_figure_height": reference["sword"]["blade_length_over_figure_height"],
    }
    return result


def features_sheet(ronin, reference, shares, ratios, shapes):
    palette = ronin.config["model"]["palette"]
    provenance = read(RONIN_DIR / "palette_provenance.json")["materials"]
    row = 22
    image = Image.new("RGBA", (1100, max(70 + len(palette) * row + 20, 700)), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Palette: sampled from the reference -> adopted for AZURE RONIN (shadow / base / light)",
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
    bars = (("reference", reference["family_area_share"]), ("RONIN 48 S/SW/SE", shares["front"]),
            ("RONIN 48 all 8", shares["all"]))
    for index, (label, share) in enumerate(bars):
        y = 62 + index * 44
        draw.text((x0, y), label, fill=MUTED)
        x = x0
        for family, value in share.items():
            width = round(400 * value)
            draw.rectangle((x, y + 14, x + width, y + 34), fill=FAMILY_COLORS[family])
            if value >= .07:
                draw.text((x + 3, y + 18), f"{value * 100:.0f}",
                          fill=TEXT if family in DARK_FAMILIES else (16, 16, 20))
            x += width
    y = 62 + len(bars) * 44
    for index, (family, color) in enumerate(FAMILY_COLORS.items()):
        x = x0 + (index % 2) * 230
        yy = y + (index // 2) * 16
        draw.rectangle((x, yy, x + 12, yy + 12), fill=color)
        draw.text((x + 16, yy), family, fill=MUTED)

    top = y + 74
    draw.text((x0, top), "Height fractions above the sole (of the hair top)", fill=TEXT)
    height = 300
    columns = [("reference", ratios["reference"], ("shoulder", "waist_belt", "knee")),
               ("RONIN", ratios["RONIN"], ("shoulder", "hip", "knee")),
               ("MAGE", ratios["MAGE"], ("shoulder", "hip", "knee")),
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
    blade = (("reference", ratios["reference"]["blade_over_figure_height"]),
             ("RONIN", shapes["blade_over_figure_height"]))
    for index, (label, value) in enumerate(blade):
        draw.text((x0, top + height + 70 + index * 16), f"blade length / figure height, {label}: {value:.2f}",
                  fill=MUTED)
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
    parser.add_argument("--idle", type=Path, required=True,
                        help="folder written by python -m spritestack --modes idle for azure_ronin")
    parser.add_argument("--out", type=Path, required=True, help="folder for tracked sheets and metrics")
    parser.add_argument("--reference", type=Path, help="local reference image (untracked)")
    parser.add_argument("--local-out", type=Path, help="PNG path for the side-by-side with the reference")
    args = parser.parse_args()
    if bool(args.reference) != bool(args.local_out):
        parser.error("--reference and --local-out must be given together")

    characters = {name: load_character(path) for name, path in CONFIGS.items()}
    ronin = characters["RONIN"]
    reference = read(RONIN_DIR / "reference_palette.json")
    sheets = {}
    for name, path in {"RONIN": args.idle / "idle.png", "RONIN 64": args.idle / "idle-64.png", **SHEETS}.items():
        with Image.open(path) as image:
            sheets[name] = image.convert("RGBA")

    per_direction, front, everything = measure(ronin)
    per_direction_64, _, _ = measure(view_for_cell(ronin, 64))
    ratios = proportions(characters, reference)
    shapes = shape_measures(ronin)
    args.out.mkdir(parents=True, exist_ok=True)
    zoom_sheet(sheets["RONIN"], 48, 6, "48x48 standard cell, shown at 6x").save(args.out / "idle_zoom_48.png")
    zoom_sheet(sheets["RONIN 64"], 64, 4.5,
               "64x64 comparison cell (same model, 4/3 px per unit), shown at 4.5x").save(args.out / "idle_zoom_64.png")
    native_sheet(sheets).save(args.out / "native_scale.png")
    lineup(sheets).save(args.out / "lineup.png")
    shares = {"front": front, "all": everything}
    features_sheet(ronin, reference, shares, ratios, shapes).save(args.out / "reference_features.png")
    methods = [item["method"] for item in read(RONIN_DIR / "palette_provenance.json")["materials"].values()]
    metrics = {
        "reference_source_sha256": reference["source_sha256"],
        "family_area_share": {"reference": reference["family_area_share"], "ronin_48_front_mean": front,
                              "ronin_48_all_mean": everything},
        "proportions": ratios,
        "shapes": shapes,
        "palette_methods": {method: methods.count(method) for method in ("extracted", "adjusted", "derived")},
        "idle_48": per_direction,
        "idle_64": per_direction_64,
    }
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.reference:
        local_comparison(args.reference, sheets["RONIN"], sheets["RONIN 64"], args.local_out)
    print(f"Wrote comparison sheets and metrics to {args.out}")


if __name__ == "__main__":
    main()
