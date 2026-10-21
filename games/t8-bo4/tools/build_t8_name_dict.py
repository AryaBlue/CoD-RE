"""Build PATH/TO/t8_name_dict.json ({hash: name}) for BO4 XModel names.

Hash (from t8_namehash.md): FNV-1a-64 of the bare name, lower-cased, '\\' -> '/', masked to 60 bits.
Sources: Greyhound's fnv1a_xmodels.wni, the rip folder names, ACTS's path.wni, identifier strings in
zm_escape.ff.dec, and any extra word lists passed on the command line (one name per line).
python -I build_t8_name_dict.py [extra_list.txt ...]
"""
import json, os, re, struct, sys

GREYHOUND = "PATH/TO/greyhound_app"  # set this to your own path
RIP = GREYHOUND + "/exported_files/black_ops_4/xmodels"
WNI = GREYHOUND + "/package_index/fnv1a_xmodels.wni"
ACTS_WNI = "PATH/TO/acts/bin/package_index/path.wni"  # set this to your own path
ZONE = "PATH/TO/zm_escape.ff.dec"  # set this to your own path
OUT = "PATH/TO/t8_name_dict.json"  # set this to your own path
MASK = 0x0FFFFFFFFFFFFFFF


def t8hash(name):
    h = 0xCBF29CE484222325
    for c in name.lower().replace("\\", "/").encode():
        h = ((h ^ c) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h & MASK


assert t8hash("") == 0x0BF29CE484222325
assert t8hash("a") == 0x0F63DC4C8601EC8C
assert t8hash("foobar") == 0x05944171F73967E8


def lz4_block(src, size):
    out, i = bytearray(), 0
    while i < len(src):
        tok = src[i]; i += 1
        n = tok >> 4
        if n == 15:
            while True:
                b = src[i]; i += 1; n += b
                if b != 255: break
        out += src[i:i + n]; i += n
        if i >= len(src) or len(out) >= size: break
        off = src[i] | src[i + 1] << 8; i += 2
        m = tok & 15
        if m == 15:
            while True:
                b = src[i]; i += 1; m += b
                if b != 255: break
        m += 4
        start = len(out) - off
        for k in range(m):
            out.append(out[start + k])
    return bytes(out)


def read_wni(path):
    b = open(path, "rb").read()
    magic, ver, count, csize, dsize = struct.unpack_from("<4sHIII", b, 0)
    assert magic == b"WNI ", magic
    data = lz4_block(b[18:18 + csize], dsize)
    assert len(data) == dsize, (len(data), dsize)
    entries, p = {}, 0
    for _ in range(count):
        h, = struct.unpack_from("<Q", data, p); p += 8
        e = data.index(b"\0", p)
        entries[h] = data[p:e].decode("utf-8", "replace"); p = e + 1
    return entries


wni = read_wni(WNI)
names = {}       # name -> source
for h, n in wni.items():
    names.setdefault(n, "wni")
for d in os.listdir(RIP):
    names.setdefault(d, "rip")
for n in read_wni(ACTS_WNI).values():
    names.setdefault(n, "acts_path_wni")
for m in re.findall(rb"[a-z0-9][a-z0-9_/\\.\-]{3,120}", open(ZONE, "rb").read()):
    if b"_" in m: names.setdefault(m.decode(), "zone_strings")
for path in sys.argv[1:]:
    for line in open(path, encoding="utf-8", errors="replace"):
        n = line.strip()
        if n: names.setdefault(n, os.path.basename(path))

out, collisions, wni_agree = {}, 0, 0
for n, src in names.items():
    h = "%016x" % t8hash(n)
    if h in out and out[h]["name"].lower() != n.lower():
        collisions += 1
        continue
    out[h] = {"name": n, "source": src}
for h, n in wni.items():
    if t8hash(n) == (h & MASK): wni_agree += 1
json.dump({h: v["name"] for h, v in sorted(out.items())}, open(OUT, "w"), indent=0)
json.dump({h: v["source"] for h, v in sorted(out.items())}, open(OUT.replace(".json", "_sources.json"), "w"), indent=0)
by = {}
for v in out.values(): by[v["source"]] = by.get(v["source"], 0) + 1
print("wni entries %d (stored hash matches our T8 hash for %d)" % (len(wni), wni_agree))
print("candidates %d, dictionary %d, collisions dropped %d, by source %s" % (len(names), len(out), collisions, by))
