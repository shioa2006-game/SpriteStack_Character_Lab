from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v=Volume(spec)
    x,y,z=v.x,v.y,v.z
    ax,ay=abs(x),abs(y)
    jamb=(ax>=5.5)&(ax<7.5)&(ay<2)&(z>=0)&(z<27)
    shoe=(ax>=5)&(ax<8)&(ay<3)&(z>=0)&(z<2.5)
    cornice=(ax<8.5)&(ay<3)&(z>=26.5)&(z<31)
    v.paint(jamb|shoe|cornice,"stone","jambs")
    v.finish(jamb & (z%7<.55),"shade")
    v.finish(cornice & ((z<27.5)|(z>30)),"wear")
    v.finish(shoe & (z<1),"moss")
    socket=(ax<7)&(abs((x+7)%3.5-1.75)<1.25)&(ay<1.25)&(z>=31)&(z<32)
    v.paint(socket,"iron","jambs")
    v.finish(socket & (z>31.5),"shade")
    # Portcullis with tapering teeth and bronze pegs at the joints.
    bar=(abs((x+6.25)%2.5-1.25)<.70)&(ay<.75)&(ax<5.75)&(z>=0)&(z<27)
    bar &= (z>1.5)|(abs((x+6.25)%2.5-1.25)<.35)
    cross=(ax<5.75)&(ay<1.25)&((abs(z-6)<.75)|(abs(z-18)<1)|(abs(z-25)<1))
    v.paint(bar|cross,"iron","grille")
    v.finish(bar & (y>0) & (z>1.5),"edge")
    v.finish(cross & (y>.5)&(abs((x+6.25)%2.5-1.25)<.65),"bronze")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
