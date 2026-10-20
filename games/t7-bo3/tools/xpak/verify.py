import sys, os, json, glob
import texture2ddecoder
from PIL import Image

DDS_DIR = sys.argv[1]
VDIR = os.path.join(DDS_DIR, "verify")
os.makedirs(VDIR, exist_ok=True)

def load_dds_bc7(path):
    raw = open(path, "rb").read()
    assert raw[:4] == b"DDS "
    # 4 magic + 124 header + 20 DX10 = 148
    import struct
    h = struct.unpack_from("<I", raw, 12)[0]  # height
    w = struct.unpack_from("<I", raw, 16)[0]  # width
    pix = raw[148:148 + w*h]
    bgra = texture2ddecoder.decode_bc7(pix, w, h)
    img = Image.frombytes("RGBA", (w, h), bgra, "raw", "BGRA")
    return img

rows = []
for path in sorted(glob.glob(os.path.join(DDS_DIR, "*.dds"))):
    name = os.path.splitext(os.path.basename(path))[0]
    img = load_dds_bc7(path)
    small = img.convert("RGB").resize((128, 128))
    r, g, b = [sum(small.getdata(band)) / (128*128) for band in range(3)]
    img.resize((256, 256)).save(os.path.join(VDIR, name + ".png"))
    rows.append((name, round(r,1), round(g,1), round(b,1)))

for n, r, g, b in rows:
    print(f"  {n:40} meanRGB=({r:5.1f},{g:5.1f},{b:5.1f})")
json.dump(rows, open(os.path.join(VDIR, "_meancolour.json"), "w"), indent=1)
print("wrote", len(rows), "PNG thumbnails to", VDIR)
