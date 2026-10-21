"""Find the GfxWorld baked world VERTEX buffer: long contiguous runs of float32 that read as
world-coordinate positions. The world position buffer is a big run spanning the whole island
(far bigger than the prison interior) incl. exterior (bridge/docks). Report longest runs + their
xyz bounds so we can tell interior vs exterior coverage. numpy, read-only."""
import mmap
import numpy as np

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
LANDMARK = (-1815.0, 8033.0, 1432.0)


def main():
    f = open(DEC, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    n = len(mm); a = np.frombuffer(mm, dtype="<f4", count=n // 4)
    fin = np.isfinite(a)
    mag = np.abs(a)
    # a float is a plausible world-coord component: finite and within a generous map box, OR ~0
    plausible = fin & (mag < 3e5)
    # long runs of plausible floats
    idx = np.nonzero(~plausible)[0]
    # run lengths between consecutive non-plausible positions
    bounds = np.concatenate(([-1], idx, [len(a)]))
    runlen = np.diff(bounds) - 1
    order = np.argsort(runlen)[::-1]
    print(f"zone floats {len(a):,}; longest plausible-float runs:")
    shown = 0
    for o in order[:60]:
        L = runlen[o]
        if L < 3000:
            break
        start = bounds[o] + 1
        seg = a[start:start + L]
        nv = L // 3
        v = seg[:nv * 3].reshape(-1, 3)
        mn = v.min(0); mx = v.max(0)
        ext = mx - mn
        # heuristic: position buffer has large spatial extent on x & y (world); normals/uv are tiny
        big = (ext[0] > 500) and (ext[1] > 500)
        if big:
            byte = start * 4
            inside = all(mn[i] - 50 <= LANDMARK[i] <= mx[i] + 50 for i in range(3))
            print(f"  @0x{byte:x} floats={L} (~{nv} vtx) xyz_min={[round(float(x),1) for x in mn]} "
                  f"max={[round(float(x),1) for x in mx]} landmark_in={inside}")
            shown += 1
        if shown >= 30:
            break
    mm.close(); f.close()


if __name__ == "__main__":
    main()
