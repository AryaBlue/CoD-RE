# BO4 (T8) fastfile framing, XModels, meshes and placements (zm_escape, offline)

Read from the decompressed `zm_escape.ff.dec` and `zm_escape.xpak` only; the game never ran. All offsets are file
offsets in the decompressed base zone unless said otherwise. Struct shapes come from ACTS (`bo4_unlinker_model.cpp`)
and Greyhound (`gh_GameBlackOps4.cpp`, `gh_DBGameAssets.h`); everything below was then checked against the file itself.
Marks: [V] verified against other data, [I] inferred.

## 1. Fastfile framing

```
0x00     u64 stringCount (6868), u64 -1, u64 assetCount (43970), u64 -1    XAssetList, 0x20 bytes, not in the virtual block
0x20     stringCount x u64 (-1 / 0), then the strings
0x32a72  assetCount x 16 bytes {u8 type, 7 bytes junk, u64 header ptr}     ptr -1 = body follows in list order
```

- Pointers: 0 = null, -1 = data follows inline, -2 = inline plus an inserted alias, anything else is
  `(ref - 1) = block << 60 | offset`. Block 4 is `XFILE_BLOCK_VIRTUAL`.
- An asset reference is an alias to the asset-list slot: `ref = 0x4000000000000000 + 0x32a60 + 16 * listIndex + 1`.
  `0x32a60` is the virtual offset of slot 0's header field (the list starts 0x20 earlier in the virtual block than in
  the file). So a static-model record's "model pointer" is simply a list index.
- Types in zm_escape: 4 xmodel (3242), 5 xmodelmesh (16991), 6 material (7823, in two runs of 514 and 7309), 9 image
  (10027).
- Bodies are written in list order, and within a type the list is sorted by `name & 0x7fff...ffff`. Each body struct
  starts 8 bytes before its name hash (the first qword is zero).
- An asset the zone only refers to (it lives in a common zone) is a stub: the zeroed struct with bit 63 set in its
  name. Counts found equal the list counts exactly: xmodel 3171 real + 71 stubs, xmodelmesh 16651 + 340, material
  6517 + 1306.
- Name hashes: xmodel = `fnv1a64(name) & M63`; material = `fnv1a64("mc/" + name) & M63` (found by trial, 4425 of 7823
  named). Material +0x18 keeps the old 32-bit hash.

## 2. XModel (0x150 bytes, offsets from the name hash, i.e. struct + 8)

```
+0x00  u64 name                 +0x08  boneNames ptr          +0x10  ptr (per-bone u32)
+0x18..0x28  parent / rot / trans style ptrs                  +0x30, +0x38, +0x40, +0x48  ptrs
+0x60  physConstraints          +0x68  submodels ptr
+0x70  XModelMesh* meshes[8]    aliases, lowest detail first: meshes[numLods-1] is the full-detail LOD
+0xb0  meshMaterials ptr (-1)   +0xb8  ptr                    +0xc0  u32 numLods      +0xc4  f32 lodDist[8]
+0x104 f32 mins[3]              +0x110 f32 maxs[3]            +0x134 f32 radius
+0x140 u8 numBones, u8 numRootBones
```

- After the header: bone data, then `numLods x 0x20 {u16 numMaterials; ptr materials; ptr himipInvSqRadii; f32; f32}`,
  then per LOD the inline arrays (numMaterials aliases if `materials == -1`, numMaterials floats if `himip == -1`).
- A materials pointer that is not -1 is a block-4 offset to an array an earlier model wrote. These resolve without a
  full stream walk: 2577 of the 2776 distinct targets are "first seen in this model, and one earlier LOD of this model
  wrote an inline array of that length" (virtual to file pairs, monotone in 2577 of 2579); 180 more are the only array
  of the right length between two such anchors; 19 are the nearest of several.

## 3. XModelMesh (0x50), mesh info (0x200) and surfaces

```
XModelMesh
+0x00  u64 name        +0x08  surfs ptr (-1)     +0x10  meshinfo ptr (-1)   +0x18  ptr   +0x20  u64 xpak stream key
+0x40  f32 lod distance                          +0x44  u8 numSurfs         +0x46  u16 flags
+0x48  meshinfo: u8 status; +4 u32 verts; +8 u32 weights; +0xc u32 indices; +0x20 buffer ptr; +0x28 u32 size;
       +0x2c vertex off; +0x30 uv off; +0x34 face off; +0x38 weight off      (offsets inside the buffer)

surface (0x30)
u16 flags; u16; u16 vertCount; u16 triCount; u32 vertexBase; u32 indexBase; ...    surface k uses material k

buffer
u16 indices at faceOff; float3 positions at vertexOff; at uvOff 16 bytes per vertex:
{u8 rgba[4]; half u; half v; u32 normal (10:10:10, (x-512)/511); u32 tangent}
```

- `status` bit 0 clear (0, 8): the buffer is inline in the fastfile at +0x248 and the surfaces follow it. Bit 0 set
  (1, 9): the buffer is streamed, an xpak object keyed by +0x20, surfaces at +0x248. Bit 0x40: 24-byte vertices.
- Checked against a Greyhound rip: positions, UVs and normals of `p8_wood_beam_generic_02`,
  `p7_zm_asc_pipes_electrical_90` and `p8_zm_esc_pipe_metal_1_16` agree to 0.0, with equal vertex and triangle counts
  and material names. [V]
