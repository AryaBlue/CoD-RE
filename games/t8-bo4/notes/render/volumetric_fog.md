# BO4 (T8) volumetric lights and fog volumes: how much lit haze each light makes

Offline, local only. Tags: **[P]** proven from bytes / bytecode, **[I]** inferred, **[?]** unknown.

## Answer in short

BO4 does not use one density for everything. Lights that should show a beam are flagged **volumetric** per light and get their own ray-marched pass with a per-light **intensity boost** (stops) and a per-light **sample count**. The spawn dishes 142 / 77 / 161 / 92 are flagged, boost 16x (4 stops), 7 samples. The dock poles 1541-1545 are **not** flagged, so they get no beam from that pass. None of d0 / c8 / b4 / u110 / flags114 is a scatter scale.

## 1. Per-light fields (zone light record, stride 600, base zone array at 0x10c7ae0e)

Matched against the 16 `light` entities that are also primary lights (KVP value == zone value on every one) **[P]**:

| zone off | KVP | note |
|---|---|---|
| 0xb4 (`b4`) | `spec_comp` | stored as 2^spec_comp (2 -> 4, 5 -> 32, -2 -> 0.25); the specular scale, GPU light +36 |
| 0xc4 | `cut_on` | distance (again at 0x11c) |
| 0xc8 (`c8`) | `near_feather` | 0.0001 when the key is absent |
| 0xd0 (`d0`) | `feather` | 0 when absent. Radial falloff feather, **not** a fog value |
| 0xe0..0xf4 | `size_min`, `size_max` | |
| 0x118 | `penumbra_inches` | |
| 0x124 | shadow map level | `shadowmap_scale` 1 -> 2, 0.5 -> 3 |
| 0x190, 0x194 | `texture_tile` | |
| 0x198, 0x19c | `texture_scroll_speed` | |
| **0x1a8 byte 0** | volumetric on / off **[I]** | 1 on 531 lights, 0 on 2,397. Byte 1 is 1 on all |
| **0x1ac** | `volumetric_sample_count` **[P]** | u32; 7 default, also 3 / 12 / 16 / 20 / 27 |
| **0x1b0** | `volumetric_intensity_boost` **[P]** | float, stored as 2^boost: 7.25 -> 152.2185, 7.5 -> 181.0193, absent -> 1 |
| 0x1b8, 0x1bc | `lod_fade_range`, `lod_fade_start` | |

- `u110` (4 on 1,878 / 1 on 1,050) and `flags114` (bit 0, bit 16): **[?]**. No relation to the volumetric flag (cross-tab in `light_histograms.txt`).
- [I] feather / near_feather / cut_on are the likely inputs of the two CPU-built fades of the light record (d^2 fade at +216/+220, axial fade at +232/+236). Formula not recovered.
- Why 0x1a8 is read as the enable **[I]**: dishes are 1 and poles 0; flagged lights have boosts from -2 to 16 stops and colour x boost has median 2.9e5 (dishes 2.8e5), designers boost dim lights (corr(log colour, stops) = -0.47); unflagged lights mostly sit at tool defaults (0 or 7.25 stops). The 16 entities are all 0 there: consistent, proves nothing.

`lights_scatter.json` = {index: boost if flagged else 0}. `lights_volumetric.json` has flag, boost, stops, samples and the fields above.

## 2. The volumetric-light pass (shader evidence) **[P]**

core_bootstrap pixel shaders 0x1326064, 0x1404e7c, 0x142092c, 0x1424dc4 (`asm\boot_1404e7c_vollight.asm`). Reduced-resolution full-screen pass (reads 4x-scaled depth layers t6 / t7), output x exposure `cb2[110].y`.

Part A, global medium, sun + ambient: up to `cb3[87].y` steps between the fog box (`cb3[80..81]`) and the scene, fewer when the result would be dim.

Part B, loop over `cb3[121].z` records of a **192-byte structured buffer t5**:

| off | meaning |
|---|---|
| 0 | bits 0-7 **sample count N**, bit 8 shadowed, bits 9-24 shadow slice |
| 4, 16 | clip plane n, d (cone lights) |
| 20 | cone apex |
| 32 | cos^2 of the cone half angle (<= 0: no cone clip) |
| 36 | light position (camera relative) |
| 48 | radius^2 - \|pos\|^2 (sphere clip) |
| 52, 56, 60 | d2min, k, o: `atten = k / max(d2, d2min) + o` |
| 64, 76 | axis, apex pull-back |
| 80, 84 | cone scale, offset |
| 88, 92 | axial fade scale, offset |
| 96-175 | shadow matrix rows, atlas scale / offset |
| **176** | **rgb colour used for the beam** |

