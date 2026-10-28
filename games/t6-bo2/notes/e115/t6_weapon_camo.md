# T6 weapon camo (pack-a-punch): what the swapped material draws

BO2 applies camo, including the zombies pack-a-punch camo, by swapping materials. This note answers whether the
camo is a detail map over the gun's colour (as in T5) or a replacement colour, and what the swap needs. Researched
2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in data or shader bytecode.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - OAT Unlinker dumps of `zm_nuked.ff`: the camo assets, materials and techsets.
  - The camo pixel shader, read through D3DDisassemble.
  - Only values, slots and names are given here, no shader text.

## Answer

**T6 replaces the colour; it is not a detail map over the gun's colour [V].** Unlike T5, the camo material's
pixel shader never samples the gun's colour map. Its albedo is the **camo `ColorMap`, sampled at the gun's UV × a
tiling scale**, times the vertex colour.

**The swap itself.** `WeaponCamoMaterial` maps each base material to a camo material [V]:
- `mtl_t6_wpn_*` → `mtl_weapon_camo_zombies` for the PaP set on nuked, and `camo_zmb_dlc2` / `dlc4` on prison and tomb.
- Each mapping carries `shaderConsts[8]` and `replaceFlags` (useColorMap / useNormalMap / useSpecularMap).

**The camo material is a template** (techset `mc_sw4_3d_weapon_camo_*`) [V]:

| shader slot | in `mtl_weapon_camo_zombies` | meaning |
|---|---|---|
| `ColorMap` | `camo_zombies_col` | the camo colour |
| `SpecularAndGloss` | `camo_zombies_spc` | the camo specular (rgb) and gloss (a) |
| `Camo_Detail_Map` | `camo_zombies_nml` | the camo's detail normal |
| `Weapon_Normal_Map` | `camo_code_nml` | a placeholder for the gun's own normal map |
| `Weapon_Specular_Map` | `camo_code_spc` | a placeholder for the gun's own specular map |

- **The placeholders:** the `camo_code_*` slots are filled at runtime with the base material's maps when the matching `replaceFlags` bit (useNormalMap / useSpecularMap) is set [I: from the slot names and the flags; the swap code wasn't traced].
- **Material constants:** ReflectionAmount and SpecularAmount are (1,0,0,1).

## The pixel shader

