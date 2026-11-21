#!/usr/bin/env python3
"""Check actual posed geometry (not screenshots), motion correspondence and blade penetration."""
import json
from pathlib import Path
import numpy as np
import generate as g
P=Path(__file__).resolve().parent
cfg=g.CFG['attack']
mat=g.static.model()
pid=g.split(mat)
blade_points=np.stack((g.static.X,g.static.Y,g.static.Z),axis=-1)[np.isin(mat,[17,18])]
def penetration(t,points=blade_points):
    """Sample every original blade-voxel center against inverse posed body voxels.
    This is not continuous mesh collision or a gameplay hitbox.
    Grip and sword voxels are deliberately excluded from the body targets.
    """
    rs,us=t['sword']
    samples=points@rs.T+us
    counts={}
    for name in g.PARTS:
        if name in ('sword','hand_R'): continue
        r,u=t[name]
        q=np.floor(((samples-u)@r-g.SLO)/g.SD).astype(int)
        keep=((q>=0)&(q<np.array(mat.shape[::-1]))).all(axis=-1)
        hits=np.count_nonzero(pid[tuple(q[keep][:,::-1].T)]==g.PARTID[name])
        if hits: counts[name]=int(hits)
    return counts
def overlap_check_all():
    measurements=[]
    for i,key in enumerate(cfg['keys']):
        j,t=g.pose('attack',i)
        assert all(np.array_equal(x,y) for a,b in [('sword','hand_R'),('shield','hand_L')] for x,y in zip(t[a],t[b]))
        measurements.append({'index':i+1,'phase':cfg['poses'][i],
            'blade_collision_centers_by_part':penetration(t),
            'grip_tip_length':float(np.linalg.norm(j['sword_tip']-j['hand_R'])),
            'head':j['head'].tolist(),'hand_R':j['hand_R'].tolist(),
            'arm_length':float(np.linalg.norm(j['elbow_R']-j['shoulder_R'])+
                               np.linalg.norm(j['hand_R']-j['elbow_R']))})
    rests=[g.pose('attack',i)[0] for i in (0,len(cfg['keys'])-1)]
    assert all(np.array_equal(a,rests[1][k]) for k,a in rests[0].items())
    assert max(x['grip_tip_length'] for x in measurements)-min(x['grip_tip_length'] for x in measurements) < 1e-8
    assert max(x['arm_length'] for x in measurements)-min(x['arm_length'] for x in measurements) < 1e-8
    assert not any(x['blade_collision_centers_by_part'] for x in measurements),measurements
    return measurements
if __name__=='__main__':
    qa={'blade_centers_per_pose':len(blade_points),'stored_discrete_poses':overlap_check_all(),
        'definition':'sampled source blade voxel centers vs transformed occupied body voxels, discrete keys only; not a mesh collision proof',
        'both_attachments_share_corresponding_hand_transform':True,'first_and_last_same_guard':True}
    (P/'output'/'attack_geometry_qa.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))
