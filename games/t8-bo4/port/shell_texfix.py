"""shell_chunks_zfix2 -> shell_chunks_v3: flip winding, keep the puddle decals (stripping them left holes), flat colours for flow maps,
reveal map as alpha for overlay blend/decal materials (sampled: faces with another surface just beneath)."""
import glob, json, os, random, re, shutil, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from door_probe import ray, VERT_RE

GEO = r"F:\ClaudeWork\bo3\bod_port\geo"
SRC, OLD, DST = GEO + r"\shell_chunks_zfix2", GEO + r"\shell_chunks_wind", GEO + r"\shell_chunks_v3"
MATS = r"F:\ClaudeWork\c2m\app2\exported_maps\black_ops_4\zm_escape\zm_escape_materials.json"
TGA = r"F:\ClaudeWork\c2m\app2\exported_images\black_ops_4"
FLAT = {"t8_water_puddle_muddy": (58, 54, 44), "t8_zm_esc_lava_flow": (200, 80, 25), "t8_zm_esc_lava_river_01_flow": (200, 80, 25),
        "t8_water_ocean_mp_seaside": (38, 56, 64), "t8_decal_grunge_drip_water_flowing_02": (70, 70, 68), "mtl_p8_esc_cellblock_d_pillar_leak": (96, 96, 94),
        "t7_decal_water_ground_running_dirt": (52, 50, 46), "t8_decal_grunge_puddle_01": (52, 50, 46), "t8_decal_grunge_puddle_mud_01": (52, 48, 40),
        "t8_zm_zod_decal_water_puddle_01": (52, 50, 46)}
OVERLAY_MIN, SAMPLE = 0.8, 150

def load(p):
    t = open(p, encoding="utf-8", errors="replace").read()
    off = {int(m.group(1)): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in VERT_RE.finditer(t)}
    ml = re.findall(r'^MATERIAL \d+ "([^"]+)"', t, re.M)
    out = []
    for blk in re.split(r'^TRI ', t, flags=re.M)[1:]:
        mi = int(blk.split(None, 3)[1]); vs = [int(x) for x in re.findall(r'^VERT (\d+)', blk, re.M)[:3]]
        if len(vs) == 3: out.append((ml[mi], [off[v] for v in vs]))
    return out

def main():
    if os.path.isdir(DST): shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("_images"))
    shutil.copytree(OLD + r"\_images", DST + r"\_images")  # keeps the herringbone puddle retexture + puddle png fixes
    faces = [f for p in sorted(glob.glob(DST + r"\*.XMODEL_EXPORT")) for f in load(p)]
    T = np.array([f[1] for f in faces]); mat = np.array([f[0] for f in faces])
    M = json.load(open(MATS))
    reveal = {m: M[m]["Textures"]["revealMap"]["Name"] for m in set(mat) if m in M and "revealMap" in M[m].get("Textures", {})
              and not M[m]["Textures"]["revealMap"]["Name"].startswith("$")}
    random.seed(1)
    alpha_mats = []
    for m, r in sorted(reveal.items()):
        idx = np.nonzero(mat == m)[0]
        pick = random.sample(list(idx), min(SAMPLE, len(idx)))
        over = 0
        for i in pick:
            c = T[i].mean(0); n = np.cross(T[i][1] - T[i][0], T[i][2] - T[i][0]); L = np.linalg.norm(n)
            if L < 1e-6: continue
            n /= L
            near = T[(np.abs(T[:, :, 0] - c[0]).min(1) < 150) & (np.abs(T[:, :, 1] - c[1]).min(1) < 150) & (np.abs(T[:, :, 2] - c[2]).min(1) < 150) & (mat != m)]
            # another surface within 4u behind this face (either side, winding was flipped)
            if min(ray(near, c + n * 0.1, -n, 4), ray(near, c - n * 0.1, n, 4)) < 4: over += 1
        frac = over / max(1, len(pick))
        if frac >= OVERLAY_MIN and os.path.exists(os.path.join(TGA, r + ".TGA")):
            alpha_mats.append(m)
            png = os.path.join(DST, "_images", m, m + "_c.png")
            col = Image.open(png).convert("RGB"); a = Image.open(os.path.join(TGA, r + ".TGA")).convert("L").resize(col.size)
            col.putalpha(a); col.save(png)
        print(f"{m}: overlay {frac:.2f} ({len(idx)} faces){'  -> ALPHA' if m in alpha_mats else ''}")
    for m, rgb in FLAT.items():
        png = os.path.join(DST, "_images", m, m + "_c.png")
        os.makedirs(os.path.dirname(png), exist_ok=True)
        if m in alpha_mats:
            im = Image.open(png); a = im.getchannel("A"); im = Image.new("RGB", im.size, rgb); im.putalpha(a); im.save(png)
        else:
            Image.new("RGB", (64, 64), rgb).save(png)
    print("alpha materials", len(alpha_mats), "flat", len(FLAT))
    json.dump(alpha_mats, open(GEO + r"\shell_alpha_mats.json", "w"), indent=0)

if __name__ == "__main__":
    main()
