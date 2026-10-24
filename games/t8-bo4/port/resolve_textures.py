"""Resolve C2M export_mat_info (real format: Textures is a dict keyed by map type) to shell colour PNGs.
material -> Textures.colorMap.Name -> exported_images/<name>.TGA -> _images/<mat>/<mat>_c.png (placeholders only)."""
import json, os, re, sys
from PIL import Image

MJ  = r"F:\ClaudeWork\c2m\app2\exported_maps\black_ops_4\zm_escape\zm_escape_materials.json"
TGA = r"F:\ClaudeWork\c2m\app2\exported_images\black_ops_4"
OUT = r"F:\ClaudeWork\bo3\bod_port\geo\shell_chunks_spawn\_images"
COLOUR = ("colorMap", "colourMap", "color", "diffuseMap", "albedo")
WRITE = "--write" in sys.argv

def norm(m): return re.sub(r"[^a-z0-9_]", "_", m.lower())

def colour_name(mat):
    t = mat.get("Textures", {})
    if not isinstance(t, dict): return None
    for key in COLOUR:
        v = t.get(key)
        if isinstance(v, dict):
            nm = v.get("Name")
            if nm and not nm.startswith("$"): return nm
    # fall back: any slot whose Name ends in a colour suffix
    for v in t.values():
        if isinstance(v, dict):
            nm = v.get("Name") or ""
            if nm and not nm.startswith("$") and re.search(r"_(c|col|color|colour|albedo)$", nm.lower()):
                return nm
    return None

idx = {os.path.splitext(f)[0].lower(): os.path.join(TGA, f) for f in os.listdir(TGA)}
def find_tga(nm):
    i = nm.lower()
    for k in (i, "i_" + i, re.sub(r"^i_", "", i), i.split("/")[-1]):
        if k in idx: return idx[k]
    return None

def is_placeholder(p):
    if not os.path.exists(p): return True
    try:
        with Image.open(p) as im: return max(im.size) <= 64
    except Exception: return True

d = json.load(open(MJ, encoding="utf-8"))
# keyed by material name -> material dict
mats = {norm(k): v for k, v in d.items()} if isinstance(d, dict) else {}
shell_mats = [n for n in os.listdir(OUT) if os.path.isdir(os.path.join(OUT, n))]
print(f"materials in json {len(mats)}, shell material folders {len(shell_mats)}")

written = nocol = notga = skip_real = nomat = 0
samples = []
for n in shell_mats:
    mat = mats.get(n)
    if not mat: nomat += 1; continue
    nm = colour_name(mat)
    if not nm: nocol += 1; continue
    src = find_tga(nm)
    if not src: notga += 1; continue
    dst = os.path.join(OUT, n, n + "_c.png")
    if not is_placeholder(dst): skip_real += 1; continue
    if WRITE:
        with Image.open(src) as im:
            im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(dst)
    written += 1
    if len(samples) < 8: samples.append(f"{n} <- {os.path.basename(src)}")

print(f"{'WROTE' if WRITE else 'would write'} {written} | skip_real {skip_real} | no_colour {nocol} | no_tga {notga} | not_in_json {nomat}")
for s in samples: print("  ", s)
