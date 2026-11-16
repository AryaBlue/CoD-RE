# BO4 (T8) baked lighting: lighting asset, GI volumes, lighting states

Offline notes from a decompressed, patched map zone (ACTS `fastfile -d -p -H`). Asset type numbers and the ComWorld layout
come from ate47's atian-cod-tools (ACTS): `ASSET_TYPE_LIGHTING = 146`, `ASSET_TYPE_GAMEWORLD = 13`, `ComWorld`
(`probeCount`, `sunVolumeProbeCount`, `ComProbeTriggerData`). Everything else here was worked out from the bytes.
Tags: [V] verified against other data, [I] inferred, [?] unknown.

## Where it is

- A map zone has one asset of type 146. Its name hash is the map name (`maps/<mode>/<map>.d3dbsp`), like ComWorld and
  GfxWorld. It sits shortly before GfxWorld in the asset list.
- Beware: the GameWorld asset (type 13) directly follows ComWorld and also carries the map name. It holds path nodes and
  nav sample points, not light.
- In a patched zone an XHash is 16 bytes; offsets below are for the patched layout, relative to the name hash.

## Header (partial)

| offset | content |
|---|---|
| +0x248 | 4 x lighting state, 0x394 bytes each |
| +0x1098 | 4 x 0x80 sun block: 3 x vec4 basis (row 2 = sun direction), position, yaw/pitch, one pointer |
| +0x1298 | 4 x {u64 count; ptr}: per-primary-light tables |
| +0x12d8 | 4 x 0x58 probe set: {u32 probeCount; u32; ptr; ptr probes; ptr; u64; ptr; u64; ptr; u64; ptr; u32; u32} |
| +0x15a0 | 4 x 0x40 volume set: {u32 volumeCount; f32 globalScale; ptr volumes; vec3 mins; vec3 maxs; u32; u32 nodeCount; ptr; ptr} |

States 2 to 4 alias the arrays of state 1, so the baked data is shared by all lighting states [V].
A second block with engine-default values follows 0x14c0 later (ComWorld `sunVolumeCount` is 2) [I].

## Lighting state (0x394)

| offset | type | meaning |
|---|---|---|
| 0x00 | f32 x2 | sun pitch, yaw (degrees) [V] |
| 0x08 | f32 x3 | sun colour, linear [V] |
| 0x14 | f32 | sun intensity [V] |
| 0x20 | char[0x40] | skybox model [V] |
| 0x60 | u8 x2 | flags |
| 0x64, 0x68 | f32 | [?] exposure related (engine defaults 0, 0) |
| 0x6c, 0x70 | f32 | exposure EV min, max [I] (engine defaults -32, 31) |
| 0x74 | u32 | bounce count [I] (default 4) |
| 0x7c | char[0x40] | sun cookie [V] |
| 0xf8.. | f32 | physically based sky: inches per metre, planet and atmosphere radii, Rayleigh and Mie scale heights, g [I] |
| 0x170 | f32 | sun angular diameter, radians [V] |
| 0x174 | f32 | sun solid angle, steradians [V] |
| 0x17c | f32 x4 | sun disc radiance = intensity / solid angle [V] |
| 0x2a8 | | fog block A [I] |
| 0x33c | | fog block B: start, base height, half distance, half height, .., colour, max opacity [I] |

No separate exposure, bloom or tone-map asset was found; the worldspawn `vbloom` / `fxgrade` names do not exist as assets.

## Probe (0x144)

| offset | type | meaning |
|---|---|---|
| 0x00 | f32 | scale of this probe's GI volume (engine default 0.18) [V] |
| 0x04 | f32 x3 | linear RGB tint [I] |
| 0x10, 0x1c | f32 x3 | scale and offset in a 3D atlas [I] |
| 0x28 | u32 | index, type in the high word |
| 0x2c | f32 x3 | origin |
| 0x38 | f32 x9 | axes, row vectors |
| 0x5c, 0x68 | f32 x3 | extents towards -axis and +axis |
| 0x74 | f32 x3 | box centre |
| 0x80 | f32 | radius |
| 0xb4 | u32 | clip plane count (0 to 6) |
| 0xb8 | f32 x4 x6 | clip planes |
| 0x118 | u32 | per-probe value [?] |
| 0x120 | u32 | [?] possibly the cube face size |
| 0x140 | u32 | guid |

Probe 0 is the global fallback; its scale repeats in the volume-set header.

## GI volume (0x50), one per probe from probe 1

| offset | type | meaning |
|---|---|---|
| 0x00 | f32 x3 | box centre |
| 0x0c | f32 x3 | half size |
| 0x18 | f32 x3 | angles; the middle one is 360 - yaw of the probe axes |
| 0x24 | f32 | scale (= probe +0x00) |
| 0x28 | f32 | [?] |
| 0x2c | u16 x4 | nx, ny, nz (each at most 16), box count |
| 0x38 | ptr | cell data |
| 0x40 | ptr | boxes |

Stream order per volume: cell data, the box array, then each box's clip planes.

