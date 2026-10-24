"""BoD (T8 zm_escape) terrain collision tri-soup -> clip.json {tris, tri_contents} in world (== MotD) coordinates.
Verts: float3[223601] @0x1D92462C; indices: u32[1057185] @0x1DBB4888 (352,395 tris, global, contiguous).
Usage (64-bit Python): clip_tris_t8.py [out.json] [--outside-footprint] [--box X0 Y0 X1 Y1]"""
import argparse
import json
from pathlib import Path

import numpy as np

ZONE = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\decomp\zm_escape.ff.dec")
VERTS, NUM_VERTS = 0x1D92462C, 223601
INDICES, NUM_INDICES = 0x1DBB4888, 1057185
OUT = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\clip\bod_terrain_clip.json")
SHELL_FOOTPRINT = ((-2381, -4224), (4257, 10720))  # 0.5/99.5 percentile of the shell clip brushes (x, y)
SOLID = 0x1


def tris():
    d = np.memmap(ZONE, np.uint8, "r")
    v = np.frombuffer(d[VERTS:VERTS + NUM_VERTS * 12], np.float32).reshape(-1, 3).astype(float)
    i = np.frombuffer(d[INDICES:INDICES + NUM_INDICES * 4], np.uint32).reshape(-1, 3)
    return v[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", type=Path, default=OUT)
    ap.add_argument("--outside-footprint", action="store_true", help="only tris whose centre is outside the shell clip")
    ap.add_argument("--box", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="only tris centred in this xy box")
    args = ap.parse_args()
    t = tris()
    area = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    keep = area > 1e-3
    c = t.mean(1)
    if args.outside_footprint:
        (x0, y0), (x1, y1) = SHELL_FOOTPRINT
        keep &= (c[:, 0] < x0) | (c[:, 0] > x1) | (c[:, 1] < y0) | (c[:, 1] > y1)
    if args.box:
        x0, y0, x1, y1 = args.box
        keep &= (c[:, 0] >= x0) & (c[:, 0] <= x1) & (c[:, 1] >= y0) & (c[:, 1] <= y1)
    out = t[keep].round(3)
    args.out.write_text(json.dumps({"brushes": [], "tris": out.tolist(), "tri_contents": [SOLID] * len(out)}))
    lo, hi = out.reshape(-1, 3).min(0), out.reshape(-1, 3).max(0)
    print(f"{len(out)} of {len(t)} tris -> {args.out}; bounds {lo.round().tolist()} .. {hi.round().tolist()}")


if __name__ == "__main__":
    main()
