"""Bake BRAM with local joint weights into a separate output directory."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from research.phase4.skin import WeightedReslice
from research.verify_bram import BRAM, read
from spritestack.bake import bake
from spritestack.character import load_character


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--weights", type=Path, default=Path(__file__).with_name("weights.json"))
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("--out must be a new directory to preserve existing results")

    character = load_character(BRAM)
    skin = WeightedReslice(character, read(args.weights))
    print(f"Weighted source voxels: {skin.blended_count} / {(character.part_ids > 0).sum()}", flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".weighted-", dir=out.parent) as temporary:
        stage = Path(temporary) / "output"
        stage.mkdir()
        bake(character, stage, pose_volume=skin)
        stage.rename(out)
    print(f"Baked weighted BRAM to {out}")


if __name__ == "__main__":
    main()
