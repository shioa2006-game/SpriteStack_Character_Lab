from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v=Volume(spec)
    x,y,z=v.x,v.y,v.z
    base=(abs(x)<5.5)&(abs(y)<5)&(abs(x)+abs(y)<8)&(z>=0)&(z<3)
    v.paint(base,"shade","socket")
    v.finish(base & (z>2),"wear")
    v.finish(base & (abs(x)+abs(y)>7)&(z<1.5),"bronze")
    # Three irregular six-sided prisms share the dark stone socket.
    for cx,cy,height,radius,dx,dy in [(-2.2,1.5,11,1.75,-.48,.15),(2.5,-.5,14,1.85,.34,-.08),(0,-1,21,2.85,-.045,.035)]:
        t=z-2.5
        u=x-cx-dx*t; vside=y-cy-dy*t
        hexagon=np.maximum(abs(u),.50*abs(u)+.866*abs(vside))
        width=radius*np.minimum(1,np.maximum(0,(height-z)/(height*.32)))
        crystal=(t>=0)&(z<height)&(hexagon<width)
        v.paint(crystal,"slate","quartz")
        v.finish(crystal & (u+vside*.48>0),"blue")
        v.finish(crystal & (vside>abs(u)*.65),"teal")
        # Ice grows around the existing facets, with a luminous ridge and a pale tip.
        bright_face=(vside>0)|(u<-.35*width)
        rind=(t>=1)&(z<height)&(hexagon>=width)&(hexagon<width+.75)&(bright_face|(z>height-4))
        v.paint(rind,"ice","frost")
        v.finish(rind & ((u+vside>.85*width)|(z>height-2)),"light")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
