# BO4 emissive materials, part 2: the non-standard classes

<!-- toc -->
## Contents

- [1. t8_rock_coal_01_emissive_blend (and 2. t8_zm_esc_rubble_piles_junk_burn_emi)](#1-t8_rock_coal_01_emissive_blend-and-2-t8_zm_esc_rubble_piles_junk_burn_emi)
  - [Worked radiance, coal blend (vertex alpha 1, flicker 1, face-on)](#worked-radiance-coal-blend-vertex-alpha-1-flicker-1-face-on)
- [3. mtl_p7_zm_zod_matchstick_glow](#3-mtl_p7_zm_zod_matchstick_glow)
- [4a. The three *_flow lava materials](#4a-the-three-_flow-lava-materials)
- [4b. mtl_p7_zm_ctl_fuse_gold / _metal / _brass](#4b-mtl_p7_zm_ctl_fuse_gold--_metal--_brass)
- [4c. mtl_p8_zm_esc_cryo_chamber_power_source_screen_green](#4c-mtl_p8_zm_esc_cryo_chamber_power_source_screen_green)
- [4d. p7_zm_ctl_decal_emissive115_droplets_01](#4d-p7_zm_ctl_decal_emissive115_droplets_01)
- [4e. mtl_p8_spa_fireplace_log_emissive](#4e-mtl_p8_spa_fireplace_log_emissive)
- [5. Summary for the exporter](#5-summary-for-the-exporter)
- [6. Shared constant blocks](#6-shared-constant-blocks)
<!-- /toc -->

Follow-up to [emissive.md](emissive.md) (same marks: **[P]** bytecode / zone bytes, **[I]** inferred, **[?]** unknown; maths only).
Constants are the **live (patched zone)** cb0 rows; "float n" is the index in that buffer (`mats_true.json`, second buffer).
`X = cb2[110].x` (read as 1 / exposure, EMISSIVE.md 4e), `time = cb2[89].w`, `F(p, inv)` = the view-angle term:

    F(p, inv) = 1 if p == 0, else inv ? pow(1 - sat(N.V), p) : pow(sat(N.V), p)        N = vertex normal

Two families:

- **Unlit emissive** (coal blend, junk burn, fireplace log, 115 droplets): about 50 to 100 instructions, cb0 + cb2 only.
  No lighting, **no fog**, output alpha is the constant 1, colour is `709 -> 2020 * E * exposure`. They are overlay shells:
  everything is multiplied by **vertex colour alpha** **[P: the vertex shader passes COLOR.w straight through]**.
  Their relative mode uses the emission's **own** luminance: `E *= max(luma(E), 1e-4, X)`, luma weights (0.299, 0.587, 0.114).
- **Lit emissive variants** (lava flow, fuses, screen, matchstick): the standard lit shader with extra UV machinery; emission is
  added to the lit colour before fog and exposure, relative mode is `max(Llit, 1e-4, X)` as in part 1.

The blend state of the unlit shells was not decoded **[?]**; alpha 1 with colour pre-multiplied by vertex alpha only makes sense
as an additive (or max) overlay **[I]**.

## 1. t8_rock_coal_01_emissive_blend (and 2. t8_zm_esc_rubble_piles_junk_burn_emi)

Technique set `030b0f2a627a4b72` (core_common 0xd5cfe60), pixel shader core 0xd5d2160, 65 instructions, `CB0[7]`;
the second coal instance uses `1033b38672149a9a` (esc 0xd188ccd), shader esc 0xd189ca5, same code **[P]**.
Listings: `asm\coal_blend_unlit_core_d5d2160.asm`, vertex shader `asm\coal_blend_vs_core_d5d043c.asm`.

    e       = emissiveMap(uv)                                    plain uv, no parallax, no scroll
    phase   = frac(seed.x + seed.y + seed.z + cb0[3].y)          seed = frac(5/5/6-bit fields of a per-instance word * 0.01)
    flick   = lerp(cb0[4].x, cb0[4].y, pow(|flickerLookup(cb0[3].x, phase + time * cb0[3].z).r|, cb0[4].z))
    E       = e.rgb * cb0[5].yzw * e.a * vertexAlpha * cb0[4].w * F(cb0[5].x, cb0[6].y) * flick
    if cb0[6].x:  E *= max(luma(E), 1e-4, X)
    out.rgb = M709to2020 * E * exposure ;  out.a = 1

| slot | float | meaning | coal blend | junk burn |
|---|---|---|---|---|
| cb0[3].x, .y, .z | 12, 13, 14 | flicker lookup u, phase offset, speed | 0.4, 0.4, 0.25 | 0.4, 0.4, 0.25 |
| cb0[4].x, .y, .z | 16, 17, 18 | flicker min, max, power | 0.5, 1.0, 0.2 | 0.3, 1.0, 0.2 |
| cb0[4].w | 19 | **scale** | 16 | 4 |
| cb0[5].x | 20 | view-angle power | 1 | 1 |
| cb0[5].yzw | 21-23 | **tint** | (1, 1, 1) | (1, 0.425, 0.109) |
| cb0[6].x | 24 | relative flag | 1 | 1 |
| cb0[6].y | 25 | invert view-angle term | 0 | 0 |

Answers: it is **not** a mix-layer class and there is no blend map. The only mask is **vertex alpha** (times the emissive map's own
alpha), so the glow appears only where the mesh's vertex alpha is painted. Yes, there is flicker (50 to 100%, per-instance phase).
It is unlit and unfogged; the colour map is not sampled at all (the material's colorMap is the emissive image again).

### Worked radiance, coal blend (vertex alpha 1, flicker 1, face-on)

Same emissive image as the hot coal (linear mean (0.0151, 0.0011, 0.0004), brightest 1% (0.311, 0.062, 0.011), brightest 0.1%
(0.770, 0.304, 0.052)). Before the relative step `E = map * 16`; then `exposed = E * max(1, luma(E) * exposure)`.

| | E = map * 16 | luma(E) | exposed, exposure <= 1 / luma | exposed at exposure 1 |
|---|---|---|---|---|
| mean of the surface | (0.24, 0.018, 0.006) | 0.083 | (0.24, 0.018, 0.006) | same |
| brightest 1% | (4.98, 0.99, 0.18) | 2.09 | (4.98, 0.99, 0.18) | (10.4, 2.1, 0.37) |
| brightest 0.1% | (12.3, 4.9, 0.83) | 6.65 | (12.3, 4.9, 0.83) | (82, 32, 5.5) |

- Times `N.V` (cosine, power 1), times vertex alpha, times flicker 0.5..1.
- So the ember bed is a **dim dark-red wash** (about mid grey in exposed units, pure red) with sparse orange cores of 5 to 10,
  one sixteenth of the hot variant (256). Its job is the low glow around the hot coals, not the bright core.
- The self-luminance square only matters when `luma(E) * exposure > 1`, i.e. on the cores when exposure is above about 0.5.

Junk burn (image linear mean (0.050, 0.009, 0.002), brightest 1% (0.80, 0.31, 0.09)): `E = map * (1, 0.425, 0.109) * 4`:
mean (0.20, 0.015, 0.001), brightest 1% (3.2, 0.53, 0.04), luma 1.27; flicker 30 to 100%. A deep red smoulder with orange spots.

## 3. mtl_p7_zm_zod_matchstick_glow

Technique set `5bc2bf7bc1d51be8` (esc 0xe255f2d), lit shader esc 0xe256eb1, 2,668 instructions, `CB0[11]` (`asm\matchstick_lit_esc_e256eb1.asm`).

    uvA    = scrolled / rotated / zoomed uv (below)
    e      = emissiveMap(uvA).rgb * cb0[8].xyz
    mask   = emissiveMap(uv * cb0[9].xy).a
    P      = per-object constants: instance record (t4, +8) -> index into a 384-byte per-object buffer (t0), first two floats
    reveal = sat((revealMap(uv).r - lo) / (hi - lo)),  t = sat(P.y * 0.998 + 0.001),  s = sat(cb0[10].w)
             lo = sat((1 - t) - cb0[10].z * pow(t, s)),  hi = sat((1 - t) + cb0[10].z * pow(1 - t, s))
    E0     = e * mask * reveal * F(cb0[7].y, off) * cb0[7].x * sat(P.x)
    E      = cb0[8].w ? E0 * max(Llit, 1e-4, X) : E0             added to the lit colour, then fog, exposure

    uvA = ( rot( (uv - 0.5 + parallax * (cb0[6].y + 1e-5)) * cb0[4].xy + cb0[4].zw * cb0[4].xy , angle )
            + cb0[3].zw * time * cb0[4].xy ) / zoom + wobble + 0.5
    angle = (1 + cb0[3].y * time) * cb0[3].x degrees ;  zoom = lerp(cb0[5].x, cb0[5].y, 0.5 - 0.5 * sin(cb0[6].x * time))

| slot | float | meaning | value |
|---|---|---|---|
| cb0[7].x | 28 | **scale** | 12 |
| cb0[7].y | 29 | view-angle power | 1 |
| cb0[8].xyz | 32-34 | **tint** | (0.305, 0.061, 0.003) |
| cb0[8].w | 35 | relative | 1 |
| cb0[3].zw | 14, 15 | scroll, UV per second (before the uv scale) | (4, 4) |
| cb0[4].xy | 16, 17 | emissive uv scale | (0.5, 0.5) |
| cb0[3].x, .y | 12, 13 | rotation degrees, rotation speed | 0, 0 |
| cb0[5].xy, cb0[6].x | 20, 21, 24 | zoom min, max, speed | 1, 1, 1 (no zoom) |
| cb0[6].y | 25 | parallax depth | 0 |
| cb0[9].xy | 36, 37 | mask uv scale | (2, 8) |
| cb0[10].z, .w | 42, 43 | reveal edge width, edge curve | 1, 0 |

**What drives it [P]:** two per-object shader constants, not the material. `P.x` (clamped 0..1) is a straight multiplier on the
emission, `P.y` is the reveal amount swept through the reveal map (0 = nothing, 1 = all). Both come from the per-entity
constant buffer that scripts set; with them at 0 the material emits nothing. Which script sets them was not traced **[?]**.
Fully on: `map * (0.305, 0.061, 0.003) * 12 * N.V`, peak about (2.6, 0.56, 0.03) exposed, a red-orange ember glow, with the
pattern scrolling at 2 UV per second diagonally (a fast shimmer).

## 4a. The three *_flow lava materials

Technique sets `254dd1b267e2414d` (esc 0xd7ba90d; t8_zm_esc_lava_flow, t8_zm_esc_lava_river_01_flow), shader esc 0xd7bb8d9, and
`19672eb502cd9501` (esc 0xd469385; t8_zm_esc_lava_vertical_flow), shader esc 0xd46a375; same code, `CB0[8]`
(`asm\lava_flow_lit_esc_d7bb8d9.asm`, `asm\lava_vertical_flow_lit_esc_d46a375.asm`). Lit class with a **tiled flow map**:

    G      = cb0[2].x                                            cells across the uv square
    for the 4 cell corners c around uv:  f = flowMap(round(uv * G + corner) / G).xy       point-sampled per cell
                                         d_c = (1 - 2 f.x, 2 f.y - 1)                     flow direction, length up to 1.41
                                         uv_c = uv + d_c * cb0[2].y * time                straight scroll, no reset
    w      = smoothstep weights of frac(uv * G)                  (3 - 2t) t^2 on each axis
    colour, normal, emissive = bilinear blend over the 4 corners of map(uv_c)
    k      = cb0[3].y ? length(d at uv) * cb0[4].y + cb0[4].x : 1          (1, 0) here, so k = 1
    E0     = emissive.rgb * cb0[6].xyz * emissive.a * k * F(cb0[5].w, cb0[7].x) * (1 - decal)
    E      = E0 * cb0[5].z * (cb0[6].w ? max(Llit, 1e-4, X) : 1)

So the lava texture slides along the painted direction of each of G x G cells and neighbouring cells cross-fade; there is no
flicker and no pulsing. Emissive alpha is taken from the first corner sample only.

| slot | float | meaning | lava_flow | lava_river_01_flow | lava_vertical_flow |
|---|---|---|---|---|---|
| cb0[2].x | 8 | flow cells | 6 | 6 | 6 |
| cb0[2].y | 9 | **scroll speed**, UV per second per unit of flow | 0.08 | 0.03 | 0.2 |
| cb0[3].zw | 14, 15 | normal map uv scale | (1, 1) | (1, 1) | (1, 1) |
| cb0[5].z | 22 | **scale** | 22.63 | 45.25 | 22.63 |
| cb0[5].w | 23 | view-angle power | 0.25 | 0.4 | 0.25 |
| cb0[6].xyz | 24-26 | **tint** | white | white | white |
| cb0[6].w | 27 | relative | 1 | **0** | 1 |
| cb0[5].y | 21 | sun and sun shadow off | 0 | 0 | 0 |

Direction is entirely the flow map (red = -u..+u as 1..0, green = -v..+v as 0..1); there is no direction constant.
Face-on, exposed units for the relative two, scene units for the river:

| | mean | brightest 1% |
|---|---|---|
| lava_flow (map mean (0.429, 0.012, 0.0002)) | (9.7, 0.26, 0.005) | (22.4, 5.1, 0.43) |
| lava_vertical_flow (map mean (0.609, 0.021, 0.0006)) | (13.8, 0.48, 0.014) | (22.5, 6.9, 1.0) |
| lava_river_01_flow (map mean (0.259, 0.018, 0.0007), alpha mean 0.52) | (11.7, 0.83, 0.03) * alpha, absolute = up to 4,400 nits | (44, 10.4, 0.3) * alpha |

t8_zm_esc_lava_rocky_river_01 is the **standard** class (scale 11.31, power 0.5, tint white, flag 0 = absolute), no flow.

## 4b. mtl_p7_zm_ctl_fuse_gold / _metal / _brass

Technique set `14d665d575b6c5ab` (core 0xf4c9edc), shader core 0xf4caee4, `CB0[6]` (`asm\fuse_lit_core_f4caee4.asm`).
The standard lit emissive formula with a spec-colour row inserted, so every emissive slot sits one row later **[P]**:

| value | slot | float | all three fuses |
|---|---|---|---|
| spec colour tint | cb0[1].yzw | 5-7 | gold (1.0, 0.708, 0.283) / metal (0.539, 0.546, 0.546) / brass (0.451, 0.389, 0.225) |
| gloss min, max | cb0[2].xy | 8, 9 | 0, 17 |
| sun off | cb0[2].w | 11 | 0 |
| **scale** | cb0[3].x | 12 | 4 |
| view-angle power | cb0[3].y | 13 | 0 |
| **tint** | cb0[4].xyz | 16-18 | (0.050, 0.568, 1.0) |
| relative | cb0[4].w | 19 | 1 |
| invert, parallax depth | cb0[5].x, cb0[5].z | 20, 22 | 0, 0 |

`E = emissiveMap.rgb * emissiveMap.a * tint * 4 * max(Llit, X)`: peak (0.2, 2.3, 4.0) exposed where the map is white; the
map's brightest 1% is 0.29, giving (0.06, 0.66, 1.16): a small element-115 blue line. No mask, no script input.

## 4c. mtl_p8_zm_esc_cryo_chamber_power_source_screen_green

Technique set `2c943cd77180a61b` (esc 0xd8b4d6d), shader esc 0xd8b5d5d, `CB0[11]` (`asm\screen_green_lit_esc_d8b5d5d.asm`).
Lit; one emissive layer with optional flipbook / scroll (all off here) and flicker:

    e     = emissiveMap1(uvS) * cb0[9]                           rgb * tint, alpha * scale
    flick = lerp(cb0[8].x, cb0[8].y, pow(|flickerLookup(cb0[7].x, frac(seed + cb0[7].y) + time * cb0[7].z).r|, cb0[8].z))
    E0    = e.rgb * e.a * flick * (1 - decal) * F(cb0[10].y, cb0[10].z)
    E     = cb0[10].x ? E0 * max(Llit, 1e-4, X) : E0

| slot | float | meaning | value |
|---|---|---|---|
| cb0[9].xyz | 36-38 | **tint** | (0.0029, 0.0168, 0.0012) |
| cb0[9].w | 39 | **scale** (on the map alpha) | 2 |
| cb0[10].x | 40 | relative | 1 |
| cb0[10].y, .z | 41, 42 | view-angle power, invert | 0, 0 |
| cb0[7].xyz | 28-30 | flicker u, phase, speed | 0, 0, 1 |
| cb0[8].xyz | 32-34 | flicker min, max, power | 0, 1, 0.125 |
| cb0[2].x | 8 | flipbook on if > 0.5 (columns .y, rows .z, frame time .w) | 0 = off |
| cb0[6].y | 25 | parallax depth | 0 |

Peak `(0.0029, 0.0168, 0.0012) * 2` = (0.006, 0.034, 0.002) exposed where the map is white and opaque (map alpha mean 0.13):
a very dark green, close to off. The flicker can take it to zero. This screen is meant to look nearly dead.

## 4d. p7_zm_ctl_decal_emissive115_droplets_01

Technique set `27e6a0026f0fa7c4` (zm_common 0x11ef202), unlit shader zmc 0x11f1412, 102 instructions, `CB0[11]`
(`asm\droplets_unlit_zmc_11f1412.asm`).

    uvM   = mask uv: (uv - 0.5 + parallax * (cb0[5].w + 1e-5)) * cb0[3].zw, rotated by cb0[2].z degrees (speed cb0[2].w),
            scrolled by cb0[3].xy * time, zoomed by lerp(cb0[4].z, cb0[4].w, ..), + 0.5
    m     = emissiveMask(uvM).r * vertexAlpha * cb0[6].z
    uvE   = uv * cb0[10].xy + time * cb0[10].zw + distortion(uv * cb0[8].yz + time * cb0[9].xy) * cb0[9].z * texel
    e     = emissiveMap(uvE)
    E     = e.rgb * cb0[7].xyz * e.a * m * F(cb0[6].w, cb0[8].x)
    if cb0[7].w:  E *= max(luma(E), 1e-4, X)                      then 709 -> 2020, exposure, alpha 1, no fog

| slot | float | meaning | value |
|---|---|---|---|
| cb0[6].z | 26 | **scale** | 16 |
| cb0[6].w | 27 | view-angle power | 0.5 |
| cb0[7].xyz | 28-30 | **tint** | (0.017, 0.283, 1.0) |
| cb0[7].w | 31 | relative | 1 |
| cb0[5].w | 23 | mask parallax depth | 1.0 |
| cb0[3].xy, cb0[10].zw, cb0[9] | 12-13, 42-43, 36-39 | scrolls, distortion | all 0 |
| cb0[3].zw, cb0[10].xy | 14-15, 40-41 | uv scales | (1, 1), (1, 1) |

The mask is `$white_reveal` (white), so the masks left are vertex alpha and the image alpha (mean 0.05: sparse droplets).
Brightest 1% of the image is 0.148 grey: `0.148 * (0.017, 0.283, 1.0) * 16` = (0.04, 0.67, 2.4) before the relative step: blue drops.

## 4e. mtl_p8_spa_fireplace_log_emissive

Technique set `07f52a25fafe3bac` (core 0xd90c0cc), unlit shader core 0xd90c634, 49 instructions, `CB0[5]`
(`asm\fireplace_log_unlit_core_d90c634.asm`). The smallest unlit emissive:

    E = emissiveMap.rgb * cb0[3].xyz * emissiveMap.a * vertexAlpha * cb0[2].z * F(cb0[2].w, cb0[4].x)
    if cb0[3].w:  E *= max(luma(E), 1e-4, X)

| slot | float | meaning | value |
|---|---|---|---|
| cb0[2].z | 10 | **scale** | 512 |
| cb0[2].w | 11 | view-angle power | 0 |
| cb0[3].xyz | 12-14 | **tint** | (0.418, 0.038, 0.014) |
| cb0[3].w | 15 | relative | **0** (absolute scene units) |
| cb0[4].x | 16 | invert | 0 |

`map * (214, 19.6, 7.4)` scene units times vertex alpha: image mean 0.0056 gives (1.2, 0.11, 0.04), brightest 1% (0.244)
gives (52, 4.8, 1.8) = 5,200 nits of red. Absolute, so it dims and brightens with the exposure; no flicker, no fog.

## 5. Summary for the exporter

| material | class | scale | tint | power | relative | mask | motion |
|---|---|---|---|---|---|---|---|
| t8_rock_coal_01_emissive_blend | unlit shell | 16 (f19) | white (f21-23) | 1 (f20) | yes, own luma (f24) | vertex alpha * map alpha | flicker 0.5..1 |
| t8_zm_esc_rubble_piles_junk_burn_emi | unlit shell | 4 | (1, 0.425, 0.109) | 1 | yes, own luma | vertex alpha * map alpha | flicker 0.3..1 |
| mtl_p7_zm_zod_matchstick_glow | lit | 12 (f28) | (0.305, 0.061, 0.003) (f32-34) | 1 (f29) | yes | reveal map * per-object P.y, * per-object P.x | scroll 2 UV/s |
| t8_zm_esc_lava_flow | lit, flow map | 22.63 (f22) | white (f24-26) | 0.25 (f23) | yes (f27) | map alpha | flow 0.08 |
| t8_zm_esc_lava_vertical_flow | lit, flow map | 22.63 | white | 0.25 | yes | map alpha | flow 0.2 |
| t8_zm_esc_lava_river_01_flow | lit, flow map | 45.25 | white | 0.4 | no | map alpha | flow 0.03 |
| mtl_p7_zm_ctl_fuse_* | lit, standard + 1 row | 4 (f12) | (0.050, 0.568, 1.0) (f16-18) | 0 | yes (f19) | map alpha | none |
| ..._power_source_screen_green | lit, layer | 2 (f39) | (0.0029, 0.0168, 0.0012) (f36-38) | 0 | yes (f40) | map alpha | flicker 0..1 |
| p7_zm_ctl_decal_emissive115_droplets_01 | unlit shell | 16 (f26) | (0.017, 0.283, 1.0) (f28-30) | 0.5 (f27) | yes, own luma (f31) | vertex alpha * mask * map alpha | none |
| mtl_p8_spa_fireplace_log_emissive | unlit shell | 512 (f10) | (0.418, 0.038, 0.014) (f12-14) | 0 | no | vertex alpha * map alpha | none |

Float numbers are for the live buffer (`emissive_params2.json` was never written). In the base-zone `materials.json` the
unlit classes use the **same** float index; the lit classes differ only in rows 0-2, as in part 1. When in doubt check the
value, not the index.

## 6. Shared constant blocks

Not finished. What is established:

- In the patched zone a material's constant pointers are either inline (FF marker) or block-5 pointers (0x5...), never
  anything else: 3,416 headers scanned, 1,957 inline, 873 shared **[P]**.
- The base-zone rule should carry over: pointer = block base + running sum of the inline constant bytes of the earlier
  materials **[I]**. It could not be confirmed, because the scan found only 3,416 of the 7,975 material headers, so the
  running sum is short and the base votes do not converge (best agreement 225 of 873).
- To finish it: a complete material-header walk of the patched zone (asset-list order), then one base per zone.
  Until then the 48 shared blocks are **[?]**; the 242 emissive materials in `mats_true.json` are all read from inline
  buffers and are not affected.