Cell data: `6 * nx * ny * nz` half floats, plane-major. Planes are +X, +Y, +Z, -X, -Y, -Z in the volume's local axes [I];
inside a plane the order is z, y, x with x fastest [V]. It is a monochrome ambient cube: each plane is the light arriving
from that side. Absolute value = stored value x scale [V: overlapping volumes agree within a few per cent only after
scaling]. The result is in the same units as the primary lights (light colour / distance^2, distance in inches) [V].

Box (0x50): centre, half size, six feather distances, .., u32 clip plane count at +0x3c, ptr at +0x40 to that many vec4.

## zm_escape: what the bake holds

Working numbers from the same read.

### Exposure fields in the lighting state

No exposure volumes and no lgt8 / fxg8 asset exist: those worldspawn names are source files, and their values are
compiled into the lighting-state record. Labelled by comparing with the engine-default record (`skybox_default_day`)
that sits 0x14c0 further on:

| offset | zm_escape | default | reading |
|---|---|---|---|
| +0x18, +0x1c | 1.0, 2.5 | 1, 1 | [?] |
| +0x64 | 1.0 | 0 | [?] EV compensation or enable |
| +0x68 | 0 | 0 | [?] |
| +0x6c | -0.5 | -32 | [I] exposure EV min |
| +0x70 | 0 | 31 | [I] exposure EV max |
| +0x74 | 4 | 4 | [I] bounce count |
| +0x78 | 0.9 | 1 | [?] (the sun cookie strength, see the sky note) |
| +0x36c | -0.5 base, 0 patched | 0 | [?] the only field the patch changed |

- All four states carry the same values. So [I] auto exposure is clamped to EV -0.5..0, almost fixed: multiplier
  2^-EV = 1.0..1.41 (or 0.83..1.18 with the photographic constant). The shader read in
  [lighting_spec.md](lighting_spec.md) section 7 later showed the centre is also held to +/-1 stop.
- Units [V]: light colour / distance_inches^2 is the irradiance the baked data is in; the moon is 0.42.
- The per-probe and global "scale" (lighting header `{u32 721; f32 0.03378; ..}`, default 0.18) is the normalisation of
  the GI data, not an exposure key [I].
- Sun block in the state [V]: +0x170 angular diameter 0.009512 rad, +0x174 solid angle 7.116e-5 sr, +0x17c four
  sun-disc radiances = intensity / solid angle (x8 in the lightning states).
- Bloom and tone-map curve: not in the zone. The LUT material and trim LUT are the only grade data.

### Baked indirect light [V unless marked]

- One GI volume per reflection probe: 721 volumes (probes 1..721; probe 0 is the global fallback and has none).
- A volume is an oriented box with a grid of at most 16 x 16 x 16 cells; 559358 cells in all.
- Per cell: six half floats, a monochrome ambient cube, stored plane-major `[+X][+Y][+Z][-X][-Y][-Z]`, each plane
  `[z][y][x]` with x fastest. Directions are in the volume's local axes [I: gradient test 0.38 / 0.36 / 0.42 on axis,
  about 0 off axis]. A plane holds the light arriving from that side.
- Absolute value = stored value x the probe's scale (probe +0x00 = volume +0x24). Proof: 76 pairs of overlapping
  volumes agree within 4% after scaling, 59% before. Units are the lights' own, colour / inches^2: a floor pool under a
  spawn ceiling spot is 17361 / 150^2 = 0.77 direct, and the baked -Z cube above it 4.3 x 0.00476 = 0.020.
- Colour: the grid is monochrome. The probe carries one linear rgb (+0x04; probe 0's is 0.62 x the moon colour) [I] as
  the tint of that probe's indirect light. The rgb's luminance is not part of the scale (tested); use
  irradiance x rgb / luminance(rgb) [guess].
- Cell positions: centre + ((i + 0.5) / n * 2 - 1) * half along the probe's axis rows (cell centres; corner against
  centre not settled [I]). The volume's angle field is 360 - yaw of those axes.
- Each volume also has one or two blend boxes (origin, half size, six feather distances, optional clip planes).
- Numbers: scale 0.0001..0.06 (median 0.0093); cell irradiance (mean of six) median 0.0055, p99 0.029, max 1.5; volume
  means from 1e-5 (sealed rooms) to 0.026.
- Sanity against unshadowed cone-aware direct light at each cell: lit cells rise with direct light (below the median
  0.0027, median to p90 0.0033, p90 to p99 0.0069, top 1% 0.0103); cells with no lamp near sit at 0.0077 outdoors,
  because sky and moon are in the bake and beat the lamp bounce. The spawn lab (250 units round 9600, 11300, 300) has
  median 0.0012, p90 0.0078, max 0.095, and its three hot spots in the -Z plane sit exactly under ceiling spots 142, 77
  and 161. Rank correlation over all cells is weak (0.12 on lit cells) because the estimate has no shadows.

### Reflection probes

722 records of 0x144 (patched 0x18dc495a): origin, axes, extents, box centre, radius, clip planes, guid, a per-probe
32-bit value at +0x118 and 64 at +0x120 [?: cube hash or face size]. No image name or xpak key was identified, so the
cubes were not extracted. After the probes: 889 x 0x25c records (count field next to the probe count) [?], probably
probe blend volumes, not decoded.

## Open

Colour of the indirect light (only one RGB per probe was found), the 0x25c-byte records after the probe array, the volume
lookup tree, reflection cube images, bloom and tone-map parameters.
