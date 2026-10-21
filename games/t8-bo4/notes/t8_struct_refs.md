# BO4 / T8 (zm_escape) Structure References

Research deliverable for the offline BO4 GfxWorld + collision extractor. Goal: adapt a
known/published layout rather than reverse from zero.

**Scope of confidence tags**
- **RIPPER-VERIFIED** — taken directly from the source of a tool that provably rips BO4
  assets (Greyhound/Wraith). Layout is proven because the tool produces correct output.
- **UNLINKER-SOURCE** — taken from ate47/atian-cod-tools (ACTS), an offline BO4 fastfile
  unlinker. These are on-disk/in-zone layouts with `static_assert` size checks, but many
  fields are still `unkXX` (partially reversed).
- **LINEAGE** — from a closely related title (BO3/T7) on the CoD research wiki; BO4 is the
  same engine family, so the shape is a strong starting point but must be re-verified.
- **COMMUNITY-GUESS / GAP** — no authoritative source; flagged as needing raw-byte RE.

**Primary repos mined (read-only, nothing cloned/run):**
- Scobalula/Greyhound @ commit `22c3d17` — proven BO4 model/image/anim ripper (reads live process memory).
- ate47/atian-cod-tools (ACTS) @ commit `7906279` — offline BO4 `.ff`/`.xpak` unlinker.
- Scobalula/Husky @ commit `ce1f82d` — CoD BSP/GfxWorld→OBJ extractor (lineage only; **stops at Vanguard/MW2019, NO BO4**).
- codresearch.dev (COD Engine Research wiki) — struct wiki (has BO1/BO2/BO3, **no BO4 pages**).

---

## KEY ORIENTING FACT — how BO4 stores map collision vs AI nav (read this first)

From the ACTS BO4 asset-type enum (UNLINKER-SOURCE, `src/core/shared/games/bo4/pool.hpp`,
`enum XAssetType : byte`), BO4 keeps **three separate things** our converter conflates:

| Asset | enum id | What it is | Open-source extractor? |
|---|---|---|---|
| `ASSET_TYPE_CLIPMAP` | **11** | **World / bullet collision** — Treyarch's own `clipMap_t` (brushes, planes, tris, BSP). NOT Havok. | **No** (ACTS marks `col_map` unimplemented) |
| `ASSET_TYPE_NAVMESH` | **96** | AI pathing navmesh — the `hkaiNavMesh` Havok data seen in the zone. | **No** |
| `ASSET_TYPE_NAVVOLUME` | **97** | AI nav volume (flight/3D nav) — Havok. | **No** |
| `ASSET_TYPE_PHYSPRESET` / `ASSET_TYPE_PHYSCONSTRAINTS` | 0 / 1 | Rigid-body physics (ragdoll/props) — Havok (`hknp`/`hkp`). | **No** |
| `ASSET_TYPE_GFXWORLD` | **14** | Render geometry. | Partial (ACTS: metadata only) |
| `ASSET_TYPE_GAMEWORLD` | 13 | Gameplay entity world. | No |
| `ASSET_TYPE_COMWORLD` | 12 | Lights/probes/exploders (NOT collision). | Yes (ACTS, metadata) |
| `ASSET_TYPE_XMODEL` / `ASSET_TYPE_XMODELMESH` | 4 / 5 | Models + streamed mesh. | **Yes (Greyhound)** |

