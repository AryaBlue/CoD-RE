"""Estimate cod2map's unique plane count from a .map's brush faces (3-point planes; a plane and its flip count once).
Usage: count_map_planes.py <file.map> [...]"""
import re
import sys

import numpy as np

FACE = re.compile(r"^\s*\(\s*(\S+) (\S+) (\S+)\s*\)\s*\(\s*(\S+) (\S+) (\S+)\s*\)\s*\(\s*(\S+) (\S+) (\S+)\s*\)", re.M)


def planes(path):
    pts = np.array(FACE.findall(open(path, errors="replace").read()), float).reshape(-1, 3, 3)
    n = np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0])
    length = np.linalg.norm(n, axis=1)
    n, pts = n[length > 1e-9] / length[length > 1e-9, None], pts[length > 1e-9]
    d = np.einsum("ij,ij->i", n, pts[:, 0])
    flip = (n[:, 0] < -1e-6) | ((np.abs(n[:, 0]) <= 1e-6) & ((n[:, 1] < -1e-6) | ((np.abs(n[:, 1]) <= 1e-6) & (n[:, 2] < 0))))
    n[flip], d[flip] = -n[flip], -d[flip]
    key = np.column_stack([np.round(n, 4), np.round(d, 1)])
    return len(pts), len(np.unique(key, axis=0))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        faces, unique = planes(path)
        print(f"{path}: {faces} brush faces, ~{unique} unique planes (x2 with flips = ~{2 * unique})")
