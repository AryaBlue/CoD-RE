# BoD Havok → BO3 clip: feasibility (from zm_escape.ff.dec, 2026-10-21)

## What is actually in the zone
- 5 Havok binary tagfiles (`TAG0` / `SDKV 20170200` = Havok 2017.2 / `DATA` / `TYPE`), starting at .dec offset 330,700,640.
- Classes present are **AI only**: hkaiNavMesh, hkaiStreamingSet, hkaiAnnotatedStreamingSet, hkaiDirectedGraphExplicitCost, hkaiNavMeshClearanceCache, hkcdStaticAabbTree/StaticTree, hkaiCarver.
- **No physics shapes** (no hknp*/hkp* shape, MOPP or compressed-mesh classes; those hits are just name-table noise).
- So the Havok data is the **zombie navmesh**, not player collision. Player/bullet collision is presumably still Treyarch's own clipMap-style asset (to be located by the worker; the T6 struct shapes are in t6_world_structs.h).

## Navmesh → BO3: tractable, but it only gives floors
- hkaiNavMesh is a polygon mesh: m_faces (startEdgeIndex, numEdges), m_edges (a, b, opposite) and m_vertices (hkVector4, world space), with streaming sections in hkaiStreamingSet.
- The tagfile format is documented by open-source readers (e.g. HavokLib / hktag readers). Parsing 2017.2 TAG0 is a few hundred lines; no Havok SDK is needed.
- **It yields walkable floor polygons only. There are no walls, ceilings or props.** Uses:
  1. Seeds for BO3's cod2map navmesh (node positions on every face centroid): **cheap and high value.**
  2. Thin floor clip brushes (extrude each convex face 4u down, like our tri-prism path): **cheap.**
  3. Walls: not present. They would have to come from render geometry (tri-prism every gfx tri, which is how BO3 itself handles terrain), or from the real T8 clip asset.

## Recommendation
- Keep the lead's fallback: render swap first, shell clip kept.
- For the true BoD layout (route 3), the cheapest full collision is:
  - render-tri prisms from the extracted gfx (we already do this for clip tris; mind the 65k welded-vert cap per collision model — chunk it);
  - plus navmesh-derived seeds for AI pathing.
- Havok physics → brush conversion is moot: there is none to convert.
