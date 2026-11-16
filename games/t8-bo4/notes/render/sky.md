# BO4 (T8) sky: how zm_escape's night sky is drawn

<!-- toc -->
## Contents

- [0. Short version](#0-short-version)
- [1. Assets and where they are](#1-assets-and-where-they-are)
  - [The mesh **[P]**](#the-mesh-p)
- [2. Textures](#2-textures)
- [3. The material: constants and what the shader does with them **[P]**](#3-the-material-constants-and-what-the-shader-does-with-them-p)
- [4. Brightness in scene units](#4-brightness-in-scene-units)
- [5. Orientation](#5-orientation)
- [6. Sun cookie `cookie_sun_clouds`](#6-sun-cookie-cookie_sun_clouds)
- [7. To draw this](#7-to-draw-this)
<!-- /toc -->

Offline read of your own zones and xpaks. Marks: **[P]** proven from the data or the shader bytecode,
**[I]** inferred, **[?]** unknown. Scene unit: 1.0 = 100 nits before exposure.

## 0. Short version

- The sky is an **xmodel** (a dome) with one material; the picture is an **8192 x 4096 lat-long BC6H (unsigned float) map**,
  `i_skybox_zm_escape_override`, sampled by view direction, not by the mesh UVs. **[P]**
- Brightness: `radiance = texture * 0.25`. Upper-hemisphere mean (0.0128, 0.0145, 0.0235); median luminance 0.0023; the
  moonlit cloud peaks at 0.56 (8K: 0.59). **[P]** for the numbers, **[I]** that 0.25 is the only scale (it fits the bake, section 4).
- No rotation, no mirror: `u = 0.5 - yaw/360`, `v = (90 - elevation)/180` with world yaw from +X towards +Y, +Z up. **[P]** shader,
  **[I]** that the engine's sky rotation is zero (the moon check in section 5 agrees).
- There is no moon disc and no stars in the map: it is storm cloud with a moonlit break, plus town lights on the horizon. **[P]**
- Height fog is applied to the sky in its shader (towards the navy fog colour at the horizon). Froxel fog is not. **[P]**

## 1. Assets and where they are

All bodies are in the **zm_escape** zone itself (real bodies, not stubs), base and patched alike. Offsets: patched =
`work17\dec\zm_escape.ff.dec`, base = `<work>\zm_escape.ff.dec`.

| what | name / hash | where |
|---|---|---|
| lighting state 1 | skybox name `skybox_zm_escape_override` at state +0x20 | patched 0x18c6b1c4 **[P]** |
| xmodel | `skybox_zm_escape_override`, hash 249f782b5e492972 | patched 0x174fa9bf, base 0x14c64215 (asset 39725) **[P]** |
| material | unnamed, `xmaterial_36aacbf5cb9a8d3`, 13 textures | patched 0x1657802c, base 0x13d064ed **[P]** |
| pixel shader | 16,520 B (base 16,492 B) | patched 0xd12cc95, base 0xd18fcfa **[P]** |
| vertex shader | 4,204 B | patched 0xcc79461, base 0xd18ec66 **[P]** |
| colour map | `i_skybox_zm_escape_override`, image hash 0ab153c4e27b9316 | body patched 0xee80ae1; pixels in `zone\base.xpak` **[P]** |

The material is found from the model's material list (t8models\xmodels.json); the shader from the material's texture
semantics (t8mat\shaders2.pkl: the only pixel shader binding this set). Listings in `asm\`.

Other states: state 2 `skybox_zm_escape_override_lightning` = the same colour map through a one-texture shader with scale
**4.0**; states 3 and 4 `skybox_zm_escape_vortex` (its own 8K map + six cloud layers, not decoded here);
`skybox_default_black` scale 0.000977. **[P]**

### The mesh **[P]**

Dome, radius 783 units, z from -266 to +374, 277 vertices / 448 triangles at the top LOD (6 LODs, all the same shape), one
bone `t6_skybox`. Already on disk: `t8models\mesh\skybox_zm_escape_override.npz`. The vertex shader normalises the vertex
position and scales it by a per-view constant (cb2[74].z), adds no model matrix and writes depth 0 (far plane, reversed Z):
the dome is camera-centred and its size does not matter. Its UVs (a planar top-down projection) are **not used** by the
pixel shader. To draw it, any camera-centred sphere, cube or full-screen pass with the view direction does the same job.

## 2. Textures

Pulled by xpak key with `pull.py` (keys from the image bodies; all in `zone\base.xpak` except the 64 px one).
The xpak index text gives width and height the other way round from the zone; the zone (8192 wide) is right. **[P]**

| slot (shader register) | image | format, size | values | file here |
|---|---|---|---|---|
| colorMap (t0) | i_skybox_zm_escape_override | BC6H_UF16, 8192x4096 (+4096, 2048, 1024 mips as separate stream objects) | linear float, 0 .. 3.99; see below | `i_skybox_zm_escape_override_{8192,4096,2048}.dds`, `_4096.hdr`, `_2048.hdr`, `_2048.f32.npy` |
| cloud layer 2 mask (t25, semantic e566b554) | skybox_clouds_cumulus1_mask | BC4, 2048x2048, tiles | 0 .. 0.447, median 0.20 | `.dds`, `.png` |
| cloud layer 1 mask (t22, e566b555) | ximage_69ea2734ef1da8d7 | BC4, 2048x2048 | 0 .. 0.98, median 0 | `.dds`, `.png` (layer is switched off) |
| horizon band mask (t38, 404ef853) | ximage_68aac921bc7f78b7 | BC4, 2048x512 | 0 .. 0.95, median 0 | `.dds`, `.png` |
| cloud layer 2 colour (t24), two disc colours (t46, t62) | $white_diffuse_hdr | stand-in, white | 1 | - |
| cloud layer 1 colour (t21), horizon colours (t26, t30) | $black_color | stand-in, black | 0 | - |
| sky-wide cloud mask (t37, 0c154291) | $white_reveal | stand-in, white | 1 | - |
| disc masks (t60, t64) | $black_reveal | stand-in, black | 0 | - |

Colour map numbers (unscaled texture values, solid-angle weighted where it says mean) **[P]**:

- min 0, max 3.99 (8K) / 3.80 (2K); brightest pixel (1.97, 2.34, 3.99), blue-white.
- luminance percentiles over the whole map: p50 0.0018, p90 0.033, p99 0.50, p99.9 1.19.
- mean rgb, upper hemisphere (0.0511, 0.0580, 0.0939); lower hemisphere (0.00026, 0.00027, 0.00034): the ground half is black.
- The decoder (`bc6.py`, all 14 modes) agrees with Pillow's BC6H decode to 1/255 on the 2K mip.
- The 2K and 4K stream objects have the same means as the 8K to 4 digits, so the 2K or 4K file is enough for a port.

Colour space **[P]/[I]**: the sky shader uses the texture as it is: there is **no 709 -> 2020 matrix** in it, unlike the
albedo path in BO4_LIGHTING_SPEC.md. So the map is either authored in the working space (Rec.2020 linear) or simply left
unconverted. The difference is small for this blue-grey; treat the values as scene-linear.

## 3. The material: constants and what the shader does with them **[P]**

Patched pixel shader cb0 (33 rows; the base zone's has 32 and every index is one lower, values identical):

| cb0 row | value | meaning (from the bytecode) |
|---|---|---|
| [32].w | **0.25** | final brightness scale of the whole sky |
| [32].xyz, [24..31] | 0 ; [27].w = [31].w = 1 | two "disc" layers (planet / moon cards). Their size divisor is 0, so they never draw |
| [2].zw | 1, 1 | horizon band: alpha scale, azimuth sign |
| [3] | 1, 0.007, -0.05, 0 | horizon band: height scale, scroll in u per second, height offset, (moon-glow power, unused) |
| [4].x | 0.5 | horizon band on (> 0). Its colour = [4].x * [5].rgb * black stand-in = black |
| [5] | 1, 1, 1, 1 | horizon band tint, alpha power |
| [10] | 0, 0.0015, **0** | cloud layer 1 scroll; brightness 0 = **layer 1 off** |
| [11] [12] [13] [14] | (0.008, 0.008, 0, 0) (0, 0, 1.5, 3) (45, 1.2) (1, 1, 1, 1.5) | layer 1 tiling, horizon fade, rotation deg + deg/s, tint + alpha power (all unused) |
| [15] | 0, 0.05, **1** | cloud layer 2 scroll (u, v per second), brightness 1 = on |
| [16] | 0.03, 0.03, 0, 0 | layer 2 tiling, offset |
| [17].zw | 1, 3 | layer 2 horizon fade: `min(1, (dir.z * 1)^3)`, zero below the horizon |
| [18].xy | 90, 0 | layer 2 rotation in degrees, degrees per second |
| [19] | 0.8, 1.0, 1.7, 4 | layer 2 colour, alpha power |
| [21].z | 0 | moon-glow tint of the layers: off |

Vertex shader cb0: one row (200000, 200000) = the two cloud plane heights in units, passed on times 1e-4 **[P]** (which
component belongs to which layer **[I]**).

In order, for view direction `d` (unit, world, z up) and time `t` (cb2[89].w, seconds **[I]**):

1. **Base**: `c = tex(colorMap, u = 0.5 - atan2(d.y, d.x)/2pi, v = acos(d.z)/pi)`. Mips from the direction's derivatives.
2. **Cloud layer 2** (the only live layer): a plane 200000 units up, seen from the camera:
   `p = 20 * (-d.y, d.x) / d.z + cam.xy * 1e-4` (the 90 degree turn applied), `uv = p * 0.03 + (0, 0.05) * t`,
   `a = cumulus_mask(uv).r ^ 4 * min(1, d.z^3)`, zero below the horizon, `c = lerp(c, (0.8, 1.0, 1.7), a)`.
   One tile spans tan(zenith angle) = 1.67; alpha peaks at 0.035 and averages 0.0009 over the upper half, so this is a faint
   blue drifting veil: about +10 % on the dark parts, nothing on the lit cloud. v scrolls a full tile in 20 s **[I: time unit]**.
3. **Horizon band**: `h = d.z - 0.05`; where 0 <= h <= 1: `uv = (-yaw/pi + 0.007 t, 1 - h)` (the 2048x512 mask wraps twice
   round the horizon, bottom row at 2.9 degrees elevation), `m = mask.r`, `c *= 1 - m * m * (v < 0.1 ? 10 v : 1)`.
   Black silhouettes of cloud bank low in the sky, turning slowly (one tile = 180 degrees of yaw in 143 s **[I]**).
4. `c *= 0.25`.
5. **Sky fog** (same form as world height fog, section 6b of the spec, but its own parameter rows cb3[63..65]; colour is the
   shared cb3[61].rgb): distance is taken as 3.15e9 units along `d`,
   `T = clamp(2^(H * cb3[63].w * dist + cb3[64].w), cb3[65].w, 1)`, `c = lerp(fogColour, c, T)`.
6. Box / water volume fog (inactive on this map), then **atmospheric extinction** over at most cb3[82].w units
   (per-channel multiply, a few per cent).
7. `c *= exposure` (cb2[110].y), values under 6.1e-5 zeroed, clamp 65024, dither. Alpha 1. No froxel fog, no tone map here.

`preview_composite.png` is steps 1-4 at t = 0 (no fog), `sky_composite_t0_2048.f32.npy` the same in float.

Values of cb3[63..65] **[?]**: CPU side, not located. If they equal the world set (fog block B: half distance 3500, half
height 1050, base -450, max opacity 0.75, colour (0.0191, 0.0247, 0.0388)) then for a camera near z = 300:
`T = 2^(-0.18 / d.z + 0.03)` clamped to >= 0.25: 0.90 at the zenith, 0.79 at 30 degrees, 0.49 at 10 degrees, 0.25 (the
clamp) below about 5 degrees. That would put 75 % fog colour on the horizon, which is brighter and bluer than the sky there
and reads as the navy rim in the reference video **[I]**. Block B's unexplained pair (0, 800) may belong to this set **[?]**.
Worldspawn also carries the keys `sky_intensity_factor0/1` with no value found **[?]** (could be a further CPU-side multiplier).

## 4. Brightness in scene units

`radiance = texture * 0.25` (before fog and exposure):

| | luminance |
|---|---|
| upper hemisphere mean rgb | (0.0128, 0.0145, 0.0235), luminance 0.0148 (1.5 nits) |
| upper hemisphere p10 / p50 / p90 / p99 / p99.9 | 0.0006 / 0.0023 / 0.028 / 0.19 / 0.33 |
| brightest cloud edge | 0.56 at 2K, 0.59 at 8K (rgb up to (0.49, 0.58, 1.0)) |
| within 10 degrees of the moon direction | 0.054 mean |

Irradiance from the sky alone on the six axis faces (luminance, scaled): +X 0.0559, -X 0.0048, +Y 0.0085, -Y 0.0256,
+Z 0.0494, -Z 0.00001. Mean of six = 0.0240; **divided by pi = 0.00765** (rgb 0.0066, 0.0075, 0.0121).

Cross-check with the bake: t8light\gi gives a median ambient-cube value (mean of six) of **0.0077** for outdoor cells with no
lamp near. The sky alone, at scale 0.25, gives 0.00765 if the cubes hold irradiance / pi (i.e. the colour that multiplies
albedo). Without the 0.25 it would be 0.031, four times too bright. So 0.25 fits, and the bake stores E / pi **[I]** (one
agreeing number, not a proof: it is the median of cells that also see some occlusion and some moon bounce).
For scale: the moon is 0.42 * (0.451, 0.540, 0.973), luminance 0.23 as irradiance facing it, about five times the sky's +Z
irradiance (0.049).

The sky is strongly one-sided: the +X / -Y quadrant (towards the moonlit break) sends 5-10 times what -X / +Y sends.

## 5. Orientation

From the shader **[P]**: +Z is up (v = 0 at the zenith, v = 0.5 the horizon), `u = 0.5 - yaw/360` with
yaw = atan2(y, x): the map's centre column looks along +X, columns to the right look towards -Y (yaw 270 at u = 0.75),
columns to the left towards +Y. Pixel -> direction: `yaw = (0.5 - u) * 360`, `elevation = 90 - 180 v`.

The vertex shader can turn the lookup direction by three angles held in per-view constants (cb2[74].xy = sin/cos of a yaw,
cb2[75] = sin/cos of two tilts). These are engine values (the old r_skyRotation idea), not in the material or the lighting
state; taken as zero **[I]**. The cloud layers use the unturned direction.

Moon check **[I]**: the state's moon (pitch 59, yaw 338) lands at u 0.561, v 0.172 (pixel 1149, 176 of 2048x1024; marked on
`preview_composite_moon_marked.png`). No disc is painted, but that point sits on the top edge of the bright break in the
cloud: mean luminance within 20 degrees of it is 0.22 (texture units) against 0.059 for the whole upper half and 0.109 for
the same cone on a mirrored map. The centroid of the brightest 0.5 % of pixels is pitch 37, yaw 343 (22 degrees below the
moon: the lit cloud hangs under it). Turning the map moves the best fit by under 10 degrees. So: no mirror, no rotation.

## 6. Sun cookie `cookie_sun_clouds`

- Image body in the patched zm_escape zone at 0xf39a8ed, **resident** (no xpak object): 512x512 R8G8B8A8, ten mips stored
  smallest first, 1,398,100 bytes. Grey (r = g = b to 2/255), alpha 255. Values 0 .. 1, mean 0.653: soft dark blobs on
  white. Top mip in `cookie_sun_clouds.png`. **[P]**
- Use (BO4_LIGHTING_SPEC.md section 4): `moon *= 1 + strength * (tex - 1)`, world XY projected by cb3[32..33]. **[P]**
- Lighting state fields around the name (state +0x7c), identical in all four states, against the engine-default record:

| offset | value | default | reading |
|---|---|---|---|
| +0x78 | 0.9 | 1 | strength: darkest cloud shadow leaves 10 % of the moonlight **[I]** |
| +0xbc | 0.0004 | 0.001 | scale, uv per unit: one tile = 2500 units **[I]** |
| +0xc4 | 0.085 | 0 | **[?]** (rotation or a scroll term) |
| +0xd0, +0xd4 | 0.008, 0.01 | 0, 0 | scroll x, y in uv per second: a tile passes in about 100 s **[I]** |
| +0xd8 | 8 (int) | 0 | **[?]** |

  How the CPU folds these into cb3[32..33] was not read; the mean of the cookie (0.653, i.e. 0.69 after strength) is the
  average dimming of the moon on open ground.

## 7. To draw this

1. Texture: `i_skybox_zm_escape_override_2048.hdr` (or the 4096 .hdr / .dds; the 8K only matters for the cloud edges up close).
   Linear float, no sRGB decode. Lat-long, clamp v, wrap u.
2. Lookup with the world view direction, z up: `u = 0.5 - atan2(d.y, d.x) / (2 pi)`, `v = acos(d.z) / pi`. No rotation.
3. `colour = texel * 0.25`. That is scene units; the port's exposure and tone map apply as for everything else.
4. Optional, cheap, matches the game: cloud veil `colour = lerp(colour, (0.8, 1.0, 1.7) * 0.25, mask(uv)^4 * saturate(d.z)^3)`
   with `uv = 0.6 * (-d.y, d.x) / d.z + (0, 0.05 t)` from `skybox_clouds_cumulus1_mask_2048`; and the black horizon band
   from `ximage_68aac921bc7f78b7_2048x512` (section 3, step 3). Both can be left out at first: together they change the
   upper-half mean by 2 %.
5. Fog: apply the map's height fog to the sky at "infinite" distance with its 0.75 opacity cap (section 3, step 5), lerping
   towards (0.0191, 0.0247, 0.0388). No froxel fog on the sky. This is what makes the horizon navy rather than black.
6. Draw at the far plane, camera-centred, after opaque geometry; no depth write.
7. The lower hemisphere of the map is black (0.0003): anything seen below the horizon (the sea) needs its own surface.
8. Lightning state: the same map * 4.0 with none of the layers (16 times the normal sky), and the moon * 8.

Not done: the vortex sky's textures and layers (states 3, 4); the values of cb3[63..65]; cb2[74..75] at run time.
