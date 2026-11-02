# T5 weapon colour detail (`weapon_camo_neutral` and the others)

What a T5 gun's default colour detail slot is, how it tiles, and how it combines with the gun colour, so that the
non-PaP guns draw it too. Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in data or shader bytecode.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - OAT Unlinker dump of T5 `common_zombie.ff`: materials, techsets, techniques, shader_bin and images.
  - The shaders, read through D3DDisassemble.
  - Only names, registers, values and maths are given here, no shader text.

## Slot and tiling [V]

- **Texture slot:** `colorDetailMap` (OAT semantic color7Map). The shaders sample it as `colorDetailMapSampler`.
- **Constant:** `colorDetailScale`. Only `.xy` is used; it is the UV tiling of the detail map.
- **Sampler:** wrap on every material (none clamp).
- **Techsets:** `mc_l_sm_*_wpn_clrdtl[_hero]` and `mc_l_sm_*sc0x0_clrdtl*`.
  - 97 materials in common_zombie have the slot.
  - 71 of them use `mc_l_sm_r0c0n0s0_wpn_clrdtl`.
- **Techniques:** every lit technique of the techset is an lprobe technique that binds `colorDetailMap` and `colorDetailScale`:

  | technique | technique name | pixel shader |
  |---|---|---|
  | lit | `lprobe_47db1249` | `lprobe_17fa5aa3` |
  | lit sun | `lprobe_71514e1b` | `lprobe_59382ee4` |
  | lit sun shadow | `lprobe_7722a335` | `lprobe_30742b15` |
  | lit spot | `lprobe_664feba3` | `lprobe_8a7eb22d` |

  - In all four pixel shaders the detail is sampled at `uv × colorDetailScale.xy` and offset by −0.5.

## How it combines [V: lit sun and lit, in full]

```
d      = colorDetailMap(uv × colorDetailScale.xy).rgb − 0.5
albedo = saturate(colorMap(uv).rgb + d × colorMap(uv).a) × vertexColour.rgb
linear = albedo²          // gamma → linear, then the usual t5 lprobe lighting
```

- **It is a signed add, masked by the colour map's alpha.** 0.5 grey is neutral; brighter lightens, darker darkens.
- **Mask:** colour alpha 0 leaves the gun colour untouched, and 1 applies the full detail.
- **Order:** the add happens in gamma space before squaring, and before the vertex-colour multiply.
- **Other textures:** normal, specular and occlusion are sampled at the plain `uv`; the detail affects only albedo.
- **Lit sun shadow and spot:** the tiling and the −0.5 offset are [V]. The rest of the combine is [I: same pattern].

## The images [V: decoded top mip]

| image | size | value | effect `d` |
|---|---|---|---|
| `weapon_camo_neutral` | 128² | flat 0.502 grey | +0.002, i.e. **no visible change** |
| `weapon_camo_off` | 128² | flat 0.502 grey | +0.002, no change |
| `cammo_gunmetal` | 32² | flat 0.278 grey | **−0.222 × colour.a**, a darkening |
| `cammo_gunplastic` | 32² | flat 0.278 grey | −0.222 × colour.a |

- These four are flat (zero variance), so their `colorDetailScale` doesn't matter.
- The other `cammo_*` images (wood_tile, base_*, tan_*, plastic_*, od_green_aug…) are per-gun and weren't measured [U].

**colorDetailScale across the 97 materials:**

| image | scales (count) |
|---|---|
| `weapon_camo_neutral` | 8×8 (18) |
| `weapon_camo_off` | 8×8 (13), 1×1 (5), 2×2 (2), 4×2 (2), 3×2 (1), 0.7 (1) |
| `cammo_gunmetal` | 0.5–2 |
| `cammo_gunplastic` | 1–8 |
| everything else | 1–4 |

## What it means for us

1. **The neutral and off guns:** drawing the detail or not looks the same, because 0.502 is neutral. The visible case is the gunmetal/gunplastic guns (and the per-gun `cammo_*` ones), which are **darker** where colour alpha is high.
   - If our T5 path currently puts the detail image *into* the colour slot (`GameProfile.cpp:904`, the [I] stand-in), that is wrong in kind: it replaces the gun with flat grey. The detail should stay a separate texture.
2. **Fix:**
   - Keep `colorMap` as albedo.
   - Bind `colorDetailMap` as an extra texture with the `colorDetailScale` tiling (already exported: `MaterialMaps.cpp:191` `colourDetailScale`).
   - Apply `saturate(c.rgb + (detail − 0.5) × c.a)` before the gamma-to-linear square.
   - This needs the colour map's **alpha** kept, not dropped.
3. **Camos (MP / PaP):** a camo goes into this same slot and is tiled by the same scale, as a signed add over the gun colour masked by its alpha [I: the slot is named camo and this is how T5 camo layers]. So the same shader path draws both the default detail and the camo.

## Open

1. Confirm the full combine in the sun-shadow and spot pixel shaders [I].
2. Measure the per-gun `cammo_*` images (wood, tan, base…), which may be real patterns where the tiling matters.
3. Check whether T5 swaps this slot at runtime for the PaP camo 15 or swaps the whole material (`GameProfile.cpp:904` note).
