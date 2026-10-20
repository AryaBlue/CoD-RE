# T6 (BO2) techniques, vertex formats and shader arguments

How BO2 picks the technique (shader pass) for each draw, the exact vertex input formats it feeds shaders, and how
BO1/WaW techniques line up with T6 ones.

**Sources**
- **Names, call order, tables:** the server build `CoDMPServer_PC.exe` + `.map` + `.pdb` from the game's `pc pdb`
  folder. Functions were decompiled with Ghidra 12 headless.
- **Data tables** were read straight from its `.rdata`/`.data` and emulated where code builds them.
- **Addresses** are server-build addresses; t6zm ones come from `t6zm_all_functions.tsv` where matched.
- **BO1/WaW technique numbers** are OAT's `MaterialTechniqueType` (T4/T5), confirmed against real BO1 dumps (Kino).

## 1. The 36 T6 technique types

Name table at server 0x00D1BE90: 48 `{const char *name; uint value}` pairs, used by `Material_TechniqueTypeForName`
when loading `.techset` text. The first 36 are the slots of `MaterialTechniqueSet.techniques[36]`.

| # | name | # | name |
|---|---|---|---|
| 0 | depth prepass | 18 | lit spot dlight glight |
| 1 | build shadowmap depth | 19 | lit spot shadow dlight glight |
| 2 | unlit | 20 | lit spot square dlight glight |
| 3 | emissive | 21 | lit spot square shadow dlight glight |
| 4 | lit | 22 | lit spot round dlight glight |
| 5 | lit sun | 23 | lit spot round shadow dlight glight |
| 6 | lit sun shadow | 24 | lit omni dlight glight |
| 7 | lit spot | 25 | lit omni shadow dlight glight |
| 8 | lit spot shadow | 26 | light spot |
| 9 | lit spot square | 27 | light omni |
| 10 | lit spot square shadow | 28 | fakelight normal |
| 11 | lit spot round | 29 | fakelight view |
| 12 | lit spot round shadow | 30 | sunlight preview |
| 13 | lit omni | 31 | case texture |
| 14 | lit omni shadow | 32 | solid wireframe |
| 15 | lit dlight glight | 33 | shaded wireframe |
| 16 | lit sun dlight glight | 34 | debug bumpmap |
| 17 | lit sun shadow dlight glight | 35 | debug performance |

Entries 36-47 ("custom tech 01" … "custom tech 12") are text aliases for slots 2-13. Each value is
`slot | 0x100` for most entries (some have the flag clear: 26-31, 33); the flag's use isn't traced yet.

## 2. How a draw picks its technique

### Draw method (once, at init)

`GfxDrawMethod gfxDrawMethod` (server 0x084F6F08, 0xB8 bytes):
`{GfxDrawSceneMethod drawScene; u8 baseTechType; u8 emissiveTechType; u8 litTechType[16 surfType][11 lightType];}`.

`R_InitDrawMethod` (0x00A7C770):

| mode | drawScene | baseTechType | emissiveTechType | litTechType |
|---|---|---|---|---|
| `r_fullbright` | FULLBRIGHT | 2 unlit | 2 unlit | all 2 |
| `r_debugShader` != 0 | DEBUGSHADER | 34 debug bumpmap | 34 | all 34 |
| `r_debugPerformance` != 0 | DEBUGSHADER | 4 lit | 3 emissive | defaults |
| normal | STANDARD | 4 lit | 3 emissive | defaults |

`R_SetDefaultLitTechTypes` (0x00A7C560) fills the defaults. Rows are `surfaceType_t`, columns `GfxLightType`
(NONE, DIR, SPOT, SPOT_SQUARE, SPOT_ROUND, OMNI, then the same five `_SHADOWMAP`):

| surface types | NONE | DIR | SPOT | SPOT_SQ | SPOT_RND | OMNI | DIR_SM | SPOT_SM | SPOT_SQ_SM | SPOT_RND_SM | OMNI_SM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all except below | 4 | 5 | 7 | 9 | 11 | 13 | **6** | 8 | 10 | 12 | 14 |
| `*_NO_SUN_SHADOW` (1 TRIANGLES, 2 STATICMODEL_RIGID, 7 XMODEL_RIGID, 10 XMODEL_SKINNED) | 4 | 5 | 7 | 9 | 11 | 13 | **5** | 8 | 10 | 12 | 14 |
| 11 CODE_MESH, 13 PARTICLE_CLOUD | - | - | - | - | - | - | - | - | - | - | - |

