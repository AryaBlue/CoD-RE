# Porting a Black Ops 4 map to Black Ops 3 — the method

A repeatable recipe for taking a BO4 (T8) map and rebuilding it as a playable BO3 (T7) custom Zombies map with the BO3 Mod Tools. It was worked out on **Blood of the Dead** (`zm_escape`, built as `zm_alcatraz_bodfull`), so every step below has been run end to end at least once. Steps marked *(unverified)* built cleanly but have not been confirmed in game yet.

For personal, offline use only. You need your own copies of BO4, BO3 and the BO3 Mod Tools. Nothing extracted from either game belongs in a public repo; this folder holds the method and our code only.

---

## 0. The shape of the problem

A BO4 map is not one mesh. It splits into five parts, and each part takes a different route:

| Part | Where it lives in BO4 | How it gets to BO3 |
|---|---|---|
| World surfaces (walls, floors, terrain) | GfxWorld, verts streamed in the `.xpak` | C2M map export → OBJ → `XMODEL_EXPORT` chunks placed as `misc_model` |
| Static props (most of the visible map) | collision static-model array in the clipMap (transform + AABB, **no name**) | Greyhound rip of the models + bounds-matching to recover names |
| Collision | clipMap (asset 11): brushes + a terrain tri-soup | brushes → `.map` brushes; tri-soup → 2×2 clip mesh patches |
| Entities (spawns, boxes, perks, spawners) | entity list inside the decompressed zone | parsed offline → BO3 prefabs/structs by script |
| Navmesh | Havok (AI only) | **not ported** — cod2map regenerates it, seeded with nav points |

BO3's limits drive most decisions:
- **131,072 unique brush planes** (`MAX_MAP_PLANES`). Brushes spend planes; patch meshes don't.
- **60k verts / 64 materials** per xmodel.
- Collmaps only accept brushes.
- Player collision on a prop needs a collmap; `BulletCollisionLOD` only stops bullets.

---

## 1. Prerequisites

- **BO3 Mod Tools** (Steam app 455130), BO4 installed, BO3 installed. Python 3.10+ 64-bit, with numpy, scipy and Pillow.
- **Greyhound** (Scobalula) attached to running BO4, to rip models + images in BO3 `XMODEL_EXPORT` format.
- **C2M** with *Export Materials .JSON* ticked, run with the map loaded in BO4. It gives the world mesh and a material → texture JSON.
- **atian-cod-tools (ACTS, ate47)** for `acts fastfile -d <map>.ff -o <dir>`. Run it **without** `-r bo4`, which forces an unusable module; the generic reader does the AES + Oodle step offline.
- The tools in this folder: `tools/` (extraction) and `port/` (build stages). Every script has its paths as constants at the top. Set them to your own install.
- **Close BO4, Greyhound and BO3 before building.** cod2map hangs at the signature step while BO4 or Greyhound are running, and deploying fails while BO3 is open.

---

## 2. Extract (offline, no game memory reading)

1. **Get the zone files:** `tools/casc_bo4.py` + `tvfs.py` + `extract_zone.py` read BO4's CASC storage and pull `zone\<map>.ff` / `.xpak` byte-exact.
2. **Decompress:** `tools/decomp_recipe.sh` (ACTS `fastfile -d`) → `<map>.ff.dec`, the linked asset stream.
3. **Collision brushes:** `tools/clip_t8.py` → `clip.json` (planes, brush verts, contents). The offsets are map-specific: find the inline ClipInfo block (9× `{u32 count, pad, u64 ptr}`) and the 64-byte brush records. See `notes/t8_struct_refs.md`.
4. **Terrain tri-soup:** `port/clip_tris_t8.py` → walkable collision tris (plain float3 verts + global u32 indices).
5. **Static-model records:** `tools/rip_bounds.py` (AABBs of every ripped model), then `tools/match_placements.py` / `match_confident.py`, then `port/match_arch.py` / `match_catalog.py`. Records carry no usable name, so **bounds are the oracle**. A model is the right name when its LOD0 AABB, transformed by the record, equals the record's AABB within a few units. The transform is `local→world = (invScaledAxis rows × scale²)ᵀ` with `scale = 1/|row|`. Under ~24u, bounds can't tell models apart.
6. **Entity list:** `port/entitylist.py` → `entities.json` (spawns, zones, spawners, boxes, perks, wall-buys, power switch). Script-model hashes resolve through `tools/build_t8_name_dict.py` plus `port/t8hash.py` (FNV-1a-64 of the rip names).
7. **Materials:** run C2M's material export, then `port/resolve_textures.py` maps each material's `colorMap` to the exported TGA, giving `<mat>_c.png`. The JSON is a dict keyed by map type; `$`-prefixed names are engine defaults.
8. **Navmesh:** skip. `tools/navmesh_extract.py` reads the Havok tagfile (metres × 39.37), but only its points are useful, as cod2map nav seeds.

