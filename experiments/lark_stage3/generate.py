#!/usr/bin/env python3
"""Pose shared rigid parts of the original LARK slices, then re-slice and bake.
External deps: NumPy, Pillow. Volumes and projected per-part IDs are saved.
"""
from pathlib import Path
import argparse, json, hashlib, math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from baseline.base import static_generator as static
import walk_motion

P=Path(__file__).resolve().parent
BASE=P/'baseline'
CFG=json.loads((BASE/'rig_motion.json').read_text())
CFG['walk'].update(json.loads((P/'walk_motion.json').read_text()))
CFG['attack']=json.loads((P/'attack_motion.json').read_text())
DIR=static.DIRS
V=lambda p: np.array(p,dtype=float)
D=.5
# Destination samples: 0.5 cubic voxels; original material lookup is .5,.5,1.
LO=V([-24,-23,-2]); HI=V([24,25,44])
N=np.rint((HI-LO)/D).astype(int)
SLO=V([-20,-15,0])
SD=V([.5,.5,1])
REST={
 'pelvis':(0,0,9.75),'chest':(0,0,13.6),'neck':(0,.3,18.25),'head':(0,.7,24.0),
 'shoulder_R':(-5.9,-.02,15.9),'elbow_R':(-7.85,.29,12.45),'hand_R':(-9.39,3.03,11.25),
 'shoulder_L':(5.9,-.02,15.9),'elbow_L':(7.85,.29,12.45),'hand_L':(9.39,3.03,11.25),
 'hip_R':(-2.65,0,9.62),'knee_R':(-3.15,1.53,6.2),'ankle_R':(-3.35,1.15,2.65),'toe_R':(-3.35,3.35,0),
 'hip_L':(2.65,0,9.62),'knee_L':(3.15,.24,6.18),'ankle_L':(3.35,-.75,2.65),'toe_L':(3.35,1.45,0),
 'sword_tip':(-16.35,6.30,2.45),'shield_center':(10.6,4.65,10.9)}
REST={k:V(v) for k,v in REST.items()}
REST_BLADE=V([-6.35,2.45,-8.85])
PARTS=['head','chest','pelvis']+[a+'_'+s for s in 'RL' for a in ['thigh','shin','boot','upper','fore','hand']]+['sword','shield']
PARTID={k:i+1 for i,k in enumerate(PARTS)}
def I(): return np.eye(3),np.zeros(3)
def unit(v): return v/max(1e-10,np.linalg.norm(v))
def rot(axis,deg):
 x,y,z=unit(V(axis)); a=math.radians(deg)
 W=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
 return np.eye(3)+math.sin(a)*W+(1-math.cos(a))*(W@W)
def align(a,b):
 a,b=unit(a),unit(b); cross=np.cross(a,b); dt=np.clip(a@b,-1,1)
 if np.linalg.norm(cross)<1e-8:
  return np.eye(3) if dt>0 else rot(np.cross(a,[0,1,0] if abs(a[1])<.9 else [0,0,1]),180)
 return rot(cross,math.degrees(math.acos(dt)))
def about(R,p,q): return R,q-R@p
def tr(T,p): return T[0]@p+T[1]
def seg(a,b,c,d): return about(align(b-a,d-c),a,c)
def solve(a,c,l1,l2,pole):
 d=unit(c-a); h=np.clip(np.linalg.norm(c-a),abs(l1-l2)+.001,l1+l2-.035); c=a+d*h
 v=pole-a; perp=unit(v-d*(v@d)); q=(l1*l1-l2*l2+h*h)/(2*h)
 return a+q*d+math.sqrt(max(0,l1*l1-q*q))*perp,c
def distseg(P,A,B):
 d=B-A
 t=np.clip(((P-A)*d).sum(-1)/(d@d),0,1)
 return ((P-A-t[...,None]*d)**2).sum(-1)

