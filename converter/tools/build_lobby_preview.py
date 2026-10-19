"""Front-end-only preview of a converted map: globe entry, custom games entry, menu art and text.

Builds B2W's frontend zone (mod_load.ff + the menu image pack) for the project and installs it as
mods/<project> with the same zone as mod.ff, so the entry can be seen before the map itself is built.
Selecting the map does not load anything yet.

usage: python313\\python.exe tools\\build_lobby_preview.py [bo1_map=zombie_theater] [project=zm_kino]
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b2w_bo1" / "src"))

import run_bo1  # noqa: E402
from waw2bo2 import all2raw, menuart, modzone  # noqa: E402
from waw2bo2.package import plutonium_mods_dir  # noqa: E402


def main() -> int:
    bo1_map = sys.argv[1] if len(sys.argv) > 1 else "zombie_theater"
    project = sys.argv[2] if len(sys.argv) > 2 else "zm_kino"
    settings = run_bo1.settings_for(bo1_map, project)
    bo2 = Path(settings.bo2)
    linker = Path(settings.t6) / "Linker.exe"
    # newest BO2 stock view (the receipt goes stale while All2Raw is still writing raw/)
    views = all2raw.CachePaths.for_settings(settings).bo2 / "views"
    stock = max((p for p in views.iterdir() if (p / "catalog.json").is_file()), key=lambda p: p.stat().st_mtime)

    work = ROOT / "work" / f"lobby_{project}"
    shutil.rmtree(work, ignore_errors=True)
    project_root = work / "project"
    project_root.mkdir(parents=True)
    menuart.stage_art(settings, project_root)
    ff = modzone.link_lobby(bo2, project_root, project, work / "build", linker, stock)
    modzone.verify_lobby_tables(ff, Path(settings.t6) / "Unlinker.exe", work / "build", project)

    out = ff.parent
    dest = plutonium_mods_dir() / project
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ff, dest / "mod_load.ff")
    shutil.copy2(ff, dest / "mod.ff")
    for pack in out.glob("*.ipak"):
        shutil.copy2(pack, dest / pack.name)
    metadata = json.loads((project_root / "menu.json").read_text(encoding="utf-8"))
    (dest / "mod.json").write_text(json.dumps({"name": metadata["title"] + " (preview)",
                                               "description": metadata["description"], "version": "0.0.1"}, indent=2) + "\n",
                                   encoding="utf-8")
    print("installed", dest, sorted(p.name for p in dest.iterdir()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
