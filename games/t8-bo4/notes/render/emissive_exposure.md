# BO4 emissive, part 3: cb2[110].x is 1 / exposure

Offline, maths only. Tags: **[P]** proven from bytecode, **[I]** inferred, **[?]** unknown.
Zones: patched core_bootstrap ("bootp") and core_common ("core"). Listings named below are in `asm\`;
the full per-reader table is `survey110_bootp.json` / `survey110_core.json` (made by `survey110.py`). The bulk
disassembly folder `all\` was deleted afterwards (311 MB); `dumpboot.py` + `dumpall.py` rebuild it.

## Answer

**cb2[110].x = 1 / exposure = 1 / cb2[110].y** (the scene value that lands on exposed 1.0) **[I, strong]**.
The engine's `E *= max(luma(lit), 1e-4, X)`, `X = 1/exposure` matches the bytecode exactly. It is `max`, not lerp / min **[P]**.

Corrected formula, one line:

    out_exposed = fog( lit + M709->2020 * ( E0 * (rel ? max(luma601(lit), 1e-4, X) : 1) * scale ) ) * Y      [P]
    E0 = map.rgb * tint * map.a * F * (1 - decal) [* flicker],  F = (N.V)^p | (1 - N.V)^p | 1                  [P]
    X = cb2[110].x,  Y = cb2[110].y,  X * Y = 1                                                             [I]

so for a relative material

    emission_exposed = E0 * scale * max(1, luma(lit) * exposure)        independent of exposure               [I]

The bytecode does **not** make the globe smaller than that. A relative emitter of scale s is s times exposed white
where map * tint * F = 1, at any exposure.

## Evidence

Readers: bootp 249 shaders, core 1,526. Only .x and .y are read, except one core shader that tests `.w > 0` as a
switch (core 0x131e09e4, a 79-line UI-type shader: saturate the output or not). Nothing reads .z **[P]**.

| use | count (bootp / core) | what it shows |
|---|---|---|
| `mul rgb, rgb, Y` as the last step before the 6.1e-5 cut and the (65024, 65024, 64512) clamp | 347 / 1,544 | Y = exposure, applied once, last **[P]** |
| scene-colour tap (t22 / t25 / t46: last frame or the resolved scene, used for SSR and refraction) `* X`, mixed with unexposed lighting, then `* Y` at the end | 179 / 114 (+6 `mad -rgb, X`) | X undoes Y on an already exposed buffer, so X * Y = 1 **[I, strong]** |
| `max(luma, 1e-4)`, `max(.., X)`, `movc flag`, `mul scale` (the relative emissive) | 130 / 1,081 | max, not lerp / min **[P]** |
| `max(X, 1e-4)` with no luminance at all, then `movc flag`, `mul scale` (unlit, core 0x10144124) | 0 / 18 | "relative" unlit = scale * colour in exposed units **[P]** pattern, **[I]** meaning |
| `scale * X`, colour `* that`, alpha from colour / `max(scale * X, 1)` (core 0xf831588) | 0 / 1 | same idea written as a product **[P]** |
| `max(X, 1)` then `lerp(1, max(X,1) * c, k)` (core 0xd783254, 0xd9ae8e4) | 0 / 2 | "never dimmer than exposed-white-relative"; only makes sense if X is above 1 in bright scenes and below 1 in dark ones **[I]** |
| `min(luma, X)` (vertex and compute lighting, bootp 0x13a1861, core 0x11d932d8) | 11 / 4 | clamps one light's contribution to exposed white: X is "the scene value of exposed 1.0" **[I]** |
| debug border writes (X, 0, X/2, 1) with no `* Y` (bootp 0x2397d, core 0xd05f244) | 2 / 1 | the odd one out; a 2D overlay shader **[?]** |

Order in the standard lit emissive (lamp-post, `asm\lamppost_lit_bootp_13aa2d1.asm`) **[P]**:

    line 3393  luma601(lit)            3394  max 1e-4          3395  max X
    line 3396  movc (cb0[3].w ? that : 1)                      3397  * cb0[2].y (scale)
    ...        add to lit, fog
    line 3515  * Y                     3516-3518  cut < 6.1e-5, clamp

So the final `* Y` does follow the relative term, and X * Y cancels.

No second exposure hides later **[P]**: the SDR tone-map shader multiplies by a per-draw value `v1.x`, and the vertex
shader stored directly in front of it (bootp 0x120e86d before 0x120ec95) writes the literal 1.0. The pairing by
file position is **[I]**. The bloom chain has no constants at all (BLOOM.md).

Auto exposure (spec section 7) gives typical values: exposure = 0.18 / geometric-mean scene luminance, so X is about
5.6 x the scene's log-average luminance; dark Alcatraz interiors X << 1, daylight X >> 1 **[I]**.

## What a globe should look like

Display-referred = film curve 8a of the spec, then BT.709 OETF, 8-bit, before the grade LUT and bloom.
Tint t = (1, 0.775, 0.617), map = 1, power 6, relative. **Identical at exposure x1 and x2** (only the surroundings move).

| r / R on the sphere | N.V | (N.V)^6 | scale 8: exposed, 8-bit | scale 64: exposed, 8-bit |
|---|---|---|---|---|
| 0 | 1.0 | 1.000 | (8.0, 6.2, 4.9) -> 249 245 241 | (64, 50, 39) -> 254 254 254 |
| 0.44 | 0.9 | 0.531 | (4.3, 3.3, 2.6) -> 239 232 225 | (34, 26, 21) -> 254 255 255 |
| 0.60 | 0.8 | 0.262 | (2.1, 1.6, 1.3) -> 219 209 200 | (17, 13, 10) -> 254 253 252 |
| 0.71 | 0.7 | 0.118 | (0.94, 0.73, 0.58) -> 187 175 165 | (7.5, 5.8, 4.7) -> 249 244 240 |
| 0.80 | 0.6 | 0.047 | (0.37, 0.29, 0.23) -> 144 131 120 | (3.0, 2.3, 1.8) -> 230 221 214 |
| 0.87 | 0.5 | 0.016 | (0.12, 0.10, 0.08) -> 92 81 72 | (1.0, 0.78, 0.62) -> 190 178 168 |
| 0.92 | 0.4 | 0.004 | (0.03, 0.03, 0.02) -> 44 37 32 | (0.26, 0.20, 0.16) -> 127 114 104 |

- Scale 8, tint t, in general: centre = 8 t exposed (above the bloom threshold 1.5 inside r = 0.65), cream-white core,
  warm falloff, nothing past r = 0.9.
- The real lamp-post material is **scale 64**, power 6 (part 1, section 6a); "float 8" is the index of the scale in the
  base json, not its value. Face-on core 64 t exposed is what the bytecode gives; if the port shows 64 x, it agrees.
- Colour comes from the map, not just the tint: map mean (0.786, 0.624, 0.383), so the mean emission hue is
  1 : 0.62 : 0.30. A port using tint alone is paler than the game.

For the core to stay near exposed 1 at scale 8, X * Y would have to be about 1/8 (1/64 at scale 64). Nothing in the
bytecode supports that: the SSR / refraction round trip needs X * Y = 1.

## Why the reference can still show a small orange globe with little halo [I]

Not the emissive formula. Candidates, in order:

1. (N.V)^6 on a small sphere: energy is 1/4 of a flat disc and the outer third is below white and orange.
2. The bloom prefilter is luma-weighted (`w = 1 / (1 + Y)`, 5 taps, BLOOM.md). A globe a few pixels wide next to dark
   texels is averaged down hard: one tap at 64 among four at 0.2 gives about 0.5, below the 1.5 threshold, so no halo.
   Bloom only grows when the globe covers many pixels.
3. Bloom is a screen blend of bloom / 256 in display space, after the curve, so it cannot exceed white or widen much.
4. The map's own orange and dark areas, and the grade LUT.
5. Lit luminance never matters unless the glass itself is above exposed white.

If the port's globe has an enormous halo, check 2 and 3 (and that the falloff power 6 is live) before changing X.
