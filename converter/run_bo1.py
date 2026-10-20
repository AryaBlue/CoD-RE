"""Convert a BO1 zombies map to a BO2 Plutonium map with the BO1-enabled B2W fork (b2w_bo1).

usage: python313\\python.exe run_bo1.py [bo1_map=zombie_theater] [project] [--bo1 DIR] [--bo2 DIR]
       [--extract-only] [--redump] [--no-install] [--from stage|build-mod|compile-scripts|bridge-link|audit]
       python313\\python.exe run_bo1.py --list-maps [--bo1 DIR]     (JSON: every BO1 map, installed or not)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "b2w_bo1" / "src"))
os.environ["PYTHONPATH"] = str(ROOT / "b2w_bo1" / "src")
# BO1 bring-up: unported BO1 features are listed in the stage report instead of stopping the build
os.environ.setdefault("WAW2BO2_ALLOW_STAGE_ERRORS", "1")
# use BO2's own weapons (same name, or b2w_bo1/src/waw2bo2/compat/bo1_bo2_weapons.json) instead of porting BO1's
os.environ.setdefault("WAW2BO2_BO2_WEAPONS", "1")
# translated shaders shared by every map's build (b2w_bo1/src/waw2bo2/shaders.py)
os.environ.setdefault("WAW2BO2_SHADER_CACHE", str(ROOT / "b2w_work" / "shader_cache"))

# Auto-detect the game installs from the user's Steam libraries (any drive), so
# this works on any machine. --bo1/--bo2 override; a clear error asks for them
# when a game isn't found instead of silently using someone else's path.
from waw2bo2.launcher import find_steam_app
def _detect(folder):
    found = find_steam_app(folder)
    return str(found) if found else None
BO1 = _detect("Call of Duty Black Ops")
BO2 = _detect("Call of Duty Black Ops II")
T5_UNLINKER = ROOT / "oat_ext" / "build" / "bin" / "Release_x86" / "Unlinker.exe"

# Every BO1 zombies map: BO2 project name, menu text, pack. A map is installed when zone/Common/<map>.ff
# exists (DLC owners have it; without the DLC only <map>_patch.ff ships).
MAPS = {
    "zombie_theater": dict(project="zm_kino", pack="Base game", menu_title="Kino der Toten",
        menu_description="Group 935 test subjects return to an abandoned Berlin theater. Survive the undead, "
                         "link the teleporter and find the film reels.",
        menu_location="Berlin, Germany", menu_longitude="-45", menu_latitude="58"),
    "zombie_pentagon": dict(project="zm_five", pack="Base game", menu_title="Five",
        menu_description="The Pentagon is overrun. Hold the war room, the labs and the elevators "
                         "while the Pentagon Thief steals your guns.",
        menu_location="Washington, D.C., USA"),
    "zombie_cod5_prototype": dict(project="zm_nacht", pack="Rezurrection", menu_title="Nacht der Untoten",
        menu_description="Where it all began: a ruined bunker in the swamp, boarded windows and the undead "
                         "trying every way in.",
        menu_location="Germany"),
    "zombie_cod5_asylum": dict(project="zm_verruckt", pack="Rezurrection", menu_title="Verruckt",
        menu_description="An asylum split in two. Restore the power, open the halls and survive the "
                         "patients who never left.",
        menu_location="Wittenau Sanatorium, Germany"),
    "zombie_cod5_sumpf": dict(project="zm_shinonuma", pack="Rezurrection", menu_title="Shi No Numa",
        menu_description="A flooded Japanese research outpost. Hold the huts, run the swamp and use the "
                         "zipline and flogger traps.",
        menu_location="Rising Sun Facility, Japan"),
    "zombie_cod5_factory": dict(project="zm_derriese", pack="Rezurrection", menu_title="Der Riese",
        menu_description="Group 935's factory: link the teleporters, Pack-a-Punch your weapons and hold out "
                         "against the undead and the hellhounds.",
        menu_location="Breslau, Germany"),
    "zombie_cosmodrome": dict(project="zm_ascension", pack="First Strike", menu_title="Ascension",
        menu_description="A Soviet launch facility. Ride the lunar landers, launch the rocket and watch out "
                         "for the space monkeys.",
        menu_location="Baikonur, Kazakhstan"),
    "zombie_coast": dict(project="zm_cotd", pack="Escalation", menu_title="Call of the Dead",
        menu_description="A frozen shipwreck and lighthouse, with a director who won't stay down.",
        menu_location="Siberia, Russia"),
    "zombie_temple": dict(project="zm_shangrila", pack="Annihilation", menu_title="Shangri-La",
        menu_description="A jungle temple full of traps, napalm and shrieker zombies.",
        menu_location="Himalayas"),
    "zombie_moon": dict(project="zm_moon_bo1", pack="Rezurrection", menu_title="Moon",
        menu_description="Griffin Station on the Moon: low gravity, no air and the hacker.",
        menu_location="The Moon"),
}


def installed(bo1_map: str, bo1: str) -> bool:
    return (Path(bo1) / "zone" / "Common" / f"{bo1_map}.ff").is_file()


def unlink_images(bo1: str, zone: str, out: Path) -> Path:
    """The images of one BO1 zone, as DDS (once per zone)."""
    folder = out / zone
    if not (folder / "images").is_dir():
        zones = Path(bo1) / "zone"
        subprocess.run([str(T5_UNLINKER), "--no-color", "--include-assets", "image", "--image-format", "DDS",
                        "--search-path", f"{zones / 'Common'};{zones / 'English'}", "--output-folder", str(folder),
                        str(zones / "Common" / f"{zone}.ff")], check=False, stdout=subprocess.DEVNULL)
    return folder / "images"


def menu_art(bo1_map: str, bo1: str) -> Path | None:
    """work/<map>_menu/art/{blit,large,blur}.png (plus optional icon/preview.png the user drops in), made from
    the map's own BO1 loading screen and lobby picture the first time it is needed."""
    art = ROOT / "work" / ("kino_menu" if bo1_map == "zombie_theater" else f"{bo1_map}_menu") / "art"
    if (art / "blit.png").is_file():
        return art
    images = ROOT / "work" / "bo1_menu_images"
    found = {}
    for zone in ("frontend", "code_post_gfx", bo1_map, f"{bo1_map}_patch"):
        if not (Path(bo1) / "zone" / "Common" / f"{zone}.ff").is_file():
            continue
        folder = unlink_images(bo1, zone, images)
        for role, name in (("preview", bo1_map), ("loadscreen", f"loadscreen_{bo1_map}")):
            if role not in found and (folder / f"{name}.dds").is_file():
                found[role] = folder / f"{name}.dds"
    if "loadscreen" not in found:
        return None
    sys.path.insert(0, str(ROOT / "tools"))
    import make_menu_art
    from PIL import Image
    art.mkdir(parents=True, exist_ok=True)
    big = make_menu_art.large(Image.open(found["loadscreen"]))
    big.save(art / "large.png")
    make_menu_art.blur(big).save(art / "blur.png")
    make_menu_art.blit(Image.open(found.get("preview", found["loadscreen"]))).save(art / "blit.png")
    print(f"menu art made from the map's BO1 images: {art}", flush=True)
    return art


