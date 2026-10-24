# cod2map64.exe plane caps (RE 2026-10-23)

Our own RE of the BO3 modtools map compiler `bin/cod2map64.exe`
(sha256 201a6b31072f74cfacab944014d446185570608e37e556132cc00db3f9db8efd, PE x86_64,
PDB ref cod2map64_modtools.pdb, source path q:\t7\pc\code\tools\cod2map\map.cpp).

## Two plane limits

**Compile working cap = 0xA0000 (655,360).** In FindFloatPlane `FUN_1400a00c0`:
`if (0xA0000 < (int)(numplanes + 2)) Error("MAX_MAP_PLANES_COMPILE (%i)", 0xA0000)`.
- numplanes counter: global `0x1841820a8` (planes added in +/- pairs, +2 per call).
- compile plane array: `0x1841820b0`, stride 0x20 (32 B/entry).
- Generous; not normally the binding limit.

**Final output cap MAX_MAP_PLANES = 0x20000 (131,072).** In EmitPlanes `FUN_14010e9b0`:
dedups referenced compile planes into the BSP plane lump; `if (nummapplanes == 0x20000) Error("MAX_MAP_PLANES (%i)")`.
- nummapplanes counter: global `0x141a0d6cc`.
- output plane array: `0x14379c6d0`, stride 0x10 (16 B/entry = dplane_t normal[3]+dist).
- Counts UNIQUE planes only (per-plane ref flag at compile entry +0x14 gates the copy). THIS is the binding cap that the merged MotD-shell+BoD clip hit.

## Practical takeaways for the port pipeline
- Patch collision meshes (clip_brushes.patches) do NOT add to the plane table — confirmed: the spawn build linked 143,999 patches + 7,891 brushes fine. So terrain soup is plane-free; only brush walls spend the 131,072 budget.
- Pure-BoD world brushes = 50,105 unique planes (bod_clip_le45.json) -> fits with ~80k headroom. The old failure was shell+BoD combined.
- RAISING the final cap (only if a map's brush planes exceed 131k): patch the `== 0x20000` immediate in EmitPlanes to a larger value AND enlarge the output array at 0x14379c6d0 (16 B * count). The matching limit also lives in BlackOps3.exe (loads the BSP), so a raised-cap map only loads on a patched/offline (Plutonium) engine -> legitimate for personal offline ports only, never for a shareable workshop map. Primary path stays collision decimation.

Tools/credits: analysed with Ghidra via REA. Our RE notes only; no Treyarch binary or game content is republished.