Per light: clip the view ray to the cone and the radius sphere, then take N equi-angular samples (`theta_j = lerp(theta_a, theta_b, (j + jitter) / N)`, `t_j = t_closest + D tan(theta_j)`, D = ray-to-light distance). Per sample X:

    dens  = min(1, exp(X.z * cb3[84].z + cb3[85].z))                 height falloff of the global medium
    spot  = smoothstep(sat(dot(normalize(L + pull * axis), axis) * s + o))      L = lightPos - X   (smoothstep here, t^2 on surfaces)
    axial = sat(dot(L, axis) * s2 + o2)^2
    atten = k / max(|L|^2, d2min) + o
    phase = cb3[81].w / (1 + cb3[81].z * dot(viewDir, normalize(L)))^2          Schlick form, same constants as the sun in part A
    step  = (1 - exp(sigT * dens * dt)) * (cb3[85].w, cb3[86].x, cb3[86].y) / dens     analytic integral over the step, dt = t_j - t_(j-1)
    beam += colour176 * (sigS * dens) * atten * spot * axial * shadow(1 tap) * phase * depthMask * step * T(view path so far)

sigS = (cb3[84].w, cb3[85].x, cb3[85].y); sigT (negative) = (cb3[83].w, cb3[84].x, cb3[84].y). Same global medium as spec section 6c. **No clamp, no normalisation by max component, no compression.** The only per-light extras are N and the separate colour.

- [I] `colour176 = light colour x 2^volumetric_intensity_boost` (CPU fill, not in the shaders, so not proven).
- [I] Only lights with 0x1a8 = 1 are put in t5.

## 3. Froxel pass (0xf49310) re-read **[P]**

- Reads the same 336-byte light record as surface lighting and the same colour (+24..32). No field is read only by the froxel path. So there is no per-light scale there.
- Has its own light clusters (uint arrays t0, t21, ranges `cb3[111] >> 5`) and loops over fog volumes (t1, 204 bytes):

      dens    = min(100 * d0, d0 * min(1, exp(-k * (z + h))))         d0 = +120, k = +124, h = +128
      sigT    = dens * (s + rgb)                                       s = +140, rgb = +148..156
      sun     = sunColour * cascadeShadow * dens * s * dz * exp(-sigT * dist) * (1 - g^2) / (4 pi (1 + g c)^2)     g = +136, clamp 0..1e4
      ambient = tex3D(t24) * dens * s * dz * exp(-sigT * dist) / (4 pi)
      local   = only if flags(+144) & 2:  colour * atten(surface formula; shadow 4 taps on the t0-cluster lights) * dens * s * dz
                * phase(g, view . L) * min(1, exp(-sigT * (distView + distLight))) * volume[+184]

- So the froxel side has one local-light scale **per fog volume** (+184), not per light.
- Other GPU fog-volume fields: +0..95 six planes, +132 start distance, +160 rgb colour, +196 max distance (pixel variant 0x1452620). `flags & 5` picks one of three near-identical sun / ambient branches.

## 4. Fog volumes in the zone **[P layout, I meanings]**

Patched zone (`zm_escape.fd.patch.dec`), GfxWorld area. Common volume header: 6 planes (vec4), 6 inverse feather distances, 1.0, u32 flags, mins (vec4), maxs (vec4), a 16-byte tool string, then a per-kind tail. Decoded to `fog_volumes.json` (cod units).

- **53 fog volumes**, 180 bytes each, at 0x1f449846. Tail = u32 index into **53 settings records of 0x90** at 0x1f44bd8a.
- Settings record: +0 name[0x28], +0x28 world fog block, +0x50 lit fog block. The unused half is uninitialised.
- 43 classic world fog, 9 lit (volumetric) fog, 1 both.
- Lit fog block, 16 floats, same layout as lighting-state fog block A: `baseHeight, heightFalloff, maxDist (3937 = 100 m), stepCount (7 / 30 / 31), sigma rgb, f7 (0.1-0.75, g?), rgb2, f11, colour rgb, f15`. Which of f7 / f11 / f15 is g, and which feeds the +184 local-light scale: **[?]**.
- Flags low nibble 1 / 2 / 4 / 8 [I] = the fog bank or lighting state the volume belongs to; scripts blend bank 1 -> 2 on dog rounds.
- **No lit fog volume covers the spawn room** (box 9430..10186, 10753..11888, 225..448 only has a default world fog volume), so local density does not explain the dish cones.
- Also: 12 volumes of 192 bytes at 0x1f4466c2 with tail (1, 0, a, b): spawn room (-1, 0), others (1.8, 1.8), (3, 3), (3.5, 3.5), (-1.5, -0.5). [I] exposure volumes (EV min, max).
- Not decoded: 41 x 176 at 0x1f446fc2; 9 x 180 at 0x1f448bf2 followed by 96 vec4; 49 + 43 x 184 at 0x1f44db5a / 0x1f456d42.
- Map scripts set no fog.

