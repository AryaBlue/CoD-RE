# T6 (BO2) renderer - structs, functions, how a frame flows

Time-boxed pass on 2026-10-20 (25 minutes). Sources:

- **Server build:** the dedicated server `CoDMPServer_PC.exe` (2013-03-11) in the game's `pc pdb` folder ships the whole
  D3D11 renderer (`gfx_d3d:*` objects, 1,581 functions), with its `.map` (names, addresses) and `.pdb` (types).
- **Matcher:** we matched those functions to Plutonium's client `t6zm.exe` with `../t6match`.

Files next to this note:

| file | what |
|---|---|
| `t6_renderer_functions.tsv` | all 1,834 renderer and HUD-draw functions (`R_`, `RB_`, `Material_`, `Image_`, `Load_`, `CG_Draw*`, `SCR_`) with the server address and, for 309, the t6zm address (and which pass matched it) |
| `t6_renderer_globals.tsv` | 35 renderer and cgame globals mapped to t6zm |
| `t6_renderer_structs.txt` | PDB layouts of 39 renderer structs (back end, command buffers, views, scene, globals) |

## How sure the t6zm addresses are

- **The server build differs from t6zm:** it keeps frame pointers and asserts, while t6zm is fully optimised. Byte
  signatures matched 21 of 1,834 functions, so they don't work.
- **The matcher instead works in two steps:**
  - **Seeds:** functions that reference the same rare string literals in both builds. Assert strings exist only in
    the server, so these are mostly errors, dvar names and asset names.
  - **Propagation:** for each matched pair, align the two lists of direct calls (assert and print calls removed), using
    callees that are already matched as anchors. Gaps of equal length are then paired.
- **Coverage:** 6,660 functions across the whole exe, but only 206 of the 1,834 functions in the table (most renderer
  code has no strings). That is pass **A** in the table.
- **Pass B** (`callers.py`) also pairs a server function when every t6zm function calling its matched callees narrows
  to one, alternating with the sequence step. That brings the whole exe to 9,811 functions and the table to 309. It
  has no independent check yet beyond the command sizes below, so treat B rows as leads.
  - Its new command-buffer matches carry the same command sizes as the server build: quad pic 0x18/0x14, clear screen
    0x1C, rotated stretch pics 0x34.
- **Accuracy:** checked against 28 t6zm addresses we had already verified at runtime. 22 are right, 2 wrong (each
  points to a neighbouring function), and 4 are unmatched, so **about 92% right**.
  - Spot checks agree: `R_AddCmdDrawStretchPicInternal` pushes command size 0x34 in both builds, and
    `R_AddCmdDrawTextInternal` pushes command id 17 (`RC_DRAW_TEXT_2D`) in both.
- **Before hooking anything, check the bytes.**
- **Globals:** pairing data addresses inside matched functions, aligned by the instruction bytes in front of them.
  Scalars and arrays come out right (`level` = 0x02338780, `cg_viewModelArray` = 0x0107CC28, which is exactly what our
  DLL already uses).
- **Big structs whose layout differs between the builds come out skewed:** `rgp` comes out at 0x03579504, but it
  really starts at 0x03579180, because the client's `sortedMaterials` has 0x1380 entries where the server has 0x1100.

## Key t6zm addresses (matched)

| function | t6zm | server |
|---|---|---|
| `R_SyncRenderThread` | 0x0070E780 | 0x00A2F050 |
| `R_IssueRenderCommands` | 0x0070E850 | 0x00A2F1E0 |
| `R_AddCmdDrawStretchPicInternal` | 0x0070F050 | 0x00A2C120 |
| `R_AddCmdDrawTextInternal` | 0x0070F440 | 0x00A2C5C0 |
| `R_GetCommandBuffer` (B) | 0x0070EA40 | |
| `R_AddCmdDrawQuadPicInternal` (B) | 0x00710600 | |
| `R_EndFrame` | 0x00710BB0 | 0x00A2E4A0 |
| `R_AddBrushModelToSceneFromAngles` (B) | 0x00724BA0 | 0x00A0F6D0 |
| `R_AddDObjToScene` (B) | 0x00724CC0 | 0x00A0F850 |
| `R_UpdateFrameFog` (B) | 0x00725BB0 | 0x00A10A30 |
| `R_ClearScene` | 0x0072F180 | 0x00A1D030 |
| `R_SetViewParmsForScene` | 0x0072F310 | 0x00A1D1F0 |
| `R_AddXModelSurfaces` | 0x00726C20 | 0x00A12440 |
| `R_GenerateSortedDrawSurfs` | 0x0072CF60 | 0x00A1AE70 |
| `RB_EndSceneRendering` | 0x00730AB0 | 0x00A25380 |
| `R_TextWidth` | 0x00732710 | 0x00A285F0 |
| **`Material_RegisterHandle`** (`precacheshader` / HUD materials by name) | **0x007333C0** | 0x00A2A140 |
| `Material_Duplicate` (verified before) | 0x00733120 | 0x00A29DE0 |
| `Material_LoadPerMap` | 0x00733430 | 0x00A2A1E0 |
| `RB_EndFrame` | 0x00748580 | 0x00A5A750 |
| `RB_Draw3D` | 0x00748680 | 0x00A5A9D0 |
| `RB_CallExecuteRenderCommands` (B) | 0x00748BD0 | 0x00A5AB50 |
| `Image_Register` | 0x0074C8C0 | 0x00A614D0 |
| `R_RegisterDvars` | 0x00718990 | 0x00A1F600 |
| `SCR_UpdateScreen` (B) | 0x00569940 | |
| `CG_DrawActive` (B) | 0x00640EB0 | |

