# T4 / T5 / T6 map world structs: a cross-game reference

What E115 needs to read from OAT's in-memory `gfxworld`, `clipmap`, `comworld` and `mapents` assets to draw a WaW (T4),
BO1 (T5) or BO2 (T6) map as a recognisable, correctly placed environment, and later to collide with it. Researched
2026-10-26. XModel, Material and GfxImage are covered in [assets_t4_t5_t6.md](assets_t4_t5_t6.md) (called **ASSETS** below); this file only
points at it.

## Conventions

- **Path prefixes.**

  | Prefix | Path |
  |---|---|
  | `OAT/` | `<OAT checkout>/src/` (the vendored OpenAssetTools tree E115's helper links; the only one with T4) |
  | `OAT6/` | `<OAT T6 fork>/src/` (T6 OpenAssetTools fork with the BSP linker) |
  | `RE/` | the root of this repo (CoD-RE) |
  | `CONV/` | `<b2w checkout>/src/waw2bo2/` (B2W Python converter) |
  | `AUDIT/` | `<scratch>/worldaudit/zm_nuked/maps/mp/` (a measured dump of stock `zm_nuked`; not published) |

- **Short names.**

  | Name | File |
  |---|---|
  | `T4H` / `T5H` / `T6H` | `OAT/Common/Game/T{4,5,6}/T*_Assets.h` |
  | `D4` / `D5` | `OAT/ObjWriting/Game/T{4,5}/Maps/WorldConverterDumperT{4,5}.cpp` |
  | `D6` | `RE/games/t6-bo2/oatfork/new/src/ObjWriting/Game/T6/Maps/WorldConverterDumperT6.cpp` |
  | `U5` | `RE/games/t5-bo1/oat-bsp/new/src/ObjWriting/Game/T5/BSP/BSPUnlinkerT5.cpp` (T5 world -> BSP data, second reader) |
  | `GWL` | `OAT6/ObjLoading/Game/T6/BSP/Linker/GfxWorldLinker.cpp` (writes T6 GfxWorld, so it shows the intended layout) |
  | `BSPC` | `OAT6/ObjLoading/Game/T6/BSP/BSPCreator.cpp` |
  | `PACK` | `OAT/Common/Utils/Pack.cpp` (same line numbers in `OAT6`) |
  | `PORT` | `RE/shared/notes/bo1_to_bo2_porting.md` |
  | `TECH` | `RE/games/t6-bo2/notes/t6_techniques.md` |
  | `SPEC` | an internal T6 GfxWorld FBX dumper spec in the converter project (not published) |

  `D6` lives only in CoD-RE (the T6 oatfork). The `RE/shared/oat-patches/oat_ext` copies of `D4`/`D5` are the same
  length as the vendored ones; `D5` is byte-identical (`diff -q` clean).

- **Status tags.** **[V]** read in the source at `file:line`. **[V-calc]** computed from a header (32-bit pointers).
  **[M]** measured in a real dump (`AUDIT/`). **[I]** inferred. **[!]** sources disagree, or a trap.
- Read fields **by name** from OAT's native structs. Offsets only matter for raw memory work.

---

## 0. Where things hang, per game

| | T4 (WaW) | T5 (BO1) | T6 (BO2) |
|---|---|---|---|
| Vertex buffer | `GfxWorld.vd.vertices` (`GfxWorldVertex*`), count `GfxWorld.vertexCount` | `GfxWorld.draw.vd.vertices`, count `draw.vertexCount` | `GfxWorld.draw.vd0.data` (bytes), size `draw.vertexDataSize0` |
| Index buffer | `GfxWorld.indices` (u16), `GfxWorld.indexCount` | `draw.indices`, `draw.indexCount` | `draw.indices`, `draw.indexCount` |
| Layer stream | `GfxWorld.vld.data`, `vertexLayerDataSize` | `draw.vld.data`, `draw.vertexLayerDataSize` | `draw.vd1.data`, `draw.vertexDataSize1` |
| Surfaces | `GfxWorld.dpvs.surfaces[surfaceCount]` | same | same |
| Static models | `dpvs.smodelDrawInsts[dpvs.smodelCount]` | same | same |
| Lightmaps | `GfxWorld.lightmaps[lightmapCount]` | `draw.lightmaps[draw.lightmapCount]` | `draw.lightmaps[draw.lightmapCount]` |
| Reflection probes | `GfxWorld.reflectionProbes[reflectionProbeCount]` | `draw.reflectionProbes[...]` | `draw.reflectionProbes[...]` |
| Brush models | `GfxWorld.models[modelCount]` | same | same |
| Sky | `skySurfCount`, `skyStartSurfs`, `skyImage`, `skyBoxModel` | same | only `skyBoxModel` (+ surface flag 0x4) |

**[!] T4 has no `GfxWorldDraw`.** Vertices, indices, lightmaps and probes sit directly in `GfxWorld`
(`T4H:2673-2741`; `D4:108-127,178`). T5 groups them into `GfxWorldDraw draw` (`T5H:2907-2925`, `GfxWorld.draw`
`T5H:3239`; `D5:483,491-510,574`). T6 keeps `draw`, but swaps the vertex array for two byte streams
(`T6H:1219-1251`). **[V]**

---

## 1. World geometry

### 1.1 Vertex layout

**T4 and T5: `GfxWorldVertex`, 44 bytes** (`T4H:2276-2285`, `T5H:2884-2893`) **[V]**, size `RE/shared/probe/sizes.txt:20` **[V]**

| Off | Field | Type | Decode |
|---|---|---|---|
| 0 | `xyz` | float[3] | world position, game units |
| 12 | `binormalSign` | float | ±1; binormal = sign · cross(normal, tangent) (`CONV/fbx.py:135-139`) **[V]** |
| 16 | `color` | `GfxColor` u32 | D3DCOLOR 0xAARRGGBB, bytes in memory B,G,R,A (`CONV/world.py:155-159`) **[V]** |
| 20 | `texCoord` | float[2] | UV0, D3D convention (v = 0 at the top) **[I]**, see 5.4 |
| 28 | `lmapCoord` | float[2] | lightmap UV in the page of `surface.lightmapIndex` |
| 36 | `normal` | `PackedUnitVec` u32 | "scale based", below |
| 40 | `tangent` | `PackedUnitVec` u32 | same |

Note the in-memory order (binormalSign at 12) differs from the order the dumpers write it out (`D4:119-125`).

Scale-based unit vector (`PACK:127-136`, `CONV/world.py:162-169`) **[V]**: bytes `b0 b1 b2 b3` (little-endian):
`s = (b3 + 192) / 32385; v = ((b0-127)·s, (b1-127)·s, (b2-127)·s)`, then normalise (the converter does; OAT does not).

T5 uses the same reader as T4 in the converter (`D5:499-509` writes the raw u32s into the WaW format; Kino rendered
correctly in game per the user's notes) **[I]**: treat T5 colour and normals exactly like T4.

**T6: `GfxPackedWorldVertex`, 36 bytes in `vd0`** (`OAT6/Common/Game/T6/T6_Assets.h:5773-5782`; `static_assert`
in `D6:27`) **[V]**

| Off | Field | Type | DXGI (`TECH:173,176`) | Decode |
|---|---|---|---|---|
| 0 | `xyz` | float[3] | R32G32B32A32_FLOAT, w = binormalSign | world position |
| 12 | `binormalSign` | float | (w of the above) | ±1 |
| 16 | `color` | u32 | R8G8B8A8_UNORM | **R in the low byte** (`PACK:153-159`; `D6:83-91`) |
| 20 | `texCoord` | u32 | R16G16_FLOAT | u = half(low 16), v = half(high 16) (`PACK:109-116`; `D6:197`) |
| 24 | `normal` | u32 | R10G10B10A2 | "third based", below (`PACK:138-151`; `D6:205`) |
| 28 | `tangent` | u32 | R10G10B10A2 | same |
| 32 | `lmapCoord` | u32 | R16G16_UNORM | u = (p & 0xFFFF)/65535, v = (p >> 16)/65535 (`D6:198-200`; `GWL:253-260`) |

Third-based unit vector (`PACK:138-151`) **[V]**: three 10-bit fields at bits 0, 10, 20; the top 2 bits are unused.
Each field is a two's-complement 10-bit integer `n` and the value is `n / 511` **[V-calc]**: OAT's bit trick
`(float_bits(0x40400000 + n - 2·(n & 0x200)) - 3.0) · 8208.0312` is `n·2^-22·8208.03 = n/511`.

**[!] `GfxPackedWorldVertex` is not in the vendored `OAT/` T6 header.** `OAT/Common/Game/T6/T6_Assets.h` only has
`GfxWorldVertexData0 { byte128* data; void* vb; }` (`T6H:1219-1223`); the struct is in `OAT6` only. E115 must declare
the 36-byte layout itself.

**[!] `TECH:173` calls the normal "R10G10B10A2_UNORM"** (the input-layout format) while OAT decodes it as signed.
Not a real conflict: the shader decodes the UNORM bits itself (`TECH:197-198`). On the CPU, use OAT's decode.

**[!] `SPEC:52` says to "pass the stored u32 unchanged"** for T6 normals. The shipped dumper does not. It re-encodes
the T6 10:10:10 value into the WaW scale-based format (`D6:67-81`). Trust `D6`.

**Layer streams (blend materials).** T4/T5 `vld` holds the extra layers' UVs and normal transforms at byte offset
`tris.vertexLayerData`, with a per-format stride (`CONV/world.py:109-123`). T6 `vd1` is at `tris.vertexDataOffset1`
in the `PACKED_WORLD_T*N*` layouts (`TECH:177-185`). For a first pass, draw only the base layer, as the converter
does (`CONV/t6bridge.py`, "layered materials drawn as their base layer"). **[V]**

### 1.2 Surfaces (`GfxSurface`)

| Field | T4 (`T4H:2588-2606`) | T5 (`T5H:3067-3089`) | T6 (`T6H:3901-3923`) |
|---|---|---|---|
| `tris.firstVertex` | int: base vertex | int: base vertex | int: **not usable in stock maps** (below) |
| `tris.vertexCount` | u16 | u16 | u16, **often 0** |
| `tris.triCount` | u16 | u16 | u16 |
| `tris.baseIndex` | int: first index | int | int |
| `tris.vertexLayerData` | int, byte offset into `vld` | int | - |
| `tris.vertexDataOffset0/1` | - | - | int, **byte** offsets into `vd0` / `vd1` |
| `tris.mins/maxs` | - | float[3] each | vec3 each |
| `tris.himipRadius*` | - | `himipRadiusSq` | `himipRadiusInvSq` |
| `material` | `Material*` (ASSETS 5) | same | same |
| `lightmapIndex` | char | char | char |
| `reflectionProbeIndex` | char | char | char |
| `primaryLightIndex` | char | char | char |
| `flags` | char | char | char |
| `bounds[2]` | float[2][3] | float[2][3] | vec3[2] |
| Size | 52 **[V-calc]** | 80 **[V-calc]** (`type_align32(16)`) | 80 (`sizes.txt:21`) **[V]** |

All indices are **u16 in every game** (`T4H:2680`, `T5H:2924`, `T6H:1246`). **[V]**

T6 surface flags (`OAT6/Common/Game/T6/T6_Assets.h:3913-3919`) **[V]**: 0x1 CASTS_SUN_SHADOW, 0x2
HAS_PRIMARY_LIGHT_CONFLICT, **0x4 IS_SKY**, **0x8 NO_DRAW**, 0x10 CASTS_SHADOW, 0x20 QUANTIZED, 0x40 NO_COLOR. T5
shares the low bits (`U5:36-39,495-506`) **[V]**. T4 is assumed to match **[I]**.

### 1.3 Triangles of one surface

**T4** (`CONV/world.py:204-206` checks this; `CONV/fbx.py:115-118` uses it) **[V]**

```
for k in 0 .. triCount*3-1:
    v = world.vd.vertices[ tris.firstVertex + world.indices[tris.baseIndex + k] ]
```

Indices are local to the surface. The reader enforces `max(local) < vertexCount`. `firstVertex..+vertexCount` can be
a large, sparse span, so compact to the referenced vertices (`CONV/fbx.py:108-111`). **[V]**

**T5**: the same, through `draw` (`U5:975-994`) **[V]**:
`v = draw.vd.vertices[tris.firstVertex + draw.indices[tris.baseIndex + k]]`. `U5` skips surfaces with
`triCount == 0 || vertexCount == 0` or an out-of-range span (`U5:973-981`).

**T6** (`D6:139-162,190-209`) **[V]**

```
base = (uint8_t*)draw.vd0.data + tris.vertexDataOffset0      // byte offset
for k in 0 .. triCount*3-1:
    i = draw.indices[tris.baseIndex + k]                       // local to the block
    v = *(GfxPackedWorldVertex*)(base + i*36)
```

- Blocks are padded to 16 bytes. **[M]** Stock nuked surface 0 has 17 vertices at offset 0; surface 1 starts at
  offset 624 = 612 padded (`AUDIT/zm_nuked.d3dbsp.gfxworld.txt:9-10`). Overall stride is 36.01
  (`...gfxworld.txt:6`).
- Surfaces **share blocks**, and `vertexCount` is usually 0. Size a block by the highest index any surface uses
  (`D6:139-162`). **[V]**
- **[!] `firstVertex` vs `vertexDataOffset0`.** OAT's own T6 linker writes `vertexDataOffset0 = firstVertex·36`
  (`GWL:360,403`). Stock maps do not. Nuked surface 0 has `firstVertex 193928`, `off0 0`, and surface 1 has
  `firstVertex 186518`, `off0 624` (`AUDIT`, as above). **[M]** So always address through `vertexDataOffset0`.
- Bounds: `GWL:382-390` computes them by walking these exact indices from `vd0 + vertexDataOffset0`. That confirms
  the recipe. **[V]**

### 1.4 How the dumpers export it (for cross-checking E115's reader)

| Step | T4 | T5 | T6 |
|---|---|---|---|
| Vertices | `D4:116-126` | `D5:499-509` | `D6:190-209` (per block, re-encoded) |
| Indices | `D4:127` | `D5:510` | `D6:210` |
| Surfaces | `D4:129-143` | `D5:512-526` (layered names -> `generated/_<id>`, `D5:49-62`) | `D6:212-227` (writes `block.first` as firstVertex) |
| Static models | `D4:145-155` | `D5:528-538` | `D6:229-239` |
| Brush models | `D4:190-195` | `D5:587-592` | `D6:242-247` |
| Python reader | `CONV/world.py:172-262` | same | same |

**[!] `SPEC:60` says strings are NUL-terminated.** The real format is a u32 length followed by bytes (`D4:37-47`,
`CONV/world.py:30-34`).

### 1.5 Brush models (doors, debris, movers)

`GfxWorld.models[i]` = `GfxBrushModel {writable, bounds[2][3], surfaceCount, startSurfIndex}` (`T4H:2462-2468`,
`T5H:2965-2971`). Model 0 is the world. Model N is the render part of the `"model" "*N"` entity. **[V]**
`dpvs.staticSurfaceCount` = the world's surfaces, and brush-model surfaces follow them (`GWL:481,1051-1052`) **[V]**.
Stock nuked: 9867 surfaces, `staticSurfaceCount 9865`. Every brush model has 0 surfaces and
`startSurfIndex 0xFFFFFFFF` (`AUDIT/...gfxworld.txt:6-60`) **[M]**. Skip a model when `surfaceCount == 0`.
Whether brush-model surfaces are stored in world space or relative to the entity origin is **unverified**. See §8.

---

## 2. Static models (`GfxStaticModelDrawInst`)

| Off | T4 (`T4H:2566-2579`) | T5 (`T5H:3106-3116`) | T6 (`T6H:3946-3961`) |
|---|---|---|---|
| 0 | `cullDist` f32 | `cullDist` | `cullDist` |
| 4 | `placement` (52 B) | `placement` | `placement` |
| 56 | `model` `XModel*` | `model` | `model` |
| 60 | `lodFade` u32 | `flags` int | `flags` int |
| 64 | `cachedLightSettingIndex` | `smodelCacheIndex` u16[4] | `invScaleSq` f32 |
| 68 | `field_44, field_45` (2 chars), `reflectionProbeIndex` u8, `primaryLightIndex` u8 | (cont.) | `lightingHandle` u16, `colorsIndex` u16 |
| 72 | `flags` int | `lightingHandle` u16, `reflectionProbeIndex`, `primaryLightIndex` | `lightingSH` (`GfxLightingSHQuantized`, 3×u16[4] = 24 B) |
| 76 | `smodelCacheIndex` u32[4] | end | -> 96: `primaryLightIndex`, `visibility`, `reflectionProbeIndex`, pad |
| 100 | | | `smid` u32 |
| 104 | | | `lmapVertexInfo[4]` (4 × 12 B: `lmapVertexColors*`, `VB*`, `numLmapVertexColors` u16 + pad) |
| Size | **92** **[V-calc]** | **76** (`sizes.txt:22`) **[V]** | **152** (`sizes.txt:22`) **[V]** |

**Placement** (`GfxPackedPlacement`, `T4H:2554-2559`, `T5H:3099-3104`, `T6H:3925-3930`): `origin` float[3],
`axis[3][3]`, `scale` float. The game transforms a model-space point as
`world = origin + scale · (lx·axis[0] + ly·axis[1] + lz·axis[2])` (`GWL:571-580`) **[V]**. So `axis[i]` is the
world-space direction of model axis i (X forward, Y left, Z up), and the 4×4 has columns
`(s·axis[0], s·axis[1], s·axis[2], origin)`. `U5:1130-1135` reads `axis` as a rotation plus a uniform `scale`.
**[V]** The axes are unit length **[I]**: the scale is held separately, and T6 adds `invScaleSq = 1/scale²` (by name).

**T5 -> T6 changes** (`PORT:136`) **[V]**:
- `smodelCacheIndex` is removed.
- Added: `invScaleSq`, `colorsIndex`, the quantised `lightingSH`, `visibility`, `smid` (= index; `GWL:566`), and
  `lmapVertexInfo[4]` (baked per-vertex lightmap colours per LOD).
- `reflectionProbeIndex` and `primaryLightIndex` move after the SH.
- Placement and `model` keep their offsets.

T4 differs from T5 by `lodFade`, `cachedLightSettingIndex` and a u32 (not u16) cache array.

The parallel `dpvs.smodelInsts[i]` holds world bounds (T5/T6 also hold `lightingOrigin`; T4 holds `groundLighting`, a
`GfxColor`) (`T4H:2581-2586`, `T5H:3059-3065`, `T6H:3894-3899`) **[V]**. To draw a static model: transform LOD 0 of
`model` (ASSETS 1-3) by the matrix above. `cullDist` is in game units; ignore it at first.

---

## 3. Lighting

### 3.1 Lightmap pages

| | T4 | T5 | T6 |
|---|---|---|---|
| Array | `GfxLightmapArray {primary, secondary}` (`T4H:2421-2425`) | `{primary, secondary, secondaryB}` (`T5H:2877-2882`) | `{primary, secondary}` (`T6H:3754-3758`) |
| `lmapCoord` | float2 | float2 | unorm16 ×2 |
| Per surface | `lightmapIndex` | same | same |

- **Unlit sentinel.** The converter treats `lightmapIndex >= lightmapCount` as unlit (`CONV/lightmaps.py:286-287`)
  **[V]**. Stock nuked uses **31**: 82 surfaces, `lightmaps 3` (`AUDIT/...gfxworld.txt:441`) **[M]**.
- Static models are not lightmapped. They use the light grid (`GfxLightGrid`, `T4H:2439`, `T5H:2941`, `T6H:1253`).
  T6 also has per-instance `lightingSH` / `lmapVertexInfo`. Skip all of this at first: use a flat ambient plus the sun.

**T4 page** (`CONV/lightmaps.py:3-15,115-166`) **[V]**:
- `secondary` is W × 2H RGBA8. The top half is colour A, with direction x in alpha. The bottom half is colour B, with
  direction y in alpha. Sample it at (u, v/2) and (u, v/2 + ½).
- `primary` is 2W × 2H L8: sun visibility.
- At a flat normal: `d = alpha · (4.08, 4.0645) + (-2.08, -2.0645)` (`lightmaps.py:62-63`), and
  `light = A + B · (0.6·exp(-|d|²) + 0.4)`.
- WaW works in **gamma** space: final ≈ albedo · light.

**T5 page** (`PORT:322-345`; `CONV/lightmaps.py:23-31`) **[V]**:
- `secondary` is W × 2H R5G6B5 (D3DFMT 23). Halves A and B as in T4. `.x`/`.z` are the red/blue share, and `.y` is
  one direction component, decoded `·4 - 2`.
- `secondaryB` is W × H G16R16 (fmt 34): the brightness of A and B. `s = secondaryB · 31.875`, and
  `colour = s · (4r, 2(1-r-b), 4b)`.
- `primary` (DXT1, `.y`) is sun visibility.
- Same flat-normal combine as T4. The result multiplies `albedo²` and ends `sqrt(sat(hdr · colour))`: **linear**.
- OAT's DX9 image loader cannot decode formats 23/34. Our dumper writes the raw pixels to `.loaddef.bin`
  (`PORT:340-343`). See ASSETS 6.
- **[!] Primary size:** `PORT:328` says 2W × 2H, `CONV/lightmaps.py:28` says 2W × H. Measure it on Kino.

**T6 page** (`CONV/lightmaps.py:9-15`; `AUDIT/...gfxworld.txt:443-457`) **[V]/[M]**:
- `primary` is **null** in stock nuked.
- `secondary` is W × **3H** RGBA8 (DXGI 28): three stacked pages. Nuked page 0 is 2048 × 3072.
  1. ambient: `rgb / (a + 1e-6)`, linear;
  2. directional colour, decoded the same way;
  3. direction `·0.5 + 0.5` in rgb, sun visibility in alpha.
- Final = `sqrt(hdr · (albedo² · lighting + ...))`.

**Recognisable first pass** **[I]**: `albedo × decoded ambient (+ A/B combine for T4/T5)`. Then apply gamma for
T4, or `sqrt` for T5/T6.

### 3.2 Sun and primary lights

- `ComWorld.primaryLights[primaryLightCount]` (`ComPrimaryLight`, `T4H:2058`, `T5H:2446`, `T6H:3439`). Fields
  include `type`, `color`, `dir`, `origin`, `radius` and the cone cosines (`D4:86-90`, `D5:450-471`) **[V]**.
- The sun is `primaryLights[GfxWorld.sunPrimaryLightIndex]`. This is 1 in OAT's linker (`OAT6/.../BSP/BSP.h:84`,
  `GWL:729`) and in nuked (`AUDIT/...gfxworld.txt:1` "grid sun 1") **[V]/[M]**. `surface.primaryLightIndex` names the
  light baked as that surface's primary.
- Sun parameters are in `GfxWorld.sunParse`, and the layout differs per game:
  - T4 (`T4H:2299`): ambientScale, sunColor, angles, ...;
  - T5 (`T5H:2701-2719`): `GfxWorldSunColor` with ambient/sunDiffuse/sky colours and exposure;
  - T6 (`T6H:1168-1201`): `GfxWorldSun` with ambient, `sunCd`, `sunCs`, angles, exposure; plus fog.
- The `worldspawn` entity also carries `sundirection` / `suncolor` (T5 Kino) **[M]**.

### 3.3 Reflection probes

`GfxReflectionProbe` (`T4H:2343`, `T5H:2869`, `T6H:3744`) **[V]**:
- T4: `origin` + `reflectionImage`;
- T5 adds probe volumes;
- T6 adds `lightingSH` and `mipLodBias`.

`surface.reflectionProbeIndex` and the smodel's `reflectionProbeIndex` index the probe array. `GfxCell.reflectionProbes`
lists the probes per cell. The images are cubemaps: nuked has 26 probes, and `*reflection_probe0` is a 4 × 4 cube
with `mapType 5`, DXGI 77 (`AUDIT/...gfxworld.txt:6,458`) **[M]**. They are optional for a first pass.

---

## 4. Visibility and what not to draw

### 4.1 DPVS in brief

- **Cells.** `GfxWorld.dpvsPlanes.cellCount` cells in `GfxWorld.cells` (`T4H:2357,2407`, `T5H:2800,2850`, `T6H:3725`).
  Each `GfxCell` has bounds, an `aabbTree[aabbTreeCount]`, `portals[portalCount]` and a reflection probe list.
  T4/T5 also have `cullGroups`.
- **AABB tree nodes** (`GfxAabbTree`, `T4H:2395`, `T6H:6412`):
  - `startSurfIndex` / `surfaceCount` are a contiguous range of `dpvs.sortedSurfIndex` that covers the node's whole
    subtree;
  - `smodelIndexes` lists the subtree's static models;
  - `childrenOffset` is a **byte** offset to the first of the contiguous children (`GWL:26-32`, "verified against
    zm_nuked").
- **Portals** (`GfxPortal`, `T4H:2385`): a plane, a polygon `vertices[vertexCount]` and the cell they lead to.
- **Surface ranges in `GfxWorldDpvsStatic`**:

  | Game | Ranges | Source |
  |---|---|---|
  | T4/T5 | lit, decal, emissive | `T4H:2617`, `T5H:3118` |
  | T6 | lit, litTrans, emissiveOpaque, emissiveTrans | `T6H:1300-1311` |

  Nuked's values: lit 0-8865, litTrans 8865-9785, emissiveOpaque 9785-9796, emissiveTrans 9796-9865
  (`AUDIT/...gfxworld.txt:7`) **[M]**.
- **Clipmap PVS.** `clipMap_t.numClusters/visibility` is the collision PVS. Nuked has 1 cluster
  (`AUDIT/zm_nuked.d3dbsp.clipmap.txt:2`) **[M]**.

**Drawing every surface is fine for a first version** **[I]**:
- OAT's own T6 linker ships maps with one cell, no portals and an all-visible PVS. Linked maps load (user notes on the
  BSP linker; see also `GWL:26-32`).
- Stock nuked is 9.9 k surfaces, 195 k vertices and 399 k indices (`AUDIT/...gfxworld.txt:6`). That is small for a
  modern GPU. Batch by (material, lightmap page).
- What matters is **order**: opaque ranges first, then the decal/translucent ranges with blending. Drawing decals and
  glass in the opaque pass is wrong (`GWL:420-424`).

### 4.2 Surfaces and materials to skip

| What | How to detect it | Source |
|---|---|---|
| Sky surfaces | T4/T5: the indices listed in `skyStartSurfs[skySurfCount]` (`T4H:2683-2684`, `T5H:3214-3215`); techset `wc_sky` (`CONV/t6bridge.py:1284`); flag 0x4; `U5:501` also matches "sky" in the techset or material name | **[V]** |
| Skybox | Not a surface. Draw the XModel named by `GfxWorld.skyBoxModel` (or the worldspawn key `skyboxmodel`) around the camera | **[V]** names; **[I]** drawing |
| Editor/tool surfaces | techset `wc_tools` (`CONV/t6bridge.py:1285`, `U5:1021-1025`) | **[V]** |
| No-draw helpers | flag 0x8. Stock nuked `wpc/caulk_shadow_primary` uses techset `wpc_shadowcaster_*` with flags 0x19 and lmap 31 (`AUDIT/...gfxworld.txt`, surf 9786) | **[M]** |
| Shadow-caster-only | `shadowcaster` techsets; the converter keeps them out of colour passes (`CONV/t6bridge.py:1411-1412`, `CONV/fbx.py:154`) | **[V]** |
| Caulk, clip, hint, portal | Normally compiled out of the GfxWorld. In the clipmap they show up as clip materials (nuked material 0 is `light_demote_hint`, cflags 0x8000000; `AUDIT/...clipmap.txt:3`). Filter collision by contents, not by name | **[M]**; **[I]** |
| Empty brush models | `models[i].surfaceCount == 0` | **[M]** |

---

## 5. Coordinates

### 5.1 The CoD frame

- **Units: 1 unit = 1 inch** **[I]**. CoD-RE writes "COD world units (inches) 1:1, Z-up"
  (`RE/games/t8-bo4/notes/EMITTER_SPEC.md:11`) and converts Havok metres with ×39.37
  (`RE/games/t8-bo4/tools/navmesh_extract.py:12`). Those are T7/T8 notes; T4-T6 share the engine family.
- **Axes: Z up, +X forward at yaw 0, +Y left, right-handed.** `AnglesToAxis` (`OAT6/.../BSP/BSPUtil.cpp:89-112`)
  **[V]** gives:
  - `axis[0] = (cp·cy, cp·sy, -sp)`: forward; positive pitch looks down;
  - `axis[1]`: left;
  - `axis[2]`: up.

  Yaw turns X towards Y about +Z.
- **Entity angles** are degrees `"pitch yaw roll"` (`x, y, z` above) **[V]**.

### 5.2 What the converters do

| Tool | Transform | Source |
|---|---|---|
| B2W world FBX | position `(x, z, -y)`; normals/tangents too; FBX Y-up, `UnitScaleFactor 1` | `CONV/fbx.py:104,130-132` **[V]** |
| OAT T6 BSP linker | inverse: `BO2 = (x, -z, y)` | `OAT6/.../BSP/BSPUtil.cpp:17-24` **[V]** |
| T5 BSP unlinker | `(x, z, -y)`; quaternion `(qx, qz, -qy, qw)` | `U5:57-72` **[V]** |

- **The "×100" in the user's notes is an FBX/ufbx artefact, not a unit change.** The linker divides node
  translation/scale by 100 because ufbx stores them ×100 (`BSPC:52-60`) **[V]**. Vertex positions stay 1:1 game units;
  "OAT waw2bo2 glbs are 1:1 COD inches (NO x100 scale)" (`RE/games/t8-bo4/tools/smodel_lib.py:5`) **[V]**.
- **[!] `U5` calls its transform `LhcToRhc`.** But `(x, y, z) -> (x, z, -y)` has determinant +1. It is a rotation,
  so handedness is unchanged **[V-calc]**. CoD world space is already right-handed. Only the up axis changes.
- **Winding.** CoD front faces are the **reverse** of the FBX/OpenGL counter-clockwise rule:
  - the linker flips every FBX triangle when writing BO2 indices (`BSPC:267-273`);
  - the converter pre-reverses so that they survive ("WaW triangles already use BO2's winding",
    `CONV/fbx.py:146-152`);
  - `U5` reverses when it exports (`U5:195-198,991-994`). **[V]**

  So, in a right-handed frame, stored triangles are **clockwise when seen from the front**. Collision agrees:
  walkable floors have a −Z right-hand normal (user notes on the BSP linker, offline-verified) **[I]**.
- **UVs.** The converter writes FBX `v' = 1 - v` (`CONV/fbx.py:144-145`) and the linker undoes it (`BSPC:153-164`)
  **[V]**. So the stored UVs follow the D3D top-left convention **[I]**.

### 5.3 What E115 should apply (Y-up, right-handed, metres)

```
p_E = 0.0254 * ( x, z, -y )          // positions (and placement origins)
n_E =          ( x, z, -y )          // normals, tangents, axis vectors (no scale)
tri_E = (i0, i2, i1)                 // only if E115 uses CCW front faces (GL/Vulkan default): reverse once
```

- The matrix is `M = 0.0254 · [[1,0,0],[0,0,1],[0,-1,0]]`, a proper rotation times a scale.
- Static model world matrix = `M · [s·axis0 | s·axis1 | s·axis2 | origin]`. The XModel's own vertices are also Z-up
  inches, so they stay in model space inside that matrix (ASSETS 3).
- This matches the converter, so E115 coordinates line up with B2W and FBX outputs, just ×0.0254. **[I]**
- Keep the binormal sign as-is: a proper rotation preserves cross products (`CONV/fbx.py:135-137`) **[V]**.
- Sample UVs unchanged with D3D/Vulkan conventions. Flip v only for OpenGL-style uploads **[I]**.

---

## 6. `clipMap_t` (collision)

### 6.1 Layout: T4/T5 inline vs T6 `ClipInfo`

| Data | T4 (`T4H:1996-2049`) | T5 (`T5H:2384-2444`) | T6 (`T6H:1021-1106`) |
|---|---|---|---|
| planes | `clip.planeCount/planes` | same | `clip.info.planeCount/planes` |
| materials | `numMaterials`, `dmaterial_t {char material[64]; surfaceFlags; contentFlags}` (`T4H:1821`) | same (`T5H:2130`) | `info.materials`, `ClipMaterial {const char* name; surfaceFlags; contentFlags}` (`T6H:3200`) |
| brush sides | `numBrushSides/brushsides` | same | `info.` |
| leaf-brush nodes, leafbrushes | inline | inline | `info.` |
| brushVerts, uinds | inline | inline | `info.` |
| brushes | `u16 numBrushes; cbrush_t*` | same | `info.numBrushes`, `cbrush_array_t*` (128-aligned typedef, `T6H:1018`) + **new** `brushBounds`, `brushContents` |
| nodes, leafs, verts, triIndices, triEdgeIsWalkable, partitions, aabbTrees, cmodels, visibility, mapEnts, dynEnts, constraints | inline | inline (+ ropes) | inline (+ ropes) |
| `triIndices` | `u16*`, 3 per tri | `u16*`, 3 per tri | `u16 (*)[3]` (same data) |
| `leafsurfaces`, `borders` | yes | yes | removed |

Source for the T5 -> T6 move: `PORT:146-153,174-179` **[V]**.

**[!]** `PORT:176` says `pInfo` points at `info`. In the loaded stock nuked clipmap, `pInfo`, `cmodel0.info`,
`cmodel1.info`, `brushBounds` and `brushContents` are **all null** (`AUDIT/zm_nuked.d3dbsp.clipmap.txt:9-10`) **[M]**.
Always read `clip->info` directly, as `D6` does (`D6:299`). Don't rely on those pointers.

Nuked's counts **[M]** (`...clipmap.txt:1-2`):

| planes | materials | brushes | brush sides | collision verts | collision tris | partitions | aabb nodes | leafs | submodels | static models |
|---|---|---|---|---|---|---|---|---|---|---|
| 14 905 | 766 | 7 620 | 33 971 | 15 864 | 24 502 | 6 866 | 17 474 | 1 977 | 140 | 1 349 |

### 6.2 Brushes

`cbrush_t` (`T4H:1914`, `T5H:2223`, `T6H:3240`, 96 B in T6, `sizes.txt:39`) **[V]** has these fields:
- `mins`, `contents`, `maxs`, `numsides`, `sides`;
- the axial side flags: T4 `axialMaterialNum[2][3]` (a material index); T5/T6 `axial_cflags[2][3]` and
  `axial_sflags[2][3]`, where `[0]` is the min side and `[1]` the max side (`D6:336-346`);
- `numverts`, `verts` (the brush's corner points).

Each side (`cbrushside_t`, `T4H:501`, `T5H:621`, `T6H:3207`) has a `cplane_s* plane` (normal, dist). T4 adds
`materialNum`; T5/T6 add `cflags, sflags`. The full plane set is the 6 axial planes, in the order
−x, +x, −y, +y, −z, +z with `dist = -mins / +maxs`, followed by `sides[0..numsides)`
(`D4:319-333`, `D5:211-225`, `D6:337-353`) **[V]**.

**Brush -> triangles.** Take the convex hull of `brush.verts`. If `numverts == 0`, take the 8 corners of
`mins/maxs`. Skip brushes with fewer than 4 points (QuickHull, `U5:259-300`) **[V]**. The alternative is clipping
large quads by the planes **[I]**.

**Which brushes belong to the world.** Walk the leaf-brush node tree from every world leaf (`cLeaf.leafBrushNode`) (`D4:339-385`, `D6:93-122`) **[V]**:
- a node with `leafBrushCount > 0` is a leaf and lists its `data.leaf.brushes`;
- a node with `leafBrushCount < 0` also has a shared subtree at `index + 1`;
- children are at `index + childOffset[k]` (offset 0 = none).

The brush entity `*N` owns what `cmodels[N].leaf` reaches.

- **[!] T6 world leafs also reach brush-model brushes.** `D6` subtracts them from cmodel 0 (`D6:403-414`). `D4`/`D5`
  don't. Do the subtraction in every game; it costs nothing **[I]**.
- **Effective contents.** AND the leaf `brushContents` with every node's `contents` along the path, then AND with the
  brush's `contents` (`D4:476-514`) **[V]**.

### 6.3 Terrain triangle soup (partitions / aabb tree)

- `clip.verts[vertCount]`, plus `triIndices` with `triCount` triangles (`D4:307-310`, `D6:374-377`) **[V]**.
- `CollisionAabbTree` (`T4H:1897`, `T5H:2206`, `T6H:3295`; 32 B) has `origin`, `materialIndex`, `childCount`,
  `halfSize`, and a union `u {firstChildIndex | partitionIndex}`. A node with `childCount == 0` is a leaf:
  `partitions[u.partitionIndex]` (`D4:420-436`) **[V]**. The children of an inner node are
  `[firstChildIndex, +childCount)` **[I]**.
- `CollisionPartition` (`T4H:1881`, `T5H:2190`, `T6H:3281`) has `triCount`, `firstTri`, `nuinds`, `fuind`; T4/T5 also
  have `borderCount` and `borders`. The triangles are `triIndices[(firstTri + k)*3 + c]`, `k < triCount`
  (`U5:166-180`) **[V]**.
  - **[!]** `triCount` is `unsigned char` in T4 but `char` (signed) in T5/T6. Cast it to u8, as all dumpers do
    (`D5:315`, `D6:463`).
- **Roots.** World leafs give `[firstCollAabbIndex, +collAabbCount)`, and each cmodel has its own leaf for moving
  terrain (`D4:516-524`) **[V]**.
- **Per-triangle material** = the leaf node's `materialIndex` (`D4:420-436`).
- **Effective contents.** A trace tests every node's material on the way down, so a triangle collides only if all of
  them pass (`D4:451-454`) **[V]**.
- **[!] Not all of it is solid.** Decals and other contents-0 surfaces share the soup (`D4:420-422`). On one measured
  WaW map only 51 % of the triangles were solid; the rest were missile/shot clip (0x2080), player/monster clip or
  glass (`CONV/fbx.py`, `collision_material_slots` docstring) **[V]**.
- **Walkable edges.** `triEdgeIsWalkable` holds bit `3t + e` for each edge; the size is
  `(3·triCount + 31)/32·4` bytes (`D4:440-449`) **[V]**.

### 6.4 Static-model collision

- `clip.staticModelList[numStaticModels]` (`cStaticModel_s`, `T4H:1811`, `T5H:2120`, `T6H:3264`; T6 adds `contents`)
  has `xmodel`, `origin`, `invScaledAxis[3][3]`, `absmin` and `absmax` **[V]**.
- World -> model: `local = transpose(invScaledAxis) · (p − origin)`. So `p = origin + inverse(transpose(A)) · local`.
  The rows of `invScaledAxis` are `axis/scale` (`CONV/hulls.py:62-75`, `U5:604-624`) **[V]**.
- The triangles are in the XModel's `collSurfs[].collTris[]`: a `plane` (n, d), `svec` and `tvec` (float4 each);
  ASSETS 1.3. Rebuild the corners by solving `n·p = d`, `svec·p − svec.w = s`, `tvec·p − tvec.w = t` at
  (s, t) = (0,0), (1,0), (0,1) (`CONV/hulls.py:46-59`) **[V]**.

### 6.5 Recipe: one collision triangle soup

1. **Terrain.**
   - For each world leaf, walk its aabb roots.
   - At each partition leaf, emit its triangles. Keep a triangle if `materials[materialIndex].contentFlags` (ANDed
     along the path) intersects the mask (start with `CONTENTS_SOLID 0x1`, `CONV/oneway.py:14`; the WaW player mask is
     `0x281C011`, `oneway.py:13`).
   - Drop water-only triangles (`0x20`, `CONV/fbx.py:231-237`).
2. **Brushes.** Make a hull for each world-owned brush whose effective contents pass the mask.
3. **Static models.** Transform the reconstructed `collTris` of `staticModelList[i]` (6.4).
4. **Brush entities.** Per `*N`: the cmodel's brushes and terrain roots, placed at the entity's origin (see §8).
5. Apply the §5.3 transform. Winding: stored triangles are one-sided with T6/T4 front = clockwise in RH. Use
   two-sided collision until that is checked in E115.

- **[!] Content bits can differ between games.** Verify them on a known T6 brush (`PORT:223`). Nuked: `cflags 0x1` on
  solid wall materials, and 0x0 on `decal_wall_fillet` (`AUDIT/...clipmap.txt:4-8`) **[M]**.
- **T6 limit.** The OAT T6 linker caps collision at 65 535 welded vertices. That only matters when writing T6, not for
  E115 (user notes).

---

## 7. mapents

### 7.1 Format

- `MapEnts {name, entityString, numEntityChars}` (`T4H:2269-2274`, `T5H:2676`). T6 adds `MapTriggers trigger`, the
  trigger models, hulls and slabs (`T6H:1142-1157`) **[V]**.
- `numEntityChars` **includes the trailing NUL** (`OAT6/ObjWriting/Game/T6/Maps/MapEntsDumperT6.cpp:751` writes
  `numEntityChars - 1`) **[V]**.
- The text is a sequence of `{ ... }` blocks, each with `"key" "value"` lines. The first block is `worldspawn`
  (nuked/Kino `.ents` heads) **[M]**.
- The converter parses it with `\{([^{}]*)\}` and `"([^"]*)"\s+"([^"]*)"` (`CONV/entities.py:23-24,39-40`) **[V]**.
  No escape sequences appear **[I]**.

| Key | Format |
|---|---|
| `origin` | `"x y z"`, game units |
| `angles` | `"pitch yaw roll"`, degrees. Axis via §5.1 |
| `angle` | yaw only. −1 = up (pitch −90), −2 = down (pitch 90) (`CONV/entities.py:80-87`) |
| `model` | an XModel name, or `*N` = brush model N (clip `cmodels[N]`, gfx `models[N]`) |
| `targetname`, `target`, `script_noteworthy`, `script_string`, `script_int`, `spawnflags` | script linkage |

### 7.2 Classnames that matter

| Class | T4 | T5 (Kino) **[M]** | T6 (nuked) **[M]** | Use |
|---|---|---|---|---|
| `worldspawn` | 1 | 1 (`skyboxmodel skybox_zombie_theater`, `sundirection`, `suncolor`) | 1 (`skyboxmodel skybox_dlc0_zm_nuketown`, `lutmaterial`) | sky, sun |
| `info_player_start` | yes **[I]** | 1, at `-1 -1379 128` (`PORT:91`) | 1, at `0 -376 -28`, angles `0 90 0` | **camera start** |
| `script_struct` `targetname initial_spawn_points` | ? | 4 (`PORT:92`) | 6 (`script_noteworthy initial_spawn`) | co-op starts (preferred over `info_player_start`, `CONV/entities.py:222-224`) |
| zombie spawners | `actor_zombie_*` (`CONV/entities.py:175`, "WaW zombie spawner classes") **[V]** | `actor_zombie_ger_zombie` 28, `actor_zombie_quad` 21, `actor_zombie_dog` 1 | `actor_zm_nuked_basic_01/_02(_beyes)`, `actor_zm_nuked_dog` (1 each); positions are `script_struct` with `script_noteworthy riser_location / dog_location / spawn_location`, grouped by `targetname *_zone_spawners` | markers |
| `script_model` | yes | 108 | 169 | draw `model` at `origin`/`angles` (ASSETS 1) |
| `script_brushmodel`, `trigger_*`, `info_volume` | yes | 275 / 145 / 24 | 74 / 51 / 12 | `*N` brush geometry; triggers invisible |
| `mp_global_intermission`, `info_intermission` | | | 1 / 1 | optional camera |
| `light` | | 36 | 12 | ignore (baked) |
| `node_*` | | 1460 + 108 | 703 + 186 | AI paths. Ignore (also in gameworld) |

- **MP spawn classes** (`mp_dm_spawn`, `mp_tdm_spawn*`, ...) are not in these ZM maps. The bridge generates them from
  `spawns.json` (`CONV/entities.py:284-290`). Expect those names in MP fastfiles **[I]**.
- **`misc_model` entities are compiled into GfxWorld static models** and are not in the entity string **[I]**. Kino
  keeps one typo'd `misc_modle` **[M]**.

---

## 8. Open questions to settle against the three test zones

1. **Brush-model render space.** Are `models[N]` surfaces (for example the 275 on Kino) in world space at their
   compile position, or relative to the entity origin? Clip brushes for `*N` are relative to the origin
   (`CONV/entities.py:298-309`) **[I]**. Check by comparing `models[N].bounds` with the entity `origin`.
2. **T4 surface flags.** Is 0x4 sky / 0x8 no-draw the same in WaW? Check `skyStartSurfs` against `flags & 4` on
   `nazi_zombie_prototype`.
3. **T6 `firstVertex`.** Confirm on `zm_nuked` that `vertexDataOffset0` blocks cover every index and that
   `firstVertex` is unrelated (2 samples so far).
4. **T5 primary lightmap size** (2W × 2H or 2W × H, §3.1).
5. **Unlit sentinel in T4/T5.** Is it 31, or any value ≥ `lightmapCount`?
6. **AABB child range.** Is `firstChildIndex` an absolute node index (assumed) or relative?
7. **Winding in E115.** Draw one wall with culling on and confirm "clockwise front in RH" (§5.2) before turning on
   collision one-sidedness.
