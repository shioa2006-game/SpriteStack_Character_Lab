#!/usr/bin/env python3
"""Generate a knight entirely from horizontal, palette/material-ID slices.
Python 3.10+; numpy and Pillow. No network or input images required.
Model: X+ anatomical left, Y+ forward, Z+ up. Angles are camera yaw.
"""
from pathlib import Path
import argparse
import json
import math
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
DIRS = ['S','SW','W','NW','N','NE','E','SE']
H = 32
DX = .5
X0,Y0 = -20,-15
nx,ny = 80,60
Z,Y,X = np.meshgrid(np.arange(H)+.5, Y0+(np.arange(ny)+.5)*DX,
                     X0+(np.arange(nx)+.5)*DX, indexing='ij')
M = np.zeros(X.shape, np.uint8)
# name / part group / three RGB shades (shadow, midtone, light)
P={
 1:('leather','boots',('50303c','8b503b','c5824c')),
 2:('sole','boots',('292539','4b3139','745044')),
 3:('trousers','legs',('202846','354669','546789')),
 4:('tunic','torso',('1d3760','346aa4','5eabd0')),
 5:('tunic trim','torso',('263b68','427fb5','81bed3')),
 6:('belt','torso',('382537','624037','996249')),
 7:('buckle','torso',('98543d','e0a459','f8d790')),
 8:('sleeve','arms',('213959','3f75aa','6caaca')),
 9:('gauntlet','arms',('583541','95563e','cd8e61')),
 10:('skin','head',('ad5c49','e7a47d','ffcf9c')),
 11:('hair','head',('4b252f','794334','b3673d')),
 12:('hair lock','head',('61302f','955036','c88148')),
 13:('eyes','head',('292336','302638','493347')),
 14:('eye glint','head',('d1bcb4','fff0ce','fff7e6')),
 15:('cheeks','head',('ab544d','d78367','efa186')),
 16:('smile','head',('773c40','994d48','af5e53')),
 17:('sword edge','sword_R',('495c7e','92aace','c8eef1')),
 18:('sword ridge','sword_R',('6b84a3','b4d3e2','e6fbf9')),
 19:('crossguard','sword_R',('87513e','c68c4a','f4cc80')),
 20:('hilt grip','sword_R',('503138','765843','a07a55')),
 21:('shield rim','shield_L',('683f45','a66f51','deb178')),
 22:('shield face','shield_L',('294b66','448c9d','75c2c2')),
 23:('shield emblem','shield_L',('a56b45','dfaa64','f6d58c')),
 24:('shield reverse','shield_L',('493142','704f49','a57b59')),
 25:('neck','head',('91504b','cf8869','eab18a')),
 26:('undershirt','torso',('222d4b','355276','547b9c')),
}
G=list(dict.fromkeys(v[1] for v in P.values()))
PART=np.array([0]+[G.index(v[1])+1 for v in P.values()],np.uint8)
HEX=lambda s: tuple(bytes.fromhex(s))
PAL=np.array([[(0,0,0)]*3]+[[HEX(a) for a in v[2]] for v in P.values()],np.uint8)
def paint(cond,m): M[cond]=m
def egg(cx,cy,cz,rx,ry,rz,m,p=2):
    paint((abs((X-cx)/rx)**p+abs((Y-cy)/ry)**p+abs((Z-cz)/rz)**p)<=1,m)
def capsule(a,b,r,m):
    a,b=np.array(a),np.array(b); d=b-a
    t=np.clip(((X-a[0])*d[0]+(Y-a[1])*d[1]+(Z-a[2])*d[2])/np.dot(d,d),0,1)
    paint((X-a[0]-t*d[0])**2+(Y-a[1]-t*d[1])**2+(Z-a[2]-t*d[2])**2<=r*r,m)
def decal_front(m,xmask,zmask):
    # Paint the exposed occupied surface from the front, rather than floating eyes.
    for z in range(H):
        for x in range(nx):
            if not (xmask[0]<=X[z,0,x]<=xmask[1] and zmask[0]<=Z[z,0,x]<=zmask[1]): continue
            iy=np.flatnonzero(M[z,:,x])
            if iy.size and M[z,iy[-1],x] in [10,13,14,15,16]:
                M[z,iy[-1],x]=m
