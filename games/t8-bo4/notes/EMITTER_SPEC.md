# BO4 extractor → BO3 shell pipeline: exact emitter spec

Target: two files per map, consumed unchanged by the pipeline that built the shipped zm_alcatraz:
- `<map>.gfx.bin`, render world (W2BSP001), read by `waw2bo2.world.read_gfx_world` (F:\Documents\BO1MapConverter\b2w_bo1\src\waw2bo2\world.py:172), then `bod_port\geo\build_textured.py` → XMODEL_EXPORT chunks.
- `<map>_clip.json`, collision brushes plus triangles, read by `bo3_modtools_test\clip_brushes.py` → cod2map clip brushes and navmesh.

Check every emit with `python E:\ClaudeWork\bo4_recon\validate_emit.py <gfx.bin> <clip.json> -1815 8033 1432`. Known-good baseline (zm_prison):
- gfx: 324,065 verts, 11,988 surfaces, 224,550 tris, winding_ok 100.0%.
- clip: 15,133 brushes, `problems: []`, 18 brushes with verts more than 0.05u outside their planes (float noise).

Conventions for both files: COD world units (inches) 1:1, Z-up, world space. No scaling and no axis swap.

## 1. gfx.bin (all little-endian; `string` = u32 byte length + UTF-8, no terminator)

Emit **version 1**, the minimum: no static models, brush models, layers or shadow data.

```
char[8]  "W2BSP001"
u32      version = 1
u32      vertexCount          (≤ 20,000,000)
u32      indexCount           (≤ 60,000,000; = 3 × total tris)
u32      surfaceCount
u32      staticModelCount = 0
string   name                 e.g. "maps/zm/zm_escape"
string   baseName             e.g. "zm_escape"
string   skyboxModel          "" is fine
vertex[vertexCount]           44 bytes each:
    f32 x, y, z
    u32 color                 0xAARRGGBB (byte order B,G,R,A); white = 0xFFFFFFFF
    f32 u, v                  material UV, as the engine samples it (no flip)
    f32 lmU, lmV              0 is fine (unused downstream)
    u32 normal                packed "unit vec scale": bytes x,y,z,s; comp = (byte-127)*(s+192)/32385, then normalised
    u32 tangent               same packing (unused downstream; 0x7F7F7FFF-ish or copy the normal is fine)
    f32 binormalSign          ±1
u16      indices[indexCount]  SURFACE-LOCAL (0..vertexCount_of_surface-1), so each surface needs < 65,536 verts
surface[surfaceCount]:
    u32 firstVertex           index into the global vertex array
    u16 vertexCount
    u16 triCount
    u32 baseIndex             index (not byte offset) into indices[]
    string material           material asset name (a leading "," is stripped)
    u8  lightmapIndex, reflectionProbeIndex, primaryLightIndex, flags   (0s fine)
    f32 mins[3], maxs[3]
(staticModelCount = 0 → nothing more; the file must END here — trailing bytes are an error)
```

Packing helper for a unit normal n: use `s = 255` (byte 3), so scale = 447/32385; then bytes x, y, z = round(n.i / scale + 127), clamped to 0..255.

Reference writer: `E:\ClaudeWork\bo4_recon\emit_gfx_v1.py` (`write_gfx_v1(...)`). Re-emitting zm_prison as v1 reads back with identical geometry, indices and surfaces; the maximum normal quantisation error is 0.0088.

**Winding (critical; we were bitten today):** emit the engine's NATIVE index order. For T6 (and expected for T7/T8), `(p1-p0)×(p2-p0)` points AGAINST the vertex normal. The validator's `winding_ok_pct` must be about 100. If it reports about 100% `winding_reversed`, swap corners 2 and 3.

**Materials:** `build_textured` collapses names to base textures and looks up images by material name. Emit the real BO4 material names; texture mapping is a separate pass.

## 2. clip.json

```json
{"brushes": [{"contents": int, "planes": [[nx,ny,nz,d], ...], "verts": [[x,y,z], ...]}, ...],
 "tris": [[[x,y,z],[x,y,z],[x,y,z]], ...],
 "tri_contents": [int, ...],          // parallel to tris
 "tri_materials": [str|null, ...]}    // parallel to tris, optional
```
- **Planes:** OUTWARD normals; a point is inside when `n·x ≤ d` for every plane. The FIRST SIX planes must be axial in the order −X, +X, −Y, +Y, −Z, +Z, i.e. `[-1,0,0,-minX]`, `[1,0,0,maxX]`, and so on. Bevel/side planes follow. The validator enforces this.
- **verts:** the brush's corner points (optional but recommended). They are used for the face centre, and the validator checks they lie inside.
- **Only WORLD brushes.** Drop brush-entity (submodel) brushes stored in local space at the origin; one 22k-unit cube buried every navmesh node on zm_prison. clip_brushes also skips brushes with smallest axial extent > 4096.
- **contents bits used (T6 values; confirm T8):** SOLID 0x1, PLAYERCLIP 0x10000, MONSTERCLIP 0x20000, CLIPSHOT 0x2000, MISSILECLIP 0x80, DETAIL 0x8000000.
  - Mapping: SOLID or (PLAYERCLIP and MONSTERCLIP) → `clip`; PLAYERCLIP → `clip_player`; MONSTERCLIP → `clip_ai`; CLIPSHOT|MISSILECLIP → `clip_weapon`; anything else is skipped.
  - If T8's bit values differ, remap to these T6 values when emitting.
- **tris:** collision-mesh triangles (terrain soup), world space. Each becomes a 4u-deep prism brush. On zm_prison the walkable ground came from BRUSHES; tris were mostly bullet-only (0x2080).

## 3. What's already proven downstream (no need to re-prove)

zm_prison's gfx.bin and clip.json, through exactly this path (build_textured → import_rip → make_shell_map --clip → build_usermap.ps1), produced the shipped, in-game-tested zm_alcatraz: walkable, navmeshed (1,237/1,238 nodes valid) and textured.

Once BO4 output passes validate_emit, swap the two inputs:
- point build_textured.py `GFX` at the new gfx.bin;
- run `make_shell_map.py --clip <new clip.json>`;
- run `build_usermap.ps1 -Map <name>`.

It needs a BO4-side spawn (`--start`) and node_pathnodes or other seeds (`--ents`); without seeds cod2map keeps only a tiny navmesh region.

## 4. Where T8 data probably lives (for stage 3)
Vertex and index buffers are expected to be streamed in the `.xpak` rather than inline in the fastfile. GfxWorldDraw-like counts and pointers in the zone blob give the sizes, and stream keys locate the data in the xpak. T6 reference structs (verbatim, OAT): `E:\ClaudeWork\bo4_recon\t6_world_structs.h`.
