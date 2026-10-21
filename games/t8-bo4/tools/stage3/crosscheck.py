"""Cross-validate 60-bit FNV-1a hash route vs the bounds-confident names.
For each confident record, read the xmodel-ptr at the bounds-pinned base, decode -> 60-bit hash,
compare to FNV-1a-60 of its model name. Report agreement overall + on large props."""
import json
import numpy as np

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
CONF = r"PATH/TO/bod_props_bounds_confident.json"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
BASE = 0x13A3D588
M60 = 0x0FFFFFFFFFFFFFFF


def hash64(s):
    s = s.lower().replace("\\", "/"); h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h & M60


def main():
    raw = open(DEC, "rb").read(); data = np.frombuffer(raw, dtype=np.uint8); n = data.size
    u32 = data[:(n // 4) * 4].view("<u4"); b = ARRAY // 4

    def ptr_hash(rec):
        o = b + rec * 24
        low = int(u32[o + 21]); high = int(u32[o + 22])
        if high != 0x40000000:
            return None
        tgt = BASE + (low - 1)
        if tgt < 0 or tgt + 8 > n:
            return None
        return int.from_bytes(data[tgt:tgt + 8].tobytes(), "little") & M60

    conf = json.load(open(CONF))
    agree = total = large_agree = large_total = 0
    for e in conf:
        rec = e["record"]; name = e["model"]; size = e.get("size", 0)
        ph = ptr_hash(rec)
        if ph is None:
            continue
        total += 1
        ok = (ph == hash64(name))
        agree += ok
        if size >= 24:
            large_total += 1; large_agree += ok
    print(f"confident records checked: {total}")
    print(f"hash==name agreement: {agree}/{total} = {100*agree/max(total,1):.1f}%")
    print(f"  large (size>=24u): {large_agree}/{large_total} = {100*large_agree/max(large_total,1):.1f}%")


if __name__ == "__main__":
    main()
