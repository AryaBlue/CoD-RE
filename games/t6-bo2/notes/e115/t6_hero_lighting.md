# T6 viewmodel lighting: probe choice, grid SH and hero lighting

How BO2 (`t6zm.exe`) lights the first-person gun, for R4b: which reflection probe it uses, where its K term comes
from, and what hero lighting is. Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in code or data at the address.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - Exe: the Steam `t6zm.exe` (32-bit), disassembled with capstone. Plutonium's exe matches it where checked.
  - Shaders: OAT Unlinker dumps of `zm_nuked.ff` and `common_zm.ff`, read through D3DDisassemble. Only names, slots and values are given here, no shader text.
- **Correction to `docs/rtx/r4_specular.md`:** the model K term is not built from L1 RGB SH (see [K](#the-k-term-vertex-shader)).

## Summary for E115

1. **The viewmodel has no special reflection scale.**
   - `occlusionAmount` is a **material** constant. The m1911 and most T6 guns have (1,1,1,1), so reflection y = 1, as in E115 now [V].
   - The real game's darker gun therefore has to come from K and from the probe choice [I].
2. **The probe and the grid sample are both taken at the player's eye position** (origin + view height + lean). They are not taken from the camera or the gun bones, and the probe is not a fixed one [V].
3. **`reflectionLightingSH` is the chosen probe's own `lightingSH`**, copied from the probe [V]. Not the cube's last mip.
4. **K uses 9-term SH:** a scalar per SH times an RGB colour, each clamped to ≥ 0.1 before the divide [V].
5. **Hero lighting is not a viewmodel path.** It applies to the materials that opt into it:
   - It is a per-material techset option (ray gun, bowie knife, monkey bomb, Olympia, char skin and cloth). The m1911 and most guns don't have it [V].
   - It does two things: an output colour matrix (the identity by default) and a sun scale.
   - It never touches the probe or grid SH [V].

## Which probe a model uses [V]

- **Every model goes through one lighting allocator,** `0x457970`, called at the entity's lighting origin. On a cache miss it picks:
  1. the first probe (index ≥ 1) whose probe volume (6 planes) contains the origin (`0x409490`);
  2. else the nearest probe by squared distance in the origin's cell list (`0x408ef0` for the cell, then `0x409230`);
  3. else, with no cell, the nearest of all probes ≥ 1 that have no volumes (`0x409410`).
- **Probe 0 means "none".** It is never picked by distance.
- **Storing and binding:**
  - The index is kept in the scene entity (+0x87), then in draw-surface bits 25..29.
  - `0x46b6f0` binds that probe's cube to PS t15, but only when the technique uses the probe.
- **Static models** use a precomputed byte (smodel instance +0x62); **world surfaces** use surface byte +0x35.
- **The viewmodel** is added at `0x53987a` (entnum 0x3ff) through the ordinary entity path `0x4106f0`.
  - Its lighting origin is ps origin xy, and z + view height (ps+0x208), with a lean offset added (`0x75f570`) [V; field names I].
  - So it is **the eye position**, with no gun offset or bob.
- `r_showReflectionProbeSelection` is registered but never read [V].

## The K term (vertex shader)

`vs_pimp_shader_lprobe_*` [V]:
- **cb3 layout:**
  - `gridLightingCoordsAndVis` @4
  - `gridLightingSH0-2` @5-7
  - `reflectionLightingSH0-2` @8-10
- **Each SH is evaluated as:**
  - a scalar second-order polynomial in N, with 9 coefficients: SH0.w, SH1.xyzw, SH2.xyzw;
  - multiplied by the RGB in SH0.xyz;
  - then clamped per channel to ≥ 0.1.
- **The divide:** `K = max(grid(N), 0.1) / max(refl(N), 0.1)`, sent to the PS (v9) and used as the reflection's scale.
- **reflectionLightingSH** = 0x30 bytes copied from `GfxReflectionProbe + 0xc` (stride 0x4c) at `0x46b787`. That is the probe's `lightingSH` [V].
- **gridLightingSH and coords** come from the model-lighting handle (`0x4576d0`, `0x457530`). It is filled from the world light grid at the same lighting origin as the probe [V for the call; I for the exact field].
  - coords.w = sun visibility / 255.
  - coords.xy = the handle's slot in the modelLighting 3D atlas.
- **PS diffuse ambient** = the modelLighting 3D texture (t13) at `N·lightingLookupScale/max|N| + coords`, squared, ×32, × `occlusionAmount` (z; x in the hero variant) [V].

## occlusionAmount [V]

- **It is a material constant.** The technique arg is `material.occlusionAmount`; there is no code or per-object write.
- **Components, normal lprobe PS:**
  - x = sun specular
  - y = reflection
  - z = model-lighting ambient
- **Components, hero variant:** x scales sun specular and ambient; y = reflection; z unused.
- **Values seen:**

  | occlusionAmount | materials |
  |---|---|
  | (1,1,1,1) | m1911, judge, b2023r, kard, python, hk416, m14, type95, olympia, saiga, dsr50, frag, semtex, claymore |
  | (0.7,1,1,1) | xm8 |
  | (0.5,0.4,1,1) | perk bottles |
  | (0.5,1,1,1) | visor / sunglasses |
  | none | viewmodel arms (char_skin / char_cloth techsets, another lighting model) |

## Hero lighting

**Dvars** [V]:

| dvar | type | default | range | global | registered |
|---|---|---|---|---|---|
| `r_heroLighting` | bool | 1 | | `0x34c52f8` | `0x423063` |
| `r_heroLightScale` | vec3 | (1,1,1) | 0..2 | `0x34c5564` | `0x4230c3` |

**Code constants** (per view, not per object) [V]:
- **`heroLightingR/G/B`** (const 0x97-0x99, b0[114-116]), filled by `0x416380`.
  - A 3x4 colour matrix: `diag(r_heroLightScale)` × a 6500K→6500K Bradford adaptation (`0x74d390`), which is the identity.
  - So it is **the identity by default**.
- **`lightHeroScale`** (const 0x9a, b0[57]) = (diffuse, specular, 1, 1), from `0x415d90`:
  - (1,1) when `r_heroLighting` is off;
  - `r_primaryLightTweakDiffuseStrength` / `...SpecularStrength` (default 1) when `r_primaryLightUseTweaks` is on;
  - else refdef +0x250/+0x254. Their normal writer is [U]: one CG path zeroes them (`0x657cc3`), and 1.0 is likely [I].

**Hero lights in the map** [V]:
- When `r_heroLighting` is on, `0x467370` walks `GfxWorld.heroLights` (count world+0x3ec, AABB tree +0x3f8) at each model's lighting origin.
- It adds those lights into that model's light-grid sample. This happens for every model, not only the viewmodel.
- Whether any ZM map has hero lights is [U].

**Shaders** [V]:
- **Who reads the hero constants:**
  - `heroLightingR` is read by 398 PS: lprobe hero variants, plus char_skin, char_cloth, embers, clan tag and player icon.
  - `lightHeroScale` is read by 160 lprobe sun variants.
  - No VS reads either.
- **Opting in:** hero-lit lprobe is a **per-material techset**.
  - With it: ray gun, bowie knife and monkey bomb (`mc_lit_sm_r0c0n0s0_7426e277`), Olympia, sog knife and optics (`..._r0c0n0s0o0_909j993q`), and the zombie wolf.
  - Without it: the m1911 (`mc_lit_sm_r0c0n0s0_zqq1fze7`) and most T6 guns (`mc_lit_sm_r0c0n0s0o0_3z86zq2z`).
- **The hero lit-sun math** (ray gun PS `d8b9d620`):
  - sun = `sunDiffuse × lightHeroScale.x × sunVis`, used for both sun diffuse and sun specular.
  - Then the whole lit colour (diffuse + reflection + sun) goes through the `heroLightingR/G/B` matrix, before fog and `hdrControl0.x`.
  - `lightHeroScale.y` is not read in the shaders checked.

## Other viewmodel differences

- **Render flags:**
  - The viewmodel ORs `0x40400001` when a weapon check passes (`0x5397be`) [V].
  - Bit 0x400000 is passed to the lighting allocator as its flag. Third-person weapons set it too [V]. Its meaning there is [U].
- **An extra pass:** `0x4106f0`'s argument 12 records a "viewmodel slot" (`0x3480008`) for an extra pass at `0x5c10d3`. The viewmodel sets it only when a weapon field (+0x1c) is 8 [V]. That pass is [U].
- **Not found:** a separate grid sample, forced sun visibility, or a viewmodel-only technique.

## For R4b

- **Probe and grid point:** sample the viewmodel's probe and grid at the player's eye: origin + view height (+ lean). Pick the probe with the volume → cell nearest → global nearest rule.
- **Reflection SH:** use the probe's own `lightingSH` from the zone, not the cube's last mip.
- **SH evaluation:** evaluate both SH as 9-term scalar × RGB, clamp each to ≥ 0.1, then K = grid / refl.
- **Material scale:** keep `occlusionAmount` per material (y = reflection). Guns are mostly 1.
- **Hero lighting:** with the defaults, the output matrix is the identity and lightHeroScale is (1,1) [I for the refdef path]. It can be skipped for parity until a map with hero lights or a non-default scale turns up.

## Open

1. What normally writes refdef +0x250/+0x254 (`lightHeroScale` for hero materials)?
2. What do render-flag bit 0x400000 and the `0x5c10d3` pass do in lighting?
3. How exactly does `0x457530`/`0x457b3b` build the grid SH, and how is sun visibility worked out at the eye?
4. Does any ZM map have `heroLightCount > 0`?