---

## 3. Rebuild the world mesh (shell chunks)

1. **Chunk the mesh:** C2M OBJ → `XMODEL_EXPORT` chunks of ≤60k verts and ≤64 materials. Give each map's chunks a **unique prefix**, because gdtdb scans every GDT and duplicate names stop the build.
2. **Fix the winding first:** BO3 front faces wind *opposite* the vertex normal. Check the shell against a Greyhound prop that renders correctly (`port/winding_check.py`). If they disagree, run `port/flip_winding.py`. Shells wound the wrong way come out as "invisible floors, missing walls" because BO3 back-face culls them.
3. **Z-fighting:** BO4 stacks up to 5 coplanar surfaces from different chunks (floor + puddle + grime + blend). `port/zfix_global.py` groups faces across chunks by plane and 256u cell, keeps the dominant material and lifts overlays by `rank × 0.4u`.
4. **Texture fixes** (`port/shell_texfix.py`):
   - BO4 keeps transparency in the **revealMap**, not colour alpha, so overlay materials need the revealMap copied in as alpha.
   - Flow maps and puddles get flat colours.
   - Decals that use a normal map as their colour need stripping or recolouring (`port/strip_mats.py`).
5. **Strip engine-only surfaces:** remove `shadowcaster` (renders cyan), `caulk_shadow_primary` and `infinite_blackness` (black voids). Don't strip by "decal" in the name: decal-named materials are about 27% of all faces and are often the primary floor.
6. **Skybox/distant chunks:** keep chunks that reach ±80k out of the playable build. The playable core of BoD was about ±15k.
7. **Import:** `port/import_rip.py <chunks_dir> <tag> --models`. **It overwrites `source_data\<tag>.gdt` with only the models you pass**, so always pass the full set and back the GDT up first. Place the chunks as `misc_model` at `0 0 0`.

---

## 4. Collision

1. **Brushes:** `port/clip_brushes.py` writes `clip.json` brushes into the `.map`.
   - Keep SOLID / PLAYERCLIP / MONSTERCLIP.
   - Drop the local-space brush entities (doors and movers centred at the origin).
   - Drop any brush whose smallest extent is over 4096 (a huge solid cube buried the navmesh).
   - Brushes over 45 sides trip a Radiant assert, so lighting never bakes.
2. **Tri-soup:** emit it as 2×2 collapsed **clip mesh patches** (`make_shell_map.py --terrain`). Patches don't spend planes, and 200k+ of them have linked fine. Keep walkable tris (`|nz| ≥ 0.5`).
3. **Budget gate:** `port/count_map_planes.py` / `plane_count.py` before every build. Approximate the table as unique × 2; it must stay under 131,072. Over budget, use `port/decimate_clip.py` (merging slivers into boxes), crop to the playable box, or both. The cap itself can be patched in cod2map, but the result then only loads on a patched engine; see `notes/cod2map_caps.md`.
4. **Nav seeds:** cod2map keeps only the region it can reach from its seeds. Seed it with BoD nav points or entity positions (`make_shell_map --ents`).

---

## 5. Props

