#!/usr/bin/env python3
"""Export a PNG-only browser manifest; optional self-contained HTML requires no server."""
import base64, json, re
from pathlib import Path
P=Path(__file__).resolve().parent
def build():
 out={}
 for ver,rel in [('old','baseline/output'),('new','output')]:
  folder=P/rel
  meta=json.loads((folder/'metadata.json').read_text())
  out['directions']=meta['neutral']['directions']
  out[ver]={}
  for mode in ['idle','walk','attack']:
   file=folder/(mode+'.png')
   data='data:image/png;base64,'+base64.b64encode(file.read_bytes()).decode()
   clip={**meta['animations'][mode]} if mode!='idle' else {**meta['neutral'],'rows':out['directions'],'columns':8,'horizontal':True}
   out[ver][mode]={**clip,'src':f'{rel}/{mode}.png','data':data}
  out[ver]['camera']=meta['camera']
 script='window.LARK_ASSETS = '+json.dumps(out,separators=(',',':'))+';\n'
 (P/'preview_assets.js').write_text(script)
 html=P/'preview.html'
 if html.is_file():
  s,n=re.subn(r'<script\b[^>]*\bsrc=["\'](?:\./)?preview_assets\.js["\'][^>]*>\s*</script>',
   lambda m:'<script>\n'+script+'</script>',html.read_text(),count=1)
  if n:(P/'LARK_Preview_Standalone.html').write_text(s)
if __name__=='__main__':build()
