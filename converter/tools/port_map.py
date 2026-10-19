"""BO1 (T5) zombies map -> BO2 (T6) map zones, using the OAT BSP fork with the T5 BSP dumper.

The BO1 world (geometry, collision, brush models) and its gameplay entities, converted to BO2 conventions, replace the
world of a stock BO2 zombies map (the donor, zm_nuked) inside a separate Plutonium mod. The donor's level scripts are
rebuilt (zm_nuked_patch.ff) with the BO1 map's zones and without the donor's own set pieces.
Props are left out and every surface uses a placeholder material until materials/models are ported.

usage: python port_map.py [bo1_map=zombie_theater] [--props] [--install MODNAME]
"""
import argparse, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zm_gameplay  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OAT = os.path.join(ROOT, "oat-bsp", "build", "bin", "Release_x86")
GSC_TOOL = os.environ.get("GSC_TOOL", os.path.join(ROOT, "tools", "gsc-tool", "gsc-tool.exe"))
BO1 = os.environ.get("BO1_DIR", r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops")
BO2 = os.environ.get("BO2_DIR", r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops II")
PLUTO_MODS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Plutonium", "storage", "t6", "mods")
DONOR = "zm_nuked"
# asset types OAT cannot re-link from a loaded zone
SKIP_TYPES = {"keyvaluepairs"}


def run(args, log, env=None, quiet=False):
    print(">", os.path.basename(args[0]), " ".join(args[1:])[:200])
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        r = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, env=env)
    lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
    if not quiet:
        errors = [l for l in lines if "ERROR" in l and "Missing asset" not in l]
        missing = sum("Missing asset" in l for l in lines)
        for line in errors[:10] + ([f"({missing} missing assets)"] if missing else []) + lines[-1:]:
            print("   ", line)
    return r.returncode


def bo1_zone(name):
    for sub in ("zone/Common", "zone/English"):
        p = os.path.join(BO1, sub, name + ".ff")
        if os.path.isfile(p):
            return p
    sys.exit(f"BO1 zone {name}.ff not found under {BO1}")


def bo2_zone(name):
    return os.path.join(BO2, "zone", "all", name + ".ff")


def unlink(zone, out, assets, log, env=None, load=()):
    shutil.rmtree(out, ignore_errors=True)
    args = [os.path.join(OAT, "Unlinker.exe")]
    for z in load:
        args += ["--load", z]
    return run(args + ["--include-assets", assets, "-o", out, zone], log, env)


def zone_listing(zone, log):
    """Asset lines ("type,name") of a stock zone."""
    run([os.path.join(OAT, "Unlinker.exe"), "--list", zone], log, quiet=True)
    lines = []
    for l in open(log, encoding="utf-8", errors="replace").read().splitlines():
        if ", " not in l or l.startswith(("Loaded", "Unloaded", "Zone", "Finished")):
            continue
        kind, name = l.split(", ", 1)
        if kind in SKIP_TYPES or "//" in name:  # "//" starts a comment in zone files; such assets come in as dependencies
            continue
        lines.append(f"{kind},{name}")
    return lines


def link(name, work, stock_zone, raw_files, is_map, extra_lines=()):
    """Relinks a stock zone with replacement raw files; returns the built .ff path."""
    build = os.path.join(work, "build_" + name)
    shutil.rmtree(build, ignore_errors=True)
    raw = os.path.join(build, "zone_raw", name)
    os.makedirs(os.path.join(build, "zone_source"))
    for rel, src in raw_files.items():
        dst = os.path.join(raw, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    header = [">game,T6"] + ([">map,zm"] if is_map else []) + [""]
    lines = header + zone_listing(stock_zone, os.path.join(work, name + "_list.log"))
    lines += [l for l in extra_lines if l not in lines]
    open(os.path.join(build, "zone_source", name + ".zone"), "w").write("\n".join(lines) + "\n")
    rc = run([os.path.join(OAT, "Linker.exe"), "-b", build, "--load", stock_zone, name], os.path.join(work, name + "_link.log"))
    ff = os.path.join(build, "zone_out", name, name + ".ff")
    if not os.path.isfile(ff):
        sys.exit(f"linking {name} failed (exit {rc}), see {work}\\{name}_link.log")
    print(f"    built {name}.ff ({os.path.getsize(ff) // 1024} KB)")
    return ff


def compile_gsc(sources, work):
    """{internal path: source text} -> {internal path: compiled file}."""
    base = os.path.join(work, "gsc")
    shutil.rmtree(base, ignore_errors=True)
    for path, text in sources.items():
        dst = os.path.join(base, "src", path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(text)
    # gsc-tool names a script after its path minus the first folder, so compile "src" to get "maps/mp/..."
    log = os.path.join(work, "gsc.log")
    with open(log, "w") as f:
        subprocess.run([GSC_TOOL, "-m", "comp", "-g", "t6", "-s", "pc", "src"], cwd=base, stdout=f, stderr=subprocess.STDOUT)
    out = {}
    for path in sources:
        compiled = os.path.join(base, "compiled", "t6", path)
        if not os.path.isfile(compiled):
            sys.exit(f"gsc compile failed for {path}, see {log}")
        out[path] = compiled
    return out


def decompile(compiled, work):
    base = os.path.join(work, "decomp")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base)
    shutil.copy(compiled, base)
    subprocess.run([GSC_TOOL, "-m", "decomp", "-g", "t6", "-s", "pc", os.path.basename(compiled)], cwd=base,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return open(os.path.join(base, "decompiled", "t6", os.path.basename(compiled)), encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bo1_map", nargs="?", default="zombie_theater")
    ap.add_argument("--props", action="store_true", help="include static models (needs ported xmodels)")
    ap.add_argument("--zombies", action="store_true", help="let zombies spawn (needs converted AI paths)")
    ap.add_argument("--trace", action="store_true", help="print each level script step to the console")
    ap.add_argument("--install", metavar="MODNAME", help="copy the built zones into this Plutonium mod folder")
    a = ap.parse_args()

    work = os.path.join(ROOT, "work", a.bo1_map)
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ)
    if not a.props:
        env["OAT_T5BSP_NO_XMODELS"] = "1"
    common = [bo1_zone("common_zombie")]

    print("1. BO1 entities, level script and donor entities")
    dump = os.path.join(work, "dump")
    unlink(bo1_zone(a.bo1_map), dump, "mapents,rawfile", os.path.join(work, "dump_ents.log"), load=common)
    donor_dump = os.path.join(work, "donor")
    unlink(bo2_zone(DONOR), donor_dump, "mapents", os.path.join(work, "donor_ents.log"))
    bo1_ents = open(os.path.join(dump, "maps", a.bo1_map + ".d3dbsp.ents"), encoding="latin1").read()
    donor_ents = open(os.path.join(donor_dump, "maps", "mp", DONOR + ".d3dbsp.ents"), encoding="latin1").read()
    bo1_gsc = open(os.path.join(dump, "maps", a.bo1_map + ".gsc"), encoding="latin1").read()

    print("2. converting gameplay entities")
    ents, report = zm_gameplay.convert_ents(bo1_ents, donor_ents)
    for line in report:
        print("   ", line)
    ents_path = os.path.join(work, "bo2.ents")
    open(ents_path, "w", encoding="latin1").write(ents)
    env["OAT_T5BSP_ENTS"] = ents_path

    print("3. BSP dump")
    bsp = os.path.join(work, "bsp")
    rc = unlink(bo1_zone(a.bo1_map), bsp, "mapents,gfxworld,clipmap,comworld,lightdef", os.path.join(work, "dump_bsp.log"), env, load=common)
    gfx, col = os.path.join(bsp, "bsp", "map_gfx.glb"), os.path.join(bsp, "bsp", "map_col.glb")
    if rc != 0 or not (os.path.isfile(gfx) and os.path.isfile(col)):
        sys.exit(f"BSP dump failed (exit {rc}), see {work}\\dump_bsp.log")

    print("4. level scripts")
    init_zones, zone_body = zm_gameplay.bo1_zone_setup(bo1_gsc)
    print(f"    start zones {init_zones}, {zone_body.count('add_adjacent_zone')} zone links")
    patch_dump = os.path.join(work, "donor_patch")
    unlink(bo2_zone(DONOR + "_patch"), patch_dump, "script", os.path.join(work, "donor_patch.log"))
    level_src = decompile(os.path.join(patch_dump, "maps", "mp", DONOR + ".gsc"), work)
    standard_src = decompile(os.path.join(patch_dump, "maps", "mp", DONOR + "_standard.gsc"), work)
    level_src, standard_src, removed = zm_gameplay.patch_donor_scripts(level_src, standard_src, init_zones, zone_body, a.zombies)
    print(f"    removed {removed} donor set pieces")
    if a.trace:
        level_src = zm_gameplay.add_trace(level_src, "main", "main")
        standard_src = zm_gameplay.add_trace(standard_src, "main", "standard")
    sources = {f"maps/mp/{DONOR}.gsc": level_src, f"maps/mp/{DONOR}_standard.gsc": standard_src}
    if a.trace:
        # traced copy of the shared zombies setup; the map's patch zone loads after patch_zm, so this one wins
        common_dump = os.path.join(work, "patch_zm")
        unlink(bo2_zone("patch_zm"), common_dump, "script", os.path.join(work, "patch_zm.log"))
        zm_src = decompile(os.path.join(common_dump, "maps", "mp", "zombies", "_zm.gsc"), work)
        sources["maps/mp/zombies/_zm.gsc"] = zm_gameplay.add_trace(zm_src, "init", "zm_init")
    scripts = compile_gsc(sources, work)

    print("5. linking")
    map_ff = link(DONOR, work, bo2_zone(DONOR), {"bsp/map_gfx.glb": gfx, "bsp/map_col.glb": col}, True)
    patch_ff = link(DONOR + "_patch", work, bo2_zone(DONOR + "_patch"), scripts, False, [f"script,{p}" for p in scripts])

    if a.install:
        mod = os.path.join(PLUTO_MODS, a.install)
        os.makedirs(mod, exist_ok=True)
        for ff in (map_ff, patch_ff):
            shutil.copy(ff, os.path.join(mod, os.path.basename(ff)))
        # shared scripts can only be replaced from the mod folder (the stock patch zone's copy wins over ours)
        shutil.rmtree(os.path.join(mod, "maps"), ignore_errors=True)
        for path, compiled in scripts.items():
            if not path.startswith(f"maps/mp/{DONOR}"):
                dst = os.path.join(mod, path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(compiled, dst)
        print(f"installed into {mod}")


if __name__ == "__main__":
    main()