- Where the data is: low LODs are resident (inline in the fastfile); detailed LODs are streamed. zm_escape.xpak's index
  lists 13066 mesh objects the zone needs but stores only 646; the rest (and 28500 of 34722 images) sit in the install's
  other xpaks. The index text per key (`model: <xmodel hash>`, `name: <mesh hash>`, `size0`) agrees with this decode for
  98% of the streamed LODs, an independent check of the mesh order.
- Which install xpak stores each streamed object: all 40925 objects were found, base.xpak 26788, initial.xpak 13557,
  core_common 487, the rest in `core_*`, `mp_common` and `zm_common`. Objects are read by key straight from the CASC
  install (chunk-level reader; spans stay in table order and their content offsets are all 0).
- xpak image objects: one object holds the low mip chain (largest first), plus one single-level object per higher mip.

Not resolved in the first pass: 266 static models whose every LOD is in an xpak that had not been read, 314 with only a
resident low LOD (median 19% of the top LOD's vertices), 167 models that fail to decode (empty or short xpak objects,
one surface table that overruns), 5 xmodels whose per-LOD material structs were not located. Record bounds are tight to
the placed mesh and sometimes padded (dock posts, hanging body bags, lamps), so they do not equal the model box: the
model box equals the record box within 1 unit for 26496 of 42558 records with this mapping, and for about 1000 when
the mapping is shifted by one either way.

## 4. Placement tables [V unless marked]

- Model instance table: 47626 rows of 56 bytes at 0x1c33563d `{u32 x; u16 flags; u16 dynamic id; u32 z; u32 -1;
  xmodel ptr; ...}`, with a parallel 47626 x 68-byte array at 0x1c6755a3 `{u32 id; f32 radius; u32 0; quat xyzw;
  origin; scale; mins; maxs}`. The owning asset type is not identified (it sits before the GfxWorld static list); x and
  z are not established.
- Extra placements: instance-table rows that are not static records, plus clipmap dynents (392-byte records, quat at
  -0x20 and origin at -0x10 of the model pointer). 12206 instances in zm_escape (cell mattresses, pillows, grass,
  candles, the placed cryo chambers, 404 clipmap dynents).
- 6647 instance rows sit at the world origin with identity rotation: 133 unnamed bone models (cables, chains, pipes,
  planks; 4-7 bones), all dynamic ids 1..6645, the world box stored on the row. They are spline or bone deformed per
  instance, not group members and not entity children. Per-instance records (origin, length, 6 control vectors, 3x3 plus
  inverse) sit around 0x1ca4bf00..0x1cb76000, about 216 bytes each [I]. Drawing them needs mesh bone weights plus the
  spline pose.
- Static level fx list: 2470 x 80-byte records from 0x1d142461 `{4 x u32; 24 zero; fx ptr; origin; angles; i32; f32
  scale}`.

## 5. Composite groups and bone-posed statics [V]

- Composite groups at 0x1d773c10..0x1d922f22: 2044 records, one per static record of a model that has submodels, in
  static-record order per parent (group count equals static count for all 99 parents). Each is an xmodel-like 0x150
  header with no name, n aliases (parent, then submodels), parents, local transforms, n base mats `{quat xyzw, trans,
  2.0}`, n 4x4 matrices. Base mats share a space whose root is bone 0; a submodel's world transform is the record
  transform composed with `base[k]` relative to `base[0]`. 2301 submodels were already instance-table rows (mean error
  0.03); 1359 were not (shelf supports 548, cell doors 344, bed drawers 310, ...).
- The 1522-byte array at 0x1c5c4e95 (295 entries) is the same kind of record for bone-posed single models (stair tees
  150, hallway railing 94, ...): per-instance bone poses for skinned statics [I].

## 6. Strings, script bundles and fx assets [V]

- Zone string table: decrypts with the ACTS `decrypt_t8old` routine, the 2018-10-13 variant; 6868 strings.
- Script bundles: `{u64 name; u64 0; u64 type; u64 nObj; ptr; u64 nSub; ptr}`, objects of 0x30 `{u64; u64 key hash;
  u64; u64 asset hash; u32 key (t89 script hash); u32 string index; u32 type; u32 value}`, subs `{u32 key string index;
  u64 n; ptr}`, items recursive. 113 bodies in the zone, 100 of them scenes. Keys: name `c571857e`, type `c90c8b5c`,
  model `96700090`, anim `72ccf9d6`. Scene entities and structs name their bundle with `scriptbundlename`.
- Fx assets: header 0xa0, stubs are the zero struct with bit 63; the five list runs match the body chains exactly
  (778 / 300 / 97 / 39 / 14). No name list on disk resolves fx names; an effect's class can be told from the names of
  the materials it draws.
- Greyhound and ACTS `.wni` lists are keyed by the asset hash masked to 60 bits; they name 5873 of the 7823 zone
  materials.
- Shared texture tables [V on 585 anchors]: file offset minus virtual offset never falls along the material run and
  grows by the inline constants plus 0x138 per material; anchors are named sharers whose table is told by its images.
  Leave-one-out gives 97% right under the acceptance rule.

## Open

- The owning asset of the instance table, and its `x` / `z` fields.
- Fx asset names (hashes only).
- Material shared constant blocks: see the emissive notes under `notes/render/`.