(B) = pass B match.

Most of the renderer sits between 0x70E000 and 0x777000 in t6zm.

Globals (t6zm):
- `level` 0x02338780
- `cgArray` 0x01113F9C, `cgsArray` 0x01113F78
- `cg_viewModelArray` 0x0107CC28
- `frontEndDataOut` 0x033ED200 (16/16 votes)
- `scene` 0x03413A80
- `dpvsGlob` 0x034049A0
- `s_world` 0x035F21F4
- `cinematicGlob` 0x035BF048
- `rgp` 0x03579180 (runtime-verified, see `t6_materials_runtime.md`)

## How a frame flows (from the names, call graph and structs)

The full step-by-step path, main loop to `Present`, with t6zm addresses for each step: [`t6_frame_walkthrough.md`](t6_frame_walkthrough.md).

How each draw picks its technique, the exact vertex input formats, and how BO1/WaW technique numbers map to T6: [`t6_techniques.md`](t6_techniques.md).
Every t6zm function match (9,800+ rows) is in `t6zm_all_functions.tsv`, globals in `t6zm_all_globals.tsv`.

1. **Front end (main thread).** cgame builds the scene:
   - `R_ClearScene`, then `R_AddDObjToScene`, `R_AddBrushModelToSceneFromAngles` and the light adders fill `GfxScene`
     (one `GfxDrawSurf` array per pass and surface type: bsp, static model, entity, fx, times lit, emissive, shadow).
   - `R_SetViewParmsForScene` and `R_RenderScene` add the view.
   - HUD and 2D drawing go through `R_AddCmd*Internal` (stretch pic, text, quad lists), which append commands to the
     frame's command list.
2. **Worker threads.** `R_InitWorkerThreads` / `R_*WorkerCmds`: visibility (dpvs), skinning and surface adding are
   split into worker commands. The front end waits for them (`R_WaitFrontendWorkerCmds`).
3. **Sorting.**
   - `R_GenerateSortedDrawSurfs` and `R_SortSurfaces` sort each list by the 64-bit `GfxDrawSurf` key below.
   - Materials sort once per registration: `R_SortMaterials` over `rgp.sortedMaterials` (see `t6_materials_runtime.md`).
4. **Hand-off.**
   - `R_EndFrame` closes the list (`R_AddCmdEndOfList`).
   - `R_IssueRenderCommands` / `R_ToggleSmpFrame` swap between the two `GfxBackEndData` buffers.
   - `frontEndDataOut` is the one the front end fills; `R_SyncRenderThread` waits for the render thread.
5. **Back end (render thread).**
   - `RB_ExecuteRenderCommandsLoop` walks `GfxCmdArray.cmds`. Each command starts with
     `GfxCmdHeader {u16 byteCount; u8 id; u8 ui3d}` and `id` is a `GfxRenderCommand`.
   - `RB_BeginViewCmd` draws a 3D view through `RB_Draw3D` and `R_DrawSurfs`, per material and technique.
   - `RB_EndSceneRendering` and the post-fx follow, then `RB_EndFrame` / `RB_SwapBuffers` present.

### GfxRenderCommand (command ids)

| id | command |
|---|---|
| 0 | END_OF_LIST |
| 1 | SET_CUSTOM_CONSTANT |
| 2 | SET_MATERIAL_COLOR |
| 3 | SAVE_SCREEN |
| 4 | SAVE_SCREEN_SECTION |
| 5 | CLEAR_SCREEN |
| 6 | BEGIN_VIEW |
| 7 | SET_VIEWPORT |
| 8 | SET_SCISSOR |
| 9 | RESOLVE_COMPOSITE |
| 10 | PC_COPY_IMAGE_GEN_MIP |
| 11 | STRETCH_PIC (also FIRST_NONCRITICAL) |
| 12 | STRETCH_PIC_FLIP_ST |
| 13 | STRETCH_PIC_ROTATE_XY |
| 14 | STRETCH_PIC_ROTATE_ST |
| 15 | DRAW_QUAD_PIC |
| 16 | DRAW_FULL_SCREEN_COLORED_QUAD |
| 17 | DRAW_TEXT_2D |
| 18 | DRAW_TEXT_3D |
| 19 | BLEND_SAVED_SCREEN_BLURRED |
| 20 | BLEND_SAVED_SCREEN_FLASHED |
| 21 | DRAW_POINTS |
| 22 | DRAW_LINES |
| 23 | DRAW_UI_QUADS |
| 24 | DRAW_UI_QUADS_REPLACE_IMAGE |
| 25 | DRAW_TRIANGLES |
| 26 | DRAW_UI_TRIANGLES |
| 27 | DRAW_QUADLIST_2D |
| 28 | DRAW_EMBLEM_LAYER |
| 29 | STRETCH_COMPOSITE |
| 30 | PROJECTION_SET |
| 31 | DRAW_FRAMED |
| 32 | CONSTANT_SET |
| 33 | COUNT |

