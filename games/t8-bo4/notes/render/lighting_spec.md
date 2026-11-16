# BO4 (T8) lighting, fog and tone map: read from the shader bytecode

<!-- toc -->
## Contents

- [0. Where the shaders are](#0-where-the-shaders-are)
- [1. Frame structure **[B]**](#1-frame-structure-b)
- [2. Material inputs and BRDF **[B]**](#2-material-inputs-and-brdf-b)
- [3. Punctual lights **[B formula, I field mapping]**](#3-punctual-lights-b-formula-i-field-mapping)
  - [type 4 (omni / spot; 2791 in zm_escape)](#type-4-omni--spot-2791-in-zm_escape)
  - [type 2 (rectangle area light; 137 in zm_escape)](#type-2-rectangle-area-light-137-in-zm_escape)
- [4. Sun / moon **[B]**](#4-sun--moon-b)
- [5. Indirect light **[B]**](#5-indirect-light-b)
- [6. Fog **[B formula, I field mapping]**](#6-fog-b-formula-i-field-mapping)
  - [6a. Froxel volume](#6a-froxel-volume)
  - [6b. World height fog (cb3[60..62])](#6b-world-height-fog-cb36062)
  - [6c. Atmospheric extinction (cb3[82..84])](#6c-atmospheric-extinction-cb38284)
  - [6d. Box fog / water volume (cb3[88..91])](#6d-box-fog--water-volume-cb38891)
- [7. Exposure **[B]**](#7-exposure-b)
- [8. Tone map, grade LUT, output](#8-tone-map-grade-lut-output)
  - [8a. Film-curve path (SDR) **[B]** (boot 0x11f43f0 / 0x130d950 / 0x141a41c)](#8a-film-curve-path-sdr-b-boot-0x11f43f0--0x130d950--0x141a41c)
  - [8b. HDR-master path **[B]**](#8b-hdr-master-path-b)
  - [8c. Bloom, emissive](#8c-bloom-emissive)
- [9. Other look-shaping passes](#9-other-look-shaping-passes)
- [10. What an engine needs to match this](#10-what-an-engine-needs-to-match-this)
- [11. Not found / open](#11-not-found--open)
<!-- /toc -->

Offline read of the DXBC in your own zones. Maths and behaviour only, no shader code.
Marks: **[B]** read from bytecode, **[I]** inferred (bytecode + zone data fit), **[?]** not found / unknown.

D3D asm note: `exp` is 2^x and `log` is log2. Every "2^" below is literal. Where the source clearly meant
e^x the compiler left a 1.442695 or 0.693147 factor, and that is shown.

## 0. Where the shaders are

| zone dump | what is in it |
|---|---|
| `cache\ffx\core_bootstrap.ff.dec` (base zone, 34 MB, kept) | the engine's own shaders: 425 compute (deferred lighting, froxel fog, LUT builders, exposure), 294 pixel (post, final output) |
| `cache\ffx\patched\core_common.fd.patch.dec`, `zm_escape.fd.patch.dec`, `zm_common.fd.patch.dec` | material shaders: g-buffer writers (3 or 4 targets) and forward-lit shaders (1 target) that carry the whole light loop inline |

The reflection chunk (RDEF) is stripped from every blob (only ISGN/OSGN/SHEX), so there are **no names**:
constants are identified by register (cb2 = per-view, cb3 = per-scene lighting, cb0 = material, cb8+ = pass constants).
The game exe holds no plain DXBC. No shader hash table was decoded; a shader is identified by zone + file offset + the
16-byte DXBC checksum at offset+4.

Tools here: `scan.py` (index DXBC in a dump), `d3d.py <zone> <hexoffset>` (D3DDisassemble through ctypes; zones `boot`,
`core`, `esc`, `zmc`), `feat.py` / `feat_boot.py` (feature index), `zscan.py` (pull a zone out of the CASC, decompress with
ACTS, count shader kinds), `boot_list.txt` (every core_bootstrap pixel/compute shader with constants). Listings are in `asm\`.

| role | zone, offset | listing |
|---|---|---|
| deferred lighting (compute, smallest of 113 variants) | boot 0xb4fc20 | `asm\boot_b4fc20_deferred.asm` |
| forward lit, standard BRDF + all light types | core 0xe82c23c | `asm\lit_core_e82c23c.asm` |
| forward lit, simple (light loop easiest to read) | core 0xd166698 | `asm\lit_core_d166698.asm` |
| forward lit, sun + probes + all fog terms | esc 0xe8b91fd | `asm\lit_esc_e8b91fd.asm` |
| g-buffer writer | esc 0xdca7631 | `asm\gbuf4_esc_dca7631.asm` |
| froxel fog lighting / integrate | boot 0xf49310 / 0x3fc80 | `asm\boot_f49310_froxel.asm`, `asm\boot_3fc80_froxel_integrate.asm` |
| auto exposure | boot 0x270924 | `asm\boot_270924.asm` |
| SDR film curve + bloom + grade LUT | boot 0x11f43f0 (with vignette: 0x130d950) | `asm\boot_11f43f0.asm`, `asm\boot_130d950.asm` |
| HDR-master output: PQ -> 32^3 LUT -> dither | boot 0x130a578, 0x1404220 | `asm\boot_130a578.asm` |
| HDR -> SDR display LUT builder (BT.2390 + trim LUT) | boot 0x3d39c (4-output: 0x714250) | `asm\boot_3d39c.asm` |
| grade LUT composer (strip blend, tonal mixers) | boot 0xe059c, strip -> 3D: 0x6b4f8c | `asm\boot_e059c.asm` |
| LUT blend in PQ space | boot 0x6d3bdc | `asm\boot_6d3bdc.asm` |

The forward-lit and deferred shaders carry the same constants (0.375892, 0.62, 17, LTC fits, 0.488603) and the same GPU light
struct (stride 336), so the forward listing is a valid read of the deferred maths **[B]**.

## 1. Frame structure **[B]**

1. Opaque: g-buffer. o0 albedo, o1 = normal xy (tangent-basis encoding) + gloss in z (`gloss*0.497556+0.001466`) + material id/3 in w,
   o2 = (F0, ?, material AO, ?), o3 = motion vectors (4-target variants). Chroma of o2 is checkerboarded and rebuilt from 4 neighbours.
2. Deferred lighting in a compute shader (per pixel: sun, clustered punctual lights, probes, fog), writes R11G11B10 HDR.
3. Translucents / FX: forward, same functions inline.
4. Froxel volumetric fog built by compute, sampled by every lit pixel (so it is applied in the lighting shader, not as a post pass).
5. Exposure is **pre-applied**: every shader ends `colour *= cb2[110].y`, zeroes values < 6.1e-5, clamps to (65024, 65024, 64512).
6. Post: bloom, tone map / display LUT, dither.

Colour space: all lighting is done in **Rec.2020 linear**. Albedo and tints are converted with the 709->2020 matrix
(0.627404 0.329283 0.043313 / 0.069097 0.919540 0.011362 / 0.016391 0.088013 0.895595) before use **[B]**.
Scene unit: 1.0 = 100 nits in the output stage (section 5) **[B]**.

Clusters: 64x64 pixel tiles (`pixel >> 6`), 16 depth slices: `slice = min(15, linearDepth * 1/128)` (cb3-scaled depth in units),
a uint texture array holds 32-bit masks per (tile, slice, word); bits are walked with firstbit_lo. Each entry is first rejected
against an AABB (centre + half extents as f16) from a 76-byte bounds buffer. Lights use mask texture t6 / struct buffer t12
(336 B); probes use t7 / t15 (224 B) + t16 (96 B blend volumes) **[B]**.

## 2. Material inputs and BRDF **[B]**

- gloss g in 0..1: `g = max(sat(glossRange/17), 0.01)` where glossRange = lerp(cb0 min, cb0 max, glossMap) on a 0..17 scale.
- normal-variance (Toksvig style) from the normal map's third channel v: `var = min(v*v/3, 1)`;
  `g' = max(-log2(2^(-17 g) + var) / 17, 0)`.
- specular power `P = 2^(17 g')`, **alpha^2 = 2 / (P + 2)**, alpha = sqrt(alpha^2), perceptual roughness r = sqrt(alpha).
- F0 from the spec colour (g-buffer o2.x, 0.04 for plain dielectrics; metals put colour in F0 and darken albedo).

Direct specular (lights are "pi-less": no 1/pi anywhere, colour already carries it):

    D   = alpha^2 / (NdotH^2 (alpha^2 - 1) + 1)^2
    k   = ((r + 1) / 2)^2 / 2                         (= (r+1)^2 / 8)
    Vis = 1 / ((NdotL (1-k) + k) (NdotV (1-k) + k))
    F   = F0 + (1 - F0) (1 - VdotH)^5
    spec = 0.25 * D * Vis * F * NdotL * lightSpecScale

Multi-scatter gain after the sum: `spec *= 1 + F0 * (1/E - 1)`, E from a 2D LUT (t0) indexed (alpha, sqrt(1 - NdotV)).

Direct diffuse (roughness-aware, not plain Lambert):

    t    = 1 - NdotL * (1 - 0.5 NdotV)
    diff = lerp(NdotL, 0.62 (1 - t^2), alpha)          then * albedo * lightColour

Two-sided / thin materials keep separate front and back sums with |NdotL|.

## 3. Punctual lights **[B formula, I field mapping]**

GPU light record, 336 bytes (offsets in bytes; filled by the engine from the 600-byte zone light):

| off | meaning |
|---|---|
| 12 | position (camera-relative world, units = inches) |
| 24, 28, 32 | colour * intensity, linear Rec.2020 |
| 36 | specular scale |
| 40 | axis = direction TO the light (aim = -axis) |
| 52 | packed: bits 0-15 shadow slice, bits 23-26 second shadow light |
| 56 | flags: bits 0-2 type (4 or 2), 3-5 shadow mode (1 = none), 6 = 2D (spot) shadow else cube, 7-14 cookie index + 1, 15 = inverted cone |
| 60-135 | shadow view-projection rows, atlas scale/offset |
| 144 | cosOuter (cos of half outer fov; <= -1 means no cone) |
| 148 | feather (fraction of the cone, 0 = hard / no cone term) |
| 152 | apex pull-back distance |
| 156 | shadow filter radius scale |
| 160-183 | cookie projection (two rows) |
| 208, 212 | cube-shadow depth remap |
| 216, 220 | d^2 fade: scale, offset |
| 224 | inverse-square cutoff c |
| 228 | bulb radius R |
| 232, 236 | axial fade: scale, offset |
| 256-300 | type 2 only: four quad corners (relative) |
| 304-335 | type 2 only: three plane fade (scale, offset) pairs |

### type 4 (omni / spot; 2791 in zm_escape)

    L   = lightPos - P,  d2 = |L|^2
    w   = sat( (1/(d2 + 1) - c) / (1 - c) )            windowed inverse square, +1 inch^2 bias
    f1  = sat( d2 * s1 + o1 )                           linear-in-d^2 fade
    f2  = sat( dot(L, axis) * s2 + o2 )^2               fade along the axis
    cone: v = normalize(L + apex * axis);  x = dot(v, axis)
          t = sat( ((x - cosOuter) / (1 - cosOuter)) / feather )
          spot = t^2                                    (1 if feather <= 0 or cosOuter <= -1)
    atten = w * f1 * f2 * spot

- No smoothstep and no exponent other than the square. The cone is measured from a point `apex` behind the light, so the cone
  is one bulb radius wide at the light itself.
- Units: inches. With the +1 bias, intensity I gives I/(d^2+1); the earlier finding "colour ~ 1600 * 2^stops, 1.0 at 40 units" fits **[I]**.
- Zone field mapping **[I]**: `colour` -> 24..32; `cosHalfFovOuter` -> cosOuter; `c0` (fov_feather) -> feather;
  `d4` -> apex: it equals bulbRadius / tan(fovOuter/2) on every light checked (2 / tan 50 deg = 1.678, 2 / tan 30 deg = 3.464);
  `bulb` -> R; `radius` -> c = 1/(radius^2 + 1) so the window reaches 0 exactly at the radius (not readable from the shader,
  the engine fills it) **[I]**. `c8`, `d0`, `b4` -> one of (s1, o1), (s2, o2), specular scale: **[?]**, set on the CPU.
  A safe stand-in is s1 = 0, o1 = 1, f2 = 1.
- The old guess `(1-(d/r)^4)^2` is **wrong**: use the window above.

Bulb radius R > 0 (sphere light):

    spec numerator *= alpha^1.49785 / (0.375892 * R / d + 0.962406 * alpha^1.49785)     (energy normalisation, alpha^2 raised to 0.748925)
    L_spec = L + c2r * min(1, R / |c2r|),  c2r = dot(L, Rv) Rv - L                      (Rv = reflection vector; representative point)

Diffuse uses the centre direction.

Shadows: spot = one 2D array slice, depth compare; 8-tap rotated disc (taps (±0.808,∓0.808), (0,-1), (0.606,0.606), (-0.714,0),
(0.404,-0.404), (0,0.429), (-0.202,-0.202), (0.143,0)), per-pixel rotation from interleaved-gradient noise
`frac(52.982918 * frac(dot(pix + 5.588238*frame, (0.067111, 0.005837))))`; result cubed (`s^3`). Omni = cube array, same 8 taps.
Receiver offset along the normal: `P + N * (0.4 - 0.2 |NdotL|)` (sign by side). A light may name a second shadow light (bits 23-26)
whose shadow multiplies in **[B]**.

Cookies: flag bits 7-14 select a slice of a 2D array (the 33 cookies in the gfx world). UV = two projection rows applied to the
direction, scaled by `(1 - dot(axis, Ldir))` (halved for inverted cones), `frac`ed. RGB multiplies the colour **[B]**.

### type 2 (rectangle area light; 137 in zm_escape)

- Influence: three slab terms, each `sat(pd) * sat(pd * s + o)` with pd = plane distance, times the cone term. **No inverse square.**
- Diffuse: polygon form-factor vector F summed over the 4 edges (acos fit `1.5708 + x(-0.879406 + 0.308609 x)`), F *= -1/(2 pi),
  `E = max(0, (|F|^2 + dot(F, N)) / (|F| + 1))`.
- Specular: linearly transformed cosines; two 64x64 LUTs (t49 matrix terms, t50 magnitude) indexed (alpha, acos-like NdotV fit
  `1.570729 + x(-0.212114 + x(0.074261 - 0.018729 x))`), edge integral fit `5.42031 + (3.12829 + 0.090233|x|)|x|`.
- Cookie sampled at a fixed high mip as an average colour.

## 4. Sun / moon **[B]**

    sunColour = cb3[56].rgb * T_atm(viewHeight, sunZenith) * cloudCookie * cascadeShadow^3 * extraLightShadow

- Direction cb3[17].xyz. T_atm is a 2D transmittance LUT (t51) of a precomputed atmosphere (planet radius 6,360,000 m,
  0.0254 m per unit), u = 0.5 * (atan(max(mu, -0.1975) * 5.349624) / 1.1 + 0.74), v = sqrt((r - 6360000) * 1.2e-5).
- Cloud cookie: 2D array slice, `1 + strength * (tex - 1)`, world XY projected by cb3[32..33].
- Shadow: 3 cascades (cb3[28..30] centre + inverse half size, array t13), 8-tap disc when the quality flag cb3[120].z is set;
  beyond the cascades a compressed static shadow tree (uint buffer t23, 128-cell top level, 10-bit child links). A screen-space
  cloud/contact mask (t31) is subtracted, the result is cubed.
- Sun specular: the reflection vector is pulled to within the sun's angular radius (cos 0.999989, sin 0.004756) before the BRDF.
- zm_escape values **[I]**: sun colour (0.451, 0.540, 0.973) * 0.4204 (states 1, 3) or * 3.3636 (lightning), pitch 59, yaw 338, in
  the lighting state records already found (README round 4).

## 5. Indirect light **[B]**

Probe record 224 bytes + 1..n blend volumes of 96 bytes (6 planes each; weight = product of `sat(dot(n, P - c) + d)`;
extra volumes combine by max, or subtract when flagged). Two passes: priority probes first, the rest only while the summed
weight is < 1. Sums are divided by max(weight, 1).

Per probe:

    irradiance = ambientCube(N_local) * probeScale * cube(N_local, mip 6)
    ambientCube = X^2 * A_x(+/-) + Y^2 * A_y(+/-) + Z^2 * A_z(+/-)     three 3D atlases (t17, t18, t19); the +/- half is picked
                                                                      by a 0.5 offset on one atlas axis; uvw = sat(local * scale + 0.5) * size + offset
    reflection = cube(parallax-corrected R, mip)                       ray / 6-plane box intersection, cube array slice = bits 16-24
    mip        = sqrt(2 * hitDist / |hit - cubeCentre|) + 5 (1 - g) - 0.8448
    specular  += reflection * w * K*Ld / (K*Ld + Ls)                   Ld = luma(irradiance), Ls = luma(reflection)
    K          = max(NdotV * 2^max(10.049101 - 10 q, 10.364187 - 5 q - 2.015905 * 5 q^2), 1.26816),  q = 1 - g

So the reflection is **normalised by the local irradiance**: a bright cube map in a dark spot is pulled down to about K times
the diffuse level. This is the main guard against glowing reflections indoors.

Outside every probe (weight < 0.99) the global probe (slice 0) fills the rest, scaled by cb3[19].x, in one of two modes (cb3[27].x):
- **sky visibility**: a world-XY sun volume: height map (t47) + 3D/2D textures holding 4 SH-L1 coefficients (t63, t29, t48), blended to
  open sky (3.544908, 0, 0, 0) above the stored height. `vis = max(0, dot(sh * (1, 2/3, 2/3, 2/3), (0.282095, -0.488603 Ny, 0.488603 Nz, -0.488603 Nx)))`
  times cb3[23].z; diffuse = cube(N, mip 6) * vis. Specular uses the same SH along R (no 2/3) with the same normalisation.
- **global ambient cube volume**: the same three atlases over one box (cb3[96..98]).

Environment BRDF: 2D LUT (t5) indexed (NdotV, g) gives (A, B); ambient specular = reflection * (F0 * A + B-term), times the
material cavity value. AO: `ao = screenSpaceAO(t27) * gbufferAO`, applied to indirect **[B, exact use per term not traced]**.

The baked data behind these textures is the other worker's job (`t8light\gi\`).

## 6. Fog **[B formula, I field mapping]**

Applied in this order at the end of every lit shader.

### 6a. Froxel volume

    uv = project(P) by cb3[46..49];   w = log2(viewZ * cb3[50].x) * cb3[50].y          (logarithmic slices)
    T    = tex3D(t56).rgb                 transmittance
    Sa   = tex3D(t54).rgb                 in-scatter, ambient + local lights
    Ss   = tex3D(t55).rgb                 in-scatter, sun only (unphased)
    c    = dot(viewDir, sunDir)
    phaseSun = cb3[42].x * (1 + c^2) / |cb3[42].y * c + cb3[42].z|^1.5      (Cornette-Shanks; y = -2g, z = 1 + g^2, x = normalisation)
    colour = colour * T + (Sa * 0.8 (1.4 + 0.5 c) + Ss * phaseSun) * cb3[56].rgb

Building the volume (boot 0xf49310): 128 slices on a quadratic depth scale `depth = 1400 * (slice/128)^2` units for the global
term; density per fog volume = `min(base * 2^(-k * height), cap)`; three fog-volume types (1 global/height, 4, 5 local shapes,
204-byte records, ray/slab clipped). Sun in-scatter uses the cascade shadow map and the Schlick phase
`(1 - g^2) / (4 pi (1 + g c)^2)`. Punctual lights come from the same cluster lists with the same attenuation; spot shadows are
sampled (1-4 taps), ambient comes from a 3D ambient texture * 1/(4 pi). The result is blended with the reprojected previous
frame (history textures, previous view-projection in cb8[16..19]) **[B, per-light phase not traced]**.

### 6b. World height fog (cb3[60..62])

    b  = k * dz + b0            dz = P.z - camera.z;  k = cb3[60].x, b0 = cb3[60].y
    f(b) = b < 0 ? 2^b : b + 1
    H  = (f(b) - cb3[60].z) / (k * dz)                  mean density along the ray (cb3[60].z = f(b0))
    T  = clamp( 2^(H * cb3[60].w * dist + cb3[61].w), cb3[62].w, 1 )
    colour = lerp(cb3[61].rgb, colour, T)

Half-life form: density halves per "half height" above the base and is constant below it; transmittance halves per "half
distance". This is exactly the shape of **fog block B** **[I]**: start 100, base height -450, half distance 3500, half height 1050,
max opacity 0.75, colour (0.0191, 0.0247, 0.0388): k = -1/1050, b0 = -(camZ + 450)/1050, cb3[60].w = -1/3500,
cb3[61].w = +100/3500 (so nothing fogs inside the start distance), cb3[62].w = 1 - 0.75 = 0.25, cb3[61].rgb = the colour.
The fifth and sixth values of block B (0, 800) and the base/patched -0.5 / 0 at +0x36c are **[?]**.

### 6c. Atmospheric extinction (cb3[82..84])

    d  = min(dist, cb3[82].w)
    H  = same f() form with k = cb3[83].x, b0 = cb3[83].y, f(b0) = cb3[83].z, along viewDir.z * d
    colour *= 2^( d * H * (cb3[83].w, cb3[84].x, cb3[84].y) )         per-channel, no added colour

**Fog block A** fits this plus the froxel volume **[I]**: -300 = base height, 1/1300 = height falloff, 3937 (100 m) = max distance,
rgb 2.8e-5 = per-unit extinction, rgb (0.143, 0.170, 0.241) with 0.3 = fog albedo/ambient colour and anisotropy g or density scale;
7, 0.75 and rgb 0.0014 are **[?]**. Which of A's fields feed cb3[42] (g) and the volume density could not be read: those are CPU side.

### 6d. Box fog / water volume (cb3[88..91])

Ray vs an AABB; inside length l (+ depth below the surface): `colour = colour * 2^(-l * ext.rgb) + lut(log2(l + 1)/15) * ...`, then a
second `2^(l * k)` lerp to cb3[91].rgb. Only active when cb3[89].y marks a volume. Not needed for zm_escape's look **[B]**.

## 7. Exposure **[B]**

Auto exposure (boot 0x270924), 8x8 tiles of a luminance buffer:

    Lavg   = exp( mean( ln( max(lum, 0.001) ) ) )                      geometric mean
    ev     = log2( Lavg * k / 0.18 ) + bias + 3                        k = cb8[1].y, bias = cb8[0].z
    ev     = centre + strength * (ev - centre)                         centre = cb8[1].x, strength = cb8[0].w
    ev     = clamp(ev, minEV, maxEV)                                   cb8[0].x, cb8[0].y
    ev     = clamp(ev, centre - 1, centre + 1)                         **never more than 1 stop from the authored centre**
    target = 2^(ev - 3)
    rate   = lerp(0.1, 0.4, 0.04 / (target + 0.04)) seconds            darker targets adapt slower
    cur   += (target - cur) * (1 - e^(-1 / (60 rate)))                 per frame, 60 fps assumed
    smooth = mean(cur, previous 8 frames)
    exposure = k / smooth                                              -> cb2[110].y

With strength 1, bias 0 this puts the scene's geometric-mean luminance at 0.18 (18 nits). The authored centre, bias, min/max are
per-map values **[?]**: likely the candidates already found in the lighting state record (+0x1c = 2.5, +0x6c = -0.5); the
vbloom / fxgrade assets named by worldspawn are not in any zone read.

## 8. Tone map, grade LUT, output

There are two complete paths in the bytecode. Which one a given PC setting runs is chosen on the CPU **[?]**.

### 8a. Film-curve path (SDR) **[B]** (boot 0x11f43f0 / 0x130d950 / 0x141a41c)

    x  = hdr.rgb * exposure + 0.00873
    t  = sat( 0.598206 + 0.072703 * log2(x) )                           13.75 stops: 0.0033 .. 46
    y  = sat( ((((7.712947 t - 19.311527) t + 14.275167) t - 2.490045) t + 0.878083) t - 0.06691 )
    lin = BT709_EOTF_inverse(y)            (y <= 0.081 ? y/4.5 : ((y + 0.099)/1.099)^(1/0.45))
    lin = sat( M_2020->709 * lin )         (1.660491 -0.587641 -0.072850 / -0.124550 1.132900 -0.008349 / -0.018151 -0.100579 1.118730)
    e  = BT709_OETF(lin)                   (lin <= 0.018 ? 4.5 lin : 1.099 lin^0.45 - 0.099)
    e  = e + b - e * b,  b = sat(bloomTex / 256)                        bloom is a **screen blend** in display space
    e  = sat(e + overlayTex)
    out = LUT32( e * 31/32 + 1/64 )                                     the 32^3 grade LUT, sampled last

Curve values (x -> linear display): 0.01 -> 0.017, 0.05 -> 0.065, 0.18 -> 0.194, 0.5 -> 0.387, 1 -> 0.553, 2 -> 0.720, 4 -> 0.860,
8 -> 0.953, 16 -> 0.992. A custom filmic polynomial, not ACES. The vignette variant scales the two top polynomial coefficients
by `v = c0 + r^2 c1 + r^3 c2 + r^4 c3` (r = elliptical distance from centre, cb8[0..1]).

So the earlier guess is nearly right: the grade LUT is applied **after** the tone curve on the display-encoded signal, but the
encoding is the **BT.709 OETF (1.099 x^0.45 - 0.099), not sRGB**, and the LUT input is 709-primaries.

### 8b. HDR-master path **[B]**

    p   = PQ( sat(hdr.rgb * 0.01) )                                     ST 2084, scene 1.0 = 100 nits, Rec.2020
    out = LUT32( p * 31/32 + 1/64 )                                     a float 32^3 display LUT rebuilt by compute when settings change
    out = floor(out * 877 + noise) / 876                                128x128 noise tile, 10-bit video-range dither

The display LUT for SDR is built per texel as (boot 0x3d39c):

    nits = 10000 * PQ^-1(coord)
    nits = 18 * (nits / 18)^gamma * ...                                 system gamma about 18 nits (cb8[2].x; written as (n/18)^g * 18)
    ICtCp;  I' = BT.2390 EETF(I): knee start ks = 1.5 * PQ(maxNits) - 0.5, Hermite roll-off to PQ(maxNits),
            then I' += PQ(minNits) * (1 - I')^4;  Ct, Cp scaled by min(I'/I, I/I')
    rgb  = (nits_rgb - minNits) / (maxNits - minNits)                   cb8[0].z, cb8[0].w
    e    = BT709_OETF(rgb)
    out  = trimLUT( e * 32/33 + 0.5/33 )                                **the SDR trim-pass LUT, on the 709-encoded signal**

The grade LUT (mtl_lut_*, 1024x32 strip) is turned into a 3D texture by 0x6b4f8c (up to 4 strips blended by weight), optionally
run through the composer 0xe059c (strip values are BT.709-OETF encoded; three tonal-range colour matrices + gammas, an sRGB-indexed
inner LUT, luma curves), and in this path is sampled with a PQ coordinate and blended in PQ space (0x6d3bdc) **[B]**; the exact
order of grade vs display mapping in the final float LUT is assembled on the CPU **[?]**.

Reading of the decoded LUTs in `t8light\grade\` **[I]**: lut0/lut1 are near identity with a slight blue lift, consistent with
either path; the trim LUT's gentle contrast reduction (0.097 -> 0.122, 0.5 -> 0.5, 0.871 -> 0.857) is what an SDR trim on a
709-encoded signal looks like. For the port: tone curve 8a, then lut0 on the 709-OETF-encoded result, then the trim LUT on the
same encoding is the closest offline match; treating either LUT as sRGB-encoded is a small error (709 OETF vs sRGB differ
mostly in the darks).

### 8c. Bloom, emissive

- Bloom enters as a screen blend of `bloom/256` in display space in path 8a **[B]**. Threshold / strength are in the bloom
  down-sample passes and their constants, not traced **[?]**.
- Unlit / FX colour: `tex * vertexColour` -> 709->2020 -> `* cb2[110].y` (exposure), no fog on that variant **[B]** (esc 0xcf994e5).
- The emissive material shader (cb slot 6 float 8 scale, floats 12-14 tint) was **not located** by a cbuffer-pattern search **[?]**.
  By the unlit path, an emissive scale is a scene-linear multiplier in 100-nit units before exposure, so scale 32-64 bulbs are
  3,200-6,400 nits before exposure and are meant to clip through the shoulder and feed bloom **[I]**.

## 9. Other look-shaping passes

| item | status |
|---|---|
| screen-space AO texture multiplied with g-buffer AO in the deferred shader | **[B]** exists (t27); its generator not read |
| screen-space shadow / contact mask subtracted from sun shadow | **[B]** (t31) |
| vignette | **[B]** in the film-curve variant (section 8a) |
| output dither (128x128 noise, 10-bit) | **[B]** |
| film grain, sharpening, SSR, light shafts, depth of field, motion blur | **[?]** not looked for; `boot_list.txt` lists all 719 engine shaders with their constants for a later pass |
| temporal AA | **[I]** motion vectors in the g-buffer and interleaved-gradient noise keyed on the frame index |

## 10. What an engine needs to match this

General capabilities, none map-specific:

1. **Rec.2020 linear lighting** with 709->2020 on colour inputs, HDR target, scene unit 1.0 = 100 nits, exposure applied before the tone curve.
2. **Gloss model**: gloss -> `alpha^2 = 2/(2^(17 g) + 2)`, GGX D, Schlick-GGX visibility with k = (r+1)^2/8, Schlick Fresnel, pi-less
   light units, multi-scatter gain from a directional-albedo LUT, normal-variance gloss reduction.
3. **Roughness-aware diffuse** (`lerp(NdotL, 0.62(1 - t^2), alpha)`).
4. **Punctual lights in inches** with the windowed inverse square `sat((1/(d^2+1) - c)/(1 - c))`, c = 1/(radius^2+1); cone =
   linear-then-squared ramp from the outer angle over a feather fraction, measured from an apex pulled back by
   bulbRadius/tan(halfFov); optional d^2 and axial fades.
5. **Sphere lights** (bulb radius): representative-point specular with the energy normalisation above.
6. **Rectangle area lights**: slab-bounded influence without distance falloff, form-factor diffuse, LTC specular.
7. **Light cookies** (2D array) on spots and a scrolling cloud cookie on the sun.
8. **Shadows**: per-light spot (2D) and omni (cube) maps, 8-tap rotated disc with per-pixel noise rotation, cubed result,
   normal-offset receiver; 3 sun cascades plus a far static shadow structure.
9. **Clustered culling** (64 px tiles x 16 depth slices, bit masks) for lights and for probes.
10. **Box-blended local probes**: ambient cube (6 directional colours in 3D textures) for diffuse, parallax-corrected cube map for
    specular, **reflection normalised by local irradiance** (`K*Ld/(K*Ld + Ls)`), roughness + distance driven mip.
11. **Global fallback**: SH-L1 sky visibility volume times a sky cube, or one large ambient-cube volume.
12. **Environment BRDF LUT** and AO (screen-space x material) on indirect.
13. **Froxel volumetric fog**: log-depth 3D textures (transmittance, ambient+local in-scatter, sun in-scatter), fog volumes with
    exponential height density, shadowed sun and shadowed spot lights injected, Cornette-Shanks/HG phase for the sun,
    temporal reprojection; applied inside the lighting shader for opaque and translucent alike.
14. **Analytic height fog** in half-distance / half-height form with start distance and max opacity, plus per-channel
    atmospheric extinction with a max distance.
15. **Auto exposure**: log-average metering to 0.18, authored centre with a hard +/-1 stop window, min/max EV, asymmetric
    adaptation (0.1 s bright, 0.4 s dark), 9-frame smoothing.
16. **Display pipeline**: 5th-order log-domain film curve -> BT.709 OETF -> screen-blend bloom -> 32^3 grade LUT on the encoded
    signal -> optional SDR trim LUT -> dither. Optional HDR path: PQ-indexed 32^3 LUT with BT.2390 mapping in ICtCp.
17. **Vignette** as a radial polynomial on the tone curve.

## 11. Not found / open

- Zone-field -> GPU-constant mapping for light fields c8, d0, b4 (which fade or scale each feeds).
- The per-map exposure centre / bias / min / max and bloom threshold / strength values.
- Emissive material shader; film grain, sharpening, SSR, god rays, SSAO generator, bloom chain.
- Which output path (8a or 8b) and which LUT order the PC SDR setting uses: decided on the CPU.
- Fog block A field order beyond the fits marked [I]; block B's two trailing values.
- All shaders were read from the base core_bootstrap zone and the patched material zones; a patched core_bootstrap was not dumped.
