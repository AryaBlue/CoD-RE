"""BO3 sun (ssi) + world fog (fsi) GDT entries for a usermap, cloned from stock entries with overrides.
Default preset: Blood of the Dead's stormy Aether look, approximated by eye."""
import argparse
import re
from pathlib import Path

TOOLS = Path(r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130")

BOD_SUN = {  # dim cold green-blue moonlight; pitch as stock night, exposure a little darker than zm_factory
    "colorSRGB": "0.46 0.62 0.6 1", "ev": "5", "evcmp": "2", "evmin": "2.5", "evmax": "3.5", "stops": "-1.5",
    "pitch": "130", "yaw": "140", "skyboxmodel": "skybox_default_night"}
BOD_FOG = {  # stock-style atmospheric fog (worldfog renders nothing; scatter needs the sun term or extinction alone turns it red)
    "worldfog": "0", "atmospherefog": "1", "atmosphereextinctionstrength": "1", "atmosphereinscatterstrength": "8",
    "atmospherefogcolor": "0.62 0.86 0.82 1", "atmospherefogdensity": "1", "atmospheresunenabled": "1",
    "atmospherehazecolor": "0.55 0.75 0.72 1", "atmospherehazedensity": "0.4", "atmospherehazebasedist": "2000",
    "atmospherehazefadedist": "4000", "basedist": "200", "halfdist": "2500", "baseheight": "1150", "halfheight": "520",
    "fogcolor": "0.55 0.75 0.72 1", "sunfog": "0", "sunintensityscale": "0"}


def clone(gdt, src, name, fields):
    text = (TOOLS / "source_data" / gdt).read_text(errors="replace")
    gdf = gdt.replace(".gdt", ".gdf")
    out = re.search(rf'\t"{src}" \( "{gdf}" \)\n\t\{{\n.*?\n\t\}}\n', text, re.S).group()
    out = out.replace(f'"{src}" (', f'"{name}" (', 1)
    for key, value in fields.items():
        if f'"{key}" "' in out:
            out = re.sub(rf'"{key}" "[^"]*"', lambda _: f'"{key}" "{value}"', out)
        else:
            out = out.replace("\n\t}\n", f'\n\t\t"{key}" "{value}"\n\t}}\n', 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="asset name for both the ssi and the fog, e.g. zm_alcatraz_bod")
    ap.add_argument("--gdt", default=None, help="output GDT name under source_data (default <name>_atmos.gdt)")
    args = ap.parse_args()
    body = clone("ssi.gdt", "default_night", args.name, BOD_SUN) + clone("fog.gdt", "zm_factory_afog", args.name, BOD_FOG)
    out = TOOLS / "source_data" / (args.gdt or f"{args.name}_atmos.gdt")
    out.write_text("{\n" + body + "}\n")
    print(f"{out}: ssi + fog '{args.name}', skybox {BOD_SUN['skyboxmodel']}")


if __name__ == "__main__":
    main()
