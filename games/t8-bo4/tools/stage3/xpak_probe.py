"""Priority-2 foothold: confirm the xpak mesh decode + ripper-verified vertex format work offline.
Parse the KAPI index metadata to classify entries (image vs mesh), decode a sample MESH entry via
xpak_kapi, and interpret its bytes as float3 positions + u16 indices (§1b vertex format)."""
import os
import struct
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # xpak_kapi in ../
from xpak_kapi import Xpak  # noqa: E402

XPAK = r"PATH/TO/zm_escape.xpak"  # set this to your own path


def parse_index(x):
    """Index records at IndexOffset: u64 hash, u64 propsSize, <props ascii>. Return {key: props}."""
    f = x.f
    f.seek(x.h["index_offset"])
    blob = f.read(x.h["index_size"])
    out = {}
    pos = 0
    while pos + 16 <= len(blob):
        key, psize = struct.unpack_from("<QQ", blob, pos)
        pos += 16
        props = blob[pos:pos + psize].decode("latin1", "replace")
        pos += psize
        out[key] = props
        if len(out) >= x.h["index_count"]:
            break
    return out


def main():
    x = Xpak(XPAK)
    print("header:", {k: hex(v) if isinstance(v, int) else v for k, v in x.h.items()})
    idx = parse_index(x)
    print(f"index records parsed: {len(idx)}")
    kinds = {}
    sample_mesh = []
    for key, props in idx.items():
        t = None
        for line in props.replace("\r", "\n").split("\n"):
            if line.startswith("type:"):
                t = line[5:].strip()
        kinds[t] = kinds.get(t, 0) + 1
        if t == "mesh" and len(sample_mesh) < 4 and key in x.entries:
            sample_mesh.append((key, props))
    print("entry kinds:", kinds)

    for key, props in sample_mesh:
        print(f"\n== mesh key 0x{key:016x} props={props[:120]!r}")
        data = x.read(key)
        print(f"   decoded {len(data)} bytes")
        # interpret first chunk as float3 positions
        nf = min(12, len(data) // 12)
        pos = np.frombuffer(data[:nf * 12], dtype="<f4").reshape(-1, 3)
        print("   first positions (float3):", [tuple(round(float(v), 2) for v in p) for p in pos[:6]])
        rng = pos.max(0) - pos.min(0) if len(pos) else None
        print("   pos spread:", None if rng is None else [round(float(v), 1) for v in rng])


if __name__ == "__main__":
    main()
