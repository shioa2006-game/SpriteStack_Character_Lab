#!/usr/bin/env python3
"""Draw a rig explainer from animation joints and the baked sprite PNGs.

Input: output/joints.json, optionally output/idle.png and output/attack.png.
Coordinates match the 24-degree projection and 48 x 48 cell of the generator.
"""
from argparse import ArgumentParser
from math import cos, radians, sin
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COLORS = {
    'ink': '#e9f0f0', 'dim': '#a9c0c2', 'accent': '#ffd69c',
    'panel': '#1c3040', 'panel_edge': '#426070', 'paper': '#122232',
    'C': '#e8edf5', 'R': '#f3b976', 'L': '#6fddd7',
}
FONTS = Path('/usr/share/fonts/truetype/dejavu')
TRUNK = [('pelvis','chest'), ('chest','neck'), ('neck','head')]
DIRS = ['S','SW','W','NW','N','NE','E','SE']
PITCH = 24.0
PX_PER_UNIT = 1.19
PIVOT = (24.0,40.0)

def font(size, bold=False):
    try:
        return ImageFont.truetype(str(FONTS/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)
    except OSError:
        return ImageFont.load_default()

def text(d, xy, value, size=16, color='ink', bold=False, anchor=None):
    d.text(xy,value,fill=COLORS.get(color,color),font=font(size,bold),anchor=anchor)

def project(q, direction):
    x,y,z=q
    yaw=radians(-45*DIRS.index(direction))
    a=radians(PITCH)
    side=x*cos(yaw)+y*sin(yaw)
    depth=-x*sin(yaw)+y*cos(yaw)
    up=z*cos(a)-depth*sin(a)
    return (PIVOT[0]+side*PX_PER_UNIT, PIVOT[1]-up*PX_PER_UNIT)

def limbs(side):
    return [('chest','shoulder_'+side), ('shoulder_'+side,'elbow_'+side),
            ('elbow_'+side,'hand_'+side), ('pelvis','hip_'+side),
            ('hip_'+side,'knee_'+side), ('knee_'+side,'ankle_'+side),
            ('ankle_'+side,'toe_'+side)]

def sprite(data_dir, sheet, frame, dr):
    path=data_dir/(sheet+'.png')
    if not path.exists():
        return None
    src=Image.open(path).convert('RGBA')
    direction=DIRS.index(dr)
    if sheet=='idle':
        return src.crop((48*direction,0,48*(direction+1),48))
    w,h=src.width//6,src.height//8
    tile=src.crop((w*frame,h*direction,w*(frame+1),h*(direction+1)))
    px,py=(w-48)//2,(h-48)//2
    return tile.crop((px,py,px+48,py+48))

def card(im,draw,x,y,w,h,title,subtitle,joints,dr,background):
    draw.rounded_rectangle((x,y,x+w,y+h),18, fill=COLORS['panel'],outline=COLORS['panel_edge'],width=2)
    text(draw,(x+28,y+23),title,21,'ink',True)
    text(draw,(x+28,y+56),subtitle,15,'dim')
    k=7
    ox=x+(w-48*k)//2
    oy=y+99
    if background is not None:
        highlight=background.resize((48*k,48*k), Image.Resampling.NEAREST)
        opacity=highlight.getchannel('A').point(lambda a:int(a*.42))
        im.paste(highlight,(ox,oy),opacity)
    py=oy+PIVOT[1]*k
    px=ox+PIVOT[0]*k
    draw.line((x+36,py,x+w-37,py),fill='#557687',width=1)
    draw.line((px-8,py,px+8,py),fill=COLORS['ink'],width=2)
    draw.line((px,py-8,px,py+8),fill=COLORS['ink'],width=2)
    text(draw,(x+33,y+h-30),'GROUND ANCHOR  (24, 40)',13,'dim',True)
    q={}
    for name,xyz in joints.items():
        if isinstance(xyz,(list,tuple)) and len(xyz)==3:
            sx,sy=project(xyz,dr);q[name]=(ox+sx*k,oy+sy*k)
    links=[('C',TRUNK),('R',limbs('R')+[('hand_R','sword_tip')]),
           ('L',limbs('L')+[('hand_L','shield_center')])]
    for group,edges in links:
        for u,v in edges:
            if u in q and v in q:
                a,b=q[u],q[v]
                draw.line((a,b),fill='#10202d',width=7)
                draw.line((a,b),fill=COLORS[group],width=4 if v not in ('sword_tip','shield_center') else 5)
    for name,(a,b) in q.items():
        group='R' if name.endswith('_R') or name=='sword_tip' else ('L' if name.endswith('_L') or name=='shield_center' else 'C')
        radius=6 if name.startswith(('hand','sword','shield')) else 4
        draw.ellipse((a-radius,b-radius,a+radius,b+radius),fill=COLORS[group],outline='#10202d',width=2)
    if 'sword_tip' in q:
        a,b=q['sword_tip']
        tx=x+28 if a<x+w/2 else x+w-28
        ty=max(y+95,min(b-17,y+h-54))
        anchor='lm' if a<x+w/2 else 'rm'
        draw.line((a,b,tx+(88 if a<x+w/2 else -88),ty), fill=COLORS['R'],width=1)
        text(draw,(tx,ty),'SWORD TIP',13,'R',True,anchor)
    if 'shield_center' in q:
        a,b=q['shield_center']
        tx=x+w-28 if a>x+w/2 else x+28
        ty=max(y+120,min(b+25,y+h-57))
        anchor='rm' if a>x+w/2 else 'lm'
        draw.line((a,b,tx+(-85 if a>x+w/2 else 85),ty), fill=COLORS['L'],width=1)
        text(draw,(tx,ty),'SHIELD',13,'L',True,anchor)

def make(path,out):
    data=json.loads(path.read_text(encoding='utf-8'))
    ddir=path.parent
    rest=data['rest']
    rest=rest[0] if isinstance(rest,list) else rest
    frame=min(2,len(data['attack'])-1)
    swing=data['attack'][frame]
    im=Image.new('RGB',(1140,778),COLORS['paper'])
    d=ImageDraw.Draw(im)
    text(d,(36,28),'LARK    /    SPRITE STACKING LAB',16,'accent',True)
    text(d,(34,57),'JOINTS, POSES & HAND SOCKETS',35,'ink',True)
    text(d,(36,113),'One articulated model. One pair of motions. Eight independent projections.',17,'dim')
    card(im,d,35,155,522,472,'01  /  NEUTRAL RIG','S view   |   fixed orthographic pitch 24°',rest,'S',sprite(ddir,'idle',0,'S'))
    card(im,d,582,155,522,472,'02  /  ATTACK RIG',
         'SW view   |   sampled pose %02d'% (frame+1),swing,'SW',sprite(ddir,'attack',frame,'SW'))
    for ox,col,label,detail in [
        (35,'R','R  /  CHARACTER RIGHT','Shoulder → elbow → hand → sword'),
        (404,'L','L  /  CHARACTER LEFT','Shoulder → elbow → hand → shield'),
        (771,'C','C  /  CENTRAL BODY','Head, neck, chest and pelvis'),
    ]:
        d.ellipse((ox,657,ox+14,671),fill=COLORS[col])
        text(d,(ox+24,651),label,15,col,True)
        text(d,(ox,682),detail,15,'dim')
    d.line((35,715,1104,715),fill=COLORS['panel_edge'],width=1)
    text(d,(35,735),'Equipment follows its hand in model space. Colored lines show joint connectivity, not sprite colors.',16,'dim')
    out.parent.mkdir(parents=True,exist_ok=True)
    im.save(out)

if __name__=='__main__':
    cli=ArgumentParser(description=__doc__)
    basedir=Path(__file__).resolve().parent
    cli.add_argument('--joints',type=Path,default=basedir/'output/joints.json')
    cli.add_argument('--out',type=Path,default=basedir/'output/rig.png')
    args=cli.parse_args()
    make(args.joints,args.out)
