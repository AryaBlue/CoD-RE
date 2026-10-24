"""Buyable debris at BoD door spots: trigger_use zombie_debris + clip brushmodel + rubble script_models sized from door_probe.py.
Idempotent: strips earlier "// entity boddoor" entries."""
import re, sys, uuid

MAP = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\map_source\zm\zm_alcatraz_bodfull.map"
ZONE = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\usermaps\zm_alcatraz_bodfull\zone_source\zm_alcatraz_bodfull.zone"
RUBBLE = "p7_debris_concrete_rubble_lg_03_no_metal"
# name, centre xy, floor z, width (across X), height, cost
DOORS = [("cellblock", (2066, 9977), 1338, 264, 342, 750),
         ("infirmary", (2428, 9793), 1338, 64, 102, 1000),
         ("office", (-992, 8502), 1332, 94, 220, 1250)]

def guid(): return "{" + str(uuid.uuid4()).upper() + "}"

def brush(x0, y0, z0, x1, y1, z1, tex):
    t = f"{tex} 64 64 0 0 0 0 lightmap_gray 16384 16384 0 0 0 0"
    P = lambda *a: "( " + " ".join(f"{v:g}" for v in a) + " )"
    faces = [(P(x1, y1, z0), P(x1, y0, z0), P(x1, y0, z1)), (P(x1, y1, z0), P(x0, y1, z0), P(x0, y0, z0)),
             (P(x1, y0, z1), P(x0, y0, z1), P(x0, y1, z1)), (P(x1, y0, z1), P(x1, y0, z0), P(x0, y0, z0)),
             (P(x0, y1, z1), P(x0, y0, z1), P(x0, y0, z0)), (P(x0, y1, z1), P(x0, y1, z0), P(x1, y1, z0))]
    return "// brush 0\n{\n guid \"" + guid() + "\"\n" + "".join(f" {a} {b} {c} {t}\n" for a, b, c in faces) + "}\n"

def ent(kv, body=""):
    return "{\nguid \"" + guid() + "\"\n" + "".join(f"\"{k}\" \"{v}\"\n" for k, v in kv.items()) + body + "}\n"

def main():
    out = []
    for name, (x, y), z, w, h, cost in DOORS:
        tgt = f"bod_debris_{name}"
        out.append(ent({"classname": "trigger_use", "targetname": "zombie_debris", "target": tgt, "zombie_cost": str(cost),
                        "script_flag": f"bod_open_{name}", "cursorhint": "HINT_ACTIVATE"},
                       brush(x - w / 2 - 40, y - 64, z, x + w / 2 + 40, y + 64, z + 100, "trigger")))
        out.append(ent({"classname": "script_brushmodel", "DYNAMICPATH": "1", "script_noteworthy": "clip", "targetname": tgt, "spawnflags": "1"},
                       brush(x - w / 2, y - 14, z, x + w / 2, y + 14, z + h, "clip")))
        n = max(1, round(w / 90))
        for i in range(n):
            px = x - w / 2 + (i + .5) * w / n
            out.append(ent({"classname": "script_model", "model": RUBBLE, "origin": f"{px:.0f} {y} {z}", "angles": f"0 {(i * 67) % 360} 0",
                            "modelscale": f"{min(1.6, max(.8, h / 120)):.2f}", "targetname": tgt}))
    txt = open(MAP, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in txt[:2000] else "\n"
    txt = txt.replace("\r\n", "\n")
    parts = re.split(r"(?=^// entity )", txt, flags=re.M)
    txt = "".join(p for p in parts if not p.startswith("// entity boddoor")).rstrip("\n") + "\n"
    txt += "".join(f"// entity boddoor {i}\n{e}" for i, e in enumerate(out))
    open(MAP, "w", encoding="utf-8", errors="surrogateescape", newline="").write(txt.replace("\n", nl))
    z = open(ZONE, encoding="utf-8").read()
    if f"xmodel,{RUBBLE}" not in z:
        open(ZONE, "w", encoding="utf-8").write(z.replace("zbarrier,zmcore_bgb_machine", f"zbarrier,zmcore_bgb_machine\nxmodel,{RUBBLE}"))
    print(f"debris doors {len(DOORS)}")

if __name__ == "__main__":
    sys.exit(main())
