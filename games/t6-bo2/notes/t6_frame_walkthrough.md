# T6 (BO2) - one frame, from the main loop to the pixels on screen

This walks one client frame of Black Ops II (Plutonium `t6zm.exe`) through every function that builds and presents it.

**Sources**
- **Names and call order** come from the server build `CoDMPServer_PC.exe` in the game's `pc pdb` folder. It ships the
  full client renderer with a `.map` and `.pdb`. The call graph was read straight from its code, including tail jumps
  and the dispatch tables.
- **t6zm addresses** come from `../t6match`.
- **The steps of this walk** were confirmed by hand: each function's call order was lined up against its t6zm twin,
  and the two render-command tables were compared.

**How to read the tables**
- **t6zm column, plain:** confirmed (pass M in `t6_renderer_functions.tsv` / `t6zm_all_functions.tsv`).
- **`~`:** placed by call position only.
- **`-`:** not located in t6zm yet; the server address is given.
- **Server addresses** are the `CoDMPServer_PC.exe` ones. Check bytes before hooking anything.

## The whole frame on one page

```
Com_Frame_Try_Block_Function                    main loop, once per frame
└─ SCR_UpdateScreen                             throttle / keep-alive, sync with last frame
   └─ SCR_UpdateFrame                           THE frame driver
      ├─ R_BeginFrame                           start front end; sort materials if needed
      ├─ CL_CompositeRender                     (compositing command list)
      ├─ CL_CGameRendering (per local client)
      │  ├─ CG_DrawActiveFrame                  game state -> scene
      │  │  ├─ R_ClearScene
      │  │  ├─ ... snapshots, prediction, entities -> R_AddDObjToScene / R_LinkDObjEntity
      │  │  ├─ CG_CalcViewValues, R_SetupRenderSceneViewParms
      │  │  ├─ CG_Draw2D                        HUD -> R_AddCmd* 2D commands
      │  │  └─ CG_DrawActive
      │  │     └─ CL_RenderScene
      │  │        └─ R_RenderScene              visibility, draw-surface lists, sorting
      │  │           └─ R_GenerateSortedDrawSurfs
      │  ├─ CG_Draw2dHudElems                   script HUD elements (perk icons!)
      │  └─ UI_Refresh                          menus
      ├─ SCR_DrawScreenField / CL_DrawScreen    loading screen, console, debug overlays
      ├─ R_EndFrame                             close the command list
      └─ R_IssueRenderCommands                  hand the frame to the back end
         ├─ R_SyncRenderThread / R_WaitFrontendWorkerCmds
         ├─ RB_BeginFrame
         ├─ RB_Draw3D                           every 3D view of the frame
         │  └─ RB_StandardDrawCommands          shadow maps, prepass, lit passes, post fx
         │     └─ RB_DrawLitCommandBuffer       replay worker-recorded draw lists
         │        └─ R_DrawLit -> R_DrawSurfs -> R_RenderDrawSurfListMaterial
         │           -> R_Tess* (per surface type) -> R_DrawIndexedPrimitive
         ├─ RB_CallExecuteRenderCommands        2D / UI command list
         │  └─ RB_ExecuteRenderCommandsLoop     table dispatch per command id
         ├─ Sys_RenderCompleted
         └─ RB_EndFrame
            └─ RB_SwapBuffers -> IDXGISwapChain::Present   <- what the user sees
```

### Is there a render thread?

On PC this build runs the back end inline. `R_IssueRenderCommands` calls `RB_BeginFrame`, `RB_Draw3D`,
`RB_CallExecuteRenderCommands` and `RB_EndFrame` directly, in both builds (t6zm 0x70E850 calls 0x748680, 0x748BD0 and
0x748580).

The parallelism comes from worker threads instead:
- visibility, skinning and FX run as worker commands during the front end;
- the 3D draw lists are recorded on workers into command buffers (`R_DrawLitCmd`, `R_DrawLitBspCmd`, ...);
- the back end replays them (`R_RunCommandBuffer`). By the names, these are D3D11 deferred contexts and command
  lists.

## 1. Main loop -> frame driver