## 5. What to do in the port

- Keep the thin global medium. For lights with `lights_scatter.json` > 0, add beam in-scatter with colour x that value (dishes x16) using the section 2 formula. Unflagged lights (poles) get no beam.
- Open [?]: whether unflagged lights still get the plain 1x froxel term in the global medium (CPU-filled flag). Check the video for halos on the poles.

## Ruled out

- d0 / c8 / b4 as scatter scales (feather, near_feather, 2^spec_comp).
- A per-light scale inside the froxel in-scatter loop, and any clamp or colour normalisation in either pass.
- Local fog density raising haze in the spawn room; script-set fog.

## 6. Part A of the volumetric pass: the global medium, and world fog

[P] shader, [I] mapping to lighting-state fog block A, [?] unknown.

### Part A formula [P]

    c      = dot(V, cb3[17].xyz)
    phase  = cb3[81].w / (1 + cb3[81].z * c)^2
    len    = min(min(sceneDist, boxExit) - boxEntry, cb3[82].w)
    n      = cb3[87].y steps (fewer when the estimate x exposure is under cb8[5].z), dt = len / n, jittered start
    dens   = min(1, exp(X.z * cb3[84].z + cb3[85].z))
    src    = sigS * dens * (cb3[82].rgb * phase * shadow + amb)
    L     += src * (1 - exp(-sigT * dens * dt)) * k / dens * T * depthMask;   T *= exp(-sigT * dens * dt)

sigS = (cb3[84].w, 85.x, 85.y), -sigT = (cb3[83].w, 84.x, 84.y), k = (cb3[85].w, 86.x, 86.y), amb = (cb3[86].z, 86.w, 87.x).
shadow = cascade 2 only, 1 outside it. Thin limit: L = sigS * dens * len * (sun * phase + amb).
The only light-independent term is amb, a constant colour: no GI texture, no SH, no minimum.

### Mapping [I]

- cb3[82].w = 3937, cb3[87].y = 7, dens = min(1, exp(-(z + 300) / 1300)): 0.584 at z 400, 0.500 at z 600.
- sigS = (2.80, 3.04, 3.11)e-5; k = 1 / sigT (analytic step integral).
- cb3[82].rgb = moon colour x 0.42 = (0.190, 0.227, 0.409); cb3[81].z = +-g, .w = (1 - g^2) / 4 pi, g = f7 = 0.75:
  phase 0.557 towards the moon, 0.035 side on, 0.011 away.
- amb = block A colour (0.143, 0.170, 0.241). The local lit volumes carry the same slot as colour x 2^stops (0.0625, 2, 5.657, 45.25),
  so it is an authored radiance. Whether f15 (0.3) or 1 / 4 pi multiplies it: [?]. rgb2 (0.0014..) and f11: [?].

### Veil, green channel, ambient only

| path | z 400 | z 600 |
|---|---|---|
| 500 | 0.0015 | 0.0013 |
| 1,000 | 0.0030 | 0.0026 |
| 4,000 (capped 3,937) | 0.0119 | 0.0102 |

rgb at z 400 / 3,937: (0.0092, 0.0119, 0.0172). x 0.3 if f15 scales it (0.0036 green), x 0.08 if 1 / 4 pi does.
Moon, where unshadowed: +74 % looking at it, +5 % side on, +1.5 % away.

### World fog (block B) [P shader, I fields]

`colour = lerp(cb3[61].rgb, colour, T)` on pre-exposure HDR, in deferred and forward lit shaders. No sun, exposure or HDR scale in
the shader; a CPU prescale cannot be excluded. With start 100, half distance 3500, base -450, half height 1050, max 0.75,
colour (0.0191, 0.0247, 0.0388), green veil:

| path | z 400 | z 600 |
|---|---|---|
| 500 | 0.0011 | 0.0010 |
| 1,000 | 0.0024 | 0.0021 |
| 4,000 | 0.0088 | 0.0079 |

rgb at z 400 / 4,000: (0.0068, 0.0088, 0.0138). This alone is the size and tint of the veil asked for.
Indoors the room's world fog volume replaces block B (spawn lab: 1000, -150, 10000, 1000, colour (0.027, 0.035, 0.055)); if its
first field is the start distance there is no world fog inside 1,000 units and the lab veil is the lit-fog ambient above.
