"""Bake research-only specimens for the existing comparison page."""
import argparse
from pathlib import Path

from objects.bake import ROOT, load
from research.objects01.game_projection import PROFILE, collect, game_camera, read_json, write_atlas
from .variants import HEIGHTS, crate


def build(out):
    profile = read_json(PROFILE)
    step = profile["step_model"]
    game = game_camera(profile, step)
    entries, frames = {}, []
    for h in HEIGHTS:
        model = crate(h)
        collect(model, f"lab/{h}", (24, 1.5, 1), entries, frames)
        collect(model, f"game/{h}", game, entries, frames)
        if h != step:
            collect(model, f"fit/{h}", game_camera(profile, h), entries, frames)
    pillar = load(ROOT / "stone_pillar")
    factor = step / profile["legacy_source_units_per_step"]["stone_pillar"]
    collect(pillar, "lab/pillar-fit", (24, 1.5, factor), entries, frames)
    collect(pillar, "game/pillar-raw", game, entries, frames)
    write_atlas(out, "scale-study", entries, frames)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    build(p.parse_args().out)
