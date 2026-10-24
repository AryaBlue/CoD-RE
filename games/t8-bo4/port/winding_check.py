"""Per-chunk winding check: compare triangle geometric normal vs vertex normals, split floors (nz>0.7) and walls."""
import sys, glob, os
import numpy as np

def parse(p):
    pos, tris, cur = {}, [], None
    with open(p, errors="replace") as f:
        lines = f.read().split("\n")
    i = 0; n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith("VERT ") and cur is None and i + 1 < n and lines[i+1].strip().startswith("OFFSET"):
            v = int(s.split()[1]); o = lines[i+1].replace(",", " ").split(); pos[v] = (float(o[1]), float(o[2]), float(o[3])); i += 2; continue
        if s.startswith("TRI "):
            mat = int(s.split()[2]); vs, ns = [], []
            j = i + 1
            while len(vs) < 3 and j < n:
                t = lines[j].strip()
                if t.startswith("VERT "): vs.append(int(t.split()[1]))
                elif t.startswith("NORMAL "): ns.append([float(x) for x in t.replace(",", " ").split()[1:4]])
                j += 1
            tris.append((vs, ns, mat)); i = j; continue
        i += 1
    return pos, tris

def main():
  for p in sorted(glob.glob(sys.argv[1])):
      pos, tris = parse(p)
      A = np.array([[pos[v] for v in t[0]] for t in tris]); N = np.array([np.mean(t[1], 0) for t in tris])
      g = np.cross(A[:,1]-A[:,0], A[:,2]-A[:,0]); gl = np.linalg.norm(g, axis=1); ok = gl > 1e-6
      g = g[ok] / gl[ok, None]; N = N[ok]
      agree = (g * N).sum(1) > 0
      floor = N[:, 2] > 0.7; wall = np.abs(N[:, 2]) < 0.3
      print(f"{os.path.basename(p)[:10]} tris {len(tris):6d} | floors {floor.sum():6d} winding==normal {agree[floor].mean()*100:5.1f}% | walls {wall.sum():6d} agree {agree[wall].mean()*100:5.1f}%")

if __name__ == "__main__":
    main()
