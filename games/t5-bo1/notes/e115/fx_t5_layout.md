# FX: T5 (BO1) PC layout against T4

The `FxEffectDef` / `FxElemDef` layouts that `tools/zonedump/ExportFx.cpp` reads, T5 next to T4. It's for the T5 path
in the fx export, so Kino and the other BO1 maps get effects.

Tags:
- **[V]**: read from OAT's headers (`src/Common/Game/T4/T4_Assets.h`, `T5/T5_Assets.h` in the vendored
  OpenAssetTools) and OAT's zone-load rules (`src/ZoneCode/Game/T5/XAssets/FxEffectDef.txt`). Offsets are for the
  32-bit build; `ExportFx.cpp` static_asserts the sizes and key offsets, so a header change breaks the build.
- **[M]**: measured by exporting every effect of the Kino zone set, `zombie_theater.ff` + `code_post_gfx`, `common`,
  `common_zombie`, `English/en_zombie_theater.ff`: 338 effects, 2692 elems, 198 images, 0 missing.
- **[I]**: inferred.

## Sizes [V]

| struct | T4 | T5 |
|---|---|---|
| `FxEffectDef` | 0x24 (36) | 0x3C (60) |
| `FxElemDef` | 0x100 (256) | 0x124 (292) |
| `FxElemAtlas` | 8 | 8 |
| `FxElemVisualState`, `FxElemVelStateSample`, `FxSpawnDef`, ranges | same | same |
| `FxTrailDef` / `FxTrailVertex` | same | same |
| `FxElemMarkVisuals` (2 materials) | same | same |
| `FxImpactEntry` (31 nonflesh + 4 flesh) | same | same |

## `FxEffectDef` [V]

| field | T4 | T5 | note |
|---|---|---|---|
| `name` | 0x00 | 0x00 | |
| `flags` | 0x04 `int` | 0x04 `char` | |
| `efPriority` | 0x1C `char` | 0x05 `char` | moved up next to flags |
| `reserved[2]` | - | 0x06 | 0 on every Kino effect [M] |
| `totalSize` | 0x08 | 0x08 | |
| `msecLoopingLife` | 0x0C | 0x0C | |
| `elemDefCountLooping` / `OneShot` / `Emission` | 0x10 / 0x14 / 0x18 | same | |
| `elemDefs` | 0x20 | 0x1C | |
| `boundingBoxDim[3]` | - | 0x20 | |
| `boundingSphere[4]` | - | 0x2C | |

- **The bounds are all zero** on the Kino effects checked [M]. [I] They're filled at runtime, or only by a tool the
  shipped zones didn't run, so a port has to compute its own.
- `efPriority` is spread over 0-255 (255 on 108 effects, 65 on 68, 0 on 49) [M].

## `FxElemDef` [V]

Fields up to `initialRotation` sit at the same offsets. T5 inserts `rotationAxis`, which shifts everything after it
by 4. `effectAttached` shifts the tail by another 4, and T5 adds 0x24 bytes at the end.

| field | T4 | T5 |
|---|---|---|
| `flags` … `initialRotation` | 0x000-0x097 | 0x000-0x097 |
| `rotationAxis` (`uint`) | - | 0x098 |
| `gravity` | 0x098 | 0x09C |
| `reflectionFactor` | 0x0A0 | 0x0A4 |
| `atlas` | 0x0A8 | 0x0AC |
| `windInfluence` | 0x0B0 | 0x0B4 |
| `elemType` / `visualCount` / `velIntervalCount` / `visStateIntervalCount` | 0x0B4-0x0B7 | 0x0B8-0x0BB |
| `velSamples` / `visSamples` / `visuals` | 0x0B8 / 0x0BC / 0x0C0 | 0x0BC / 0x0C0 / 0x0C4 |
| `collMins` / `collMaxs` | 0x0C4 / 0x0D0 | 0x0C8 / 0x0D4 |
| `effectOnImpact` / `OnDeath` / `Emitted` | 0x0DC / 0x0E0 / 0x0E4 | 0x0E0 / 0x0E4 / 0x0E8 |
| `emitDist` / `emitDistVariance` | 0x0E8 / 0x0F0 | 0x0EC / 0x0F4 |
| `effectAttached` (`FxEffectDefRef`) | - | 0x0FC |
| `trailDef` | 0x0F8 | 0x100 |
| `sortOrder` / `lightingFrac` | 0x0FC / 0x0FD | 0x104 / 0x105 |
| `useItemClip` / `unused[1]` | 0x0FE / 0x0FF | - |
| `unused[2]` | - | 0x106 |
| `alphaFadeTimeMsec` (`u16`) | - | 0x108 |
| `maxWindStrength` / `spawnIntervalAtMaxWind` / `lifespanAtMaxWind` (`u16`) | - | 0x10A / 0x10C / 0x10E |
| `u` (`FxElemDefUnion`, 8) | - | 0x110 |
| `spawnSound` (`const char*`) | - | 0x118 |
| `billboardPivot[2]` | - | 0x11C |

T4's `useItemClip` is gone; T5 has `unused[2]` in its place.

## Elem types [V]

