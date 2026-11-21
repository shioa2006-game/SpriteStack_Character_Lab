"""Inject defects into temporary copies of a character and check that verify_character reports them.

Nothing under characters/ or docs/ is modified. Each case copies the
character's manifest, NPZ and quality settings into a temporary folder, bakes
the idle sheets there with the shared idle bake, applies one defect and runs
research.verify_character. For defects in the sheets, the character's dedicated
verifier (research.verify_<name>) is also run on the damaged folder so the two
can be compared; the dedicated verifiers read the committed model, so they
cannot see defects injected into a copied model.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from research.verify_character import verify
from spritestack.bake import bake_idle
from spritestack.character import load_character


ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


class Workspace:
    """A disposable copy of one character, baked into <folder>/out."""

    def __init__(self, name, folder):
        self.name, self.folder = name, folder
        source = ROOT / "characters" / name
        config = json.loads((source / "character.json").read_text(encoding="utf-8"))
        for mode in ("walk", "attack"):
            config[mode]["clip"] = str((source / config[mode]["clip"]).resolve())
        self.write_config(config)
        for file in ("materials.npz", "part_ids.npz"):
            shutil.copy(source / file, folder / file)
        quality = json.loads((source / "quality.json").read_text(encoding="utf-8"))
        if quality.get("provenance"):
            quality["provenance"] = {k: str((source / v).resolve()) for k, v in quality["provenance"].items()}
        for motion in quality.get("motions", {}).values():
            if "same_as" in motion:
                motion["same_as"] = str((source / motion["same_as"]).resolve())
        quality["published"] = None
        (folder / "quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
        self.quality = quality
        self.out = folder / "out"
        self.bake()

    @property
    def path(self):
        return self.folder / "character.json"

    def config(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write_config(self, config):
        self.path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def arrays(self):
        with np.load(self.folder / "materials.npz") as m, np.load(self.folder / "part_ids.npz") as p:
            return m["slices"].copy(), p["parts"].copy()

    def save(self, materials, parts):
        np.savez_compressed(self.folder / "materials.npz", slices=materials)
        np.savez_compressed(self.folder / "part_ids.npz", parts=parts)

    def part(self, name):
        return self.config()["rig"]["parts"].index(name) + 1

    def material(self, name):
        return [m["name"] for m in self.config()["model"]["palette"]].index(name) + 1

    def index(self, xyz):
        model = self.config()["model"]
        return tuple(int(math.floor((c - o) / s)) for c, o, s in
                     zip(xyz[::-1], model["origin_xyz"][::-1], model["voxel_size_xyz"][::-1]))

    def bake(self):
        shutil.rmtree(self.out, ignore_errors=True)
        self.out.mkdir()
        bake_idle(load_character(self.path), self.out, self.quality.get("cells"))

    def sheet(self):
        with Image.open(self.out / "idle.png") as image:
            return image.convert("RGBA")

    def cell(self, sheet, direction):
        i = DIRECTIONS.index(direction)
        return sheet.crop((i * 48, 0, (i + 1) * 48, 48))


# ---------------------------------------------------------------- defects

def move_part(name, dy):
    """Move a part forward (+y) or back by dy model units."""
    def apply(ws):
        materials, parts = ws.arrays()
        mask = parts == ws.part(name)
        shift = int(round(dy / ws.config()["model"]["voxel_size_xyz"][1]))
        moved_m, moved_p = np.roll(np.where(mask, materials, 0), shift, 1), np.roll(np.where(mask, parts, 0), shift, 1)
        materials[mask], parts[mask] = 0, 0
        put = moved_p > 0
        materials[put], parts[put] = moved_m[put], moved_p[put]
        ws.save(materials, parts)
    return apply


def mirror_model(ws):
    materials, parts = ws.arrays()
    ws.save(materials[:, :, ::-1].copy(), parts[:, :, ::-1].copy())


def floating_block(center, part, material):
    def apply(ws):
        materials, parts = ws.arrays()
        z, y, x = ws.index(center)
        block = (slice(z, z + 2), slice(y, y + 2), slice(x, x + 2))
        assert not parts[block].any(), "floating block must go into empty space"
        materials[block], parts[block] = ws.material(material), ws.part(part)
        ws.save(materials, parts)
    return apply


def relabel_block(center, part):
    def apply(ws):
        materials, parts = ws.arrays()
        z, y, x = ws.index(center)
        block = (slice(z - 1, z + 2), slice(y - 1, y + 2), slice(x - 1, x + 2))
        assert parts[block].all(), "relabelled block must be inside the body"
        parts[block] = ws.part(part)
        ws.save(materials, parts)
    return apply


def replace_materials(old, new):
    def apply(ws):
        materials, parts = ws.arrays()
        materials[np.isin(materials, [ws.material(n) for n in old])] = ws.material(new)
        ws.save(materials, parts)
    return apply


def cut_slices(name, z_low, z_high):
    def apply(ws):
        materials, parts = ws.arrays()
        model = ws.config()["model"]
        z = model["origin_xyz"][2] + (np.arange(parts.shape[0]) + .5) * model["voxel_size_xyz"][2]
        cut = (parts == ws.part(name)) & ((z >= z_low) & (z < z_high))[:, None, None]
        materials[cut], parts[cut] = 0, 0
        ws.save(materials, parts)
    return apply


def cut_material_below(part, names, z_limit):
    def apply(ws):
        materials, parts = ws.arrays()
        model = ws.config()["model"]
        z = model["origin_xyz"][2] + (np.arange(parts.shape[0]) + .5) * model["voxel_size_xyz"][2]
        cut = ((parts == ws.part(part)) & np.isin(materials, [ws.material(n) for n in names])
               & (z < z_limit)[:, None, None])
        materials[cut], parts[cut] = 0, 0
        ws.save(materials, parts)
    return apply


def recolor_voxel(center, material):
    def apply(ws):
        materials, parts = ws.arrays()
        point = ws.index(center)
        assert parts[point], "recolored voxel must be occupied"
        materials[point] = ws.material(material)
        ws.save(materials, parts)
    return apply


def edit_config(change):
    def apply(ws):
        config = ws.config()
        change(config)
        ws.write_config(config)
    return apply


def set_rest(marker, axis, value):
    def change(config):
        config["rig"]["rest"][marker][axis] = value
    return edit_config(change)


def swap_attachments(config):
    a, b = config["rig"]["attachments"].values()
    a["hand"], b["hand"] = b["hand"], a["hand"]


def copy_palette(target, source):
    def change(config):
        palette = {m["name"]: m for m in config["model"]["palette"]}
        for tone in ("shadow", "base", "light"):
            palette[target][tone] = palette[source][tone]
    return edit_config(change)


def edit_sheet(change):
    def apply(ws):
        sheet = ws.sheet()
        change(ws, sheet)
        sheet.save(ws.out / "idle.png")
    return apply


def mirror_cell(target, source):
    def change(ws, sheet):
        sheet.paste(ImageOps.mirror(ws.cell(sheet, source)), (DIRECTIONS.index(target) * 48, 0))
    return edit_sheet(change)


def push_to_top(direction):
    def change(ws, sheet):
        cell = ws.cell(sheet, direction)
        top = cell.getbbox()[1]
        moved = Image.new("RGBA", cell.size)
        moved.paste(cell.crop((0, top, 48, 48)), (0, 0))
        sheet.paste(moved, (DIRECTIONS.index(direction) * 48, 0))
    return edit_sheet(change)


def touch_pixel(direction, alpha=None, rgb=None):
    def change(ws, sheet):
        x0 = DIRECTIONS.index(direction) * 48
        pixels = sheet.load()
        x, y = next((x, y) for y in range(48) for x in range(x0, x0 + 48) if pixels[x, y][3] == 255)
        r, g, b, a = pixels[x, y]
        pixels[x, y] = (*(rgb or (r, g, b)), alpha if alpha is not None else a)
    return edit_sheet(change)


def misspell_material(ws):
    path = ws.folder / "quality.json"
    quality = json.loads(path.read_text(encoding="utf-8"))
    quality["visibility"][-1]["materials"][0] = "book covr"
    path.write_text(json.dumps(quality, indent=2), encoding="utf-8")


def shift_anchor(ws):
    path = ws.out / "metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["neutral"]["anchor"] = [24, 41]
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


# name, character, defect, rebake after the defect, expected {check: status}, sheet-level, published folder
CASES = [
    ("staff moved 2 units forward, out of the right hand", "crystal_mage", move_part("staff", 2), True,
     {"rig.contacts": "FAIL", "model.connectivity": "FAIL", "rig.item_main": "FAIL"}, False, None),
    ("model mirrored: staff and book change sides", "crystal_mage", mirror_model, True,
     {"rig.handedness": "FAIL"}, False, None),
    ("attachments swapped in character.json", "crystal_mage", edit_config(swap_attachments), True,
     {"rig.handedness": "FAIL"}, False, None),
    ("E cell replaced with the mirrored W cell", "crystal_mage", mirror_cell("E", "W"), False,
     {"sheet48.redraw": "FAIL", "sheet48.mirror": "WARNING"}, True, None),
    ("S cell pushed against the top edge", "crystal_mage", push_to_top("S"), False,
     {"sheet48.margins": "FAIL", "sheet48.redraw": "FAIL"}, True, None),
    ("one half-transparent pixel in N", "crystal_mage", touch_pixel("N", alpha=128), False,
     {"sheet48.alpha": "FAIL"}, True, None),
    ("one recolored pixel compared with the published sheet", "crystal_mage",
     touch_pixel("N", rgb=(255, 0, 255)), False,
     {"sheet48.redraw": "FAIL", "sheet48.published": "FAIL"}, True, ROOT / "docs/assets/crystal_mage"),
    ("anchor in metadata.json moved by 1 px", "crystal_mage", shift_anchor, False,
     {"sheet48.layout": "FAIL"}, True, None),
    ("floating 2x2x2 block of hair behind the head", "crystal_mage",
     floating_block((0, -8, 25), "head", "hair"), True, {"model.connectivity": "FAIL"}, False, None),
    ("hidden 3x3x3 block inside the pelvis relabelled as head", "crystal_mage",
     relabel_block((0, -.1, 12.5), "head"), True, {"model.fragments": "WARNING"}, False, None),
    ("crystal voxels recolored as wood", "crystal_mage",
     replace_materials(["crystal", "crystal glow"], "staff carving"), True,
     {"sheet48.visible_crystal": "FAIL", "sheet64.visible_crystal": "FAIL", "model.palette": "WARNING"},
     False, None),
    ("gap cut through the staff shaft", "crystal_mage", cut_slices("staff", 8.0, 9.0), True,
     {"rig.continuous_staff": "FAIL", "rig.item_main": "FAIL"}, False, None),
    ("one hidden voxel recolored (model differs from its builder)", "crystal_mage",
     recolor_voxel((0, -.15, 17.0), "robe shade"), True, {"model.regenerate": "FAIL"}, False, None),
    ("staff_tip marker moved 5 units above the staff", "crystal_mage", set_rest("staff_tip", 2, 36.2), True,
     {"rig.markers": "FAIL"}, False, None),
    ("NaN in a rest joint", "crystal_mage", set_rest("hand_R", 0, float("nan")), False,
     {"model.numbers": "FAIL"}, False, None),
    ("quality.json names a material that does not exist", "crystal_mage", misspell_material, False,
     {"quality.references": "FAIL"}, False, None),
    ("book cover recolored with the cape colors (limit: not a technical defect)", "crystal_mage",
     copy_palette("book cover", "cape"), True, {}, False, None),
    ("shield moved 2 units forward, off the left hand", "maren", move_part("shield", 2), True,
     {"rig.contacts": "FAIL", "model.connectivity": "FAIL", "rig.item_off": "FAIL"}, False, None),
    ("long hair cut above the shoulders", "maren", cut_material_below("head", ["hair", "hair shade"], 24.0),
     True, {"rig.presence_long_hair_below_the_shoulders": "FAIL"}, False, None),
    ("W cell replaced with the mirrored E cell", "maren", mirror_cell("W", "E"), False,
     {"sheet48.redraw": "FAIL", "sheet48.mirror": "WARNING"}, True, None),
]


def dedicated_verifier(name, out):
    """Run research.verify_<name> on a damaged sheet folder; return (exit code, last message line)."""
    run = subprocess.run([sys.executable, "-B", "-m", f"research.verify_{name}", str(out)], cwd=ROOT,
                         capture_output=True, text=True)
    lines = [line for line in (run.stderr or run.stdout).strip().splitlines() if line.strip()]
    return run.returncode, lines[-1][:140] if lines else ""


def run_case(case, folder):
    label, name, defect, rebake, expected, sheet_level, published = case
    ws = Workspace(name, folder)
    defect(ws)
    refused = None
    if rebake:
        try:
            ws.bake()
        except ValueError as error:  # the shared bake itself refuses the damaged model
            refused = str(error)
    report = verify(ws.path, ws.out, ws.folder / "quality.json", published)
    statuses = report.statuses()
    missed = {check: (want, statuses.get(check, "not run")) for check, want in expected.items()
              if statuses.get(check) != want}
    others = sorted(check for check, status in statuses.items()
                    if status in ("FAIL", "WARNING") and check not in expected)
    old = dedicated_verifier(name, ws.out) if sheet_level else None
    return {"case": label, "character": name, "expected": expected, "missed": missed,
            "other_findings": {check: statuses[check] for check in others}, "bake_refused": refused,
            "dedicated_verifier": old}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="write the case results to this JSON file")
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix="verify-selftest-") as temp:
        for number, case in enumerate(CASES):
            folder = Path(temp) / f"case{number:02}"
            folder.mkdir()
            result = run_case(case, folder)
            results.append(result)
            mark = "detected" if not result["missed"] else f"MISSED {result['missed']}"
            print(f"[{mark}] {result['character']}: {result['case']}")
            print(f"    expected {result['expected'] or 'no FAIL (known limit)'}")
            if result["bake_refused"]:
                print(f"    the idle bake refused the damaged model: {result['bake_refused']}")
            if result["other_findings"]:
                print(f"    also reported {result['other_findings']}")
            if result["dedicated_verifier"]:
                code, message = result["dedicated_verifier"]
                print(f"    research.verify_{result['character']}: exit {code}: {message}")
    if args.json:
        args.json.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    missed = [r for r in results if r["missed"]]
    print(f"{len(results) - len(missed)} of {len(results)} cases reported as expected")
    raise SystemExit(1 if missed else 0)


if __name__ == "__main__":
    main()
