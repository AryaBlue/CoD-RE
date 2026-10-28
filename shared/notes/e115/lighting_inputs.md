# Lighting inputs in WaW / BO1 / BO2 zones

What a map zone carries for lighting things other than lightmapped world surfaces: the light grid, the primary
lights, reflection probes, per-static-model lighting and vertex colour. Lightmaps themselves are in
[world_t4_t5_t6.md §3.1](world_t4_t5_t6.md) and E115's own lightmaps doc (not published here).

Tags: **[M]** measured on the stock maps below with a throwaway probe over OAT's loaders, **[V]** read in the games'
own code (exe or shader disassembly) by us or by b2w, **[I]** inferred.

- Maps: WaW `nazi_zombie_prototype`, BO1 `zombie_theater`, BO2 `zm_nuked`.
- OAT headers, cited `T4H:` `T5H:` `T6H:` = `src/Common/Game/T*/T*_Assets.h` in the vendored copy
  (`<OAT checkout>`, vendored in our b2w fork).
- Offsets come from `offsetof` in an x86 build against those headers **[M]**, so they are OAT's layout. Where OAT
  might be wrong, that is called out.
- b2w references: `LG` = `<b2w checkout>/Reference tools/codport/bo2/lightgrid.py`, `LT` = `<b2w checkout>/src/waw2bo2/lighting.py`.
  Their decodes are read out of t6zm.exe / OpenBLOPS. These are b2w's claims **[V by b2w]**; we haven't re-checked
  them against the exe.

## Counts per map [M]

| | prototype (T4) | theater (T5) | nuked (T6) |
|---|---|---|---|
| primary lights (`ComWorld` = `GfxWorld.primaryLightCount`) | 21 | 90 | 18 |
| by type (0 none / 1 sun / 2 spot / 3 omni / 5 T6 omni?) | 1 / 1 / 14 / 5 | 1 / 1 / 76 / 12 | 1 / 1 / 4 / 0 / 12×type 5 |
| `sunPrimaryLightIndex` (world and grid) | 1 | 1 | 1 |
| light grid entries | 18 105 | 99 290 | 45 835 |
| grid colour sets (`colorCount`) | 3 526 | 32 001 | 0 |
| grid SH sets (`coeffCount`, T6) | n/a | n/a | 47 900 |
| grid row data bytes | 8 484 | 7 316 | 4 524 |
| sky grid volumes (T6) | n/a | n/a | 1 |
| reflection probes | 44 (64×64) | 2 (probe 1 256×256) | 26 (128×128) |
| static models | 1 506 | 3 326 | 2 082 |
| smodels with baked vertex lightmap colours | n/a | n/a | 716 |

Probe 0 is always a dummy at the origin with a 4×4 image on T5/T6. Light 0 is always an all-zero type-0 light.

## 1. Primary lights

### Where they live

- `ComWorld` (asset type `comworld`, same name as the gfxworld) holds the authored lights:
  `primaryLightCount` +8, `primaryLights` +12 (`T4H:2113`, `T5H:2512`, `T6H:1108`).
- `GfxWorld.primaryLightCount` matches on all three maps.
- `GfxWorld.sunLight` is a `GfxLight*` holding only the sun. It is the one we read for the sun today.

### `ComPrimaryLight` offsets (`T4H:2058`, `T5H:2446`, `T6H:3439`)

| field | T4 | T5 | T6 |
|---|---|---|---|
| `type` u8 | 0 | 0 | 0 |
| `canUseShadowMap` | 1 | 1 | 1 |
| `exponent` u8 | 2 | 2 | 2 |
| `priority` | 3 | 3 | 3 |
| `cullDist` i16 | 4 | 4 | 4 |
| `color` f32×3 | 8 | 8 | 8 |
| `dir` | 20 | 20 | 20 |
| `origin` | 32 | 32 | 32 |
| `radius` | 44 | 44 | 44 |
| `cosHalfFovOuter / Inner / Expanded` | 48 / 52 / 56 | same | same |
| `rotationLimit / translationLimit` | 60 / 64 | same | same |
| `mipDistance` | – | 68 | 68 |
| `diffuseColor` f32×4 | – | 72 | 80 |
| `specularColor` / `attenuation` | – | 88 / 104 | – |
| `dAttenuation` / `roundness` | – | – | 72 / 76 |
| `falloff` / `angle` / `aAbB` / `cookieControl0` | – | 120 / 136 / 152 / 168 | 96 / 112 / 128 / 144 |
| `defName` | 68 | 216 | 192 |
| size | 72 | 220 | 196 |

### What the values look like [M]

- **Type.** 0 is empty, 1 is the sun (only slot 1), 2 is a spot (cone set, T4 exponent 1) and 3 is an omni on
  T4/T5. The cosines are filled in on omnis too, but they're leftovers [I].
- **T6** has no type 3 on Nuked. Its 12 type-5 lights use def `white_light_cube` with cosOuter 0.378, so they're
  most likely omnis lit through a cube cookie [I]. The T6 enum isn't in OAT. Its spot lights use def `white_light`.
