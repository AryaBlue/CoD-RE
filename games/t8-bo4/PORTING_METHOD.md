# Porting a Black Ops 4 map to Black Ops 3: the method

This is the recipe for rebuilding a BO4 (T8) map as a playable BO3 (T7) custom Zombies map with the BO3 Mod Tools.
We worked it out on Blood of the Dead (`zm_escape`, built as `zm_alcatraz_bodfull`). We ran every step end to end at
least once. Steps marked *(unverified)* build fine but we have not confirmed them in game.

It is for personal, offline use. You need your own copies of BO4, BO3 and the BO3 Mod Tools. Nothing extracted from
either game belongs in a public repo. This folder has the method and our code only.

## How to read this

Every scripted step has a command line. The paths in the examples are made up: BO4 in `C:\Games\BO4`, BO3 and the Mod
Tools in `C:\Games\BO3`, work files in `C:\work`. Most scripts keep their paths as constants at the top
(`PATH/TO/...`, or a Steam path). Open the script and set them to your own before you run it. Run scripts from
`games\t8-bo4`.

## 0. What the problem looks like

A BO4 map is not one mesh. It has five parts, and each takes a different route to BO3.

| Part | Where it lives in BO4 | How it gets to BO3 |
|---|---|---|
| World surfaces (walls, floors, terrain) | GfxWorld, with vertices streamed in the `.xpak` | C2M map export, then OBJ, then `XMODEL_EXPORT` chunks placed as `misc_model` |
| Static props (most of what you see) | the collision static-model array in the clipMap: a transform and an AABB, **no name** | rip the models with Greyhound, then match them by bounds to recover names |
| Collision | clipMap (asset 11): brushes and a terrain triangle soup | brushes become `.map` brushes; the soup becomes 2x2 clip mesh patches |
| Entities (spawns, boxes, perks, spawners) | the entity list inside the decompressed zone | parsed offline, then turned into BO3 prefabs and structs by script |
| Navmesh | Havok (AI only) | not ported. cod2map makes a new one, seeded with nav points |

BO3's limits decide most of the choices:
- 131,072 unique brush planes (`MAX_MAP_PLANES`). Brushes use planes. Patch meshes do not.
- 60k vertices and 64 materials per xmodel.
- Collmaps accept brushes only.
- A prop only blocks the player if it has a collmap. `BulletCollisionLOD` only stops bullets.

## 1. What you need

- BO3 Mod Tools (Steam app 455130), BO4 and BO3 installed. Python 3.10 or newer, 64-bit, with numpy, scipy and Pillow.
- **Greyhound** (Scobalula), attached to a running BO4. It rips models and images in BO3 `XMODEL_EXPORT` format.
- **C2M**, with *Export Materials .JSON* ticked, run with the map loaded in BO4. It gives you the world mesh and a
  JSON that maps materials to textures.
- **atian-cod-tools (ACTS, ate47)** for `acts fastfile -d`.
- The scripts in this folder: `tools/` for extraction, `port/` for the build stages.
- **Close BO4, Greyhound and BO3 before you build.** cod2map hangs at its signature step while BO4 or Greyhound runs,
  and deploying fails while BO3 is open.

## 2. Extract (offline, no memory reading)

1. **Get the zone files.** `tools\casc_bo4.py`, `tvfs.py` and `extract_zone.py` read BO4's CASC storage and pull
   `zone\<map>.ff` and the `.xpak` files out byte for byte.

       python -I tools\extract_zone.py

   You get the `.ff` and `.xpak` files in the folder you set as `OUT`.

2. **Decompress.** `tools\decomp_recipe.sh` shows the ACTS call. Leave out `-r bo4`, which forces a module that does
   not work offline. The generic reader does the AES and Oodle steps.

       acts.exe fastfile -d C:\work\zm_escape.ff -o C:\work\dec

   You get `zm_escape.ff.dec`, the linked asset stream (about 487 MB for Blood of the Dead).

3. **Collision brushes.** `tools\clip_t8.py` writes `clip.json` with planes, brush vertices and contents.

       python tools\clip_t8.py C:\work\dec\zm_escape.ff.dec C:\work\clip.json

   The offsets are map specific. Find the inline ClipInfo block (nine records of `{u32 count, pad, u64 ptr}`) and
   the 64-byte brush records for your map. `notes\t8_struct_refs.md` explains how.

4. **Terrain triangle soup.** `port\clip_tris_t8.py` writes the walkable collision triangles (plain float3 vertices
   and global u32 indices).

