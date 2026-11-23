"""Rigid biped poses and two-link IK for the configured walk and attack."""

import math

import numpy as np


def vec(values):
    return np.array(values, dtype=float)


def unit(v):
    return v / max(1e-10, np.linalg.norm(v))


def rotate(axis, degrees):
    x, y, z = unit(vec(axis))
    angle = math.radians(degrees)
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * skew + (1 - math.cos(angle)) * (skew @ skew)


def align(a, b):
    a, b = unit(a), unit(b)
    cross = np.cross(a, b)
    dot = np.clip(a @ b, -1, 1)
    if np.linalg.norm(cross) < 1e-8:
        if dot > 0:
            return np.eye(3)
        perpendicular = [0, 1, 0] if abs(a[1]) < .9 else [0, 0, 1]
        return rotate(np.cross(a, perpendicular), 180)
    return rotate(cross, math.degrees(math.acos(dot)))


def about(rotation, source, target):
    return rotation, target - rotation @ source


def transform(matrix, point):
    rotation, translation = matrix
    return rotation @ point + translation


def segment(a, b, c, d):
    return about(align(b - a, d - c), a, c)


def solve(a, c, length_a, length_b, pole):
    direction = unit(c - a)
    reach = np.clip(np.linalg.norm(c - a), abs(length_a - length_b) + .001,
                    length_a + length_b - .035)
    c = a + direction * reach
    bend = pole - a
    perpendicular = unit(bend - direction * (bend @ direction))
    along = (length_a * length_a - length_b * length_b + reach * reach) / (2 * reach)
    height = math.sqrt(max(0, length_a * length_a - along * along))
    return a + along * direction + height * perpendicular, c


# Optional walk.tuning keys that scale the shared walk clip for one character's body.
# Absent keys leave the clip unchanged, so existing characters bake exactly as before.
WALK_SCALES = {
    "stride_scale": ("forward_each_frame", "swing_forward"),
    "swing_lift_scale": ("swing_lift",),
    "root_bob_scale": ("root_bob",),
    "root_sway_scale": ("root_sway",),
    "twist_scale": ("twist",),
}


def walk_clip(clip, tuning):
    """Return the walk clip as this character walks it: the shared clip with the
    tuning's optional scale factors and root_level_offset applied."""
    scaled = dict(clip)
    for key, fields in WALK_SCALES.items():
        if key in tuning:
            factor = float(tuning[key])
            if not factor > 0:
                raise ValueError(f"walk.tuning.{key} must be positive")
            for field in fields:
                value = clip[field]
                scaled[field] = ([round(v * factor, 6) for v in value] if isinstance(value, list)
                                 else round(value * factor, 6))
    if "root_level_offset" in tuning:
        scaled["root_level"] = round(clip["root_level"] + float(tuning["root_level_offset"]), 6)
    if "torso_lean" in tuning:
        scaled["torso_lean"] = float(tuning["torso_lean"])
    return scaled


def cyclic(values, at):
    """Linear interpolation in a cyclic list at a fractional index."""
    count = len(values)
    low = math.floor(at)
    t = at - low
    return (1 - t) * values[low % count] + t * values[(low + 1) % count]


# walk.head: how the head rides on the neck during the walk. Characters without the
# block keep the older head (a share of the neck's sway and the root bob, no turn), so
# their walks bake exactly as before. See README.md ("walk.head"). The head is drawn
# one ray per pixel, and its eyes and mouth are single voxels about 0.6 px across: a
# shift of half a voxel or a small turn changes which voxels the rays hit, and the face
# can lose its eyes. So the head moves away from the older head position only in whole
# steps of snap units (1.0 = two posed voxels, about one pixel), and the turns default to 0.
HEAD_DEFAULTS = {
    "snap": 1.0,
    "follow": [1.0, 1.0, 1.0],
    "forward_offset": 0.0,
    "bob": 0.0,
    "surge": 0.0,
    "sway": 0.0,
    "lag_frames": 0.25,
    "yaw_follow": 0.0,
    "pitch_follow": 0.0,
    "nod_deg": 0.0,
    "tilt_deg": 0.0,
}
HEAD_LIMITS = {
    "snap": (0, 2), "follow": (0, 1.5), "forward_offset": (-1, 1), "bob": (0, 1.5), "surge": (-1, 1), "sway": (-1, 1),
    "lag_frames": (0, 3), "yaw_follow": (0, 1), "pitch_follow": (0, 1), "nod_deg": (-6, 6), "tilt_deg": (-6, 6),
}