- **Colour.** WaW is 0..1 LDR: the spots read (1, 0.502, 0) orange, def `light_point_linear`. BO1 is HDR, with
  spots up to about 10. BO2 is HDR: spots 19–73 max channel, type 5 7–28. Nuked's spots are cyan,
  e.g. (24.2, 40.2, 47.9), and its type-5 lights are green (2.95, 13.8, 0.93).
- **Radius.** WaW 300–600. Kino about 200. Nuked spots 400–1000, type 5 60–650.
- **T5/T6 extra fields** (`falloff`, `aAbB`, `angle`, `dAttenuation`, `roundness`) are what BO2's lit programs use
  for attenuation. b2w derived it from t6 `sub_782FA0` (`LT:189-200`) [V by b2w]:

      A = (1/(aAbB.x-aAbB.y), 1/(aAbB.z-aAbB.w), 1/(f.z-f.x), 1/(min(f.w,f.y)-f.y)),   B = (-aAbB.y·A.x, -aAbB.w·A.y, -f.x·A.z, -f.y·A.w)
      atten(d) = smoothstep(sat(d·A.z+B.z) · sat(d·A.w+B.w)) · sat(dAttenuation / d²)

  `falloff` on our maps is (0, radius, 0, 0) [M].

### The sun, compared

| | `GfxWorld.sunLight` (`GfxLight`) | `ComPrimaryLight[1]` | other |
|---|---|---|---|
| WaW | (0.354, 0.470, 0.552) dir (−0.828, −0.253, 0.5) | (0.435, 0.570, 0.693), same dir | GfxLight ≈ 0.81 × Com in every channel [M] |
| BO1 | (8.298, 0, 0) | (13, 12.049, 9.829) dir (0.179, −0.633, 0.754) | `sunParse.sunSettings[0].sunDiffuse` (0.638, 0.538, 0.342, w 13) |
| BO2 | (4.778, 11.637, 15) dir (−0.410, −0.354, 0.841) | (1, 1, 1), same dir | `initWorldSun` sunCd × 15 = GfxLight [M] |

- **BO1.** Normalised, the ComPrimaryLight colour is (1, 0.927, 0.756). Raised to 2.2 that gives (1, 0.846, 0.540),
  which matches sunSettings' (1, 0.843, 0.536) to about 3 digits [M]. So the ComPrimaryLight colour is the
  gamma-space sun and sunSettings holds it linear [I].
- **BO1's `GfxLight` read is broken.** It comes out as (8.3, 0, 0). OAT's 368-byte T5 `GfxLight` (`T5H:2732`)
  likely has the colour slot wrong [I].
- **Recommendation:** take the BO1 sun from `ComPrimaryLight[1]` or `sunSettings`, not `GfxLight`.
  - Our `World.cpp` currently sets no BO1 sun because of that read.
  - The scale between the two candidates (8.29 vs 13) is still [I]: sunSettings.sunDiffuse.w = 13 is the intensity
    multiplier, so the linear sun colour is about (8.29, 6.99, 4.45).
- **BO2.** The sun's colour lives in `GfxWorld.sunLight` / `initWorldSun`. ComPrimaryLight[1] is white.

### `GfxLight` offsets (`T4H:2327`, `T5H:2732`, `T6H:3629`)

- `type` 0, `canUseShadowMap` 1, `cullDist` 2 (T6 4), `color` 4 (T6 8), `dir` 16 (20), `origin` 28 (32),
  `radius` 40 (44), `cosHalfFovOuter` 44 (48), `cosHalfFovInner` 48 (52), `exponent` 52 (56),
  `spotShadowIndex` 56 (60), `def` 60 (T5 352, T6 336).
- Size: T4 64, T5 368, T6 352.
- T6 adds `diffuseColor`, `shadowColor`, `falloff`, `aAbB`, cookies and view/proj matrices.
- The renderer builds GfxLights from the ComPrimaryLights at load [I]. Only `sunLight` is stored in the zone.

## 2. Light grid (lights static models, characters, dynamic entities)

### `GfxLightGrid`

The grid is embedded in GfxWorld at +296 (T4), +536 (T5) and +464 (T6). Struct definitions: `T4H:2439`,
`T5H:2941`, `T6H:1253`.

| field | T4 | T5 | T6 |
|---|---|---|---|
| `hasLightRegions` bool | 0 | 0 | – |
| `sunPrimaryLightIndex` | 4 | 4 | 0 |
| `mins` u16×3 / `maxs` u16×3 | 8 / 14 | 8 / 14 | 4 / 10 |
| `offset` f32 | – | – | 16 |
| `rowAxis` / `colAxis` | 20 / 24 | same | same |
| `rowDataStart` u16* | 28 | 28 | 28 |
| `rawRowDataSize` / `rawRowData` | 32 / 36 | same | same |
| `entryCount` / `entries` | 40 / 44 | same | same |
| `colorCount` / `colors` | 48 / 52 | same | same |
| `coeffCount` / `coeffs` | – | – | 56 / 60 |
| `skyGridVolumeCount` / `skyGridVolumes` | – | – | 64 / 68 |
| size | 56 | 56 | 72 |

### Spatial index