5. **Static-model records.** First get the AABB of every ripped model:

       python tools\rip_bounds.py C:\work\rip C:\work\rip_bounds.json

   Then run `tools\match_placements.py` or `match_confident.py`, and after those `port\match_arch.py` or
   `match_catalog.py`. The records carry no usable name, so **bounds decide**. A model has the right name when its
   LOD0 AABB, moved by the record's transform, equals the record's AABB to within a few units. The transform is
   `local to world = (invScaledAxis rows x scale^2) transposed`, with `scale = 1 / |row|`. Below about 24 units the
   bounds cannot tell models apart.

6. **Entity list.** `port\entitylist.py` writes `entities.json` (spawns, zones, spawners, boxes, perks, wall-buys, the
   power switch). Script-model hashes resolve through `tools\build_t8_name_dict.py` and `port\t8hash.py` (FNV-1a-64 of
   the rip names).

7. **Materials.** Run C2M's material export. Then `port\resolve_textures.py --write` maps each material's `colorMap`
   to the exported TGA and gives you `<mat>_c.png`. The JSON is a dict keyed by map type. Names that start with `$` are
   engine defaults.

8. **Navmesh.** Skip it. `tools\navmesh_extract.py` reads the Havok tagfile (metres x 39.37), but only its points are
   useful, as nav seeds for cod2map.

If a step fails: a script that stops on an assert is nearly always pointing at the wrong offsets or the wrong
path constant. Check those two first.

## 3. Rebuild the world mesh (shell chunks)

1. **Chunk the mesh.** Cut the C2M OBJ into `XMODEL_EXPORT` chunks of at most 60k vertices and 64 materials. Give
   each map's chunks a **unique prefix**. gdtdb scans every GDT, and duplicate names stop the build.
2. **Fix the winding first.** BO3 front faces wind the opposite way to the vertex normal. Check your shell against a
   Greyhound prop that renders correctly:

       python port\winding_check.py "C:\work\shell\*.xmodel_export"
       python port\flip_winding.py C:\work\shell\chunk_000.xmodel_export

   Shells wound the wrong way show up as "invisible floors, missing walls", because BO3 culls back faces.
3. **Z-fighting.** BO4 stacks up to five coplanar surfaces from different chunks (floor, puddle, grime, blend).
   `port\zfix_global.py` groups faces across chunks by plane and 256-unit cell, keeps the dominant material and lifts
   the overlays by `rank x 0.4` units.
4. **Texture fixes** (`port\shell_texfix.py`):
   - BO4 keeps transparency in the **revealMap**, not in the colour alpha. Overlay materials need the revealMap copied
     in as alpha.
   - Flow maps and puddles get flat colours.
   - Decals that use a normal map as their colour need stripping or recolouring (`port\strip_mats.py`).
5. **Strip engine-only surfaces.** Remove `shadowcaster` (renders cyan), `caulk_shadow_primary` and
   `infinite_blackness` (black voids). Do not strip by "decal" in the name. Decal-named materials are about 27% of all
   faces and are often the main floor.
6. **Skybox and distant chunks.** Keep chunks that reach +-80k out of the playable build. The playable core of Blood of
   the Dead was about +-15k.
7. **Import:**

       python port\import_rip.py C:\work\shell bod_shell --models

   **This overwrites `source_data\<tag>.gdt` with only the models you pass.** Always pass the full set, and back the
   GDT up first. Then place the chunks as `misc_model` at `0 0 0`.

## 4. Collision

1. **Brushes.** `port\clip_brushes.py` writes the `clip.json` brushes into the `.map`.
   - Keep SOLID, PLAYERCLIP and MONSTERCLIP.
   - Drop local-space brush entities (doors and movers centred at the origin).
   - Drop any brush whose smallest extent is over 4096. A huge solid cube once buried the navmesh.
   - Brushes with more than 45 sides trip a Radiant assert, and then lighting never bakes.
2. **Triangle soup.** Write it as 2x2 collapsed **clip mesh patches** with `make_shell_map.py --terrain`. Patches use no
   planes, and 200k or more of them have linked fine. Keep the walkable triangles (`|nz| >= 0.5`).
3. **Check the plane budget before every build:**

       python tools\count_map_planes.py C:\work\map_source\zm_alcatraz_bodfull.map

   Approximate the plane table as unique planes x 2. It must stay under 131,072. If you are over, run
   `port\decimate_clip.py` (it merges slivers into boxes), crop to the playable box, or both:

       python port\decimate_clip.py C:\work\clip.json C:\work\clip_small.json --target-planes 120000

   You can patch the cap in cod2map, but then the map only loads on a patched engine. See `notes\cod2map_caps.md`.
