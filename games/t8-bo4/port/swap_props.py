"""Replace the MotD prop misc_models in bodfull with BoD's own catalogue placements -> <map>.base_bodprops (add_zones reads it)."""
import json, re, sys, uuid

R = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
SRC = R + r"\map_source\zm\zm_alcatraz_bodfull.map.bak_prezones"
DST = R + r"\map_source\zm\zm_alcatraz_bodfull.map.base_bodprops"
ZONE = R + r"\usermaps\zm_alcatraz_bodfull\zone_source\zm_alcatraz_bodfull.zone"
CAT = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_placements_catalog.json"
GDTS = [R + r"\source_data\bod_props.gdt", R + r"\source_data\bod_props2.gdt"]
STOCK = {"p7_debris_concrete_rubble_sm_10"}

def guid(): return "{" + str(uuid.uuid4()).upper() + "}"

def main():
    have = set(STOCK)
    for g in GDTS:
        have |= set(re.findall(r'^\s*"([^"]+)"\s*\(\s*"xmodel\.gdf"', open(g, encoding="utf-8", errors="replace").read(), re.M))
    t = open(SRC, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in t[:2000] else "\n"
    t = t.replace("\r\n", "\n")
    ents = re.split(r"(?=^// entity \d+\n)", t, flags=re.M)
    def motd(e):
        m = re.search(r'^"model" "([^"]+)"', e, re.M)
        return '"classname" "misc_model"' in e and m and not m.group(1).startswith("bodgfx_")
    keep = [e for e in ents if not motd(e)]
    out, used, skipped = [], set(), 0
    for r in json.load(open(CAT)):
        if not r.get("use"): continue
        if r["model"] not in have: skipped += 1; continue
        used.add(r["model"])
        o, a = r["origin"], r["angles"]
        out.append("{\nguid \"" + guid() + "\"\n\"classname\" \"misc_model\"\n" f"\"model\" \"{r['model']}\"\n\"origin\" \"{o[0]:.4f} {o[1]:.4f} {o[2]:.4f}\"\n"
                   f"\"angles\" \"{a[0]:.4f} {a[1]:.4f} {a[2]:.4f}\"\n\"modelscale\" \"{r.get('scale', 1):.4f}\"\n\"static\" \"1\"\n"
                   + "".join(f"\"lightingstate{i}\" \"1\"\n" for i in range(1, 5)) + "}\n")
    body = "".join(keep).rstrip("\n") + "\n" + "".join(f"// entity bodprop {i}\n{e}" for i, e in enumerate(out))
    open(DST, "w", encoding="utf-8", errors="surrogateescape", newline="").write(body.replace("\n", nl))
    # zone: swap the MotD prop xmodel lines for the BoD ones
    z = open(ZONE, encoding="utf-8").read()
    import os
    if not os.path.exists(ZONE + ".bak_premotdswap"):
        open(ZONE + ".bak_premotdswap", "w", encoding="utf-8").write(z)
    lines = [l for l in z.splitlines() if not (l.startswith("xmodel,") and not l.startswith(("xmodel,bodgfx_", "xmodel,p7_debris_concrete_rubble_lg_03")))]
    lines += [f"xmodel,{m}" for m in sorted(used - STOCK)]
    open(ZONE, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"dropped {len(ents) - len(keep)} MotD props; placed {len(out)} BoD props ({len(used)} models); skipped {skipped} (model not imported)")

if __name__ == "__main__":
    sys.exit(main())
