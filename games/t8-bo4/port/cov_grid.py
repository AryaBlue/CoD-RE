import json, numpy as np, collections
DEC = r"E:\ClaudeWork\bo3\bod_port\t8_world\decomp\zm_escape.ff.dec"
CONF = r"E:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_props_bounds_confident.json"
ARRAY, COUNT = 0x1D3898E4, 42559
REC = np.dtype([("origin", "<3f4"), ("inv", "<9f4"), ("absmin", "<3f4"), ("absmax", "<3f4"), ("rest", "V24")])
with open(DEC, "rb") as f:
    f.seek(ARRAY); r = np.frombuffer(f.read(COUNT * REC.itemsize), REC)
amn, amx = r["absmin"].astype(float), r["absmax"].astype(float)
c = (amn + amx) / 2; ext = amx - amn
ok = np.isfinite(c).all(1) & np.isfinite(ext).all(1) & (np.abs(c) < 1e6).all(1) & (ext >= 0).all(1) & (ext < 1e5).all(1)
conf = json.load(open(CONF)); res = np.zeros(COUNT, bool); name = {}
for e in conf: res[e["record"]] = True; name[e["record"]] = e["model"]
print(f"records {COUNT}, sane {ok.sum()}, resolved {res.sum()} (sane {(res&ok).sum()})")
foot = np.clip(ext[:, 0], 1, None) * np.clip(ext[:, 1], 1, None)  # XY footprint
arch = ok & (ext.max(1) >= 128)
G = 2000
lo = np.percentile(c[ok][:, :2], 0.5, axis=0); hi = np.percentile(c[ok][:, :2], 99.5, axis=0)
print("XY 0.5-99.5% bounds", lo.round(), hi.round())
cell = np.floor(c[:, :2] / G).astype(int)
stats = collections.defaultdict(lambda: [0, 0, 0, 0, 0.0, 0.0])  # tot, res, archtot, archres, area tot, area res
for i in np.nonzero(ok)[0]:
    s = stats[tuple(cell[i])]; s[0] += 1; s[1] += res[i]
    if arch[i]: s[2] += 1; s[3] += res[i]; s[4] += foot[i]; s[5] += foot[i] * res[i]
cells = {k: v for k, v in stats.items() if v[0] >= 20}
def frac(v): return v[5] / v[4] if v[4] else (v[1] / v[0])
good = sum(frac(v) >= 0.7 for v in cells.values()); mid = sum(0.3 <= frac(v) < 0.7 for v in cells.values())
print(f"\ncells with >=20 records: {len(cells)}; arch-area resolved >=70%: {good}, 30-70%: {mid}, <30%: {len(cells)-good-mid}")
L = np.array([-1815, 8033, 1432])
def region(m, label):
    a = m & arch
    print(f"\n{label}: records {m.sum()} resolved {(m&res).sum()} ({(m&res).sum()/max(m.sum(),1):.0%}); "
          f"arch(>=128u) {a.sum()} resolved {(a&res).sum()} ({(a&res).sum()/max(a.sum(),1):.0%}); arch footprint resolved {foot[a&res].sum()/max(foot[a].sum(),1):.0%}")
    big = np.nonzero(a & ~res)[0]; big = big[np.argsort(-foot[big])][:8]
    print("   largest UNRESOLVED arch (centre, extent):", [(c[i].round().astype(int).tolist(), ext[i].round().astype(int).tolist()) for i in big])
    print("   resolved model mix:", collections.Counter(name[i] for i in np.nonzero(m & res)[0]).most_common(10))
d = np.linalg.norm(c - L, axis=1)
for R in (1500, 3000): region(ok & (d < R), f"WITHIN {R}u of s_warden_box")
w = foot * ok; cen = (c[ok] * w[ok, None]).sum(0) / w[ok].sum(); print("\nfootprint-weighted centroid", cen.round())
cnt_cen = np.median(c[ok], axis=0); print("median centre", cnt_cen.round())
region(ok & (np.linalg.norm(c[:, :2] - cnt_cen[:2], axis=1) < 3000), "WITHIN 3000u (XY) of median centre")
print("\nGRID (cell=2000u; 'res/tot arch%area' ; rows = Y descending, cols = X)")
xs = sorted({k[0] for k in cells}); ys = sorted({k[1] for k in cells}, reverse=True)
print("      " + "".join(f"{x*G:>9d}" for x in xs))
for y in ys:
    row = ""
    for x in xs:
        v = cells.get((x, y)); row += f"{'' if not v else f'{v[0]}/{frac(v):.0%}':>9s}"
    print(f"{y*G:>6d}" + row)
gaps = sorted(cells.items(), key=lambda kv: -(kv[1][4] - kv[1][5]))[:10]
print("\nTOP GAPS by unresolved arch footprint (cell origin, records, resolved, arch unresolved, unresolved area k-u2):")
for k, v in gaps: print(f"  ({k[0]*G},{k[1]*G})  tot {v[0]} res {v[1]} archUnres {v[2]-v[3]} area {(v[4]-v[5])/1e3:.0f}k  res%area {frac(v):.0%}")
pf = json.load(open(r"E:\ClaudeWork\bo3\bod_port\t8_world\stage3_gfxworld\placements_full.json"))["records"]
h = np.array([p.get("name_hash") or "?" for p in pf]); print("\nrecords in pf", len(pf))
m = (cell[:, 0] == 0) & (cell[:, 1] == 2)
big = np.nonzero(m & ~res)[0]; big = big[np.argsort(-foot[big])][:3]
print("(0,4000) biggest unresolved:", [(c[i].round().tolist(), ext[i].round().tolist(), h[i]) for i in big])
print("unresolved records with XY extent >4000u:", int((ok & ~res & (ext[:, :2].max(1) > 4000)).sum()))
sp = ok & ~res & (d < 3000)
hc = collections.Counter(h[sp]); print(f"\nspawn<3000 unresolved: {sp.sum()} recs over {len(hc)} distinct hashes; top 15 cover {sum(v for _,v in hc.most_common(15))}")
for k, v in hc.most_common(15):
    idx = np.nonzero(sp & (h == k))[0]; print(f"  {v:5d} {k}  median extent {np.median(ext[idx].max(1)):.0f}u")
spa = sp & arch; ha = collections.Counter(h[spa]); print(f"spawn<3000 unresolved ARCH: {spa.sum()} recs, {len(ha)} hashes; top 10 cover {sum(v for _,v in ha.most_common(10))}")
for k, v in ha.most_common(10):
    idx = np.nonzero(spa & (h == k))[0]; print(f"  {v:5d} {k}  median extent {np.median(ext[idx].max(1)):.0f}u  footprint sum {foot[idx].sum()/1e3:.0f}k")
