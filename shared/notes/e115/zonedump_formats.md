# E115 file formats

Every file and key the engine reads. The engine never opens game files (the exceptions are listed at the bottom).
`tools/zonedump` converts zones into these files, and the engine reads only these. The rules are in
E115's architecture doc and decision D4 (both unpublished).

Everything here was read in the code as of 2026-10-26. **[I]** marks anything inferred rather than read.

## Files

| file | writer | reader | needed for |
|---|---|---|---|
| `<map>.glb` world | `zonedump --world` | `src/asset/GltfLoader.cpp` | drawing a map |
| `<model>.glb` model | `zonedump --xmodel` | same | drawing a model |
| `<out>.glb` model + clips | `zonedump --xanim` | same | animated actors, `--spawn`, `--viewmodel` |
| `<stem>_<i>.dds` | `src/asset/GlbWriter.cpp` (called by every glb export) | `src/asset/Dds.cpp` via the glb | textures |
| `<map>_col.glb` collision | `zonedump --collision` | `src/physics/LoadCollision.cpp` | walking |
| `<map>.ents` | `zonedump --world` | `src/scene/MapEntities.cpp` | player start |
| `sounds.json` + `.wav`/`.flac` | `zonedump --sounds` / `--all-sounds` (`tools/zonedump/Sound.cpp`) | `src/audio/SoundAliases.cpp` | sound |
| `nav.json` pathnodes | `zonedump --nav` (`tools/zonedump/ExportNav.cpp`) | `src/nav/NavGraph.cpp` | AI routes |
| `weapons.json` weapon defs | `zonedump --weapons` (`tools/zonedump/ExportWeapons.cpp`) | not read yet | guns |
| `fx/<name>.json` + `images/*.dds` effects | `zonedump --fx` (`tools/zonedump/ExportFx.cpp`) | `src/fx/FxDef.cpp` | muzzle flashes, impacts, blood, glows |
| `impactfx.json` impact table | `zonedump --impactfx` (same file) | not read yet | which impact effect plays |
| `zbarriers.json` + `zbarrier_models/*.glb` | `zonedump --zbarriers` (`tools/zonedump/ExportZBarrier.cpp`) | not read yet | t6 window boards, the box |
| `world.script_models.json` + `script_models/*.glb` | `zonedump --world` (`tools/zonedump/ExportWorld.cpp`) | not read yet | the script_model ents and the models scripts swap them to |
| `<map>.lighting` | hand-written | `src/lighting/LightingEnvironment.cpp` | lighting overrides |
| views file | hand-written | `src/app/Options.cpp` | scripted screenshots |

`zonedump --lightgrid <out.json>`, `--clip-materials` and `--names` write diagnostics. The engine doesn't read them.

## Conventions

### Spaces and units

| data | space | units |
|---|---|---|
| glb mesh positions, node TRS under the root, probe positions, `e115_light.origin`, `e115_sun.toSun`, exposure planes | cod: right-handed, **z up** | cod units (inches) |
| the `cod_to_engine` root node (node 0 of every zonedump glb) | maps cod to engine: rotate −90° about x, `(x, y, z) → (x, z, −y)`, scale 0.0254 | — |
| engine world, camera, `--cam`/`--target`, views files, `.lighting` directions | engine: right-handed, **y up** | metres |
| `.ents` origins and angles | cod map space | cod units, degrees |
| `sounds.json` distances | cod | cod units |

- **The root space is the first mesh node's world transform.** `main.cpp` takes `rootToWorld` from the first scene entity
  that has a mesh, not from the node named `cod_to_engine`. It uses that transform to move `e115_sun`, `e115_probes`,
  `e115_node_probes`, `e115_light.origin` and `.ents` origins into the world, and it uses the inverse for the
  exposure-volume camera position. zonedump puts the world mesh at node 1 with an identity local, under
  `cod_to_engine`. So the first mesh node of a world glb must have an identity local.
- Node names the engine depends on:
  - `tag_origin`: the root-motion node of a `e115_delta` clip (`src/anim/Actor.cpp`). `--in-place` drops its channels.
  - Notetracks named `sndnt#<alias>` play `<alias>` from `sounds.json` at the actor (`main.cpp`).

### How extras are parsed

`GltfLoader.cpp` has no JSON library. It finds keys by plain substring search:

- A key is the first `"key"` in the extras string, followed by `:`. It isn't scoped to one object.
- A sub-key of an object (for example `e115_sun.exposure`) is searched from that object's start to the **end of the
  whole extras string**. An optional sub-key left out can therefore pick up a same-named key from a later object (for
  example a volume's `"exposure"` inside `e115_exposure`). **Writers must emit every sub-key**, as `GlbWriter` does.
- Booleans count only as the literal `true`/`false`. Anything else is treated as absent.
- `e115_layers` is parsed up to its first `]`, so its objects must stay flat.
- Bit fields (`e115_contents`, `e115_surface`, `e115_entity`, mask values) must be whole numbers in 0..2³²−1, or
  the load throws.

`sounds.json` is parsed with nlohmann::json. `.ents` and `.lighting` have their own line parsers.

## glb / glTF

### Standard glTF the loader uses

| item | read | notes |
|---|---|---|
| `scene` / `scenes[0].nodes` | roots | without a scene, every parentless node is a root |
| node `translation`/`rotation`/`scale` or `matrix`, `children`, `mesh`, `skin` | yes | depth-first order from the roots; node *i* of the file isn't necessarily node *i* in memory |
| material `pbrMetallicRoughness.baseColorFactor`, `.baseColorTexture` | yes | metallic/roughness ignored |
| material `alphaMode` (`OPAQUE`/`MASK`/`BLEND`), `alphaCutoff`, `doubleSided` | yes | |
| `KHR_materials_unlit` | yes | drawn unlit, never casts |
| `MSFT_texture_dds` `{"source": N}` | yes | the writer always uses it and puts it in `extensionsRequired` |
| images: `uri` relative to the glb, or `bufferView` | yes | `data:` URIs throw. `.dds` or `image/vnd-ms.dds` → DDS, otherwise stb (png/jpg/tga/bmp) |
| DDS DX10 header: DXGI format (its `_SRGB` flag decides sRGB), `TextureCube` misc flag | yes | a cube base texture makes the material a cube sky |
| skins: `joints`, `inverseBindMatrices` (MAT4), `skeleton` | yes | |
| animations: translation/rotation/scale channels, `LINEAR`/`STEP`/`CUBICSPLINE` | yes | morph weights skipped with a warning. Times must increase |
| primitives other than triangles, morph targets, `TEXCOORD_n` other than 0 on a texture view | no | warned |

### Vertex attributes

| attribute | type | meaning | written when |
|---|---|---|---|
| `POSITION` | VEC3 float | cod units under `cod_to_engine` | always (required) |
| `NORMAL` | VEC3 float | generated (area-weighted) if absent | always |
| `TEXCOORD_0` | VEC2 float | base uv | always |
| `TEXCOORD_1` | VEC2 float | lightmap uv, 0..1 | the material has `e115_lightmap` |
| `COLOR_0` | VEC3/VEC4, written as normalised u16 | **linear** rgba; rgb multiplies albedo | some vertex isn't white (zonedump keeps it only on techsets that tint with it, unless `--vertex-colour`) |
| `TEXCOORD_2`..`TEXCOORD_4` | VEC2 float | uv of layer slot 0..2 | the material has `e115_layers` |
| `_E115_LAYER_WEIGHTS` | VEC4 float | raw 0..1 blend weight per slot (x/y/z), never gamma-decoded; w unused | the material has `e115_layers`. Without it, the layer uvs are ignored |
| `JOINTS_0` / `WEIGHTS_0` | VEC4 u16 / float | 4 influences, weights sum to 1 | skinned xmodels. Must come together. Other sets are ignored |

### Material extras

| key | JSON type | units / space | default when absent | engine does | emitted by |
|---|---|---|---|---|---|
| `e115_lightmap` | number: glTF texture index | page: linear rgb / max(a, 1/255) (E115 lightmaps doc, unpublished) | not lightmapped (lit by probes or the stand-in light) | samples the page at `TEXCOORD_1` as baked indirect light | `--world`, world surfaces with a lightmap page |
| `e115_sun` | number: glTF texture index | sun visibility 0..1 in `.g`, at `TEXCOORD_1` | fully visible | baked sun shadow. **Read only when `e115_lightmap` is present** | `--world`, when the page has a sun page |
| `e115_layers` | array of `{"op": "blend"\|"multiply", "color": tex, "slot": 0..2}` | — | no layers | up to 3 layers over the base (blend: `lerp(albedo, rgb, a·w)`, multiply: `albedo *= lerp(1, rgb, w)`). An unknown `op` or an out-of-range slot drops the layer with a warning. A layer without `color` isn't drawn. Skinned and sky draws skip layers | `--world`, multi-layer world techsets |
| `e115_casts_shadow` | `false` | — | `true` | left out of the sun shadow pass | any export, when the game's material flag `0x40` (CASTS_SHADOW) is clear |
| `e115_receives_sun_shadow` | `false` | — | `true` | no dynamic sun shadow map. Baked or probe sun visibility only. The node's flag must also be true to receive | `--world`, surfaces whose primary light isn't the sun |
| `e115_blend` | `"alpha"` \| `"multiply"` \| `"add"` | — | `"alpha"` | blend equation of a `BLEND` material. Unknown values are drawn as alpha, with a warning | any export, from the drawn technique's blend state |
| `e115_sort` | whole number 0..255 | cod `MaterialInfo::sortKey` | −1 (unknown, sorts first) | blended draws go in ascending key order, scene order within a key. Out of range or non-whole → throws | any export (always when the material had a definition) |
| `e115_water` | `true` | — | `false` | parsed into `MaterialData::water`. **Not used by the renderer** (see Mismatches). zonedump sets `baseColorFactor` to the game's `waterColor` and no texture | any export, `water*` techsets |
| `e115_sky_rotation` | `[cos, sin]` | turn about cod z, `x' = x·cos − y·sin` | `[1, 0]` | turns the sky cube lookup. **Sky nodes only** | any export, from `skyBoxRotation` |
| `e115_sky_flip_z` | `true` | — | — | **not read** (see Mismatches) | any export, `skyBoxRotation.w < 0` |
| `e115_sky_hdr` | `[mode, scale]` | mode 1: linear = rgb / max(a, 1e-6) of a unorm cube. Mode 0: sRGB texture taken as is | `[0, 0]`: plain sky | scale 0 = plain. Otherwise decode by mode, then × scale. **Sky nodes only**. zonedump writes mode-1 base textures non-sRGB | any export, from `skyColorParm` (T5 `sky_cubemap_hdr`: `cloudsHeight.z`, mode 0) |
| `e115_uv_scroll` | `[u, v]` | uv per second [I] | `[0, 0]` | offset `fract(uvScroll · t)` added to uv0. **Sky nodes only** | any export, from `uvScroll` |
| `e115_contents` | whole number u32 | cod contents bits ([collision_contents.md](collision_contents.md)) | collision: `0x1` (solid) | collision: the triangles' contents. 0 = not loaded. Ignored when drawing | `--collision` |
| `e115_surface` | whole number u32 | cod surface flags | 0 | parsed into `surfaceFlags`. **Not used** | `--collision` (always written with `e115_contents`) |

### Node extras

| key | JSON type | units / space | default | engine does | emitted by |
|---|---|---|---|---|---|
| `e115_light` | `{"origin": [x, y, z], "probe": n}`, either sub-key optional | origin: root (cod) space | origin: the mesh bounds centre. probe: −1 | origin: where the probe field is sampled for this node. probe: index into `e115_node_probes`, used instead of the field. Out of range → throws | `--world`, static models (`lightingOrigin`; BO2 own light sample) |
| `e115_casts_shadow` | `false` | — | `true` | the node's meshes stay out of the sun shadow pass | `--world`, skybox. Static models only with `--smodel-cast-bits` |
| `e115_receives_sun_shadow` | `false` | — | `true` | as on materials. Both flags must be true | `--world`, static models that aren't sun-primary, skybox |
| `e115_sky` | `true` | — | `false` | skybox: drawn first, centred on the camera, unlit, behind everything. Left out of the scene bounds and probe lighting. Enables the sky material keys | `--world`, the skybox xmodel |
| `e115_brushmodel` | string `"*N"` | — | `""` | parsed. **Not used** | `--world`, brush-model nodes |
| `e115_targetname` | string | — | `""` | parsed. **Not used** (the node's `name` is also the targetname when there is one) | `--world`, brush-model nodes with a targetname, script_model nodes |
| `e115_classname` | string | — | `""` | not read yet | `--world`, script_model nodes (`"script_model"`) |
| `e115_noteworthy` | string | — | `""` | not read yet | `--world`, script_model nodes with a `script_noteworthy` |
| `e115_trigger` | `true` | — | `false` | collision: the node and its whole subtree are skipped (never solid) | `--collision`, the `triggers` group and each trigger node |
| `e115_entity` | whole number ≤ INT32_MAX | index of the entity block in the map's entity string (`.ents` order) [I: same string] | −1 | parsed. **Not used** (brush models don't move yet) | `--collision`, brush-model nodes; `--world`, script_model nodes |
| `e115_hitboxes` | array of `{"min": [x,y,z], "max": [x,y,z], "offset": [x,y,z], "r2": n, "loc": string, "skin": n}` | the bone node's own space, cod units (x along the bone) | none | `NodeData::hitBoxes`, traced by `physics/HitTest` (below). A missing sub-key → throws. Unknown `loc` → warning, taken as `none` | `--xmodel`, `--xanim`: every bone of a skinned model |

#### `e115_hitboxes`

One entry per model that has the bone. In a merged `--xanim` glb a shared bone (for example `j_head` on the body and on
the attached head) carries one entry per model.

| sub-key | from | meaning |
|---|---|---|
| `min`, `max` | `XBoneInfo::bounds[0]`, `[1]` | the box corners in bone space |
| `offset` | `XBoneInfo::offset` | the box centre. It equals (min + max) / 2 on every Nacht zombie bone |
| `r2` | `XBoneInfo::radiusSquared` | the reject sphere, \|half extent\|². Bones with no box have 0. t4 skips `r2` < 4 |
| `loc` | `XModel::partClassification[bone]` | hit location name, as OAT names them: `none`, `helmet`, `head`, `neck`, `torso_upper`, `torso_mid` (t6 only), `torso_lower`, `right_arm_upper`, `left_arm_upper`, `right_arm_lower`, `left_arm_lower`, `right_hand`, `left_hand`, `right_leg_upper`, `left_leg_upper`, `right_leg_lower`, `left_leg_lower`, `right_foot`, `left_foot`, `gun`, `shield` (t6 only) |
| `skin` | — | index of the glb skin (one per merged model) the box came from, so one model's boxes can be switched off (`BoneTraceOptions::hiddenSkins`) |

t4 and t5 `hitLocation_t` have no `torso_mid`, so zonedump adds 1 to raw values from `torso_lower` up before naming
them. t6's enum matches the list above. The box is tested in the node's world space, so the node matrix (with
`cod_to_engine`'s 0.0254 scale) puts it in metres. See [t4_hits_damage.md](../../../games/t4-waw/notes/e115/t4_hits_damage.md) §1.

### Animation extras

`GlbWriter` writes all five on every animation.

| key | JSON type | units | default | engine does | emitted by |
|---|---|---|---|---|---|
| `e115_frame_rate` | number | frames per second | 30 | parsed. **Not used at run time** (key times are already seconds) | `--xanim` (`framerate`, else 30) |
| `e115_looped` | bool | — | `false` | looped clips wrap. Others hold the last frame and report finished | `--xanim` (`bLoop`) |
| `e115_delta` | bool | — | `false` | carries root motion: the `tag_origin` translation channel moves the actor (and its collision capsule), unless `--in-place` | `--xanim` (has a delta part) |
| `e115_additive` | bool | — | `false` | channels are offsets on another pose. Playing one alone logs a warning | `--xanim` (cod `assetType == 6`) |
| `e115_notetracks` | array of `{"name": string, "time": number}` | seconds from clip start | none | reported when crossed (wraps fire the tail, then the head). Not an array, or a note without `name`/`time` → throws | `--xanim` (normalised time × length) |

### Root extras

| key | JSON type | space | default | engine does | emitted by |
|---|---|---|---|---|---|
| `e115_sun` | object, below | root (cod) | no sun | becomes `LightingEnvironment.sun` and the baked settings (`importLighting`) | `--world`, when the gfxworld has a sun light |
| `e115_probes` | probe set, below | root (cod) | none | the irradiance field for things without lightmaps | `--world`, from the light grid |
| `e115_node_probes` | probe set, below | root (cod) | none | per-node light, indexed by `e115_light.probe` | `--world`, BO2 static models with their own sample |
| `e115_collision` | `{"game": string, "masks": {name: u32}}` | — | no masks | masks go to `CollisionMesh::setMask`. `game` is ignored | `--collision` |
| `e115_exposure` | object, below | cod | none | BO1-style auto exposure from the camera position | `--world`, T5 only |

`e115_sun`:

| sub-key | type | default | meaning |
|---|---|---|---|
| `color` | `[r, g, b]` | required (a missing one → warning, no sun) | linear sun radiance before exposure |
| `toSun` | `[x, y, z]` | required | direction to the sun. Normalised, `(0, 0, 1)` if zero |
| `exposure` | number | 1 | scales baked indirect light (`baked.indirect_scale`) and the sun (√ in perceptual sum). Divides the auto exposure |
| `gammaCombine` | bool | `false` | `true` → `baked.sum = perceptual`: `light = (√indirect + sun)²` |

Probe sets (`e115_probes`, `e115_node_probes`): all four sub-keys are required (missing → throws). The three values are
accessor indices into the glb's `accessors`, and a wrong size throws.

| sub-key | accessor | meaning |
|---|---|---|
| `count` | — (a number) | probes, *n* |
| `position` | VEC3 float × *n* | root (cod) space |
| `terms` | SCALAR float × 30*n* | per probe 10 rgb terms `K, Bx, By, Bz, Qxx, Qyy, Qzz, Qxy, Qxz, Qyz`. Linear `E(n) = K + B·n + nᵀQn` in baked units, multiplies albedo. zonedump converts from the SH9 basis (`IrradianceProbe::fromSh9`) |
| `sunVisibility` | SCALAR float × *n* | 0..1 (BO2 stored. WaW/BO1: 1 where the sun is the primary light, else 0) |

`e115_collision.masks`:

| mask | value written | engine use |
|---|---|---|
| `player` | `0x2818011`, T4 non-`mp_` zones `0x281C011` | trace mask of the player and spawned-actor capsules and the spawn raycast. Absent → `0x2818011` (`kAssumedPlayerMask`) |
| `player_dead` | `0x810011` | available via `CollisionMesh::mask`, not used |
| `pathnode` | t4 only: `0x820011` (t4sp `0x559470`, a contributor) | `NavGraph::dropToFloor`. Absent → callers use `player` |

`e115_exposure`:

| sub-key | type | units | meaning |
|---|---|---|---|
| `default` | number > 0, required | exposure / 8 | target outside every volume |
| `volumes` | array (optional, must be an array) | — | first volume containing the camera wins |
| `volumes[].planes` | `[[nx, ny, nz, w], ...]`, required | cod space, facing in | inside when `dot(n, p) + w ≥ 0` for all |
| `volumes[].exposure` | number, required | / 8 | volume target |
| `volumes[].featherRange` | number, required | per cod unit of depth | target = `exposure + featherAdjust · min(featherRange · depth, 1)`, depth capped at 50 |
| `volumes[].featherAdjust` | number, required | / 8 | |
| `volumes[].rateUp`, `rateDown` | number, required (clamped ≥ 1) | 1/rate per 60 Hz frame | smoothing towards the target. Outside volumes: 15 and 20 |

Every frame, baked indirect light and the sun are scaled by `current / e115_sun.exposure` (√ in perceptual sum).

### Layout of zonedump glbs

| export | nodes |
|---|---|
| `--world` | 0 `cod_to_engine`. 1 world mesh (identity, name = gfxworld name). Brush models `*N` (name = targetname or `*N`, placed at their entity). One node per static-model placement (name = xmodel). Skybox (`e115_sky`) |
| `--xmodel` | 0 `cod_to_engine`. 1 mesh (`skin: 0` when skinned). Bone *i* = node 2 + *i* |
| `--xanim` | as `--xmodel` for the first model. Later models share bones by name, and new bones go under `@tag`. One skin per model |

World materials are split per (game material, lightmap page, sun-primary). Texture files are `<glb stem>_<i>.dds` beside
the glb, and each image `name` is the game image name. Lightmap pages are `lightmap<i>` / `lightmap<i>_sun`.

## Collision glb

`loadCollisionMesh` loads it through `loadGltf`, so all the glb rules above apply. It uses only:

| item | use |
|---|---|
| node transforms, including `cod_to_engine` | triangles go to engine world space (metres) |
| triangle primitives | indexed or not. A count that isn't a multiple of 3 throws |
| material `e115_contents` | the triangles' contents. No material or no key → `0x1`. `0` → skipped |
| node `e115_trigger` | the node and everything under it is skipped |
| root `e115_collision.masks` | named masks |

Writer layout (`zonedump --collision`): node 0 `cod_to_engine`, a `world` node (terrain + world brushes), one node per
brush model named `*N <classname>` at its entity's placement with `e115_entity`, and trigger brush models under a
`triggers` node. One primitive per (contents, surface) pair. Each pair has its own material named
`contents 0x… surface 0x…`, double-sided, with a hashed colour for viewers. Triangles are unwelded with flat normals.
Contents 0 is dropped at export. Bits are listed in [collision_contents.md](collision_contents.md).

## `.ents` map entities

Read from the model path with its extension replaced by `.ents`, if that file exists. zonedump writes the zone's
`map_ents` string unchanged.

- Syntax: a sequence of `{ "key" "value" ... }` blocks. Whitespace is space, tab, CR, LF and NUL. Strings have no
  escapes and may span lines. Anything else throws `AssetError` with the line number.
- Keys can repeat. The first one wins.

Keys the engine reads (`findPlayerStart`):

| key | format | use |
|---|---|---|
| `classname` | string | picks the start |
| `targetname` | string | `initial_spawn_points` on a `script_struct` (zombies) |
| `origin` | `"x y z"`, cod units | start position. An entity without a valid origin is skipped |
| `angles` | `"pitch yaw roll"`, degrees | yaw (the 2nd value) about cod z, from +x. Default 0 |

Start order: `script_struct` with targetname `initial_spawn_points`, then `mp_tdm_spawn_allies_start`, then any
`mp_*_spawn`, then `info_player_start`, then `info_player_deathmatch`. The eye is 1.6 m above the origin in engine y.
No start → automatic framing.

## `sounds.json`

Written to `<dir>/sounds.json` with the audio files beside it. Loaded with `--sounds <file>`.
See [audio.md](audio.md) for the meaning of each field.

### Read by the engine

The variant keys down to `secondary` are **required**: `at()` throws `AssetError` when one is missing. The playback-rule
keys after them are optional, with the defaults shown, so exports from before them still load.

| key | type | units | engine does |
|---|---|---|---|
| `game` | string, optional | — | provenance only, never read |
| `distanceScale` | number, **required** | — | provenance: the factor the export already applied (T6 2, else 1). Distances are effective. A file without it is refused (older exports held stored T6 distances) |
| `curves` | `{name: [[x, y], ...]}`, required | x 0..1 ascending (else throws), y gain | piecewise linear, ends held |
| `banks[]` | array, required | — | |
| `banks[].aliases[].name` | string | — | the alias name. The same name in two banks: the first loaded wins [I: like zone load order] |
| `...variants[].file` | string, relative to the json's folder, or `null` | — | decoded on first play (miniaudio: `.wav`, `.flac`). `null` = silent variant |
| `volMin`, `volMax` | number | linear gain | rolled uniformly per play |
| `pitchMin`, `pitchMax` | number | ratio | rolled uniformly per play |
| `distMin`, `distMax` | number | cod units, effective | falloff: `dryMin` curve over 0..distMin, `dryMax` curve over distMin..distMax, clamped |
| `curves.dryMin`, `curves.dryMax` | string | a name in `curves` (an unknown name throws) | |
| `looping` | bool | — | voice loops |
| `panType` | string | — | `"2d"` → not spatialised. Anything else is 3D |
| `probability` | number | 0..1, 0 = always | chance the picked variant plays at all |
| `secondary` | string or `null` | — | alias started along with this one (not itself) |
| `limitType`, `entityLimitType` | `"none"`, `"oldest"`, `"reject"`, `"priority"` (else throws) | default `"none"` | what a play does once `limitCount` voices of the alias name are going, over all voices / on its entity |
| `limitCount`, `entityLimitCount` | whole number | default 0 | |
| `neverPlayTwice` | bool | default false | the variant plays once, then its picks fail (no reroll) |
| `voiceLimit` | bool | default false | starting it stops the entity's other `voiceLimit` voices |
| `stopOnEntDeath` | bool | default false | stopped (with its fade) when its entity dies |
| `randomize` | `{"volume", "pitch", "variant": bool}` | default all false | volume/pitch rolls kept 30 s per (alias, entity); variant from one LCG step on hash(name) + entity |
| `priority` | `[min, max]` | /255, default `[0, 0]` | lerped by closeness for `"priority"` limits, which need 3/255 more to steal a voice |
| `priorityThreshold` | `[lo, hi]` | closeness 0..1, default `[0, 0]` | the lerp is min at or below lo, max at or above hi, the middle when lo = hi |
| `priorityDistance` | number | cod units, effective, default 0 | closeness = 1 − d / this, 0 for 2D. T6's `distMin`×2 case for flagged curves isn't applied (its table is a runtime global) |
| `startDelay`, `fadeIn`, `fadeOut` | number | ms, default 0 | silent wait before it starts; ramp up from silence; ramp down when it's stopped (0 = cut) |

The variant pick is uniform over the first 64. With more than two variants, it rerolls away from the last one
(`SoundSystem.cpp`). The rules run in the games' order: pick, neverPlayTwice, probability, priority, alias limit,
entity limit, voiceLimit, start ([audio.md](audio.md), Playback rules).

### Written but not read

| where | keys |
|---|---|
| top level | `unexported`: `[{"name", "variant", "file" \| null, "format" \| null, "reason"}]`, one per variant whose audio wasn't written |
| alias | `id`, `sequence` |
| variant, all games | `format`, `channels`, `rate`, `frames` (only when `file` isn't null), `distReverbMax`, `curves.wetMin`, `curves.wetMax`, `startDelay`, `reverbSend`, `centerSend`, `limitCount`, `entityLimitCount` |
| variant, T6 | `bank`, `entry`, `bus`, `volumeGroup`, `loadType`, `randomize`, `fadeIn`, `fadeOut`, `pan`, `limitType`, `entityLimitType`, `isMusic`, `isBig`, `distanceLpf`, `doppler` |
| variant, T5 | `source`, `flags` |
| variant, T4 | `source`, `flags`, `chain`, `limitType`, `entityLimitType`, `randomize` |

Values: T5 and T6 volumes are stored /65535, pitches /32767, probabilities /255. T4 floats are written as stored.
T5/T4 `looping` and `panType` come from `flags` bits 0 and 1 (T4 [I], unmeasured).

`Sound.cpp` was being edited by another session while this page was written (T4 export, effective distances), so
check the per-game rows against it.

## `nav.json` pathnodes

The gameworld's compiled pathnode graph (`GameWorldSp`/`GameWorldMp` `PathData`), written by `zonedump --nav <out.json>` for
t4, t5 and t6. Loaded with `NavGraph::load`, which moves origins into engine space with the `cod_to_engine` change and
scales radii and costs by 0.0254. Parsed with nlohmann::json. A missing key or a link to a node that doesn't exist
throws `AssetError`.

```json
{"game":"t4","nodes":[
{"origin":[268,-255,34],"angle":0,"type":"negotiation_begin","spawnflags":0,"radius":0,"targetname":"traverse",
 "target":"pf75_auto2108","script_noteworthy":"","script_linkname":"","animscript":"wall_hop","links":[[72,15,1]]}
]}
```

| key | format | meaning |
|---|---|---|
| `origin` | `[x, y, z]`, cod units, cod space | where the node was placed. Nacht's sit up to 63 units above the floor [M]. T4 drops every node at load, and `NavGraph::dropToFloor` does the same: a 30×30×30 box swept from 1 unit above down 256 lands it on the floor, then a 30×30×72 standing box there must be clear, both against world geometry only (movers never count). A node in solid or with no floor in reach is disabled ([zombies_t4_nacht.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht.md)) |
| `angle` | degrees | yaw about cod z |
| `type` | string | the game's `nodeType` lowercased without `NODE_`: `pathnode`, `negotiation_begin`, `negotiation_end`, `cover_stand`, ... Each game's enum is mapped by the writer |
| `spawnflags`, `radius` | number, cod units | as the game has them |
| `targetname`, `target`, `script_noteworthy`, `script_linkname`, `animscript` | string, `""` when unset | the node's script strings. A negotiation begin's `animscript` names its traversal (`wall_hop` for Nacht's windows) |
| `links` | `[[to, cost, negotiation], ...]` | outgoing links: target node index, cost in cod units, and 1 for a traversal link. Links can be one way (negotiation links are) |

Every key is written for every node. Link costs are the straight-line distance, except negotiation links, which cost
less than their length (15 for Nacht's 70-unit window hops) [M]. `NavGraph::path` scales its heuristic by the cheapest
cost per metre of any link, so A* stays optimal.

## `weapons.json` weapon defs

Every weapon def in one zone, written by `zonedump --weapons <out.json>` for t4, t5 and t6. OAT's weapon dumpers make
each def's `WEAPONFILE` info string, and the writer parses it. Nothing reads the file yet.

```json
{"game":"t4","weapons":[
{"name":"thompson","gameplay":{"displayName":"WEAPON_THOMPSON","type":"bullet","fireType":"full_auto",
 "damage":{"max":120,"min":80,"maxRange":800,"minRange":1800,"melee":150,"locations":{"head":4}},
 "ammo":{"clip":20,"max":200,"start":200},"times":{"reload":2.1},"models":{"view":"viewmodel_usa_thompson_smg"}},
 "fields":{"displayName":"WEAPON_THOMPSON","AIOverlayDescription":"WEAPON_SUBMACHINEGUNNER"}}
]}
```

`gameplay` uses the same keys and units for every game. The engine should read only this block:

| key | meaning |
|---|---|
| `displayName` | localised string reference |
| `type`, `class`, `fireType`, `inventory`, `penetrate` | the game's enum names, lowercased with `_` for spaces: `bullet`/`projectile`/`grenade`, `full_auto`/`single_shot`/`2_round_burst`, `primary`/`offhand`/`altmode`, ... |
| `rifleBullet`, `ammo.unlimited` | bool |
| `damage.max`, `.min` | damage per bullet up to `maxRange` and from `minRange` (cod units). It is interpolated in between |
| `damage.melee` | melee damage |
| `damage.locations` | hit location to multiplier: `head`, `helmet`, `neck`, `torsoUpper`, `gun`, ... (the `loc*` keys) |
| `times.*` | seconds: `fire`, `fireDelay`, `rechamber`, `melee`, `reload`, `reloadEmpty`, `reloadAdd`/`reloadStart`/`reloadEnd` (shell-by-shell), `raise`, `firstRaise`, `drop`, `quickRaise`, `quickDrop`, `emptyRaise`, `emptyDrop`, `adsIn`, `adsOut`, `sprintIn`, `sprintOut` |
| `ammo.clip`, `.max`, `.start` | rounds. A t5/t6 weapon with `ammoCountClipRelative` stores max and start as magazines, so the writer multiplies them by `clip` (BO2 M1911 8 × 10 = 80, M14 8 × 12 = 96). A weapon without it (ray gun 160, Mustang and Sally 50) is already in rounds [M] |
| `ammo.name`, `.clipName`, `.sharedCap` | weapons with the same `name` share reserve ammo |
| `spread.*` | degrees: `hipStandMin`, `hipDuckedMin`, `hipProneMin`, `hipMax`, `hipDuckedMax`, `hipProneMax`, `hipDecayRate`, `hipFireAdd`, `hipMoveAdd`, `hipTurnAdd`, `ads` |
| `adsZoomFov` | degrees. t4's `adsZoomFov`, and `adsZoomFov1` (the iron sights) for t5/t6 |
| `moveSpeedScale` | player speed multiplier while holding it |
| `explosion.*` | `radius`, `radiusMin` (cod units), `innerDamage`, `outerDamage` |
| `projectile.speed`, `.model` | cod units per second, xmodel name |
| `models.view`, `.world`, `.hands` | xmodel names for `--xmodel` |
| `attach.hideTags` | bones whose parts the gun model hides, with everything under them (`--hide-tags`). t5 makes one def per attachment combination over the same `gunModel` (`ak47_mp`, `ak47_acog_mp`), so each def lists the parts it doesn't carry. t6 uses it for the base gun (`scar_mp`: `tag_sights_off`) [M] |
| `attach.parts` | t6: models always bolted on (`an94_mp`'s magazine), `{model, tag, offset, rotation}`. Offsets are cod units and pitch/yaw/roll degrees. An empty tag is the gun's root [I] |
| `attach.attachments`, `.uniques` | t6: the attachment names it takes, and the `attachmentUniques` entries for each one and each pair (`au_an94_acog`, `au_an94_acog+gl`) |
| `altWeapon` | the def the alt fire switches to (`m1garand_gl`) |
| `sounds` | every non-empty `*Sound`/`*SoundPlayer` key to its alias name (`sounds.json`) |
| `anims` | every non-empty `*Anim` key to its xanim name |

A missing number is 0 and a missing string is `""`. `fields` keeps every raw key as a string in the order the game
writes them, for anything `gameplay` doesn't cover yet. Field names differ between games there.

On t6 a top-level `attachmentUniques` array holds `{name, attach, fields}`. `attach` contains `type`, `hideTags` (base gun
parts the attachment replaces: `au_an94_acog` hides `tag_sights_front`, `tag_sights`), `view` and `world` (`model`,
`additional`, `ads`, `tag`, `offset`, `rotation`, `addOffset`, `addRotation`), `disableBaseAttachment` and
`disableBaseClip`. mp_hydro plus common_mp has 502 of them, 387 with hide tags [M].

### Weapon viewmodels (`<exportRoot>/<game>/weapons/<weapon>.glb`)

The game's arms (t4: `viewmodel_usa_marine_arms`) and the weapon's `gunModel` go into one `--xanim` glb. List the
arms first, then the gun as `<gunModel>@tag_weapon`. The gun shares no bones with the arms, so without `@tag_weapon` its
root `j_gun` lands at the view origin, muzzle at the camera. Clips and models are found in every loaded zone. The first
zone resolves the materials, so give the map's zone first and `--load` the rest. The clip names are the weapon's
`anims` (above). t4 Nacht, as exported:

```
Z=<pluto_t4>/zone/english
e115_zonedump $Z/nazi_zombie_prototype.ff --load $Z/common.ff --game <pluto_t4> --xanim \
  viewmodel_colt45_idle,viewmodel_colt45_idle_empty,viewmodel_colt45_fire,viewmodel_colt45_lastshot,viewmodel_colt45_reload_notempty,viewmodel_colt45_reload,viewmodel_colt45_pullout,viewmodel_colt45_putaway \
  viewmodel_usa_marine_arms,viewmodel_usa_colt45_pistol@tag_weapon <exportRoot>/t4/weapons/zombie_colt.glb
e115_zonedump $Z/nazi_zombie_prototype.ff --load $Z/common.ff --game <pluto_t4> --xanim \
  viewmodel_kar98_idle,viewmodel_kar98_fire,viewmodel_kar98_lastshot,viewmodel_kar98_rechamber,viewmodel_kar98_reload,viewmodel_kar98_pullout,viewmodel_kar98_first_raise,viewmodel_kar98_putaway \
  viewmodel_usa_marine_arms,viewmodel_ger_kar98_rifle@tag_weapon <exportRoot>/t4/weapons/kar98.glb
```

t4 has no viewmodel sprint clips: `sprintInAnim`/`sprintLoopAnim`/`sprintOutAnim` are empty. Sprint is the offset, turn
and bob in `fields` (`sprintOfsF/R/U`, `sprintRotP/Y/R`, `sprintBobH/V`, `sprintInTime`/`LoopTime`/`OutTime`).

Attachments (`weapons.json` `attach`):
- `--hide-tags <tag,...>` drops the triangles on those bones and on everything under them.
- On t6, `--xanim` always adds the base parts of the first weapon variant that draws the gun model, so the AN-94 gets
  its magazine.
- `--attach au_<...>[,...]` adds each attachment unique's view model, and its `additional` model at the `add` offset.
  It skips the ADS-only model.
- Each part sits at its tag plus its offset and rotation. An empty tag means the gun's first bone (`j_gun`).
  - The AN-94 magazine offset matches `tag_clip1` [M].
  - The silencer is placed relative to `j_barrel`, with the offset of `tag_flash` [M].
- The hidden tags are the union of `--hide-tags`, the variant's own and the uniques'.
- `disableBaseWeaponClip` leaves off base slot 7, the magazine on every mp gun [M], and `disableBaseWeaponAttachment`
  leaves off the other slots [I].
- An `--attach` name missing from the zones is an error.

## Effects: `fx/<name>.json`

`zonedump <zone.ff> [--load <zone.ff>]... --game <install> --fx <name[,name]|*> <dir>` writes each t4 `FxEffectDef`
to `<dir>/fx/<name>.json`, for example `<dir>/fx/weapon/muzzleflashes/pistolflash.json`. Every effect it chains to
(runners, `effectOnDeath`, `effectOnImpact`, `effectEmitted`) is written too. Each sprite material's colour map goes to
`<dir>/images/<image>.dds`, converted the same way as the model export's (`ImageSource` and `writeDds`). Effects and
materials are found in every loaded zone, and a later zone wins. t5 zones export too, with `"game":"t5"`, T5's own type
names (`spriteRotated`, `line`; no `sparkCloud`) and the extra elem keys in [fx_t5_layout.md](../../../games/t5-bo1/notes/e115/fx_t5_layout.md). t6 zones export the same way, with `"game":"t6"`,
`msecNonLoopingLife`, `boundingBoxCentre` and `occlusionQuery` on the effect and `spotLight` / `{lightDef}` on spot lights
([fx_t6_layout.md](../../../games/t6-bo2/notes/e115/fx_t6_layout.md)). Nacht, as exported to
`<exportRoot>/t4/fx` (305 effects, 135 images):

```
Z=<pluto_t4>/zone/english
e115_zonedump $Z/nazi_zombie_prototype.ff --load $Z/common.ff --game <pluto_t4> --fx '*' <exportRoot>/t4/fx
e115_zonedump $Z/nazi_zombie_prototype.ff --load $Z/common.ff --impactfx <exportRoot>/t4/fx/impactfx.json
```

The file keeps the asset's units: cod inches, milliseconds and cod axes. `src/fx/FxDef.cpp` converts them on load.

```json
{"format":"e115_fx","version":1,"game":"t4","name":"weapon/muzzleflashes/pistolflash","flags":0,"msecLoopingLife":0,
 "efPriority":0,"elemCounts":{"looping":0,"oneShot":5,"emission":0},
 "elems":[{"class":"oneShot","type":"spriteBillboard","typeId":0,"flags":134,
   "flagNames":["spawnRelativeToEffect","spawnFrustumCull"],"spawnOffset":"none","runRelativeTo":"effect",
   "spawn":{"count":[1,0]},"spawnDelayMsec":[1,0],"lifeSpanMsec":[100,0],"...":"...",
   "velSamples":[{"local":{"velocity":{"base":[0,0,0],"amplitude":[0,0,0]},"totalDelta":{"...":"..."}},"world":{"...":"..."}}],
   "visSamples":[{"base":{"colour":[174,174,174,255],"rotationDelta":0.0039,"rotationTotal":0,"size":[0.13,0.13],"scale":0},
                  "amplitude":{"...":"..."}}],
   "visuals":[{"material":"gfx_fxt_fire_flame_clump"}],"effectOnDeath":"","trail":null,"sortOrder":6}],
 "materials":{"gfx_fxt_fire_flame_clump":{"techset":"effect_zfeather_add_nofog","blend":"add","blendRaw":[2,2,1],
   "alphaCutoff":0,"sortKey":48,"atlas":[2,2],"image":"images/fxt_fire_flame_clump.dds"}},
 "skipped":{"effect.totalSize":1}}
```

Top level:

| key | meaning |
|---|---|
| `msecLoopingLife` | how long the looping elems keep spawning after the effect starts. 2147483647 = until stopped |
| `elemCounts` | elems are stored looping first, then one-shot, then emission. Each elem's `class` says which |
| `materials` | every material the elems use, by name (see below) |
| `skipped` | every asset field the file leaves out, with a count. `effect.totalSize` is the runtime's storage size. `elem.flags 0x...` would count unnamed flag bits (none in Nacht + common). `elem.unused` counts non-zero padding |
| `warnings` | only when there are any: a material or image that wasn't loaded |

Per elem. Ranges are `[base, amplitude]`, and the value is base + random(0..1) × amplitude:

| key | meaning |
|---|---|
| `type` | `spriteBillboard`, `spriteOriented`, `tail`, `trail`, `cloud`, `sparkCloud`, `model`, `omniLight`, `spotLight`, `sound`, `decal`, `runner`. `typeId` is the raw enum |
| `flags`, `flagNames` | raw `FxElemDef::flags`, with the bits named by cod4's layout [I]: `spawnRelativeToEffect` 0x2, `spawnFrustumCull` 0x4, `runnerUsesRandRot` 0x8, `useCollision` 0x100, `dieOnTouch` 0x200, `drawPastFog` 0x400, `drawWithViewmodel` 0x800, `blockSight` 0x1000, `hasVelocityGraphLocal` 0x1000000, `hasVelocityGraphWorld` 0x2000000, `hasGravity` 0x4000000, `useModelPhysics` 0x8000000, `nonUniformScale` 0x10000000, `disableFountainCollision` 0x80000000 |
| `spawnOffset` | bits 0x30: `none`, `sphere`, `cylinder` |
| `runRelativeTo` | bits 0xc0: `world`, `spawn`, `effect` (follows the effect as it moves), `offset` |
| `spawn` | looping: `{intervalMsec, count}`, one spawn per interval up to `count` (2147483647 = no limit). One-shot: `{count: range}`, a whole number from base to base + amplitude |
| `spawnDelayMsec`, `lifeSpanMsec` | int ranges, ms |
| `spawnOrigin` | 3 ranges, inches, along the effect's x (forward), y (left) and z (up) |
| `spawnOffsetRadius`, `spawnOffsetHeight` | inches |
| `spawnAngles`, `angularVelocity`, `initialRotation` | radians, radians per ms, radians |
| `gravity` | times world gravity (800 in/s² [I]), used with `hasGravity` |
| `atlas` | `behavior` bits 0-1 are the start frame (0 fixed at `index`, 1 random, 2 by spawn order), 4 plays over the life, 8 stops after `loopCount` loops [I]. `fps` is frames per second. The grid is 2^`colIndexBits` × 2^`rowIndexBits`, with `entryCount` frames |
| `velSamples` | `velIntervalCount` + 1 keys spread evenly over the life. `local` is in the elem's axes and `world` in cod world axes. `velocity` is inches per ms. `totalDelta` is its running integral in key-interval units (key k is the sum of the trapezoids before it), so multiply by life / intervals to get inches |
| `visSamples` | `visStateIntervalCount` + 1 keys over the life. `colour` is r g b a bytes. The asset stores a d3dcolor (b g r a), and the writer swaps it [I: the muzzle-flash lights come out orange this way]. For colours, `amplitude` is a second colour picked between. For everything else it's a delta. `size` is the sprite's half width and height in inches [I], width only unless `nonUniformScale`. `rotationDelta` is radians per ms, and `rotationTotal` is its integral, like `totalDelta`. `scale` is for model elems |
| `visuals` | one entry per visual. `{material}` for sprites, tails, trails and clouds. `{model}` (an xmodel, `--xmodel`), `{effect}` (runners), `{sound}` (an alias), `{}` (lights) or `{decal: [model material, world material]}` |
| `effectOnImpact`, `effectOnDeath`, `effectEmitted` | effect names, `""` = none. `emitDist` and `emitDistVariance` are inches between emitted effects |
| `trail` | null, or `{scrollTimeMsec, repeatDist, splitDist, verts: [{pos, normal, texCoord}], inds}` for trail elems |
| `spawnRange` | inches from the viewer to the effect where the elem spawns: base..base+amplitude, amplitude 0 = any distance [V: `BlackOps.exe` 0x7b6c70, under `fx_cull_elem_spawn`; it compares squared distances]. Distance lods: bo1's muzzle flashes carry far tiers at 1000-5000 that only spawn far away |
| `collMins`, `collMaxs`, `fadeInRange`, `fadeOutRange`, `spawnFrustumCullRadius`, `reflectionFactor`, `windInfluence`, `sortOrder`, `lightingFrac`, `useItemClip` | as the asset stores them. The engine ignores them for now |

Per material:

| key | meaning |
|---|---|
| `blend` | `alpha`, `add`, `multiply`, `mask` or `opaque`, read from the state bits as in the model export (`MaterialState.cpp`). `blendRaw` is `[src, dst, op]` (`GFXS_BLEND_*`). An `add` with src 5 (src alpha) multiplies rgb by alpha |
| `image` | the colour map's dds, relative to `<dir>`, or null |
| `atlas` | the material's own `[columns, rows]` (`textureAtlasColumnCount`/`RowCount`) |
| `techset`, `sortKey`, `alphaCutoff`, `note` | for reference |

### `impactfx.json`

`--impactfx <out.json>` writes the zone's `impactfx` asset (the one in `common.ff` has no name). It has 16 rows in t4 and 21 in
t5 and t6 (`fximpacttable` in `common_zombie.ff` / `common_zm.ff`, adding `bullet_xtreme_*`, `rocket_explode_xtreme`,
`bolt`, `blade`). t6 has a 32nd surface column, `riotshield`. Each
row has 31 surface columns and 4 flesh columns, and each cell holds an effect name or null.

```json
{"format":"e115_impactfx","version":1,"game":"t4","asset":"","names":"...","rows":[
 {"index":0,"name":"bullet_small_normal","nonflesh":{"default":"impacts/default_hit","bark":"...","concrete":"impacts/small_concrete_1"},
  "flesh":{"flesh_body_nonfatal":"impacts/flesh_hit_body_nonfatal","flesh_body_fatal":"...","flesh_head_nonfatal":"...","flesh_head_fatal":"..."}}]}
```

- **Rows:** `bullet_small_normal`, `_exit`, `_underwater`, `bullet_large_normal`, `_exit`, `shotgun_normal`, `_exit`,
  `bullet_ap_normal`, `_exit`, `grenade_bounce`, `grenade_explode`, `rocket_explode`, `projectile_dud`, `mortar_shell`,
  `tank_shell`, `physics_impact`. That's the 16-name table at `t4sp.exe` file `0x43f1e0`, which the 4 flesh names follow.
  The contents agree with it: row 1 holds the `*_exit` flesh effects, row 2 the underwater ones, and rows 13 and 14 the
  mortar and tank effects.
- **Columns:** the surface type, which is `surfaceFlags >> 20` (the infoParm table at `0x4d46a8`): `default`, `bark`,
  `brick`, `carpet`, `cloth`, `concrete`, `dirt`, `flesh`, `foliage`, `glass`, `grass`, `gravel`, `ice`, `metal`,
  `mud`, `paper`, `plaster`, `rock`, `sand`, `snow`, `water`, `wood`, `asphalt`, `ceramic`, `plastic`, `rubber`,
  `cushion`, `fruit`, `paintedmetal`, `player`, `tallgrass`.
- [I] The names come from those tables. That the loader indexes the rows and columns by them wasn't read in code.
- [I] A weapon's `impactType` (`bullet_small`) plus `_normal`, or `_exit` where the bullet leaves a body, picks the row.

## `world.script_models.json`

`--world` puts every `script_model` ent (`model` not `*N`) in `world.glb` as a node: named after its xmodel, at its `origin` /
`angles` / `modelscale`, a child of the root like the static models. The extras are `e115_classname`, `e115_targetname`,
`e115_noteworthy` and `e115_entity`. Each xmodel's mesh is converted once and shared with the static models. The nodes come
after the skybox, so a map's older nodes, meshes, materials and textures keep their indices.

Models a script may `setmodel` to go to `script_models/<name>.glb` beside the glb, by the `--xmodel` path. A model goes there
when some loaded zone defines it and a placed model maps to it as `<m>_on`, `<m>_off` -> `_on`, or `<m>_on` -> `_off`.

```json
{"format":"e115_script_models","version":1,
 "placed":[{"entity":2288,"classname":"script_model","model":"zombie_vending_jugg","targetname":"vending_jugg","noteworthy":"","node":2380}],
 "swaps":[{"from":"zombie_vending_jugg","to":"zombie_vending_jugg_on","glb":"script_models/zombie_vending_jugg_on.glb"}],
 "spawned":[{"model":"zombie_vending_revive","glb":"script_models/zombie_vending_revive.glb"}]}
```

BO2 perk machines are `script_struct`s that the script spawns ([zombies_t6_struct_spawns.md](../../../games/t6-bo2/notes/e115/zombies_t6_struct_spawns.md)). The converter
passes the T6 `PerkRules` spawn fields to the world job:
- `--perk-structs zm_perk_machine --perk-names <specialty>=<targetname>,...`: each struct with that targetname that the
  `--mode` filter keeps, and that has a `model`, becomes a node like a script_model. Its `e115_classname` is
  `script_struct`, and its `e115_targetname` is the machine name the script gives it (`vending_jugg`, …), empty if the
  specialty isn't in the table. `placed[].classname` says which kind each entry is.
- `--extra-models <name>,...`: models the map's script spawns itself (`perks.spawnedModels`, Nuketown's five). They go to
  `script_models/` and are listed in `spawned`; their `_on` swaps are found as for placed models.

- `node` is the node index in `world.glb`, or null when the model failed (named in the warnings: `tag_origin`, and t4's
  `dest_window_*` destructibles, which no zone defines).
- [M] `--load common.ff`, 2026-10-27:
  - nacht: 54 placed; every older node, mesh, material and side file is unchanged.
  - verrückt: 72 placed, 44 missing; the 4 vending machines and the dbldoor halves are placed; 6 swaps.
  - kino (`--load common_zombie.ff`): 96 placed, 12 `tag_origin` missing; 9 swaps (4 perks, pap, chandeliers, lights).
  - zm_nuked: 168 placed, no swaps. T6 perk machines are spawned by script, not ents.
- [I] Swaps outside the name rules (other `setmodel` targets) aren't found.
- [M] 2026-10-27, a contributor's build:
  - zm_transit `--mode zclassic_transit`: 7 perk structs placed (Speed Cola, Stamin-Up, Jugg, Double Tap, Revive, PaP,
    Tombstone), each with its `_on` in `script_models/`
  - zm_nuked: no perk nodes; the 5 spawned models and their 5 `_on`s

## `zbarriers.json` (t6)

`--zbarriers <out.json>` writes every `zbarrier` asset in the zone and its `--load` zones; the main zone wins a clash. Each
piece's board, alternate and upgraded model goes to `<json dir>/zbarrier_models/<name>.glb` by the `--xmodel` path. The
layout and the map ents that use the assets are in [zbarrier_t6.md](../../../games/t6-bo2/notes/e115/zbarrier_t6.md). A t4/t5 zone is refused.

```json
{"format":"e115_zbarriers","version":1,"game":"t6","modelDir":"zbarrier_models","missingModels":[],"barriers":[
 {"name":"zmcore_basicwoodbarrier","zone":"zm_transit","attackSlots":3,"attackSlotOffset":28.0,"autoHideOpenPieces":false,
  "taunts":true,"tauntState":"zm_taunt","reachThroughAttacks":true,"reachThroughState":"zm_window_melee",
  "repairSounds":["@fe43acaa","@41b37cd3"],"upgradedRepairSounds":["@8fe763d4","@41b37cd3"],"repairSoundDelay":0.3,
  "earthquake":{"scale":[0.3,0.4],"duration":[0.2,0.4],"radius":150.0},
  "pieces":[{"index":1,"model":"p6_anim_zm_barricade_board_01","alternateModel":null,"upgradedModel":"p6_anim_zm_barricade_board_01_upgrade",
   "tearAnim":"o_zombie_board_1_pull","boardAnim":"o_zombie_board_1_repair","zombieTearState":"zm_zbarrier_board_tear",
   "zombieTearSubState":"horz_1","upgradedRepsToTear":3,"repairFx":[{"fx":"impacts/fx_large_woodhit","offset":[0.0,38.0,0.0]}],
   "repairSound":"@cf350162","repairHoverSound":"@791d41ff","pauseAndRepeatRepairSound":true,"repairSoundPause":[0.3,0.6]}]}]}
```

- Units are cod inches. Sounds are alias hashes (`@` + 8 hex digits), or null when unset.
- `pieces` has `numBoardsInBarrier` entries, at most 6, with `index` from 1, as in the ent keys `zbarrierboardmodel<N>`.
- `tearAnim` and `boardAnim` are the piece model's own xanims. `zombieTearState`/`SubState` pick the zombie's.
- `missingModels` lists models no loaded zone defines. Those aren't an error; a failed conversion is.
- [M] zm_transit: 5 assets and 25 models, none missing. All 38 `exterior_goal` windows resolve to an asset whose pieces
  match the ent's board keys and have their glbs. zm_nuked: only `zmcore_magicbox`.

### Engine units (`src/fx`)

The loader converts inches to metres (× 0.0254) and ms to seconds. Colour bytes become linear: rgb is squared and alpha
divided by 255 [I]. Effect-local axes stay cod's. The caller's `fx::Frame` gives the engine-space directions of the
effect's x (forward), y (left) and z (up). World-axis vectors map cod (x, y, z) to engine (x, z, -y).

## `vehicles.json` (t6)

`--vehicles <out.json>` writes every `vehicle` asset (VehicleDef) defined in the zone. The convert job runs it on every
t6 map, from the map zone alone. `content::loadVehicleDefs` reads the file. A t4/t5 zone is refused.

```json
{"game":"t6","units":"inches per second","vehicles":{
 "biplane_zm":{"type":"plane","maxSpeed":2640.0,"accel":528.0,"maxSpeedVertical":1144.0,"accelVertical":1056.0,
  "rotRate":60.0,"rotAccel":100.0,"isDrivable":false,"worldModel":"veh_t6_dlc_zm_biplane"}}}
```

- The keys are the vehicletype names: ent `vehicletype`, or the third `spawnvehicle` arg.
- Speeds and accels are inches/s and inches/s², as the engine stores them. OAT's dumps show mph, which is these ÷ 17.6.
- `maxSpeed` / `accel` are what a path vehicle drives at when script hasn't set a speed ([t6_vehicles.md](../../../games/t6-bo2/notes/e115/t6_vehicles.md)) [V]:
  the target is maxSpeed, it speeds up at accel and slows at 0.5 × accel.
- `rotRate` / `rotAccel` are as stored (OAT dumps them unscaled). Their units are [U].
- `type` uses OAT's class names: "4 wheel", "motorcycle", "tank", "plane", "boat", "artillery", "helicopter".
- [M] zm_tomb has 4 defs (tank_mark_iv_zm, biplane_zm, heli_quadrotor_zm, heli_quadrotor_upgraded_zm). zm_nuked has 1
  (defaultvehicle), zm_transit 1 (zombie_bus) and mp_nuketown_2020 0.

## `.lighting` overrides

Path: `--lighting <file>`, else `<exe>/../../../data/maps/<model stem>.lighting` if it exists. Applied after the glb
import, so the file wins. See E115's lighting doc (unpublished).

- Syntax: one `key = value` per line. `#` starts a comment. An unknown key or a bad value throws, naming the line.
- Space: engine world (metres, **y up**), linear radiance. Flags take `1/0`, `true/false` or `on/off`. Vectors are
  three numbers separated by spaces. Directions must be non-zero and are normalised.

| key | value | default |
|---|---|---|
| `sun.enabled` | flag | `false`. Imported `e115_sun` → `true` |
| `sun.to_light` | direction | `0 1 0`. Imported: `toSun` in world space |
| `sun.radiance` | vec3 | `0 0 0`. Imported: `color × exposure` (√exposure in perceptual sum) |
| `ambient.sky` | vec3 | `0.32 0.36 0.42` |
| `ambient.ground` | vec3 | `0.16 0.14 0.12` |
| `fallback_key.enabled` | flag | `true` |
| `fallback_key.to_light` | direction | `normalise(0.3, 1, 0.25)` |
| `fallback_key.radiance` | vec3 | `2.2 2.1 1.9` |
| `probes.enabled` | flag | `true` |
| `sun_shadow.enabled` | flag | `true` |
| `sun_shadow.cascades` | whole 1..4 | 2 |
| `sun_shadow.near_extent` | > 0, metres across the first cascade | 6.5024 |
| `sun_shadow.split_scale` | > 0 | 4 |
| `sun_shadow.blend` | 0 ≤ b < 1 | 0.25 |
| `baked.indirect` | flag | `true` |
| `baked.sun_shadow` | flag | `true` |
| `baked.indirect_scale` | number | 1. Imported: `e115_sun.exposure` |
| `baked.sum` | `linear` \| `perceptual` | `linear`. Imported `gammaCombine` → `perceptual` |
| `camera.exposure_ev` | number, image × 2^ev | 0 |
| `camera.tonemap` | `clamp` \| `aces` | `clamp` |

With `e115_exposure`, the frame loop rescales `baked.indirect_scale` and `sun.radiance` every frame, starting from
the values after the overrides.

## Other app inputs

From `src/app/Options.cpp`, `Assets.cpp` and `main.cpp`:

| input | format | notes |
|---|---|---|
| positional model | `.gltf`/`.glb` | anything else is shown as a texture preview. Default: Sponza from `assets/local/glTF-Sample-Assets` |
| | `.dds`, `.png`/`.jpg`/`.jpeg`/`.tga`/`.bmp` | preview |
| | `.iwi` | preview, decoded by `src/cod/Iwi.cpp` (a game file: see exceptions) |
| `--collision <glb>` | collision glb | |
| `--sounds <json>` | `sounds.json` | |
| `--lighting <file>` | `.lighting` | |
| `--spawn <glb>` (repeatable), `--viewmodel <glb>` | glb with clips | `--viewmodel` nodes never cast shadows |
| `--views <file>` | lines of `name cx cy cz tx ty tz` (engine metres), `#` comments | needs `--screenshot <dir>` |
| `--anim <name>` | an animation `name` in the glb | |
| `--fx <json> [x y z]`, `--fx-age <s>` | an effect from `zonedump --fx` (its export root is the folder above `fx/`) | looped at x y z (engine metres) or 1 m ahead of the camera. `--fx-age` replays it each frame and holds it that many seconds in, for repeatable screenshots |
| `<exe>/shaders/*.spv` | SPIR-V from `shaders/*.hlsl` | build output, not content |

## Mismatches

Places where the writer emits something the reader ignores, or the reader expects something the writer doesn't
provide. None of them were fixed.

| # | key / file | issue |
|---|---|---|
| 1 | material `e115_sky_flip_z` | Written by `GlbWriter` (zonedump sets it when `skyBoxRotation.w < 0`). `GltfLoader` never reads it, so `MaterialData::skyFlipZ` is always false after a load and the renderer has no input for it. Skies that the game mirrors in z draw unmirrored |
| 2 | material `e115_water` | Read, but nothing in `src/render` or the shaders uses `water`. Water draws as a plain material in `waterColor` |
| 3 | material `e115_surface` | Read into `surfaceFlags`. Nothing uses it |
| 4 | node `e115_brushmodel`, `e115_targetname` | Read. Nothing uses them |
| 5 | node `e115_entity` | Written only on collision nodes. Read, not used. The world glb's brush-model nodes carry no entity index, so a world brush model and its collision node can only be matched by `*N` / targetname |
| 6 | animation `e115_frame_rate` | Always written. Read, not used at run time |
| 7 | root `e115_collision.game` | Written. The reader ignores it (intended under D4) |
| 8 | `e115_collision.masks.player_dead` | Written. The app never queries it |
| 9 | material `e115_uv_scroll`, `e115_sky_rotation`, `e115_sky_hdr` | Written for any material with those constants. The renderer applies them only on `e115_sky` nodes, so `uvScroll` on non-sky materials is ignored |
| 10 | material `e115_sort` | `ModelData.h` documents 0..63. The reader accepts 0..255. The writer emits the raw byte |
| 11 | `sounds.json` distances | **Fixed** (d7791ba, 8a69dd6 on): the export writes effective distances plus `distanceScale`, and the reader has no game branch |
| 12 | `sounds.json` curves | Without `snddriver_globals` loaded, T4/T5 aliases name curves `"@<index>"`, and T6 writes `curves: {}`. Every referenced curve must exist, so such an export fails to load. T4 also leaves out empty-named curves that an alias can still reference [I] |
| 13 | `sounds.json` `format` | T6 writes `format` = `pcm16`/`flac`. T4/T5 write `format: "pcm16"` plus the original codec in `source`. The reader ignores both |
| 14 | `sounds.json` `unexported` and the rest of the "Written but not read" table | Ignored by the reader. Variants with `file: null` play silently |
| 15 | `.ents` | The comment in `zonedump/main.cpp` names the reader as `src/world/EntityString`. It's `src/scene/MapEntities` |
| 16 | root space | The engine takes the root space from the first mesh node, not from `cod_to_engine` (see Conventions). It matches every zonedump glb today, but no writer or reader checks it |

## Adding a game

1. **The exporter writes effective values.** Per-game quirks (unit scales, exposure /8, distance ×2, packed flags,
   mask values) belong in the zonedump profile for that game. The engine implements each behaviour once and reads the
   difference as a field. If no field can describe a behaviour, add a field here with a default that keeps old files
   working. Never add a game branch in `src/`.
2. **Write every sub-key** of an object you emit (see "How extras are parsed").
3. Outputs:

| output | required? | minimum content |
|---|---|---|
| world glb | required for maps | `cod_to_engine` at node 0, the world mesh as the first mesh node with an identity local, POSITION + indices. Everything else is optional |
| model glb | required for models | same root. Skinned: `JOINTS_0`/`WEIGHTS_0`, `skin`, joint nodes |
| clips | optional | glTF animations. `e115_looped`, `e115_delta` (with a `tag_origin` node), `e115_notetracks` matter. The rest have safe defaults |
| `.ents` | required for a player start | `classname` + `origin` (+ `angles`) on one of the start classnames, or extend `findPlayerStart` |
| collision glb | required for walking | triangles. `e115_contents` per material and `e115_collision.masks.player` (without it, the BO1 fallback mask is used). Triggers marked `e115_trigger` |
| `sounds.json` | optional | `curves`, `banks[].aliases[].variants[]` with all 13 read keys, distances effective (once exception 1 is gone) |
| lighting | optional | `e115_sun`, `e115_probes`, lightmaps, `e115_exposure`. Absent → the stand-in hemisphere + key light |

4. Optional keys degrade to the defaults in the tables above. Required sub-keys throw `AssetError`.

### Known exceptions

From grepping `src/` for t4/t5/t6 and game-specific behaviour:

| where | what |
|---|---|
| `src/app/Assets.h` `kAssumedPlayerMask` (`0x2818011`, BO1's) | fallback for collision files without `e115_collision.masks.player`. Kept only for old exports |
| `src/cod/Iwi.cpp`, `IwiWavelet.cpp` | the app reads game `.iwi` images directly (texture preview only) |
| `src/script/` (`T6Bytecode`, `T6Disasm`, `Vm`) | reads T6 compiled GSC directly. In `e115_script`, which the tests and `e115_script` tool link, not the `e115` app |
| `src/scene/MapEntities.cpp` `findPlayerStart` | cod classnames (`initial_spawn_points`, `mp_*_spawn`, `info_player_*`), with no game id |
| `src/anim/Actor.cpp`, `src/app/Puppet.cpp` | the cod bone name `tag_origin` is the root-motion node |