- `mins`/`maxs` are cell coordinates, biased.
  - prototype: (3933, 3955, 2047)–(4247, 4219, 2068)
  - theater: (4008, 4007, 2042)–(4168, 4182, 2063)
  - nuked: (4027, 4035, 2046)–(4163, 4166, 2065)
- They fit cells of 32 × 32 × 64 units with corners at `cell · size − 131072`. On prototype that gives x −5216..4832
  and z −64..1280, inside the world bounds (−6464..5824, z −188..1472).
  - Checked by `zonedump --lightgrid`: the grid E(up), trilinear over the corners, is compared with the lightmap
    page at lit floor points.
  - Median grid/lightmap luma ratio: prototype 1.25, theater 0.99, nuked 1.06. The mean colours agree too.
  - So cell size, origin, row decode and payload decode are all consistent [M].
- The row decode is b2w's (`LT:34-80`, from T4 `sub_71C3D0` / T6 `sub_7584D0`) [V by b2w]:
  - `rowDataStart[row]` is an offset in 4-byte units into `rawRowData` (0xFFFF = empty row).
  - Each row is a header `{u16 colStart, colCount, zStart, zCount; u32 firstEntry}`, then runs of
    `{u8 span, u8 height, [u8|u16 zOffset if height]}`.
  - Every (col, z) in a run takes the next entry index.
- Entry (4 B, `T4H:2427`, `T5H:2927`, `T6H:3760`): `u16 colorsIndex, u8 primaryLightIndex, u8 needsTrace`.
  - On T4/T5 the last byte is `needsTrace`; on T6 it is `visibility`.
  - T4 `needsTrace` is a corner trace mask (`LT:162`) [V by b2w]: 0 on 14 970 of 18 105 prototype entries.
  - T5's is all 0 [M].
  - T6 `visibility` is sun visibility 0–255: 255 on 36 873 of 45 835 nuked entries [M; meaning per b2w].
  - `primaryLightIndex` 255 = no primary light (976 / 8 064 / 2 770 entries) [M].

### Payload: 56 directional samples per set [V by b2w]

- Both games fill a 4×4×4 texel cube per model from its grid cell. The model shader projects the normal onto the
  cube and samples 1.5 cells from the centre, so only the 56 outer texels are read (`LG:16-31`).
- Slot order: z slowest, then y, then x, interior skipped. Direction = normalize(cell − 1.5) (`LG:614-628`).

**T4** `GfxLightGridColors { u8 rgb[56][3] }`, 168 B (`T4H:2427-2437`):
- Plain gamma RGB. WaW's model program uses `2·c/255` in gamma space, which is linear `4·(c/255)²` (`LT:158-161`).
- Measured mean bytes (29.2, 26.0, 26.3), range 0–255. A mid set reads about (10–28) per channel [M].

**T5** `GfxCompressedLightGridColors { u8 rgb[56][3] }`: each 3-byte slot is ONE 24-bit word, not three channels
(`LG:215-238`, from OpenBLOPS `R_DecodeLightGridColors`):

    packed = b2<<16 | b1<<8 | b0;  Y = ((packed>>12)/4095)² · 31.875
    R = ((packed>>6)&63)/63 · Y/0.25;  B = (packed&63)/63 · Y/0.25;  G = (Y − R/4 − B/4)/0.5

