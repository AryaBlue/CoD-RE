# FX: T6 (BO2) PC layout against T5

The `FxEffectDef` / `FxElemDef` layouts that `tools/zonedump/ExportFx.cpp` reads for T6, against T5
(`fx_t5_layout.md`). It's for the BO2 maps (`zm_nuked`, `zm_transit`).

Tags:
- **[V]**: read from OAT's `T6_Assets.h` and its zone-load rules (`src/ZoneCode/Game/T6/XAssets/FxEffectDef.txt`,
  `FxImpactTable.txt`), or from Steam `t6zm.exe` at the VA given. Offsets are for the 32-bit build. `ExportFx.cpp`
  static_asserts the sizes and key offsets.
- **[M]**: measured by exporting every effect of two zone stacks:
  - nuked: `zm_nuked` + `code_post_gfx_zm`, `common_zm`, `patch_zm`, `zm_nuked_patch`, `english/en_common_zm`,
    `en_patch_zm`, `en_zm_nuked`. 363 effects, 161 images, 0 missing.
  - transit: the same with `zm_transit` / `zm_transit_patch` / `en_zm_transit`. 282 effects, 136 images, 0 missing.
- **[I]**: inferred.

## Sizes [V]

| struct | T5 | T6 |
|---|---|---|
| `FxEffectDef` | 0x3C (60) | 0x4C (76) |
| `FxElemDef` | 0x124 (292) | 0x124 (292) |
| `FxElemVisualState`, vel/vis samples, atlas, trail | same | same |
| `FxImpactEntry` | 31 + 4 | **32** + 4 |
| impact rows | 21 | 21 |

## `FxEffectDef` [V]

| field | T5 | T6 |
|---|---|---|
| `name` | 0x00 | 0x00 |
| `flags` | 0x04 `char` | 0x04 `uint16` |
| `efPriority` | 0x05 | 0x06 |
| `elemDefCountLooping` / `OneShot` / `Emission` | 0x10 / 0x14 / 0x18 `int` | 0x08 / 0x0A / 0x0C `int16` |
| `totalSize` | 0x08 | 0x10 |
| `msecLoopingLife` | 0x0C | 0x14 |
| `msecNonLoopingLife` | - | 0x18 |
| `elemDefs` | 0x1C | 0x1C |
| `boundingBoxDim[3]` | 0x20 | 0x20 |
| `boundingSphere[4]` | 0x2C | - |
| `boundingBoxCentre[3]` | - | 0x2C |
| `occlusionQueryDepthBias` | - | 0x38 |
| `occlusionQueryFadeIn` / `FadeOut` (`int`) | - | 0x3C / 0x40 |
| `occlusionQueryScaleRange` | - | 0x44 |

- **The bounds are filled** in T6: a non-zero `boundingBoxDim` on all 643 exported effects. They were all zero in BO1 [M].
- `msecNonLoopingLife` is set on 488 of 643 [M].
- **Occlusion query:** off on almost every effect. 637 have scale range `[1, 0]` and no fades; 3 use it (bias,
  fade-in/out, scale `[0.2, 0.8]` or `[0.5, 0.5]`) [M]. [I] It's the sun/flare occlusion fade, so a port can ignore it at
  first.
- Common effect flags: 16 (99), 0 (83), 33804 (49), 1165 (44), 33805 (44), 128 (35) [M]. Not decoded.

## `FxElemDef` [V]

Same size and offsets as T5. Two changes:

| field | T5 | T6 |
|---|---|---|
| 0x100 | `FxTrailDef* trailDef` | `FxElemExtendedDefPtr extended`: `trailDef` when trail, `spotLightDef` when spot light |
| visuals union | material / model / effectDef / soundName | + `GfxLightDef* lightDef`, loaded for spot lights |

- **`extended` has to be read by type.** OAT loads `trailDef` only for `FX_ELEM_TYPE_TRAIL` and `spotLightDef` only
  for `FX_ELEM_TYPE_SPOT_LIGHT` (`FxEffectDef.txt`). On other types the pointer isn't a trail.
- `FxSpotLightDef` is `{fovInnerFraction, startRadius, endRadius}`. Spot lights export it as `spotLight`, and their
  visual as `{lightDef: <name>}`.
  - [M] Neither map has a spot-light elem, so that path is unexercised.
- Elem type ids are T5's (spriteRotated 2, line 4, runner 12), so the export reuses T5's name table.
- Vectors are `vec2_t`/`vec3_t` unions in T6 (`collMins`, vel ranges, `billboardPivot`, trail verts). Same bytes.

## Colour order [M]

- **T6 stores the vis-state colour as r g b a.** T4/T5 store a d3dcolor (b g r a), which the export swaps.
- With the T4/T5 swap, T6 muzzle-flash omni lights come out blue (157, 203, 250). Unswapped they're warm,
  e.g. `fx_at4_flash_world` (180, 148, 113), and `impacts/fx_flesh_hit` is red (50, 0, 0). So the T6 path writes the
  bytes in order.

## Elem types and fields [M]

nuked / transit elems: spriteBillboard 1507 / 1208, line 428 / 361, tail 160 / 126, runner 100 / 92, omniLight 89 / 88,
cloud 87 / 60, spriteRotated 74 / 53, model 71 / 67, decal 47 / 44, spriteOriented 37 / 19, trail 22 / 25, sound 10 / 5.

- The T5 extras carry real data:
  - wind on 731 nuked elems
  - `spawnSound` on 31 (`dst_electronics_elc_sm` ×12, `dst_spark_*`, `pfx_fire_fuel_sm`, `amb_ember_burn`)
  - `effectAttached` once (`maps/zombie/fx_zmb_trail_nuke_debris`)
  - `alphaFadeTimeMsec` on decals, plus 2 sprites
- Atlas: as T5. The low byte of `entryCountAndIndexRange` is the entry count on every drawn elem.
- Unknown elem flag bits, as in BO1: `0x200000` (178), `0x800000` (95), `0x400000` (77), `0x40000` (58), `0x20000` (32).
  T5's common `0x4000` is rare here (3).
- `spawnRange` bands are present as in BO1, so the engine's distance-LOD spawn gate matters for T6 too.

## Impact table [V][M]

- The asset type is `fximpacttable`, in `common_zm.ff` (asset `ImpactFx`). OAT loads 21 rows.
- Row names: `t6zm.exe` 0xb11100 has the same 21 + 4 flesh names as BO1.
- Columns: the infoParm table at `t6zm.exe` 0xca29d8 (stride 20) lists bark … tallgrass, then **riotshield**, then
  opaqueglass. So the 32 columns are default + 30 + `riotshield`. opaqueglass falls past the end, as it does in BO1.
- Check: the `riotshield` column holds `impacts/fx_riotshield_large` on the bullet rows [M]. 723 cells filled.

## Notes

- `weapon//grenade/fx_trail_grenade` (double slash) is its own asset next to `weapon/grenade/fx_trail_grenade`. Both
  export to the same file, so 363 effects give 362 files on nuked.
- Images come from the ipaks next to the zone (`--game` set). No image warnings on either map.
