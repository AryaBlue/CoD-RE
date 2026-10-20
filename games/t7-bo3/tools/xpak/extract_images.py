"""Batch-extract image assets from a BO3 (T7) .xpak to DDS. Map-agnostic:
by default lists/extracts every image entry; pass --prefix to filter by name.
Offline, read-only on the game files.

Usage:
  python extract_images.py <file.xpak> <out_dir> [--prefix i_foo] [--list]

Writes <out_dir>/<name>.dds for each image, plus _manifest.json recording
key/offset/size/format and a sha1 of each DDS for reproducibility.
"""
import sys, os, json, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xpak import XPak
from extract import decompress
from dds import build_dds


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    xpak_path, out_dir = argv[1], argv[2]
    prefix = None
    list_only = "--list" in argv
    if "--prefix" in argv:
        prefix = argv[argv.index("--prefix") + 1]

    x = XPak(xpak_path)
    # image entries carry a pixel format + width/height in their metadata
    names = sorted(n for n, d in x.entries.items()
                   if d.get("format") and d.get("width") and d.get("height"))
    if prefix:
        names = [n for n in names if n.startswith(prefix)]

    if list_only:
        for n in names:
            d = x.entries[n]
            print(f"  {n:48} {d.get('format'):10} {d.get('width')}x{d.get('height')} levels={d.get('levels')}")
        print(f"{len(names)} image entries")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    manifest, fails, seen = [], [], {}
    for name in names:
        d = x.entries[name]
        key = d["key"]
        if key in seen:
            fails.append({"name": name, "error": f"key clash with {seen[key]}"}); continue
        seen[key] = name
        if key not in x.hash:
            fails.append({"name": name, "error": "no data blob for key"}); continue
        raw_off, comp = x.hash[key]
        foff = x.data_offset + raw_off
        # sum the per-mip sizes the index advertises
        i, total, mips = 0, 0, []
        while f"size{i}" in d:
            mips.append(int(d[f"size{i}"])); total += int(d[f"size{i}"]); i += 1
        x.f.seek(foff); payload = x.f.read(comp)
        try:
            data = decompress(payload, total)
        except Exception as e:
            fails.append({"name": name, "error": f"decompress: {e}"}); continue
        fmt, w, h, lv = d["format"], int(d["width"]), int(d["height"]), int(d.get("levels", 1))
        try:
            dds = build_dds(fmt, w, h, lv, data, mips[0] if mips else len(data))
        except Exception as e:
            fails.append({"name": name, "error": f"dds: {e}"}); continue
        outp = os.path.join(out_dir, name + ".dds")
        with open(outp, "wb") as fo:
            fo.write(dds)
        manifest.append({
            "name": name, "key": f"0x{key:016x}", "format": fmt,
            "width": w, "height": h, "levels": lv, "semantic": d.get("semantic"),
            "file_offset": f"0x{foff:x}", "comp_size": comp,
            "decomp_size": len(data), "expected_decomp": total,
            "size_ok": len(data) == total, "dds_bytes": len(dds),
            "dds_sha1_12": hashlib.sha1(dds).hexdigest()[:12],
        })

    with open(os.path.join(out_dir, "_manifest.json"), "w") as f:
        json.dump({"ok": manifest, "fail": fails}, f, indent=1)
    print(f"extracted {len(manifest)} image(s), {len(fails)} fail(s) -> {out_dir}")
    for fl in fails:
        print("  [FAIL]", fl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