def model():
    M.fill(0)
    # Stable stagger; both soles start at precisely z=0.
    for cx,cy in [(-3.35,1.15),(3.35,-.75)]:
        egg(cx,cy+1,1.0,2.75,3.45,1.65,2,2.8)
        egg(cx,cy+.78,2.85,2.62,3.18,2.35,1,2.6)
        egg(cx,cy-.12,4.06,2.4,2.35,1.78,1)
        capsule((cx,cy,5.4),(cx*.82,0,9.85),1.95,3)
        egg(cx,cy,4.45,2.44,2.48,.76,1,2.8)
    egg(0,0,9.65,5.85,3.72,2.55,4,2.6)
    egg(0,0,13.5,6.10,3.72,4.38,4,2.5)
    egg(0,.20,9.2,5.96,3.74,1.06,5,3.0)
    egg(0,.08,11.55,5.93,3.78,1.0,6,3.8)
    egg(0,3.58,11.6,1.20,.65,.87,7,3.5)
    egg(0,1.45,16.64,3.5,2.45,1.38,5,2.5)
    egg(0,.31,17.9,2.43,2.08,1.72,25)
    # Separate anatomy at elbows, light bracers, and independent hand sockets.
    for side in [-1,1]:
        egg(side*5.95,-.10,15.98,2.48,2.45,2.33,8,2.3)
        capsule((side*6.35,-.15,15.2),(side*8.04,.17,12.22),1.38,8)
        capsule((side*8.04,.17,12.17),(side*9.32,2.66,11.25),1.27,9)
        egg(side*9.39,3.03,11.25,1.46,1.52,1.42,9)
    # Chest detail engraved into the model, not view-specific.
    egg(-2.62,3.50,14.45,.53,.39,.56,7)
    egg(2.62,3.50,14.45,.53,.39,.56,7)
    # Rounded oversize head. Back cap, temple locks, crown and sweeping fringe.
    egg(0,.78,23.5,6.3,5.20,6.20,10,2.4)
    egg(0,3.35,21.95,4.55,3.12,3.80,10,2.25)
    egg(0,-1.12,26.22,6.73,5.14,5.54,11,2.25)
    egg(0,-3.00,22.9,5.96,3.92,4.51,11,2.4)
    egg(-5.53,-.6,23.08,1.15,3.35,3.74,11)
    egg(5.53,-.75,23.66,1.24,3.60,3.70,11)
    egg(-6.1,1.18,22.72,.94,1.48,1.51,10)
    egg(6.1,.96,22.80,.94,1.48,1.51,10)
    egg(-2.5,2.83,28.75,4.09,3.39,2.56,12,2.1)
    egg(2.37,2.18,29.36,3.51,3.58,2.58,11,2.1)
    egg(3.56,4.05,27.25,2.62,2.0,2.61,12)
    egg(-3.60,4.18,26.72,2.34,2.1,2.7,11)
    egg(-.24,4.61,28.15,2.69,1.85,1.76,12)
    egg(.0,6.00,22.84,.78,.67,.74,10)
    for k in [-1,1]:
        a,b=sorted((k*1.55,k*3.00))
        decal_front(13,(a,b),(23.1,24.9))
        decal_front(14,(a+.35,a+.85),(24.35,24.8))
        a,b=sorted((k*2.56,k*4.3))
        decal_front(15,(a,b),(21.67,22.66))
    decal_front(16,(-.9,.9),(20.68,21.5))
    # Sword secured to anatomical R hand, pointing down and out.
    # Cross-section is a small diamond, not an edge-on card.
    a=np.array((-10.0,3.85,11.3)); b=np.array((-16.35,6.3,2.45)); v=b-a
    vv=v/np.linalg.norm(v)
    q=np.cross(vv,[0,1,0]);q/=np.linalg.norm(q); s=np.cross(vv,q)
    U=(X-a[0])*q[0]+(Y-a[1])*q[1]+(Z-a[2])*q[2]
    V=(X-a[0])*s[0]+(Y-a[1])*s[1]+(Z-a[2])*s[2]
    F=((X-a[0])*v[0]+(Y-a[1])*v[1]+(Z-a[2])*v[2])/np.dot(v,v)
    taper=np.clip((1-F)/.2,.07,1)
    mask=(F>=.12)&(F<=1)&(abs(U)/1.36+abs(V)/.73<=taper)
    paint(mask,17);paint(mask&(abs(U)<.47*taper),18)
    capsule((-8.83,2.69,12.94),(-10.61,4.06,10.46),.46,20)
    egg(-8.73,2.6,13.07,.79,.78,.73,19)
    ag=a+v*.13
    capsule(ag-1.65*q,ag+1.65*q,.49,19)
    egg(-9.26,3.16,11.74,1.10,1.18,1.13,9)
    # Canted small kite shield, body L only, outside of hand. Shape lives in local U/Z.
    px,py=10.60,4.65
    u=(X-px)*.84-(Y-py)*.543
    n=(X-px)*.543+(Y-py)*.84 + (Z-11)*.078
    zs=Z-10.9
    width=np.where(zs>=-0.6,3.84*(1-.14*np.maximum(zs-2.2,0)),(zs+4.85)*.905)
    shell=(zs>=-4.85)&(zs<=4.32)&(abs(u)<width)
    depth=.63-.22*(abs(u)/4)**2
    paint(shell&(n>=-1.3)&(n<=depth),24)
    paint(shell&(n>=-.28)&(n<=depth),21)
    face=shell&(abs(u)<=width-.49)&(zs>-3.75)&(zs<3.67)&(n>=.12)&(n<=depth+.15)
    paint(face,22)
    paint(face&((abs(u)/1.48+abs(zs)/2.13)<1.05),23)
    return M.copy()