`-` = 0xFF (FX code meshes and particle clouds are never drawn through a lit list).

### Per frame: lights -> techniques

`R_UpdateDrawMethod(data, viewInfo)` (0x00A7C830) builds a per-frame table in `GfxBackEndData`, for every shadowable
(primary) light `i` and every surface type `s`:

```
techForLight[s][i] = litTechType[s][ light[i].type + (shadowableLightHasShadowMap[i] ? 5 : 0) ]
```

So a shadowed variant (6, 8, 10, 12, 14) is only used for a light that got a shadow map **this frame**.

### Draw lists -> base technique

`R_SetupDrawSurfListInfos` (0x00A1A3F0) sets each list's `baseTechType` from `s_drawSurfListInfoSetup[23]`
(0x00D06298, `{drawlist, baseTechType, cameraView, depthHackList, occlusionReportsMode}`):

| setup | draw list | base technique |
|---|---|---|
| 0 | LIT_QUASI_OPAQUE | gfxDrawMethod.baseTechType (4 lit) |
| 1, 2 | EMISSIVE_OPAQUE, EMISSIVE_FX | emissiveTechType (3; 2 with r_fullbright) |
| 3, 4 | TRANS, TRANS_POST_FX | 0xFF (when base is lit) |
| 5, 6 | VIEWMODEL_FX, SUPERFLARE | emissive |
| 7, 8 | VIEWMODEL_TRANS, POST_BLUR | 0xFF |
| 9-14 | LIT_BSP, LIT_STATIC_MODEL, LIT (+ _POST_RESOLVE) | base (4) |
| 15-20 | LIGHT_MAP_BSP, LIGHT_MAP_STATIC_MODEL, LIGHT_MAP (+ _POST_RESOLVE) | base (4) |
| 21 | DEPTH_HACK | 0xFF |
| 22 | SONAR | emissive |

`disableAllShadowTech` = `viewInfo->isExtraCamera` (extra cameras never use shadowed techniques). Shadow-map and
prepass lists use 0 (depth prepass) / 1 (build shadowmap depth) and go through `R_SetPrepassMaterial`.

Draw-list names: `g_drawlistNames` (0x010C0818): LIT_BSP, LIT_STATIC_MODEL, LIT, LIT_BSP_POST_RESOLVE,
LIT_STATIC_MODEL_POST_RESOLVE, LIT_POST_RESOLVE, SONAR, LIGHT_MAP_BSP, LIGHT_MAP_STATIC_MODEL, LIGHT_MAP,
LIGHT_MAP_BSP_POST_RESOLVE, LIGHT_MAP_STATIC_MODEL_POST_RESOLVE, LIGHT_MAP_POST_RESOLVE, DEPTH_HACK, TRANS,
TRANS_POST_FX, LIT_QUASI_OPAQUE, EMISSIVE_OPAQUE, EMISSIVE_FX, SUPERFLARE, VIEWMODEL_FX, VIEWMODEL_TRANS, POST_BLUR,
SUN_SHADOW_MAP0-1, SPOT_SHADOW_MAP0-3.

### Which list a surface goes into

By **`Material.cameraRegion`** (`GfxCameraRegionType`), not by which techniques the set has
(`R_AddXModelSurfacesCamera` 0x00A11D40 and the BSP/brush/mark adders):
0 LIT_OPAQUE, 1 LIT_TRANS, 2 LIT_QUASI_OPAQUE, 3 EMISSIVE_OPAQUE, 4 EMISSIVE_TRANS, 5 EMISSIVE_FX,
6 LIGHT_MAP_OPAQUE, 7 DEPTH_HACK, 8 unused, 9 SONAR, 10 NONE (not drawn). In the model adder, LIT_OPAQUE becomes
LIGHT_MAP_OPAQUE when the model is not grid-lit.

BO1 (T5) only has 3 regions (LIT, DECAL, EMISSIVE) plus NONE, so a converted material must take its region from a
T6 donor.