| step | function | t6zm | server | what it does |
|---|---|---|---|---|
| 1 | `Com_Frame_Try_Block_Function` | 0x0088BC60 | 0x006BF540 | One iteration of the engine loop: events, server frame, client frame. Calls `SCR_UpdateScreen` at 0x88C1E6 in t6zm (the dedicated server build never calls it). |
| 2 | `SCR_UpdateScreen` | 0x00569940 | 0x00511320 | `Sys_Milliseconds`, `NET_Sleep`, `R_SyncRenderThread` (wait for the previous frame), `CG_InitScreenDimensions`, `CL_SetupViewport`, `Sys_LoadingKeepAlive`, `SND_Update`, then `SCR_UpdateFrame`. |
| 3 | `SCR_UpdateFrame` | 0x007EEDE0 | 0x00510E70 | Drives the whole frame (the table below lists what it calls, in order). t6zm has a near-copy at 0x469650 with no direct callers (another frame path, not followed). |

`SCR_UpdateFrame` in call order (server; t6zm makes the same calls, checked by alignment):

1. `Com_IsMenuLevel`, `R_GetDefaultNearClip`, dvar setup
2. **`R_BeginFrame`** (t6zm 0x00710B10)
3. demo and timescale checks, `SND_BeginFrame`, `CG_SndUpdate`
4. `CL_CompositeRender`: a separate compositing command list (`R_BeginCompositingCmdList`, clear, copy image with
   mips, resolve composite)
5. **`CL_CGameRendering`** (t6zm 0x007EE640), once per active local client (called twice, for split screen)
6. `CL_SetupScreenPlacements`, `CG_ForceFullScreenView`
7. `CG_ProcessButDontDrawActiveFrame` for clients that aren't drawn
8. `Com_RenderVoiceFrame`
9. **`SCR_DrawScreenField`**: loading screen and logo, connect screen, UI
10. `UI_DrawMouseCursor`, **`CL_DrawScreen`** (console, debug overlays; inlined in t6zm)
11. `SND_EndFrame`
12. **`R_EndFrame`** (0x00710BB0), then **`R_IssueRenderCommands`** (0x0070E850)

## 2. Front end: building the frame on the CPU

### R_BeginFrame (t6zm 0x00710B10, server 0x00A2F4C0)

It starts the front-end frame:
- `R_UpdateFrontEndDvarOptions`;
- `R_SyncRenderThread`;
- **`Material_Sort`** when `rgp.needSortMaterials` is set (see `t6_materials_runtime.md`);
- `R_SortWorldSurfaces`.

The frame's commands go into `frontEndDataOut` (a `GfxBackEndData`, t6zm 0x033ED200) through its `GfxCmdArray`.

### cgame: CL_CGameRendering -> CG_DrawActiveFrame

| function | t6zm | server | role |
|---|---|---|---|
| `CL_CGameRendering` | 0x007EE640 | 0x0050FDE0 | Per local client: extra cams, `R_BeginClientCmdList2D`, **`CG_DrawActiveFrame`**, `CL_SendCmd`, `CG_DrawExtraCamFrame`, **`CG_Draw2dHudElems`**, `UI_Refresh`, `R_AddCmdEndOfList`. |
| `CG_DrawActiveFrame` | 0x0059BAA0 | 0x004C7550 | Turns game state into a scene (list below). |
| `CG_Draw2dHudElems` | 0x00639AA0 | 0x00459B50 | Script HUD elements (`newclienthudelem`, `setshader`): this is where our perk icons draw. |
| `CG_DrawExtraCamFrame` | 0x005B2B60 | 0x004C69A0 | Extra cameras through `R_RenderExtraCam` (t6zm 0x00730250). |

`CG_DrawActiveFrame`, in order:
1. **`R_ClearScene`** (t6zm 0x0072F180)
2. `CG_ProcessSnapshots`, `CL_Input`, `CG_PredictPlayerState`, `CG_TransitionPlayerState`
3. entities: `CG_AddPacketEntities` -> `CG_ProcessEntity` / `CG_AddPacketEntity`, `R_LinkDObjEntity`
   (models reach the scene through `R_AddDObjToScene`, `R_AddBrushModelToSceneFromAngles` and the light adders)
4. `CG_UpdateViewWeaponAnim`, `CG_AddViewWeapon` (the first-person gun)
5. `CG_CalcViewValues`, **`R_SetupRenderSceneViewParms`**, `R_UpdateNonSpriteEffects` / `R_UpdateRemainingEffects`
   (FX on workers), `R_SetupVisibilityEarly`
6. screen FX state: depth of field, water sheeting, flame, poison, electrified
7. **`CG_Draw2D`**: the HUD (compass, ammo, hints, ...) as 2D render commands
8. **`CG_DrawActive`** -> **`CL_RenderScene`** -> **`R_RenderScene`**

