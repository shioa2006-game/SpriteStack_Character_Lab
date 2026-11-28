"""Regression cases for elapsed time, anchor alignment and transient markers."""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from research.attack import compare_motion as compare
from research.attack.trajectory_plot import runs


def fixture(folder, cell, anchor, times, rows, name):
    folder.mkdir()
    w, h = cell
    sheet = Image.new("RGBA", (w * len(times), h * len(rows)))
    poses = []
    for i in range(len(times)):
        pose = {"body": [0, i, 2]}
        if i != 1:
            pose[name] = [1, i+2, 4]
        poses.append(pose)
        for j, direction in enumerate(rows):
            color = (40 + 10*i, 30 + 10*compare.DIRECTIONS.index(direction), 60, 255)
            for x, y in (anchor, (0, 0), (w-1, h-1)):
                sheet.putpixel((i*w+x, j*h+y), color)
    sheet.save(folder / "attack.png")
    layout = dict(columns=len(times), rows=rows, cell=cell, anchor=anchor, durations_ms=times,
                  phase_names=["start", "wind", "hit", "rest"][:len(times)],
                  events=[dict(name="hit", frame=2, time_ms=sum(times[:2]))])
    (folder / "metadata.json").write_text(json.dumps({"animations": {"attack": layout}}))
    (folder / "joints.json").write_text(json.dumps({"attack": poses}))


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(".phase1")
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.before, self.after, self.out = [root / name for name in ("before", "after", "out")]
        fixture(self.before, [41, 33], [36, 8], [34, 41, 25], compare.DIRECTIONS, "tip")
        fixture(self.after, [27, 47], [5, 40], [27, 9, 80, 29], compare.DIRECTIONS[::-1], "end")

    def invoke(self, *options):
        args = ["compare_motion", "--before", str(self.before), "--after", str(self.after),
                "--out", str(self.out), "--markers", "tip=end", "body", "--relative-to", "body", *options]
        with patch("sys.argv", args):
            compare.main()

    def test_timing_geometry_and_coordinates(self):
        self.invoke("--phases", "wind", "hit=rest", "--directions", "E", "--front")
        old, new = [compare.Bake.read(p) for p in (self.before, self.after)]
        # Union extends further than either input, on both axes.
        self.assertEqual(compare.geometry([old, new]), ((58, 65), (36, 40)))
        with Image.open(self.out / "comparison.gif") as gif:
            expected = [(0, 30), (27, 0), (34, 10), (36, 40), (75, 20), (100, 20), (116, 30)]
            visible = [(t, d) for t, d in expected if d]
            self.assertEqual(gif.n_frames, len(visible))
            for i, (ms, duration) in enumerate(visible):
                gif.seek(i)
                self.assertEqual(gif.info["duration"], duration)
                page = gif.convert("RGB")
                for v, bake in enumerate((old, new)):
                    f = bake.frame_at(ms)
                    for j in range(8):
                        color = (40+10*f, 30+10*j, 60)
                        x, y = 85+j*58+36, 20+v*65+40
                        ax, ay = bake.layout["anchor"]
                        w, h = bake.layout["cell"]
                        for px, py in ((x, y), (x-ax, y-ay), (x-ax+w-1, y-ay+h-1)):
                            self.assertEqual(page.getpixel((px, py)), color)
        with (self.out / "trajectory.csv").open(newline="") as stream:
            rows = [r for r in csv.DictReader(stream) if r["marker"] == "end"]
        self.assertEqual([r["x"] for r in rows], ["1", "", "1", "1"])
        self.assertEqual([r["dy"] for r in rows], ["", "", "", "1"])
        self.assertEqual([r["relative_y"] for r in rows], ["2", "", "2", "2"])
        self.assertEqual(rows[2]["events"], "hit")
        self.assertEqual(rows[2]["start_ms"], "36")
        self.assertEqual(list(runs([None, (1, 2), None, (3, 4), (5, 6), None])),
                         [[(1, 2)], [(3, 4), (5, 6)]])

    def test_default_poses_and_one_sided_marker(self):
        self.invoke("--markers", "tip", "--relative-to", "end")
        with (self.out / "trajectory.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([r["x"] for r in rows if r["version"] == "after"], [""] * 4)
        self.assertTrue(all(r["relative_x"] == "" for r in rows))
        bakes = [compare.Bake.read(p) for p in (self.before, self.after)]
        self.assertEqual(compare.pose_selection(bakes, None, None),
                         [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3)])
        saved = (self.out / "trajectory.csv").read_bytes()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.invoke("--frames", "1")
        self.assertEqual((self.out / "trajectory.csv").read_bytes(), saved)

    def test_reject_bad_input_without_publishing(self):
        def rejected(pattern, *options):
            error = io.StringIO()
            with redirect_stderr(error), self.assertRaises(SystemExit) as exc:
                self.invoke(*options)
            self.assertEqual(exc.exception.code, 2)
            self.assertIn(pattern, error.getvalue())
            self.assertFalse(self.out.exists())

        rejected("outside clip", "--frames", "4")
        rejected("missing or ambiguous", "--phases", "typo")
        rejected("unknown marker", "--markers", "typo")
        meta = self.after / "metadata.json"
        original = json.loads(meta.read_bytes())
        for key, value, message in (("rgba_sha256", "invalid", "sha256"), ("columns", 2, "columns"),
                                    ("cell", [26, 47], "dimensions"), ("durations_ms", [8]*4, "time_ms"),
                                    ("rows", ["S"]*8, "direction")):
            changed = dict(original["animations"]["attack"], **{key: value})
            meta.write_text(json.dumps({"animations": {"attack": changed}}))
            rejected(message)
        changed = dict(original["animations"]["attack"], phase_names=["start", "wind", "hit", "start"])
        meta.write_text(json.dumps({"animations": {"attack": changed}}))
        rejected("ambiguous", "--phases", "start")
        meta.write_text(json.dumps(original))
        joints = self.after / "joints.json"
        poses = json.loads(joints.read_bytes())
        poses["attack"][0]["body"][2] = "bad"
        joints.write_text(json.dumps(poses))
        rejected("finite XYZ")
        joints.unlink()
        rejected("joints.json")


if __name__ == "__main__":
    unittest.main()
