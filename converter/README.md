# BO1 → BO2 map converter (work in progress)

This converts a Black Ops 1 (T5) zombies map's compiled world into a Black Ops 2 (T6) map zone. Kino der Toten (`zombie_theater`) is the map used to build and test it. It is separate from ZM Workshop for now.

## How it works

1. **`oat-bsp/`** is LJW-Dev's OpenAssetTools BSP fork (branch `t6-decompile-and-compile-bsp`). Its Linker already builds BO2 `gfxworld` / `clipmap` / `comworld` / `gameworldmp` / `mapents` from a neutral description of a map: `bsp/map_gfx.glb` and `bsp/map_col.glb`.
2. **New here:** a T5 BSP dumper.
   - Files: `src/ObjWriting/Game/T5/BSP/BSPUnlinkerT5.cpp`, `BSPDumperT5.*`, registered in `ObjWriterT5.cpp`.
   - Run `Unlinker.exe` on a BO1 map's `.ff` and it reads the BO1 world straight from the fastfile (BO1 doesn't have to be running), then writes those two glb files.
   - It handles: BO1 clipmap layout, shared world vertex windows, lit/decal/emissive surface groups, BO1 light types and missing intermission camera.
3. **`tools/port_map.py <bo1_map>`** runs the whole stage:
   - dumps the map;
   - lists a stock BO2 zm map's assets (default `zm_nuked`);
   - links the BO1 world over it into `work/<map>/build/zone_out/<target>/<target>.ff`;
   - with `--install MOD`, copies it into a Plutonium mod.

Rebuild after source changes with `sh build.sh`. It patches for MSVC 14.42 (no `stdcpp23`, no `uz` literals, warnings not errors) and puts compiler temp files on E: because C: is full.

## Status

- **Stage 1 (walk test):** world geometry, collision, brush models and entities, with placeholder (grey) materials and no props.
  - Kino builds as `zm_nuked.ff` in mod `zm_bo1port_test`.
  - It has **not been tested in game yet**.
- **Next:**
  - port BO1 materials and images (techset remap) and static props (xmodels);
  - convert physics dyn-ents;
  - own map name and globe entry instead of replacing `zm_nuked`;
  - gameplay scripts.

## Known gaps

- `keyvaluepairs` from the stock zone can't be re-linked by OAT and is skipped.
- Zone names containing `//` are skipped; the zone-file parser treats `//` as a comment, but those assets come in as dependencies anyway.
- 142 Kino physics props (dyn-ents) are skipped.