### R_RenderScene: from scene to sorted draw lists

| function | t6zm | server |
|---|---|---|
| `CG_DrawActive` | 0x00640EB0 | 0x004398B0 |
| `CL_RenderScene` | 0x00639E20 (tail-jumps into R_RenderScene) | 0x004F09C0 |
| `R_RenderScene` | 0x00730140 | 0x00A1E280 |
| `R_GenerateSortedDrawSurfs` | 0x0072CF60 | 0x00A1AE70 |

`R_RenderScene` first runs `R_UpdateExposureValue`, `R_SetSceneParms` and `R_UpdateLodParms`. Then
`R_GenerateSortedDrawSurfs` does the real work, in order:

1. **Set up the view:** `R_AllocViewInfo`, `R_InitDrawSurfListInfo`, `R_SetupSunShadowGlobals`, **`R_SetupVisibility`**
   (dpvs culling).
2. **Per-frame shader constants:** sky, sun, fog, wind, depth of field, film, bloom, HDR, exposure, and the screen FX
   (`R_SetSkyConstants`, `R_SetSunConstants`, `R_SetFrameFog`, `R_SetBloomInfo`, `R_SetHDRControlConstants`, ...).
3. **Lights:** `R_GetCachedVisibleLights`, `R_ChooseShadowedLights`, `R_CullDynamicPointLightsInCameraView`.
4. **World:** `R_AddAllBspDrawSurfacesCameraNonlit` -> `R_SortAllBspSurfacesCamera`.
5. **Static models:** `R_AddAllStaticModelSurfacesCamera` -> `R_SortAllStaticModelSurfacesCamera`.
6. **Entities:** `R_DrawAllDynEnt`, `R_DrawAllSceneEnt`, `R_InitSceneEntDrawSurfs`, `R_AddAllSceneEntSurfacesCamera`,
   `R_FinishSceneEntDrawSurfs`, all waiting on the FX workers.
7. **Shadows:** `R_AddAllSceneEntSurfacesSunShadow`, `R_MergeAndEmitSunShadowMapsSurfs`,
   `R_GenerateAllSortedSpotShadowDrawSurfs`, `R_EmitSpotShadowMapSurfs`.
8. **Final lists:** `R_SetupDrawSurfListInfos`, `R_MergeAndEmitDrawSurfLists`, `R_SplitAndMergeDrawLists`,
   **`R_SortDrawSurfs`**, `R_FinishDecalAndEmissiveDrawSurfs`, `R_AddDrawRecord`.

Each surface becomes a 64-bit `GfxDrawSurf`. Sorting is by that key: primarySortKey, then prepass, surfType,
primaryLightIndex, materialSortedIndex, and so on (`t6_renderer.md`). The lists end up in `GfxBackEndData.drawSurfs`
and in `GfxViewInfo.drawList`.

### 2D: HUD, menus, text

Anything 2D appends a render command to the current command list:

| function | t6zm | command id |
|---|---|---|
| `R_AddCmdDrawStretchPicInternal` | 0x0070F050 | 11 |
| `R_AddCmdDrawTextInternal` | 0x0070F440 | 17 |
| `R_AddCmdDrawQuadPicInternal` | 0x00710600 | 15 |
| `R_GetCommandBuffer` | 0x0070EA40 | (allocates space in `GfxCmdArray`) |

Each command starts with `GfxCmdHeader {u16 byteCount; u8 id; u8 ui3d}`.

### R_EndFrame (t6zm 0x00710BB0, server 0x00A2E4A0)

Flushes debug data and appends the end-of-list command (`R_GetCommandBuffer`). After this the frame's CPU side is
complete.

## 3. Hand-off: R_IssueRenderCommands (t6zm 0x0070E850, server 0x00A2F1E0)

In order:
1. `R_DrawRecordFrame`
2. **`R_SyncRenderThread`** (0x0070E780)
3. **`R_WaitFrontendWorkerCmds`**: every worker command of the front end must finish
4. `R_UpdateSkinCacheUsage`
5. **`RB_BeginFrame`** (~0x00747BC0): `R_Cinematic_UpdateFrame` (Bink video), dvar changes
6. **`RB_Draw3D`** (0x00748680), all 3D views
7. **`RB_CallExecuteRenderCommands`** (0x00748BD0), the 2D list, inside a critical section
   (`Sys_EnterCriticalSection` 0x0042A630 / `Sys_LeaveCriticalSection` 0x00596EB0)
