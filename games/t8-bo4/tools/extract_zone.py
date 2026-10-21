"""Extract named files from the BO4 local CASC, offline. Resolves path via TVFS,
reads blob via idx, BLTE-decodes, concatenates spans by contentOffset, writes file.
Self-check: md5(encoded BLTE stream) == EKey. Task #37 b1."""
from __future__ import annotations
import sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # co-located modules
import casc_bo4 as c
import tvfs as T

OUT = Path(r"PATH/TO/stage1_zone_out")  # set this to your own path

TARGETS = [
    "zone\\zm_escape.ff",
    "zone\\zm_escape.xpak",
    "zone\\zm_escape_d.xpak",
    "zone\\zm_escape.fd",
    "zone\\1080_zm_escape.ff",
    "zone\\4k_zm_escape.ff",
]


def extract(name, t, h, idx, cw):
    spans = T.parse_vfs_entry(t, h, T.files_cache[name], cw)
    spans = sorted(spans, key=lambda s: s[0])  # by contentOffset
    out_path = OUT / name.split("\\")[-1]
    sha = hashlib.sha256()
    total = 0
    with open(out_path, "wb") as of:
        for content_off, span_size, cft_off in spans:
            ekey, enc_size = T.read_cft_ekey(t, h, cft_off)
            blte, stored, blobsize = c.read_blob(idx, ekey)
            dec = c.blte_decode(blte, verify=True)  # per-chunk md5 byte-exactness check
            of.write(dec)
            sha.update(dec)
            total += len(dec)
    return out_path, total, sha.hexdigest(), True, len(spans)


def main():
    cfg = c.parse_build_config()
    idx = c.load_idx_map()
    vekey = bytes.fromhex(cfg["vfs-root"][1])
    t = c.blte_decode(c.read_blob(idx, vekey)[0])
    h = T.parse_header(t)
    files = T.walk_paths(t, h)
    T.files_cache = files
    cw = T.cft_width(h)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'file':40} {'bytes':>12}  ek_ok  spans  sha256[:16]")
    for name in TARGETS:
        if name not in files:
            print(f"{name:40} NOT FOUND"); continue
        p, total, sha, ek_ok, nspans = extract(name, t, h, idx, cw)
        print(f"{p.name:40} {total:>12}  {ek_ok!s:5}  {nspans:5}  {sha[:16]}")


if __name__ == "__main__":
    main()