4. **Nav seeds.** cod2map keeps only the region it can reach from its seeds. Seed it with nav points or entity
   positions (`make_shell_map --ents`).

## 5. Props

1. **Import the rip.** Bring the matched models in with `import_rip.py ... --models-from list.txt`. The list file gets
   around the Windows 32k command-line limit. Leave out models whose names collide with stock BO3 assets.
2. **Place them.** Write them as `misc_model` with origin, angles and `modelscale`. Swap any donor or shell props for
   the matched set with `port\swap_props.py`.
3. **Check for wrong-game props.** The catalogue match can pick Blackout or MP models whose bounds happen to fit.
   - Models whose materials are not in the map's C2M material JSON are suspects. Do not rely on this alone, because
     the JSON is incomplete.
   - Drop the clearly foreign ones (`p8_wz_*`, `*_mp_*`) with `port\drop_models.py`.
4. **Player collision.**
   - `port\make_collmaps.py` voxelises the LOD0 of solid categories (doors, gates, fences, railings, stairs, beds,
     tables) at 16 units. Then it greedily merges the voxels into at most 8 box brushes.
   - It writes `share\raw\collmaps\<model>.map`, sets the GDT `CollisionMap`, and adds `use_collmap` to each placement.
   - Collmap brushes also use plane budget, so keep the boxes coarse. Never delete the stock collmaps in that folder.
5. **Script models.** `port\place_script_models.py` places the entity-list `script_model`s whose hash resolves to a
   ripped name.
6. **Unripped models.** Some records match nothing you ripped (Blood of the Dead had 2,265; list them as coordinates
   and sizes). Their collision exists but nothing is drawn, so they are invisible solid ground. Section 6 fills them.

## 6. Fill "solid but invisible" (stairs, catwalks, rubble)

Wherever BO4 collision has no visible surface, add a skin and texture it from the nearest real surface.

- `port\invis_floors.py`: walkable clip patches with no shell or prop face over them.
- `port\gap_skin.py`: clip inside the AABBs of unripped records.
- `port\brush_skin.py`: faces of all-`clip` brushes. Stairs, rubble and catwalk floors are mostly brushes, so this is
  the big one. It is vectorised, with a 64-unit grid, and looks at the shell chunks only.
- `port\make_fill.py` merges the three. It takes the material from the nearest shell face of the same orientation
  (cKDTree, z weighted x3) and writes double-sided chunks of 20k triangles. Then run `make_fill.py --place`.

When a pass checks what is already covered, leave the previous fill chunks out of the check. Otherwise the old fill
hides the gaps it was covering.

## 7. Special surfaces

- **Lava.** BO4 lava is an emissive map with a black colour, moved by a flow map. Run `port\lava_fx.py png`, then
  `lava_fx.py gdt` after every shell import. Colour is the emissive image, the material is `lit_emissive_scroll`,
  `scaleRGB` is 3, and scroll comes from `gUVScroll02/03_Angle`.
- **Sea.** BO4's ocean is a water system, not geometry. `port\add_water.py` lays 4096-unit `t7_water_sector_flow` mesh
  patches at sea level *(unverified)*.
- **Atmosphere.** Fog and visionset values from BO4 cannot be recovered offline, so set them by eye
  (`port\make_atmos.py`). Start from a stock map's fog block. Stock maps use atmospheric fog with world fog off, and
  world fog alone renders nothing. If the whole scene turns red, the atmospheric extinction and inscatter values are
  subtracting the fog colour. Turn that part off.

## 8. Gameplay

Run these in this order on every rebuild. Each script rewrites the output of the one before.

1. `add_zones.py`: rebuilds the `.map` from the prop base and adds zone volumes. **BO3 kills any player outside an
   enabled zone**, so the zones must tile the whole playable box. Blood of the Dead used a 512 x 512 x 128 grid of
   cells. Each cell went to its nearest spawner anchor, vertical runs were merged, and adjacencies were set to always
   on. Zombie spawn locations go on nav seeds. The player start comes from the map's `initial_spawn_points`. **BO3
   Zombies ignores `info_player_start`.**
2. `add_water.py`
3. `add_gameplay.py`: magic boxes, Pack-a-Punch, wall-buys (BO3 wall-buy yaw runs *along* the wall), perks, GobbleGum
   and the power switch. They are stock prefabs placed at the BO4 entity positions, with a T8 to T7 weapon mapping.