**Implication for the port:** the `hkai*` Havok data the teammate found is the **AI navmesh
(96/97)**, which is a Havok format with no community extractor. But the **world/bullet
collision is still a Treyarch `clipMap_t` (asset 11)** — brush/plane/tri, the same family our
T6 converter expects — it just has not been reversed by any open tool yet. So collision is
*conceptually* convertible (not pure Havok), but the BO4 `clipMap_t` layout must be
reversed by hand (BO3's layout below is the best starting template). Havok is only
unavoidable for AI nav + rigid-body physics, which a map port can regenerate or omit.

---

## 1. BO4/T8 XModel — surface + streamed vertex/index layout  ⭐ MOST ACTIONABLE

**Source:** Scobalula/Greyhound @ `22c3d17`
- Structs: `src/WraithXCOD/WraithXCOD/DBGameAssets.h` (`BO4XModel`, `BO4XModelLod`, `BO4XModelSurface`, `BO4XModelMeshInfo`)
  https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/DBGameAssets.h
- Read logic: `src/WraithXCOD/WraithXCOD/GameBlackOps4.cpp` (`ReadXModel` ~L1114, `LoadXModel` ~L1443, stream structs ~L551)
  https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/GameBlackOps4.cpp

**Confidence: RIPPER-VERIFIED.** Greyhound produces correct BO4 models from this exact code.
Caveat: Greyhound reads from the *live process*, so pointer fields are runtime VAs. The
**mesh buffer byte layout** (positions/UV/normal/weights/faces below) is the same bytes that
live in the `.xpak`-streamed mesh blob, so it is directly usable offline. Fixed-size header
structs (`BO4XModelSurface` etc.) are runtime layouts — field *order* is reliable, but the
`Padding[...]` gaps are in-memory and may differ from the on-disk/zone struct; cross-check
against ACTS `bo4_unlinker_model.cpp` when parsing the zone image rather than live memory.

### 1a. Model → LOD → Surface chain

```c
// BO4XModel (relevant fields; in-memory). #pragma pack(1)
uint64_t NamePtr;
uint64_t BoneIDsPtr;            // +0x10
uint64_t ParentListPtr;        // +0x20
uint64_t RotationsPtr;         // +0x28  (quat)
uint64_t TranslationsPtr;      // +0x30  (vec3)
uint64_t BaseMatriciesPtr;     // +0x40
uint8_t  Padding[0x28];
uint64_t ModelLodPtrs[8];      // up to 8 LODs
uint64_t MaterialHandlesPtr;   // array of material ptrs, 1 per surface
uint32_t NumLods;
uint8_t  Padding3[0x78];
uint16_t NumCosmeticBones;
uint8_t  Padding4[0x5];
uint8_t  NumBones;
uint8_t  NumRootBones;
uint16_t NumUnknown;

struct BO4XModelLod {          // #pragma pack(1)
    uint64_t UnknownZero;
    uint64_t NameHash;
    uint64_t XSurfacePtr;      // -> array of BO4XModelSurface
    uint64_t XModelMeshPtr;    // -> BO4XModelMeshInfo(Ex) (stream info)
    uint64_t UnknownPtr;
    uint64_t LODStreamKey;     // xpak cache key for the mesh blob (see §2)
    uint8_t  Padding[0x18];
    float    LodDistance;
    uint8_t  NumSurfs;
    uint8_t  SurfacesIndex;
    uint16_t UnknownFlags;
};

struct BO4XModelSurface {      // one per submesh; #pragma pack(1)
    uint8_t  Flag1, Flag2, Flag3, Flag4;  // Flag1 & 2 => "complex"/4-bone weights
    uint16_t VertexCount;
    uint16_t FacesCount;
    uint32_t VerticiesIndex;   // base vertex index into the LOD-wide buffers
    uint32_t FacesIndex;       // base face index into the LOD-wide face buffer
    uint8_t  Padding[0x20];
};
```
Material per surface: read `MaterialHandlesPtr[surfaceIndex]` (pointer stride 8; Greyhound
advances `+8` then reads a `uint64_t` handle per surface). 1 material per submesh.

### 1b. Streamed mesh blob — the on-disk/xpak byte layout (THE important bit)

`BO4XModelMeshInfoEx` (the stream descriptor at `XModelMeshPtr`) gives offsets *within* the
mesh blob and the blob's size/key. The blob itself is either already in memory (StatusFlag &
0x3F == 8) or must be pulled from the `.xpak` cache via `LODStreamKey` (§2).

