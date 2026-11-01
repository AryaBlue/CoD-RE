# Breakable map glass (T5 / T6)

Breakable window glass in BO1 and BO2 maps: what the zones hold, what E115 already exports, and what an export
would need so the runtime can break panes. Researched 2026-10-29.

## Conventions

- **Tags:** [V] read in zone data or exports; [I] inferred; [U] unknown.
- **Method:** a scratch OAT dumper read the `glasses` asset and the GfxWorld brush models. The exports were read from
  `assets/local/reforged`.

## Which maps have glass [V]

| game | maps with glass panes |
|---|---|
| T5 zombies | `zombie_pentagon` (Five): 46 panes. `zombietron`: 5. No other T5 zm map. |
| T5 mp | array 20, cairo 24, crisis 19, duga 16, firingrange 5, mountain 67, nuked 62, radiation 17, russianbase 20, villa 74 |
| T6 zombies | `zm_nuked`: 1 pane with **no surfaces**, so there is nothing to see or break. transit, buried, highrise, prison, tomb and transit_dr have none. |
| T6 mp | e.g. raid 43, nuketown_2020 2 |
| T4 | none (no `glasses` asset in WaW) |

So for zombies, glass matters on **Five**, and that's BO1, not BO2. The T6 callback found in the scripts
(`codecallback_glasssmash`) has nothing to fire on in any stock T6 zm map except nuked's empty pane.

## BO2 zombies windows: script model swaps, not glass [V]

- **TranZit:**
  - 13 `script_model`s with `targetname "transit_glass"`: 10 `p6_zm_window_dest_glass_small` and 3 `_big`
    (`script_noteworthy` `glass_small`/`glass_big`).
  - `zm_transit_utility.gsc` `transit_breakable_glass` sets each pane's health to 99999 and `setcandamage(1)`.
  - On the **first player damage** it plays `level._effect["glass_impact"]`
    (`maps/zombie/fx_zmb_tranzit_window_dest_lg`) at the origin, facing forward. 0.1 s later it calls
    `setmodel(<model> + "_broken")` and plays `fly_glass_break`.
  - Later hits do nothing. With more than 2 splitscreen players the panes are deleted.
  - The 120 `*_broken` models elsewhere on the map are static, already broken.
  - **Export:** the swap list (`asset/ScriptModelSwaps.h`) includes `<model>_broken`, so both panes get a swap glb.
- **Buried:** every window (manor, church, candy shop, factory, ...) is a static world model, with no entity and no
  script. They don't break in stock BO2 either, so they're correct as they are.
- **Barriers:** the zbarrier pieces on both maps are boards and the box, with no glass. `showzbarrierpiece` and
  `setzbarrierpiecestate` only open and close boards.
- **Legacy path:** `_zm_blockers.gsc` has an old glass barricade path (`repair_board` with an `unbroken_section`
  whose `script_noteworthy` is `"glass"`). No BO2 zm map uses it. BO1's Five has 132 of them.

## What the zone holds [V]

- **One `glasses` asset per map:**
  - A list of `Glass` entries, one per pane.
  - Runtime pool sizes (max shards, groups, physics pieces, verts, indices). Those are engine budgets, not data
    anyone needs.
- **Each `Glass`:**
  - `glassDef`: shared per glass type.
  - `index`: matches the order in the map's `glass` entities.
  - `brushModel`: the pane's `*N` submodel.
  - `origin`, `angles` and the world box `absmin`/`absmax`.
  - `isPlanar`, plus an **outline**: `numOutlineVerts` 2D points in a plane frame (`outlineAxis[3]`, `outlineOrigin`).
  - `uvScale` and `thickness`.
  - T6 only: `numCellIndices`/`cellIndices[6]` (the vis cells it's in) and `binormalSign`.
- **Each `GlassDef`:**
  - `maxHealth`, `thickness`.
  - Shard sizes `min`/`maxShardSize`, `shardLifeProbablility`, `maxShards`.
  - Three materials: pristine, cracked and shard.
  - Three sound aliases: crack, shatter, auto-shatter.
  - Two effects: crack and shatter. On the maps read, crack is empty and shatter is the window-edge effect.
- **Examples:**
  - Five: all 46 panes are planar 4-point rectangles on one def, health 120.
  - Raid: 43 panes, 31 planar. The non-planar ones still carry 6-point outlines.
- **Pristine geometry:**
  - It lives in the **GfxWorld brush model** `models[brushModel]`, as ordinary surfaces in the pane's local space.
    Raid's pane 0 is `*93`: 2 surfaces of `glass_clear_iw`.
  - nuked's pane has 0 surfaces.

## What E115 already exports [V]

- **Drawn:**
  - Every pane's `*N` brush model is a node in `world.glb`, drawn as pristine glass.
  - Checked on Five (46/46) and Raid (43/43).
- **Solid:**
  - The same `*N` is in `col.glb`, so panes block movement and bullets today.
  - Checked on Five (46/46) and Raid (43/43).
- **Entities:** `world.ents` has one `"classname" "glass"` entity per pane, with `model "*N"`, `origin`, and
  `type` = the GlassDef name.

So a pane can already be found, hidden and made non-solid by its `*N`. What's missing is the def data, the
crack/shatter assets, and the outline for the shards.

## What an export needs

1. **`glass.json` per map** (zonedump `--glass`, a new optional world job for T5 and T6):
   - `panes`: one per `Glass`, with `model` ("*N"), `def`, `origin`, `absmin`/`absmax`, `planar`, `outline`
     (2D points), `axis` (3 vec3), `outlineOrigin`, `uvScale`, `thickness`.
   - `defs`: per GlassDef, with `maxHealth`, `thickness`, `shardSize` [min, max], `shardLife`, `maxShards`, the three
     material names, the three sound aliases and the two effect names.
2. **The cracked and shard materials as textures:** they are usually not drawn anywhere else in the world.
   - Export them like the script-model materials: colour maps in the map's texture set, keyed by material name.
   - The pristine material is already in `world.glb`.
3. **The effects:** `destructibles/fx_dest_window_glass_edge` through the existing fx export. It is not in Five's
   export yet [V].
4. **The sounds:** nothing to do. `dst_generic_glass_small`, `_med` and `_large` are already in Five's `sounds.json`
   [V].

## What the runtime does with it 

The stock behaviour is from the defs and the script callback. The exact damage model is [U].

1. **Damage:** bullets, melee and explosions that hit a pane's `*N` collision subtract from its health
   (`maxHealth`, 120 on the stock defs).
2. **Crack** [I]: below some health threshold, or on the first hit, swap to the cracked material and play crack fx and
   sound. Neither threshold is in the data [U].
3. **Shatter at 0 health:**
   - Hide the `*N` world node and turn off its collision.
   - Play the shatter fx at the hit point and the shatter sound.
   - Spawn shards over the `outline` polygon with the shard material, sized `shardSize`. Each shard falls with
     probability `shardLife` [I].
   - Fire the script callback: T6 `codecallback_glasssmash`.
4. **Reset per match:** panes are restored when the map reloads.

## Still to check

- The crack threshold and how damage scales by weapon [U]. This needs the engine (T5/T6 exe), as it's not in the zones.
- T5's script callback name (T6's is `codecallback_glasssmash`).
