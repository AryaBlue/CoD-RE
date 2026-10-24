"""Strip decal-overlay faces from a Greyhound XME in place: faces whose material is nodraw, or whose only "colour" is a
non-colour map (normal/rough/gloss/spec/occlusion, e.g. global_rough_wet_n.png) with no i_*_c.png beside it. Those
render as opaque quads in BO3 (the bathtub blood puddles). MATERIAL lines are kept so face indices stay valid.
Usage: strip_overlay.py <xme>... [--dry]"""
import re
import sys
from pathlib import Path

NON_COLOUR = re.compile(r"_(n|nml|normal|r|g|s|o|m|t|gloss|rough|occ)\.png$", re.I)
MATERIAL = re.compile(r'^MATERIAL (\d+) "([^"]+)" "\w+" "(?:color:)?([^"]*)"')


def overlay_materials(lines, folder):
    bad = set()
    for line in lines:
        m = MATERIAL.match(line)
        if not m:
            continue
        index, name, colour = int(m.group(1)), m.group(2), m.group(3).replace("\\\\", "\\")
        images = folder / "_images" / (colour.split("\\")[-2] if "\\" in colour else name)
        has_colour = images.is_dir() and any(images.glob("i_*_c.png"))
        if name.endswith("nodraw") or (NON_COLOUR.search(colour) and not has_colour):
            bad.add(index)
    return bad


def strip(xme, dry=False):
    """Returns (faces removed, bad material indices); leaves the file alone if it would remove every face."""
    xme = Path(xme)
    lines = xme.read_text(errors="replace").splitlines(keepends=True)
    bad = overlay_materials(lines, xme.parent)
    if not bad:
        return 0, bad
    out, removed, total, i = [], 0, 0, 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("TRI "):
            total += 1
            if int(line.split()[2]) in bad:
                removed += 1
                i += 13  # TRI + 3 x (VERT, NORMAL, COLOR, UV)
                continue
        out.append(line)
        i += 1
    if removed == 0 or removed == total:
        return 0, bad
    out = [f"NUMFACES {total - removed}\n" if line.startswith("NUMFACES ") else line for line in out]
    if not dry:
        xme.write_text("".join(out))
    return removed, bad


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    for path in (a for a in sys.argv[1:] if a != "--dry"):
        n, bad = strip(path, dry)
        print(f"{Path(path).name}: {n} faces removed (materials {sorted(bad)})")
