# Stage-3 GfxWorld/placements — offline worker MODLOG (task #37)

Zone: E:\ClaudeWork\bo3\bod_port\t8_world\decomp\zm_escape.ff.dec (510,745,780 bytes).
64-bit py: python.exe (64-bit)  (run with -I).
Landmark s_warden_box -1815 8033 1432 (shared world space w/ MotD zm_prison after metre->inch).

## CONFIRMED FACTS
- XHash = {u64 name; u64 str} = 0x10. Hash64 = FNV1a basis 0xCBF29CE484222325 prime 0x100000001B3, 64-bit; lowercase + '\\'->'/'. Name hashes stored MASKED to 63 bits (&0x7FFFFFFFFFFFFFFF): "maps/zm/zm_escape.d3dbsp"=0x6ba7703dc1c9d8da (10 hits), "zm_escape"=0x551fd293040f234e (6 hits).
- ACTS BO4 structs use NATURAL x64 alignment; unkXX field names == byte offsets.
- GfxWorld sizeof 0x1ab0; offsets: name@0x0, surfaceCount@0x18, draw@0xd8, modelCount@0x180, mins@0x190, maxs@0x19c, checksum@0x1a8, dpvs@0x1b8 (smodelCount@0x1bc, smodelDrawInsts ptr@0x400). NOTE: on-disk stream layout did NOT match these offsets at name-hash hits -> GfxWorld not yet cleanly located by struct scan (deprioritised; see below).
- XModel sizeof 0x150, name XHash @ +0x0.

## STATIC-MODEL PLACEMENT ARRAY (= collision static models; BoD session located it)
- @0x1D3898E4, 42,559 records x 0x60 bytes.
- Record (BoD layout, VERIFIED matches my independent orthonormal-matrix scan, phase +0x14):
  +0x00 float3 origin | +0x0c float3x3 invScaledAxis | +0x30 float3 absmin | +0x3c float3 absmax
  +0x48 u32 0 | +0x4c u32 flags(0x3039 / 0x13039 / misc) | +0x50 u32 0 | +0x54 u64 xmodel ptr | +0x5c u32 contents
- origin == midpoint(absmin,absmax) for props. rec1000 origin=(-1731.5,8286.0,1346.5) == ON the landmark -> ARRAY + ORIGIN FIELD CONFIRMED REAL world coords.
- TRANSFORM SOLVE: invScaledAxis = (1/s)*R^T (uniform s). s = 1/norm(row); R = s * invScaledAxis^T (orthonormal det+1, verified).

## OPEN BLOCKER: XModel pointer base
- xmodel ptr form 0x40000000_XXXXXXXX. BoD decode (XXXXXXXX-1)+0x101DF9EC lands in a block filled w/ repeating 0x00c000 padding -> that base is for clip-INTERNAL ptrs, NOT the cross-asset XModel pool. Need the XModel-pool base.
- FIX IN PROGRESS: hash the 6092 Greyhound BoD model names (E:\ClaudeWork\bo3\greyhound\app\exported_files\black_ops_4\xmodels\<name>), scan .dec for those hashes -> real XModel struct offsets -> solve base = struct_off - (ptr_low-1); same pass gives hash->name.

## TARGET OUTPUT SCHEMA (motd_smodels.json): list of {model, source, origin[3], angles[3], scale, axis[9], flags}
  reuse MotD matrix->angles convention from bod_port\geo builder.

## FILES (this batch) E:\ClaudeWork\bo3\bod_port\t8_world\stage3_gfxworld\
  find_gfxworld.py, inspect_hits.py, scan_placements.py, dump_record.py, extract_0x60.py, verify_chain.py
