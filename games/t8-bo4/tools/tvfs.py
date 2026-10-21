"""TVFS parser for BO4 vfs-root: path table (radix trie) -> VFS entries -> CFT ekeys.
Validated against casctest listing + idx membership. Part of task #37 b1."""
from __future__ import annotations
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # co-located modules
import casc_bo4 as c


def parse_header(t):
    ver, hdrSize, ekeySize, patchKeySize = struct.unpack_from(">BBBB", t, 4)
    flags = struct.unpack_from(">I", t, 8)[0]
    pto, pts, vto, vts, cto, cts = struct.unpack_from(">IIIIII", t, 12)
    maxDepth = struct.unpack_from(">H", t, 36)[0]
    return dict(ver=ver, hdrSize=hdrSize, ekeySize=ekeySize, patchKeySize=patchKeySize,
                flags=flags, pto=pto, pts=pts, vto=vto, vts=vts, cto=cto, cts=cts, maxDepth=maxDepth)


def walk_paths(t, h):
    """Return {path: vfs_offset}. Path table is a radix trie; 0xFF ends a name and
    introduces a u32 value; value&0x80000000 => folder subtree of (val&0x7fffffff) bytes
    INCLUDING the 4-byte value; else value is a VFS-table byte offset. 0x00 => '\\' sep."""
    data = t
    files = {}

    def read_name(pos):
        frag = []
        while data[pos] != 0xFF:
            if data[pos] == 0x00:
                frag.append("\\"); pos += 1
            else:
                ln = data[pos]; pos += 1
                frag.append(data[pos:pos + ln].decode("latin1")); pos += ln
        pos += 1  # the 0xFF
        val = struct.unpack_from(">I", data, pos)[0]; pos += 4
        return "".join(frag), val, pos

    def walk(pos, end, prefix):
        while pos < end:
            name, val, pos = read_name(pos)
            cur = prefix + name
            if val & 0x80000000:
                sublen = val & 0x7FFFFFFF
                cend = pos + sublen - 4
                walk(pos, cend, cur)
                pos = cend
            else:
                files[cur] = val

    start = h["pto"]
    walk(start, start + h["pts"], "")
    return files


def cft_width(h):
    s = h["cts"]
    return 1 if s <= 0xFF else 2 if s <= 0xFFFF else 3 if s <= 0xFFFFFF else 4


def parse_vfs_entry(t, h, voff, cw):
    """Return list of spans: (contentOffset, spanSize, cftOffset)."""
    base = h["vto"] + voff
    span_count = t[base]; p = base + 1
    spans = []
    for _ in range(span_count):
        content_off, span_size = struct.unpack_from(">II", t, p); p += 8
        cft_off = int.from_bytes(t[p:p + cw], "big"); p += cw
        spans.append((content_off, span_size, cft_off))
    return spans


def read_cft_ekey(t, h, cft_off):
    base = h["cto"] + cft_off
    ekey = t[base:base + h["ekeySize"]]
    enc_size = struct.unpack_from(">I", t, base + h["ekeySize"])[0]
    return ekey, enc_size


if __name__ == "__main__":
    cfg = c.parse_build_config()
    idx = c.load_idx_map()
    vekey = bytes.fromhex(cfg["vfs-root"][1])
    t = c.blte_decode(c.read_blob(idx, vekey)[0])
    h = parse_header(t)
    files = walk_paths(t, h)
    print("paths parsed:", len(files))
    # validate against casctest listing
    import re
    try:
        cl = open(r"PATH/TO/casctest_full.log", encoding="latin1").read()
        casc_paths = set(m.group(1) for m in re.finditer(r"file: (.+?) / \d+", cl))
        casc_paths.discard("vfs-root")
        mine = set(files)
        print("casctest paths:", len(casc_paths), "| mine:", len(mine))
        print("in casctest not mine:", len(casc_paths - mine), "| in mine not casctest:", len(mine - casc_paths))
        exm = sorted(casc_paths - mine)[:5]; exi = sorted(mine - casc_paths)[:5]
        if exm: print("  sample casctest-only:", exm)
        if exi: print("  sample mine-only:", exi)
    except FileNotFoundError:
        print("(no casctest log to validate against)")
    cw = cft_width(h)
    print("cft offset width:", cw)
    for name in ["zone\\zm_escape.ff", "zone\\zm_escape.xpak", "zone\\zm_escape_d.xpak",
                 "zone\\1080_zm_escape.ff", "zone\\4k_zm_escape.ff", "zone\\zm_escape.fd"]:
        if name not in files:
            print(f"  {name}: NOT FOUND"); continue
        spans = parse_vfs_entry(t, h, files[name], cw)
        tot = sum(s[1] for s in spans)
        ek0, es0 = read_cft_ekey(t, h, spans[0][2])
        ok = ek0[:9] in idx
        print(f"  {name}: voff={files[name]} spans={len(spans)} total={tot} "
              f"ek0={ek0.hex()} encSize0={es0} inIdx={ok}")
