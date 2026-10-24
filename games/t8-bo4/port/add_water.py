"""Sea plane round the island: BO4's ocean is a water system, not shell geometry, so it never came across. Run after add_zones (it rewrites the map)."""
import re, sys, uuid

MAP = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\map_source\zm\zm_alcatraz_bodfull.map"
SEA_Z, TILE = -100.0, 4096
X0, X1, Y0, Y1 = -32768, 45056, -4096, 40960
MAT = "t7_water_sector_flow"
UV, LM = 0.68, 1 / 16  # texel and lightmap density copied from the stock mp_sector water patches

def patch(x0, y0, x1, y1):
    v = lambda x, y: f"\tv {x} {y} {SEA_Z:g} t {y * UV:.4f} {x * UV:.4f} {x * LM:.4f} {-y * LM:.4f}\n"
    return (" {\n  guid \"{" + str(uuid.uuid4()).upper() + "}\"\n  mesh\n  {\n  contents umbraTarget;\n  toolFlags;\n   " + MAT + "\n   lightmap_gray\n   2 2 0 8\n"
            "   (\n" + v(x0, y1) + v(x1, y1) + "   )\n   (\n" + v(x0, y0) + v(x1, y0) + "   )\n  }\n }\n")

def main():
    t = open(MAP, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in t[:2000] else "\n"
    t = t.replace("\r\n", "\n")
    t = re.sub(r"// brush bodwater \d+\n \{\n.*?\n \}\n", "", t, flags=re.S)
    i = t.index("\n// entity 1\n")
    j = t.rindex("\n}", 0, i)  # close of worldspawn
    out, n = [], 0
    for x in range(X0, X1, TILE):
        for y in range(Y0, Y1, TILE):
            out.append(f"// brush bodwater {n}\n" + patch(x, y, x + TILE, y + TILE)); n += 1
    t = t[:j + 1] + "".join(out) + t[j + 1:]
    open(MAP, "w", encoding="utf-8", errors="surrogateescape", newline="").write(t.replace("\n", nl))
    print(f"sea patches {n} at z {SEA_Z:g} ({MAT})")

if __name__ == "__main__":
    sys.exit(main())
