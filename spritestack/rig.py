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


def outward(offset, sign):
    return vec([sign * offset[0], offset[1], offset[2]])


class Biped:
    def __init__(self, character):
        self.config = character.config
        self.motions = character.motions
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
        clip = self.motions["walk"]
        tuning = self.config["walk"]["tuning"]
        bob = clip["root_bob"][index]
        yaw = clip["twist"][index]
        root = vec([clip["root_sway"][index], 0, clip["root_level"] + bob])
        self._torso(root, yaw, clip["torso_lean"], tuning["hip_yaw_scale"], joints, transforms)

        neck = self.rest["neck"]
        offset = vec([(joints["neck"] - neck)[0] * tuning["head_lateral_scale"],
                      tuning["head_forward_offset"], clip["root_level"] + bob * tuning["head_bob_scale"]])
        transforms["head"] = about(np.eye(3), neck, neck + offset)
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
                sign * tuning["hand_outward"], swing,
                abs(swing) * tuning["hand_lift_scale"] + tuning["hand_lift"],
            ])
            wrist = (rotate([1, 0, 0], -swing * tuning["wrist_pitch_scale"])
                     @ rotate([0, 0, 1], yaw * tuning["wrist_yaw_scale"]))
            self._arm(side, shoulder, hand, wrist, outward(tuning["elbow_pole"], sign),
                      joints, transforms)

    def _attack(self, key, joints, transforms):
        tuning = self.config["attack"]["tuning"]
        root, yaw, lean = vec(key["root"]), key["yaw"], key["lean"]
        self._torso(root, yaw, lean, tuning["hip_yaw_scale"], joints, transforms)

        head = (rotate([0, 0, 1], yaw * tuning["head_yaw_scale"])
                @ rotate([1, 0, 0], -lean * tuning["head_lean_scale"]))
        transforms["head"] = about(head, self.rest["neck"], joints["neck"])
        joints["head"] = transform(transforms["head"], self.rest["head"])

        for side, sign in (("R", -1), ("L", 1)):
            ankle = self.rest["ankle_" + side].copy()
            if side == tuning["step_side"]:
                ankle[1] += key["front_step"]
                ankle[2] += key.get("front_lift", 0)
            self._leg(side, ankle, 0, outward(tuning["knee_pole"], sign), joints, transforms)

            shoulder = transform(transforms["chest"], self.rest["shoulder_" + side])
            if side == tuning["main_hand_side"]:
                hand = vec(key["hand_" + side])
                wrist = align(vec(tuning["weapon_axis"]), vec(key["blade"]))
                elbow_pole = vec(key["elbow_pole_" + side])
            else:
                hand = self.rest["hand_" + side] + root + vec(key["shield_delta"]) + vec([
                    0, yaw * tuning["support_yaw_offset"], tuning["support_hand_lift"],
                ])
                wrist = (rotate([0, 0, 1], yaw * tuning["support_wrist_yaw_scale"])
                         @ rotate([1, 0, 0], tuning["support_wrist_pitch"]))
                elbow_pole = vec(tuning["support_elbow_pole"])
            self._arm(side, shoulder, hand, wrist, elbow_pole, joints, transforms)
