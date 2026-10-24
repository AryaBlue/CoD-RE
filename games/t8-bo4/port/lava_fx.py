"""Lava: BO4 draws it from the emissive map (colour is black, flow map drives motion). Use the emissive as the colour PNG, and after the
bodisland import switch those materials to BO3 lit_emissive_scroll so it glows and drifts. Usage: lava_fx.py png | gdt"""
import os, re, sys
from PIL import Image

SHELL = r"F:\ClaudeWork\bo3\bod_port\geo\shell_chunks_v3\_images"
TGA = r"F:\ClaudeWork\c2m\app2\exported_images\black_ops_4"
GDT = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\source_data\bodisland.gdt"
LAVA = {"t8_zm_esc_lava_flow": ("i_t8_zm_esc_lava_flow_e", 0.03, 0.05), "t8_zm_esc_lava_river_01_flow": ("i_t8_zm_esc_lava_river_01_e", 0.04, 0.02),
        "t8_zm_esc_lava_vertical_flow": ("i_t8_zm_esc_lava_vertical_flow_e", 0.0, -0.08)}
GLOW = "3"

def png():
    for m, (e, _, _) in LAVA.items():
        d = os.path.join(SHELL, m)
        if not os.path.isdir(d): print("not in shell:", m); continue
        Image.open(os.path.join(TGA, e + ".TGA")).convert("RGB").save(os.path.join(d, m + "_c.png"))
        print("emissive colour", m)

def gdt():
    t = open(GDT, encoding="utf-8", errors="replace").read()
    for m, (_, u, v) in LAVA.items():
        hit = re.search(r'(\n\s*"bodisland_' + m + r'"\s*\(\s*"material\.gdf"\s*\)\s*\{)(.*?)(\n\s*\})', t, re.S)
        if not hit: continue
        b = hit.group(2)
        img = re.search(r'"colorMap" "([^"]*)"', b).group(1)
        for k, val in (("materialType", "lit_emissive_scroll"), ("colorMap00", img), ("colorTint1", "1 1 1 1"), ("scaleRGB", GLOW),
                       ("gUVScroll02_Angle", f"{u:g}"), ("gUVScroll03_Angle", f"{v:g}"), ("emissiveIncompetence", "1")):
            if re.search(rf'"{k}" "[^"]*"', b): b = re.sub(rf'"{k}" "[^"]*"', f'"{k}" "{val}"', b)
            else: b += f'\n\t\t"{k}" "{val}"'
        t = t[:hit.start(2)] + b + t[hit.end(2):]
        print("scroll material", m)
    open(GDT, "w", encoding="utf-8").write(t)

if __name__ == "__main__":
    {"png": png, "gdt": gdt}[sys.argv[1]]()
