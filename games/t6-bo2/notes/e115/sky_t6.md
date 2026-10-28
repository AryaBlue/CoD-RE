# T6 sky shader (skycubemaphdr): rotation, HDR decode, fog

What BO2's sky material does, read from its own shaders. Material: `mc/mtl_dlc0_zm_skybox_nuketown`, techset
`mc_skycubemaphdr_1f117w7u`, shader `pimp_shader_skycubemaphdr_2306aa25`. Researched 2026-10-26.

## Conventions

- **Status tags.**
  - **[V]** verified in the disassembly.
  - **[V-data]** verified on exported zone data.
  - **[I]** inferred.
- **How the shaders were read.** The VS/PS bytecode was dumped from the material's lit technique (technique 2), then
  disassembled with D3DCompiler_47 `D3DDisassemble`.
- **Bindings.** Pass args bind the material constants:
  - one material vertex const at VS `cb2[1]` (byte offset 16);
  - one material pixel const at PS `cb2[2]` (byte offset 32).
- **Which constant is which.** By value, VS `cb2[1]` is `skyBoxRotation` and PS `cb2[2]` is `skyColorParm` **[I]**.
  - The constant name hashes weren't matched.
  - The value fit is exact: the rotation is a unit (sin, cos) pair with ±8000 in w, and the PS reads x as a flag and y
    as a scale.

## Material constants (zm_nuked)

| constant | value | used by |
|---|---|---|
| skyBoxRotation | (0.743145, 0.669131, -0.743145, 8000) | VS: cube lookup rotation |
| skyColorParm | (1, 6, 1, 1) | PS: HDR flag, scale, —, fog weight |
| cloudsUVMad1/2, cloudsUVMul1/2, skyBoxCloudW, cloudsHeight, cloudsFeather | — | not bound by this technique |

T5 zombie_theater `mc/mtl_skybox_zombie_theater` (`mc_sky_cubemap_hdr`) has skyBoxRotation
(-8.74228e-08, -1, 8.74228e-08, -8000) **[V-data]**.
- -8.74228e-08 is exactly float `sin(pi)`, so the turn is 180°.
- The T5 shader is now read too (DX9 bytecode, see "T5 shader" below). Its skyBoxRotation constant has the same hash
  (0xd8e38a65) and the same use as T6 **[V]**.

## Vertex shader [V]

```
dir.x = v.x * R.y - v.y * R.x        // R = skyBoxRotation, R.z == -R.x
dir.y = v.x * R.x + v.y * R.y
dirA.z = R.w < 0 ? -v.z : v.z        // primary sample
dirB.z = -dirA.z                     // second sample, z mirrored
blend  = cb0[101].x                  // code constant, probably the sky transition [I]
```

- The rotation is about cod up (z): cos = `R.y`, sin = `R.x`. Nuketown turns 48°, Kino 180°.
- The ±8000 magnitude in `R.w` isn't used; only its sign is.
- zonedump writes `e115_sky_rotation: [cos, sin]` = `[R.y, R.x]`.
- zonedump writes `e115_sky_flip_z: true` when `R.w < 0`; negate cod z after the turn. The second, mirrored sample
  is not exported: every sky seen has a transition of 0 in practice [I].
- Nuketown has w > 0, so its primary is unmirrored.
- Kino has w < 0, so its primary is z-mirrored **[V, T5 vs read]**.

## Pixel shader [V]

```
if (P.x > 0)  c = cube.rgb / (cube.a + 1e-6)     // P = skyColorParm; alpha is a divisor (HDR encode)
else          c = cube.rgb * cube.rgb            // gamma-2 decode
c   = lerp(cA, cB, blend)
c   = M3x3(cb0[144..146]) * c                    // code colour matrix
c  *= P.y                                        // 6 on nuketown
lin = c * cb0[141].x                             // code exposure/scale [I]
f   = heightFog(view ray) * fogAmount(vs)        // the same exp fog as the world
out = lin + P.w * f * (fogColour - lin)
out *= cb0[20].x
o.rgb = sqrt(out)                                // gamma-2 encode; o.a = 1
```

**sRGB or linear.** The game samples the cube raw, as UNORM, and does gamma 2 by hand **[I, strong]**:

- The non-HDR branch squares the sample, and the output is `sqrt()`. A hardware sRGB decode would make that a double
  decode.
- In the HDR branch, `rgb / a` is already a linear HDR value. Then ×`P.y`.

For E115:

1. Sample the sky cube **without** sRGB decode.
2. Compute `rgb / max(a, 1e-6) * skyColorParm.y`.
3. Treat the result as linear radiance. Our sRGB swapchain does the encode.

E115 currently marks every non-BC5 image sRGB (`tools/zonedump/main.cpp:80`, an assumption). That is wrong for HDR
sky cubes.

## T5 shader (sky_cubemap_hdr) [V]

- Same vs as T6: the turn about cod z by skyBoxRotation, z mirrored when w < 0.
- The ps has no skyColorParm. It squares the sample (gamma-2 decode) and scales by `cloudsHeight.z` (hash 0x1bcf62ae,
  c20), then the same sqrt output. Kino: `cloudsHeight.z` = 4.
- zonedump writes `e115_sky_hdr: [0, cloudsHeight.z]`: flag 0, so the colour is the srgb-decoded sample (which
  approximates rgb^2) times the scale.

## uvScroll (T4/T5)

- `uvScroll` is a material constant on T4 and T5 materials **[V-data]**.
  - Non-zero only on T4 nazi_zombie_prototype's sky cloud layers: `mtl_skybox_zombie_bot_clouds` (0.004, 0.0042) and
    `mtl_skybox_zombie_top_clouds` (0.001, 0.001).
  - The 21 T5 ones are all 0.
- zonedump writes `e115_uv_scroll: [u, v]` when it is non-zero.
- Units: uv per second **[I]**. The T4 shader isn't read. Those speeds give a slow cloud drift.
- T6 has per-layer `Layer1Scroll` / `Layer1Rotation` on 3-layer unlit decals (the nuked radiation puddles) instead.
  They are not exported.
