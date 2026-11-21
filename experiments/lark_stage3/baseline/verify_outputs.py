#!/usr/bin/env python3
"""Check delivered images/measurements; optionally compare a separately generated run."""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from PIL import Image
import json, numpy as np
P=Path(__file__).resolve().parent
D=['S','SW','W','NW','N','NE','E','SE']
def check(out,compare=None):
 m=json.loads((out/'metadata.json').read_text())
 vis=json.loads((out/'measurements.json').read_text())
 base=Image.open(out/'idle.png').convert('RGBA')
 assert base.tobytes()==Image.open(P/'base'/'knight_48x48_8way.png').convert('RGBA').tobytes()
 assert all(v['stance_world_max']==0 and v['max_z']==v['min_z']==0 for v in vis['gait'].values())
 volumes=np.load(out/'posed_slices.npz'); ids=np.load(out/'posed_part_ids.npz')
 assert set(volumes.files)==set(ids.files) and len(volumes.files)==13
 for key in volumes.files:
  assert volumes[key].shape==(92,96,96) and np.array_equal(volumes[key]>0,ids[key]>0)
 endpoints=json.loads((out/'joints.json').read_text())
 assert endpoints['rest'][0]==endpoints['attack'][0]==endpoints['attack'][-1]
 for state in ['walk','attack']:
  spec=m['animations'][state]; s=spec['cell'][0]; a=spec['anchor'];offset=(s-48)//2
  assert a==[24+offset,40+offset] and spec['rows']==D and spec['columns']==6
  im=Image.open(out/(state+'.png'))
  assert im.mode=='RGBA' and im.size==(6*s,8*s) and sha256(im.tobytes()).hexdigest()==spec['rgba_sha256']
  assert set(np.unique(np.asarray(im)[...,3]))=={0,255}
  for row,d in enumerate(D):
   frames=[im.crop((n*s,row*s,(n+1)*s,(row+1)*s)) for n in range(6)]
   assert len({f.tobytes() for f in frames})==(6 if state=='walk' else 5)
   for f in frames:
    x0,y0,x1,y1=f.getbbox()
    assert min(x0,y0,s-x1,s-y1)>0
   if state=='attack':
    assert frames[0].tobytes()==frames[-1].tobytes()
    assert frames[0].crop((offset,offset,offset+48,offset+48)).tobytes()==base.crop((48*row,0,48*(row+1),48)).tobytes()
  gif=Image.open(out/(state+'_SW_NE.gif'))
  assert gif.is_animated and gif.n_frames==6 and gif.info['loop']==0
  decoded=[]
  for i in range(6):
   gif.seek(i);assert gif.info['duration']>0
   decoded.append(gif.convert('RGB').tobytes())
  assert len(set(decoded))==6
  print(state, im.size, '48 frames, binary alpha, no clipping;', gif.n_frames, 'GIF frames decoded')
 if compare:
  for name in ['idle.png','walk.png','attack.png','walk_SW_NE.gif','attack_SW_NE.gif','walk_part_ids.png','attack_part_ids.png','metadata.json','joints.json','measurements.json']:
   assert (out/name).read_bytes()==(compare/name).read_bytes(),name
  for file in ['posed_slices.npz','posed_part_ids.npz','rest_part_ids.npz']:
   a,b=np.load(out/file),np.load(compare/file)
   assert a.files==b.files and all(np.array_equal(a[k],b[k]) for k in a.files),file
  print('PASS independent rebuild: PNG/GIF/JSON bytes and all slice arrays identical')
if __name__=='__main__':
 p=ArgumentParser();p.add_argument('--out',type=Path,default=P/'output');p.add_argument('--compare',type=Path)
 a=p.parse_args();check(a.out,a.compare)
