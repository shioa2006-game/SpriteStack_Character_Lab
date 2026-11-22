"""Check the crystal mage: model sources, rig attachments, connectivity, both idle sheets, published copies."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from characters.crystal_mage.bake_idle import comparison_character
from characters.crystal_mage.build_model import build
from spritestack.bake import check_attachment
from spritestack.character import load_character
from spritestack.render import Renderer, normals
from spritestack.rig import Biped


ROOT = Path(__file__).resolve().parents[1]
MAGE_DIR = ROOT / "characters/crystal_mage"
MAGE = MAGE_DIR / "character.json"
LARK = ROOT / "characters/lark/character.json"
PUBLISHED = ROOT / "docs/assets/crystal_mage"
DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
SHEETS = {48: ("idle.png", "metadata.json"), 64: ("idle-64.png", "idle-64.json")}
# Items that must stay readable: the crystal in every direction, the book where the
# left side faces the camera. The book may be hidden by the body in N and NE.
CRYSTAL, STAFF_WOOD, BOOK = [22, 23], [19, 20, 21], [24, 25]
BOOK_VIEWS = ("S", "SW", "W", "SE")


def read(path):
    return json.loads(path.read_bytes())


def dilate(mask):
    """Grow a boolean Z/Y/X mask by one voxel in all 26 directions."""
    for axis in range(3):
        padded = np.pad(mask, [(1, 1) if i == axis else (0, 0) for i in range(3)])
        mask = padded[tuple(slice(0, -2) if i == axis else slice(None) for i in range(3))] | \
            padded[tuple(slice(1, -1) if i == axis else slice(None) for i in range(3))] | \
            padded[tuple(slice(2, None) if i == axis else slice(None) for i in range(3))]
    return mask


def components(mask):
    """The 26-connected components of a mask, largest first."""
    remaining, found = mask.copy(), []
    while remaining.any():
        region = np.zeros_like(mask)
        region[tuple(np.argwhere(remaining)[0])] = True
        while True:
            grown = dilate(region) & remaining
            if grown.sum() == region.sum():
                break
            region = grown
        found.append(region)
        remaining &= ~region
    return sorted(found, key=lambda region: -int(region.sum()))


def check_sources(character):
    material_ids, part_ids = build(character.config)
    assert np.array_equal(material_ids, character.model), "materials.npz differs from build_model.py"
    assert np.array_equal(part_ids, character.part_ids), "part_ids.npz differs from build_model.py"
    palette = character.config["model"]["palette"]
    used = set(np.unique(character.model[character.model > 0]).tolist())
    assert used == set(range(1, len(palette) + 1)), "unused palette entry"
    assert set(np.unique(character.part_ids[character.part_ids > 0]).tolist()) == set(character.parts.values())
    provenance = read(MAGE_DIR / "palette_provenance.json")["materials"]
    sampled = read(MAGE_DIR / "reference_palette.json")["materials"]
    assert list(provenance) == [item["name"] for item in palette], "provenance does not list the palette in order"
    for item in palette:
        source = provenance[item["name"]]
        assert source["source"] in sampled, item["name"]
        if source["method"] == "extracted":
            assert all(item[tone] == sampled[source["source"]][tone] for tone in ("shadow", "base", "light")), \
                f"{item['name']} is marked extracted but differs from the sample"
    lark = load_character(LARK)
    assert character.motions["walk"] == lark.motions["walk"], "shared walk clip differs"
    methods = [item["method"] for item in provenance.values()]
    print(f"Model NPZ rebuilt from source ({len(used)} materials, {len(character.parts)} parts); "
          f"palette provenance {dict((m, methods.count(m)) for m in ('extracted', 'adjusted', 'derived'))}, "
          "extracted tones match the samples; walk clip shared with LARK")


def check_rig(character):
    attachments = character.config["rig"]["attachments"]
    assert attachments == {"staff": {"hand": "hand_R", "marker": "staff_tip"},
                           "book": {"hand": "hand_L", "marker": "book_center"}}
    rig = Biped(character)  # rejects unknown parts or attachments
    joints, transforms = rig.pose("rest", 0)
    check_attachment(rig, joints, transforms)
    grid = character.source_grid
    for part, marker in (("staff", "staff_tip"), ("book", "book_center")):
        voxels = np.argwhere(character.part_ids == character.parts[part])[:, ::-1]
        low = grid.origin + voxels.min(axis=0) * grid.spacing
        high = grid.origin + (voxels.max(axis=0) + 1) * grid.spacing
        point = np.array(character.config["rig"]["rest"][marker])
        assert np.all(point >= low - .5) and np.all(point <= high + .5), f"{marker} lies outside the {part}"
    print("Biped accepts the staff and book in the sword/shield attachment slots; rest attachments follow "
          "hand_R and hand_L; markers lie on their items")


def check_handedness(character):
    grid = character.source_grid
    for part, expected in (("staff", -1), ("book", 1)):
        voxels = np.argwhere(character.part_ids == character.parts[part])
        x = grid.origin[0] + (voxels[:, 2].mean() + .5) * grid.spacing[0]
        assert np.sign(x) == expected, part
    print("Staff on the anatomical right (x < 0), book on the anatomical left (x > 0)")


def stray_views(character, fragment):
    """Directions (48 and 64 px) in which any voxel of a fragment is drawn."""
    tagged = character.part_ids.copy()
    tagged[fragment] = 255
    seen = []
    for variant in (character, comparison_character(character)):
        view = variant.config["view"]
        renderer = Renderer(variant)
        surface = normals(variant.model, variant.source_grid)
        for direction, yaw in view["directions"].items():
            _, _, parts = renderer.render(variant.model, tagged, variant.source_grid, yaw,
                                          view["neutral_cell"], view["neutral_rays"], surface)
            if (parts == 255).any():
                seen.append(f"{view['neutral_cell']} {direction}")
    return seen


def check_connectivity(character):
    parts, grid = character.part_ids, character.source_grid
    names = {part_id: name for name, part_id in character.parts.items()}
    whole = components(parts > 0)
    assert len(whole) == 1, f"model splits into components {[int(c.sum()) for c in whole[:5]]}"
    pieces = {}
    for name, part_id in character.parts.items():
        mask = parts == part_id
        if name == "staff":
            # The right fist is painted over the shaft; staff and fist together must be one piece.
            mask |= parts == character.parts["hand_R"]
        found = components(mask)
        for fragment in found[1:]:
            size = int(fragment.sum())
            neighbours = sorted({names[int(i)] for i in np.unique(parts[dilate(fragment) & ~fragment])
                                 if i and i != part_id})
            assert neighbours, f"{name} has a floating fragment"
            seen = stray_views(character, fragment) if size < 3 else []
            assert not seen, f"{name}: a {size}-voxel fragment shows as a stray pixel in {seen}"
            pieces.setdefault(name, []).append(f"{size} vox touching {'/'.join(neighbours)}")
    touching = {}
    for a, b in (("staff", "hand_R"), ("book", "hand_L"), ("hand_R", "fore_R"), ("hand_L", "fore_L"),
                 ("fore_R", "upper_R"), ("fore_L", "upper_L"), ("upper_R", "chest"), ("upper_L", "chest")):
        contact = int((dilate(parts == character.parts[a]) & (parts == character.parts[b])).sum())
        assert contact > 0, f"{a} does not touch {b}"
        touching[f"{a}-{b}"] = contact
    staff = parts == character.parts["staff"]
    held = staff | (parts == character.parts["hand_R"])
    rows = np.where(staff.any(axis=(1, 2)))[0]
    gaps = [int(z) for z in range(rows.min(), rows.max() + 1) if not held[z].any()]
    assert rows.min() == 0 and not gaps, f"staff does not run from the floor to its top: gaps {gaps}"
    top = float(grid.origin[2] + (rows.max() + 1) * grid.spacing[2])
    print(f"One 26-connected model ({int(whole[0].sum())} voxels), no floating piece; staff and right fist "
          f"form one piece, continuous from z=0 to z={top}")
    print(f"  extra pieces of a part, each covered by the listed parts and never drawn as a stray "
          f"pixel (< 3 voxels checked in all 16 renders): {pieces or 'none'}")
    print(f"  contact voxels along the arms and items {touching}")


def projected_x(character, view, yaw, part):
    voxels = np.argwhere(character.part_ids == character.parts[part])[:, ::-1]
    center = character.source_grid.origin + (voxels.mean(axis=0) + .5) * character.source_grid.spacing
    theta = np.radians(yaw)
    return float(center @ np.array([np.cos(theta), np.sin(theta), 0])) * view["camera"]["pixels_per_unit"]


def check_sheet(output, character, cell):
    image_name, layout_name = SHEETS[cell]
    layout = read(output / layout_name)
    view = character.config["view"]
    neutral = layout["neutral"]
    anchor = [24, 40] if cell == 48 else character.config["comparison_view"]["base_pivot"]
    assert neutral["directions"] == DIRECTIONS and neutral["cell"] == [cell, cell] and neutral["anchor"] == anchor
    if cell == 48:
        assert layout["animations"] == {} and layout["camera"] == view["camera"]
    with Image.open(output / image_name) as sheet:
        assert sheet.mode == "RGBA" and sheet.size == (cell * 8, cell)
        frames = {d: sheet.crop((i * cell, 0, (i + 1) * cell, cell)) for i, d in enumerate(DIRECTIONS)}
    assert len({frame.tobytes() for frame in frames.values()}) == 8
    for a, b in (("SW", "SE"), ("W", "E"), ("NW", "NE")):
        assert frames[a].tobytes() != ImageOps.mirror(frames[b]).tobytes(), f"{a} is a mirrored {b}"

    renderer = Renderer(character)
    surface = normals(character.model, character.source_grid)
    visible, sides = {}, {}
    for direction, frame in frames.items():
        alpha = np.asarray(frame)[..., 3]
        assert set(np.unique(alpha)) == {0, 255}, direction
        x0, y0, x1, y1 = frame.getbbox()
        assert min(x0, y0, cell - x1, cell - y1) >= 1, direction
        yaw = view["directions"][direction]
        redrawn, ids, parts = renderer.render(character.model, character.part_ids, character.source_grid,
                                              yaw, cell, view["neutral_rays"], surface)
        assert redrawn.tobytes() == frame.tobytes(), f"{direction} is not the render of the committed model"
        counts = {
            "head": int((parts == character.parts["head"]).sum()),
            "staff": int(((parts == character.parts["staff"]) & np.isin(ids, STAFF_WOOD)).sum()),
            "crystal": int(((parts == character.parts["staff"]) & np.isin(ids, CRYSTAL)).sum()),
            "book": int(((parts == character.parts["book"]) & np.isin(ids, BOOK)).sum()),
        }
        visible[direction] = counts
        assert counts["head"] > 0 and counts["staff"] > 0 and counts["crystal"] >= 3, (direction, counts)
        if direction in BOOK_VIEWS:
            assert counts["book"] >= 4, (direction, counts)
        # Each visible item must sit on the screen side its 3D position projects to.
        side = {}
        for part in ("staff", "book"):
            columns = np.where(parts == character.parts[part])[1]
            expected = projected_x(character, view, yaw, part)
            if len(columns) >= 4 and abs(expected) >= 2:
                drawn = columns.mean() + .5 - neutral["anchor"][0]
                assert np.sign(drawn) == np.sign(expected), (direction, part, drawn, expected)
                side[part] = "left" if drawn < 0 else "right"
        sides[direction] = side
    print(f"{cell}x{cell}: {cell * 8}x{cell} RGBA, eight distinct frames, S..SE order, anchor {anchor}, "
          "binary alpha, 1 px margins, every frame equals a fresh render of the committed model, "
          "no frame is a mirror of its opposite: passed")
    print(f"  visible px {visible}")
    print(f"  screen side of staff/book (checked where the projection is 2 px or more off the anchor) {sides}")
    return layout


def check_published(output):
    for cell, names in SHEETS.items():
        image_name, layout_name = names
        with Image.open(output / image_name) as baked, Image.open(PUBLISHED / image_name) as published:
            same = baked.convert("RGBA").tobytes() == published.convert("RGBA").tobytes()
        assert same, f"docs/assets/crystal_mage/{image_name} differs from the bake"
        assert read(PUBLISHED / layout_name) == read(output / layout_name), f"published {layout_name} differs"
    print("Published gallery PNGs and JSON (48 and 64) match the bake (decoded RGBA)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="folder written by characters.crystal_mage.bake_idle")
    parser.add_argument("--skip-published", action="store_true",
                        help="do not compare with docs/assets/crystal_mage (before publishing)")
    args = parser.parse_args()
    character = load_character(MAGE)
    check_sources(character)
    check_rig(character)
    check_handedness(character)
    check_connectivity(character)
    check_sheet(args.output, character, 48)
    check_sheet(args.output, comparison_character(character), 64)
    if not args.skip_published:
        check_published(args.output)


if __name__ == "__main__":
    main()
