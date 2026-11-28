from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v=Volume(spec)
    x,y,z=v.x,v.y,v.z
    ax,ay=abs(x),abs(y)
    slab=(ax<5.75)&(ay<5)&(ax+ay<9)&(z>=0)&(z<2.5)
    seat=(ax<4.75)&(ay<4)&(ax+ay<7.5)&(z>=2.5)&(z<4)
    v.paint(slab|seat,"stone","plinth")
    v.finish(slab & (z<1),"moss")
    v.finish(slab & (z>2),"wear")
    def oval(cx,cy,cz,a,b,c):
        return ((x-cx)/a)**2+((y-cy)/b)**2+((z-cz)/c)**2 < 1
    torso=oval(0,0,9,3.85,3.2,6.7)
    head=oval(0,.2,15.6,4.5,3.35,4)
    v.paint(torso|head,"stone","effigy")
    wing=((ax-3)/1.8)**2+((y+.65)/3.15)**2+((z-9.8)/5.1)**2 < 1
    v.paint(wing,"shade","effigy")
    v.finish(wing & (((z-.75*y)%3)<1) & (z<11),"stone")
    feet=(abs(ax-1.75)<1.1)&(y>0)&(y<3.75)&(z>=3.5)&(z<5.3)
    v.paint(feet,"wear","effigy")
    for side in (-1,1):
        disk=oval(1.9*side,3.15,16,2.05,1.65,2.2)
        v.paint(disk,"wear","effigy")
        eye=oval(1.95*side,4.48,16.35,1.10,.65,1.0)
        v.paint(eye,"basalt","effigy")
        brow=(abs(x-2*side)<1.95)&(y>2)&(y<4.6)&(abs(z-16.85-.37*ax)<.65)
        ear=(ax>2)&(ax<4.25)&(abs(y)<1.3)&(z>=17)&(z<17+ax*.85-(.75 if side<0 else 0))&(x*side>0)
        v.paint(brow|ear,"chalk","effigy")
    beak=(ax<1.05)&(y>=3.25)&(y<5.6-.65*ax)&(z>12.3+y*.29)&(z<17.1-ax)
    v.paint(beak,"wear","effigy")
    v.finish(beak & (z<15.1),"basalt")
    v.finish(torso & (y>2)&(z>7)&(z<12)&((z-.8*ax)%3<.6),"wear")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