```c
struct BO4XModelMeshInfoEx {   // #pragma pack(1)
    uint8_t  StatusFlag;       // &0x3F==8 => resident; &64 => HasExtendedVertexInfo
    uint8_t  Flag2, Flag3, Flag4;
    uint32_t VertexCount;
    uint32_t WeightCount;
    uint32_t FacesCount;
    uint8_t  Padding[0x10];
    uint64_t XModelMeshBufferPtr;
    uint32_t XModelMeshBufferSize;
    uint32_t VertexOffset;     // byte offset of position array in blob
    uint32_t UVOffset;         // byte offset of GfxStreamVertex array
    uint32_t FacesOffset;      // byte offset of index array
    uint32_t WeightsOffset;    // byte offset of weight array
    uint32_t BlendShapesOffset;
    uint8_t  Pad[416];
    uint32_t BlendShapeCount;
    uint32_t UnknownPossibleValueOrPad;
    uint64_t BlendShapeNames;
    uint64_t BlendShapeIndexes;
};
```

**Per-vertex data, read with these strides (verbatim from `LoadXModel`):**

- **Position** — at `VertexOffset + (surface.VerticiesIndex * 12)`. Each vertex = **3× float32
  (12 bytes)**, read straight into a `Vector3`. NOTE: full floats, *not* packed/quantised —
  directly usable. (Greyhound: `MeshReader.Read<Vector3>()`.)

- **UV + normal + tangent + colour** — at `UVOffset + (VerticiesIndex * stride)`, where
  **stride = 16 bytes normally, 24 bytes if `HasExtendedVertexInfo` (StatusFlag & 64)**. The
  struct for the first 16 bytes:
  ```c
  struct GfxStreamVertex {     // 16 bytes
      uint8_t  Color[4];       // RGBA vertex colour
      uint16_t UVUPosition;    // half-float U
      uint16_t UVVPosition;    // half-float V
      int32_t  VertexNormal;   // packed 10/10/10
      int32_t  VertexTangent;  // packed 10/10/10 (same scheme; Greyhound ignores it)
  };
  ```
  **Normal unpack** (per component, for Normal and Tangent):
  ```
  packedX = ((n >>  0) & 0x3FF) - 512
  packedY = ((n >> 10) & 0x3FF) - 512
  packedZ = ((n >> 20) & 0x3FF) - 512
  normal.{x,y,z} = packed{X,Y,Z} / 511.0
  ```
  If extended (24-byte stride): the extra 8 bytes follow and are skipped by Greyhound
  (comment: "first 4 bytes seems to be UV, possibly better camo UV mapping").

- **Weights** — at `WeightsOffset + (VerticiesIndex * 12)`. Only present when
  `surface.Flag1 & 2`. Struct (12 bytes):
  ```c
  struct GfxStreamWeight {
      uint8_t  WeightVal1..4;  // byte weights, /255.0
      uint16_t WeightID1..4;   // bone indices
  };
  ```
  If `Flag1 & 2` is unset: single rigid weight (bone 0, weight 1.0).

- **Faces/indices** — at `FacesOffset + (surface.FacesIndex * 2)`. Each face = **3× uint16**
  (16-bit index width), CCW triangle:
  ```c
  struct GfxStreamFace { uint16_t Index1, Index2, Index3; };
  ```

- **Blend shapes** (optional, if `BlendShapeCount != 0`): delta table at `BlendShapesOffset`;
  `Bo4GfxBlendShapeVert` = `{uint16 FlagsAndShapeIndex; uint16 X,Y,Z; uint16 Unk0..3}` with
  `shapeIndex = FlagsAndShapeIndex >> 8` and XYZ delta as half-floats. Not needed for a map port.

**Takeaway for the extractor:** XModel geometry is trivially parseable offline — positions are
plain float3, indices are u16 triples, surfaces give `(firstVertex=VerticiesIndex,
vertexCount, baseIndex=FacesIndex, triCount=FacesCount/3)`. This is the single highest-value
finding and the thing the ripper most firmly proves.

