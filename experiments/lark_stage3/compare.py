#!/usr/bin/env python3
"""Build fair real-size contact sheets, animated A/B trials, and measurement JSON."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import generate as rig
P=Path(__file__).resolve().parent
OUT=P/'output'; OLD=P/'baseline'/'output'
DEST=P/'comparisons';DEST.mkdir(exist_ok=True)
DIRECTIONS=list(rig.DIR); INK='#ecf0e8'; COOL='#a6c9c5'; GOLD='#f0bc79'; BG='#101b26'; PANEL='#1d2c37'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def text(d,x,y,s,size=13,color=INK):
 font=ImageFont.truetype(FONT,size) if Path(FONT).is_file() else ImageFont.load_default(size=size)
 d.text((x,y),s,font=font,fill=color,anchor='lt')
def data(folder,name):return json.loads((folder/f'{name}.json').read_text())
META=[data(x,'metadata') for x in [OLD,OUT]]
J=[data(x,'joints') for x in [OLD,OUT]]
STATS=[data(x,'measurements') for x in [OLD,OUT]]
ART=[{m:Image.open(p/f'{m}.png').convert('RGBA') for m in ('walk','attack')} for p in (OLD,OUT)]
def spec(v,m):return META[v]['animations'][m]
def durations(v,m):
 q=spec(v,m); return q.get('durations_ms',[1000/q['fps']]*q['columns'])
def tile(v,m,dr,i):
 cell=spec(v,m)['cell'][0];r=DIRECTIONS.index(dr)
 return ART[v][m].crop((cell*i,cell*r,cell*(i+1),cell*(r+1)))
def paste(im,f,anchor,p,z):
 f=f.resize((f.width*z,f.height*z),Image.Resampling.NEAREST)
 im.paste(f,(int(p[0])-anchor[0]*z,int(p[1])-anchor[1]*z),f.getchannel('A'))
def floor(d,box,center=None):
 x,y,w,h=box
 d.rectangle((x,y,x+w,y+h),fill=PANEL,outline='#334c56')
 for dx in range(16,w,16):d.line((x+dx,y+1,x+dx,y+h-1),fill='#253945')
 for dy in range(16,h,16):d.line((x+1,y+dy,x+w-1,y+dy),fill='#253945')
 if center:
  a,b=center;d.line((a-6,b,a+6,b),fill='#53676c');d.line((a,b-4,a,b+4),fill='#53676c')
def new(size,title,sub):
 im=Image.new('RGB',size,BG);d=ImageDraw.Draw(im)
 text(d,16,14,title,21);text(d,17,42,sub,12,COOL)
 return im,d
def facing(dr):
 theta=math.pi/4*DIRECTIONS.index(dr)
 return np.array([-math.sin(theta),math.cos(theta)*math.sin(math.radians(24))])
def frame_at(t,ds):
 return min(len(ds)-1,int(np.searchsorted(np.cumsum(ds),t,side='right')))
def effect(f,dr,i):
 # Optional motion streak from the *same* projected tip path as the sprite.
 q=spec(1,'attack')
 if i!=q.get('phase_names',['']).index('cut'): return f
 coords=[rig.scalar_projection(rig.V(J[1]['attack'][k]['sword_tip']),dr)+q['anchor'] for k in [i-1,i]]
 a,b=coords; length=np.linalg.norm(b-a)
 if length<3:return f
 # Thin outside-only portion. No opaque art pixels are covered or replaced.
 line=Image.new('RGBA',f.size);d=ImageDraw.Draw(line)
 u=(b-a)/length;c=b-u*min(1.8,length*.2);a=b-u*min(8,length*.66)
 d.line([tuple(a),tuple((a+c)/2)],fill='#8eb9c4',width=1)
 d.line([tuple((a+c)/2),tuple(c)],fill='#f0dea5',width=1)
 la=np.array(line);fa=np.array(f);la[fa[...,3]>0]=0
 return Image.alpha_composite(f,Image.fromarray(la))
def views(m):
 z=2; cell=spec(1,m)['cell'][0]; a=spec(1,m)['anchor'];c0=spec(0,m)['columns'];c1=spec(1,m)['columns'];cw=cell*z+3;rh=cell*z+6
 im,d=new((76+cw*max(c0,c1),83+rh*len(DIRECTIONS)*2),f'LARK / {m.upper()} / 8 DIRECTIONS',
          'Top: v2 baseline    Bottom: v3 revision    Same pixel scale x2 per direction')
 for r,dr in enumerate(DIRECTIONS):
  for v in range(2):
   yy=68+(r*2+v)*rh
   text(d,13,yy+14,dr,16,GOLD);text(d,13,yy+38,f'v{v+2}',12,COOL)
   for i in range(spec(v,m)['columns']):
    x=58+i*cw;p=(x+a[0]*z,yy+a[1]*z)
    floor(d,(x,yy,cell*z-1,cell*z-1),p)
    paste(im,tile(v,m,dr,i),a,p,z)
 im.save(DEST/f'{m}_eight_direction_AB.png')
def game_sizes():
 im,d=new((968,736),'LARK / NATIVE SIZE','New sprites  •  left x1  /  right x3  •  attack padding does not change character scale')
 for idx,dr in enumerate(DIRECTIONS):
  col=idx%4; row=idx//4; x=13+col*239;y=75+row*324
  text(d,x,y,dr,16,GOLD);text(d,x+35,y,'first contact / cut',11,COOL)
  for yy,m,i in [(y+22,'walk',0),(y+172,'attack',spec(1,'attack')['phase_names'].index('cut'))]:
   floor(d,(x,yy,225,142))
   for zz,px in [(1,x+38),(3,x+149)]:
    p=(px,yy+126);paste(im,tile(1,m,dr,i),spec(1,m)['anchor'],p,zz)
 im.save(DEST/'native_vs_3x.png')
def write_gif(frames,ds,path):
 # Uniform palette across frames; baseline/new share the same swatches.
 allcolors=set()
 for f in frames:
  allcolors.update(f.getdata())
 if len(allcolors)>256:
  sample=Image.new('RGB',(frames[0].width,frames[0].height*min(12,len(frames))))
  for i in range(min(12,len(frames))): sample.paste(frames[i*len(frames)//min(12,len(frames))],(0,i*frames[0].height))
  pal=sample.quantize(256)
 else:
  pal=Image.new('P',(1,1));pal.putpalette([i for rgb in sorted(allcolors) for i in rgb]+[0]*(768-3*len(allcolors)))
 q=[f.quantize(palette=pal,dither=Image.Dither.NONE) for f in frames]
 q[0].save(path,save_all=True,append_images=q[1:],duration=ds,loop=0,optimize=True)
def gif_walk(dirs,versions,filename,speed=1):
 w=345;h=260;zoom=3
 ds=durations(1,'walk'); step=40
 ims=[]
 for tm in range(0,int(1667/speed),step):
  # Walk across a visibly stationary floor, identical speed & coordinate origin in both versions.
  t=tm*speed; dist=t*.001*1.9*9*1.19*zoom
  im,d=new((20+w*len(versions),73+h*len(dirs)),'LARK / WALK',f'Ground travel • {speed:g}x speed • {step}ms capture • same distance on both sides')
  for col,v in enumerate(versions):
   text(d,18+w*col,59,'v2 BASELINE' if v==0 else 'v3 REVISION',11,GOLD)
   for row,dr in enumerate(dirs):
    x=10+w*col;y=74+h*row
    p=np.rint(np.array([x+160,y+181])+facing(dr)*(dist-48)).astype(int)
    floor(d,(x,y,w-11,h-6))
    d.line((x+116,y+180,x+214,y+180),fill='#354c57')
    text(d,x+8,y+8,dr,12,COOL)
    i=frame_at(t%sum(durations(v,'walk')),durations(v,'walk'))
    paste(im,tile(v,'walk',dr,i),spec(v,'walk')['anchor'],p,zoom)
  ims.append(im)
 write_gif(ims,[step]*(len(ims)-1)+[step+400],DEST/filename)
def stylized_gif(dirs,variants,filename):
 # Variants specify source version, indices and timing. GIF timestamps rounded to centiseconds.
 cols=len(variants);w=239;h=211;z=3
 times={0,1300}
 schedules=[]
 for label,v,inds,ds,fx in variants:
  ends=np.floor(np.cumsum(ds)/10+.5000001).astype(int)*10
  times.update(map(int,ends[:-1]))
  schedules.append(ends)
 times=sorted(times);ims=[]
 for t in times[:-1]:
  im,d=new((15+cols*w,73+len(dirs)*h),'LARK / ATTACK','Same scale x3  •  same start  •  trail only if marked')
  for c,((name,v,inds,ds,fx),ends) in enumerate(zip(variants,schedules)):
   xx=8+c*w;text(d,xx+8,59,name,11,GOLD)
   q=np.searchsorted(ends,t,side='right')
   if q>=len(inds):q=len(inds)-1
   i=inds[q]
   for ri,dr in enumerate(dirs):
    yy=76+h*ri;x=xx+w//2;y=yy+168
    floor(d,(xx,yy,w-9,h-8),(x,y))
    text(d,xx+7,yy+5,dr,13,COOL)
    f=tile(v,'attack',dr,i)
    if fx:f=effect(f,dr,i)
    paste(im,f,spec(v,'attack')['anchor'],(x,y),z)
    text(d,xx+7,yy+h-25,f'{q+1:02}/{len(inds):02}   {t:03} ms',12,GOLD)
  ims.append(im)
 write_gif(ims,np.diff(times).tolist(),DEST/filename)
def walk_metrics(v):
 q=spec(v,'walk');m=STATS[v];f=q['suggested_forward_per_frame_model_units']; n=q['columns'];res={}
 cfg=rig.CFG['walk']; stance=[['L','R'],['L'],['L'],['L','R'],['R'],['R']] if v==0 else q.get('stance_by_frame')
 for s,start in [('L',0),('R',n//2)]:
  a=[]
  for ii in range(start,start+n//2+1):
   i=ii%n
   if stance and s not in stance[i]: continue
   a.append(np.array(J[v]['walk'][i]['toe_'+s])+[0,ii*f,0])
  if len(a)>1:
   delta=np.array(a)-a[0]; res[s]={'world_sampled_drift':float(np.max(np.linalg.norm(delta,axis=-1))),
       'projected_sampled_drift':{dr:float(max(np.linalg.norm(rig.scalar_projection(d,dr)) for d in delta)) for dr in DIRECTIONS},
       'sole_z':np.array(a)[:,2].tolist()}
 return res
def attack_metrics(v,indices=None):
 q=J[v]['attack']
 if indices is not None:q=[q[i] for i in indices]
 pts=np.array([p['sword_tip'] for p in q]); diffs=np.diff(pts,axis=0)
 return {'tip_xyz':pts.tolist(),'model_units':np.round(np.linalg.norm(diffs,axis=-1),3).tolist(),
    'projected_px':{dr:[round(np.linalg.norm(rig.scalar_projection(d,dr)),3) for d in diffs] for dr in DIRECTIONS},
    'sword_grip_to_tip':np.round(np.linalg.norm(pts-np.array([p['hand_R'] for p in q]),axis=-1),8).tolist()}
def walk_shape(v):
 # Registered per-part mask variation: compensate rounded projected head-joint displacement.
 q=spec(v,'walk');j=J[v]['walk'];cell=q['cell'][0]; n=q['columns']
 ids=np.asarray(Image.open((OLD,OUT)[v]/'walk_part_ids.png'));res={}
 for r,dr in enumerate(DIRECTIONS):
  masks=[];heads=[]
  for i in range(n):
   masks.append(np.asarray(tile(v,'walk',dr,i))[...,3]>0)
   head=ids[cell*r:cell*(r+1),cell*i:cell*(i+1)]==rig.PARTID['head']
   xy=np.rint(rig.scalar_projection(rig.V(j[i]['head'])-rig.V(j[0]['head']),dr)).astype(int)
   heads.append(np.roll(np.roll(head,-xy[0],axis=1),-xy[1],axis=0))
  ious=[round(float(np.sum(a&b)/np.sum(a|b)),4) for a,b in zip(masks,masks[1:]+masks[:1])]
  hp=[int(np.sum(a^b)) for a,b in zip(heads,heads[1:]+heads[:1])]
  res[dr]={'mask_iou_including_loop':ious,'registered_head_mask_changed_px':hp}
 return res
def path_img():
 im,d=new((1110,650),'LARK / SWORD-TIP PATH','Projected 3D coordinates • labeled key poses • matching orthographic scale • not interpolated hitboxes')
 cols=['#cf8c62','#8ed3cf']
 for ri,dr in enumerate(['SW','NW','N','NE','W','E']):
  x=10+(ri%3)*365;y=70+(ri//3)*282
  floor(d,(x,y,355,267));text(d,x+11,y+10,dr,17,GOLD)
  for v in range(2):
   p=spec(v,'attack'); f=tile(v,'attack',dr,0)
   anchor=[x+175,y+201]
   if v==0:paste(im,f,p['anchor'],anchor,4)
   pts=[tuple(np.array(anchor)+rig.scalar_projection(rig.V(q['sword_tip']),dr)*4) for q in J[v]['attack']]
   d.line(pts,fill=cols[v],width=2)
   for ii,(px,py) in enumerate(pts[:-1]):
    d.ellipse((px-3,py-3,px+3,py+3),fill=cols[v]);text(d,px+5,py-4,str(ii+1),11,cols[v])
  text(d,x+12,y+245,'v2 orange  /  v3 teal   (last = guard)',11,COOL)
 im.save(DEST/'tip_trajectory.png')
def main():
 for m in ('walk','attack'):views(m)
 game_sizes();path_img()
 for speed,name in [(.6,'slow'),(1,'standard'),(1.6,'fast')]:
  gif_walk(['SW','NE'],[0,1],'walk_AB_'+name+'.gif',speed)
 gif_walk(['S','N','W','E'],[0,1],'walk_AB_cardinals.gif')
 gif_walk(['SW','NE'],[1],'walk_v3.gif')
 a=durations(0,'attack');b=durations(1,'attack');o=list(range(len(a)));n=list(range(len(b)))
 cut=spec(1,'attack')['phase_names'].index('cut')
 variants=rig.CFG['attack']['comparison_variants']
 subset=lambda k: (f'v3 / {k} SAMPLED',1,variants[k]['source_indices'],variants[k]['durations_ms'],False)
 base=('v2 BASELINE',0,o,a,False);new=('v3 REVISION',1,n,b,False)
 stylized_gif(['SW','NW','N','NE'],[base,new],'attack_AB.gif')
 stylized_gif(['W','E','S','SE'],[base,new],'attack_AB_other_directions.gif')
 stylized_gif(['SW','NE'],[new],'attack_v3.gif')
 stylized_gif(['NW','N','NE'],[subset('6'),subset('8'),new],'attack_sample_count.gif')
 stylized_gif(['NW','NE'],[new,('v3 / EQUAL TIMES',1,n,[sum(b)/len(b)]*len(b),False)],'attack_timing.gif')
 stylized_gif(['NW','N','NE'],[new,('v3 / OPTIONAL TRAIL',1,n,b,True)],'attack_optional_trail.gif')
 ms={'versions':[],'attack_sample_count_comparison':{k:{**p,'tip':attack_metrics(1,p['source_indices'])} for k,p in variants.items()}}
 for v in range(2):
  ms['versions'].append({'attack_timeline_ms':np.r_[0,np.cumsum(durations(v,'attack'))].tolist(),
    'attack_tip':attack_metrics(v),'visibility_px_full_solo':STATS[v]['visibility_px_full_solo']['attack'],
    'walk_timeline_ms':np.r_[0,np.cumsum(durations(v,'walk'))].tolist(),
    'walk_toe':walk_metrics(v),'walk_shape':walk_shape(v)})
 (DEST/'comparison_metrics.json').write_text(json.dumps(ms,indent=2))
if __name__=='__main__':main()
