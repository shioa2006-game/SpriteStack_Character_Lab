"""Check any biped character's model, rig, held items and idle sheets.

The checks are the same for every character. What differs per character (item
roles, visibility thresholds, published copy, the model builder, extra checks)
lives in a quality file next to character.json (default: quality.json), never
in this module.

Results are PASS (technically sound), WARNING (possible problem, not
necessarily a defect), FAIL (contract violation or clear generation defect)
and SKIP (not run because the quality file does not ask for it or a
prerequisite failed). The exit code is 1 when any check FAILs.
"""

import argparse
import dataclasses
import importlib
import json
import math
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from spritestack.bake import check_attachment, neutral_layout, view_for_cell
from spritestack.character import load_character
from spritestack.render import Renderer, normals
from spritestack.rig import Biped


DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
SIDES = {"hand_R": -1, "hand_L": 1}  # sign of x (x positive is the anatomical left)
LIMB_CHAIN = [(f"{a}_{side}", b if b == "chest" else f"{b}_{side}")
              for side in ("R", "L") for a, b in (("hand", "fore"), ("fore", "upper"), ("upper", "chest"))]
STRAY_VOXELS = 3  # a detached piece smaller than this that is drawn is a stray pixel
MARKER_PASS, MARKER_FAIL = 1.5, 3.0  # model units from an item marker to the item's nearest voxel


@dataclasses.dataclass
class Result:
    check: str
    status: str
    message: str
    details: dict = dataclasses.field(default_factory=dict)


class Report:
    def __init__(self):
        self.results = []

    def add(self, check, status, message, **details):
        assert status in ("PASS", "WARNING", "FAIL", "SKIP"), status
        self.results.append(Result(check, status, message, details))

    def counts(self):
        return {status: sum(r.status == status for r in self.results)
                for status in ("PASS", "WARNING", "FAIL", "SKIP")}

    def failed(self):
        return any(r.status == "FAIL" for r in self.results)

    def statuses(self):
        return {r.check: r.status for r in self.results}

    def print(self, verbose=False):
        for result in self.results:
            print(f"[{result.status:7}] {result.check}: {result.message}")
            if result.details and (verbose or result.status != "PASS"):
                for key, value in result.details.items():
                    print(f"            {key}: {value}")
        print("Summary:", ", ".join(f"{status} {count}" for status, count in self.counts().items()))

    def to_json(self):
        return {"summary": self.counts(), "results": [dataclasses.asdict(r) for r in self.results]}


@dataclasses.dataclass
class Context:
    character_path: Path
    character: object
    quality: dict
    quality_dir: Path
    output: Path | None
    published: Path | None
    report: Report
    renders: dict = dataclasses.field(default_factory=dict)

    @property
    def parts(self):
        return self.character.part_ids

    def part_mask(self, *names):
        return np.isin(self.character.part_ids, [self.character.parts[name] for name in names])

    def material_ids(self, names):
        lookup = {item["name"]: i for i, item in enumerate(self.character.config["model"]["palette"], 1)}
        unknown = [name for name in names if name not in lookup]
        if unknown:
            raise KeyError(f"unknown material names {unknown}")
        return [lookup[name] for name in names]

    def cells(self):
        return self.quality.get("cells") or [self.character.config["view"]["neutral_cell"]]

    def render(self, cell, direction, parts=None):
        """Cached render of the rest model in one idle cell and direction."""
        key = (cell, direction, parts is None)
        if parts is None and key in self.renders:
            return self.renders[key]
        seen = view_for_cell(self.character, cell)
        view = seen.config["view"]
        if ("surface",) not in self.renders:  # the same model in every cell
            self.renders[("surface",)] = normals(seen.model, seen.source_grid)
        surface = self.renders[("surface",)]
        result = Renderer(seen).render(seen.model, self.parts if parts is None else parts, seen.source_grid,
                                       view["directions"][direction], cell, view["neutral_rays"], surface)
        if parts is None:
            self.renders[key] = result
        return result


def resolve(base, value):
    return None if value is None else (base / value).resolve()


