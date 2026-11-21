"""Sample AZURE RONIN's colors and proportions from the local reference image.

The reference illustration is not tracked. Pass its path with --image. The
annotated boxes (reference_regions.json) and the derived colors are tracked so
the palette can be audited without the image. Color sampling reuses the
three-tone rule of experiment 01 (characters/maren/extract_reference.py); this
script adds the sword and width measurements that the swordsman needs.
"""

import argparse
import json
import math
from pathlib import Path

from characters.maren.extract_reference import extract


HERE = Path(__file__).resolve().parent


def sword_and_widths(regions):
    marks, sword, widths = regions["landmarks_y"], regions["sword"], regions["widths_x"]
    height = marks["sole"] - marks["hair_top"]
    center = widths["figure_center"]

    def length(a, b):
        return math.dist(sword[a], sword[b])

    (x0, y0), (x1, y1), (xm, ym) = sword["tsuba"], sword["tip"], sword["blade_mid"]
    chord = length("tsuba", "tip")
    # Distance of the blade middle from the straight tsuba-tip chord: the curvature (sori).
    sagitta = abs((x1 - x0) * (y0 - ym) - (x0 - xm) * (y1 - y0)) / chord
    return {
        "sword": {
            "blade_length_over_figure_height": round(chord / height, 4),
            "hilt_length_over_figure_height": round(length("pommel", "tsuba") / height, 4),
            "blade_sagitta_over_blade_length": round(sagitta / chord, 4),
            "blade_angle_deg_from_vertical": round(math.degrees(math.atan2(x0 - x1, y1 - y0)), 2),
            "tip_height_fraction_above_sole": round((marks["sole"] - y1) / height, 4),
            "tsuba_height_fraction_above_sole": round((marks["sole"] - y0) / height, 4),
        },
        "half_width_over_height": {
            "shoulder_right": round((center - widths["shoulder_right"]) / height, 4),
            "shoulder_left": round((widths["shoulder_left"] - center) / height, 4),
            "scarf_tail_tip_right": round((center - widths["scarf_tail_tip_right_of_figure"]) / height, 4),
            "long_panel_tip_left": round((widths["long_panel_tip_left_of_figure"] - center) / height, 4),
            "ponytail_tip_right": round((center - widths["ponytail_tip_right_of_figure"]) / height, 4),
        },
        "shoulder_width_over_height": round((widths["shoulder_left"] - widths["shoulder_right"]) / height, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True, help="local reference image (untracked)")
    parser.add_argument("--regions", type=Path, default=HERE / "reference_regions.json")
    parser.add_argument("--out", type=Path, required=True, help="JSON file to write")
    args = parser.parse_args()
    regions = json.loads(args.regions.read_text(encoding="utf-8"))
    result = extract(args.image, regions)
    result.update(sword_and_widths(regions))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(result['materials'])} sampled materials to {args.out}")


if __name__ == "__main__":
    main()
