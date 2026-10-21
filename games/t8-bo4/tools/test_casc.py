"""The one offline test for the BO4 CASC reader module (task #37 b1).
Re-run after any BO4 update. Covers the normal path plus failure/edge checks:
  1. encoding-file oracle (md5 decoded == build-config ckey)   [BLTE+idx correctness]
  2. TVFS path set is a superset of casctest's real paths       [path-table correctness]
  3. every zm_escape target resolves, EKey is in the idx         [TVFS->idx linkage]
  4. BLTE byte-exactness (per-chunk md5) on .ff and .xpak        [extraction integrity]
  5. extracted files on disk carry the right container magics    [end product]
Run:  python -I test_casc.py
"""
from __future__ import annotations
import sys, re, hashlib, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # co-located modules
import casc_bo4 as c, tvfs as T

OUT = r"PATH/TO/stage1_zone_out"  # set this to your own path
TARGETS = ["zone\\zm_escape.ff", "zone\\zm_escape.xpak", "zone\\zm_escape_d.xpak",
           "zone\\zm_escape.fd", "zone\\1080_zm_escape.ff", "zone\\4k_zm_escape.ff"]
MAGIC = {".ff": b"TAff0000", ".fd": b"TAff0000", ".xpak": b"KAPI"}

fails = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        fails.append(name)


def main():
    cfg = c.parse_build_config()
    idx = c.load_idx_map()
    print("test 1: encoding-file oracle")
    dec = c.blte_decode(c.read_blob(idx, bytes.fromhex(cfg["encoding"][1]))[0])
    md5 = hashlib.md5(dec).hexdigest()
    check("encoding ckey", md5 == cfg["encoding"][0], f"{md5}")
    check("encoding size", len(dec) == int(cfg["encoding-size"][0]), f"{len(dec)}")

    t = c.blte_decode(c.read_blob(idx, bytes.fromhex(cfg["vfs-root"][1]))[0])
    h = T.parse_header(t)
    files = T.walk_paths(t, h)
    cw = T.cft_width(h)
    print("test 2: TVFS paths vs casctest")
    try:
        cl = open(os.path.join(OUT, "casctest_full.log"), encoding="latin1").read()
        casc = set(m.group(1) for m in re.finditer(r"file: (.+?) / \d+", cl))
        casc -= {"vfs-root", "DOWNLOAD", "ENCODING", "INSTALL"}
        missing = casc - set(files)
        check("superset of casctest", len(missing) == 0, f"paths={len(files)} missing={len(missing)}")
    except FileNotFoundError:
        print("  [SKIP] no casctest_full.log")

    print("test 3+4: target resolve + BLTE byte-exact")
    for name in TARGETS:
        if name not in files:
            check(name, False, "NOT IN TVFS"); continue
        spans = T.parse_vfs_entry(t, h, files[name], cw)
        ok_idx = True
        for _, _, cft in spans:
            ek, _es = T.read_cft_ekey(t, h, cft)
            if ek[:9] not in idx:
                ok_idx = False
        try:
            for _, _, cft in spans:
                ek, _ = T.read_cft_ekey(t, h, cft)
                c.blte_decode(c.read_blob(idx, ek)[0], verify=True)
            exact = True
        except Exception as e:
            exact = False
        check(name, ok_idx and exact, f"spans={len(spans)} inIdx={ok_idx} byteExact={exact}")

    print("test 5: extracted file magics")
    for name in TARGETS:
        f = name.split("\\")[-1]
        p = os.path.join(OUT, f)
        if not os.path.exists(p):
            print(f"  [SKIP] {f} not extracted yet"); continue
        ext = os.path.splitext(f)[1]
        d = open(p, "rb").read(8)
        check(f, d.startswith(MAGIC[ext]), f"magic={d!r}")

    print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
