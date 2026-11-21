"""Command line entry point for the common sprite generator."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from .bake import bake, bake_idle, view_for_cell
from .character import load_character


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, type=Path, help="path to character.json")
    parser.add_argument("--out", required=True, type=Path, help="new output directory")
    parser.add_argument("--modes", choices=("all", "idle"), default="all",
                        help="all: idle, walk and attack (default). idle: only the idle eight "
                             "directions from the rest model, without walk or attack poses")
    parser.add_argument("--cells", type=int, nargs="+", metavar="PX",
                        help="idle cell sizes for --modes idle (default: view.neutral_cell and, if "
                             "character.json has one, comparison_view.neutral_cell). A size other than "
                             "view.neutral_cell is drawn with comparison_view and written as "
                             "idle-<PX>.png and idle-<PX>.json")
    args = parser.parse_args()
    if args.cells and args.modes != "idle":
        parser.error("--cells needs --modes idle")
    if args.cells and len(set(args.cells)) != len(args.cells):
        parser.error("--cells must not repeat a size")

    try:
        out = args.out.resolve()
        if out.exists():
            parser.error("--out must be a new directory to preserve existing files")
        character = load_character(args.character)
        for cell in args.cells or []:
            view_for_cell(character, cell)
        out.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".spritestack-", dir=out.parent) as workspace:
            staging = Path(workspace) / "output"
            staging.mkdir()
            if args.modes == "idle":
                bake_idle(character, staging, args.cells)
            else:
                bake(character, staging)
            staging.rename(out)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Sprite bake failed: {error}\n")
    if args.modes == "idle":
        print(f"Baked idle eight directions to {args.out}")
    else:
        print(f"Baked eight directions to {args.out}")


if __name__ == "__main__":
    main()
