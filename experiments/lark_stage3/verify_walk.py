"""Re-render walk IDs; compare actual silhouette/head-foot masks and projected stance."""
import argparse
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "baseline"))
import animate as a
import numpy as np
from PIL import Image, ImageDraw
import walk_motion as w

HERE = Path(__file__).resolve().parent
CELL = 48


def iou(x,y):
    return float((x&y).sum() / max(1, (x|y).sum()))


def run(dest):
    dest.mkdir(parents=True, exist_ok=True)
    src=np.load(a.P/'base'/'knight_materials.npz')['slices']
    part=a.split(src)
    stats={}
    canvas=Image.new('RGB',(714,1680),'#27334a')
    pen=ImageDraw.Draw(canvas)
    for ver,pose in [('old',lambda i:a.pose('walk',i)), ('new',lambda i:w.pose(a,i))]:
        results={d:[] for d in a.DIR}
        joints=[]
        boot_min=[]
        for i in range(6):
            j,t=pose(i)
            joints.append(j)
            m,p=a.slices(src,part,t)
            boot_min.append({s:float(np.argwhere(p==a.PARTID['boot_'+s])[:,0].min()*a.D+a.LO[2]) for s in 'RL'})
            sm=a.smooth(m)
            for r,d in enumerate(a.DIR):
                sprite,_,pi=a.render(m,p,-45*r,48,norm=sm)
                results[d].append((np.asarray(sprite)[...,3]>0,pi,sprite))
        fstats={}
        for r,(d,poses) in enumerate(results.items()):
            fstats[d]={}
            bg=Image.new('RGB',(108,102),'#263851')
            bpen=ImageDraw.Draw(bg)
            for yy in (81,91,101): bpen.line((0,yy,107,yy),fill='#415269')
            bpen.line((52,64,52,101),fill='#415269')
            for i,(sil,pi,sprite) in enumerate(poses):
                y=(r*2+(ver=='new'))*104
                if not i: pen.text((4,y+9),d+' '+ver,fill='#e4eaf4')
                im=bg.copy()
                si=sprite.resize((96,96),Image.Resampling.NEAREST)
                im.paste(si,(4,1),si)
                canvas.paste(im,(60+i*108,y))
                pen.text((67+i*108,y+8),str(i+1),fill='#e4eaf4')
            for name,fn in [('silhouette',lambda s,p:s),('head',lambda s,p:p==a.PARTID['head'])]:
                masks=[fn(s,p) for s,p,_ in poses]
                fstats[d][name+'_minimum_iou']=round(min(iou(masks[i],masks[(i+1)%6]) for i in range(6)),4)
                fstats[d][name+'_mean_changed_px']=round(float(np.mean([(masks[i]^masks[(i+1)%6]).sum() for i in range(6)])),2)
            fstats[d]['minimum_visible_boot_px']={s:int(min((p==a.PARTID['boot_'+s]).sum() for _,p,_ in poses)) for s in 'LR'}
            fstats[d]['visible_boot_px_by_frame']={s:[int((p==a.PARTID['boot_'+s]).sum()) for _,p,_ in poses] for s in 'LR'}
        # The floor root is advanced, not merely scrolled; stance points are independently rounded
        # to simulate Canvas integer-pixel draw origin at rendered frame boundaries.
        speeds={}
        steps=w.CFG['forward_each_frame']
        for rate in [.6,1.,1.6]:
            fps=w.CFG['fps']*rate
            speed=steps*fps
            floor_drift={}
            for d in a.DIR:
                side_drifts=[]
                for s,start in [('L',0),('R',3)]:
                    path=[]
                    for i in range(start,start+4):
                        root=a.V([0,speed*(i/fps),0])
                        p=joints[i%6]['toe_'+s]
                        root_px=a.scalar_projection(root,d)
                        # Integer world-root draw position, integer-foot sample coordinates.
                        path.append(np.round(root_px)+np.round(a.scalar_projection(p,d)))
                    side_drifts.append(float(np.max(np.linalg.norm(np.asarray(path)-path[0],axis=1))))
                floor_drift[d]=max(side_drifts)
            speeds[str(rate)]={'fps':fps,'model_units_per_second':speed,'integer_boundary_drift_max_px':floor_drift}
        fstats_out={'directions':fstats,'per_pose_lowest_boot_voxel_z_by_side':boot_min,
                    'speed_scenarios':speeds,
                    'toe_world_stance_max_by_side':a.measure_gait({'walk':joints}),
                    'head_3D_height_range':float(np.ptp([j['head'][2] for j in joints]))}
        stats[ver]=fstats_out
    canvas.save(dest/'walk_diagnostic.png')
    (dest/'walk_diagnostic.json').write_text(json.dumps(stats,indent=2)+'\n')
    return stats


if __name__=='__main__':
    pa=argparse.ArgumentParser()
    pa.add_argument('--out',type=Path,default=HERE/'output')
    run(pa.parse_args().out)