def head_settings(walk):
    """The walk.head block with its defaults filled in, or None when it is absent."""
    if "head" not in walk:
        return None
    given = walk["head"]
    unknown = set(given) - set(HEAD_DEFAULTS) - {"description"}
    if unknown:
        raise ValueError(f"walk.head: unknown keys {sorted(unknown)}")
    head = {key: given.get(key, value) for key, value in HEAD_DEFAULTS.items()}
    head["follow"] = [float(v) for v in np.broadcast_to(np.asarray(head["follow"], dtype=float), 3)]
    for key, (low, high) in HEAD_LIMITS.items():
        values = head[key] if key == "follow" else [head[key]]
        if not all(low <= float(v) <= high for v in values):
            raise ValueError(f"walk.head.{key} must be within [{low}, {high}]")
    return head


def head_rhythm(clip, lag):
    """Per frame, lag frames late: (depth, side). depth is the root bob as a share of its
    deepest value (1 at the lowest frame), side the root sway as a share of its widest."""
    bob, sway = clip["root_bob"], clip["root_sway"]
    deepest, widest = min(bob), max(abs(v) for v in sway)
    depth = [v / deepest if deepest < 0 else 0. for v in bob]
    side = [v / widest if widest > 0 else 0. for v in sway]
    return [(cyclic(depth, index - lag), cyclic(side, index - lag)) for index in range(len(bob))]


def per_side(value, side):
    """A tuning value given once for both sides, or as {"R": ..., "L": ...}."""
    return value[side] if isinstance(value, dict) else value


def outward(offset, sign):
    return vec([sign * offset[0], offset[1], offset[2]])


