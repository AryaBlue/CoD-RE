# BO1 to BO2 map converter

This converts a Black Ops 1 (T5) Zombies map into a Black Ops II (T6) map you can load in Plutonium. We built and
tested it on Kino der Toten (`zombie_theater`). It is work in progress and is separate from ZM Workshop.

## What you get

Right now (stage 1, a walk test) you get the map's walls, floors, collision, brush models and entities. Every
surface uses a grey placeholder material and there are no props. Kino builds over `zm_nuked` in a Plutonium mod called
`zm_bo1port_test`. We have not tested it in game yet.

## How it works

1. `oat-bsp/` is LJW-Dev's OpenAssetTools BSP fork (branch `t6-decompile-and-compile-bsp`). Its Linker can build the
   BO2 `gfxworld`, `clipmap`, `comworld`, `gameworldmp` and `mapents` assets from two neutral files:
   `bsp/map_gfx.glb` and `bsp/map_col.glb`.
2. Our addition is a BO1 BSP dumper (`BSPUnlinkerT5.cpp`, `BSPDumperT5.*`, registered in `ObjWriterT5.cpp`).
   You run `Unlinker.exe` on a BO1 map's `.ff`. It reads the world straight from the fastfile, so BO1 does not
   need to be running, and writes those two glb files. It handles the BO1 clipmap layout, shared world vertex windows,
   lit/decal/emissive surface groups, BO1 light types and a missing intermission camera.
3. `tools/port_map.py` runs the whole stage for you.

## Worked example: port Kino

You need Black Ops 1, Black Ops II and Plutonium installed, and a built `oat-bsp` (run `sh build.sh` in it; it patches
for MSVC 14.42). Say the games are in `C:\Games\BO1` and `C:\Games\BO2`.

    set BO1_DIR=C:\Games\BO1
    set BO2_DIR=C:\Games\BO2
    python converter\tools\port_map.py zombie_theater --install zm_bo1port_test

What it does, in order:

1. dumps the BO1 entities and level script, and the donor's entities (the donor is `zm_nuked`);
2. converts the gameplay entities;
3. dumps the BO1 world with the BSP dumper;
4. lists a stock BO2 zm map's assets;
5. links the BO1 world over it. The output is `work\zombie_theater\build\zone_out\<target>\<target>.ff`;
6. with `--install`, copies the zones into `%LOCALAPPDATA%\Plutonium\storage\t6\mods\zm_bo1port_test`.

Then start BO2 Zombies in Plutonium with that mod. Useful flags: `--props` (include static models, needs ported
models), `--zombies` (let zombies spawn, needs converted AI paths), `--trace` (print each level script step).

If it fails:
- `Missing asset` lines in the log are normal for dependencies. Real problems are lines that say `ERROR`.
- The BO1 map's `.ff` must be in `zone\Common` or `zone\English` of your BO1 install. If it is not found, check
  `BO1_DIR`. A map from a DLC you do not own will not be there.
- Compiling scripts needs `gsc-tool.exe`. Put it in `tools\gsc-tool\` or set `GSC_TOOL` to its path.

## The B2W route

`run_bo1.py` is the full converter. It is built on our fork of Ticass/B2W (`b2w-patch/` holds our changes:
`changes.patch` against `BASE_COMMIT`, plus `new/`). It expects to sit next to the fork's `b2w_bo1` folder, so run it
from there:

    python run_bo1.py --list-maps
    python run_bo1.py zombie_theater
    python run_bo1.py zombie_theater --bo1 "C:\Games\BO1" --bo2 "C:\Games\BO2" --no-install

It finds both games from your Steam libraries. Pass `--bo1` and `--bo2` if it does not. `--list-maps` prints every
BO1 map as JSON. `--no-install` builds without touching your installed Plutonium mod. `--from build-mod` restarts at
a later step and reuses the last build's output. The steps are `stage`, `build-mod`, `compile-scripts`,
`bridge-link` and `audit`.

If it fails, it prints the reason. "`<map>.ff` is not in ...\zone\Common" means that map's DLC is not installed.
Use `--from` to rerun only the step that failed.

## Next steps

- Port BO1 materials and images (a techset remap) and static props (xmodels).
- Convert physics dyn-ents.
- Give the map its own name and globe entry, instead of replacing `zm_nuked`.
- Gameplay scripts.

## Known gaps

- `keyvaluepairs` assets from the stock zone cannot be re-linked by OAT, so they are skipped.
- Zone names that contain `//` are skipped, because the zone-file parser reads `//` as a comment. Those assets still
  come in as dependencies.
- 142 Kino physics props (dyn-ents) are skipped.
