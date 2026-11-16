# BO4 (T8) emissive materials: the standard lit class, read from the shader bytecode

<!-- toc -->
## Contents

- [0. Short answer](#0-short-answer)
- [1. How the shaders were found](#1-how-the-shaders-were-found)
- [2. Which shader each example uses **[P]**](#2-which-shader-each-example-uses-p)
- [3. The material constant buffer (cb0) **[P]**](#3-the-material-constant-buffer-cb0-p)
- [4. The formula, step by step **[P]**](#4-the-formula-step-by-step-p)
  - [4a. Parallax UV (lines 925-939)](#4a-parallax-uv-lines-925-939)
  - [4b. Emissive map, tint, view-angle term (lines 939-980)](#4b-emissive-map-tint-view-angle-term-lines-939-980)
  - [4c. Scale and the relative flag (lines 3381-3402)](#4c-scale-and-the-relative-flag-lines-3381-3402)
  - [4d. Flicker, 7-row class only (hot coal; `asm\coal_hot_lit_esc_d261e15.asm` lines 957-969)](#4d-flicker-7-row-class-only-hot-coal-asmcoal_hot_lit_esc_d261e15asm-lines-957-969)
  - [4e. What X (cb2[110].x) is **[I]**](#4e-what-x-cb2110x-is-i)
- [5. Other emissive classes **[P for the tail, fresnel/parallax not read in each]**](#5-other-emissive-classes-p-for-the-tail-fresnelparallax-not-read-in-each)
- [6. Worked numbers](#6-worked-numbers)
  - [6a. Lamp-post globe (scale 64, power 6, tint (1, 0.775, 0.617), relative, depth 0.05)](#6a-lamp-post-globe-scale-64-power-6-tint-1-0775-0617-relative-depth-005)
  - [6b. Hot coal (scale 256, power 1, tint white, relative, flicker 0.7..1.0)](#6b-hot-coal-scale-256-power-1-tint-white-relative-flicker-0710)
  - [6c. The other examples](#6c-the-other-examples)
- [7. To copy this](#7-to-copy-this)
- [8. Not found / open](#8-not-found--open)
<!-- /toc -->

Offline read of the DXBC in your own zones. Maths and behaviour only, no shader code.
Marks: **[P]** proven from bytecode / zone bytes, **[I]** inferred, **[?]** unknown.
D3D asm note: `exp` is 2^x, `log` is log2, so `log, mul k, exp` is pow(x, k).

## 0. Short answer

Every emissive material read is drawn by a **forward lit** pixel shader (one colour target, whole light loop inline),
not the g-buffer. Emission is added to the lit colour **before fog and before exposure** **[P]**:

    uvE   = uv - 0.5 * depth * (V.T, V.B) / (N.V)                     parallax, only when N.V > 0
    e     = emissiveMap(uvE)                                          rgb and alpha both used
    F     = 1                               if power == 0
          = pow(1 - sat(N.V), power)        if invert flag
          = pow(sat(N.V), power)            otherwise                 N = vertex normal (not normal-mapped), faced to the viewer
    E0    = e.rgb * tint * e.a * F * (1 - decalCoverage) [* flicker]
    Llit  = dot(litColour2020, (0.299, 0.587, 0.114))                 the surface's own lit radiance, just computed
    m     = relative ? max(Llit, 1e-4, X) : 1                         X = cb2[110].x
    out   = litColour + M709to2020 * (E0 * m * scale)
    out   = fog(out) ; out *= cb2[110].y (exposure)

- "float 9" **is** the view-angle power: `pow(N.V, 6)` on the lamp-post globe **[P]**. This is what confines the glow.
- Base colour / albedo does **not** multiply emission **[P]**. It only enters through `Llit` (the floor of `m`).
- There is no distance term **[P]**.
- Emission is **exposure-compensated** when the material's `relative` flag is set **[P for the maths, I for X]**:
  X is read as 1 / exposure, so `scale` is then a multiple of *exposed* white (1.0 after exposure, mid grey 0.18),
  not of 100 nits. With the flag clear, `scale` is plain scene units (1.0 = 100 nits) and is exposed like everything else.

## 1. How the shaders were found

Material -> technique set -> shaders, in the **patched** zones (`work17\dec\*.ff.dec`, same bytes as `cache\ffx\patched`):

- Material header (patched layout, name hash at +8): technique set pointer at +0x38. A small value `0x4000000000000000 | (v + 1)`
  is an alias to an asset-list slot: `index = (v - B) / 16`, B from `t8zone.asset_list` **[P]**.
- zm_escape's list holds 664 technique sets in one run (indices 19358..20021). Their bodies/stubs in the file are in
  name-hash order except ten written early as dependencies; **list order = ascending name hash** **[I]**, checked by the
  result: every material's shader declares `CB0[n]` with n = its buffer size / 16 (5 rows for 80 bytes, 7 for 112) **[P]**.
- Technique set body = 0xa8 bytes: name, 0, hash, 0, 8-byte word, 15 technique pointers from +0x28. A stub is the name with
  bit 63 set and 0xa0 zero bytes: the body is in a zone loaded earlier **[P]**.
- Shader struct = 0x28 bytes: name, 16 zero bytes, bytecode pointer, size. The pointer is either inline (DXBC follows) or an
  alias to bytecode written earlier; aliases are placed by size and by the local file/virtual offset **[P struct, I placement:
  one candidate in every case used here]**.
- The lamp-post's technique set `7615346333341f5d` is a stub in zm_escape, core_common and zm_common. Its body is in the
  **patched core_bootstrap** (`zone_tmp\core_bootstrap.fd.patch.dec` 0x150d3d9, pulled with `pull.py`) **[P]**.

Scripts here: `ts2.py` (technique set bodies), `mats.py` (material -> technique set), `tsdump.py <zone> <hexoffset>` (technique set
-> shaders), `truecb.py` (live constant buffers), `classes.py` (emission tail of every emissive technique set),
`export_params.py` (-> `emissive_params.json`), `pull.py` (zone out of the CASC), `dumpall.py` (disassemble everything to `all\`,
311 MB, deleted after use).

## 2. Which shader each example uses **[P]**

| material | technique set | lit pixel shader (zone, offset) | listing |
|---|---|---|---|
| mtl_p8_zm_esc_light_lamppost_ems_on | 7615346333341f5d (core_bootstrap patched 0x150d3d9) | bootp 0x13aa2d1 (+0x13c2029, 0x13da20d variants) | `asm\lamppost_lit_bootp_13aa2d1.asm` |
| mtl_p8_light_bulb_filament, mtl_p8_zm_esc_light_bulb_filament, _off | 4021c1f92b4f6277 (esc 0xdbb766d) | esc 0xdbb7e15 (+5 variants) | `asm\filament_lit_esc_dbb7e15.asm` |
| t8_rock_coal_01_emissive_blend_hot (two instances) | 11fa8c1960248eb4 (esc 0xd261619), 5f24658ab1df7801 (esc 0xe2b348d) | esc 0xd261e15, esc 0xe2b4415 | `asm\coal_hot_lit_esc_d261e15.asm`, `coal_hot_lit2_esc_e2b4415.asm` |
| mtl_p8_zm_esc_lab_monitor_glass (also the candles) | 537f7652a72f872c (core 0x132a8b74) | core 0x132a9b70 | `asm\lab_monitor_lit_core_132a9b70.asm` |
| t7_zm_mob_window_cellhouse_ext_yellow/blue_emissive, garage window | 43c57282a9fe1f23 (esc 0xdc63fbd) | esc 0xdc64f95 | `asm\window_yellow_lit_esc_dc64f95.asm` |
| t7_slu_metal_garage_window_emissive (second instance) | 599e03b1605a93b5 (esc 0xe1e6365) | esc 0xe1e7385 | `asm\window_garage_lit_esc_e1e7385.asm` |

All of these are the same class: one target, `CB0[5]` (or `[7]` with flicker), `CB2[120]`, `CB3[121]`, about 3,150 to 3,660 instructions.
The technique lists are in `asm\techset_*.txt`. The other techniques in each set are depth / velocity / shadow passes with no
material constants. No g-buffer writer is bound by any of them **[P]**.

## 3. The material constant buffer (cb0) **[P]**

Read from the live zone at `header + 0x140 + technique slot data + 0x100 * i`; the second buffer (i = 1) is cb0.
Lamp-post globe, as stored:

    cb0[0] = (0, 0.558, 0.039, 0.0)        cb0[1] = (1.0, 0.0, 7.0, 0)       cb0[2] = (0, 64.0, 6.0, 0)
    cb0[3] = (1.0, 0.775, 0.617, 1.0)      cb0[4] = (0, 0, 0.05, 0)

| slot | float | meaning | evidence |
|---|---|---|---|
| cb0[0].yzw | 1-3 | base colour tint: `albedo = colorMap.rgb * lerp(1, tint, mask)`, mask = colorMap.a (or tintMask.r) | `add cb0[0].yzw, -1 ; mad mask ; mul` |
| cb0[1].x | 4 | normal map strength | `mad cb0[1].x, (n - 0.5), 0.5` |
| cb0[1].y, .z | 5, 6 | gloss min, max on the 0..17 scale (max only when there is no gloss map) | `lerp(cb0[1].y, cb0[1].z, gloss)`, `* 0.058824` |
| cb0[2].x | 8 | non-zero = skip the sun and its shadow cascades (1 on the filaments) | `if_z cb0[2].x` around the cascade loop |
| **cb0[2].y** | 9 | **emissive scale** | `mul m, cb0[2].y` |
| **cb0[2].z** | 10 | **view-angle power** (the "float 9" of materials.json) | `log N.V ; mul cb0[2].z ; exp` ; `eq cb0[2].z, 0 -> 1` |
| **cb0[3].xyz** | 12-14 | **emissive tint** | `mul emissiveMap.rgb, cb0[3].xyz` |
| **cb0[3].w** | 15 | **relative flag** (exposure-compensated) | `movc m, cb0[3].w, max(...), 1.0` |
| cb0[4].x | 16 | invert the view-angle term (rim glow) | `movc F, cb0[4].x, pow(1-N.V), pow(N.V)` |
| cb0[4].z | 18 | emissive parallax depth | `add cb0[4].z, 1e-5` then the UV offset |
| cb0[5].xyz | 20-22 | flicker: lookup u, phase offset, speed (7-row class only) | see 4d |
| cb0[6].xyz | 24-26 | flicker: min, max, power | see 4d |

**Layout warning.** `t8mat\materials.json` and `t8light\emissive_materials.json` were read from the *base* zone, whose first two rows are
packed differently (tint at floats 0-2, gloss at 4-5). From row 2 on the values agree with one shift in row 2 only:

| value | base-zone json float | live cb0 |
|---|---|---|
| sun-shadow-off flag | 7 | cb0[2].x |
| scale | 8 | cb0[2].y |
| power | 9 | cb0[2].z |
| tint | 12-14 | cb0[3].xyz |
| relative flag | 15 | cb0[3].w |
| invert flag | 16 | cb0[4].x |
| parallax depth | 18 | cb0[4].z |
| flicker | 20-22, 24-26 | cb0[5].xyz, cb0[6].xyz |

So an exporter working from materials.json can keep using floats 8, 9, 12-14 and add 15, 16, 18 (and 7).

## 4. The formula, step by step **[P]**

Listing line numbers are for `asm\lamppost_lit_bootp_13aa2d1.asm`.

### 4a. Parallax UV (lines 925-939)

    V   = normalise(camera - position)                 the shader input is position relative to the camera
    N   = normalise(vertex normal) * facing            flipped on back faces, so N.V > 0 on anything visible
    T,B = tangent, bitangent built from screen derivatives of position and uv, normalised, * facing
    off = (N.V > 0) ? -(V.T, V.B) / (N.V) : 0
    uvE = ((uv * 2 - 1) + off * (depth + 1e-5)) * 0.5 + 0.5

In UV units the shift is `0.5 * depth * tan(view angle)` away from the viewer: the emissive pattern sits "inside" the surface.
Lamp-post depth 0.05: 0.025 UV at 45 degrees, 0.043 at 60 degrees. Other materials use 0.01 to 1.0; most use 0.

### 4b. Emissive map, tint, view-angle term (lines 939-980)

    e   = emissiveMap(uvE)                             same sampler as the colour map
    c   = e.rgb * tint
    F   = power == 0 ? 1 : invert ? pow(1 - sat(N.V), power) : pow(sat(N.V), power)
    E0  = c * F * e.a * (1 - decalCoverage)

- The N in F is the interpolated **vertex** normal, not the normal-mapped one.
- The emissive map's alpha multiplies emission. (The lamp-post map's alpha is 1 everywhere in the exported image; the filament
  map's alpha is the filament shape.)
- `decalCoverage` is the summed alpha of forward-blended decals on the surface; 0 without decals.
- No albedo, no vertex colour, no distance, no light term here.

### 4c. Scale and the relative flag (lines 3381-3402)

    lit  = diffuseLight * albedo2020 + specLight * F0_2020 + (1 - F0_2020) * extra        Rec.2020, scene units
    Llit = max(dot(lit, (0.299, 0.587, 0.114)), 1e-4)
    m    = relative ? max(Llit, X) : 1                 X = cb2[110].x
    m   *= scale
    E    = E0 * m                                      Rec.709 primaries
    lit += M * E                                       M = 709 -> 2020: (0.627404, 0.329283, 0.043313 / 0.069097, 0.919540, 0.011362 / 0.016391, 0.088013, 0.895595)
    alphaOut = alpha + sat(dot(E / max(m, 1), (0.299, 0.587, 0.114)))

Then, unchanged from the lit spec: volumetric fog (transmittance * colour + in-scatter), height fog, `* cb2[110].y`,
zero below 6.1e-5, clamp to (65024, 65024, 64512). So emission is fogged and exposed with the surface.

### 4d. Flicker, 7-row class only (hot coal; `asm\coal_hot_lit_esc_d261e15.asm` lines 957-969)

    phase = frac(seed.x + seed.y + seed.z + cb0[5].y)          seed = a constant-interpolated vertex output, per instance [I]
    f     = flickerLookupMap(cb0[5].x, phase + time * cb0[5].z).r        time = cb2[89].w
    E0   *= lerp(cb0[6].x, cb0[6].y, pow(|f|, cb0[6].z))

Hot coal: u 0.4, phase 0.4, speed 0.25, range 0.7..1.0, power 0.2: a slow shimmer between 70% and 100%.

### 4e. What X (cb2[110].x) is **[I]**

Not set by any shader; it comes from the CPU with the exposure (`cb2[110].y`). Evidence for X = 1 / exposure:

- The deferred lighting shader multiplies the **previous frame's colour** (screen-space reflection tap) by `cb2[110].x`, adds it to
  scene-unit reflections, and the sum is multiplied by `cb2[110].y` at the end (`shaders\asm\boot_b4fc20_deferred.asm` line 302, 1081).
  The stored frame is already exposed, so X has to undo an exposure **[P usage, I meaning]**.
- 1,505 material/FX shaders use it only as `max(luminance, X)` or `colour * X`, always followed by `* cb2[110].y`.
- Unlit emissive shaders (no lit colour) use `m = max(X, 1e-4)` (`asm\unlit_emissive_esc_d4dd5ad.asm`).
- Against: a border-debug shader writes `(X, 0, 0.5 X)` with no exposure multiply (`asm\debug_border_bootp_2397d.asm`),
  which would also fit a fixed display white level. Not resolvable offline **[?]**.

With X = 1 / exposure, a relative emissive lands at `E0 * scale * max(1, Llit * exposure)` in **exposed** units: constant on
screen whatever the exposure, and never dimmer than `scale` times the lit surface under it. The exact value of X at run time,
and whether it is this frame's or last frame's exposure, is **[?]**.

## 5. Other emissive classes **[P for the tail, fresnel/parallax not read in each]**

`classes.json` lists every emissive technique set of zm_escape with its shaders and the three instructions after the `X` floor.
All share `m = max(Llit, 1e-4, X)`, an optional relative flag, a scale, then 709 -> 2020 and add. Only the slots move:

| class (cb0 rows) | scale | relative flag | notes |
|---|---|---|---|
| standard lit emissive (5) and with flicker (7): 126 materials | cb0[2].y | cb0[3].w | section 4; lamps, bulbs, windows, monitors, candles, coal |
| layered / blend variants (6, 8) | cb0[3].x or cb0[3].y | cb0[4].w | |
| flow / lava (8) | cb0[5].z | cb0[6].w | t8_zm_esc_lava_* |
| (6) | cb0[3].w | cb0[5].x | |
| (10) | cb0[7].z | cb0[8].w | |
| multi-layer (10-21 rows) | per layer | none: always relative | `max Llit, X ; mul rgb` |
| unlit emissive (5-18 rows, about 650 instructions) | cb0[2].x (5-row) | cb0[3].w, cb0[7].w | `m = max(X, 1e-4)`, power cb0[2].y, invert cb0[4].x, depth cb0[4].z |
| core_bootstrap lit variants | - | - | same tail (`asm\boot_lit_relative_bootp_12379d5.asm`) |

No "ems_on" technique exists: `_ems_on` / `_off` are material instances of the standard class that differ only in constants
(filament_off: scale 1.5e-5, flag 0). 62 emissive materials point at their technique set by direct address rather than a list
alias and 48 share a constant block; those were not followed **[?]**.

## 6. Worked numbers

Units: "exposed" = after `* exposure`, before the tone map (1.0 = exposed white, 0.18 = mid grey). Scene units (1.0 = 100 nits)
are exposed / exposure = exposed * X. Relative materials are fixed in exposed units; their scene-unit radiance depends on X **[I]**.
Map statistics are from the exported images, sRGB decoded.

### 6a. Lamp-post globe (scale 64, power 6, tint (1, 0.775, 0.617), relative, depth 0.05)

Emissive map: linear mean (0.786, 0.624, 0.383), near-white (0.99) over about two thirds. `map * tint`: mean (0.786, 0.484, 0.236),
white areas (1.0, 0.775, 0.617).

    E(N.V) = map * tint * (N.V)^6 * 64 * max(1, Llit * exposure)        exposed units

| N.V | angle off the normal | (N.V)^6 | mean colour, exposed | white-area colour, exposed |
|---|---|---|---|---|
| 1.0 | 0 | 1.000 | (50.3, 31.0, 15.1) | (64.0, 49.6, 39.5) |
| 0.9 | 26 | 0.531 | (26.7, 16.5, 8.0) | (34.0, 26.4, 21.0) |
| 0.8 | 37 | 0.262 | (13.2, 8.1, 4.0) | (16.8, 13.0, 10.4) |
| 0.7 | 46 | 0.118 | (5.9, 3.6, 1.8) | (7.5, 5.8, 4.6) |
| 0.6 | 53 | 0.0467 | (2.3, 1.4, 0.71) | (3.0, 2.3, 1.8) |
| 0.5 | 60 | 0.0156 | (0.79, 0.48, 0.24) | (1.0, 0.78, 0.62) |
| 0.4 | 66 | 0.0041 | (0.21, 0.13, 0.062) | (0.26, 0.20, 0.16) |
| 0.3 | 73 | 0.00073 | (0.037, 0.023, 0.011) | (0.047, 0.036, 0.029) |
| 0.2 | 78 | 0.000064 | (0.003, 0.002, 0.001) | (0.004, 0.003, 0.003) |

- Scene units: multiply by X. At an exposure of 8 the face-on mean is (6.3, 3.9, 1.9) = 630 / 390 / 190 nits; at exposure 1 it is the table.
- In Rec.2020 the face-on mean is (42.4, 32.1, 17.1).
- On a sphere (N.V = sqrt(1 - r^2), r = fraction of the silhouette radius): half brightness at r = 0.45, 10% at r = 0.73,
  1% at r = 0.89. The mean colour drops below exposed white at r = 0.77 (blue), 0.83 (green), 0.85 (red).
- The mean of (N.V)^6 over the disc is exactly 1/4, so the globe sends a quarter of the light of the flat
  `map * tint * 64` disc into bloom.
- Colour: hue is the map times the tint, orange (R:G:B = 1 : 0.62 : 0.30 on average). The centre is far above white and will
  clip pale through the tone map; from about r = 0.75 outwards it is unclipped, saturated orange falling to nothing at the
  silhouette, where only the lit glass shows (albedo white * (0.558, 0.039, 0): deep red-orange). The base tint does not colour
  the emission.
- Grazing: (N.V)^6 removes it; in addition the parallax shifts the map by 0.025 * tan(angle) UV.
- `Llit` only matters if the lit glass exceeds exposed 1.0 (direct sun); then emission scales up with it.

So the port's "big white disc" is the missing `(N.V)^6`: the same material without it is 64 * (0.79, 0.48, 0.24) across the whole
silhouette, four times the bloom energy with no falloff.

### 6b. Hot coal (scale 256, power 1, tint white, relative, flicker 0.7..1.0)

Emissive map: almost black with small hot cracks. Linear mean (0.0151, 0.0011, 0.0004); brightest 1% mean (0.311, 0.062, 0.011);
brightest 0.1% (0.770, 0.304, 0.052); maximum (0.965, 0.708, 0.195).

    E(N.V) = map * flicker * N.V * 256 * max(1, Llit * exposure)        exposed units, flicker in 0.7..1.0

| | face-on (N.V = 1), flicker 1 | N.V = 0.5 | N.V = 0.2 |
|---|---|---|---|
| mean of the surface | (3.86, 0.29, 0.11) | (1.93, 0.15, 0.05) | (0.77, 0.06, 0.02) |
| brightest 1% | (79.6, 15.9, 2.9) | (39.8, 8.0, 1.4) | (15.9, 3.2, 0.6) |
| brightest 0.1% | (197, 78, 13) | (99, 39, 6.6) | (39, 16, 2.7) |
| maximum | (247, 181, 50) | (123, 91, 25) | (49, 36, 10) |

- 27% of texels exceed exposed 1.0 face-on, 1.6% exceed 10: a dim red body with a small orange-to-yellow core that clips.
- The falloff is plain cosine (power 1), so it stays bright to steep angles; flicker takes it down to 70%.
- Scene units: multiply by X. If the port applies 256 in plain scene units and then a night exposure below 1, or reads the map
  without the relative floor, it comes out dull, as seen.

### 6c. The other examples

| material | scale | power | tint | relative | face-on exposed peak (map = 1) |
|---|---|---|---|---|---|
| mtl_p8_light_bulb_filament | 32 | 0 | (1, 0.474, 0.205) | yes | (32, 15.2, 6.6), no angle term; map alpha masks the wire |
| mtl_p8_zm_esc_light_bulb_filament | 16384 | 0 | (0.863, 0.395, 0.006) | yes | (14142, 6478, 98): always clipped, a bloom source |
| mtl_p8_light_bulb_filament_off | 1.5e-5 | 0 | grey | no | off |
| mtl_p8_zm_esc_lab_monitor_glass | 4 | 5 | (0.068, 0.314, 0.255) | yes | (0.27, 1.26, 1.02) * (N.V)^5 |
| t7_zm_mob_window_cellhouse_ext_yellow_emissive | 32 | 0 | white | yes | 32 * map |
| t7_zm_mob_window_cellhouse_ext_blue_emissive_01 | 8 | 0 | (0.071, 0.245, 0.275) | yes | (0.57, 1.96, 2.20) * map |
| t7_slu_metal_garage_window_emissive | 16 | 3 | (1, 0.807, 0.376) | **no** | scene units: (16, 12.9, 6.0) * (N.V)^3 * map = up to 1,600 nits, then exposed |
| mtl_p8_zm_esc_candle_med_melt_on | 8 | 0 | (1, 0.510, 0.205) | **no** | scene units: (8, 4.1, 1.6) * map |

## 7. To copy this

Per material, write (all in `emissive_params.json`: 78 standard-class materials filled in, 48 more share a constant block that was not followed; from `t8mat\materials.json` use the
base-zone float numbers of section 3):

| value | live cb0 | base json float | use |
|---|---|---|---|
| scale | cb0[2].y | 8 | multiplier |
| power | cb0[2].z | 9 | view-angle exponent; 0 = off |
| tint | cb0[3].xyz | 12-14 | linear, Rec.709 |
| relative | cb0[3].w | 15 | 1 = exposure-compensated |
| invertFresnel | cb0[4].x | 16 | 1 = pow(1 - N.V) |
| parallaxDepth | cb0[4].z | 18 | UV shift 0.5 * depth * tan |
| noSunShadow | cb0[2].x | 7 | lighting only |
| flicker u, phase, speed / min, max, power | cb0[5].xyz / cb0[6].xyz | 20-22 / 24-26 | 7-row materials with flickerLookupMap |
| emissive map | texture | emissiveMap | rgb **and** alpha |

Shader side:

1. Draw emissive materials lit as usual, then add `E` to the lit colour before fog and exposure.
2. `F = power == 0 ? 1 : pow(invert ? 1 - NdotV : NdotV, power)` with the **vertex** normal faced to the viewer.
3. `E0 = emissiveMap(uvE).rgb * tint * emissiveMap.a * F` (+ flicker). Do not multiply by albedo or base tint.
4. `m = relative ? max(luma(lit), 1 / exposure) : 1`, luma weights (0.299, 0.587, 0.114); `E = E0 * m * scale`.
   If the engine does not pre-expose, the same thing is: relative emission is added **after** exposure as `E0 * scale`
   (times `max(1, exposed luma of the lit surface)`); non-relative emission is added in scene units before exposure.
5. Convert `E` 709 -> 2020 if the lit colour is in 2020; fog it with the surface.
6. Parallax is optional polish except where depth is large (0.1 to 1.0 on a few materials).

## 8. Not found / open

- The run-time value of `cb2[110].x`, and proof that it is 1 / exposure **[?]** (section 4e). Everything in section 6 in exposed
  units depends on it; the shapes (angle falloff, colour, ratios between materials) do not.
- Blend state of the lit emissive passes, so what the `alphaOut` term does on screen **[?]**.
- Emissive textures' colour space: taken as sRGB-decoded by the sampler, tints linear **[I]**.
- The 62 direct-pointer and 48 shared-constant emissive materials, and the fresnel/parallax slots of the non-standard classes.
- List order = name order for technique sets is inferred (section 1).