8. **`Sys_RenderCompleted`** (0x0057E760)
9. **`RB_EndFrame`** (0x00748580), also inside the lock

## 4. Back end, 3D: RB_Draw3D

`RB_Draw3D` (t6zm 0x00748680) -> `RB_Draw3DInternal` (inlined in t6zm) picks the draw method, then tail-jumps:
- **`RB_StandardDrawCommands`** (t6zm 0x007318C0, server 0x00A27AE0): normal rendering;
- `RB_FullbrightDrawCommands`: `r_fullbright`;
- `RB_DebugShaderDrawCommands`: debug shader views.

### RB_StandardDrawCommands: the render passes, in order

This sequence lines up call for call between the two builds.

1. **UI3D and sonar:** `RB_UI3D_RenderToTexture` (t6zm 0x00738500) renders in-world screens to textures;
   `RB_SonarRenderToTexture`.
2. **Shadow maps:** `RB_SunShadowMaps`, `RB_SpotShadowMaps` (each `R_RunCommandBuffer` -> `R_DrawSunShadowMap` /
   `R_DrawSpotShadowMap`).
3. **Clear:** `RB_StandardDrawCommands_ClearScreen` (`R_GetClearColor`, `R_ClearScreen`).
4. **Depth prepass and opaque:** `RB_DrawLitCommandBuffer` (t6zm 0x007315B0) and `RB_DrawDepthPrepassCommandBuffer`
   (0x007741B0), then five more `RB_DrawLitCommandBuffer` calls. These replay the lit draw lists the workers recorded
   (opaque bsp, static models, entities, ...).
5. **Misc buffers:** `RB_DrawMiscCommandBuffer` (0x007316D0) x2.
6. **Resolve and SSAO:** `R_Resolve` (0x0073FF40), `R_ResolveFloatZ` (copy scene and depth), `RB_SSAO` (0x00766EB0).
7. **Transparent and emissive:** six more `RB_DrawLitCommandBuffer` calls (lit transparent, quasi-opaque, emissive,
   decals, ...), then `R_ResolveFloatZ` again.
8. **Alpha and misc:** `RB_SetFrameBufferAlpha`, `RB_DrawMiscCommandBuffer`.
9. **Sun and coronas:** `R_BeginView`, `RB_DrawOcclusionQueries`, **`RB_DrawSun`**, `RB_DrawCoronas`,
   `R_ResolveDistortion`.
10. **FX and superflares:** `RB_DrawMiscCommandBuffer` x4, **`R_DrawSuperflare`** (0x00731110) x2.
11. **Waypoints:** `RB_DrawWaypoints` (0x00731790), the 3D objective markers.
12. **Post blur:** `R_DrawPostBlur` (0x00731090).
13. **`RB_EndSceneRendering`** (0x00730AB0): debug lines and collision drawing.
14. **`RB_BloomLDR`** (0x00767DE0): bloom, TXAA, HDR depth of field, the vision-set LUT (`RB_CreateVisionLut`),
    `RB_AdditionalPostFX`.

### How one draw list becomes GPU draw calls

```
RB_DrawLitCommandBuffer        R_WaitDrawWorkerCmdsOfType -> R_RunCommandBuffer (replay) -> R_InitContext
  (recorded earlier on a worker by R_DrawLitCmd:
     R_DrawLit x5, R_DrawSonar, R_DrawLitQuasiOpaque, R_DrawTrans, R_DrawTransPostFX,
     R_DrawEmissiveOpaque, R_DrawEmissiveFX, R_DrawViewmodelFX, R_DrawViewModelTrans)
R_DrawLit                      R_InitCmdBufSourceState, R_SetRenderTargetSize, R_SetViewportStruct, R_DrawCall(callback)
R_DrawSurfs                    R_Set3D, viewport, R_SetCustomCodeConstants, then per material:
  R_RenderDrawSurfListMaterial   RB_ShaderConstantSetFromDrawSurf
                                 R_SetTechnique  (R_GetTechType, R_SetMaterial, R_SetPrepassMaterial)
                                 R_UpdateMaterialTime
                                 R_SetupPass     (R_SetState = blend/depth/raster, R_SetPassShaderStableArguments)
                                 -> surface-type table (16 entries, server 0x00D1D748), indexed by GfxDrawSurf.surfType:
```