def smooth_norm(m):
    occ=(m>0).astype(np.float32)
    blur=occ.copy()
    for ax in range(3):
        pad=[(0,0)]*3;pad[ax]=(1,1)
        p=np.pad(blur,pad)
        j=[slice(None)]*3
        j[ax]=slice(None,-2);a=p[tuple(j)]
        j[ax]=slice(2,None);b=p[tuple(j)]
        blur=.25*a+.5*blur+.25*b
    gz,gy,gx=np.gradient(blur,1,DX,DX)
    return np.stack((-gx,-gy,-gz),axis=-1)

def render(m, angle, scale=1, pitch=24, outline=True):
    # Orthographic inverse projection, samples at exact pixel centers.
    # The first non-empty sample along each ray is the visible slice texel.
    theta=math.radians(angle); a=math.radians(pitch)
    r=np.array([math.cos(theta),math.sin(theta),0])
    n=np.array([-math.sin(theta),math.cos(theta),0])
    eye=n*math.cos(a)+np.array([0,0,math.sin(a)])
    up=-n*math.sin(a)+np.array([0,0,math.cos(a)])
    size=48*scale; unit=1.19*scale
    yy,xx=np.indices((size,size))
    origin=((xx+.5-24*scale)/unit)[...,None]*r+((40*scale-yy-.5)/unit)[...,None]*up
    ids=np.zeros((size,size),np.uint8)
    hits=np.zeros((size,size,3),np.int16)
    hitd=np.full((size,size),-100.,np.float32)
    for dep in np.arange(42,-36,-.18):
        xyz=origin+dep*eye
        ix=np.floor((xyz[...,0]-X0)/DX).astype(int)
        iy=np.floor((xyz[...,1]-Y0)/DX).astype(int)
        iz=np.floor(xyz[...,2]).astype(int)
        sub=(ids==0)&(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny)&(iz>=0)&(iz<H)
        ids[sub]=m[iz[sub],iy[sub],ix[sub]]
        active=sub&(ids>0)
        hits[active]=np.stack((iz[active],iy[active],ix[active]),axis=-1)
        hitd[active]=dep
    g=smooth_norm(m)[tuple(hits.transpose(2,0,1))]
    mag=np.linalg.norm(g,axis=-1)
    # Light is fixed relative to the camera so every view is equally legible.
    light=(-.42*r+.32*n+np.array([0,0,.85]))
    light/=np.linalg.norm(light)
    value=(g@light)/np.maximum(mag,.001)
    tones=np.where(value>.45,2,np.where(value<-.38,0,1))
    rgba=np.zeros((size,size,4),np.uint8)
    sel=ids>0
    rgba[sel,:3]=PAL[ids[sel],tones[sel]]
    rgba[sel,3]=255
    # Contrast between occluding weapon/body and adjoining body volumes.
    gp=PART[ids]
    for ax,step in [(0,-1),(0,1),(1,-1),(1,1)]:
        other=np.roll(gp,step,axis=ax); od=np.roll(hitd,step,axis=ax)
        dark=sel&(other>0)&(gp!=other)&((hitd-od)>1.8)
        rgba[dark,:3]=PAL[ids[dark],0]
    if outline:
        img=Image.fromarray(rgba)
        expanded=np.array(img.getchannel('A').filter(ImageFilter.MaxFilter(2*scale+1)))!=0
        edge=expanded&~sel
        rgba[edge]=[36,28,42,255]
    return Image.fromarray(rgba),ids

