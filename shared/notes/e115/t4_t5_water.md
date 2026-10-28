# T4 / T5 water (`wc_water`): what the lit water shader does

All 23 T4 maps and T5 `mp_radiation` (`wc/water_default`, `wc/water_mp_rad`) draw their water with the `wc_water`
techset. E115 draws it as a flat lit stand-in. This note covers what the real shader computes: inputs, Fresnel,
reflection, refraction, constants, and where each value lives. Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in shader bytecode, material data or the mod-tools material template.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - The `wc_water` techset, dumped from `mp_kneedeep.ff` (T4, Plutonium) and `mp_radiation.ff` (T5) with a scratch OAT-based dumper: techniques, pass args and shader bytecode.
  - The shaders, read through D3DDisassemble. They are D3D9 SM3 with constant tables, so register names are known.
  - The materials, from OAT Unlinker.
  - The BO1 mod tools' `mtl_water.template`, which maps artist parameters to constants.
- Only names, registers, values and the maths in words are given here, no shader text.
- `exp` below means the shader's `exp`, which is **2^x**.

## Techniques [V]

- **T4:** every lit technique slot (8–21, 36–42) uses one VS/PS pair, `water_l_sun`.
  - Technique flags 0xc1, which include NEEDS_RESOLVED_POST_SUN: it reads the resolved scene.
  - Other slots: `build_floatz`, `vertcol_shaded`, wireframe, `debug_bumpmap`.
- **T5:** `pimp_technique_waterlsun`, in two variants:
  - `..._53bd42e` (slots 10–16, 52–58, 73–79) reads linear float-Z.
  - `..._78f69911` (slots 80–86, 108–114) reads a hardware depth buffer, decoded as `zNear·0.99951 / max(0.99951 − d, 1e-8)`.
  - Both use the same VS; apart from the depth decode the maths is identical.
- **No cubemap and no reflection probe is sampled.** The "env" term is a screen-space lookup into the resolved scene, plus a sky/ground colour.

## Inputs [V]

| input | T4 PS reg | T5 PS reg | source |
|---|---|---|---|
| `normalMapSampler` | s4 | s1 | material `normalMap` (all three maps found use `test_mitton_water`) |
| `floatZSampler` | s5 | s2 | code: scene depth |
| `refractSampler` | s6 | s3 | code: the resolved scene colour |
| `gameTime` (.w) | c5 | c5 | code |
| `fogColor` | c0 | c0 | code |
| `sunPosition`, `sunDiffuse` | c17, c18 | c17, c18 | code |
| `hdrControl0` (.x) | — | c7 | code (T5 only) |
| `envMapParms` | c6 | c6 | material |
| `waterColor` | c7 | c8 | material |
| `waterParams` | c8 | c9 | material |
| `waterScroll0/1/2` | c9, c10, c11 | c10, c11, c20 | material |
| `waterSkyColor`, `waterGroundColor` | c20, c21 | c21, c22 | material |
| `waterSunValues` | c22 | c23 | material |

- The material's `colorMap` (`case64blue`) is not sampled by the lit shader.
- VS-side code constants: `worldMatrix`, `viewProjectionMatrix`, `clipSpaceLookupScale` / `clipSpaceLookupOffset`, `fogConsts`. T5 adds `fogConsts2` and the sun-fog constants.

**Material constants** come from the template [V]:

| constant | components |
|---|---|
| `waterParams` | (roughness, refract, feather, opacity) |
| `waterScrollN` | (scrollX / 64, scrollY / 64, 0, 0) |
| `waterSunValues` | (sunBrightness, sunSize, 0, 0) |
| `envMapParms` | (min, max − min, −1.7 × exponent, 2.5) |

`envMapParms.w` (2.5, "sun intensity") isn't read by the lit PS [V].

## The maths, per pixel [V unless tagged]