def split(m):
 # Assign immutable ownership separately from color. Recombines the static model exactly.
 xyz=np.stack((static.X,static.Y,static.Z),axis=-1); z=static.Z
 pid=np.zeros_like(m)
 def mark(p,mask):pid[mask]=PARTID[p]
 mark('head',np.isin(m,[10,11,12,13,14,15,16,25]))
 mark('chest',np.isin(m,[4,5,6,7,26])&(z>=11.25))
 mark('pelvis',np.isin(m,[4,5,6,7,26])&(z<11.25))
 for side,sgn in [('R',-1),('L',1)]:
  sideOK=static.X*sgn>0
  b=lambda n:REST[n+'_'+side]
  mark('boot_'+side,sideOK&np.isin(m,[1,2]))
  legs=sideOK&(m==3)
  dl=distseg(xyz,b('hip'),b('knee'));dr=distseg(xyz,b('knee'),b('ankle'))
  mark('thigh_'+side,legs&(dl<dr)); mark('shin_'+side,legs&(dl>=dr))
  arm=sideOK&np.isin(m,[8,9])
  a=distseg(xyz,b('shoulder'),b('elbow')); e=distseg(xyz,b('elbow'),b('hand')); h=((xyz-b('hand'))**2).sum(-1)
  mark('upper_'+side,arm&(a<e)); mark('fore_'+side,arm&(a>=e));mark('hand_'+side,arm&(h<1.28**2))
 mark('sword',np.isin(m,[17,18,19,20]));mark('shield',np.isin(m,[21,22,23,24]))
 assert np.array_equal(m>0,pid>0)
 return pid

def pose(mode,i):
 j={k:v.copy() for k,v in REST.items()}; t={k:I() for k in PARTS}
 if mode=='rest' or (mode=='attack' and not CFG[mode]['keys'][i]):return j,t
 if mode=='walk':
  return walk_motion.pose(__import__('sys').modules[__name__],i)
 atk=CFG[mode]['keys'][i]; root=V(atk['root']); yaw=atk['yaw']; lean=atk['lean']
 Rhip=rot([0,0,1],yaw*.24)
 Rch=rot([0,0,1],yaw)@rot([1,0,0],-lean)
 t['pelvis']=about(Rhip,REST['pelvis'],REST['pelvis']+root)
 # Pivot the upper torso at the waist so the rotating torso never leaves the hips.
 t['chest']=about(Rch,REST['pelvis'],REST['pelvis']+root)
 j['pelvis']=tr(t['pelvis'],REST['pelvis'])
 for n in ['chest','neck']:j[n]=tr(t['chest'],REST[n])
 Rh=rot([0,0,1],yaw*.48)@rot([1,0,0],-lean*.37)
 t['head']=about(Rh,REST['neck'],j['neck']);j['head']=tr(t['head'],REST['head'])
 for side,sgn in [('R',-1),('L',1)]:
  k=lambda n:n+'_'+side
  b=lambda n:REST[k(n)]
  q=lambda n:j[k(n)]
  j[k('hip')]=tr(t['pelvis'],b('hip'))
  ankle=b('ankle').copy()
  if side=='R':ankle[1]+=atk['front_step']
  pitch=0
  l1=np.linalg.norm(b('knee')-b('hip'));l2=np.linalg.norm(b('ankle')-b('knee'))
  knee,actual=solve(q('hip'),ankle,l1,l2,j[k('hip')]+V([sgn*.85,8,-.3]))
  j[k('knee')]=knee;j[k('ankle')]=actual
  t[k('thigh')]=seg(b('hip'),b('knee'),q('hip'),knee)
  t[k('shin')]=seg(b('knee'),b('ankle'),knee,actual)
  t[k('boot')]=about(rot([1,0,0],pitch),b('ankle'),actual)
  j[k('toe')]=tr(t[k('boot')],b('toe'))
  shoulder=j[k('shoulder')]=tr(t['chest'],b('shoulder'))
  if side=='R':
   hand=V(atk['hand_R'])
   wrist=align(REST_BLADE,V(atk['blade']))
   bend=shoulder+V(atk.get('elbow_pole_R',[-4.3,-2.2,1.9 if i<=2 else -3.3]))
  else:
   hand=b('hand')+root+V(atk['shield_delta'])+V([0,yaw*.031,0.25])
   wrist=rot([0,0,1],yaw*.35)@rot([1,0,0],-8)
   bend=shoulder+V([5,-2.4,-4.2])
  l1=np.linalg.norm(b('elbow')-b('shoulder'));l2=np.linalg.norm(b('hand')-b('elbow'))
  el,ac=solve(shoulder,hand,l1,l2,bend)
  j[k('elbow')]=el;j[k('hand')]=ac
  t[k('upper')]=seg(b('shoulder'),b('elbow'),shoulder,el)
  t[k('fore')]=seg(b('elbow'),b('hand'),el,ac)
  t[k('hand')]=about(wrist,b('hand'),ac)
 t['sword']=t['hand_R'];t['shield']=t['hand_L']
 j['sword_tip']=tr(t['sword'],REST['sword_tip']);j['shield_center']=tr(t['shield'],REST['shield_center'])
 return j,t