| id | T4 | T5 | Kino elems [M] |
|---|---|---|---|
| 0 | spriteBillboard | spriteBillboard | 1541 |
| 1 | spriteOriented | spriteOriented | 111 |
| 2 | tail | **spriteRotated** (new) | 84 |
| 3 | trail | tail | 118 |
| 4 | cloud | **line** (new) | 410 |
| 5 | sparkCloud | trail | 15 |
| 6 | model | cloud | 74 |
| 7 | omniLight | model | 89 |
| 8 | spotLight | omniLight | 103 |
| 9 | sound | spotLight | 0 |
| 10 | decal | sound | 17 |
| 11 | runner | decal | 84 |
| 12 | - | runner | 46 |

- **The ids are renumbered from 2 up.** A T5 elem can't be read through T4's table.
- T5 has **no sparkCloud**. T4's `LAST_SPRITE`/`LAST_DRAWN` boundaries become 5 (trail) and 9 (spotLight).
- `line` is the second most common T5 type (410 elems). It's a muzzle-flash staple, on the flame-strip materials
  (`gfx_fxt_fire_flame_vert_c/d`) [M]. [I] It's a view-aligned strip from `size[0]` (width) to `size[1]` (length), like
  a tail with no velocity stretch.

## Visuals union [V]

- `FxElemVisuals` has the same members in both: material / model / effectDef / soundName. T5's `anonymous` is a
  non-const `void*`.
- OAT picks the member by type the same way in both (`FxEffectDef.txt`):
  - `markArray` when decal; `array` when `visualCount > 1`; `instance` otherwise.
  - model → `model`, runner → `effectDef`, sound → `soundName`.
  - material for the sprite types, tail, line, trail and cloud.
- `FxEffectDefRef` (impact / death / emitted / attached / runner) is a `{handle, name}` union in T5. In the shipped
  zones it holds the name.
- **Decal:** the same `FxElemMarkVisuals`, `materials[2]` (`mc/` model and `wc/` world variants). Kino's blood splat
  `impacts/fx_flesh_hit_splat` has 3 decal visuals (`gfx_impact_blood_spatter01..03`) [M].

## New T5 fields [M]

| field | what Kino has | reading |
|---|---|---|
| `rotationAxis` | 0 on 2650 elems; nonzero on 42 (spriteRotated, cloud, omni), e.g. `0xE0000000`, `0x40040000` | [I] a packed bit field, not an index. Not decoded |
| `effectAttached` | empty on every elem | chained like the other refs anyway |
| `alphaFadeTimeMsec` | decals only: 5000 on 63, 10000 on 6, 500 and 2000 once each | [I] the decal's fade-out time |
| `maxWindStrength` / `spawnIntervalAtMaxWind` / `lifespanAtMaxWind` | `0, 1, 0` on 377 looping elems; real values on 6, e.g. `500, 400, 1000` | [I] wind scaling of looping spawn and life |
| `u` on cloud | int range, e.g. `[1024, 0]`, `[512, 256]` | `cloudDensityRange` |
| `u` on everything else | `[1, 1]` by default; line elems trim to e.g. `[0.4, 0.5]`, `[1, 0.09]` | `billboardTrim` top/bottom width |
| `spawnSound` | 6 elems: `dst_electronics_elc_sm` ×3, `dst_electronics_sparks_lg`, `dst_electrical_large`, `wpn_thundergun_idle` | a sound alias played on spawn |
| `billboardPivot` | 177 elems: spriteRotated `[0, 1]`, billboard `[0, -0.8]`, tail `[0, -0.5]`, line `[0, 0.4]`… | [I] the quad's pivot in half-sizes |
| `unused[2]` | 0 everywhere | |

- The union is chosen by type in the exporter: `cloudDensityRange` on clouds, `billboardTrim` on the rest [I]. The
  values back it up: whole numbers only on clouds, and fractions ≤ 1 elsewhere.

## Atlas [V][M]

- T4 ends `int16 entryCount`; T5 ends `uint16 entryCountAndIndexRange`.
- **Low byte = entry count.** On every drawn Kino elem it equals `2^(colIndexBits + rowIndexBits)` (2377 + 47 elems).
  The 268 misses are light/model/runner/sound elems and 13 billboards, all with 0 [M].
- The high byte is 2 on 2377 elems and 4-128 on the rest. [I] It's an index range; not decoded.
- The export writes `entryCount` (the low byte) for the engine loader, plus the raw `entryCountAndIndexRange`.

## Trails [V][M]

- `FxTrailDef` and `FxTrailVertex` don't change. Only the type id moves (T4 3 → T5 5).
- Kino has 15 trail elems, with 16/16, 8/8, 12/12 or 7/8 verts/indices.

## Elem flags [M]

- T5 sets bits the iw3 table in `ExportFx.cpp` doesn't name. The export keeps them in `unknownFlags`.
- **`0x4000` is the most common** (326 elems), e.g. on every elem of `fx_pistol_flash_base`. Next come `0x200000`
  (100), `0x800000` (61) and `0x400000` (45). [I] These are T5 additions; not decoded.
- The named bits (spawn offset, run-relative, hasGravity …) are assumed to keep their iw3 meaning [I]. The measured
  values are plausible: muzzle-flash elems are `runRelativeTo: effect` and blood drops have `hasGravity`.

## Not carried over

- **impactfx** stays T4 only. T5's impact-type row names aren't read, and the T4 names come from `t4sp.exe`.
- **The engine loader** (`src/fx/FxDef.cpp`) knows T4's type names only. `spriteRotated` and `line` need mapping there
  [I: spriteRotated ≈ spriteOriented with the pivot; line ≈ tail]. The T5 `type` string also has to win over `typeId`,
  since the ids don't match T4's.
