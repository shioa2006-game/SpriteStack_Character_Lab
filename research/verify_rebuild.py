"""Compare LARK's decoded sprites with the imported originals on any OS."""

import argparse
import json
from pathlib import Path

from PIL import Image


REFERENCE = Path(__file__).resolve().parents[1] / "experiments/lark_stage3/output"


def check_sprites(rebuild):
    reference_metadata = json.loads((REFERENCE / "metadata.json").read_bytes())
    rebuilt_metadata = json.loads((rebuild / "metadata.json").read_bytes())
    metadata_matches = reference_metadata == rebuilt_metadata
    print("Parsed metadata (including directions, anchors, frames and timing):", metadata_matches)

    neutral = reference_metadata["neutral"]
    width, height = neutral["cell"]
    sizes = {"idle.png": (width * len(neutral["directions"]), height)}
    for name, layout in reference_metadata["animations"].items():
        width, height = layout["cell"]
        size = (width * layout["columns"], height * len(layout["rows"]))
        sizes[f"{name}.png"] = sizes[f"{name}_part_ids.png"] = size

    passed = metadata_matches
    for name, size in sizes.items():
        original = REFERENCE / name
        regenerated = rebuild / name
        with Image.open(original) as expected, Image.open(regenerated) as actual:
            dimensions_match = expected.size == actual.size == size
            pixels_match = expected.convert("RGBA").tobytes() == actual.convert("RGBA").tobytes()
        bytes_match = original.read_bytes() == regenerated.read_bytes()
        print(f"{name} {size[0]}x{size[1]} dimensions={dimensions_match} "
              f"RGBA={pixels_match} file_bytes={bytes_match}")
        passed = passed and dimensions_match and pixels_match
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rebuild", type=Path)
    raise SystemExit(0 if check_sprites(parser.parse_args().rebuild) else 1)