- Kino's mid set (bytes 208,147,26) decodes to (0.33, 0.35, 0.35) linear, which is Kino's own ambient
  (0.314, 0.328, 0.342) [M with b2w's decode].
- Read as channels, the bytes come out green/yellow. That's the mistake to avoid.

**T6** `coeffs { u16 coeffs[9][3] }` (`T6H:3772`). Every stock map uses these; `colors` (as T4 bytes,
`(b/255)²·32`) is read only when `coeffCount == 0` (`LG:27-31`).
- `value = u16/65535 · 32 − 16`. Basis order: `1, x, y, z, zx, zy, xy, 3z²−1, x²−y²` (`LG:28-29`, t6zm 0x755740 / 0x7556a0).
- Our data agrees: coeff 0 (DC) is always ≥ 32770, i.e. ≥ 0 decoded, while the others centre on about 33 000 [M].
- Nuked mid set DC = (40361, 44906, 46010) → (3.71, 5.93, 6.47). That's cyan, like its lightmap ambient [M].
- Entry `colorsIndex` max is 47 9xx, so it indexes `coeffs` [M].

**T6 sky grid volume** (`T6H:3777`, 1 on nuked): a huge box (−44 k..59 k) with its own colorsIndex 2104, plight 1,
vis 200. That's the outside-the-grid fallback [I].

## 3. Static models

### `GfxStaticModelDrawInst` lighting fields

Struct definitions: `T4H:2566`, `T5H:3106`, `T6H:3946`. The full layout is in world_t4_t5_t6.md §2.

| field | T4 | T5 | T6 |
|---|---|---|---|
| `cachedLightSettingIndex` | 64 | – | – |
| `lightingHandle` u16 | – | 72 | 68 |
| `colorsIndex` u16 | – | – | 70 |
| `lightingSH` (`GfxLightingSHQuantized`, u16 V0..V2[4]) | – | – | 72 |
| `primaryLightIndex` | 71 | 75 | 96 |
| `visibility` | – | – | 97 |
| `reflectionProbeIndex` | 70 | 74 | 98 |
| `smid` | – | – | 100 |
| `lmapVertexInfo[4]` (12 B each) | – | – | 104 |

Values [M]:
- `lightingHandle` / `cachedLightSettingIndex` are 0 on every model in all three games. They're filled at
  runtime [I].
- T6 `lightingSH` is all zeros in the zone. The runtime fills it from the grid coeffs; b2w notes the model shader
  divides probe reflection by gridSH / probeSH (`LG:600-612`) [V by b2w].
- T6 `colorsIndex` ranges 2..8358 (in range of `coeffs`) and `visibility` 0..255 (mean 133). That's a per-model
  baked grid sample plus sun visibility [I].
- `primaryLightIndex` is set per model. The sun (1) dominates: 1156 / 600 / 1377 models.
- Reflection probe index: prototype uses 43 probes, theater only probe 1, nuked 25.
- Flags: theater 0x1 ×33; nuked 0x1 ×33, 0x2 ×634, 0x3 ×82 (meaning unknown).

### `GfxStaticModelInst`

Struct definitions: `T4H:2581`, `T5H:3059`, `T6H:3894`.
- `mins` 0, `maxs` 12, `lightingOrigin` 24 (T5/T6), `groundLighting` `GfxColor` 24 (T4) / 36 (T5).
- `groundLighting` is all zero in both T4 and T5 zones. It's runtime [I].
- `lightingOrigin` (T5/T6) is the point to sample the grid at, instead of the bounds centre [I by name].

### T6 baked vertex lightmap colours

`GfxStaticModelLmapVertexInfo` (`T6H:3939`): `u32* lmapVertexColors`, VB, `u16 numLmapVertexColors`, one per LOD.
- 716 of 2082 nuked models carry them: 14–28 610 per LOD, mean 786 [M].
- Example LOD 0 words: `00897e64 00887d64` on an office chair, `00030c10` on a dark one.
  - Read as BGRA (little-endian D3DCOLOR) that's R 0x89, G 0x7e, B 0x64: warm. The order is [I].
  - The 4th byte is used: mean 54 over all words, 0 in those examples. Its meaning is unknown, possibly a
    scale/exponent or sun visibility [I].
- These are per-vertex lightmap samples. They replace the grid for those models (how isn't measured) [I].
- **Not yet decoded.** Checking the encoding needs the T6 static-model lit shader (`*_lmap_vertex*` / smodel
  techniques) disassembled, as done for the world programs.

## 4. Reflection probes

`GfxReflectionProbe` (`T4H:2343`, `T5H:2869`, `T6H:3744`):

| field | T4 | T5 | T6 |
|---|---|---|---|
| `origin` | 0 | 0 | 0 |
| `lightingSH` (`GfxLightingSH`, f32 V0..V2[4]) | – | – | 12 |
| `reflectionImage` `GfxImage*` | 12 | 12 | 60 |
| `probeVolumes` / `probeVolumeCount` | – | 16 / 20 | 64 / 68 |
| `mipLodBias` | – | – | 72 |
| size | 16 | 24 | 76 |

- The array is at `GfxWorld.reflectionProbes` +248 (count +244) on T4. On T5/T6 it is at
  `GfxWorld.draw.reflectionProbes` (draw +4, count draw +0) (`T5H:2907`, `T6H:1231`).
- Images are cubemaps named `*reflection_probe<i>`: 64² on WaW, 256² on Kino, 128² on Nuked [M].
- `probeVolumes` is 0 on all probes measured [M].
- T6 probe SH is float and filled in the zone: probe 1 V0 (0.612, 1.066, 1.255, 2.488) [M].
  - The layout (3 × vec4 per probe) looks like the usual packed L1 RGB form [I].
  - It's used to normalise reflections against the grid SH (`LG:604-608`) [V by b2w].
- `mipLodBias` −8 on all Nuked probes [M].
- World surfaces pick a probe through `GfxSurface.reflectionProbeIndex`; static models through the draw-inst field.

## 5. Vertex colour

Who exports it, where, and whether it matters. **Correction:** it only multiplies albedo on single-layer
techsets. On multi-layer ones it is layer blend weights, not a tint. See section 7 [V].

| | world vertex | colour field | static model vertex (`GfxPackedVertex`) |
|---|---|---|---|
| WaW | `GfxWorldVertex`, 44 B (`T4H:2276`) | +16 `GfxColor`, D3DCOLOR (BGRA in memory) | +16 `GfxColor` (`T4H:413`) |
| BO1 | `GfxWorldVertex`, 44 B (`T5H:2884`) | +16 `GfxColor`, D3DCOLOR (BGRA) | +16 `GfxColor` (`T5H:482`) |
| BO2 | `GfxPackedWorldVertex`, 36 B in `draw.vd0` | +16, 4 bytes (read as RGBA) | +16 `GfxColor` (`T6H:5744`) |

- The BGRA order on T4/T5 is the D3D9 D3DCOLOR convention [I, strong]. BO2's RGBA order is [I]: the cut channel is
  green in either order, so the T6 finding below holds regardless.

Measured [M]:
- **World, over lightmapped corners:**
  - WaW mean (254.8, 239.6, 254.1), 91.4% white
  - BO1 (254.8, 252.2, 253.8), 97.8% white
  - BO2 (253.2, 225.1, 251.6), 77.9% white
  - BO2's cut is green. That is the layer-1 blend weight (section 7), not a tint, so it has nothing to do with
    Nuked's cyan cast.
- **Static models, LOD 0 over unique smodel XModels:**
  - WaW 70 models: mean (232.3, 232.2, 232.3, a 248.5), 82.8% white, 24 models non-white
  - BO1 234 models: (252.3, 252.3, 252.2), 97.7% white, 29 non-white
  - BO2 332 models: (253.4, 253.4, 253.4), 98.9% white, 38 non-white
  - The channels are equal, so model vertex colour is grey (an AO/darkening mask), not a tint [M].
- **zonedump exports none of it today.** Neither `World.cpp` nor the xmodel path writes COLOR_0.

## 6. BO2 directional third (zonedump `Lightmap.cpp`)

**What changed.**
- Until now the BO2 page was only the ambient third.
- Nuked's LIT and LIT_SUN_SHADOW programs compute
  `ambient + saturate(dot(page3.rgb·2−1, N_world)) · directional` [V, fxc disassembly of wpc_lit_sm].
- zonedump now bakes that per texel. N is the interpolated vertex normal (flat normal map, the same convention as our
  WaW/BO1 bakes), rasterised into page space from the world triangles. Seams are grown 4 texels; uncovered texels
  use (0, 0, 1).
- Only `pageT6` changes. The WaW/BO1 pages are untouched.

**Numbers, linear light, page means [M]:**

| page | before (ambient only) | after |
|---|---|---|
| 0 (1024×2048) | (1.20, 1.71, 1.88), p99 (3.5, 5.2, 5.2) | (3.16, 4.26, 4.71), p99 (8.6, 14.2, 12.5) |
| 1 (1024×1024) | (1.43, 1.98, 2.21) | (3.66, 4.78, 5.50) |
| 2 (1024×512) | (1.65, 2.29, 2.62) | (3.86, 5.50, 6.62) |

- About 2.5× brighter, same hue (B/R ≈ 1.5 both). It doesn't change the cyan, which is authored (see the cyan
  report).
- Through the HDR/tonemap path the visible change is mainly contrast: sun-facing sides are brighter than shaded
  ones on rocks, walls and the bus.
- Export cost: none measurable (Nuked exports in 2.2 s).

**Shots.** Engine `--screenshot`, a contributor's debug build. Before = the 926e511 export, after = the new export.
Local files (not published):
- `dir_compare_t6.png` (before | after), `--cam 20 6 20 --target 0 1 -10`
- `dir_compare_t6b.png`, `--cam -25 4 5 --target 0 2 0`
- single frames: `dir_before_t6*.png`, `dir_after_t6*.png`

**Not done.** The bumped normal. The game uses the normal-map normal; we bake at the geometric one, so bump detail
in the directional term is missing until the engine does this per pixel.

## 7. Vertex colour semantics per techset (why `--vertex-colour` turns surfaces magenta)

**Method.** The probe walked every lit world surface on prototype, theater and nuked. For each material it took the
techset, the LIT pass shaders and the texture table. Then fxc disassembled the LIT VS and PS of every world techset
(416 programs, `fxc /dumpbin`, sm3 on T4/T5, DXBC on T6). COLOR0 was traced from the VS input through the
interpolator to each PS instruction that reads it. That covers 31 lit techsets on T4, 99 on T5 and 72 on T6, all
the lit ones the three maps use [V].

### The two families

| | single layer | multi layer |
|---|---|---|
| techset name | `wc_l_sm_<L0>` (T4/T5), `wpc_lit_sm_<L0>_<hash>` (T6) | `l_sm_<L0>_<L1>[_<L2>…]` (T4/T5), `lit_sm_<L0>_<L1>…` (T6), no prefix, no hash |
| COLOR0 in the PS | `albedo.rgb *= COLOR0.rgb` | per-layer blend weights, **never** a tint |
| measured | 100% white on every material in all 3 maps [M] | carries all the non-white values [M] |

Shader evidence [V]:
- **Single layer:**
  - T5 `wc_l_sm_r0c0n0s0x0`: `mul_pp r0.xyz, r1, v0`
  - T6 `wpc_lit_sm_r0c0n0x0_f488034e`: `mul r1.xyz, r1.xyzx, v1.xyzx`
  - T4 `wc_l_sm_r0c0n0s0_sco`: `mad_pp r2.xyz, r0, -v0, r2 ; mad_pp r0.xyz, r0, v0, r2`, which is a lerp, so the
    tint still holds at white [I]
  - Bases `b0` (blend) and `t0` (alpha test) also take COLOR0.a into alpha.
- **Multi layer, layer k ≥ 1 weighted by one channel:**
  - layer 1 = **G**, layer 2 = **B**, layer 3 = **A**
  - R is read only when the base op is `b0` (base alpha, e.g. T4 `l_sm_b0c0n0s0_sco_b1…`: `mul_pp r5.w, r1.w, v5.x`)
  - 2 layers: the VS packs COLOR0.xy into TEXCOORD6.xy beside the layer-1 UV in .zw (T5 `mov o7.xy, v1 ;
    mov o7.zw, v5.xyxy`). The PS then does T6 `lit_sm_r0c0n0x0_b1c1n1`: `sample r1, v7.zwzz, t2 ; mul r1.w,
    r1.w, v7.y`.
  - 3 or more layers: COLOR0 arrives as COLOR (T6 `…_m2c2_m3c3`: `mad … v1.yyyy` for layer 1, `mad r3.xyz,
    v1.zzzz, r3, 1` for layer 2, `mad r3.xyz, v1.wwww, r3, 1` for layer 3).
- **No COLOR0 at all:** only `wpc_sw4_3d_unlit_3layer_texcolor` (an unlit effect), so it is irrelevant here.

**Op letter of a layer group** (`<op><k>` then `c<k>` colour, `n<k>` normal, `s<k>` spec, `x<k>`):

| op | layer k combine (w = its channel) | confidence |
|---|---|---|
| `b` blend | `c = lerp(c, cₖ, cₖ.a·w)`. Normal and spec lerp by the same factor. | [V] |
| `m` multiply | `c *= lerp(1, cₖ.rgb, w)` (`mad r, w, cₖ - 1, 1` form) | [V] |
| `t` | `cₖ.a·w` against a constant threshold (alpha-tested blend) | [I] |
| `a` | `cₖ·w` added | [I] |
| `v` | `log(w)` / `1-w` terms (height or power blend) | [I] |
| `x<k>` in a group | an extra term lerped by the same w | [I] |
| `_sco`, `_sls` | flags on the whole technique, not layers | [V] |

Layers ≥ 1 sample their own UV from the second vertex stream: T4/T5 `srfTriangles.vertexLayerData`, T6
`draw.vd1` at `vertexDataOffset1`. The routing is in `MaterialVertexDeclaration.routing` (enums `T4H:1317`,
`T5H:1082`, `T6H:5781`). I did not print the per-pass routing or measure the stride [I]. That step is next if
layers get implemented.

### Rule for zonedump (per material, from the techset name)

Split the techset name on `_`. A token is a layer group if it matches `^([a-z]\d)+$` with one repeated digit, which
is the layer index (`b1c1n1s1x1` is layer 1). The highest index + 1 is the layer count.
- Shortcut that agrees on all 202 lit techsets: a `wc_` or `wpc_` prefix means single layer, and no prefix on
  `l_sm_` / `lit_sm_` means multi-layer [M].
- **1 layer:** export COLOR0 and tint albedo with `rgb²` (linear). Base ops `b0`/`t0` also use the alpha. It is
  white on all three maps today, so the tint is cosmetic but correct.
- **≥ 2 layers:** do **not** tint.
  - Interim: export the base layer with COLOR0 = white. This is what fixes the magenta.
  - Proper: export layer k's colour/normal/spec images, the second UV set and the weights (G, B, A for k = 1, 2, 3;
    R only for a `b0` base). Combine them in the shader per the op table.
