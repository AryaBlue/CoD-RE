# BO3 (T7) Collision + GfxWorld Concrete Layouts — Hypothesis Template for BO4 Hand-RE

Companion to `t8_struct_refs.md`. This file gives the **exact BO3/T7 struct layouts** so two
teammates can use them as the starting hypothesis when reversing the BO4/T8 equivalents (same
engine family — T8 is expected to be a close evolution of T7).

- **Teammate A** — reverse BO4 `clipMap_t` (asset 11). Use §1.
- **Teammate B** — reverse BO4 `GfxWorld` surfaces + static-model placements (asset 14). Use §2.

**Confidence tags**
- **WIKI-RE** — COD Engine Research wiki, reversed from BO3 binary. Field *order + types* are
  solid; most **absolute offsets are NOT published** (the wiki gives sizes/alignment only where
  noted). Treat offsets as "derive by summing declared sizes", then verify against the zone.
- **RIPPER-VERIFIED (lineage)** — from Husky's `BlackOps3.cs`, which provably produces correct
  BO3 map OBJs from live process memory. Byte offsets ARE concrete (computed below), but they
  are **in-memory (runtime VA) layouts**; on-disk zone padding may differ — re-verify the
  `Padding[...]` gaps against the BO4 zone image before trusting absolute offsets.
- **CAVEAT** — wiki itself flags the field as unconfirmed/approximate.