class Biped:
    def __init__(self, character):
        self.config = character.config
        self.motions = character.motions
        self.walk_clip = walk_clip(character.motions["walk"], self.config["walk"]["tuning"])
        if "fps" in self.config["walk"]:
            self.walk_clip["fps"] = self.config["walk"]["fps"]
        self.head = head_settings(self.config["walk"])
        self.head_rhythm = head_rhythm(self.walk_clip, self.head["lag_frames"]) if self.head else None
        self.parts = character.parts
        self.rest = {name: vec(point) for name, point in self.config["rig"]["rest"].items()}
        self.attachments = self.config["rig"]["attachments"]
        limb_parts = ("thigh", "shin", "boot", "upper", "fore", "hand")
        body_parts = {"head", "chest", "pelvis"} | {
            f"{part}_{side}" for part in limb_parts for side in ("R", "L")
        }
        if body_parts & self.attachments.keys() or self.parts.keys() != body_parts | self.attachments.keys():
            raise ValueError("rig parts must be the biped body parts and its configured attachments")
        for attachment in self.attachments.values():
            if attachment["hand"] not in ("hand_R", "hand_L") or attachment["marker"] not in self.rest:
                raise ValueError("each attachment needs a biped hand and a defined rest marker")

    def pose(self, mode, index):
        joints = {name: point.copy() for name, point in self.rest.items()}
        transforms = {name: (np.eye(3), np.zeros(3)) for name in self.parts}
        if mode == "rest":
            return joints, transforms
        if mode == "walk":
            self._walk(index, joints, transforms)
        elif mode == "breathe":
            key = self.motions[mode]["keys"][index]
            pivot = self.rest["pelvis"]
            lift = key["lift"] * self.config[mode]["lift_scale"]
            lean = key["lean"] * self.config[mode]["lean_scale"]
            upper = about(rotate([1, 0, 0], lean), pivot, pivot + vec([0, 0, lift]))
            # Rib cage, neck, arms and grips rise together over the resting hips.
            for part in ("chest", "head", "upper_R", "fore_R", "hand_R", "upper_L", "fore_L", "hand_L"):
                transforms[part] = upper
            for name in ("chest", "neck", "head", "shoulder_R", "elbow_R", "hand_R",
                         "shoulder_L", "elbow_L", "hand_L"):
                joints[name] = transform(upper, self.rest[name])
        elif mode == "attack":
            key = self.motions[mode]["keys"][index]
            if key:
                self._attack(key, joints, transforms)
        else:
            raise ValueError(f"unknown pose mode: {mode}")

        for part, attachment in self.attachments.items():
            hand = attachment["hand"]
            marker = attachment["marker"]
            transforms[part] = transforms[hand]
            joints[marker] = transform(transforms[part], self.rest[marker])
        return joints, transforms

    def _torso(self, root, yaw, lean, hip_yaw_scale, joints, transforms):
        pivot = self.rest["pelvis"]
        pelvis = rotate([0, 0, 1], yaw * hip_yaw_scale)
        chest = rotate([0, 0, 1], yaw) @ rotate([1, 0, 0], -lean)
        transforms["pelvis"] = about(pelvis, pivot, pivot + root)
        transforms["chest"] = about(chest, pivot, pivot + root)
        joints["pelvis"] = transform(transforms["pelvis"], pivot)
        for name in ("chest", "neck"):
            joints[name] = transform(transforms["chest"], self.rest[name])

    def _leg(self, side, ankle_target, pitch, pole_offset, joints, transforms):
        suffix = "_" + side
        hip, knee, ankle = (name + suffix for name in ("hip", "knee", "ankle"))
        base_hip, base_knee, base_ankle = (self.rest[name] for name in (hip, knee, ankle))
        joints[hip] = transform(transforms["pelvis"], base_hip)
        joints[knee], joints[ankle] = solve(
            joints[hip], ankle_target, np.linalg.norm(base_knee - base_hip),
            np.linalg.norm(base_ankle - base_knee), joints[hip] + pole_offset)
        transforms["thigh" + suffix] = segment(base_hip, base_knee, joints[hip], joints[knee])
        transforms["shin" + suffix] = segment(base_knee, base_ankle, joints[knee], joints[ankle])
        boot = transforms["boot" + suffix] = about(rotate([1, 0, 0], pitch),
                                                    base_ankle, joints[ankle])
        joints["toe" + suffix] = transform(boot, self.rest["toe" + suffix])

    def _arm(self, side, shoulder, hand_target, wrist, pole_offset, joints, transforms):
        suffix = "_" + side
        shoulder_name, elbow, hand = (name + suffix for name in ("shoulder", "elbow", "hand"))
        base_shoulder, base_elbow, base_hand = (self.rest[name] for name in (shoulder_name, elbow, hand))
        joints[shoulder_name] = shoulder
        joints[elbow], joints[hand] = solve(
            shoulder, hand_target, np.linalg.norm(base_elbow - base_shoulder),
            np.linalg.norm(base_hand - base_elbow), shoulder + pole_offset)
        transforms["upper" + suffix] = segment(base_shoulder, base_elbow, shoulder, joints[elbow])
        transforms["fore" + suffix] = segment(base_elbow, base_hand, joints[elbow], joints[hand])
        transforms[hand] = about(wrist, base_hand, joints[hand])

    def _walk(self, index, joints, transforms):
        clip = self.walk_clip
        tuning = self.config["walk"]["tuning"]
        bob = clip["root_bob"][index]
        yaw = clip["twist"][index]
        root = vec([clip["root_sway"][index], 0, clip["root_level"] + bob])
        self._torso(root, yaw, clip["torso_lean"], tuning["hip_yaw_scale"], joints, transforms)

        neck = self.rest["neck"]
        if self.head is None:
            transforms["head"] = about(np.eye(3), neck, neck + self._legacy_head(bob, joints["neck"]))
        else:
            transforms["head"] = self._walk_head(index, yaw, bob, joints["neck"])
        joints["head"] = transform(transforms["head"], self.rest["head"])

        for side, sign in (("R", -1), ("L", 1)):
            stance = clip["contact"]["inclusive_stance_cyclic"][side]
            local = (index - stance[0]) % len(clip["poses"])
            ankle = self.rest["ankle_" + side].copy()
            ankle[0] += sign * clip["track_offset"]
            if local < len(stance):
                ankle[1] = tuning["stance_start_y"] - clip["forward_each_frame"] * local
                pitch = 0
            else:
                swing = local - len(stance)
                ankle[1] = clip["swing_forward"][swing]
                ankle[2] += clip["swing_lift"][swing]
                pitch = clip["swing_pitch"][swing]
            self._leg(side, ankle, pitch, outward(tuning["knee_pole"], sign), joints, transforms)
            if local < len(stance) and np.linalg.norm(joints["ankle_" + side] - ankle) >= 1e-6:
                raise ValueError(f"unreachable walk stance ankle: frame {index}, side {side}")

            shoulder = transform(transforms["chest"], self.rest["shoulder_" + side])
            swing = clip["right_arm_swing"][index] * tuning["arm_swing_scale"][side]
            hand = self.rest["hand_" + side] + root + vec([
                sign * per_side(tuning["hand_outward"], side), swing,
                abs(swing) * tuning["hand_lift_scale"] + per_side(tuning["hand_lift"], side),
            ])
            pitch = (per_side(tuning.get("wrist_pitch", 0), side)
                     - swing * per_side(tuning["wrist_pitch_scale"], side))
            wrist = (rotate([1, 0, 0], pitch)
                     @ rotate([0, 0, 1], yaw * tuning["wrist_yaw_scale"]))
            self._arm(side, shoulder, hand, wrist, outward(tuning["elbow_pole"], sign),
                      joints, transforms)

    def _legacy_head(self, bob, posed_neck):
        """Translation of the head used without walk.head: a share of the neck's sway and
        of the root bob, a fixed forward offset."""
        tuning, neck = self.config["walk"]["tuning"], self.rest["neck"]
        return vec([(posed_neck - neck)[0] * tuning["head_lateral_scale"], tuning["head_forward_offset"],
                    self.walk_clip["root_level"] + bob * tuning["head_bob_scale"]])

    def _walk_head(self, index, yaw, bob, posed_neck):
        """The head rides on the neck joint (a share of its sway, lean and bob) and, lag
        frames behind the body, settles down and forward with the root bob and shifts
        sideways with the sway. The difference from the older head at rest is rounded
        to whole snap steps. Optional small turns about the neck: a share of the chest's twist
        and lean, a nod with the bob and a sideways tilt with the sway."""
        head = self.head
        depth, side = self.head_rhythm[index]
        neck = self.rest["neck"]
        offset = (vec(head["follow"]) * (posed_neck - neck)
                  + vec([head["sway"] * side, head["forward_offset"] + head["surge"] * depth,
                         -head["bob"] * depth]))
        if head["snap"] > 0:
            # The older head at rest: no sway, no bob. A whole-step move from it shifts
            # the head voxels exactly, so the face is drawn as in the older walk.
            base = self._legacy_head(0, neck)
            offset = base + head["snap"] * np.floor((offset - base) / head["snap"] + .5)
        pitch = self.walk_clip["torso_lean"] * head["pitch_follow"] + head["nod_deg"] * depth
        rotation = (rotate([0, 0, 1], yaw * head["yaw_follow"]) @ rotate([1, 0, 0], -pitch)
                    @ rotate([0, 1, 0], head["tilt_deg"] * side))
        return about(rotation, neck, neck + offset)

    def _attack(self, key, joints, transforms):
        tuning = self.config["attack"]["tuning"]
        root, yaw, lean = vec(key["root"]), key["yaw"], key["lean"]
        self._torso(root, yaw, lean, tuning["hip_yaw_scale"], joints, transforms)

        head = (rotate([0, 0, 1], yaw * tuning["head_yaw_scale"])
                @ rotate([1, 0, 0], -lean * tuning["head_lean_scale"]))
        neck = joints["neck"]
        if snap := tuning.get("head_snap"):
            delta = (neck - self.rest["neck"]) * vec(tuning.get("head_follow", [1, 1, 1]))
            neck = self.rest["neck"] + snap * np.floor(delta / snap + .5)
        transforms["head"] = about(head, self.rest["neck"], neck)
        joints["head"] = transform(transforms["head"], self.rest["head"])

        for side, sign in (("R", -1), ("L", 1)):
            ankle = self.rest["ankle_" + side].copy()
            if side == tuning["step_side"]:
                ankle[0] += sign * key.get("front_outward", 0)
                ankle[1] += key["front_step"]
                ankle[2] += key.get("front_lift", 0)
            self._leg(side, ankle, 0, outward(tuning["knee_pole"], sign), joints, transforms)

            shoulder = transform(transforms["chest"], self.rest["shoulder_" + side])
            if side == tuning["main_hand_side"]:
                hand = vec(key["hand_" + side])
                axis = key["aim"] if "aim" in key else key["blade"]
                wrist = align(vec(tuning["weapon_axis"]), vec(axis))
                if roll := float(key.get("wrist_roll", 0)):
                    wrist = rotate(axis, roll) @ wrist
                elbow_pole = vec(key["elbow_pole_" + side])
            else:
                hand = self.rest["hand_" + side] + root + vec(key["support_delta"] if "aim" in key else key["shield_delta"]) + vec([
                    0, yaw * tuning["support_yaw_offset"], tuning["support_hand_lift"],
                ])
                wrist = (rotate([0, 0, 1], yaw * tuning["support_wrist_yaw_scale"])
                         @ rotate([1, 0, 0], key.get("support_pitch", tuning["support_wrist_pitch"])))
                elbow_pole = vec(tuning["support_elbow_pole"])
            self._arm(side, shoulder, hand, wrist, elbow_pole, joints, transforms)