- Confidence:
  - **high** that the family split and channel mapping are right: every lit world techset on 3 maps was traced, with
    no exception.
  - **high** for `b` and `m`, the only ops on the magenta surfaces.
  - **medium** for `a`/`t`/`v`/`x` [I].

### The magenta surfaces in the grid

The magenta is `albedo × (R, G≈0, B)`. G is the layer-1 weight, and B and A sit at 255 because a 2-layer techset
ignores them. Rows below are ranked by triangles × magenta share [M]. Mean RGBA is in 0–255.

**Prototype (T4).** Material names are hashed (`*<a>n_<b>n`), so the layers come from the texture table:

| material | tris | mean RGBA | magenta | techset | layer 0 colour → layer 1 colour |
|---|---|---|---|---|---|
| `*9n_10n` | 3043 | 255 151 255 255 | 38% | `l_sm_r0c0n0s0_sco_b1c1n1s1_sco` | `peleliu_wall_concrete_bunker_chipped_c` → `peleliu_wall_concrete_grungy_edges_c` |
| `*28n_29n` (the road) | 615 | 255 157 255 255 | 38% | `l_sm_r0c0n0s0_sco_b1c1n1s1` | `peleliu_terrain_dirt_crumbly_c` → `okinawa_terrain_dirt_drydirt_c` |
| `*33n_35n` | 391 | 255 130 255 255 | 48% | `…_sco_b1c1n1s1_sco` | `peleliu_terrain_dirt_drymuddrk_c` → `peleliu_terrain_dirt_crumbly_c` |
| `*56n_35n` | 370 | 255 133 255 255 | 47% | same | `peleliu_terrain_dirt_trckslight_c` → `peleliu_terrain_dirt_crumbly_c` |
| `*57n_35n` | 300 | 255 149 255 255 | 42% | same | `peleliu_terrain_grass_patchy_dead_c` → `peleliu_terrain_dirt_crumbly_c` |
| `*1n_30n` | 445 | 252 130 255 255 | 48% | same | `berlin_ceilings_plaster2_c` → `peleliu_terrain_rubble_conc_chunks_c` |