def call_target(spec):
    module, _, name = spec.partition(":")
    return getattr(importlib.import_module(module), name)


# ---------------------------------------------------------------- voxel helpers

def dilate(mask):
    """Grow a boolean Z/Y/X mask by one voxel in all 26 directions."""
    for axis in range(3):
        padded = np.pad(mask, [(1, 1) if i == axis else (0, 0) for i in range(3)])
        shifted = [padded[tuple(slice(k, k + mask.shape[axis]) if i == axis else slice(None) for i in range(3))]
                   for k in range(3)]
        mask = shifted[0] | shifted[1] | shifted[2]
    return mask


def components(mask):
    """The 26-connected components of a mask, largest first, as full-size masks."""
    found = []
    if not mask.any():
        return found
    occupied = np.argwhere(mask)
    low, high = occupied.min(axis=0), occupied.max(axis=0) + 1
    window = tuple(slice(a, b) for a, b in zip(low, high))
    remaining = mask[window].copy()
    while remaining.any():
        region = np.zeros_like(remaining)
        region[tuple(np.argwhere(remaining)[0])] = True
        count = 1
        while True:
            region = dilate(region) & remaining
            grown = int(region.sum())
            if grown == count:
                break
            count = grown
        full = np.zeros_like(mask)
        full[window] = region
        found.append(full)
        remaining &= ~region
    return sorted(found, key=lambda m: -int(m.sum()))


def world_points(character, mask):
    grid = character.source_grid
    return grid.origin + (np.argwhere(mask)[:, ::-1] + .5) * grid.spacing


def drawn_directions(ctx, fragments):
    """For each fragment mask, the 'cell direction' labels in which any of its voxels is drawn."""
    tagged = ctx.parts.copy()
    labels = list(range(255, 255 - len(fragments), -1))
    for label, fragment in zip(labels, fragments):
        tagged[fragment] = label
    seen = [[] for _ in fragments]
    for cell in ctx.cells():
        for direction in DIRECTIONS:
            _, _, parts = ctx.render(cell, direction, tagged)
            present = set(np.unique(parts).tolist())
            for index, label in enumerate(labels):
                if label in present:
                    seen[index].append(f"{cell} {direction}")
    return seen


# ---------------------------------------------------------------- model checks

def non_finite(value, path="config"):
    if isinstance(value, float) and not math.isfinite(value):
        yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from non_finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from non_finite(item, f"{path}[{index}]")


def check_references(ctx):
    """Every part, hand, marker and material named in the quality file must exist."""
    character = ctx.character
    parts, rest = set(character.parts), set(character.config["rig"]["rest"])
    materials = {item["name"] for item in character.config["model"]["palette"]}
    unknown = []
    named_parts = [name for item in items(ctx).values() for name in [item["part"], item["hand"], *item.get("through", [])]]
    named_parts += [name for rule in ctx.quality.get("continuous", []) for name in [rule["part"], *rule.get("through", [])]]
    named_parts += [rule["part"] for key in ("presence", "visibility") for rule in ctx.quality.get(key, [])]
    named_parts += [name for pair in ctx.quality.get("contacts", []) for name in pair]
    unknown += [f"part {name}" for name in dict.fromkeys(named_parts) if name not in parts]
    unknown += [f"marker {item['marker']}" for item in items(ctx).values() if item["marker"] not in rest]
    named_materials = [m for key in ("presence", "visibility") for rule in ctx.quality.get(key, [])
                       for m in rule.get("materials") or []]
    unknown += [f"material {name}" for name in dict.fromkeys(named_materials) if name not in materials]
    ctx.report.add("quality.references", "FAIL" if unknown else "PASS",
                   f"the quality file names things the character does not have: {unknown}" if unknown else
                   "every part, marker and material named in the quality file exists")
    return not unknown


