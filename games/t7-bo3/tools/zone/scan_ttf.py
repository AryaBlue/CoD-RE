import re,struct,sys
from pathlib import Path
def fonts(z):
    for m in re.finditer(rb'(\x00\x01\x00\x00|OTTO)\x00[\x05-\x30]',z):
        i=m.start(); n=struct.unpack_from('>H',z,i+4)[0]
        tags=[z[i+12+16*k:i+16+16*k] for k in range(n)]
        if b'cmap' in tags and b'head' in tags:
            end=max(struct.unpack_from('>I',z,i+12+16*k+8)[0]+struct.unpack_from('>I',z,i+12+16*k+12)[0] for k in range(n))
            yield i,end
def scan():
  for p in sys.argv[1:]:
    z=Path(p).read_bytes()
    for i,end in fonts(z):
        names=re.findall(rb'[a-z0-9_/\-.]{3,}\.(?:ttf|otf)',z[max(0,i-200):i],re.I)
        print(p,hex(i),end,names[-1:],z[i-24:i].hex(' '))

def export(paths, out):
    from PIL import ImageFont
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for p in paths:
        z = Path(p).read_bytes()
        for i, end in fonts(z):
            name = re.findall(rb'[a-z0-9_/\-.]{3,}\.(?:ttf|otf)', z[max(0, i - 200):i], re.I)[-1].decode()
            target = out / Path(name).name
            target.write_bytes(z[i:i + (end + 3) // 4 * 4])
            ImageFont.truetype(str(target), 32).getbbox("BLACK OPS III")
            print("ok", target.name, end)