def slices(m,pid,t):
 out=np.zeros(tuple(N[::-1]),np.uint8); imm=np.zeros_like(out)
 # Volume mapping: inverse sample each outgoing 0.5³ cell in its attached source part.
 # Owning cells are not blended; later parts occlude intersects in a deterministic order.
 for name in PARTS:
  group=PARTID[name]; q=np.argwhere(pid==group)[:,::-1]
  outer=np.array([SLO+np.array((x,y,z))*SD for x in [q[:,0].min(),q[:,0].max()+1]
    for y in [q[:,1].min(),q[:,1].max()+1] for z in [q[:,2].min(),q[:,2].max()+1]])
  R,u=t[name]; bb=outer@R.T+u
  mn=np.maximum(0,np.floor((bb.min(0)-LO)/D).astype(int)); mx=np.minimum(N,np.ceil((bb.max(0)-LO)/D).astype(int)+1)
  assert np.all(mn>0) and np.all(mx<N),(name,mn,mx)
  coords=np.stack(np.meshgrid(*(np.arange(a,b) for a,b in zip(mn,mx)),indexing='ij'),axis=-1)
  idx=np.floor(((LO+(coords+.5)*D-u)@R-SLO)/SD).astype(int)
  valid=((idx>=0)&(idx<np.array(m.shape[::-1]))).all(-1)
  ii=idx[valid][:,::-1]; v=tuple(ii.T)
  chosen=pid[v]==group; src=m[v][chosen]
  di=tuple(coords[valid][chosen][:,::-1].T)
  out[di]=src;imm[di]=group
 return out,imm

def smooth(m):
 w=(m>0).astype(np.float32)
 for ax in range(3):
  pd=[(0,0)]*3;pd[ax]=(1,1);wp=np.pad(w,pd)
  j=[slice(None)]*3;j[ax]=slice(None,-2);a=wp[tuple(j)];j[ax]=slice(2,None);b=wp[tuple(j)]
  w=.25*a+.5*w+.25*b
 # Match Stage 1's apparent filter width vertically across two half-size layers.
 gz,gy,gx=np.gradient(w,D,D,D)
 return np.stack((-gx,-gy,-gz),axis=-1)

def camera(theta):
 theta=math.radians(theta);a=math.radians(24)
 r=V([math.cos(theta),math.sin(theta),0]);n=V([-math.sin(theta),math.cos(theta),0]);z=V([0,0,1])
 return r,n*math.cos(a)+z*math.sin(a),-n*math.sin(a)+z*math.cos(a),n
def render(m,pid,angle,basecell=48,scale=1,norm=None,mask_only=False):
 r,eye,up,n=camera(angle)
 size=basecell*scale; pad=(basecell-48)//2
 px=(24+pad)*scale;py=(40+pad)*scale
 yy,xx=np.indices((size,size));u=1.19*scale
 origin=((xx+.5-px)/u)[...,None]*r+((py-yy-.5)/u)[...,None]*up
 ids=np.zeros((size,size),np.uint8); part=np.zeros_like(ids); hits=np.zeros((size,size,3),np.int16)
 depth=np.full((size,size),-100.,np.float32)
 # Same ray sample interval as the static stage (start may differ by a whole number of steps).
 for dep in np.arange(51.,-45.,-.18):
  ix=np.floor((origin+dep*eye-LO)/D).astype(np.int16)
  sub=(ids==0)&((ix>=0)&(ix<N)).all(-1)
  ix=ix[sub][:,::-1]
  mat=m[tuple(ix.T)]; ids[sub]=mat
  if not mask_only:
   active=sub&(ids>0); hits[active]=ix[mat>0];depth[active]=dep
 if mask_only:return ids
 part[:]=pid[tuple(hits.transpose(2,0,1))]
 sel=ids>0
 part[~sel]=0
 g=norm[tuple(hits.transpose(2,0,1))]
 light=unit(-.42*r+.32*n+V([0,0,.85]))
 value=(g@light)/np.maximum(np.linalg.norm(g,axis=-1),.001)
 tones=np.where(value>.45,2,np.where(value<-.38,0,1))
 rgb=np.zeros((size,size,4),np.uint8);rgb[sel,:3]=static.PAL[ids[sel],tones[sel]];rgb[sel,3]=255
 gp=static.PART[ids]
 for ax,step in [(0,-1),(0,1),(1,-1),(1,1)]:
  alt=np.roll(gp,step,axis=ax); dz=np.roll(depth,step,axis=ax)
  sh=sel&(alt>0)&(gp!=alt)&((depth-dz)>1.8)
  rgb[sh,:3]=static.PAL[ids[sh],0]
 expanded=np.asarray(Image.fromarray(rgb).getchannel('A').filter(ImageFilter.MaxFilter(2*scale+1)))>0
 rgb[expanded&~sel]=[36,28,42,255]
 return Image.fromarray(rgb),ids,part