`GfxCmdArray` (0x18): `{u8* cmds; int usedTotal; int usedCritical; GfxCmdHeader* lastCmd; int byteSize; int warnSize}`.

### GfxDrawSurf sort key (64 bits, low bit first)

| bits | field |
|---|---|
| 0-15 | objectId |
| 16-24 | customIndex |
| 25-29 | reflectionProbeIndex |
| 30-31 | dlightMask |
| **32-43** | **materialSortedIndex** (index into `rgp.sortedMaterials`) |
| 44-51 | primaryLightIndex |
| 52-55 | surfType |
| 56-57 | prepass |
| 58-63 | primarySortKey |

So the sort order is primarySortKey, then prepass, surface type, primary light, material, and so on. The material index
is only 12 bits (4,096). The client's table holds 0x1380 = 4,992 entries, so watch the count.

### Structs (server PDB; check sizes before trusting them on t6zm)

- **`GfxBackEndData`** (0x78D00, two of them, double-buffered):
  - `drawSurfs` and `drawSurfCount` at +0x56E80
  - `viewParms`
  - `gfxEnts` and `gfxEntCount`
  - `shaderConstantSets`
  - `textureOverrides` / `textureOverrideCount`: by the name, per-entity image overrides (the engine's own texture swap; not checked)
  - dynamic vertex and index buffers
  - `commands` (`GfxCmdArray*`) at +0x5FB28
  - `viewInfo` / `viewInfoCount`
  - `sunLight`, `shadowableLights[]`, `sunShadow`, `spotShadows`, `frameStats`
- **`GfxViewInfo`** (0xC40):
  - `viewParms`, the scene, display and scissor viewports, `sceneDef`
  - `visibleLights[]`
  - `frustumPlanes`
  - `drawList` (`GfxDrawSurfListInfo*`)
  - `input` (`GfxCmdBufInput*`)
  - `weaponViewParms`, `sonarViewParms`
  - flags: `drawInfrared`, `drawPostBlur`, ...
- **`GfxCmdBufState`** (0x67C0): the live D3D11 state while drawing.
  - samplers and textures
  - `material`, `techType`, `technique`, `pass`
  - the vertex and pixel shader constant caches
  - blend, depth-stencil and rasterizer state objects
  - the current shaders, viewport and scissor, `backEndData`
- **`GfxCmdBufSourceState`** (0x1A80): what code-constant shader arguments read from.
  - matrices, the `GfxCmdBufInput` code constants and images
  - `viewParms`, `eyeOffset`, `objectPlacement`, `materialTime`, the render-target size
- **`r_globals_t rg`** (0x13100):
  - `materialHashTable[0x1100]` at +0x174: the name lookup `Material_RegisterHandle` uses
  - `materialUsage[]`, `clientFogs`, `frameStats`, LOD parms, sun overrides
  - `drawWorld`, `drawSModels`, `drawXModels`, `drawBModels`
  - `codeImageNames`
- **`r_global_permanent_t rgp`** (server 0x4780): `sortedMaterials[]`, `needSortMaterials`, `materialCount`, then the
  built-in images and materials (`whiteImage`, `blackImage`, `defaultMaterial`, `whiteMaterial`, `additiveMaterial`,
  line, point and shadow materials, ...).
  - On t6zm the array is 0x1380 entries, so every field after it is +0xA00 (verified: needSortMaterials 0x0357DF80,
    materialCount 0x0357DF84).
- **`GfxScene`** (0x165500): fixed-size `GfxDrawSurf` arrays per pass and surface type (`bspDrawSurfs`,
  `entDrawSurfsLight`, `fxDrawSurfsEmissive`, the sun and spot shadow lists, ...), plus scene entities, models and
  brushes.
- Also dumped: `DxGlobals` (0x1C380, the D3D11 device and context), `GfxViewParms` (0x150), `GfxLight` (0x160),
  `GfxSunShadow`, `GfxSpotShadow`, `GfxWorkerData`, `GfxSceneEntity`, `GfxSceneModel`, `GfxPlacement`.

## Next steps

- Confirm `Material_RegisterHandle` (0x7333C0) on live t6zm. If it holds, a perk icon or any HUD material can be
  registered at runtime from a material we build in memory, with no fastfile.
- `GfxBackEndData.textureOverrides` looks like the engine's built-in per-entity texture swap. If so, it may be a cleaner route than
  replacing SRVs.
- More coverage: open the server exe in Ghidra with the PDB for real function bodies and compare decompiled call graphs
  instead of raw call lists. Rizin through REA can't open this target on Windows.
