# BO4 (T8) primary lights, light exploders and lighting states (zm_escape)

Read offline from the decompressed `zm_escape` zone (base and bdiff-patched). Marks: [V] verified against other data,
[I] inferred, [?] unknown. The GPU side of the same lights is in [lighting_spec.md](lighting_spec.md) section 3, the
volumetric fields in [volumetric_fog.md](volumetric_fog.md), the baked side in [baked_lighting.md](baked_lighting.md).

## ComWorld header [V]

Asset header name hash `6ba7703dc1c9d8da` = `maps/zm/zm_escape.d3dbsp`.

| offset | field | zm_escape |
|---|---|---|
| +0x14 | primaryLightCount | 2928 |
| +0x20 | lightExploderCount | 85 |
| +0x30 | sunVolumeCount | 2 (721 and 1 probes) |
| +0x40 | probeCount | 722 |
| +0x50 | probeExploderCount | 40 |

## Primary light record, stride 600

ACTS has this struct as "todo". Offsets inside one light:

| offset | meaning | mark |
|---|---|---|
| 0x00 | 4x4 matrix (shadow / projector) | [I] |
| 0x40 | type: 4 (2791 lights, omni / spot) or 2 (137, rectangle area light) | [V by the shader's use] |
| 0x48 | origin | [V] |
| 0x54 | direction TO the light; aim = -this | [V: ceiling lights] |
| 0xa8 | colour * intensity, linear rgb (again at 0x240); 0x230 holds its largest channel | [V] |
| 0xb4 | `spec_comp`, stored as 2^spec_comp (2 -> 4, 5 -> 32, -2 -> 0.25): the specular scale | [V] |
| 0xbc | cos(fov/2); 0x238 fov outer in degrees | [V] |
| 0xc0 | `fov_feather` | [V] |
| 0xc4 | `cut_on` distance (again at 0x11c) | [V] |
| 0xc8 | `near_feather` (0.0001 when the key is absent) | [V] |
| 0xcc | radius (again 0x23c) | [V] |
| 0xd0 | `feather`, radial falloff feather (0 when absent) | [V] |
| 0xd8 / 0xdc | bulb size | [V] |
| 0xe0..0xf4 | `size_min`, `size_max` | [V] |
| 0x118 | `penumbra_inches` | [V] |
| 0x124 | shadow map level: `shadowmap_scale` 1 -> 2, 0.5 -> 3 | [V] |
| 0x148 | cookie / IES name, 20 chars; 0x250 cookie index | [V] |
| 0x190, 0x194 | `texture_tile` | [V] |
| 0x198, 0x19c | `texture_scroll_speed` | [V] |
| 0x1a8 byte 0 | volumetric on / off: 1 on 531 lights, 0 on 2397 | [I] |
| 0x1ac | `volumetric_sample_count`, u32: 7 default, also 3 / 12 / 16 / 20 / 27 | [V] |
| 0x1b0 | `volumetric_intensity_boost`, stored as 2^boost (7.25 -> 152.2, absent -> 1) | [V] |
| 0x1b8, 0x1bc | `lod_fade_range`, `lod_fade_start` | [V] |
| 0x1c0 | bounds radius; 0x1c4 bounds centre; 0x1d0 / 0x1dc bounds min / max | [I] |
| 0x1ec | 1 = cutscene set (573 lights; their exploders are the `lgtexp_xd_` shots) and the lightning | [I] |
| 0x1f0 | id = 0x30000 + index | [V] |
| 0x218 | 1 = starts off, lit by its exploder (818; never set on a light without an exploder) | [I] |

- 16 lights are also `light` entities: radius, fov, fov_feather, bulb_size and every field marked [V] above match the
  entity's key-value pairs exactly.
- Intensity = colour * about 1600 * 2^stops [V within 5%], so 0 stops gives 1.0 at 40 units with inverse square. The
  falloff window is the shader's `sat((1/(d^2+1) - c)/(1 - c))`, see the lighting spec; the older guess `(1-(d/r)^4)^2`
  is wrong.
- `u110` (4 on 1878 lights, 1 on 1050) and `flags114` (bits 0 and 16): [?]. Not related to the volumetric flag.
- No directional sun or moon light is in the list; the moon lives in the lighting states below.

## Light exploders [V]

`{u64 0, u64 name hash, i32 count, ptr}`, then per trigger 0x14 bytes `{delayOn, delayOff, fadeIn, fadeOut, u16 light,
u8 reversed}`. The name hash is fnv1a64 of the exploder name masked to 63 bits (`lgtexp_xd_sh090` -> exploder 77);
gameplay exploders are hashes only. 1033 lights belong to an exploder; `reversed` means on until it fires. Which
exploder is "power" is not readable from the zone.

## Light cookies [V]

The 46 MB grey region in GfxWorld before the vertex positions is the 33 light cookies (`GfxWorldDraw.cookieCount`):
raw rgba8, 512 wide with mips, alpha 255. Not baked light. There are no lightmaps: world vertex shaders take no second
UV and the pixel shaders write a g-buffer. The only per-vertex world colour is the reveal / tint stream.

## Lighting states [V location, I meanings]

The asset with the map's name hash (type 146, `ASSET_TYPE_LIGHTING` in ACTS) holds four 0x394-byte records, the
lighting states 1-4. Layout in [baked_lighting.md](baked_lighting.md). zm_escape values:

| field | value |
|---|---|
| sun pitch, yaw | 59, 338 (direction (0.489, -0.221, -0.857)) [V] |
| sun colour, intensity | (0.451, 0.540, 0.973) linear; 0.4204 in states 1 and 3, 3.3636 in the lightning states 2 and 4 (x8) [V] |
| skybox | `skybox_zm_escape_override`, `_override_lightning`, `skybox_zm_escape_vortex` x2 [V] |
| sun cookie | `cookie_sun_clouds` [V]; strength 0.9, scale 0.0004 uv per unit, scroll (0.008, 0.01) per second [I] |
| physically based sky | 39.37 in/m, planet 6360 km, atmosphere top 6440 km, Rayleigh 8000 m, Mie 1200 m, g 0.45 [I] |
| fog block A (+0x2a8) | -300, 1/1300, 3937 (100 m), 7; rgb 2.8e-5; 0.75; rgb 0.0014; rgb (0.143, 0.170, 0.241) with 0.3 [I] |
| fog block B (+0x33c) | 100, -450, 3500, 1050, 0, 800; rgb (0.0191, 0.0247, 0.0388) with 0.75: start, base height, half distance, half height, colour, max opacity [I] |
| exposure | +0x6c -0.5 and +0x70 0 read as EV min / max against engine defaults -32 / 31 [I]; +0x1c 2.5, +0x64 1.0, +0x78 0.9 [?] |

All four states carry the same fog. Scripts blend fog bank 1 to 2 over 3 s on hellhound rounds; which block is which
bank is [?]. Base and patched zones differ only at +0x36c (-0.5 vs 0).

So the map is moonlit: a blue sun at 0.42, 59 degrees up from yaw 338, under dark blue fog.

## Not in any zone

The worldspawn names `zm_escape/zm_escape_main_lgt8` (vbloom / vcolor) and `zm_escape_main_fxg8` (fxgrade) are source
file names only: no asset with those hashes exists in zm_escape, zm_common, zm_common_script or core_common, base or
patched. The bloom chain has no constants at all ([bloom.md](bloom.md)). The grade data in the zone is
`mtl_lut_zm_escape` and `img_trim_lut_zm_escape`.

## Patched vs base zone counts

surfaces 6137 -> 6043, model instance table 47626 -> 47552, xmodels 3242 -> 3238, meshes 16991 -> 16699, materials
7823 -> 7975, images 10027 -> 10442, lighting asset records 419 -> 428, entities 3310 -> 3362. Primary lights, light
exploders, probes and static fx: unchanged. In the patched zone an XHash is 16 bytes, so every struct holding one is 8
bytes longer per hash.