**Vertex outputs** [V]:
- `uv` = the surface texcoord.
- `viewDepth` = clip w.
- `P` = `worldMatrix × pos`. The PS normalises it as the view vector, so world surfaces are camera-relative here [I].
- `fogVis` = 2^(fog): clamped ≤ 1 in T4; T5 uses its fog constants.
- `screen` = the clip position mapped by `clipSpaceLookupScale/Offset` (projective screen UV).
- `refrDir` = the screen image of the surface's world X axis × `waterParams.y` × vertex alpha.
  - The matching Y-axis vector is **written as 0** in both games, so only the normal's x bends the refraction.
- The projection rows for the reflection lookup.
- `topV` = the screen v of the top edge of the view [I: what the formula gives].
- Vertex alpha.

1. **Normal:**
   - `n.xy = waterParams.x × Σᵢ (N(uv + waterScrollᵢ.xy × gameTime.w).ag − 0.5)`, over three samples of the **same** map at the **same** UV scale. Only the scroll differs.
   - Then `n = normalize(n.x, n.y, 1)`.
   - It is used directly as world space with z up; there is no tangent frame.
   - Channels: x from alpha, y from green (DXT5 normal maps).
   - `gameTime.w` is seconds [I].
2. **View and reflection:**
   - `V = normalize(P)`.
   - `R = V − 2(V·n)n`.
   - `R' = (R.x, R.y, |R.z|)`.
3. **Sun:** `spec = 2^((R'·sunPosition − 1) / waterSunValues.y)`, added as `spec × sunDiffuse × waterSunValues.x`.
4. **Refraction:**
   - `uvR = screen + n.x × refrDir`.
   - Read depth at `uvR`. If the scene there is nearer than the water, fall back to the unoffset `screen`.
   - `refr = scene(uvR)`.
   - `thick = sceneDepth − viewDepth`.
5. **Reflection ("env"):**
   - March nothing. Project the point `P + R' × 200000 / viewDepth` to the screen and sample the resolved scene there: `ssr`.
   - Weight `w = saturate(v_refl − topV)^0.25`, which fades to 0 as the reflected point leaves the top of the screen [I: the meaning of v].
   - **Sky/ground:** `bg = |R.z| ≥ 0.2 ? waterSkyColor : waterGroundColor`. It is a hard step, not a blend.
   - `refl = lerp(bg, ssr, w) + sun`.
   - T5 divides `ssr` by `hdrControl0.x` and raises `bg` to the **4th power** (squared twice). T4 uses the colours as stored.
6. **Fresnel:** `F = saturate(envMapParms.x + envMapParms.y × 2^(envMapParms.z × |V·n|))`, i.e. min + (max − min) × 2^(−1.7 · exponent · |V·n|).
7. **Tint:** `tint = waterColor × (refr + waterParams.w × (1 − refr))`. The refracted scene is multiplied by waterColor and lifted toward waterColor by the opacity.
8. **Shade:** `shade = lerp(fogColor, lerp(tint, refl, F), fogVis)`.
9. **Depth feather:** `a = 1 − 2^(−max(thick, k) × waterParams.z)`, with k = 0.1 in T4 and 0 in T5.
10. **Output:** `colour = lerp(refr, shade, a × vertexAlpha)`, alpha 1.
    - The material blend is opaque (One/Zero), with no cull on the depth-writing state.
    - So shallow edges show the raw scene, and deep water shows the full shade.

## Values seen [V]

| material | envMapParms | waterParams | waterColor | sky | ground | sunValues |
|---|---|---|---|---|---|---|
| T4 `wc/water_pel2_mangrove` (kneedeep) | 0.1, 0.9, −10.2 | 0.15, 30, 0.5, 0.5 | 0.306, 0.271, 0.220 | 0.510, 0.514, 0.420 | 0.239, 0.200, 0.129 | 1, 0.035 |
| T5 `wc/water_default` (radiation) | 0.1, 0.1, −1.7 | 0.15, 30, 0.5, 0.5 | 0.267, 0.286, 0.204 | 0.737, 0.729, 0.682 | 0.259, 0.267, 0.110 | 4, 0.01 |
| T5 `wc/water_mp_rad` | 0.1, 0.1, −1.7 | 0.1, 60, 1.0, 0.5 | 0.141, 0.208, 0.153 | 0.177, 0.224, 0.200 | 0.188, 0.239, 0.145 | 0, 0.01 |