BG='#152331'; CARD='#203344'; INK='#edf5ef'; SUB='#aec5cb'; ACC='#e8b97b'
def panel(w,h): return Image.new('RGB',(w,h),BG)
def line(draw,x,y,t,size=20,col=INK):
    fontpath=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font=ImageFont.truetype(str(fontpath),size) if fontpath.exists() else ImageFont.load_default(size=size)
    draw.text((x,y),t,font=font,fill=col,anchor='lt')
def paste(im,s,x,y,k=1):
    if k!=1:s=s.resize((s.width*k,s.height*k),Image.Resampling.NEAREST)
    im.paste(s,(int(x),int(y)),s)
def cell(draw,box): draw.rounded_rectangle(box,14,fill=CARD,outline='#38505d',width=1)
def atlas(m):
    colors=np.vstack(([[0,0,0]],PAL[1:,1])).astype(np.uint8)
    im=Image.new('P',(nx*8,ny*4))
    im.putpalette(colors.reshape(-1).tolist()+[0]*(768-colors.size))
    for z in range(H):
        sl=Image.fromarray(m[z,::-1,:]); sl=Image.frombytes('P',sl.size,sl.tobytes())
        im.paste(sl,((z%8)*nx,(z//8)*ny))
    im.info['transparency']=0
    return im
def exploded(m,out):
    im=panel(1080,648)
    d=ImageDraw.Draw(im)
    line(d,34,24,'THE STACK / FOOT TO CROWN',28)
    line(d,34,69,'32 horizontal layers, 1 unit per Z step. No directional drawings.',17,SUB)
    cell(d,(32,109,446,622));cell(d,(468,109,1047,622))
    line(d,48,125,'01 / exploded side view',17,ACC); line(d,486,125,'02 / selected top-down slices',17,ACC)
    # Plot exposed layers with the exact material values as flat oblique projections.
    ph=-math.pi/4
    for z in range(H):
        ys,xs=np.nonzero(m[z]);ys=Y0+(ys+.5)*DX;xs=X0+(xs+.5)*DX
        mat=m[z][np.nonzero(m[z])]
        u=xs*math.cos(ph)+ys*math.sin(ph)
        v=-xs*math.sin(ph)+ys*math.cos(ph)
        for i in np.argsort(v):
            x=232+u[i]*7.25;y=579-z*12.25+v[i]*.93
            d.rectangle((x,y,x+3,y+1),fill=tuple(PAL[mat[i],1]))
    line(d,48,573,'z=00',14,SUB);line(d,48,194,'z=31',14,SUB)
    for i,(z,label) in enumerate([(0,'00  /  Soles'),(5,'05  /  Legs'),(11,'11  /  Hands & gear'),
                                  (15,'15  /  Shoulders'),(23,'23  /  Face'),(30,'30  /  Crown')]):
        x=485+(i%3)*184;y=170+(i//3)*202
        line(d,x,y,label,15,SUB)
        px=PAL[m[z,::-1,:],1]
        aa=((m[z,::-1,:]>0)*255).astype(np.uint8)
        sl=Image.fromarray(np.dstack((px,aa)))
        paste(im,sl,x,y+23,2)
    line(d,486,575,'Top of each slice = FRONT   |   R sword / L shield',15,ACC)
    im.save(out/'B_stack.png')

def previews(sprites,hi,out):
    A=panel(670,585); d=ImageDraw.Draw(A)
    line(d,34,29,'LARK / THE BLUE SQUIRE',29);line(d,35,73,'Sprite stacking character study',17,SUB)
    cell(d,(35,113,635,533))
    paste(A,sprites['SW'],120,103,9)
    line(d,36,550,'SW  /  48 px source, nearest-neighbor x9',16,ACC)
    A.save(out/'A_character.png')
    C=panel(1100,653);d=ImageDraw.Draw(C)
    line(d,31,24,'EIGHT DIRECTIONS / ONE MODEL',30)
    line(d,32,70,'Fixed 24 deg pitch  /  45 deg yaw steps  /  exact same ground pivot',17,SUB)
    captions=['FRONT','FRONT-LEFT','LEFT','BACK-LEFT','BACK','BACK-RIGHT','RIGHT','FRONT-RIGHT']
    for i,k in enumerate(DIRS):
        x=31+(i%4)*264;y=110+(i//4)*252
        cell(d,(x,y,x+247,y+237));line(d,x+14,y+14,k,20,ACC)
        line(d,x+14,y+43,captions[i],13,SUB)
        # 4x, identical top-left and pivot in every tile, guide below feet.
        d.line((x+22,y+209,x+225,y+209), fill='#4d6a75',width=1)
        paste(C,sprites[k],x+28,y+49,4)
    line(d,32,619,'R = sword hand  /  L = shield hand  /  transparent originals in the PNG sheet',14,SUB)
    C.save(out/'C_8directions.png')
    D=panel(1100,478); d=ImageDraw.Draw(D)
    line(d,31,22,'AT GAME SIZE / NO ANTIALIASING',29)
    line(d,32,68,'Same SW view at 48 px, plus a separately rendered 96 px reference.',17,SUB)
    for i,(caption,sm,k) in enumerate([('01 / 48 px actual',sprites['SW'],1),('02 / 48 px at x6',sprites['SW'],6),('03 / 96 px at x3',hi,3)]):
        x=[31,300,690][i]; w=[238,358,378][i]
        cell(d,(x,106,x+w,429));line(d,x+16,121,caption,16,ACC)
        for yy in range(156,406,12):
            for xx in range(x+13,x+w-19,12):
                if (((xx-x-13)//12+(yy-156)//12)%2):d.rectangle((xx,yy,xx+11,yy+11), fill='#253a4b')
        paste(D,sm,x+(w-sm.width*k)/2,418-sm.height*k if i else 311,k)
    line(d,32,447,'PNG preview: the first sprite occupies exactly 48 x 48 image pixels.',15,SUB)
    D.save(out/'D_game_scale.png')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=HERE/'output')
    ap.add_argument('--slices',type=Path,help='optional original indexed PNG atlas; reconstructs exact material IDs')
    args=ap.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    if args.slices is None: m=model()
    else:
        im=Image.open(args.slices)
        if im.mode!='P' or im.size!=(nx*8,ny*4):raise ValueError('expected indexed atlas, 640 x 240')
        arr=np.asarray(im)
        m=np.stack([arr[(z//8)*ny:(z//8+1)*ny,(z%8)*nx:(z%8+1)*nx][::-1] for z in range(H)])
        if int(m.max())>=len(PAL): raise ValueError('unknown material index')
    # Anatomical side checks on every solid weapon cell, independent of camera.
    sword=np.isin(m,[17,18,19,20]);shield=np.isin(m,[21,22,23,24])
    assert sword.any() and shield.any() and np.all(X[sword]<0) and np.all(X[shield]>0)
    assert np.all(np.count_nonzero(m,axis=(1,2))>0)
    assert len(np.unique(np.sign(X[0][m[0]>0])))==2
    atlas(m).save(out/'slices_z00-z31.png')
    np.savez_compressed(out/'knight_materials.npz',slices=m)
    s={};sheet=Image.new('RGBA',(384,48));big=Image.new('RGBA',(768,96));stats={}
    for i,k in enumerate(DIRS):
        sm,ids=render(m,-45*i)
        validate=np.asarray(sm)
        box=sm.getbbox()
        assert box and box[0]>0 and box[1]>0 and box[2]<48 and box[3]<48,(k,box)
        assert set(np.unique(validate[...,3])).issubset({0,255})
        assert np.count_nonzero(np.isin(ids,[17,18]))>0
        assert np.count_nonzero(PART[ids]==G.index('shield_L')+1)>0
        s[k]=sm;sheet.paste(sm,(48*i,0))
        hd,_=render(m,-45*i,2);big.paste(hd,(96*i,0))
        if k=='SW':hi=hd
        stats[k]={'yaw_deg':-45*i,'bbox_ltrb_exclusive':box,
                  'blade_visible_pixels':int(np.count_nonzero(np.isin(ids,[17,18]))),
                  'sword_visible_pixels':int(np.count_nonzero((PART[ids]==G.index('sword_R')+1))),
                  'shield_visible_pixels':int(np.count_nonzero((PART[ids]==G.index('shield_L')+1)))}
    sheet.save(out/'knight_48x48_8way.png')
    big.save(out/'knight_96x96_8way.png')
    (out/'sprite_metadata.json').write_text(json.dumps(dict(cell=[48,48],direction_order=DIRS,
      pivot=[24,40],pitch_deg=24,atlas=dict(shape=[H,ny,nx],rows=4,cols=8,cell=[nx,ny],axes='Z,Y,X',
        image_top='+Y front',horizontal_unit=DX,x_min=X0,y_min=Y0,z_step=1),
      palette={k:dict(name=v[0],part=v[1],shades=v[2]) for k,v in P.items()},
      per_view=stats),indent=2),encoding='utf-8')
    previews(s,hi,out);exploded(m,out)
    print(json.dumps(stats)); print('48 px RGBA SHA256:',hashlib.sha256(sheet.tobytes()).hexdigest())
if __name__=='__main__':main()