4. `add_doors.py`: buyable debris doors, sized by raycasting the shell (`door_probe.py`).
5. `add_tour.py --off`. With it on you get god mode and a teleport tour for automated screenshots.
6. `add_poshud.py`: an on-screen X Y Z yaw readout, so testers can report exact spots.

For spawn points, find a clear standing column with `port\spawn_face_finder.py` and add them with
`port\add_spawns.py`. A vertex-count check misses big wall faces.

## 9. Build and deploy

    powershell -ExecutionPolicy Bypass -File port\build_usermap.ps1 -Map zm_alcatraz_bodfull

It runs, in order: gdtdb, the cod2map compile (about 60 seconds), light, link (about 6 minutes), then deploy to the game's `usermaps` folder.

- The `$R` path at the top of `build_usermap.ps1` points at the Mod Tools folder. Set it to yours first.
- gdtdb exiting with 1 on duplicate stock-named props is expected. The script tolerates it.
- For a map as big as Blood of the Dead use `-CompileArgs` with `-umbraBackfaceLimit 100 -umbraSmallestOccluder 512`
  (the script adds them by itself for maps named `zm_alcatraz_bod*`). A value of `100000` crashed UmbraConvert.
- If you only changed script or the zone, add `-SkipCompile -SkipLight`.
- Load the map from **Zombies, Custom Games**. Launch parameters (`+devmap`, `+set`) can leave the retail game stuck on
  a continue prompt.

The full order of stages:

    [edit prop base: make_collmaps, place_script_models, drop_models, make_fill --place]
    add_zones, add_water, add_gameplay, add_doors, add_tour --off, add_poshud, build

After a shell change: `make_fill`, then `import_rip <shell> <tag> --models`, then `lava_fx gdt`, then
`make_fill --place`, then the order above.

## 10. Testing

- Testers report with the position HUD: "stairs missing at X Y Z". Use the coordinates to probe the data (shell faces,
  clip brushes, gap records near that point) before you guess.
- To fix a load crash, build **subsets of real geometry** and drop chunks one at a time. An empty map crashes on load
  whatever its size, so it tells you nothing.
- Check that a "crash" really is one. Steam's `content_log.txt` shows whether the game started at all.

## 11. Gotchas (each one cost us at least one build)

| Symptom | Cause | Fix |
|---|---|---|
| Invisible floors, missing walls | shell wound backwards | `flip_winding.py`; check against a known-good prop |
| Flicker, floor patches | coplanar overlays from several chunks | `zfix_global.py` |
| Cyan walls, black voids | `shadowcaster` or `infinite_blackness` faces | strip those materials only |
| Blue floor patches | decal that uses a normal map as colour | strip or recolour it |
| Spawn inside a wall | no `initial_spawn_points`, so template spawns get shifted | add explicit ones |
| Player dies for no reason | outside every enabled zone | tile zones over the whole box |
| "Cannot have patch terrain in collision maps" | patches in a collmap | collmaps must be brushes |
| `MAX_MAP_PLANES` | too many brush planes (collmaps count too) | decimate, crop, use coarser collmaps |
| Props vanish past about 500 units | the import template carried LOD distances | zero all LOD distances |
| GDT lost models | `import_rip` overwrites the GDT | pass the full list every time; back it up |
| "Duplicate xmodel asset" | two maps share chunk names, or a name matches a stock asset | unique prefix; exclude stock names |
| Images "not a valid file" | absolute path of 253 characters or more | copy the images to a shorter path |
| Strings mangled in generated files | a shell heredoc ate `\n`, `\t` and `\r` | write scripts with a file editor, not a heredoc |

## 12. Where Blood of the Dead stands

Done and walked in game:
- the Citadel core: textured, lit and walkable, with zombies spawning across 45 zones;
- boxes, wall-buys, perks, Pack-a-Punch and the power switch;
- the real Blood of the Dead spawn;
- glowing, scrolling lava;
- Blood of the Dead props, with collision on doors, rails and stairs.

Built but not yet confirmed in game: the brush-skin fill (stairs, catwalks, rubble) and the sea.

Still open:
- Models with no static placement (cryo chambers, location signs, some warden-house trim) must be placed by hand.
- The bridge gauntlet and the skybox exterior are too big for one map at true scale.
- Lighting is set by eye.
- Doors beyond the three debris barriers.

See [CREDITS.md](../../CREDITS.md) for whose research and tools this stands on.