def font(sz):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
 return ImageFont.truetype(str(p),sz) if p.is_file() else ImageFont.load_default(size=sz)
def label(d,x,y,s,sz=16,c='#e9efdc'):
 d.text((x,y),s,font=font(sz),fill=c,anchor='lt')
def floor(im,x,y,cell,s,sprite):
 d=ImageDraw.Draw(im);g=(40+(cell-48)//2)*s+y;cx=x+cell*s//2
 d.ellipse((cx-19*s,g-5*s,cx+19*s,g+7*s),fill='#293f45')
 for off in [-12,0,12]:
  d.line((x,g+off*s,x+cell*s,g+off*s),fill='#334c53',width=1)
 im.paste(sprite.resize((cell*s,cell*s),Image.Resampling.NEAREST),(x,y),sprite.getchannel('A').resize((cell*s,cell*s),Image.Resampling.NEAREST))
def scalar_projection(x,dir):
 r,eye,up,n=camera(-45*DIR.index(dir))
 return np.array([x@r,-x@up])*1.19
def custom_ground_metrics(vol,j,mode):
 # Cell lower face (not a contact marker). Blade and boots are tracked separately.
 z=np.indices(vol.shape)[0]*D+LO[2]
 return {k:float(z[mask].min()) for k,mask in {
  'sole_floor':np.isin(vol,[1,2]),'blade_min_z':np.isin(vol,[17,18])}.items()}
def bake(args):
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
 src=np.load(BASE/'base'/'knight_materials.npz')['slices']
 assert np.array_equal(src,static.model())
 part=split(src);np.savez_compressed(out/'rest_part_ids.npz',parts=part)
 base=Image.open(BASE/'base'/'knight_48x48_8way.png').convert('RGBA')
 base.save(out/'idle.png')
 dirs=['SW','NE'] if args.phase=='A' else DIR
 joints={mode:[] for mode in ['rest','walk','attack']}
 poses={} 
 for mode in joints:
  for i in range(1 if mode=='rest' else len(CFG[mode]['keys']) if mode=='attack' else 6):
   j,t=pose(mode,i)
   for item,hand in [('sword','hand_R'),('shield','hand_L')]:
    assert np.linalg.norm(tr(t[item],REST[hand])-j[hand])<1e-6
    assert np.linalg.norm(t[item][0].T@(tr(t[item],REST['sword_tip' if item=='sword' else 'shield_center'])-j[hand])-
      (REST['sword_tip' if item=='sword' else 'shield_center']-REST[hand]))<1e-6
   vol,pi=slices(src,part,t)
   if (mode=='rest' or (mode=='attack' and not CFG[mode]['keys'][i])): 
    # Verify exact prior volume before using the prior PNG as neutral reference.
    canon=np.zeros_like(vol)
    offsets=np.rint((SLO-LO)/D).astype(int);h,y,x=src.shape
    ox,oy,oz=offsets
    canon[oz:oz+h*2,oy:oy+y,ox:ox+x]=np.repeat(src,2,axis=0)
    assert np.array_equal(vol,canon)
   poses[(mode,i)]=(vol,pi)
   joints[mode].append(j)
 (out/'joints.json').write_text(json.dumps(joints,default=lambda a:a.tolist(),indent=2))
 volFile={f'{k}_{i:02}':v for (k,i),(v,p) in poses.items()}
 idFile={f'{k}_{i:02}':p for (k,i),(v,p) in poses.items()}
 np.savez_compressed(out/'posed_slices.npz',**volFile)
 np.savez_compressed(out/'posed_part_ids.npz',**idFile)
 gt={f'{k}_{i:02}':custom_ground_metrics(v,joints[k][i],k) for (k,i),(v,p) in poses.items()}
 metas={}; motionstats={}
 for mode in ['walk','attack']:
  # Padded dry run, crop only when every full silhouette has >=1px margin.
  raw={k:[] for k in dirs}; ma={}
  count=len(joints[mode])
  for i in range(count):
   vol,pi=poses[(mode,i)];nor=smooth(vol)
   for k in dirs:
    yaw=-45*DIR.index(k)
    im,ids,ids_part=render(vol,pi,yaw,64,norm=nor)
    if mode=='attack' and not CFG[mode]['keys'][i]:
     # This exact source frame represents the same rest geometry.
     ix=DIR.index(k)
     im=Image.new('RGBA',(64,64));im.paste(base.crop((48*ix,0,48*(ix+1),48)),(8,8))
    bb=im.getbbox(); assert bb and min(bb[0],bb[1],64-bb[2],64-bb[3])>0,(mode,i,k,bb)
    raw[k].append((im,ids,ids_part))
    if not args.quick:
     itemdata={}
     for label,group,mat in [('blade','sword',[17,18]),('shield','shield',[21,22,23,24])]:
      solo=render(np.where(pi==PARTID[group],vol,0),pi,yaw,64,mask_only=True)
      vis=ids_part==PARTID[group];a=np.isin(ids,mat)&vis;b=np.isin(solo,mat)
      assert not np.any(a&~b)
      itemdata[label]=[int(a.sum()),int(b.sum())]
     ma[f'{k}_{i+1}']=itemdata
  fit=all(min(b[0]-8,b[1]-8,56-b[2],56-b[3])>=1 for arr in raw.values() for im,_,__ in arr for b in [im.getbbox()])
  cell=48 if fit else 64
  a=(64-cell)//2;crop=(a,a,a+cell,a+cell)
  assert cell==(48 if mode=='walk' else 64),(mode,cell)
  sheet=Image.new('RGBA',(count*cell,len(dirs)*cell))
  part_atlas=np.zeros((len(dirs)*cell,count*cell),np.uint8)
  by={k:[] for k in dirs}
  for row,k in enumerate(dirs):
   for i,(im,ids,pi) in enumerate(raw[k]):
    frame=im.crop(crop)
    by[k].append(frame)
    sheet.paste(frame,(i*cell,row*cell))
    part_atlas[row*cell:(row+1)*cell,i*cell:(i+1)*cell]=pi[a:a+cell,a:a+cell]
    assert set(np.unique(np.asarray(frame)[...,3]))=={0,255}
   assert len({frame.tobytes() for frame in by[k]})>=count-1,(mode,k)
  sheet.save(out/f'{mode}.png')
  Image.fromarray(part_atlas).save(out/f'{mode}_part_ids.png')
  metas[mode]={'rows':dirs,'columns':count,'cell':[cell,cell],'anchor':[24+(cell-48)//2,40+(cell-48)//2],
                'fps':CFG[mode]['fps'],'loop':mode=='walk','rgba_sha256':hashlib.sha256(sheet.tobytes()).hexdigest()}
  if mode=='attack':
   metas[mode]['durations_ms']=CFG[mode]['durations_ms']
   metas[mode]['phase_names']=CFG[mode]['poses']
  else:
   metas[mode]['suggested_forward_per_frame_model_units']=CFG[mode]['forward_each_frame']
   for key in ('stance_by_frame','stance','poses','contact'):
    if key in CFG[mode]: metas[mode][key]=CFG[mode][key]
  motionstats[mode]=ma
 meta={'version':3,'camera':CFG['camera'],'world_axes':{'X_positive':'anatomical left','Y_positive':'front','Z_positive':'up'},
       'volume_origin_xyz':LO.tolist(),'volume_order':'Z,Y,X','voxel_size_xyz':[D]*3,
       'neutral':{'layout':'1 row, 8 columns','directions':DIR,'cell':[48,48],'anchor':[24,40]},
       'parts':PARTID,'animations':metas}
 (out/'metadata.json').write_text(json.dumps(meta,indent=2))
 (out/'measurements.json').write_text(json.dumps({'vol_ground':gt,'visibility_px_full_solo':motionstats},indent=2))
 print(json.dumps({'meta':metas,'ground':gt},indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=P/'output')
 parser.add_argument('--phase',choices=['A','B'],default='B')
 parser.add_argument('--quick',action='store_true',help='skip isolated-weapon visibility passes')
 bake(parser.parse_args())
