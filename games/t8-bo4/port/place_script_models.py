"""BoD script_models (teleporters, generators, panels, lights...) as static misc_models in .map.base_bodprops + zone lines.
Doors and chalk outlines are left out (doors would block routes; we place our own wallbuys)."""
import json, re, sys, uuid

R = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
BASE = R + r"\map_source\zm\zm_alcatraz_bodfull.map.base_bodprops"
ZONE = R + r"\usermaps\zm_alcatraz_bodfull\zone_source\zm_alcatraz_bodfull.zone"
SM = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_script_models.json"
GDTS = [R + r"\source_data\bod_props.gdt", R + r"\source_data\bod_props2.gdt"]
LEAVE = re.compile(r"chalk|door")

def main():
    have = set()
    for g in GDTS:
        have |= set(re.findall(r'^\s*"([^"]+)"\s*\(\s*"xmodel\.gdf"', open(g, encoding="utf-8", errors="replace").read(), re.M))
    b = open(BASE, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in b[:2000] else "\n"
    b = re.sub(r"// entity bodscript \d+\r?\n\{.*?\r?\n\}\r?\n", "", b, flags=re.S)
    out, used = [], set()
    for x in json.load(open(SM)):
        m = x["model"]
        if x["status"] != "ripped" or LEAVE.search(m) or m not in have: continue
        o, a = x["origin"], x["angles"]
        used.add(m)
        out.append([f"// entity bodscript {len(out)}", "{", 'guid "{' + str(uuid.uuid4()).upper() + '}"', '"classname" "misc_model"', f'"model" "{m}"',
                    f'"origin" "{o[0]:.2f} {o[1]:.2f} {o[2]:.2f}"', f'"angles" "{a[0]:.2f} {a[1]:.2f} {a[2]:.2f}"', '"modelscale" "1"', '"static" "1"']
                   + [f'"lightingstate{i}" "1"' for i in range(1, 5)] + ["}"])
    b = b.rstrip("\r\n") + nl + nl.join(nl.join(e) for e in out) + nl
    open(BASE, "w", encoding="utf-8", errors="surrogateescape", newline="").write(b)
    z = open(ZONE, encoding="utf-8").read()
    add = [f"xmodel,{m}" for m in sorted(used) if f"xmodel,{m}\n" not in z]
    open(ZONE, "w", encoding="utf-8").write(z.rstrip("\n") + "\n" + "".join(l + "\n" for l in add))
    print(f"script models placed {len(out)} ({len(used)} models); zone lines added {len(add)}")

if __name__ == "__main__":
    sys.exit(main())
