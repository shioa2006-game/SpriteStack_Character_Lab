"""Validate artifact contract. Pass --rebuild PATH to compare a second bake."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageChops
import numpy as np
P=Path(__file__).resolve().parent
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def verify(rebuild=None):
 out=P/'output';old=P/'baseline'/'output'
 meta=json.loads((out/'metadata.json').read_text())
 idle=Image.open(out/'idle.png').convert('RGBA')
 assert sha(out/'idle.png')==sha(old/'idle.png')
 assert idle.size==(384,48)
 for mode,cell,count in [('walk',48,6),('attack',64,9)]:
  sheet=Image.open(out/f'{mode}.png').convert('RGBA')
  q=meta['animations'][mode]; assert sheet.size==(count*cell,8*cell)
  assert hashlib.sha256(sheet.tobytes()).hexdigest()==q['rgba_sha256']
  for r in range(8):
   for i in range(count):
    f=sheet.crop((i*cell,r*cell,(i+1)*cell,(r+1)*cell))
    assert set(f.getchannel('A').getdata())=={0,255}
    x,y,X,Y=f.getbbox();assert min(x,y,cell-X,cell-Y)>=1
    if mode=='attack' and i in (0,8):
     src=idle.crop((r*48,0,(r+1)*48,48))
     assert np.array_equal(f.crop((8,8,56,56)),src)
     assert np.count_nonzero(f.getchannel('A'))==np.count_nonzero(src.getchannel('A'))
 gif_stats={}
 for a in sorted((P/'comparisons').glob('*.gif')):
  im=Image.open(a); frames=[];end=0
  for i in range(im.n_frames):
   im.seek(i); frames.append(im.convert('RGB').tobytes());end+=im.info['duration']
  assert im.is_animated and len(set(frames))>4 and end>0
  gif_stats[a.name]={'frames_decoded':im.n_frames,'total_gif_loop_ms':end}
 matches={}
 if rebuild is not None:
  for name in ['idle.png','walk.png','attack.png','walk_part_ids.png','attack_part_ids.png','joints.json','metadata.json','measurements.json',
   'rest_part_ids.npz','posed_slices.npz','posed_part_ids.npz']:
   matches[name]=sha(out/name)==sha(rebuild/name)
  assert all(matches.values()),matches
 res={'idle_unchanged':True,'checked_sprite_cells':120,'alpha':['0','255'],'no_cell_edge_contact':True,
   'attack_starts_and_ends_with_exact_idle':True,'gif_decodes':gif_stats,'rebuild_byte_match':matches}
 (out/'artifact_validation.json').write_text(json.dumps(res,indent=2)+'\n')
 print(json.dumps(res))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rebuild',type=Path)
 verify(p.parse_args().rebuild)
