"""Command line entry point for the common sprite generator."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from .bake import bake
from .character import load_character


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, type=Path, help="path to character.json")
    parser.add_argument("--out", required=True, type=Path, help="new output directory")
    args = parser.parse_args()

    try:
        out = args.out.resolve()
        if out.exists():
            parser.error("--out must be a new directory to preserve existing files")
        character = load_character(args.character)
        out.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".spritestack-", dir=out.parent) as workspace:
            staging = Path(workspace) / "output"
            staging.mkdir()
            bake(character, staging)
            staging.rename(out)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Sprite bake failed: {error}\n")
    print(f"Baked eight directions to {args.out}")


if __name__ == "__main__":
    main()