---

## 2. BO4/T8 `.xpak` container (stream package)  ⭐ ACTIONABLE

**Source:** Scobalula/Greyhound @ `22c3d17`
- Header structs: `src/WraithXCOD/WraithXCOD/DBGameFiles.h` (`BO3XPakHeader`, `BO3XPakHashEntry`, `BO3XPakDataHeader`) — shared BO3/BO4.
  https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/DBGameFiles.h
- Parse/decompress: `XPAKCache.cpp` (`LoadPackage`, `ExtractPackageObject`, `DecompressPackageObject`) and `XPAKSupport.cpp` (`ParseXPAK`).
  https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/XPAKCache.cpp
- Cross-ref: ACTS `src/core/acts/tools/fastfile/fastfile_xpak.cpp`.

**Confidence: RIPPER-VERIFIED** (Greyhound extracts BO4 images + streamed model meshes from
`.xpak` using this). BO4 is **Version 0xB (11)**; BO3 = 0xA, MW2019 = 0xD.

### Header (`BO3XPakHeader`, used for BO4 v0xB; `#pragma pack(1)`)
```c
uint32_t Magic;        // 0x4950414B  == "KAPI" (little-endian "IPAK")
uint16_t Unknown1;
uint16_t Version;      // 0xB for BO4
uint64_t Unknown2;
uint64_t Size;
uint64_t FileCount;
uint64_t DataOffset;   // base of the data section
uint64_t DataSize;
uint64_t HashCount;    // number of BO3XPakHashEntry
uint64_t HashOffset;
uint64_t HashSize;
uint64_t Unknown3;
uint64_t UnknownOffset;
uint64_t Unknown4;
uint64_t IndexCount;   // number of key/property index records
uint64_t IndexOffset;
uint64_t IndexSize;
```
(MW2019 v0xD inserts 288 extra bytes after the first 24 — not relevant to BO4.)

### Hash/entry table (`BO3XPakHashEntry` at `HashOffset`, `HashCount` entries, 24 bytes each)
```c
uint64_t Key;          // asset data hash (== LODStreamKey / image key)
uint64_t Offset;       // offset of the object's data, RELATIVE to DataOffset
uint64_t Size;         // compressed size; mask low 56 bits: Size & 0xFFFFFFFFFFFFFF
                       //   (top byte can be 0x80 flag in newer xpaks)
```
Lookup: `objectFileOffset = Header.DataOffset + entry.Offset`.

### Index records (at `IndexOffset`, `IndexCount` entries) — metadata only
Each: `uint64 Hash; uint64 PropertiesSize; <PropertiesSize bytes>`. Properties are a
newline-separated ASCII key:value blob (`width:`,`height:`,`size0:`,`name:`,`format:`,`type:`).
For BO4, `name:` is a hex value masked to 60 bits (`& 0x0FFF...F`). Images only need this;
model mesh blobs are fetched purely by `Key` from the hash table.

### Data-object block format (`DecompressPackageObject`) — how a streamed object is stored
An object's data is a sequence of **block groups**, each prefixed by a `BO3XPakDataHeader`:
```c
struct BO3XPakDataHeader {     // #pragma pack(1)
    uint32_t Count;            // number of blocks in this group (<=30)
    uint32_t Offset;
    uint32_t Commands[30];     // per block: (cmd & 0xFFFFFF)=blockSize, (cmd>>24)=flag
};
```
Per block, `flag` selects the codec:
- `0x0` — **raw/stored** (memcpy `blockSize` bytes)
- `0x3` — **LZ4** block (`DecompressLZ4Block`)
- `0x6` — **Oodle** (via "Siren"), decompressed size = `min(remaining, 262112)` (0x40000-32)
- `0x8` — **Oodle** with a 4-byte little-endian decompressed-size prefix inside the block
  (`blockDecompressedSize = *(uint32*)dataBlock`, then decompress `dataBlock+4`, `blockSize-4`)