`ps_pimp_shader_sw4_3d_weapon_camo_3dab0a24` (lit sun) [V]:
- **Per-object constant:** `weaponParam6` (cb1[37]) drives it. It is the camo's `shaderConsts[0..3]` [I: the values below fit it].
- **Camo UV** = `uv × weaponParam6.xy`. `ColorMap`, `SpecularAndGloss` and `Camo_Detail_Map` are all sampled there. The gun's own normal and specular maps are sampled at the plain `uv`.
- **Albedo** = `ColorMap(camoUV).rgb × vertexColour`, squared (gamma to linear). **No base colour.**
- **Gloss** = `lerp(SpecularAndGloss.a, Weapon_Specular_Map.a, weaponParam6.z)`.
- **Specular colour** = `SpecularAndGloss.rgb` (the camo's), with the usual T6 Fresnel and probe reflection.
- **Normal** = vertex normal + `gunNormal.xy × [w ≥ 10]` + `detailNormal.xy × (w ≥ 4 ? w − 10 : w)`, where `w = weaponParam6.w`.
  - So w packs "use the gun's normal map" (+10) and the detail-normal strength.
  - That fits `w = shaderConsts[3] + (useNormalMap ? 10 : 0)` [I]:

    | camo | consts | useNormalMap | w | result |
    |---|---|---|---|---|
    | zombies | (2,4,0,0) | yes | 10 | gun normal on, no detail |
    | gold | (8,8,0.24,0) | yes | 10 | gun normal on, no detail |
    | diamond | (6,5,0,1) | no | 1 | no gun normal, detail 1 |

### Detail normal, gloss mix and useColorMap in detail

**Slots** (technique `pimp_technique_sw4_3d_weapon_camo_670d87b3`) [V]:
- All five textures are **material** samplers: `material.<name>`. `weaponParam6` is the only camo code input.

| shader slot | reg | sampled at | channels used | material semantic (OAT) |
|---|---|---|---|---|
| `Weapon_Normal_Map` | t1/s1 | gun `uv` | .xy | color1Map (placeholder `camo_code_nml`) |
| `Camo_Detail_Map` | t0/s2 | `uv × weaponParam6.xy` | .xy | normalMap |
| `SpecularAndGloss` | t3/s3 | camo UV | .rgb spec colour, .a gloss | colorMap |
| `Weapon_Specular_Map` | t4/s4 | gun `uv` | **.a only** | color2Map (placeholder `camo_code_spc`) |
| `ColorMap` | t2/s5 | camo UV | .rgb | colorMap |

**The normal** [V]:
- Both normal maps are decoded as `xy × 4.015748 − 2.015748` (±2 range); z isn't read.
- `gunW = (w ≥ 10) ? 1 : 0`.
- `detailW = w − (w ≥ 4 ? 10 : 0)`.
- `n.xy = gun.xy × gunW + detail.xy × detailW`.
- `N = normalize(Nvert + n.x × T + n.y × B)`, with `B = cross(Nvert, T) × tangent.w`.
- So w packs the detail-normal strength and "use the gun's normal map". The window 4 ≤ w < 10 would give a negative detail weight, so the encoding is clearly meant as `w = shaderConsts[3] + 10 × useNormalMap` [I].
- **M14, set 3** (the zombies camo): shaderConsts (6.12, 5.92, 0, **0.4**) with useNormalMap set.
  - That gives w = 10.4: the gun normal map is on, and the camo detail normal is added at **0.4** [I: the +10 encoding].
  - The camo normal tiles at 6.12 × 5.92.

**Gloss** [V]:
- `g = lerp(SpecularAndGloss.a, Weapon_Specular_Map.a, weaponParam6.z)`, i.e. z = 0 is all camo gloss and z = 1 is all gun gloss.
- g then drives everything the normal T6 lit path does:
  - sun spec power `2^(13g)`, normalised by `2^(13g)/8 + 1/4`;
  - the probe mip `4 − 4g`;
  - the gloss-dependent environment Fresnel polynomial.
- The specular colour is always `SpecularAndGloss.rgb²` (the camo's). The gun's specular rgb is never sampled.

**useColorMap** [I]:
- It isn't visible in the shader: there is no separate gun-colour slot, and albedo is always `ColorMap(camoUV)`.
- Only one shipped camo sets it: Five-seven `mtl_weapon_camo_gold_alt`, flags (1, 1, 1). Its consts are (1, 1, 0.73, 0), i.e. **1× tiling**.
- That fits useColorMap meaning "put the base material's colour map in the `ColorMap` slot", drawn untiled at the gun's UV. The same goes for useNormalMap / useSpecularMap filling the `camo_code_*` placeholders.
- The engine code that does the swap wasn't found: no slot-name hashes are baked into code, so it presumably works by slot index or semantic [U].

**Flags across nuked's 171 camo entries** [V]:

| (useColorMap, useNormalMap, useSpecularMap) | count |
|---|---|
| (0,1,1) | 76 |
| (0,1,0) | 70 |
| (0,0,0) | 22 |
| (0,0,1) | 2 |
| (1,1,1) | 1 |

**Values for the zombies PaP camo on nuked** (`camo_dsr50`, `camo_m14`… set 3) [V]:
- `shaderConsts` = (2, 4, 0, 0): the camo tiles 2× in u and 4× in v, and the gloss is all camo (z 0).
- useColorMap 0, useNormalMap 1, useSpecularMap 0.

## What our export does

`tools/zonedump/MaterialTable.cpp` + `ExportModel.cpp`, read only:
- **The swap is right in kind.** `drawn()` swaps the base material for the camo material, and the colour comes out as `camo_zombies_col`.
- **Missing: the tiling.** `shaderConsts.xy` is never applied, so the camo is drawn at 1× instead of (2,4) [I: likely the visible error].
- **Probably wrong: normal and specular.**
  - `Weapon_Normal_Map` / `Weapon_Specular_Map` resolve to the `camo_code_*` placeholders, not the gun's maps.
  - Whether `materialMaps` even recognises this techset's slot names is unchecked [U].
- **T5 path** (camo image put in the colour slot): per the RTX worker, T5 is a `colorDetailMap` (color7, tiled by `colorDetailScale`) over the base colour, so that path is the one that's conceptually wrong. T6 genuinely replaces the colour.

## Suggested fix (RTX worker's call)

1. Export the camo's `shaderConsts` and `replaceFlags` per swapped material, e.g. on `MaterialData` or as a UV transform.
2. Tile all camo-UV samples by `.xy`.
3. When the flags say so, take the normal map (and the specular map for gloss) from the **base** material rather than the `camo_code_*` placeholders.
4. Use the camo `SpecularAndGloss` for the specular colour.
5. Keep the vertex-colour multiply.

## Open

1. Trace the engine code that fills `weaponParam6` and the `camo_code_*` slots, to confirm the +10 encoding and the placeholder replacement.
2. `useColorMap = 1` (only the Five-seven gold_alt): confirm it puts the gun's colour map in `ColorMap` (see above, [I]).
3. Check the prison (`camo_zmb_dlc2`) and tomb (`camo_zmb_dlc4`) materials use the same techset.
