import json, sys, numpy as np
from collections import Counter, defaultdict
sys.path.insert(0, r"E:\ClaudeWork\bo4_recon"); import match_placements as M
G = r"E:\ClaudeWork\bo3\bod_port\t8_world\geo\\"
R = M.records(); amn, amx = R["absmin"].astype(float), R["absmax"].astype(float); c = (amn+amx)/2; ext = amx-amn
foot = np.clip(ext[:,0],1,None)*np.clip(ext[:,1],1,None); arch = ext.max(1) >= 128
conf = {p["record"] for p in json.load(open(G+"bod_props_bounds_confident.json"))}
res = {p["record"]: p for p in json.load(open(G+"bod_props_arch_resolved.json"))}
prx = {p["record"]: p for p in json.load(open(G+"bod_props_arch_proxy.json"))}
gap = json.load(open(G+"bod_rip_gap.json")); gapset = {g["record"] for g in gap}
L = np.array([-1815,8033,1432]); d = np.linalg.norm(c-L, axis=1)
def cov(m, sets):
    a = np.nonzero(m & arch)[0]; s = set().union(*sets); return foot[[i for i in a if i in s]].sum()/foot[a].sum()
for R_ in (1500, 3000):
    m = d < R_
    print(f"<{R_}u arch footprint: before {cov(m,[conf]):.0%} | +exact/variant {cov(m,[conf,res]):.0%} | +proxy {cov(m,[conf,res,prx]):.0%} | rip-gap share {cov(m,[gapset]):.0%}")
med = np.array([1471, 9463]); m = np.linalg.norm(c[:,:2]-med, axis=1) < 3000
print(f"<3000 XY median centre: before {cov(m,[conf]):.0%} | +res {cov(m,[conf,res]):.0%} | +proxy {cov(m,[conf,res,prx]):.0%} | gap {cov(m,[gapset]):.0%}")
allm = np.ones(len(R), bool); print(f"whole map: before {cov(allm,[conf]):.0%} | +res {cov(allm,[conf,res]):.0%} | +proxy {cov(allm,[conf,res,prx]):.0%} | gap {cov(allm,[gapset]):.0%}")
for rec in (926, 8727, 2689, 2342, 2688, 2697, 7308, 21496):
    t = "conf" if rec in conf else res[rec]["tier"]+":"+res[rec]["model"] if rec in res else f"proxy:{prx[rec]['model']} k{prx[rec]['k']}" if rec in prx else "GAP" if rec in gapset else "ambiguous"
    print("  target rec", rec, c[rec].round().astype(int).tolist(), t)
# group gap into distinct shapes by sorted local size (rounded 5%)
grp = defaultdict(list)
for g in gap:
    key = tuple(sorted(int(round(np.log(max(v,1))/np.log(1.06))) for v in g["local_size"]))
    grp[key].append(g)
shapes = sorted(grp.values(), key=lambda v: -sum(np.prod(np.clip(np.array(x["aabb"][:2]),1,None)) for x in v))
print(f"\nrip gap: {len(gap)} records -> ~{len(grp)} distinct shapes; spawn<3000: {sum(g['dist_landmark']<3000 for g in gap)} records")
for v in shapes[:15]:
    x = v[0]; near = sum(g["dist_landmark"] < 3000 for g in v)
    print(f"  x{len(v):3d} (spawn {near:3d}) local ~{[round(s) for s in sorted(x['local_size'], reverse=True)]} e.g. {x['centre']} scale {x['scale']} nearest-rip {x['nearest']} err {x['nearest_err']}")
rows = [{"count": len(v), "spawn_3000": sum(g["dist_landmark"] < 3000 for g in v), "local_size": sorted([round(s) for s in v[0]["local_size"]], reverse=True),
         "nearest_rip": v[0]["nearest"], "nearest_err": v[0]["nearest_err"], "near_miss": v[0]["nearest_err"] < 0.08 * max(v[0]["aabb"]),
         "examples": [g["centre"] for g in v[:3]], "records": [g["record"] for g in v]} for v in shapes]
json.dump(rows, open(G + "bod_rip_gap_shapes.json", "w"))
nm = [r for r in rows if r["near_miss"]]
print(f"\nshapes file: {len(rows)} shapes; near-miss (<8% of size from a ripped model) {len(nm)} shapes / {sum(r['count'] for r in nm)} records; true gap {sum(r['count'] for r in rows if not r['near_miss'])} records")
print("spawn<3000 gap records: near-miss", sum(r["spawn_3000"] for r in nm), "true", sum(r["spawn_3000"] for r in rows if not r["near_miss"]))