After each block group the reader is padded up to the next **0x80 boundary**
(`pos = (pos + 0x7F) & ~0x7F`). Oodle lib used by Greyhound: `oo2core_6_win64.dll` (Oodle 2.6).

**Takeaway:** fully parseable offline. BO4 model mesh = fetch `LODStreamKey` from the xpak
hash table, read `entry.Size & 0xFFFFFF...` bytes at `DataOffset+entry.Offset`, decompress the
0x80-padded Oodle/LZ4 block groups, then apply the §1b offsets.

---

## 3. BO4/T8 GfxWorld / render geometry  (PARTIAL)

**Source:** ate47/atian-cod-tools @ `7906279`,
`src/core/acts/tools/fastfile/handlers/bo4/bo4_unlinker_map_gfx.cpp`
https://github.com/ate47/atian-cod-tools/blob/main/src/core/acts/tools/fastfile/handlers/bo4/bo4_unlinker_map_gfx.cpp

**Confidence: UNLINKER-SOURCE, but mostly stubbed.** ACTS has the top-level `GfxWorld` struct
with a verified total size (`static_assert(sizeof(GfxWorld) == 0x1ab0)`), but the **render
surface/vertex/index geometry is NOT reversed** — the relevant regions are large `unkXX`
runs. The dump worker only emits JSON *metadata* (name, bounds, static-model draw instances,
lighting/cookie image refs) — it does **not** export map mesh vertices/triangles. So this is a
scaffold, not a working map-geometry ripper.

What IS known (field offsets within `GfxWorld`, pack(1)):
```c
struct GfxWorld {
    XHash    name;             // +0x0
    const char* baseName;      // +0x10
    int32_t  surfaceCount;     // +0x18
    ... (unk20 .. unkd0, ~0xB0 of unknown) ...
    GfxWorldDraw draw;         // +0xD8 (see below)
    int32_t  modelCount;       // brush models
    GfxBrushModel* models;
    vec3_t   mins;             // world AABB
    vec3_t   maxs;
    uint32_t checksum;
    int32_t  materialMemoryCount;
    GfxWorldDpvsStatic dpvs;   // static-model draw instances live here
    ... many unk ...
    GfxWorldLighting* lighting;
};  // total 0x1ab0

struct GfxWorldDraw {          // render buffers (partially known)
    uint32_t blubIESprofileCNT; GfxImage* blubIESprofileIMG;
    int32_t  cookieCount;       GfxImage* cookieArray;
    ... unk20..unk70 ...
    uint32_t indexCount;        // <-- global index buffer count
    uint32_t unk7c;
    uint16_t* indices;          // <-- global 16-bit index buffer pointer
    ... unk88..unka0 ...        // vertex buffer pointer(s) are in this unknown region
};

struct GfxStaticModelDrawInst {// per static-model placement (dpvs.smodelDrawInsts)
    XModel*  model;  uint64 unk8; void* unk10; uintptr unk18; int32 unk20;
    ScrString_t name; uint32 unk28; uint16 unk2c; uint16 unk2e; uint32 unk30; int32 unk34;
};
```
`GfxWorldDpvsStatic` holds `smodelCount`, `smodelDrawInsts` (static model placements — useful:
these reference `XModel`s you CAN rip via §1), plus `GfxVisArray smodelVisData[4]` /
`surfaceVisData[4]` / `volDecalVisData[4]`, and `groupLodModels`.

**Gap:** the `GfxSurface` / `srfTriangles` equivalents (firstVertex/vertexCount/triCount/
baseIndex per world surface) and the world **vertex buffer** layout are inside unnamed `unk`
regions. For render geometry we have `indexCount`+`indices` but not the matching vertex
struct — this still needs raw-byte RE. Static-model instances (position + XModel ref) ARE
recoverable and may cover most of a zm map's visible geometry via placed models rather than
baked world surfaces.