**Sources (read-only, nothing cloned/run):**
- COD Engine Research wiki, "Collision Map Asset (BO3)" — https://codresearch.dev/index.php/Collision_Map_Asset_(BO3)
  (cross-check pages: BO2 https://codresearch.dev/index.php/Collision_Map_Asset_(BO2) ,
  BO1 https://codresearch.dev/index.php/Collision_Map_Asset_(BO1) ,
  MW3 https://codresearch.dev/index.php/Collision_Map_Asset_(MW3) )
- Scobalula/Husky @ commit `ce1f82d`, `src/Husky/Husky/Games/BlackOps3.cs`
  https://github.com/Scobalula/Husky/blob/master/src/Husky/Husky/Games/BlackOps3.cs
  (local copy: `E:\ClaudeWork\bo4_recon\_src\husky_BlackOps3.cs`)
- NOTE: a dedicated `GfxWorld Asset (BO3)` wiki page does **not exist** (404 / absent from
  search); Husky's `BlackOps3.cs` is the authoritative open-source GfxWorld layout and is used
  for §2.

Types: `vec3 = float[3]` (12 B); `ScriptString = uint16`; pointers = 8 B (x64); `Bounds` = 24 B.

---

# 1. BO3 clipMap_t and sub-structs  (for Teammate A — BO4 collision)

**Source: COD wiki "Collision Map Asset (BO3)". Confidence: WIKI-RE.**
BO3 merged SP+MP map types (as IW did at MW3). Collision is Treyarch brush/plane + a walkable
tri soup — **not Havok**. This is the layout the BO4 `clipMap_t` (asset 11) is expected to
evolve from.

## 1.0 Parse goal → target JSON
The converter wants `clip.json`:
```
{ brushes:[ {contents, planes:[{normal[3],dist}...], verts:[[x,y,z]...]} ... ],
  tris, tri_contents, tri_materials }
```
Map onto BO3 as follows:
- **Brushes** ← `ClipInfo.brushes[]` (`cbrush_t`), each brush's planes via `cbrushside_t.plane`
  + the 6 axial planes implied by `cbrush_t.mins/maxs`, verts via `cbrush_t.verts`/`numverts`,
  contents via `ClipInfo.brushContents[]` (parallel to brushes) and/or `cbrush_t.contents`.
- **Tri soup** ← `clipMap_t.verts[]` (positions) + `clipMap_t.triIndices[]` (u16 triples).
- **tri_materials** ← via `CollisionAabbTree.materialIndex` → `ClipInfo.materials[]`
  (`ClipMaterial`), reached through the partition/aabb ranges (see §1.8).
- **walkability** ← `clipMap_t.triEdgeIsWalkable` bitfield (see §1.6).

## 1.1 cplane_s   (pack 4)
```c
struct cplane_s {       // plane equation, shared by brushsides + BSP nodes
    float normal[3];    // +0x00
    float dist;         // +0x0C
    char  type;         // +0x10  axial/non-axial classifier
    char  signbits;     // +0x11
    // (pack 4 => struct padded to 0x14 / 20 B)
};
```

## 1.2 cbrushside_t   (pack 2)
```c
struct cbrushside_t {
    cplane_s* plane;    // +0x00  -> the cutting plane
    int       cflags;   // +0x08  content flags
    int       sflags;   // +0x10  surface flags   (pack 2 => 2-byte alignment packing)
};
```

## 1.3 cbrush_t   (align 8, total size **0x60** per wiki)
```c
struct cbrush_t {
    vec3          mins;             // +0x00
    int           contents;        // +0x0C
    vec3          maxs;             // +0x10
    unsigned int  numsides;        // +0x1C
    cbrushside_t* sides;           // +0x20
    int           axial_cflags[2][3]; // +0x28  content flags per +/- axis
    int           axial_sflags[2][3]; // +0x40  surface flags per +/- axis
    unsigned int  numverts;        // +0x58
    vec3*         verts;           // +0x60? -- WARNING: see note
};  // wiki states total 0x60
```
**CAVEAT:** the field list sums past 0x60, and the wiki notes "only one `verts` is loaded, at
least on 360" and marks `contents` as appearing twice. Treat `numverts`/`verts` as present but
**verify the tail of this struct against the zone** — this is the least certain sub-struct.
A non-axial brush = intersection of (6 axial planes from mins/maxs) + (`numsides` `cbrushside_t`
planes); `verts` are the precomputed corner points.

## 1.4 ClipInfo   (the big counted-array container; `clipMap_t` holds one inline + one ptr)
```c
struct ClipInfo {
    int           planeCount;        cplane_s*      planes;
    unsigned int  numMaterials;      ClipMaterial*  materials;
    unsigned int  numBrushSides;     cbrushside_t*  brushsides;
    unsigned int  leafbrushNodesCount; cLeafBrushNode_s* leafbrushNodes;
    unsigned int  numLeafBrushes;    uint16*        leafbrushes;
    unsigned int  brushVertCount;    vec3*          brushVerts;
    unsigned int  nuinds;            uint16*        uinds;
    uint16        numBrushes;        cbrush_t*      brushes;
    Bounds*       brushBounds;       // parallel to brushes
    int*          brushContents;     // parallel to brushes  <-- per-brush contents array
};
```
(count/ptr pairs; order as listed. `numBrushes` is `uint16`.)

## 1.5 ClipMaterial   (brush material + surface/content flags)
```c
struct ClipMaterial {
    const char* name;          // +0x00
    int         surfaceFlags;  // +0x08
    int         contentFlags;  // +0x0C
};  // 0x10
```
Wiki gives no bit values for surface/content flags — carry BO3's over to BO4 as a guess, verify
with known material names (e.g. clip, nosight, water) in the zone string table.

## 1.6 clipMap_t   (top-level, relevant fields in order)  — WIKI-RE
```c
struct clipMap_t {
    const char*   name;
    int           isInUse;
    ClipInfo      info;            // INLINE ClipInfo (primary)
    ClipInfo*     pInfo;           // ptr to a ClipInfo (secondary)
    unsigned int  numStaticModels; cStaticModel_s* staticModelList;
    unsigned int  numNodes;        cNode_t*        nodes;      // BSP nodes
    unsigned int  numLeafs;        cLeaf_s*        leafs;
    unsigned int  vertCount;       vec3*           verts;      // <-- TRI SOUP VERTS
    int           triCount;        uint16*         triIndices; // <-- TRI SOUP INDICES (triples)
    char*         triEdgeIsWalkable;   // bitfield, size = (((triCount*3)+0x1F)>>5)<<2 bytes
    int           partitionCount;  CollisionPartition* partitions;
    int           aabbTreeCount;   CollisionAabbTree*  aabbTrees;
    unsigned int  numSubModels;    cmodel_t*       cmodels;
    int           numClusters;     int clusterBytes; char* visibility; // size numClusters*clusterBytes
    int           vised;           MapEnts*        mapEnts;
    cbrush_t*     box_brush;       cmodel_t        box_model;
    uint16        originalDynEntCount; uint16 dynEntCount[4];
    DynEntityDef*    dynEntDefList[2];
    DynEntityPose*   dynEntPoseList[2];
    DynEntityClient* dynEntClientList[2];
    DynEntityServer* dynEntServerList[2];
    DynEntityColl*   dynEntCollList[4];
    int           num_constraints; PhysConstraint* constraints;
    int           max_ropes;       rope_t*         ropes;      // rope_t typedef = 0xE38 B
    ScriptString  unknownScriptStringArray[0x20];
    char          unknown[0x10];
    int           checksum;        // ALWAYS the last element (mapcrc dvar)
};
```
**Walkable tri soup (the part that maps to T6 collision):**
- `verts` = `vertCount` plain `vec3` positions.
- `triIndices` = `triCount * 3` `uint16` entries; wiki does not *state* they are triples, but
  the walkable-bitfield size formula `(((triCount*3)+0x1F)>>5)<<2` implies **3 indices per
  triangle** indexing into `verts`. CAVEAT: confirm triples (not strips) on the BO4 zone.
- `triEdgeIsWalkable` = 1 bit per tri-edge (`triCount*3` bits, 32-bit-word padded). Bit set =
  that edge is walkable (used to tag the AI/player-walkable surface).

## 1.7 cLeaf_s / cLeafBrushNode_s / cNode_t / cmodel_t  (BSP + submodels)  — WIKI-RE
```c
struct cLeaf_s {
    uint16 firstCollAabbIndex;   // range into aabbTrees
    uint16 collAabbCount;
    int    brushContents;
    int    terrainContents;
    vec3   mins;
    vec3   maxs;
    int    leafBrushNode;        // index into ClipInfo.leafbrushNodes
    int16  cluster;              // vis cluster id
    int    unknown;              // CAVEAT: wiki says BO3 adds ~4 extra bytes here, position unconfirmed
};

struct cLeafBrushNode_s {
    char   axis;
    int16  leafBrushCount;
    int    contents;
    union {                      // leaf vs internal node
        struct { uint16* brushes; } leaf;
        struct { float dist; float range; uint16 childOffset[2]; } children;
    } data;
};

struct cNode_t {                 // BSP internal node
    cplane_s* plane;
    int32     children[2];       // >=0 node index, <0 leaf index (standard CoD BSP convention)
};

struct cmodel_t {                // collision submodel (e.g. door brushmodels)
    vec3     mins;
    vec3     maxs;
    float    radius;
    ClipInfo* info;
    cLeaf_s  leaf;
};
```

## 1.8 Collision accel: CollisionPartition / CollisionAabbTree  — WIKI-RE
```c
struct CollisionPartition {      // const struct
    char triCount;               // tris in this partition
    int  firstTri;               // first tri index (into triIndices/3 ?)
    int  nuinds;                 // count of uinds
    int  fuind;                  // first uind
};

union CollisionAabbTreeIndex { int firstChildIndex; int partitionIndex; };
struct CollisionAabbTree {
    vec3_t   origin;
    uint16   materialIndex;      // -> ClipInfo.materials[] (per-tri/leaf material)
    uint16   childCount;         // 0 => leaf (u = partitionIndex), else internal (u = firstChildIndex)
    vec3_t   halfSize;
    CollisionAabbTreeIndex u;
};

struct Bounds { vec3_t midPoint; vec3_t halfSize; };        // 24 B
struct DObjAnimMat { float quat[4]; float trans[3]; float transWeight; };
struct cStaticModelWritable { uint16 nextModelInWorldSector; };
```
**How material is assigned to a tri:** walk the AABB tree → leaf (`childCount==0`) →
`partitionIndex` → `CollisionPartition` → `firstTri/triCount` range of `triIndices`; the leaf's
`materialIndex` names the material for those tris. CAVEAT: the wiki does NOT confirm that
`firstTri` indexes `triIndices` (vs a separate tri list) — verify on the BO4 zone; this is the
least-documented linkage and the thing Teammate A should nail down empirically.

## 1.9 cStaticModel_s   (collision-side static model placement)  — WIKI-RE
```c
struct cStaticModel_s {
    cStaticModelWritable writable;        // uint16 nextModelInWorldSector
    XModel*  xmodel;
    int      contents;
    vec3     origin;
    vec3     invScaledAxis[3];            // inverse-scaled 3x3 rotation
    vec3     absmin;
    vec3     absmax;
    unsigned int matCount;
    DObjAnimMat* mats;
    ScriptString unknownScriptString;
};
```
(This is the **collision** copy of static-model placements; the **render** copy is
`GfxStaticModel` in §2 — they are parallel lists, same models, different struct.)

### Teammate A — BO4 reversing checklist
1. Find `clipMap_t` in the zone (asset pool 11). Anchor on `name` (null-term string) + the final
   `checksum`.
2. Lock `vertCount`/`verts` + `triCount`/`triIndices` first — the tri soup is the payload; cross
   validate with the walkable-bitfield size formula.
3. Resolve `ClipInfo` (inline) counted arrays: `numBrushes`/`brushes`, `brushContents`, planes,
   brushsides — that gives the brush set.
4. Confirm the partition→aabb→material linkage (§1.8) to tag tri materials.
5. Expect BO4 to add fields (new dynent/rope sizes, extra counts). Field *order* should largely
   hold; absolute offsets will shift — do not hardcode BO3 offsets.

---

# 2. BO3 GfxWorld surfaces + world vertex buffer + static-model instances  (for Teammate B)

**Source: Scobalula/Husky `BlackOps3.cs` @ `ce1f82d`. Confidence: RIPPER-VERIFIED (lineage).**
Husky reads these from the **live process** (`GfxMap` asset, found at asset-pool slot via
`assetPoolsAddress + 0x200`). Offsets below are computed by summing Husky's `[Pack=1]` structs
and are **in-memory VAs** — for an offline BO4 zone, treat field *order* as reliable and
re-verify the `Padding[...]` gaps (same caveat as the XModel structs in `t8_struct_refs.md §1`).

Positions here are raw engine units; Husky multiplies by 2.54 (inch→cm) for OBJ — that is
Husky's choice, not part of the layout.

## 2.1 GfxMap (= GfxWorld render asset)  — concrete in-memory offsets
```c
struct GfxMap {                 // [Pack=1]
    long  NamePointer;             // +0x000  -> gfx map name
    long  MapNamePointer;          // +0x008  -> map name
    long  Padding;                 // +0x010
    int   SurfaceCount;            // +0x018
    byte  Padding1[0x24C];         // +0x01C
    int   GfxVertexCount;          // +0x268  world vert count
    int   GfxVertexBufferSize;     // +0x26C  raw position-buffer size
    long  GfxVerticesPointer;      // +0x270  -> position buffer (GfxVertex[], 12 B each)
    byte  Padding2[8];             // +0x278
    long  GfxVertexDataBufferSize; // +0x280
    long  GfxVerticesDataPointer;  // +0x288  -> vertex-data buffer (GfxVertexData[], 20 B each)
    byte  Padding4[8];             // +0x290
    long  GfxIndicesCount;         // +0x298  global index count
    long  GfxIndicesPointer;       // +0x2A0  -> global u16 index buffer
    byte  Padding5[0x54];          // +0x2A8
    int   GfxStaticModelsCount;    // +0x2FC
    byte  Padding6[0x130];         // +0x300
    long  GfxSurfacesPointer;      // +0x430  -> GfxSurface[] (0x60 each)
    long  GfxStaticModelsPointer;  // +0x438  -> GfxStaticModel[] (0x98 each)
};
```
**Key design point (same as T6):** the world uses a **split vertex stream** — positions in one
buffer (`GfxVerticesPointer`, 12 B/vert) and colour/UV/normal/tangent in a parallel buffer
(`GfxVerticesDataPointer`, 20 B/vert), both indexed by the same vertex index. A **global u16
index buffer** + **per-surface base offsets** let the map exceed 65 k verts with 2-byte indices.

## 2.2 GfxSurface   (size **0x60 / 96 B**, read at `GfxSurfacesPointer + i*96`)
```c
struct GfxSurface {             // [Pack=1]
    byte   Padding[0xC];            // +0x00
    int    VertexBufferOffset;      // +0x0C  BYTE offset into position buffer; /12 = base vertex
    byte   Padding1[0xC];           // +0x10
    int    VertexDataBufferOffset;  // +0x1C  BYTE offset into vertex-data buffer; /20 = base vert
    int    VertexIndex;             // +0x20  base vertex index
    int    Padding2;                // +0x24
    uint16 VertexCount;             // +0x28  verts in this surface
    uint16 FaceCount;               // +0x2A  tris in this surface
    int    FaceIndex;               // +0x2C  base into global index buffer (in u16 units)
    byte   Padding3[0x18];          // +0x30
    long   MaterialPointer;         // +0x48  -> Material (1 per surface)
    byte   Padding4[0x10];          // +0x50
};  // 0x60
```
**Face assembly (verbatim from Husky):** for tri `i` in `[0, FaceCount)`:
```
base  = VertexBufferOffset / 12                       // base vertex for this surface
idx0  = triIndices[ FaceIndex + i*3 + 0 ] + base
idx1  = triIndices[ FaceIndex + i*3 + 1 ] + base
idx2  = triIndices[ FaceIndex + i*3 + 2 ] + base      // Husky swaps winding: writes 0,2,1
```
So a world surface = `(firstVertex = VertexBufferOffset/12, vertexCount = VertexCount,
baseIndex = FaceIndex, triCount = FaceCount)` into the global index buffer — directly analogous
to T6 `srfTriangles`.

## 2.3 World vertex buffers
```c
struct GfxVertex {              // 12 B, at GfxVerticesPointer + vertIndex*12
    float X, Y, Z;              // plain float3 position (NOT quantised)
};

struct GfxVertexData {          // 20 B, at GfxVerticesDataPointer + vertIndex*20
    GfxColor Color;             // +0x00  RGBA (4 B)
    float    U;                 // +0x04
    float    V;                 // +0x08  (Husky stores 1-V)
    int      Normal;            // +0x0C  packed unit vector (same 10/10/10 scheme as XModels)
    int      Padding2;          // +0x10  packed tangent (Husky ignores)
};                              // 20 B
```
Normal unpack = the same scheme as the XModel normals in `t8_struct_refs.md §1b` (Wraith
"MethodD" / 10:10:10 signed, /511). NOTE: unlike BO4 XModel UVs (half-floats), BO3 **world** UVs
here are **full float32**.

## 2.4 GfxStaticModel   (render placement instance, size **0x98 / 152 B**)
```c
struct GfxStaticModel {         // [Pack=1], at GfxStaticModelsPointer + i*0x98
    float X, Y, Z;              // +0x00  world origin
    float Matrix[9];            // +0x0C  3x3 rotation matrix (row-major: [0..2]=X, [3..5]=Y, [6..8]=Z)
    float ModelScale;           // +0x30  uniform scale
    byte  Padding[0x24];        // +0x34
    long  ModelPointer;         // +0x58  -> XModel asset (name via *(ModelPointer))
    byte  UnknownBytes2[0x38];  // +0x60
};  // 0x98
```
Placement = origin (`X,Y,Z`) + 3×3 rotation (`Matrix`, convert to Euler) + uniform `ModelScale`
+ `XModel*`. Husky skips models whose name starts with `*` (inline brush models). This is the
**render** copy; the collision copy is `cStaticModel_s` (§1.9), parallel list.

## 2.5 Material (for surface → image, abridged from Husky)
```c
struct Material {               // runtime
    long NamePointer;           // +0x00
    byte Padding[40];
    long Settings[72];
    byte ImageCount;            // after Settings
    byte Padding2[7];
    long TechniquePointer;
    long ImageTablePointer;     // -> MaterialImage64B[ImageCount]
    long UnknownPointer;
    long Padding3[2];
};
```
Per image: `MaterialImage64B` with a `SemanticHash` (colour map = `0xA0AB1041`) and
`ImagePointer`; image name at `ImagePointer + 0xF8`. (Only needed if Teammate B wants per-surface
textures; geometry does not require it.)

### Teammate B — BO4 reversing checklist
1. Find `GfxWorld` (asset pool 14; ACTS confirms top-level size `0x1ab0` — see
   `t8_struct_refs.md §3`). BO4 keeps `surfaceCount` near the top, `indexCount`+`uint16* indices`
   known, but the per-surface `GfxSurface` array ptr + the split vertex buffers are in `unk`
   regions — the BO3 layout above tells you *what shapes to look for*: a position buffer
   (float3), a parallel data buffer, a global u16 index buffer, a `GfxSurface`-like record with
   (vertexBufferOffset, vertexCount, faceCount, faceIndex, material*).
2. Static-model instances (`GfxStaticModelDrawInst` in BO4, under `GfxWorldDpvsStatic`) are
   already partly known in ACTS and are the **most recoverable** render data — origin + packed
   transform + `XModel*` (rippable via Greyhound). Confirm the BO4 transform packing against the
   BO3 `GfxStaticModel` (plain float origin + float[9] matrix + float scale) as the hypothesis;
   BO4 may pack rotation as a quat or half-floats — check.
3. BO4 world UVs/normals may be packed (half-float/10:10:10) rather than BO3's float32 UVs —
   verify the data-buffer stride empirically.

---

## Cross-check / drift notes
- The **cbrush_t** tail (`numverts`/`verts`) and the **cLeaf_s** "extra 4 bytes" are the two
  wiki-flagged uncertainties in §1 — do not trust their absolute offsets without a zone dump.
- All §1 offsets must be *derived* (wiki publishes order+sizes, not offsets); all §2 offsets are
  concrete but **in-memory** (Husky reads live RAM) — re-verify padding on the offline BO4 zone.
- Older-title wiki pages (BO2/BO1/MW3/Ghosts) are useful to bracket which fields are stable
  across the family vs which Treyarch added at BO3 — handy when a BO4 field doesn't match BO3.
