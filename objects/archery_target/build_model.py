from objects.volume import Volume, model_cli
import numpy as np


def build(spec):
    v=Volume(spec)
    x,y,z=v.x,v.y,v.z
    foot=(abs(x)<2.25)&(y>=0)&(y<2)&(z>=0)&(z<7.5)
    v.paint(foot,"oak","bracket")
    v.finish(foot & (z<1.5),"grain")
    axle=(abs(x)<4)&((y-2.75)**2+(z-6.5)**2<.95)
    v.paint(axle,"bronze","bracket")
    r=np.hypot(x,z-11.5)
    disc=(r<5.5)&(y>=1.5)&(y<4)
    v.paint(disc,"straw","board")
    v.finish(disc & (y<2) & (abs(x)>2) & (abs(x)<3.5),"oak")
    face=disc & (y>3.25)
    v.finish(face,"ivory")
    v.finish(face & (((r>2.4)&(r<4.25)) | (r<1.45)),"madder")
    v.finish(disc & (r>5) & (y<3.5),"grain")
    return v

if __name__ == "__main__":
    model_cli(__file__, build)