### At draw time: R_GetTechType

`R_SetTechnique` (0x00AA5D90) -> `R_GetTechType` (0x00AA5AC0) -> `R_SetMaterial` / `R_SetPrepassMaterial`:

1. Base not 4 (lit): use the base as is.
2. Base 4: `tech = techForLight[surfType][primaryLightIndex]` (both from the `GfxDrawSurf` key: surfType bits 52-55,
   primaryLightIndex bits 44-51). `R_SetShadowableLight` binds that light's constants.
3. `disableAllShadowTech`: `RemoveShadowTech` (0x00AA54D0) maps 6->5, 8->7, 10->9, 12->11, 14->13.
4. If `4 <= tech <= 14` and the draw surface's `dlightMask` (key bits 30-31) is non-zero: **`tech += 11`** (the
   "dlight glight" variant), and the two dlight bits are written to **pixel cbuffer 3 at offset 0xB0**
   (`R_HW_SetPixelShaderConstant(state, 3, 0xB0, bits, 8)`).
5. A missing technique logs `RB_LogTechniqueType` and `R_WARN_MISSING_TECHNIQUE`, and the surface isn't drawn.

So every lit material needs slots 4-14 for the light types its map uses, plus the matching +11 slots if dynamic
lights can touch it.

## 3. BO1 / WaW technique -> T6 slot

Same meaning, different numbering. T4 techsets have 59 slots, T5 130, T6 36.

| T6 slot | meaning | WaW (T4) | BO1 (T5) |
|---|---|---|---|
| 0 | depth prepass | 0 | 0 |
| 1 | build shadowmap depth | 2 | 2 |
| 2 | unlit | 4 | 4 |
| 3 | emissive | 5 | 5 |
| 4 | lit | 8 | 10 |
| 5 | lit sun | 10 | 11 |
| 6 | lit sun shadow | 12 | 12 |
| 7 | lit spot | 14 | 13 |
| 8 | lit spot shadow | 16 | 14 |
| 13 | lit omni | 18 | 15 |
| 14 | lit omni shadow | 20 | 16 |
| 15-25 | … dlight glight | (none) | 31-37 (LIT_DLIGHT_GLIGHT …) |

- **WaW's odd numbers are `_FADE` variants.**
- **BO1 1 is BUILD_FLOAT_Z**, not a shadow-map pass.
- **BO1 17-30** are the `_DLIGHT` and `_GLIGHT` variants; 38+ are ALPHA, REMAP, FADE, CHARRED, INSTANCED and NV_INTZ.
- **Kino check:** a BO1 world techset (`wc_l_sm_b0c0`) fills 4, 10-37, 52-58, 115-120, 125 and 127. That fits the
  T5 enum exactly.

## 4. Vertex input formats (D3D11 input layouts)