- Prototype's road is the dirt-track blend family (`*28n_29n`, `*33n_35n`, `*56n_35n`, …).
- 3-layer `*9n_10n_10n` / `*57n_27n_35n` use G for layer 1 and B for layer 2. Their B is also below 255.

**Kino (T5).** The names keep the layer materials, `*<a>n_<b>n(base:layer1)`:

| material | tris | mean RGBA | magenta | techset |
|---|---|---|---|---|
| `mtl_theater_carpet_2 : eb_ter_trashpile_blend` | 2201 | 254 224 255 255 | 11% | `l_sm_r0c0n0s0x0_b1c1n1s1x1` |
| `eb_art_floor_concrete_tile03 : eb_ter_trashpile_blend` | 990 | 255 144 255 255 | 44% | same |
| `eb_ter_asphalt_old : eb_ter_trashpile_blend` | 828 | 254 193 255 255 | 28% | same |
| `eb_art_floor_wood_hardwood02 : eb_ter_trashpile_blend` | 653 | 255 157 255 255 | 40% | same |
| `eb_art_ceiling_plaster01 : decal_grime_drip` | 1051 | 254 218 255 255 | 14% | `l_sm_r0c0n0s0x0_m1c1` |
| `eb_art_wall_metal_painted_chipped01 : decal_grime_drip` | 954 | 252 224 255 255 | 10% | same |

