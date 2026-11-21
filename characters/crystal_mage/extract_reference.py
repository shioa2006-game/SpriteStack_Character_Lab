"""Sample the crystal mage's colors and proportions from the local reference image.

The reference illustration is not tracked. Pass its path with --image. The
annotated boxes (reference_regions.json) and the derived colors are tracked so
the palette can be audited without the image. Color sampling reuses the
three-tone rule of experiment 01 (characters/maren/extract_reference.py); this
script adds the staff and width measurements that the mage needs.
"""

import argparse
import json
from pathlib import Path

from characters.maren.extract_reference import extract


HERE = Path(__file__).resolve().parent


def staff_and_widths(regions):
    marks, staff, widths = regions["landmarks_y"], regions["staff_y"], regions["widths_x"]
    height = marks["sole"] - marks["hair_top"]
    above_sole = {name: round((marks["sole"] - y) / height, 4) for name, y in staff.items()}
    head_width = widths["shoulder_left"] - widths["shoulder_right"]
    center = widths["figure_center"]
    return {
        "staff_height_fraction_above_sole": above_sole,
        "staff_length_over_figure_height": round((staff["foot"] - staff["ornament_top"]) / height, 4),
        "staff_tilt_deg_from_vertical": round(float(
            __import__("math").degrees(__import__("math").atan2(
                widths["staff_at_foot"] - widths["staff_at_grip"], staff["foot"] - staff["grip"]))), 2),
        "half_width_over_height": {
            "cape_tip_right": round((center - widths["cape_tip_right_of_figure"]) / height, 4),
            "cape_tip_left": round((widths["cape_tip_left_of_figure"] - center) / height, 4),
            "robe_hem_right": round((center - widths["robe_hem_right"]) / height, 4),
            "robe_hem_left": round((widths["robe_hem_left"] - center) / height, 4),
            "staff_at_grip": round((center - widths["staff_at_grip"]) / height, 4),
        },
        "shoulder_width_over_height": round(head_width / height, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True, help="local reference image (untracked)")
    parser.add_argument("--regions", type=Path, default=HERE / "reference_regions.json")
    parser.add_argument("--out", type=Path, required=True, help="JSON file to write")
    args = parser.parse_args()
    regions = json.loads(args.regions.read_text(encoding="utf-8"))
    result = extract(args.image, regions)
    result.update(staff_and_widths(regions))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(result['materials'])} sampled materials to {args.out}")


if __name__ == "__main__":
    main()
