"""Convert a BO1 zombies map to a BO2 Plutonium map with the BO1-enabled B2W fork (b2w_bo1).

usage: python313\\python.exe run_bo1.py [bo1_map=zombie_theater] [project=zm_kino] [--extract-only] [--redump]
       [--from stage|build-mod|compile-scripts|bridge-link|audit]
"""
import argparse
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

from waw2bo2 import all2raw, builddriver  # noqa: E402
from waw2bo2.launcher import Settings  # noqa: E402

BO1 = r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops"
BO2 = r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops II"


# Per-map front-end details: globe position (mapstable columns 16/17) and art from tools/make_menu_art.py
MENUS = {
    "zombie_theater": dict(
        menu_title="Kino der Toten",
        menu_description="Group 935 test subjects return to an abandoned Berlin theater. Survive the undead, "
                         "link the teleporter and find the film reels.",
        menu_mode="Zombies",
        menu_location="Berlin, Germany",
        menu_longitude="-45",
        menu_latitude="58",
        art=ROOT / "work" / "kino_menu" / "art",
    ),
}


def settings_for(bo1_map: str, project: str) -> Settings:
    menu = dict(MENUS.get(bo1_map, {}))
    art = menu.pop("art", None)
    if art is not None and (art / "blit.png").is_file():
        menu.update(menu_blit=str(art / "blit.png"), menu_large=str(art / "large.png"), menu_blur=str(art / "blur.png"))
        if (art / "icon.png").is_file():
            menu.update(menu_icon=str(art / "icon.png"))
        if (art / "preview.png").is_file():
            menu.update(menu_preview=str(art / "preview.png"))
    return Settings(
        **menu,
        waw=BO1,
        bo2=BO2,
        t4=str(ROOT / "oat_ext" / "build" / "bin" / "Release_x86"),
        t6=str(ROOT / "reference" / "b2w" / "vendor" / "OpenAssetToolsT6" / "build" / "bin" / "Release_x86"),
        decoder=str(ROOT / "b2w_bo1" / "tools" / "bin" / "xaudio_wma_decoder.exe"),
        work=str(ROOT / "b2w_work"),
        fastfile=str(Path(BO1) / "zone" / "Common" / f"{bo1_map}.ff"),
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
    ap.add_argument("project", nargs="?", default="zm_kino")
    ap.add_argument("--extract-only", action="store_true")
    ap.add_argument("--redump", action="store_true")
    ap.add_argument("--from", dest="from_step", choices=["stage", "build-mod", "compile-scripts", "bridge-link", "audit"],
                    help="resume at this step, reusing the earlier steps' output from the last build")
    a = ap.parse_args()
    if a.from_step:
        os.environ["WAW2BO2_FROM_STEP"] = a.from_step
    settings = settings_for(a.bo1_map, a.project)
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
                                str(paths.stage / "zone_out" / a.project / f"{a.project}.ff")])
        if world.returncode:
            print("WARNING world check flagged the lines above (tools/check_world.py)", flush=True)
        print("installed", package.package(a.project, paths.stage / "zone_out" / a.project, paths.mod / "out"),
              flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