- **Scrolls** are the same in all three: (−0.0309, 0.0206), (0.0694, −0.0809), (0.0538, 0.0497), i.e. the template's /64 values.
- `water_default` has max = min (F is a constant 0.1) and no sun on `water_mp_rad`. So at radiation the look is mostly the tinted, depth-feathered refraction.

## For the RTX worker

- **Constants:** read the material constants by name (OAT dumps some names truncated, e.g. `waterGroundC`, `waterSkyColo`). Feed `gameTime` seconds.
- **Needed inputs:** the shader needs the resolved scene colour and scene depth behind the water. Without them, use `refr` = the colour behind (or waterColor) and `thick` from a depth estimate.
- **Reflection:** a ray-traced reflection can stand in for the screen-space `ssr`. For parity, fall back to the sky/ground step at |R.z| = 0.2, and add the sun lobe.
- **Keep the quirks:** single-axis refraction offset, three same-scale normal layers, `exp` = 2^x, T5's colour^4 and /hdrControl0.

## T4 `wc_water_dynamic`: the docks / makin ocean

`wc/water_dynamic` (docks) and `wc/water_dynamic_makin` use `wc_water_dynamic`, dumped from `mp_docks.ff`.

**Two techsets split near from far** [V]:
- **`wc_water_dynamic`** is the map surface material (lit slots 8–21, 36–42). It uses `water_dynamic_far`.
- **`water_dynamic`** is a separate techset that the non-`wc` material `water_dynamic` uses, with the same constants and textures. Its lit slots use `water_dynamic_near`; technique flags 0xc9 add DECL_HAS_OPTIONAL_SOURCE.
  - Its VS reads packed vertices: a position, plus a second position and normal that it morphs towards by `waterParms.y`.
  - So it's a code-generated, geomorphing grid, not BSP geometry [I: the mesh source wasn't traced].
- **The split:** both PS compute `k = 1 − dist × waterParms.w`, where dist is from the camera.
  - **far kills pixels with k > 0** (inside the near range);
  - **near kills pixels with k < 0**.
  - So the BSP ocean surface only draws beyond `1 / waterParms.w`, and the code grid fills the near field.
- `waterParms` (VS) and `waterScroll` (PS) are **code** constants: their values come from the engine [U].
- The far VS also nudges the plane's world z when `|waterParms.z| < 5`, by `sign(z) × (5 − |z|)`. It looks like it keeps the plane off the eye when the camera is near the surface [I].

**Inputs** (far PS) [V]:

| input | reg | source |
|---|---|---|
| `colorMapSampler` (foam, `test_quinn_foam05`) | s0 | material |
| `normalMapSampler` (`test_quinn_ocean02_n`) | s4 | material |
| `floatZSampler` | s5 | code (raw float-Z) |
| `lightsSampler` | s6 | code sampler 12, post-effect 0 [U: what it holds] |
| `refractSampler` | s7 | code (resolved post-sun scene) |
| `fogColor` / `fogConsts` | c0 / c5 | code |
| `gameTime` | c6 | code |
| `waterScroll` | c8 | code |
| `sunPosition` / `sunDiffuse` | c17 / c18 | code |
| `envMapParms` | c7 | material |
| `oceanFoamValues` | c9 | material |
| `oceanShoreValues` | c10 | material |
| `oceanBumpValues` | c11 | material |
| `waterParams` | c20 | material |
| `waterScroll0..2` | c21..c23 | material |
| `waterSkyColor` | c24 | material |
| `waterSunValues` | c25 | material |

**Unused** [V]:
- `waterColor` and `waterGroundColor` aren't read. The **vertex colour** is the water colour (rgb) and opacity (a).
- Only `waterParams.x` and `oceanBumpValues.x` are read.
- `oceanFoamValues.y` is unused.

**Docks values** [V]:

