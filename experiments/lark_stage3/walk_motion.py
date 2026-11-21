"""One 6-pose cycle for LARK; 3D rig only, never manipulates projected sprites."""
import json
from pathlib import Path

import numpy as np

CFG = json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf8'))


def pose(rig, i):
    j = {k: v.copy() for k, v in rig.REST.items()}
    t = {k: rig.I() for k in rig.PARTS}
    c = CFG
    V, rot, about, tr, seg, solve = rig.V, rig.rot, rig.about, rig.tr, rig.seg, rig.solve
    i %= len(c['poses'])
    root = V([c['root_sway'][i], 0, c['root_level'] + c['root_bob'][i]])
    yaw = c['twist'][i]
    Rhip = rot([0, 0, 1], yaw * .24)
    Rch = rot([0, 0, 1], yaw) @ rot([1, 0, 0], -c['torso_lean'])
    pivot = rig.REST['pelvis']
    t['pelvis'] = about(Rhip, pivot, pivot + root)
    t['chest'] = about(Rch, pivot, pivot + root)
    for n in ('pelvis', 'chest', 'neck'):
        j[n] = tr(t['pelvis' if n == 'pelvis' else 'chest'], rig.REST[n])
    # Head stabilizes against torso yaw; reduce lateral opening near the one-pixel threshold.
    delta = j['neck'] - rig.REST['neck']
    head_offset = V([delta[0] * .25, .12, c['root_level'] + c['root_bob'][i] * .3])
    t['head'] = about(np.eye(3), rig.REST['neck'], rig.REST['neck'] + head_offset)
    j['head'] = tr(t['head'], rig.REST['head'])
    for side, sign in [('R', -1), ('L', 1)]:
        k = lambda n: n + '_' + side
        b = lambda n: rig.REST[k(n)]
        hip = j[k('hip')] = tr(t['pelvis'], b('hip'))
        local = (i + (3 if side == 'R' else 0)) % 6
        ankle = b('ankle').copy()
        ankle[0] += sign * c['track_offset']
        if local < 4:
            # Same contact world point from heel touch to toe-off, after advancing the root.
            ankle[1] = 3 - c['forward_each_frame'] * local
            pitch = 0
        else:
            ii = local-4
            ankle[1] = c['swing_forward'][ii]
            ankle[2] += c['swing_lift'][ii]
            pitch = c['swing_pitch'][ii]
        l1 = np.linalg.norm(b('knee') - b('hip'))
        l2 = np.linalg.norm(b('ankle') - b('knee'))
        knee, actual = solve(hip, ankle, l1, l2, hip + V([sign*1.12, 8, -.15]))
        if local < 4:
            assert np.linalg.norm(actual-ankle) < 1e-6, (i, side, ankle, actual)
        j[k('knee')], j[k('ankle')] = knee, actual
        t[k('thigh')] = seg(b('hip'), b('knee'), hip, knee)
        t[k('shin')] = seg(b('knee'), b('ankle'), knee, actual)
        t[k('boot')] = about(rot([1, 0, 0], pitch), b('ankle'), actual)
        j[k('toe')] = tr(t[k('boot')], b('toe'))
        shoulder = j[k('shoulder')] = tr(t['chest'], b('shoulder'))
        a = c['right_arm_swing'][i] * (1 if side == 'R' else -.57)
        hand = b('hand') + root + V([sign*.12, a, abs(a)*.18+.29])
        wrist = rot([1, 0, 0], -a*4.3) @ rot([0, 0, 1], yaw*.27)
        bend = shoulder + V([sign*4, -2.7, -4.5])
        l1 = np.linalg.norm(b('elbow') - b('shoulder'))
        l2 = np.linalg.norm(b('hand') - b('elbow'))
        el, ac = solve(shoulder, hand, l1, l2, bend)
        j[k('elbow')], j[k('hand')] = el, ac
        t[k('upper')] = seg(b('shoulder'), b('elbow'), shoulder, el)
        t[k('fore')] = seg(b('elbow'), b('hand'), el, ac)
        t[k('hand')] = about(wrist, b('hand'), ac)
    t['sword'], t['shield'] = t['hand_R'], t['hand_L']
    j['sword_tip'] = tr(t['sword'], rig.REST['sword_tip'])
    j['shield_center'] = tr(t['shield'], rig.REST['shield_center'])
    return j, t