**Lineage help:** Husky's `BlackOps3.cs` (`Scobalula/Husky` @ `ce1f82d`,
`src/Husky/Husky/Games/BlackOps3.cs`) is the closest *working* GfxWorld→OBJ reader and shows
the T7 `GfxWorld`/`GfxSurface`/`GfxWorldDraw` field pattern (vertex buffer = positions + packed
UV/normal; surfaces carry triCount/vertexCount/baseIndex). Husky never gained BO4 support, but
the BO3 layout is the single best template to resolve BO4's `unk` regions.

---

## 4. BO4/T8 clipMap_t / collision  (GAP — no open-source extractor)

**Status:** BO4 **does** have `ASSET_TYPE_CLIPMAP = 11` (Treyarch brush/plane collision, not
Havok), but **no open-source tool reverses it.** ACTS explicitly lists it as unimplemented —
`bo4_unlinker_map.hpp` header comment: `[ ] col_map (clipmap)`. ACTS's `com_map`
(`ASSET_TYPE_COMWORLD`) is **lights/probes/exploders only** (`ComWorld`, size 0x60 — see
`bo4_unlinker_map_com.cpp`), NOT collision. Greyhound/Wraith do not touch collision at all.

**Best available template = BO3 (same engine family):** COD Engine Research wiki,
"Collision Map Asset (BO3)" — https://codresearch.dev/index.php/Collision_Map_Asset_(BO3)
**Confidence: LINEAGE.** BO4's `clipMap_t` is expected to be a close evolution of this.

BO3 `clipMap_t` shape (summarised from the wiki; verify every offset against the BO4 zone):
- Identity: name, in-use flag, inline `ClipInfo` + `ClipInfo*`.
- `ClipInfo`: counted arrays of **planes (`cplane_s`), materials, brushsides (`cbrushside_t`),
  leafbrush nodes + indices, brush verts, unique indices, brushes (`cbrush_t`), brush bounds,
  brush contents.**
- BSP: node array + leaf array (each counted).
- **Geometry: vertex array + triangle index array (counts), plus a per-triangle-edge
  walkability bitfield** — this is the part most directly convertible to T6 collision tris.
- Collision accel: partition array + AABB-tree array (partitions hold triangle/index ranges).
- Submodels: `cmodel_t` array.
- Visibility: cluster count, bytes-per-cluster, vis data ptr.
- Map data: mapEnts ptr, built-in box brush/model, **checksum (last field; `mapcrc` dvar)**.
- Dynamic entities: `DynEntityDef` / `DynEntityPose` / `DynEntityClient` (0x80 in BO3) /
  `DynEntityColl` arrays; physics constraints; ropes (`rope_t` 0xE38).

Key sub-structs (BO3):
```c
cplane_s     { vec3 normal; float dist; uint8 type; uint8 signbits; ... }
cbrushside_t { cplane_s* plane; int flags; int flags2; }      // 2-byte packed
cbrush_t     { /* bounds, contents, side+vert counts & ptrs, axial flag arrays */ } // size 0x60
cStaticModel_s{ /* sectorlink, XModel*, contents, origin, inv axes, abs bounds, matrices */ }
cmodel_t     { bounds; float radius; ClipInfo*; cLeaf_s leaf; }
cLeaf_s      { /* AABB range, contents, bounds, leafbrushnode idx, cluster (+ a 4-byte field new in BO3) */ }
```
Other-title cross-refs for drift-checking: BO2
https://codresearch.dev/index.php/Collision_Map_Asset_(BO2) , MW3
https://codresearch.dev/index.php/Collision_Map_Asset_(MW3) , Ghosts, MW2 (same wiki).

**Action required:** raw-byte RE of the BO4 `clipMap_t` from the zone image, using the BO3
layout as the hypothesis. The walkable-tri array + brush/plane set is what maps onto T6-style
collision; this is the main unknown for the port but is NOT a Havok dependency.

---