| constant | value |
|---|---|
| `oceanBumpValues` | (16, 5) |
| `oceanFoamValues` | (1, 2, 8) |
| `oceanShoreValues` | (100, 0.95, 0.85) |
| `waterParams` | (6, 10, 0.05) |
| `envMapParms` | (0.2, 0.8, −17) |
| `waterSunValues` | (2, 0.07) |
| `waterSkyColor` | (0.302, 0.384, 0.376) |

The scrolls are the same as `wc_water`'s.

**The far maths** [V]:
1. **UV:**
   - The VS gives `uv = 0.04 × object position.xy`.
   - `base = uv / oceanBumpValues.x + gameTime.w × waterScroll.xy`.
2. **Distance-tiled normal:**
   - `lod = max(log2(dist / 1500), 0)`.
   - Three phases `lod + {0, ⅓, ⅔}`, each with fraction f and floor F.
   - Sample i reads the normal map at `(base + waterScrollᵢ × t) × 2^−Fᵢ`, decoded as .ag − 0.5, with weight `f(1 − f)`.
   - Sum the three, × `waterParams.x`.
   - Then `N = normalize(Nvert + n.x × T + n.y × B)`. Unlike `wc_water`, it has a real tangent frame.
   - So the waves get coarser by powers of two with distance, cross-faded so there's no seam.
3. **Grazing flatten:** `N = normalize(N + (|V.z|^0.05 − 1) × V)`.
4. **Foam:**
   - The foam map is sampled twice: at `uv / −foam.z + (t / 16, 0)` and at `uv / foam.z + (0, t / 16)`.
   - `φ = foamA.r × foamB.r`.
5. **Shore** (scene depth below the surface):
   - `s = saturate((sceneZ − waterZ) / oceanShoreValues.x)`, and `e = 1 − s` (with e = 1 when s ≤ 0).
   - `foamAmt = saturate(e × shore.z + 3φ − 1) + saturate(3φ − 1)`.
6. **Reflection:**
   - `refl = waterSkyColor + 4 × lights(screen + N.xy × 0.2) + sun`.
   - `sun = 2^((R'·sun − 1) / waterSunValues.y) × sunDiffuse × waterSunValues.x`, with R' as in `wc_water`.
   - There is no sky/ground step and no screen-space reflection in the far shader.
7. **Fresnel:** `F` uses `envMapParms` exactly as in `wc_water`.
8. **Body:**
   - `tint = vc.rgb × (refr + vc.a × (1 − refr))`, where `refr` is the unoffset scene.
   - `c = lerp(tint, refl, F) × (1 − e²)`.
9. **Foam on top:**
   - `c = c × (1 − foam.x × foamAmt) + foam.x × foamAmt`, applied to rgb and alpha. The alpha starts at `1 − e²`.
   - Then fog, weighted by that alpha.
10. **Shoreline fade and output:**
    - `q = saturate((e − shore.y) / (1 − shore.y))`. That's the last 5 % of depth at docks.
    - `out = c × (1 − q) + refr × (1 − c.a × (1 − q))`: a premultiplied composite over the refracted scene, alpha 1.

**Near differences** (`water_dynamic_near`) [V]:
- It uses the same normal, foam and shore maths.
- **Refraction** is offset by the normal along **both** screen axes (VS-built, each clamped to 0.1). It takes the shallower of the offset and unoffset depth.
- **Reflection** adds a **screen-space scene sample** at the reflected position, faded by `saturate(v)^0.25 × saturate(0.9 − dist × waterParms.w)`, over the sky colour. Then it adds `4 × lights` and the sun.

**For E115:**
- The BSP `wc/water_dynamic` surface is only the far ocean. Drawing it everywhere with the near-shader terms (two-axis refraction, screen-space reflection fade) is the closest single-surface stand-in [I].
- The water colour comes from the vertex colours, so make sure the export keeps them for these surfaces.

## Open

1. Confirm `gameTime.w` is seconds, and the sign and orientation of `clipSpaceLookupScale` (the `topV` reading).
2. The ocean's code values: `waterParms` (near range, morph, eye height?), `waterScroll`, and what post-effect 0 (`lightsSampler`) holds. Also how the near grid is generated.
3. Is T5's colour^4 on sky/ground intended, or is it gamma on top of colours that are already linear?
