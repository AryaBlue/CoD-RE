# T6 reflex/holo reticle lens (`mc_sw4_3d_reticle_dynamic`)

Why the HK416 reflex lens on MP raid draws solid green, and what the real draw is. Researched 2026-10-27.

**This is T6 (BO2), not T5.** The material and techset live in `mp_raid.ff` / `patch_mp.ff` / `common_mp.ff`.

## Conventions

- **Tags:**
  - **[V]** read in data or shader bytecode.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - OAT Unlinker dumps of `common_mp.ff` and the raid/patch zones: materials, techsets, techniques and shader_bin.
  - The shaders, read through D3DDisassemble.
  - Only names, registers, values and maths are given here, no shader text.

## Why it's green

The techset `mc_sw4_3d_reticle_dynamic_9820jqfj` has only four techniques [V]:

| technique slot | technique |
|---|---|
| unlit | `pimp_technique_radiant_cbdb0b44`, an editor stand-in (`radiantDiffuseMap` = `sw_radiant_default`) |
| emissive | `pimp_technique_sw4_3d_reticle_dynamic_71f28a27`, **the real draw** |
| solid wireframe | radiant |
| debug performance | debugperformance |

- There is no lit technique, so our fallback picks unlit, which is the radiant stand-in and draws the flat green [I: matches STATUS.md:278].
- **Fix:** draw this techset through its **emissive** technique, as a transparent emissive pass.

**Who uses which techset** (`common_mp`) [V]:
- `reticle_dynamic_9820jqfj`: reflex (the HK416's), holo, acog, combo up/down, m32.
- `reticle_dynamic_2colors_5f888f0w`: **only** `rangefinder_reticle2`. So the export's skip of 2colors doesn't affect the reflex.
- `reticle_static_*`: mms, fhj18.
- `reticle_ui3d_*`: rangefinder.

## Material

`mc/mtl_t6_attach_optic_reflex_reticle` (common_mp) [V]:
- **Sort** 62, camera region emissiveTrans.
- **Emissive state** (stateBits 0):
  - colour: src One, dst InvSrcAlpha, i.e. premultiplied;
  - alpha: src InvDestAlpha, dst One;
  - depth test ≤, no depth write, cull back.

| texture slot | image | sampler |
|---|---|---|
| `Color_Map` | `mtl_t6_attach_optic_reflex_reticle` (the reticle) | **clamped** |
| `Detail_Map` | `mtl_t6_attach_optic_reticle_noise` | wrap |
| `radiantDiffuseMap` | `sw_radiant_default` | stand-in only |

| constant | common_mp reflex | raid `_reticle_12` |
|---|---|---|
| `Reticle_Color` | (1, 0.737, 0.737) | (1, 0.767, 0.321) |
| `Glow_Color` | (1, 0, 0) | (1, 0, 0) |
| `Glow_Falloff` | 2.7 | 1.5 |
| `Noise_Scale` | 4.75 | 4.75 |
| `Emissive_Amount` | 9.03 | 12 |
| `Background` | 0 | 0 |
| `Color_Map_Noise` | 0.1 | 0.1 |
| `Color_Map_Scale` | 30 | 13.61 |

All constants use `.x` only, except the colours, which use `.rgb`.

## Vertex shader: the projection (vs `9b0c84e4`) [V]

**It is a collimated (infinity-focus) projection: there is no parallax and no depth term.**

1. `e` = the view-space position, normalised (the view direction to the vertex).
2. The normal and tangent are decoded from their packed form (component ≥ 0.5 → `2x − 2`, else `2x`). They are transformed by `inverseTransposeWorldView`.
3. `B = cross(N, T) × sign(position.w)`.
4. The reticle UV:
   - `u = dot(T, e) × Color_Map_Scale + 0.5`
   - `v = −dot(B, e) × Color_Map_Scale + 0.5`
5. The plain lens UV passes through for the noise.

- So the reticle depends only on the **view direction relative to the lens frame**. Looking straight down the lens normal puts the reticle centre at (0.5, 0.5), and moving the eye off-axis slides it across the glass, like a real red dot.
- `Color_Map_Scale` is the angular size: a larger value gives a smaller dot.

## Pixel shader (ps `1f5ed1d`) [V]

1. **Depth reject:** discard if the pixel's depth is behind the floatZ buffer at this pixel (the screen uv comes from `SV_Position × inverse screen size`, cb0[95].zw).
2. **Outside the reticle:** a reticle UV outside [0, 1] samples as 0 (on top of the clamped sampler).
3. `C = Color_Map(reticleUV)`:
   - `C.r` is the reticle mask, `C.g` the glow, `C.b` the background mask.
4. `noise = Detail_Map(lensUV × Noise_Scale).r`.
5. `reticle = C.r × Reticle_Color × (1 − Color_Map_Noise × noise)`.
6. `glow = C.g ^ Glow_Falloff × Glow_Color × noise`.
7. `rgb = ((reticle + glow) × Emissive_Amount)²`.
8. `alpha = C.b × Background`, which is 0 on both materials. So the blend is purely additive (One / InvSrcAlpha with alpha 0).
9. **Fade:** everything is multiplied by `(1 − weaponParam0.y) × saturate(2 × weaponParam0.w)`. weaponParam0 is cb1[31] [I: an ADS / visibility fade; with no weapon state, use 1].
10. Then × `hdrControl0.x`, and the output is the **square root** (linear → gamma, like the other T6 emissives).

## For the RTX worker

1. Route `mc_sw4_3d_reticle_dynamic_*` (not 2colors) to the emissive transparent pass.
   - Blend One / InvSrcAlpha, with no depth write.
   - The export already reads every constant above (ExportModel.cpp ~159-185).
2. Per vertex, compute the reticle UV from the view direction in the tangent frame, as in the VS section. A plain mesh UV gives a stuck-on decal instead of a red dot.
3. In the PS, apply the maths above.
   - The floatZ reject can be an ordinary depth test, since the lens is drawn after the opaques.
   - Treat the weaponParam0 fade as 1 [I].
4. Keep it out of RT shadow and GI casting (emissive, transparent) [I].

## Open

1. The 2colors technique (rangefinder_reticle2 only) wasn't read [U].
2. What drives weaponParam0.y/.w [U].