| surfType | tessellation function |
|---|---|
| 0, 1 | `R_TessTrianglesList` (bsp triangles) |
| 2, 3 | `R_TessStaticModelRigidList` |
| 4 | `R_TessStaticModelSkinnedDrawSurfList` |
| 5 | `R_TessBModel` (brush models) |
| 6, 7 | `R_TessXModelRigidDrawSurfList` |
| 8 | `R_TessXModelRigidSkinnedDrawSurfList` |
| 9, 10 | `R_TessXModelSkinnedDrawSurfList` (characters, zombies, the view model) |
| 11 | `R_TessCodeMeshList` (FX code meshes) |
| 12 | `R_TessMarkMeshList` (decals, marks) |
| 13 | `R_TessParticleCloudList` |
| 14 | `R_TessRopeMeshList` |
| 15 | `R_TessGlassMeshList` |

All of them end in **`R_DrawIndexedPrimitive`** (server 0x00A8DB70), the one place a mesh becomes a D3D11 indexed draw.
Batched 2D and FX geometry goes `RB_EndTessSurface` -> `RB_DrawTessSurface` -> **`R_DrawTessTechnique`**, which runs
these in order:
- `R_SetupPass`
- `R_UpdateVertexDecl`
- `R_SetupPassCriticalPixelShaderArgs`
- `R_SetStreamSource`
- `R_SetupPassPerObjectArgs` / `PerPrimArgs`
- `R_DrawIndexedPrimitive`

The live D3D state while drawing is `GfxCmdBufState` (material, technique, pass, shaders, samplers, blend, depth and
raster objects); code shader constants come from `GfxCmdBufSourceState` (layouts in `t6_renderer_structs.txt`).

## 5. Back end, 2D: RB_CallExecuteRenderCommands

`RB_CallExecuteRenderCommands` (t6zm 0x00748BD0) does three things:
1. **Sets up:** `RB_Draw3DCommon` (tail-jumps to `RB_StandardDrawCommandsCommon`: scene compositing, debug text and
   overlays), `RB_UI3D_RenderToTexture`, the render target, `RB_InitSceneViewport`, UI3D and QR-code constants.
2. **Runs the commands:** **`RB_ExecuteRenderCommandsLoop`** (t6zm 0x007485D0, server 0x00A5A7E0).
3. **Flushes:** the last tess batch (`RB_EndTessSurface`).

The loop walks the frame's `GfxCmdArray`. For each `GfxCmdHeader` it calls `handler[id]` from a table of 32 function
pointers:
- **server:** entry for id 1 at 0x00D1D78C, base 0x00D1D788;
- **t6zm:** id 1 at 0x00D1BE94, indexed from 0x00D1BE90 by code at 0x0074866B.