- The floors are a trash-pile (`glo_dec_trash_pile_c`) blend over carpet, tile and hardwood.
- The ceiling and walls are multiplied grime drips (`m1`, multiply).

**Nuked (T6):**

| material | tris | mean RGBA | magenta | techset |
|---|---|---|---|---|
| `zm_nuked_vinylsidings_yellow : wood_burned_blend` (**yellow house wall**) | 634 | 255 168 255 255 | 33% | `lit_sm_r0c0n0s0_b1c1n1x1` |
| `zm_nuked_vinylsidings_white : wood_burned_blend` | 2687 | 254 148 255 255 | 45% | `lit_sm_r0c0n0s0_b1c1n1x1` |
| `us_art_wall_woodplank_clean : zm_nuked_wood_planks_burnt_lambert_blend` | 1497 | 255 172 255 255 | 30% | `lit_sm_r0c0n0x0_b1c1n1` |
| `wood_planks_old_white : wood_burned_blend` | 1354 | 255 149 255 255 | 42% | `lit_sm_r0c0n0_b1c1n1x1` |
| `zm_nuked_wall_creampaint_02 : zm_nuked_floor_burnt_02` | 1155 | 255 128 255 255 | 53% | `lit_sm_r0c0n0x0_b1c1n1x1` |
| `zm_nuked_grass_burnt : zm_nuked_rubble_ash_dark_blend` | 973 | 221 123 255 255 | 43% | `lit_sm_r0c0n0_b1c1n1` |
| `zm_nuked_asphalt_cracked_dark : zm_nuked_rubble_ash_dark_blend` (road) | 334 | 255 159 255 255 | 39% | `lit_sm_r0c0n0x0_b1c1n1` |

- The yellow wall's layers:
  - layer 0: `zm_vinylsiding_yellow_c` / `_n` / `_s`
  - layer 1: `wood_trim_burned01_c` / `_n` (burn marks), blended by G
- The yellow wall's 3-layer pieces have B below 255, as layer 2 predicts. `…_17n_17n` (`_b2c2n2x2`) has mean
  B 114, and `…_17n_5` (`_m2c2`, `decal_wall_fillet`) has B 190.
- The roads and roofs are the same `rubble_ash` / `floor_burnt` blends.
- The non-white R on the grass and rock rows (221, 224, 233) is unused, because those bases are `r0`.