1. **Import the rip:** bring the matched models in (`import_rip.py ... --models-from list.txt`, which gets around the Windows 32k command-line limit). Exclude models whose names collide with stock BO3 assets.
2. **Placement:** write them as `misc_model` with origin, angles and `modelscale`. Swap any donor or shell props for the matched set (`port/swap_props.py`).
3. **Wrong-game props:** the catalogue match can pick Blackout or MP models whose bounds happen to fit. Check the results:
   - Models whose materials aren't in the map's C2M material JSON are suspects. Don't use this test alone, because the JSON is incomplete.
   - Drop the clearly foreign ones (`p8_wz_*`, `*_mp_*`) with `port/drop_models.py`.
4. **Player collision:**
   - `port/make_collmaps.py` voxelises the LOD0 of solid categories (doors, gates, fences, railings, stairs, beds, tables) at 16u, then greedily merges the voxels into at most 8 box brushes.
   - It writes `share\raw\collmaps\<model>.map`, sets the GDT `CollisionMap`, and adds `use_collmap` to each placement.
   - Collmap brushes spend plane budget too, so keep the boxes coarse. Never delete the stock collmaps in that folder.
5. **Script models:** `port/place_script_models.py` places entity-list `script_model`s whose hash resolves to a ripped name.
6. **Unripped models:** some records match nothing that was ripped (BoD had 2,265; list them as coords + sizes). Their collision exists but nothing is drawn there, so they become invisible solid ground; section 6 fills them.

---

## 6. Fill "solid but invisible" (stairs, catwalks, rubble slopes)

Wherever BO4 collision has no visible surface, add a skin textured from the nearest real surface:
- `port/invis_floors.py`: walkable clip patches with no shell or prop face over them.
- `port/gap_skin.py`: clip inside unripped-record AABBs.
- `port/brush_skin.py`: faces of all-`clip` brushes. Stairs, rubble and catwalk floors are mostly brushes, so this is the big one. It's vectorised, using a 64u grid and the shell chunks only.
- `port/make_fill.py` merges the three, takes the material from the nearest shell face of the same orientation (cKDTree, z weighted ×3), and writes double-sided chunks of 20k tris. Then `make_fill.py --place`.

When a pass checks what is already covered, leave the previous fill chunks out of the check. Otherwise the old fill hides the gaps it was covering.

---

## 7. Special surfaces

- **Lava:** BO4 lava is an emissive map with a black colour, moved by a flow map. `port/lava_fx.py png`, then `gdt` after every shell import: colour = the emissive image, `lit_emissive_scroll`, `scaleRGB 3`, scroll via `gUVScroll02/03_Angle`.
- **Sea:** BO4's ocean is a water system, not geometry. `port/add_water.py` lays 4096u `t7_water_sector_flow` mesh patches at sea level *(unverified)*.
- **Atmosphere:** BO4's fog and visionset values aren't recoverable offline, so set them by eye (`port/make_atmos.py`). Start from a stock map's fog block: stock maps use atmospheric fog with world fog off, and world fog alone renders nothing. If the whole scene turns red, the atmospheric extinction/inscatter values are subtracting the fog colour; turn that part off.

---

## 8. Gameplay

Run these in this order on every rebuild. Each script rewrites the output of the previous one.

1. `add_zones.py`: rebuilds the `.map` from the prop base and adds zone volumes. **BO3 kills any player outside an enabled zone**, so zones must tile the whole playable box. BoD used a 512×512×128 grid of cells, each assigned to its nearest spawner anchor, with vertical runs merged and adjacencies set to always-on. Zombie spawn locations go on nav seeds. The start comes from the map's `initial_spawn_points`; **BO3 Zombies ignores `info_player_start`**.
2. `add_water.py`
3. `add_gameplay.py`: magic boxes, Pack-a-Punch, wall-buys (BO3 wall-buy yaw runs *along* the wall), perks, GobbleGum and the power switch, all as stock prefabs at BO4 entity positions with T8 → T7 weapon mapping.
4. `add_doors.py`: buyable debris doors, sized by raycasting the shell (`door_probe.py`).
5. `add_tour.py --off` (with it on: god mode + a teleport tour for automated screenshots).
6. `add_poshud.py`: an on-screen X Y Z yaw readout so testers can report exact spots.

