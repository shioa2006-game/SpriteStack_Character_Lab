"""Bake the overhead attack and regenerate the unchanged idle and walk sheets."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from research.overhead.motion import HERE, MANIFESTS, character_for
from spritestack.bake import bake
from spritestack.character import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", choices=MANIFESTS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--clip", type=Path, default=HERE / "clip.json")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("--out must be a new directory to preserve reference sprites")
    character = character_for(args.character, read_json(args.clip))
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".overhead-", dir=out.parent) as temporary:
        stage = Path(temporary) / "output"
        stage.mkdir()
        bake(character, stage)
        stage.rename(out)
    print(f"Baked {args.character.upper()} to {out}")


if __name__ == "__main__":
    main()