Probe outputs: `vc_t4.txt`, `vc_t5.txt`, `vc_t6.txt` (per-material lines), `flow_t*.txt` (COLOR0 traces) and
`vcasm\` (disassembly), all in a contributor's scratch folder (not published).

## 8. Sun shadow maps (prep for cascaded shadow maps)

**Short version.** None of the three games stores cascade splits in the zone. They all use the same fixed scheme:
two sun-shadow partitions (near and far) with a cross-fade, and a far partition reaching 4× the near one. The near
partition's size comes from one value, `sm_sunSampleSizeNear` (world units per shadow texel). Only BO1 stores it
per map; WaW and BO2 take it from a dvar.

### What the shaders do [V]

From the `LIT_SUN_SHADOW` pixel programs (technique `0xC` on T4/T5, `0x6` on T6):
- T4 `wc_l_sm_r0c0n0s0_sco` → `lm_sm_sun_r0c0n0s0_sm3_sco.hlsl`
- T5 `wc_l_sm_r0c0n0s0x0` → `pimp_shader_lmap_b569ecd0`
- T6 `wpc_lit_sm_r0c0n0x0_f488034e` → `pimp_shader_lmap_e85ea8d1`

The VS writes one shadow coordinate (T4 `TEXCOORD4`, T6 `v7`). `.xy` is the near-partition UV, `.z` the depth and
`.w` the distance in near-partition units. The PS then switches on `.w`:

| `.w` | lookup |
|---|---|
| ≤ 0.75 | near partition only |
| 0.75–1 | near and far, lerp by `4w − 3` |
| 1–4 | far partition only. The far UV is `xy · switchPartition.w + switchPartition.xy` (`shadowmapSwitchPartition`, T4/T5 `c2`, T6 `cb0[97]`). |
| > 4 | no map. T4/T5: the branch skips the lookup, so only the baked gate applies [I, tail not fully traced]. T6 fades to the **baked** visibility over `w` 3–4 (`add_sat w, −3`), then uses only that. |

- **Filtering:**
  - T4/T5: 4 depth taps compared by hand (`cmp`, ×0.25), at offsets of 1/2048 and 1/4096 in UV. The constants suggest
    two 1024² partitions in a 1024×2048 atlas (`y · 0.5`) [I].
  - T6: 12-tap Poisson PCF with comparison sampling (`sample_c_lz`, `SunShadowSamplerState`). The tap radius is
    `sunShadowmapPixelSize` (`cb0[99]`: .xy near, .zw far). That constant is T6-only (`CONST_SRC_CODE_SUNSHADOWMAP_PIXEL_SIZE`, `T6H:5935`).
- **Baked gate:**
  - T4 reads the primary lightmap's `.x`, and T5 the primary's `.y`. If that is 0, the shader skips the map and the
    sun stays shadowed.
  - T6 starts from the baked visibility (lightmap secondary third, `.w`) and only replaces it within the map's range.
  - So the baked sun-visibility pages zonedump already exports are the right fallback beyond the far partition and
    for culled casters.

### Where the parameters live [M]

| | near sample size | casters | other |
|---|---|---|---|
| WaW (prototype) | dvar `sm_sunSampleSizeNear`. `maps/_load.gsc` lerps it from triggers (`do_sunsamplesize`). Nothing in worldspawn. | `shadowGeom[sun=1]`: 0 surfaces, 1156 smodels | `surfaceCastsSunShadow` reads all-zero (0/3481) |
| BO1 (Kino) | **`sunParse.sunSettings[0].sunShadowSampleSizeNear` = 0.25** (`T5H:2711`) | `shadowGeom[1]`: 0 surfaces, 600 smodels | `surfaceCastsSunShadow` 0/8289. Worldspawn has `sunshadowintensity 8` and `_sunshadowcolor 0.8 0.82 0.85`. |
| BO2 (Nuked) | not in the zone (no worldspawn key, no script hit); dvar default [I] | `smodelCastsShadow` 234/2082. `surfaceCastsShadow` and `surfaceCastsSunShadow` read 0/9865. `shadowGeom[1]` is empty. | `shadowMapVolumes` 5, with 46 planes |

- **All-zero caster bits** on every map. Either the bits are filled at load or OAT's layout is off [I]. Use the
  material instead: `MTL_GAMEFLAG_CASTS_SHADOW = 0x40` (`T4H:1032`, `T6H:637`).
- **BO2 shadow-map volumes.** Each volume's `control` decodes as `firstPlane | (planeCount − 1) << 16 | flags << 24`
  [M]:
  - volume 0: planes 0–5, flags 2
  - volumes 1–4: 10 planes each from 6/16/26/36, flags 8
  - Their sum is exactly 46.
  - Volume 0 is an axis-aligned box around the playable area (|x| ≈ 2130, y −1176…600, z −296…144).
  - Their use is probably limiting the cached/static sun-shadow region [I].
- **`outdoorImage`** (512² on all three) and `outdoorLookupMatrix` map world space to a 0–1 outdoor mask. They are
  for weather and outdoor occlusion, not shadows [I].
- The direction is the sun's (section 1). `GfxLight.canUseShadowMap` / `sunisprimarylight 1` mark the sun as primary
  light 1 on all three maps.

### For E115's CSM

- **Faithful match:** 2 cascades.
  - near = 1024 texels × `sampleSizeNear`, i.e. 256 units at Kino's 0.25 [I: the 1024 comes from the atlas
    constants]
  - far = 4× near
  - blend over the last 25% of near
  - fall back to the baked sun visibility beyond 4×
- **Engine-native:** more cascades are fine if the outer edge (4 × near) and the baked fallback stay. That keeps
  lightmap-shadowed interiors from catching dynamic sun.
- **Defaults:** BO1 is per map. WaW/BO2 need a default sample size. CoD4's shipped `sm_sunSampleSizeNear` is 0.25
  [I, unverified for these exes].

Probe outputs in a contributor's scratch folder (not published): `csm_t4.txt`, `csm_t5.txt`, `csm_t6.txt`, plus
`ssasm\ss_t4.asm`, `ss_t5.asm`, `ss_t6.asm`.

## Open items

- T6 smodel `lmapVertexColors` encoding (shader disassembly needed).
- The T6 light type enum (type 5).
- T6 `GfxLightGrid.offset` = 12.0 on nuked: meaning unknown.
- The model shaders' use of the grid (cube vs SH, `lightingOrigin`) for each game, if the engine wants a faithful
  smodel path.