Spawn points: find a clear standing column with `port/spawn_face_finder.py` and add them with `port/add_spawns.py`. A vertex-count check misses big wall faces.

---

## 9. Build and deploy

```
powershell -ExecutionPolicy Bypass -File build_usermap.ps1 -Map <map>
```
- The build runs gdtdb → cod2map compile (~60s) → light → link (~6 min) → deploy to the game's `usermaps`.
- gdtdb exiting 1 on duplicate stock-named props is tolerated.
- For BoD-sized maps use `-umbraBackfaceLimit 100 -umbraSmallestOccluder 512`; `100000` crashed UmbraConvert.
- If a change only touches script or the zone, add `-SkipCompile -SkipLight`.
- Load through **Zombies → Custom Games**. Launch parameters (`+devmap`, `+set`) can leave retail stuck on a continue prompt.

Full stage order:
```
[edit prop base: make_collmaps → place_script_models → drop_models → make_fill --place]
→ add_zones → add_water → add_gameplay → add_doors → add_tour --off → add_poshud → build
```
After a shell change: `make_fill` → `import_rip <shell> <tag> --models` → `lava_fx gdt` → `make_fill --place` → the order above.

---

## 10. Testing

- Testers report with the position HUD: "stairs missing at X Y Z". Use the coordinates to probe the data (shell faces, clip brushes, gap records near the point) before guessing.
- Fix a load crash by building **subsets of real geometry** (dropping chunks one at a time). An empty map crashes on load regardless of its size, so it tells you nothing.
- Check that a "crash" is really a crash: Steam's `content_log.txt` shows whether the game actually started.

---

## 11. Gotchas (each one cost at least one build)

| Symptom | Cause | Fix |
|---|---|---|
| Invisible floors, missing walls | shell wound backwards | `flip_winding.py`; check against a known-good prop |
| Flicker / floor patches | coplanar overlays from several chunks | `zfix_global.py` |
| Cyan walls / black voids | `shadowcaster` / `infinite_blackness` faces | strip those materials only |
| Blue floor patches | decal using a normal map as colour | strip or recolour |
| Spawn inside a wall | no `initial_spawn_points`, so template spawns get shifted | add explicit ones |
| Player dies for no reason | outside every enabled zone | tile zones over the whole box |
| "Cannot have patch terrain in collision maps" | patches in a collmap | collmaps must be brushes |
| `MAX_MAP_PLANES` | too many brush planes (collmaps count too) | decimate, crop, coarser collmaps |
| Props vanish past ~500u | import template carried LOD distances | zero all LOD distances |
| GDT lost models | `import_rip` overwrites the GDT | full list every time; back up |
| "Duplicate xmodel asset" | two maps share chunk names, or a stock name | unique prefix; exclude stock names |
| Images "not a valid file" | absolute path ≥253 chars | short-copy the images |
| Strings mangled in generated files | shell heredoc ate `\n`/`\t`/`\r` | write scripts with a file editor, not a heredoc |

---

## 12. Where Blood of the Dead stands

Done and walked in game:
- Citadel core: textured, lit and walkable, with zombies spawning across 45 zones.
- Boxes, wall-buys, perks, Pack-a-Punch, power switch.
- Real BoD spawn.
- Glowing, scrolling lava.
- BoD props with collision on doors, rails and stairs.

Built but not yet confirmed in game: the brush-skin fill (stairs, catwalks, rubble), the sea.

Open:
- Models with no static placement (cryo chambers, location signs, some warden-house trim) need placing by hand.
- The bridge gauntlet and the skybox exterior exceed one map at true scale.
- Lighting is set by eye.
- Doors beyond the 3 debris barriers.

See [CREDITS.md](../../CREDITS.md) for whose research and tools this stands on.