| id | command | t6zm handler | server handler |
|---|---|---|---|
| 1 | SET_CUSTOM_CONSTANT | 0x00744270 | `RB_SetCustomConstantCmd` 0x00A56130 |
| 2 | SET_MATERIAL_COLOR | 0x007442C0 | `RB_SetMaterialColorCmd` 0x00A56170 |
| 3 | SAVE_SCREEN | 0x00742570 (shared stub) | 0x00A54210 (shared stub) |
| 4 | SAVE_SCREEN_SECTION | 0x00742570 (shared stub) | 0x00A54210 (shared stub) |
| 5 | CLEAR_SCREEN | 0x007422E0 | `RB_ClearScreenCmd` 0x00A53FA0 |
| 6 | BEGIN_VIEW | 0x00744320 | `RB_BeginViewCmd` 0x00A561D0 |
| 7 | SET_VIEWPORT | 0x00744360 | `RB_SetViewportCmd` 0x00A56210 |
| 8 | SET_SCISSOR | 0x007443B0 | `RB_SetScissorCmd` 0x00A56250 |
| 9 | RESOLVE_COMPOSITE | 0x00744430 | `RB_ResolveCompositeCmd` 0x00A562B0 |
| 10 | PC_COPY_IMAGE_GEN_MIP | 0x007444C0 | `RB_PCCopyImageGenMIPCmd` 0x00A56310 |
| 11 | STRETCH_PIC | 0x00740210 | `RB_StretchPicCmd` 0x00A51880 |
| 12 | STRETCH_PIC_FLIP_ST | 0x007402A0 | `RB_StretchPicCmdFlipST` 0x00A51940 |
| 13 | STRETCH_PIC_ROTATE_XY | 0x00740320 | `RB_StretchPicRotateXYCmd` 0x00A519D0 |
| 14 | STRETCH_PIC_ROTATE_ST | 0x00740630 | `RB_StretchPicRotateSTCmd` 0x00A51D30 |
| 15 | DRAW_QUAD_PIC | 0x00740900 | `RB_DrawQuadPicCmd` 0x00A52050 |
| 16 | DRAW_FULL_SCREEN_COLORED_QUAD | 0x007412D0 | `RB_DrawFullScreenColoredQuadCmd` 0x00A52A70 |
| 17 | DRAW_TEXT_2D | 0x007479A0 | `RB_DrawText2DCmd` 0x00A5A260 |
| 18 | DRAW_TEXT_3D | 0x00747B20 | `RB_DrawText3DCmd` 0x00A5A430 |
| 19 | BLEND_SAVED_SCREEN_BLURRED | 0x00742570 (shared stub) | 0x00A54210 (shared stub) |
| 20 | BLEND_SAVED_SCREEN_FLASHED | 0x00742570 (shared stub) | 0x00A54210 (shared stub) |
| 21 | DRAW_POINTS | 0x00742B90 | `RB_DrawPointsCmd` 0x00A54890 |
| 22 | DRAW_LINES | 0x00743440 | `RB_DrawLinesCmd` 0x00A55200 |
| 23 | DRAW_UI_QUADS | 0x00743680 | `RB_DrawUIQuadsCmd` 0x00A55440 |
| 24 | DRAW_UI_QUADS_REPLACE_IMAGE | 0x00743AE0 | `RB_DrawUIQuadsReplaceImageCmd` 0x00A55940 |
| 25 | DRAW_TRIANGLES | 0x00744210 | `RB_DrawTrianglesCmd` 0x00A560C0 |
| 26 | DRAW_UI_TRIANGLES | 0x00743ED0 | `RB_DrawUITrianglesCmd` 0x00A55D80 |
| 27 | DRAW_QUADLIST_2D | 0x00740AC0 | `RB_DrawQuadList2DCmd` 0x00A52260 |
| 28 | DRAW_EMBLEM_LAYER | 0x00741100 | `RB_DrawEmblemLayer` 0x00A52860 |
| 29 | STRETCH_COMPOSITE | 0x00741230 | `RB_StretchCompositeCmd` 0x00A52980 |
| 30 | PROJECTION_SET | 0x00747B60 | `RB_ProjectionSetCmd` 0x00A5A470 |
| 31 | DRAW_FRAMED | 0x007413B0 | `RB_DrawFramedCmd` 0x00A52BF0 |
| 32 | CONSTANT_SET | 0x007417A0 | `RB_ConstantSetCmd` 0x00A53030 |

- **Shared stubs:** ids 3, 4, 19 and 20 share one handler in both builds. The linker folded identical bodies, and the
  server map names it `RB_BlendSavedScreenFlashedCmd`. On PC these are likely empty.
- **Batching:** handlers batch quads into the tess buffer, which is flushed with `RB_EndTessSurface` and
  `R_DrawTessTechnique` as above.
- **Hook point:** this table is the cleanest place to observe or extend 2D drawing (HUD, menus, perk icons).

## 6. Present: RB_EndFrame -> RB_SwapBuffers

| function | t6zm | server |
|---|---|---|
| `RB_EndFrame` | 0x00748580 | 0x00A5A750 |
| `RB_SwapBuffers` | 0x00748350 | 0x00A5A510 |

`RB_SwapBuffers` latches dvars, releases sampler states, may warm shaders (`Material_WarmAllShaders`), handles NVIDIA
stereo, and presents. The present itself:
- **t6zm:** `call eax` at **0x007483C5**. It loads the swap chain from the pointer array at 0x035B5D94 (indexed),
  takes vtable slot 0x20, and calls `this->Present(syncInterval, 0)`.
- **server:** the same at 0x00A5A59D; the swap chain comes from global 0x08412314.

Slot 8 (0x20) of `IDXGISwapChain` is `Present`. This is the moment the finished image reaches the screen, and the
point overlays (and Plutonium) hook.

## Hook ideas

- **Perk icons / HUD:** `CG_Draw2dHudElems` -> `R_AddCmdDrawStretchPicInternal` -> command 11 ->
  `RB_StretchPicCmd`. A material registered with `Material_RegisterHandle` (t6zm 0x7333C0, `t6_renderer.md`) draws
  through this path.
- **Our own overlay:** draw with D3D11 right before the `Present` call at 0x007483C5, or add commands to the list
  before `R_EndFrame`.
- **Per-frame hook that is always on the main thread:** `SCR_UpdateFrame` (0x7EEDE0) or `R_BeginFrame` (0x710B10).
