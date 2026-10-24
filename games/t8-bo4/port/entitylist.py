"""Parse BO4 zm_escape entity spawnVars (ACTS SpawnVarKeyValue 0x20 layout) from the .dec into entities.json."""
import json, mmap, re, struct, sys
from collections import Counter

DEC = r"F:\ClaudeWork\bo3\bod_port\t8_world\decomp\zm_escape.ff.dec"
OUT = r"F:\ClaudeWork\bo4_recon\entities.json"
INLINE = 0xFFFFFFFFFFFFFFFF
STRING, VECTOR, XHASH, FLOAT, INT = 2, 3, 4, 5, 6
# key-string anchor: "origin" key ptr 0x713d169 sits at .dec 0x13c0b35c
DELTA = 0x13c0b35c - 0x0713d169

fh = open(DEC, "rb"); mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)

def cstr(o, cap=256):
    e = mm.find(b"\0", o, o + cap)
    return mm[o:e].decode("latin-1") if e != -1 else None

POOL = r"F:\ClaudeWork\bo4_recon\strpool_map.json"
KNOWN = {0xd0513d9: "script_struct"}
try:
    # far pointers resolved by strpool.py local-delta voting; drop short/junk strings
    KNOWN.update({int(k, 16): v for k, v in json.load(open(POOL)).items()
                  if v and (len(v) >= 3 or v.isdigit()) and re.fullmatch(r"[A-Za-z0-9_$][\w ./:,\-$#]*", v)})
except FileNotFoundError: pass

def ptr_str(p):
    if p >> 32 != 0x40000000: return None
    v = p & 0xFFFFFFFF
    if v in KNOWN: return KNOWN[v]
    o = v + DELTA
    # constant delta only holds near the key table
    return cstr(o) if v < 0x7200000 and mm[o - 1] == 0 else f"<ptr:{v:x}>"

def is_kv(o):
    key, = struct.unpack_from("<Q", mm, o)
    t, = struct.unpack_from("<H", mm, o + 0x18)
    return (key >> 32 == 0x40000000 or key == INLINE) and t in (STRING, VECTOR, XHASH, FLOAT, INT) and mm[o + 0x1b] == 0 and mm[o + 0x1c:o + 0x20] == b"\0\0\0\0"

def runs():
    # seed from the key ptr bytes of "origin" / "classname"; walk back/forward in 0x20 steps
    seen = set()
    for pat in (struct.pack("<Q", 0x400000000713d169), struct.pack("<Q", 0x400000000713d1c7)):
        i = mm.find(pat)
        while i != -1:
            if i not in seen and is_kv(i):
                s = i
                while s - 0x20 >= 0 and is_kv(s - 0x20): s -= 0x20
                e = i
                while is_kv(e + 0x20): e += 0x20
                for o in range(s, e + 0x20, 0x20): seen.add(o)
                yield s, (e - s) // 0x20 + 1
            i = mm.find(pat, i + 1)

def decode(s, n):
    kvs, end = [], s + n * 0x20
    pending = []
    for k in range(n):
        o = s + k * 0x20
        key, = struct.unpack_from("<Q", mm, o)
        t, = struct.unpack_from("<H", mm, o + 0x18)
        v = mm[o + 8:o + 0x18]
        kv = {"key": None if key == INLINE else ptr_str(key), "type": t, "_kinline": key == INLINE}
        if t == VECTOR: kv["value"] = list(struct.unpack_from("<3f", v))
        elif t == FLOAT: kv["value"] = struct.unpack_from("<f", v)[0]
        elif t == INT: kv["value"] = struct.unpack_from("<i", v)[0]
        elif t == XHASH: kv["value"] = f"{struct.unpack_from('<Q', v)[0]:016x}"
        else:
            p, = struct.unpack_from("<Q", v)
            kv["value"] = None if p == INLINE else ptr_str(p); kv["_vinline"] = p == INLINE
        kvs.append(kv)
    # inline strings follow the array in field order (key before value)
    o = end
    for kv in kvs:
        for f, flag in (("key", "_kinline"), ("value", "_vinline")):
            if kv.get(flag):
                st = cstr(o)
                if st is None: break
                kv[f] = st; o += len(st) + 1
        kv.pop("_kinline", None); kv.pop("_vinline", None)
    return kvs

def main():
    ents, seen = [], set()
    for s, n in runs():
        if s in seen: continue
        seen.add(s)
        kvs = decode(s, n)
        d = {kv["key"]: kv["value"] for kv in kvs if kv["key"]}
        d["_off"] = hex(s)
        ents.append(d)
    ents.sort(key=lambda e: int(e["_off"], 16))
    json.dump(ents, open(OUT, "w"), indent=1)
    cls = Counter(str(e.get("classname")) for e in ents)
    print("entities", len(ents), "with origin", sum("origin" in e for e in ents))
    for c, k in cls.most_common(25): print(f"  {k:5d} {c!a}")
    keys = Counter(k for e in ents for k in e)
    print("keys:", ascii(keys.most_common(40)))

if __name__ == "__main__":
    main()