## 5. BO4/T8 fastfile (`.ff`) container + asset pool enum

**Source:** ate47/atian-cod-tools @ `7906279`
- `.ff` decompressor + header versions: `src/core/acts/tools/fastfile/decompressors/decompressor_t78.cpp`
  https://github.com/ate47/atian-cod-tools/blob/main/src/core/acts/tools/fastfile/decompressors/decompressor_t78.cpp
- Asset enum: `src/core/shared/games/bo4/pool.hpp` (`enum XAssetType : byte`)
  https://github.com/ate47/atian-cod-tools/blob/main/src/core/shared/games/bo4/pool.hpp
- API header: `include/acts_api/fastfile.h`

**Confidence: UNLINKER-SOURCE** (ACTS decompresses real BO4 `.ff`s).

### `.ff` container
- **Magic: `0x3030303066664154` = ASCII `"TAff0000"`** (little-endian), shared BO3/BO4
  (decompressor id'd as "Black Ops 3/4", mask `MASK64`).
- **Header versions:** `0x265` = BO4 **Dev**, `0x27E` = BO4 **Old**, **`0x27F` = BO4 retail**
  (BO3 were `0x132`/`0x1FB`/`0x251`). Dispatched on `header->version`.
- Header (`TXFileHeader` common prefix) exposes: `compression` (codec name), `version`,
  `encrypted` (bool), `platform` (`XFILE_PC`/`XBOX`/`PLAYSTATION`/`DEV`), `builder` string,
  and an archive checksum `[4×u32]`.
- Retail BO4 (`XFileBO4_0x27F`) header is **0x840 bytes**, with (offsets from ACTS):
  decompressedSize @ `0x490`, blockSize array @ `0x4A8` (**9 blocks**), signature @ `0x730`,
  fastfileName @ `0x6F0`, aesIV @ `0x830`. BO4 is **AES-encrypted + RSA-signed** (ACTS uses an
  `rsaKeyName="bo4"` + `KeyVersion::VER_BO4`; names are `XHash`). Payload is block-compressed
  (Oodle, like the xpak). Decompressed zone is then walked by asset pool.
- NOTE: your teammate already has the decompressed zone, so the AES/RSA/Oodle front-end is
  already solved; this section is mainly for completeness + to confirm you're on `0x27F`.

### Asset pool enum (`XAssetType : byte`) — relevant ids (full list in the file)
```
0 PHYSPRESET            1 PHYSCONSTRAINTS      2 DESTRUCTIBLEDEF     3 XANIM
4 XMODEL                5 XMODELMESH           6 MATERIAL            8 TECHNIQUE_SET
9 IMAGE                 10 SOUND               11 CLIPMAP            12 COMWORLD
13 GAMEWORLD            14 GFXWORLD            33 FX                 38 AITYPE
39 CHARACTER            40 XMODELALIAS         89..93 MAPTABLE*      96 NAVMESH
97 NAVVOLUME            147 STREAMERWORLD      152 TERRAINGFX        162 GROUPLODMODEL
```
Config mirror (names only): ACTS `config/data/asset_types.json` and `config/data/games/bo4.json`.

---

## 6. BO4/T8 Havok collision + AI navmesh  (GAP — confirmed Havok, no open extractor)

**What's confirmed:** BO4 exposes `ASSET_TYPE_NAVMESH = 96` and `ASSET_TYPE_NAVVOLUME = 97`
(ACTS enum, §5). These are the `hkaiNavMesh` / `hkaiStreamingSet` /
`hkaiNavMeshGenerationUtilsSettings` Havok objects the teammate found in the decompressed
zm_escape zone — i.e. BO4's **AI navigation is Havok AI**, and **rigid-body physics**
(`ASSET_TYPE_PHYSPRESET`/`PHYSCONSTRAINTS`) is Havok Physics (`hkp`/`hknp`).

**Open-source extraction status: NONE.**
- ACTS: only `bo4_unlinker_physpreset.cpp` exists; **no navmesh/havok handler** (the tree has
  no `hkai`/`hknp`/`hkp`/`navmesh` source beyond physpreset).
- Greyhound/Wraith/Husky: models/images/anims/GfxWorld only — no Havok, no navmesh.
- Cordycep: in-memory CoD asset loader; no published BO4 Havok→mesh converter found.
- COD Engine Research wiki: **no NavMesh / Havok page at all** (search returns nothing).

**General Havok RE approach (from other games — adaptable, not CoD-specific):**
Confidence COMMUNITY-GUESS / external.
- Havok ships **built-in reflection data** in the binary, and **public headers for Havok 2014**
  exist to cross-reference offsets→member names (zeldaret/botw wiki):
  https://github.com/zeldaret/botw/wiki/Using-Havok-reflection-data-and-public-information
- **HKX2 / HKX2Library** (DSMapStudio lineage) de/serialises Havok packfiles incl. navmesh
  (`.hknm2`): https://github.com/HKX2/HKX2Library
- **botw_havok** (Python) converts Havok packfiles ↔ JSON (physics types only, experimental):
  https://pypi.org/project/botw-havok/
These assume a standalone `.hkx` packfile; BO4 embeds Havok objects inside the Treyarch zone,
so a loader would first have to carve the `hkai*`/`hkp*` blobs out of the decompressed zone and
identify the **exact Havok SDK version** (identifiable from the version string / class
signatures in those blobs — capture it from the zone; likely a ~2014–2016 build given BO4's
2018 ship date, but **unconfirmed** — this is a thing to read off the raw bytes).

**Recommendation for the port (matches the coordinator's concern):**
1. **World/bullet collision** is NOT Havok — it's the Treyarch `clipMap_t` (§4). That is the
   thing to reverse for a walkable map; Havok is not on the critical path for it.
2. **AI navmesh (Havok)** is effectively unobtainable via existing tools. For a zm port,
   **regenerate the navmesh in the BO3 toolchain** (or reuse the donor BO3 map's nav) rather
   than converting BO4 Havok — far cheaper than reversing Havok AI serialisation.
3. If `clipMap_t` RE proves too costly, the documented fallback (reuse an existing BO3 map's
   collision shell) remains valid — but note that it's a *convenience*, not a Havok necessity.

---

## GAPS — what still needs raw-byte RE (no usable published layout found)

1. **BO4 `clipMap_t` (asset 11)** — no open extractor; only the BO3 wiki layout as a template.
   This is the #1 blocker for native BO4→T6 collision. (§4)
2. **BO4 GfxWorld render surfaces/vertex buffer** — top-level struct known (ACTS, 0x1ab0) but
   the per-surface `GfxSurface`/`srfTriangles` ranges and the world vertex buffer layout are in
   unnamed regions; only `indexCount`+`uint16* indices` are identified. Use Husky BO3 as the
   template. Static-model instance list IS recoverable. (§3)
3. **BO4 Havok navmesh/physics internals** — Havok format + exact SDK version unconfirmed; no
   CoD tool extracts it. Recommend regenerate/reuse rather than convert. (§6)
4. **On-disk (zone) vs in-memory XModel header padding** — Greyhound's fixed structs are
   in-memory; confirm the `Padding[...]` gaps against the zone layout before trusting absolute
   offsets when parsing the raw zone (the *mesh blob* byte layout in §1b is unaffected and safe).
5. **Exact retail `XFileBO4_0x27F` full field list** — ACTS uses offset constants; only the
   key offsets (0x490/0x4A8/0x6F0/0x730/0x830, size 0x840, 9 blocks) are captured here. Not on
   critical path since the zone is already decompressed.

## Local copies of mined source
Raw files saved under `E:\ClaudeWork\bo4_recon\_src\` (gh_*.{h,cpp} = Greyhound; act_*.{hpp,cpp}
= ACTS) for offline reference while building the extractor.