def settings_for(bo1_map: str, project: str, bo1: str = BO1, bo2: str = BO2):
    from waw2bo2.launcher import Settings
    menu = {k: v for k, v in MAPS.get(bo1_map, {}).items() if k not in ("project", "pack")}
    menu.setdefault("menu_mode", "Zombies")
    art = menu_art(bo1_map, bo1)
    if art is not None:
        menu.update(menu_blit=str(art / "blit.png"), menu_large=str(art / "large.png"), menu_blur=str(art / "blur.png"))
        if (art / "icon.png").is_file():
            menu.update(menu_icon=str(art / "icon.png"))
        if (art / "preview.png").is_file():
            menu.update(menu_preview=str(art / "preview.png"))
    return Settings(
        **menu,
        waw=bo1,
        bo2=bo2,
        t4=str(T5_UNLINKER.parent),
        t6=str(ROOT / "reference" / "b2w" / "vendor" / "OpenAssetToolsT6" / "build" / "bin" / "Release_x86"),
        decoder=str(ROOT / "b2w_bo1" / "tools" / "bin" / "xaudio_wma_decoder.exe"),
        work=str(ROOT / "b2w_work"),
        fastfile=str(Path(bo1) / "zone" / "Common" / f"{bo1_map}.ff"),
        project=project,
        # prefer BO2's own gameplay content: stock perk machines/gameplay. remaster (original BO2
        # materials on shared props) is off: it unpacks ~37 whole BO2 levels on a map's first build
        bo2_stock_perks=True,
        remaster=False,
        verbose=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bo1_map", nargs="?", default="zombie_theater")
    ap.add_argument("project", nargs="?", help="BO2 map name (default: the map's own, e.g. zm_kino)")
    ap.add_argument("--bo1", default=BO1, help="Black Ops install folder")
    ap.add_argument("--bo2", default=BO2, help="Black Ops II install folder")
    ap.add_argument("--list-maps", action="store_true", help="print every BO1 map as JSON and exit")
    ap.add_argument("--extract-only", action="store_true")
    ap.add_argument("--redump", action="store_true")
    ap.add_argument("--no-install", action="store_true", help="build only; leave the installed Plutonium mod alone")
    ap.add_argument("--from", dest="from_step", choices=["stage", "build-mod", "compile-scripts", "bridge-link", "audit"],
                    help="resume at this step, reusing the earlier steps' output from the last build")
    ap.add_argument("--fast-link", action="store_true",
                    help="WAW2BO2_FAST_LINK: reuse cached stock ipak images and build-mod's shader dump")
    a = ap.parse_args()
    if a.fast_link:
        os.environ["WAW2BO2_FAST_LINK"] = "1"
    if not a.bo1:
        print("error: Black Ops 1 was not found in your Steam libraries; pass --bo1 <install folder>",
              file=sys.stderr)
        return 2
    if a.list_maps:
        print(json.dumps([dict(map=name, project=m["project"], title=m["menu_title"], pack=m["pack"],
                               installed=installed(name, a.bo1)) for name, m in MAPS.items()], indent=1))
        return 0
    if not installed(a.bo1_map, a.bo1):
        print(f"error: {a.bo1_map}.ff is not in {a.bo1}\\zone\\Common (its DLC is not installed)", file=sys.stderr)
        return 2
    if not a.bo2:
        print("error: Black Ops II was not found in your Steam libraries; pass --bo2 <install folder>",
              file=sys.stderr)
        return 2
    project = a.project or MAPS.get(a.bo1_map, {}).get("project") or "zm_" + a.bo1_map.removeprefix("zombie_")
    if a.from_step:
        os.environ["WAW2BO2_FROM_STEP"] = a.from_step
    from waw2bo2 import all2raw, builddriver
    settings = settings_for(a.bo1_map, project, a.bo1, a.bo2)
    if a.extract_only:
        all2raw.extract_all(settings, refresh=a.redump)
        return 0
    code = builddriver.build(settings, redump=a.redump)
    if code == 0:
        # install into Plutonium's mods/<project> (the B2W launcher's package step)
        from waw2bo2 import package
        paths = builddriver.BuildPaths.for_settings(settings)
        # hardening: world data the engine owns at runtime or would index out of range (warns, never fails)
        print("== 7. checking the linked world against stock BO2 maps", flush=True)
        world = subprocess.run([sys.executable, str(ROOT / "tools" / "check_world.py"),
                                str(paths.stage / "zone_out" / project / f"{project}.ff")])
        if world.returncode:
            print("WARNING world check flagged the lines above (tools/check_world.py)", flush=True)
        if a.no_install:
            print("not installed (--no-install)", flush=True)
            return code
        print("installed", package.package(project, paths.stage / "zone_out" / project, paths.mod / "out"),
              flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