def check_model(ctx):
    report, character = ctx.report, ctx.character
    palette = character.config["model"]["palette"]
    used = set(np.unique(character.model[character.model > 0]).tolist())
    unused = [palette[i - 1]["name"] for i in range(1, len(palette) + 1) if i not in used]
    if unused:
        report.add("model.palette", "WARNING", f"{len(unused)} palette entries have no voxels", unused=unused)
    else:
        report.add("model.palette", "PASS", f"all {len(palette)} materials and {len(character.parts)} parts "
                   f"have voxels; materials and parts share the {character.model.shape} Z/Y/X shape")

    builder = ctx.quality.get("model_builder")
    if not builder:
        report.add("model.regenerate", "SKIP", "no model_builder in the quality file")
    else:
        config = json.loads(ctx.character_path.read_text(encoding="utf-8"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            materials, parts = call_target(builder)(config)
        numeric = sorted({str(w.message) for w in caught if issubclass(w.category, RuntimeWarning)})
        if numeric:
            report.add("model.numeric_warnings", "WARNING",
                       "the builder raised numeric warnings (NaN or overflow may have changed the shape)",
                       warnings=numeric)
        else:
            report.add("model.numeric_warnings", "PASS", "the builder ran without numeric warnings")
        same = (materials.shape == character.model.shape and np.array_equal(materials, character.model)
                and np.array_equal(parts, character.part_ids))
        report.add("model.regenerate", "PASS" if same else "FAIL",
                   f"{builder} {'reproduces' if same else 'does not reproduce'} materials.npz and part_ids.npz")

    pieces = components(character.part_ids > 0)
    if len(pieces) == 1:
        report.add("model.connectivity", "PASS", f"one 26-connected model ({int(pieces[0].sum())} voxels)")
    else:
        names = {v: k for k, v in character.parts.items()}
        loose = [{"voxels": int(piece.sum()),
                  "parts": sorted({names[int(i)] for i in np.unique(character.part_ids[piece])})}
                 for piece in pieces[1:6]]
        report.add("model.connectivity", "FAIL", f"the model splits into {len(pieces)} pieces; "
                   "smaller pieces float free of the body", floating=loose)

    check_fragments(ctx)
    check_provenance(ctx)
    check_motions(ctx)


def check_fragments(ctx):
    """Report parts split into pieces by other parts' voxels: an ownership or contact candidate."""
    character, report = ctx.character, ctx.report
    names = {v: k for k, v in character.parts.items()}
    holders = {item["part"]: [item["hand"]] + item.get("through", []) for item in items(ctx).values()}
    for rule in ctx.quality.get("continuous", []):
        holders.setdefault(rule["part"], []).extend(rule.get("through", []))
    entries, masks = [], []
    for name, part_id in character.parts.items():
        mask = ctx.part_mask(name, *holders.get(name, []))
        for piece in components(mask)[1:]:
            touching = sorted({names[int(i)] for i in np.unique(character.part_ids[dilate(piece) & ~piece])
                               if i and names[int(i)] != name})
            entries.append({"part": name, "voxels": int(piece.sum()), "touches": touching,
                            "center_xyz": np.round(world_points(character, piece).mean(axis=0), 2).tolist()})
            masks.append(piece)
    if not entries:
        report.add("model.fragments", "PASS", "every part is one piece (items counted with their hands)")
        return
    for entry, seen in zip(entries, drawn_directions(ctx, masks)):
        entry["drawn_in"] = seen or "never drawn"
    stray = [e for e in entries if e["voxels"] < STRAY_VOXELS and e["drawn_in"] != "never drawn"]
    if stray:
        report.add("model.stray_pixels", "FAIL", f"{len(stray)} detached piece(s) under {STRAY_VOXELS} voxels "
                   "are drawn as stray pixels", pieces=stray)
    else:
        report.add("model.stray_pixels", "PASS", f"no detached piece under {STRAY_VOXELS} voxels is drawn")
    report.add("model.fragments", "WARNING",
               f"{len(entries)} part piece(s) are cut off from the rest of their part by other parts' voxels; "
               "a candidate for part ownership or contact review, not a rendering defect by itself",
               pieces=entries)


def check_provenance(ctx):
    settings = ctx.quality.get("provenance")
    if not settings:
        ctx.report.add("model.provenance", "SKIP", "no provenance files in the quality file")
        return
    palette = ctx.character.config["model"]["palette"]
    provenance = json.loads(resolve(ctx.quality_dir, settings["palette"]).read_text(encoding="utf-8"))["materials"]
    samples = json.loads(resolve(ctx.quality_dir, settings["samples"]).read_text(encoding="utf-8"))["materials"]
    names = [item["name"] for item in palette]
    if list(provenance) != names:
        ctx.report.add("model.provenance", "FAIL", "palette_provenance does not list the palette in order",
                       missing=sorted(set(names) - set(provenance)), extra=sorted(set(provenance) - set(names)))
        return
    differing = [item["name"] for item in palette
                 if provenance[item["name"]]["method"] == "extracted"
                 and any(item[tone] != samples[provenance[item["name"]]["source"]][tone]
                         for tone in ("shadow", "base", "light"))]
    methods = [entry["method"] for entry in provenance.values()]
    counts = {m: methods.count(m) for m in ("extracted", "adjusted", "derived")}
    if differing:
        ctx.report.add("model.provenance", "WARNING", "materials marked extracted differ from the sampled tones",
                       materials=differing)
    else:
        ctx.report.add("model.provenance", "PASS", f"every material has a color source {counts}; "
                       "extracted tones equal the samples")


def face_contacts(a, b):
    count = 0
    for axis in range(3):
        front, back = np.moveaxis(a, axis, 0), np.moveaxis(b, axis, 0)
        count += np.count_nonzero(front[:-1] & back[1:])
        count += np.count_nonzero(back[:-1] & front[1:])
    return int(count)


def check_motions(ctx):
    settings = ctx.quality.get("motions")
    if not settings:
        ctx.report.add("model.motions", "SKIP", "no motion sources in the quality file")
        return
    for mode, source in settings.items():
        if "clip" in source:
            expected = json.loads(resolve(ctx.quality_dir, source["clip"]).read_bytes())
            label = source["clip"]
        elif "same_as" in source:
            expected = load_character(resolve(ctx.quality_dir, source["same_as"])).motions[mode]
            label = f"the {mode} clip of {source['same_as']}"
        else:
            expected = call_target(source["call"])()
            label = f"{source['call']}()"
        same = ctx.character.motions[mode] == expected
        ctx.report.add(f"model.motion_{mode}", "PASS" if same else "FAIL",
                       f"{mode} clip {'equals' if same else 'differs from'} {label}")


# ---------------------------------------------------------------- rig and item checks

def items(ctx):
    """Held items by role. Defaults: the item in hand_R is main, the item in hand_L is off."""
    configured = ctx.quality.get("items")
    if configured:
        return configured
    roles = {"hand_R": "main", "hand_L": "off"}
    return {roles.get(a["hand"], part): {"part": part, "hand": a["hand"], "marker": a["marker"]}
            for part, a in ctx.character.config["rig"]["attachments"].items()}


def check_rig(ctx):
    report, character = ctx.report, ctx.character
    try:
        rig = Biped(character)
        joints, transforms = rig.pose("rest", 0)
        check_attachment(rig, joints, transforms)
    except (ValueError, KeyError) as error:
        report.add("rig.attachments", "FAIL", f"the biped rig rejects the character: {error}")
        return
    report.add("rig.attachments", "PASS", "the biped rig accepts the parts and items; rest items follow their hands")

    attachments = character.config["rig"]["attachments"]
    rest = character.config["rig"]["rest"]
    contract = {"main": "hand_R", "off": "hand_L"}
    problems, sides = [], {}
    for role, item in items(ctx).items():
        part = item["part"]
        attached = attachments.get(part)
        if attached != {"hand": item["hand"], "marker": item["marker"]}:
            problems.append(f"{role} {part}: quality says {item['hand']}/{item['marker']}, "
                            f"character.json says {attached}")
        if role in contract and item["hand"] != contract[role]:
            problems.append(f"{role} item {part} is in {item['hand']}; the project contract puts it in {contract[role]}")
        x = world_points(character, ctx.part_mask(part))[:, 0].mean()
        hand_x = world_points(character, ctx.part_mask(item["hand"]))[:, 0].mean()
        sides[part] = round(float(x), 2)
        if np.sign(x) != SIDES[item["hand"]] or np.sign(hand_x) != SIDES[item["hand"]]:
            problems.append(f"{part} (x = {x:.2f}) or {item['hand']} (x = {hand_x:.2f}) is not on the "
                            f"anatomical {'right' if SIDES[item['hand']] < 0 else 'left'}")
    report.add("rig.handedness", "FAIL" if problems else "PASS",
               "; ".join(problems) if problems else
               "main item in the right hand (x < 0), off item in the left (x > 0), as in character.json",
               item_centroid_x=sides)

    # A marker (e.g. a blade tip) may sit just past the last voxel: LARK's and BRAM's sword tips
    # are 1.0-1.2 units beyond the blade. Farther than MARKER_FAIL it belongs to something else.
    grid = character.source_grid
    distances = {}
    for item in items(ctx).values():
        points = world_points(character, ctx.part_mask(item["part"]))
        distances[item["marker"]] = round(float(np.linalg.norm(points - rest[item["marker"]], axis=1).min()), 2)
    far = [m for m, d in distances.items() if d > MARKER_FAIL]
    near = [m for m, d in distances.items() if MARKER_PASS < d <= MARKER_FAIL]
    report.add("rig.markers", "FAIL" if far else "WARNING" if near else "PASS",
               f"markers away from their items: {far}" if far else
               f"markers off the item surface: {near}" if near else
               f"item markers lie within {MARKER_PASS} units of their items",
               distance_to_nearest_voxel=distances)

    pairs = [(item["part"], item["hand"]) for item in items(ctx).values()] + LIMB_CHAIN
    pairs += [tuple(pair) for pair in ctx.quality.get("contacts", [])]
    contacts = {f"{a}-{b}": int((dilate(ctx.part_mask(a)) & ctx.part_mask(b)).sum()) for a, b in pairs}
    missing = [pair for pair, count in contacts.items() if count == 0]
    report.add("rig.contacts", "FAIL" if missing else "PASS",
               f"parts that do not touch: {missing}" if missing else "items touch their hands and the arms are joined",
               contact_voxels=contacts)

    for role, item in items(ctx).items():
        joined = ctx.part_mask(item["part"], item["hand"], *item.get("through", []))
        pieces = components(joined)
        status = "PASS" if len(pieces) == 1 else "FAIL"
        report.add(f"rig.item_{role}", status,
                   f"{item['part']} with {item['hand']} is one piece" if status == "PASS" else
                   f"{item['part']} splits into {len(pieces)} pieces even with its hand",
                   **({} if status == "PASS" else {"voxels": [int(p.sum()) for p in pieces]}))

    for rule in ctx.quality.get("continuous", []):
        item = ctx.part_mask(rule["part"])
        held = ctx.part_mask(rule["part"], *rule.get("through", []))
        rows = np.where(item.any(axis=(1, 2)))[0]
        gaps = [int(z) for z in range(rows.min(), rows.max() + 1) if not held[z].any()]
        bottom = float(grid.origin[2] + rows.min() * grid.spacing[2])
        floor = not rule.get("from_floor") or bottom <= grid.spacing[2] / 2
        top = float(grid.origin[2] + (rows.max() + 1) * grid.spacing[2])
        ok = not gaps and floor
        report.add(f"rig.continuous_{rule['part']}", "PASS" if ok else "FAIL",
                   f"{rule['part']} runs without a gap from z={bottom} to z={top}"
                   + (" and stands on the floor" if rule.get("from_floor") else "")
                   if ok else f"{rule['part']} has gaps at z slices {gaps[:10]} or does not reach the floor "
                   f"(lowest z={bottom})")

    for rule in ctx.quality.get("presence", []):
        mask = ctx.part_mask(rule["part"])
        if rule.get("materials"):
            mask &= np.isin(character.model, ctx.material_ids(rule["materials"]))
        problems = []
        count = int(mask.sum())
        if count < rule.get("min_voxels", 1):
            problems.append(f"{count} voxels < {rule.get('min_voxels', 1)}")
        if count:
            z = world_points(character, mask)[:, 2]
            low, high = float(z.min() - grid.spacing[2] / 2), float(z.max() + grid.spacing[2] / 2)
            if "lowest_z_at_most" in rule and low > rule["lowest_z_at_most"]:
                problems.append(f"lowest z {low} > {rule['lowest_z_at_most']}")
            if "highest_z_at_least" in rule and high < rule["highest_z_at_least"]:
                problems.append(f"highest z {high} < {rule['highest_z_at_least']}")
        report.add(f"rig.presence_{rule['label'].replace(' ', '_')}",
                   "FAIL" if problems else "PASS",
                   f"{rule['label']}: " + ("; ".join(problems) if problems else f"{count} voxels in range"))


# ---------------------------------------------------------------- sheet checks

def sheet_names(ctx, cell):
    standard = ctx.character.config["view"]["neutral_cell"]
    return ("idle.png", "metadata.json") if cell == standard else (f"idle-{cell}.png", f"idle-{cell}.json")


def check_sheets(ctx):
    if ctx.output is None:
        ctx.report.add("sheet", "SKIP", "no --out folder given")
        return
    for cell in ctx.cells():
        check_sheet(ctx, cell)


def check_sheet(ctx, cell):
    report, character = ctx.report, ctx.character
    prefix = f"sheet{cell}"
    image_name, layout_name = sheet_names(ctx, cell)
    try:
        seen = view_for_cell(character, cell)
    except ValueError as error:
        report.add(f"{prefix}.view", "FAIL", str(error))
        return
    paths = [ctx.output / image_name, ctx.output / layout_name]
    if not all(path.exists() for path in paths):
        report.add(f"{prefix}.files", "FAIL", f"missing {[p.name for p in paths if not p.exists()]} in {ctx.output}")
        return

    layout = json.loads(paths[1].read_bytes())
    view = seen.config["view"]
    expected = neutral_layout(seen, Renderer(seen))
    problems = []
    if list(view["directions"]) != DIRECTIONS:
        problems.append(f"view.directions {list(view['directions'])} differ from the project order {DIRECTIONS}")
    if layout.get("neutral") != expected:
        problems.append(f"layout {layout.get('neutral')} differs from {expected}")
    if layout.get("camera") != view["camera"]:
        problems.append(f"camera {layout.get('camera')} differs from {view['camera']}")
    if image_name == "idle.png" and layout.get("parts") != character.parts:
        problems.append("parts differ from rig.parts")
    report.add(f"{prefix}.layout", "FAIL" if problems else "PASS",
               "; ".join(problems) if problems else
               f"direction order {DIRECTIONS}, cell {expected['cell']}, anchor {expected['anchor']}, camera match")

    with Image.open(paths[0]) as image:
        mode, size = image.mode, image.size
        sheet = image.convert("RGBA")
    if mode != "RGBA" or size != (cell * len(DIRECTIONS), cell):
        report.add(f"{prefix}.image", "FAIL", f"{image_name} is {mode} {size}, expected RGBA "
                   f"{(cell * len(DIRECTIONS), cell)}")
        return
    report.add(f"{prefix}.image", "PASS", f"{image_name} is RGBA {size[0]}x{size[1]} (8 cells of {cell}x{cell})")
    frames = {d: sheet.crop((i * cell, 0, (i + 1) * cell, cell)) for i, d in enumerate(DIRECTIONS)}

    partial = [d for d, f in frames.items() if not set(np.unique(np.asarray(f)[..., 3])) <= {0, 255}]
    empty = [d for d, f in frames.items() if f.getbbox() is None]
    report.add(f"{prefix}.alpha", "FAIL" if partial or empty else "PASS",
               f"partial alpha in {partial}, empty cells {empty}" if partial or empty else
               "alpha is 0 or 255 and every cell has a figure")
    margins = {d: min(b[0], b[1], cell - b[2], cell - b[3]) for d, f in frames.items() if (b := f.getbbox())}
    tight = [d for d, m in margins.items() if m < 1]
    low = min(margins, key=margins.get) if margins else None
    report.add(f"{prefix}.margins", "FAIL" if tight else "PASS",
               f"no transparent margin in {tight}" if tight else
               f"at least 1 px transparent margin; smallest {margins[low]} px in {low}", margins=margins)

    redrawn = {d: ctx.render(cell, d) for d in DIRECTIONS}
    differing = [d for d in DIRECTIONS if redrawn[d][0].tobytes() != frames[d].tobytes()]
    report.add(f"{prefix}.redraw", "FAIL" if differing else "PASS",
               f"cells that are not the render of the model: {differing}" if differing else
               "every cell equals a fresh render of the committed model with the shared renderer")

    duplicates = [(a, b) for i, a in enumerate(DIRECTIONS) for b in DIRECTIONS[i + 1:]
                  if frames[a].tobytes() == frames[b].tobytes()]
    report.add(f"{prefix}.distinct", "WARNING" if duplicates else "PASS",
               f"identical cells {duplicates}" if duplicates else "the eight cells are all different")
    yaw = view["directions"]
    pairs = [(a, b) for i, a in enumerate(DIRECTIONS) for b in DIRECTIONS[i + 1:] if (yaw[a] + yaw[b]) % 360 == 0]
    mirrored = [f"{a}/{b}" for a, b in pairs if frames[a].tobytes() == ImageOps.mirror(frames[b]).tobytes()]
    report.add(f"{prefix}.mirror", "WARNING" if mirrored else "PASS",
               f"cells equal to the mirror of the opposite direction: {mirrored}" if mirrored else
               f"no cell equals the mirror of its opposite ({', '.join(f'{a}/{b}' for a, b in pairs)})")

    check_screen_sides(ctx, cell, seen, redrawn, frames)
    check_visibility(ctx, cell, redrawn)
    check_published(ctx, cell, paths)


def check_screen_sides(ctx, cell, seen, redrawn, frames):
    """Each item must be drawn on the screen side its 3D position projects to."""
    view = seen.config["view"]
    scale = view["camera"]["pixels_per_unit"]
    anchor_x = neutral_layout(seen, Renderer(seen))["anchor"][0]
    sides, wrong = {}, []
    for item in items(ctx).values():
        part_id = ctx.character.parts[item["part"]]
        center = world_points(ctx.character, ctx.part_mask(item["part"])).mean(axis=0)
        for direction in DIRECTIONS:
            theta = math.radians(view["directions"][direction])
            expected = float(center @ np.array([math.cos(theta), math.sin(theta), 0])) * scale
            columns = np.where(redrawn[direction][2] == part_id)[1]
            if len(columns) < 4 or abs(expected) < 2:
                continue
            drawn = columns.mean() + .5 - anchor_x
            sides.setdefault(direction, {})[item["part"]] = "left" if drawn < 0 else "right"
            if np.sign(drawn) != np.sign(expected):
                wrong.append(f"{direction} {item['part']}")
    ctx.report.add(f"sheet{cell}.screen_side", "FAIL" if wrong else "PASS",
                   f"items drawn on the wrong side: {wrong}" if wrong else
                   "items are drawn on the side their 3D position projects to "
                   "(checked where the projection is 2 px or more off the anchor)", sides=sides)


def check_visibility(ctx, cell, redrawn):
    for rule in ctx.quality.get("visibility", []):
        part_id = ctx.character.parts[rule["part"]]
        materials = ctx.material_ids(rule["materials"]) if rule.get("materials") else None
        directions = DIRECTIONS if rule.get("directions", "all") == "all" else rule["directions"]
        minimum = rule["min_px"]
        if isinstance(minimum, dict):
            if str(cell) not in minimum:
                continue
            minimum = minimum[str(cell)]
        counts = {}
        for direction in directions:
            _, ids, parts = redrawn[direction]
            seen = parts == part_id
            if materials is not None:
                seen &= np.isin(ids, materials)
            counts[direction] = int(seen.sum())
        low = [d for d, n in counts.items() if n < minimum]
        status = ("FAIL" if rule.get("severity", "fail") == "fail" else "WARNING") if low else "PASS"
        ctx.report.add(f"sheet{cell}.visible_{rule['label'].replace(' ', '_')}", status,
                       f"{rule['label']}: below {minimum} px in {low}" if low else
                       f"{rule['label']}: at least {minimum} px in {', '.join(directions)}", px=counts)


def check_published(ctx, cell, paths):
    prefix = f"sheet{cell}.published"
    if ctx.published is None:
        ctx.report.add(prefix, "SKIP", "no published folder to compare with")
        return
    targets = [ctx.published / p.name for p in paths]
    if not all(t.exists() for t in targets):
        ctx.report.add(prefix, "FAIL", f"published copy missing: {[t.name for t in targets if not t.exists()]}")
        return
    with Image.open(paths[0]) as baked, Image.open(targets[0]) as published:
        same_rgba = (baked.size == published.size
                     and baked.convert("RGBA").tobytes() == published.convert("RGBA").tobytes())
    same_json = json.loads(paths[1].read_bytes()) == json.loads(targets[1].read_bytes())
    same_bytes = {p.name: p.read_bytes() == t.read_bytes() for p, t in zip(paths, targets)}
    ok = same_rgba and same_json
    ctx.report.add(prefix, "PASS" if ok else "FAIL",
                   f"{paths[0].name} decoded RGBA and {paths[1].name} match {ctx.published}" if ok else
                   f"differs from {ctx.published}: RGBA equal {same_rgba}, JSON equal {same_json}",
                   file_bytes_equal=same_bytes)


# ---------------------------------------------------------------- entry points

def verify(character_path, output=None, quality_path=None, published="quality"):
    """Run every check and return the Report. published: 'quality' (from the quality file), a folder, or None."""
    character_path = Path(character_path).resolve()
    report = Report()
    quality_path = Path(quality_path) if quality_path else character_path.parent / "quality.json"
    quality = {}
    if quality_path.exists():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    else:
        report.add("quality", "WARNING", f"no quality file at {quality_path}; using defaults "
                   "(items from rig.attachments, standard cell, no visibility rules)")
    config = json.loads(character_path.read_text(encoding="utf-8"))
    bad = list(non_finite(config))
    report.add("model.numbers", "FAIL" if bad else "PASS",
               f"non-finite numbers in character.json: {bad}" if bad else "character.json numbers are finite")
    try:
        character = load_character(character_path)
    except (ValueError, KeyError, OSError) as error:
        report.add("model.load", "FAIL", f"the shared loader rejects the character: {error}")
        return report
    report.add("model.load", "PASS", "the shared loader accepts the manifest, NPZ shapes, IDs and palette")
    if published == "quality":
        published = resolve(quality_path.parent, quality.get("published"))
    ctx = Context(character_path, character, quality, quality_path.parent,
                  Path(output).resolve() if output else None,
                  Path(published).resolve() if published else None, report)
    if not check_references(ctx):
        return report
    check_model(ctx)
    check_rig(ctx)
    check_sheets(ctx)
    for spec in quality.get("extra_checks", []):
        call_target(spec)(ctx)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--character", required=True, type=Path, help="path to character.json")
    parser.add_argument("--out", type=Path, help="folder with the idle sheets (python -m spritestack --modes idle)")
    parser.add_argument("--quality", type=Path, help="quality file (default: quality.json next to character.json)")
    parser.add_argument("--published", type=Path, help="compare with this folder instead of the quality file's")
    parser.add_argument("--no-published", action="store_true", help="skip the comparison with published copies")
    parser.add_argument("--json", type=Path, help="also write the results to this JSON file")
    parser.add_argument("--verbose", action="store_true", help="print the details of passing checks too")
    args = parser.parse_args()
    published = None if args.no_published else (args.published or "quality")
    report = verify(args.character, args.out, args.quality, published)
    report.print(args.verbose)
    if args.json:
        args.json.write_text(json.dumps(report.to_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raise SystemExit(1 if report.failed() else 0)


if __name__ == "__main__":
    main()