`Load_BuildVertexDecl` (0x00A28E10) builds each `ID3D11InputLayout` from the pass's `MaterialStreamRouting
{source, dest}` list and two tables:
- **`stream_source_info_t[20 decl][11 source]`** at 0x00D0F0C8: `{u8 stream; u8 offset; u8 DXGI_FORMAT}`. 0xFF means
  the decl has no such source; 0xFE means it's optional.
- **Destination semantics** at 0x00D0F360: `{const char *semantic; u8 index}` for POSITION, NORMAL, COLOR0, COLOR1,
  DEPTH, TEXCOORD0-13, BLENDWEIGHT (`MaterialStreamDestination_e` 0-19).

Sources (`MaterialStreamStreamSource_e`): 0 position, 1 color, 2 texcoord0, 3 normal, 4 tangent, 5 texcoord1,
6 texcoord2, 7 texcoord3, 8 normalTransform0, 9 normalTransform1, 10 blendWeight.

| decl | contents (stream:offset format) |
|---|---|
| GENERIC | pos s0:0 R32G32B32A32_FLOAT, color s0:16 R8G8B8A8_UNORM, uv0 s0:20 R32G32_FLOAT, normal s0:28 R10G10B10A2_UNORM |
| PACKED (models) | pos s0:0 R32G32B32A32_FLOAT (w = binormal sign), color s0:16 RGBA8_UNORM, uv0 s0:20 **R16G16_FLOAT**, normal s0:24 **R10G10B10A2_UNORM**, tangent s0:28 R10G10B10A2_UNORM |
| PACKED_LMAP_VC | PACKED + texcoord1 s2:0 R8G8B8A8_UNORM |
| WORLD | pos, color, uv0 s0:20 R32G32_FLOAT, normal s0:28, tangent s0:32 R10G10B10A2, texcoord1 (lightmap) s0:36 R32G32_FLOAT |
| PACKED_WORLD | PACKED + texcoord1 (lightmap) s0:32 **R16G16_UNORM** |
| PACKED_WORLD_T1N0 | PACKED_WORLD + texcoord2 s1:0 R16G16_FLOAT |
| PACKED_WORLD_T1N1 | T1N0 + normalTransform0 s1:4 RGBA8_UNORM |
| PACKED_WORLD_T2N0 | PACKED_WORLD + texcoord2 s1:0 R16G16B16A16_FLOAT |
| PACKED_WORLD_T2N1 / T2N2 | T2N0 + normalTransform0 s1:8 (+ normalTransform1 s1:12) RGBA8_UNORM |
| PACKED_WORLD_T3N0 | T2N0 + texcoord3 s1:8 R16G16_FLOAT |
| PACKED_WORLD_T3N1 / T3N2 | T3N0 + normalTransform0 s1:12 (+ normalTransform1 s1:16) |
| PACKED_WORLD_T4N0 | T2N0 + texcoord3 s1:8 R16G16B16A16_FLOAT |
| PACKED_WORLD_T4N1 / T4N2 | T4N0 + normalTransform0 s1:16 (+ normalTransform1 s1:20) |
| POS_TEX | pos s0:0 R32G32B32A32_FLOAT, uv0 s0:12 R32G32_FLOAT (pos and uv overlap: pos is read as float4 but only xyz is used) |
| PARTICLECLOUD | pos s0:0 R16G16B16A16_SNORM |
| POS_COLOR | pos s0:0 R32G32B32_FLOAT, color s0:12 RGBA8_UNORM |
| POS_FP16TEX | pos s0:0 R32G32B32_FLOAT, uv0 s0:12 R16G16_FLOAT |

`MaterialWorldVertexFormat` (`MTL_WORLDVERT_TEX_<t>_NRM_<n>`) picks the PACKED_WORLD_T*N* layout. The layer
stream (s1) holds the extra layers' UVs (half floats, two per float4) and the packed normal transforms.

The stock T6 world lit vertex program (`wpc_lit_sm_r0c0n0s0`, slot 5) reads POSITION0 float4, COLOR0, TEXCOORD0
float2, NORMAL0 float3, TEXCOORD2 float3 (tangent) and TEXCOORD1 float2 (lightmap UV). So routing sends tangent to
TEXCOORD2, as in WaW and BO1.

**Compared with BO1/WaW:** those programs unpack normal and tangent from UBYTE4 themselves (`* 1/127, -1` and the
`0.752941` = 192/255 sign scale). T6 hands the shader UNORM 10:10:10:2 values, which the T6 program decodes.

## 5. Shader constants: BO1 vs T6 fog

BO1 programs and T6 `PerScene` (cb0) carry the same fog constants with the same declared types and the same math
(height-fog integral from `fogConsts`/`fogConsts2`, sun-direction tint from `sunFog`):

| constant | BO1 (CTAB) | T6 cb0 offset, size |
|---|---|---|
| fogColor | float4 | 416, 16 |
| fogConsts | float4 | 432, 16 |
| fogConsts2 | float4 | 448, 16 |
| sunFogDir | **float3** | 464, **12** |
| sunFogColor | float4 | 480, 16 |
| sunFog | **float2** | 496, **8** |

The full T6 `PerScene` layout (from stock shader reflection) is in the converter's shader cache. Its world/model
per-object cbuffer is cb3: worldMatrix, gridLightingCoordsAndVis, gridLightingSH0-2, reflectionLightingSH0-2.

### Shader argument order

`R_SetPassShaderStableArguments` (0x00AA35C0) applies a pass's stable args in this fixed type order:
- 0 material vertex constant (looked up by `nameHash` in the material's constant table; error "material '%s' is
  missing a required named constant");
- 1 literal vertex constant;
- 2 material pixel sampler;
- 3 code vertex constant, with 4 code pixel samplers (`R_GetTextureFromCode`) handled inside that loop.

`R_SetupPassPerObjectArgs` / `PerPrimArgs` apply the per-object and per-primitive groups (the first
`perPrimArgCount`, then `perObjArgCount` of `MaterialPass.args`).

## 6. Dynamic lights ("dlight glight" techniques 15-25)

### What the engine fills: `R_SetDLightsConstants` (0x00A17480)

The engine walks the view's visible dynamic lights. **Omni lights** (type 5) go into up to 4 packed "glights";
**one spot light** (type 2) becomes "the dlight". Values land in `GfxCmdBufInput.consts[]` (code constant index =
byte offset / 16), which T6 copies into `PerScene` (cb0) without per-pass arguments:

| code const | field | value |
|---|---|---|
| 125-127 | glightPosXs / PosYs / PosZs | x, y, z of the 4 omni lights, minus `consts[0x10]` (camera-relative) |
| 128 | glightFallOffs | `-1 / radius` per light |
| 129-131 | glightReds / Greens / Blues | colour per light |
| 132 | dlightPosition | xyz camera-relative, **w = -1/radius** |
| 133 | dlightDiffuse | colour, w = 1 |
| 134 | dlightAttenuation | **always 0** |
| 135 | dlightFallOff | `(1/(b-a), 1/(d-c), -a/(b-a), -c/(d-c))` from the light's four falloff distances: two smoothstep ranges |
| 136-139 | dlightSpotMatrix0-3 | light view x light projection (cookie lookup) |
| 140 | dlightSpotDir | the light's direction (copied as is), w = 0 |
| 141 | dlightSpotFactors | `(1/(c1-c0), -c0/(c1-c0), 0, shadow fade)` from the light's two cone cosines |
| 142-145 | dlightShadowLookupMatrix0-3 | spot shadow lookup (only when the light has a shadow; the shadow image is `gfxRenderTargets[0x10]` otherwise) |
| 61 (0x3D) | dlightSpotShadowmapPixelAdjust | PCF tap spacing (this one *is* routed by a pass argument) |

The cookie texture is code texture 16 (`TEXTURE_SRC_CODE_DLIGHT_ATTENUATION`, the light def's image, white if none).
The spot shadow map is code texture 7.

### How a T6 dlight program uses it (stock `wpc_lit_sm_r0c0n0s0`, slot 15)

The pixel program reads a 2-word mask at **cb3 (`dlights`) row 11** (byte 0xB0), written per draw by `R_GetTechType`:
- `if (cb3[11].x)`: the spot dlight term. Cookie: `dlightSpotMatrix` projection → `dlightAttenuationSampler` (t11),
  sample squared. Distance: `sat(1 + d * dlightPosition.w)^2`. Cone: `sat(dot(L, dlightSpotDir) * f.x + f.y)`.
  Shadow: 12-tap PCF with `sample_c_lz` on t10 (comparison sampler), taps scaled by `dlightSpotShadowmapPixelAdjust`,
  then `lerp(1, shadow, dlightSpotFactors.w)`.
- `if (cb3[11].y)`: the 4 glights. Per light: `sat(1 + d * falloff)^2 * sat(N.L)`, colour from the Reds/Greens/Blues
  rows.

### BO1 dlight programs (T5 techniques 31-37 `*_DLIGHT_GLIGHT`)

BO1 reads the same constant names. Its math differs in a few places:
- **Distance attenuation:** `1 / (a + b*d + c*d^2)` from `dlightAttenuation`, with a guard that gives 0 when the sum is
  0. It also uses `dlightFallOff`'s two smoothsteps on the spot-space depth (`dot(pos, dlightSpotMatrix2)`).
- **Shadow:** 4 hardware-PCF `texldp` taps on `shadowmapSamplerSpot`, averaged (x 0.25).
- **Separate specular colour:** `dlightSpecular`, which T6 doesn't have.
- **No mask:** BO1 picks a separate technique per case instead (`_DLIGHT`, `_GLIGHT`, `_DLIGHT_GLIGHT`).

Because T6 writes `dlightAttenuation = 0`, a BO1 program bound by name gets **no dynamic light at all**.

### BO1 works in linear light, like T6

BO1 lit pixel programs end with `oC0 = sqrt(sat(colour * hdrControl0.x))`. That is T6's `sqrt(colour * hdr)`, apart
from the saturate. They also square the reflection-probe sample. WaW programs work in gamma space instead, so the
converter's WaW unit adapters (`sqrt(4 hdr * linear)` for sun, fog and light colours, the probe, and model lighting)
must not be applied to BO1 programs. BO1's primary-light constants are T6's set by name (`lightAttenuation`,
`lightFallOffA/B`, `lightSpotMatrix0-3`, `lightSpotAABB`, `lightConeControl1/2`, `lightSpotCookieSlideControl`),
plus `lightSpecular`.

### Per-light code constants (pass argument type 5, value `0x01000000 + id`)

Measured from the arguments of every stock pass, matching the argument's location to the program's reflected field.
These rows are per light, so a pass must route each one it reads:

| id | field | id | field |
|---|---|---|---|
| 0 | lightPosition | 7-10 | lightSpotMatrix0-3 (10 inferred) |
| 1 | lightDiffuse | 11 | lightSpotAABB |
| 2 | lightSpotDir | 12, 13 | lightConeControl1, 2 (13 inferred) |
| 3 | lightSpotFactors | 14 | lightSpotCookieSlideControl |
| 4 | lightAttenuation (inferred) | 0x3C | spotShadowmapPixelAdjust |
| 5, 6 | lightFallOffA, B | 0x3D | dlightSpotShadowmapPixelAdjust |

"Inferred" ids are not routed by any stock pass. They follow the cbuffer field order, which every measured id matches.
Other ids seen: 0x11 renderTargetSize, 0x25 shadowmapSwitchPartition, 0x26 sunShadowmapPixelSize, 0x2E materialColor,
0x45-0x48 gridLighting*, 0x6B-0x7A postFxControl0-F, 0xA9-0xB0 scriptVector0-7, 0xB3-0xB9 weaponParam*,
0xCA skyColorMultiplier. The vertex matrices (type 3, `0x04000000 + id`): 0xD5 worldMatrix, 0xE5 viewProjectionMatrix,
0xED shadowLookupMatrix, 0xE9 worldViewProjectionMatrix, 0xDA inverseViewMatrix.

### Other BO1 program facts found on the way

- **Material constant and texture names use T6's hash.** In BO1 material assets, a pass argument's value is
  `(h * 33) ^ (byte | 0x20)` over the name (T6's hash), not WaW's lower-case djb2. Checked: `Reflection_Amount` =
  211931156, `Scatter_Intensity` = 4240161686, `Rim_Specular` = 1536689958. BO1 source materials dumped by OAT carry
  `"_game": "t5"`.
- **Technique-set names.** BO1 calls the opaque unlit set `*_unlit_replace`, as T6 does; WaW calls it `*_unlit`. BO1
  also has `*_unlitdecalblend_add` / `_multiply`, which keep their blend in the material state bits (multiply:
  `zero, srccolor`).
- **Cloak models** (`mc_cod7modelcloak_*`) read the tangent as `TEXCOORD1`, with the same UBYTE4 decode as the normal
  (`mad r, v, c.xxxy, c.zzzw` with 0.00787401572 / 0.752941191). T6 model passes stream the tangent as `TEXCOORD2`.
- **`__characterDissolveColor`** (cloak vertex programs, c23) only feeds `TEXCOORD7`:
  `o.x = 31 sat(c.w) + 1`, `o.y = (2 sat(c.x) - 1) * o.x`. No lit pixel program reads `TEXCOORD7`, so the value is
  dead there. The cloak pixel programs `texkill` on `sat(cloakMap.a * scriptVector0.x + scriptVector0.y) < 0.5`, so
  `scriptVector0 = 0` keeps the model visible. BO1 technique 4 of the cloak sets is the "cloaked" overlay: it samples
  the resolved frame at `vPos` (`cloakedSampler`, code texture 9).
- **`vPos`** (SM3 pixel position) is integer pixel coordinates; D3D11 `SV_Position` is the pixel centre, so
  `vPos = SV_Position.xy - 0.5`.
- **Canopy sway** (`mc_sm_treecanopy*`, vertex program `treecanopy`): per vertex,
  `i = floor(15 * color.r)` (`mova a0.w`), spring = `lerp(u_customWindSpring, variantWindSpring[i].yzw, t)` with
  `t = sat(|world.xy - u_customWindCenter.xy| / (1e-5 + u_customWindCenter.w))`. The spring angles are scaled by
  `treeCanopySwayParms.z` into a rotation, and the result is blended with the rest pose by a weight built from
  `treeCanopySwayParms.x/.y`, plus a push along `windDirection`. So `u_customWindCenter.w = 0` (no script wind zone)
  selects `variantWindSpring`, and `treeCanopySwayParms = 0` gives exactly the rest pose. BO1 canopies light from
  the grid texture (`modelLightingSampler`).
- **T6 keeps the wind in PerScene** (cb0): `windDirection` at offset 0, `variantWindSpring[16]` at 32 (rows 2-17).
  T6's own `mc_treecanopy_sm` lit vertex program declares `gameTime` and `treeCanopySwayParms` but doesn't read
  them (it is static), and it lights from the grid SH rows in cb3, not a 3D texture.
- **`gameTime`** is T6 code constant 0x19. Stock pixel passes route it to buffer 2 row 4.

## 7. What this changed in the converter (B2W fork)

Measured offline with a harness that re-runs `shaderruntime.bind_material` for every material of the staged Kino
build (1,235 materials, donor choice as in the bridge). **Not yet verified in game.**

| | materials binding translated lit passes (slots 4-8, 13-14) | depth/shadow (0/1) | unlit (2) |
|---|---|---|---|
| before | 0 | 1,086 / 4 | 44 |
| after fixes 1-5 | 1,099 | 1,076 / 1,077 | 1,111 |
| after fixes 1-14 | **1,145** (and dlight slots 15-25 on all 1,145) | 1,101 / 1,088 | 1,189 |

After fix 14 no material fails donor matching (was 54), and about 30 passes in the whole map stay on their donor
program (mostly BO1's cloak overlay, which is better left untranslated).

The fixes:
1. **Technique numbering per source game.** The converter mapped T6 slots to *WaW* numbers for BO1 sources too, so
   BO1 lit techniques were never found (and T6 slot 1 read WaW 1, a `_FADE` variant, instead of 2). It now
   picks the table from the source techset length (59 = WaW, 130 = BO1); see section 3.
2. **Layered world materials** lost their layer data in the parallel (spawn) staging workers: a module flag set in
   the parent process was never seen by the workers, so multi-layer BO1 surfaces were matched to single-layer
   donors. The flag now travels in the worker context.
3. **Fog constants packed mid-row.** `sunFogDir` (float3) and `sunFog` (float2) occupy 12/8 bytes in T6 `PerScene`;
   the old check required a full 16-byte row. It now checks the declared width (from the source CTAB), and reads
   fields that start mid-row (like `extraCamParam` at offset 2260) through a rotated swizzle.
4. **`scriptVector0-7`** (cb1): bound directly when the donor pass routes that buffer range, otherwise zero (what T6
   holds when no script sets them).
5. **BO1 lightmap brightness (`lightmapSamplerSecondaryB`, s14).** BO1 splits a lightmap page into three textures:
   R5G6B5 colour shares and direction, G16R16 brightness, and L8 sun visibility. The converter's WaW-layout page
   already carried the 16-bit brightness as a high byte (alpha of the A/B thirds) and a low byte (third page .z/.w).
   The translated program now takes three samples and rebuilds `hi*256 + lo`. Bilinear filtering is linear, so
   the filtered bytes recombine to exactly the filtered 16-bit value. This one sampler had blocked 5,453 lit
   passes.

6. **BO1 works in linear light** (section 6). BO1 sources (`_game: t5`) skip every WaW gamma adapter. Instead: shadow
   fetches become T6 comparison samples, model lighting is scaled by `sqrt(32 / 31.875)`, and the probe texel is
   converted from T6's encoding to BO1's `8 * texel^2`.
7. **Dynamic lights.** BO1's `*_DLIGHT_GLIGHT` techniques (31-37) now feed T6 slots 15-25. The spot term is gated by
   the T6 mask `cb3[11].x` and the glights by `.y`, and `dlightAttenuation` is the constant `(1, 0, 0, 0)`, since T6
   always writes 0 there, which would make BO1's `1/(a+bd+cd^2)` zero. Per-light rows (`lightFallOffA`, the spot
   matrices, ...) are added to the pass as code arguments by id. `lightSpecular` / `dlightSpecular` read the
   diffuse colour.
8. **T6 name hash for BO1 material constants and textures** (161 passes had lost their constants).
9. **Cloak tangent:** source `TEXCOORD1` is read from T6 `TEXCOORD2` when it has the UBYTE4 unit-vector decode.
10. **`vPos`** = `SV_Position.xy - 0.5`.
11. **`mova` and relative constant reads** (`c40[a0.w]`). The bound contract gives the array length (`count`), and the
    read is clamped to it. In the unbound ABI the array is the rest of the 256-register file.
12. **Neutral BO1-only uniforms:** `__characterDissolveColor` and `u_customWindCenter/Spring` are 0, and vertex
    `gameTime` is routed as code constant 0x19 to a free material row for any material, not just the sky.
    **Canopy sway is held static** (`treeCanopySwayParms = 0`): T6 draws a depth prepass and fills
    `variantWindSpring` from its own wind, which is unmeasured, so a swaying lit pass risks depth holes.
13. **Donor rules:** `*_unlit_replace` is treated as WaW `*_unlit` (blend detection applies). `unlitdecalblend_add` /
    `_multiply` get the unlit pass with the source blend (model add: `mc_unlit_add`). BO1 canopies get the
    alpha-tested lit model pass, because T6's canopy pass has no `modelLightingSampler`. `l_r0c0n0s0sc0x0` and the
    hero eyeball get `l_sm_r0c0n0s0`.
14. **Tangent-reading BO1 shaders** (`sw4_3d_rotate`, clan tag, player icon) get normal-mapped donors, the only ones
    that stream `TEXCOORD2`.

Still open: **in-game check.** Everything above is measured offline only, by unit tests and the bind harness.

## Reproducing the tables

`tools/t6match/t6tables.py CoDMPServer_PC.exe` prints sections 1, 2 and 4 straight from the server exe. It reads the
name, list-setup and stream tables and emulates `R_SetDefaultLitTechTypes` with capstone. `tools/t6match/Decomp.java`
is the Ghidra headless script used for the decompiles:
`analyzeHeadless <proj> <name> -process -noanalysis -postScript Decomp.java out.c R_GetTechType 0x00AA5AC0 ...`.

## Functions (server build)

| function | address |
|---|---|
| R_InitDrawMethod | 0x00A7C770 |
| R_SetDefaultLitTechTypes | 0x00A7C560 |
| R_UpdateDrawMethod | 0x00A7C830 |
| R_SetupDrawSurfListInfos | 0x00A1A3F0 |
| R_SetTechnique | 0x00AA5D90 |
| R_SetLitTechniqueNoShaderConstantSet | 0x00AA5EB0 |
| R_GetTechType | 0x00AA5AC0 |
| RemoveShadowTech | 0x00AA54D0 |
| Material_TechniqueTypeForName | 0x00A4C790 |
| RB_LogTechniqueType | 0x00AA5C20 |
| Load_BuildVertexDecl | 0x00A28E10 |
| Material_StreamSourceForName / StreamDestForName | 0x00A47FB0 / 0x00A47DE0 |
| R_SetPassShaderStableArguments | 0x00AA35C0 |
| R_SetDLightsConstants | 0x00A17480 |
| R_AddXModelSurfacesCamera | 0x00A11D40 |
| gfxDrawMethod (data) | 0x084F6F08 |
| s_drawSurfListInfoSetup (data) | 0x00D06298 |
| technique name table (data) | 0x00D1BE90 |
| stream_source_info_t table (data) | 0x00D0F0C8 |
| g_drawlistNames (data) | 0x010C0818 |
