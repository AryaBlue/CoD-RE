# zonedump texture gaps: BO1 "no colour map", BO2 "no pixel data"

2026-10-26. Tags: **[V]** verified (path:line or a measurement), **[I]** inferred.
OAT = `<OAT checkout>` (our vendored OpenAssetTools fork). Probe and dumps = throwaway files in `<scratch>`
(`probe\probe.cpp`, built 32-bit against the same OAT libs as zonedump). Nothing here is committed.

## TL;DR

Both gaps have one cause. **The assets are references.** The map zone lists `,name` and stores only a placeholder.
The real definition lives in a shared zone that the game loads first. zonedump loads only the map zone, so:

- BO1: OAT's converter reads the placeholder material, whose texture table is empty, and gets no colour map.
- BO2: `ImageSource` skips reference images. The real image isn't in any zone zonedump has loaded.

The fix is to load the dependency zones before the map. Then:

- re-point xmodel material handles from placeholders to the real materials;
- index images from every loaded zone.

Measured with the probe:

- BO1 Kino: loading `code_post_gfx`, `common`, `common_zombie` and `English/en_zombie_theater` first takes materials
  without a colour map from **57 to 0**. 244 pointers resolve with 0 left unresolved, and all 324 colour images decode,
  49 of them from a dependency zone.
- BO2 Nuked: all 5 missing images decode.

## 1. BO1 zombie_theater.ff: "material X has no colour map"

- **The 115 warnings are 57 distinct materials** [V]: `<export root>/t5.log`, measured with `sort -u`.
- **All 57 are references in zombie_theater.ff** [V].
  - `Unlinker --list zombie_theater.ff` prints them as `material, ,mc/...`. The leading comma marks a reference
    (`OAT/src/ZoneCommon/Pool/XAssetInfo.cpp:96-99`, `IsReference()` = name starts with `,`).
  - The zone has 133 reference materials, and all 57 are among them.
- **Not a semantic, name-hash or slot problem** [V].
  - The real `mc/mtl_monkey_bomb_metal` (dumped from common_zombie.ff with `Unlinker --include-assets material`) has
    `colorMap` = `~-gmonkey_bomb_c` with semantic colorMap (2).
  - It also has normalMap, specularMap, and a color7Map detail slot (`weapon_camo_neutral`). techset
    `mc_l_sm_r0c0n0s0sc0x0_clrdtl_hero`.
  - OAT picks the colour map by semantic only: 2 or 0xC-0x1B on T5
    (`OAT/src/ObjWriting/XModel/XModelToCommonConverter.cpp.template:54-68`). That works once it sees the real material.
- **Why OAT sees nothing** [V by measurement, mechanism I].
  - `XModel::materialHandles[i]` (`OAT/src/Common/Game/T5/T5_Assets.h:692`) points at the placeholder the zone loader made
    for the reference.
  - `GetMaterialColorMap` loops over `textureCount`, which is 0 for that placeholder, so `colorMapName` stays empty
    (`XModelToCommonConverter.cpp.template:320-328`).
  - `AssetName()` strips the comma, which is why the log shows the bare name.
- **OAT's own `--load` doesn't fix it** [V]. I ran `Unlinker -l common_zombie.ff zombie_theater.ff
  --include-assets xmodel --model-format GLTF`. zombie_monkey_bomber's glTF still has no monkey_bomb images, the same as
  without `-l`. Loading a zone first doesn't re-link pointers in a zone loaded later, so zonedump has to do it.
- **Where the definitions live** [V]: I listed every zone in `<game install>/zone/Common` (66 .ff).
  - common_zombie.ff defines 46, common.ff 3, code_post_gfx.ff 1. Other zones overlap them.
  - Probe with `code_post_gfx, common, common_zombie` loaded before Kino: 144 surface material pointers patched, and
    materials without a colour map drop from 57 to 10.
  - `mc/lambert1` and others resolve as well.
- **The 10 left over are in none of the 66 Common zones** [V]. They're in the localised zone (see §3).
  - `mc/mtl_c_ger_honorguard_zombie_{body1,linen,lthr,metal}`
  - `mc/mtl_c_ger_richtofen_body{,_linen,_lthr,_metal}`
  - `mc/mtl_zombie_teleporter_2`
  - `mc/zombie_logo`
- **WaW (13 warnings) and BO2 (4: `mc/lambert1`, `mc/mtl_x2icon_gold`) look the same** [V for BO2: both are
  `material, ,...` refs in zm_nuked.ff. I for WaW, not checked].

## 2. BO2 zm_nuked.ff: "no pixel data found"

- **The 46 warnings are 5 distinct images** [V]: `<export root>/t6.log`, `uniq -c`.

  | image | warnings |
  |---|---|
  | `~-glimbs_c` | 39 |
  | `~-ggrey` | 3 |
  | `mtl_t6_attach_optic_reticle_noise` | 2 |
  | `~-gzombie_eye` | 1 |
  | `noise2` | 1 |

- **All 5 are references in zm_nuked.ff** (`image, ,name`; 40 image refs in the zone) [V]. `ImageSource` indexes only
  non-reference images of the map zone (`tools/zonedump/main.cpp:130-135`). It then falls back to a loose `.iwi`
  (`main.cpp:171-176`), which doesn't exist for T6. So it's neither ipak coverage nor highmip.
- **Their definitions** (probe, all 24 `zone/all/*.ipak` added to `IIPak::Repository`) [V]:

  | image | defined in | size | streaming | streamedPartCount | loadDef.resourceSize | loadDef.format (DXGI) | decodes |
  |---|---|---|---|---|---|---|---|
  | `~-glimbs_c` | common_zm | 1024x1024 | 1 | 1 | 0 | 77 (BC3) | yes |
  | `~-ggrey` | code_post_gfx_zm | 16x16 | 2 | 1 | 0 | 71 (BC1) | yes |
  | `mtl_t6_attach_optic_reticle_noise` | common_zm | 128x128 | 2 | 1 | 0 | 77 | yes |
  | `~-gzombie_eye` | common_zm | 32x32 | 2 | 1 | 0 | 71 | yes |
  | `noise2` | common_zm | 512x512 | 2 | 1 | 0 | 71 | yes |

  - All are ordinary single-part ipak streams: an empty loadDef, with pixels found through (hash, streamedParts[0].hash).
  - `~-ggrey` is also defined in zm_nuked_patch.ff, and `mtl_t6_attach_optic_reticle_noise` and `~-glimbs_c` in
    common.ff [V, `--list`].
- **The material side needs nothing on T6** [I, consistent with the logs]. These materials are defined in zm_nuked
  itself, so OAT already reads the colour map's name from the image placeholder. Only the pixel lookup fails.

## 3. English zones (the 10 leftover BO1 materials)

- **All 10 are defined in `zone/English/en_zombie_theater.ff`** [V]: `--list` over all 66 `zone/English/*.ff`.
  - `en_zombietron.ff` and `en_zombie_pentagon.ff` hold some of the honorguard ones too.
  - [I] Treyarch evidently put character models in the localised zone (Richtofen's head xmodel/materials are in
    zombie_theater.ff itself).
- Probe with en_zombie_theater.ff loaded as a fourth dep: **244 patched, 0 unresolved, 0 materials without a colour
  map, 324/324 colour images decoded** [V].
- So a map's dependency set is `code_post_gfx`, `common`, `common_zombie` and `<lang>/en_<map>`, in the same order as
  the probe [V for Kino]. [I] I didn't check the game's real load order, or whether duplicate definitions across these
  zones differ.

## 4. Proposed change (not applied)

- Add `--load <zone.ff>` (repeatable), loaded before the map zone.
- Patch xmodel material handles that are references to the loaded definition.
- Build `ImageSource` from every loaded zone. The first definition wins, in load order: deps first, then the map
  zone's own copy overrides them.
- The probe implements this (`patchMaterials`, `defined()` in `probe.cpp`) and produced the numbers above. One
  difference: the probe keeps the *first* definition (`emplace`), while the diff lets later zones override. For the
  Kino and Nuked sets both give the same counts [I: not re-measured with override order].

Usage:
- `--load code_post_gfx.ff --load common.ff --load common_zombie.ff --load ../English/en_zombie_theater.ff` for BO1 zm
- `--load code_post_gfx_zm.ff --load common_zm.ff` for BO2 zm
- A per-game default list can come later.

```diff
--- a/tools/zonedump/main.cpp
+++ b/tools/zonedump/main.cpp
@@ includes
 #include "Game/IGame.h"
+#include "Game/T4/T4.h"
+#include "Game/T5/T5.h"
+#include "Game/T6/T6.h"
 #include "Image/ImageCommon.h"
@@ class ImageSource
-        ImageSource(Zone& zone, ISearchPath& searchPath) : m_search(searchPath), m_converter(image::ToCommonConverter::GetForGame(zone.m_game_id))
+        // zones in load order (deps first, map last): a later definition replaces an earlier one, like the game
+        ImageSource(const std::vector<Zone*>& zones, ISearchPath& searchPath)
+            : m_search(searchPath), m_converter(image::ToCommonConverter::GetForGame(zones.back()->m_game_id))
         {
-            const IGame* game = IGame::GetGameById(zone.m_game_id);
-            for (const XAssetInfoGeneric* info : zone.m_pools)
-                if (!info->IsReference() && std::string(game->GetAssetTypeName(info->m_type).value_or("")) == "image")
-                    m_images[info->m_name] = info;
+            for (Zone* zone : zones)
+            {
+                const IGame* game = IGame::GetGameById(zone->m_game_id);
+                for (const XAssetInfoGeneric* info : zone->m_pools)
+                    if (!info->IsReference() && std::string(game->GetAssetTypeName(info->m_type).value_or("")) == "image")
+                        m_images[info->m_name] = info;
+            }
         }
@@ before exportXModels
+    // a map zone only references shared materials (,name -> empty placeholder); point the xmodel at the
+    // definition from a loaded dep zone so OAT sees its texture table
+    template <class XModel, class Material>
+    int resolveMaterials(Zone& map, const std::vector<Zone*>& deps)
+    {
+        const IGame* game = IGame::GetGameById(map.m_game_id);
+        std::map<std::string, Material*> defs;
+        for (Zone* zone : deps)
+            for (const XAssetInfoGeneric* info : zone->m_pools)
+                if (!info->IsReference() && std::string(game->GetAssetTypeName(info->m_type).value_or("")) == "material")
+                    defs[info->m_name] = static_cast<Material*>(info->m_ptr);
+        int patched = 0;
+        for (XAssetInfoGeneric* info : map.m_pools)
+        {
+            if (info->IsReference() || std::string(game->GetAssetTypeName(info->m_type).value_or("")) != "xmodel")
+                continue;
+            auto* model = static_cast<XModel*>(info->m_ptr);
+            for (unsigned i = 0; i < model->numsurfs; ++i)
+            {
+                Material*& mat = model->materialHandles[i];
+                if (mat && mat->info.name && mat->info.name[0] == ',')
+                    if (auto it = defs.find(mat->info.name + 1); it != defs.end())
+                        mat = it->second, ++patched;
+            }
+        }
+        return patched;
+    }
+
-    int exportXModels(Zone& zone, const std::string& which, const fs::path& dir, ISearchPath& searchPath)
+    int exportXModels(Zone& zone, const std::vector<Zone*>& deps, const std::string& which, const fs::path& dir, ISearchPath& searchPath)
     {
@@
-        ImageSource images(zone, searchPath);
+        int patched = 0;
+        switch (zone.m_game_id)
+        {
+        case GameId::T4: patched = resolveMaterials<T4::XModel, T4::Material>(zone, deps); break;
+        case GameId::T5: patched = resolveMaterials<T5::XModel, T5::Material>(zone, deps); break;
+        case GameId::T6: patched = resolveMaterials<T6::XModel, T6::Material>(zone, deps); break;
+        default: break;
+        }
+        if (!deps.empty())
+            std::printf("deps: %zu zones, %d xmodel material references resolved\n", deps.size(), patched);
+        std::vector<Zone*> all = deps;
+        all.push_back(&zone);
+        ImageSource images(all, searchPath);
@@ main()
+    // --load <zone.ff> (any number, anywhere after the zone path): shared zones the map references, loaded
+    // first and kept alive for the whole run
+    std::vector<std::unique_ptr<Zone>> depZones;
+    std::vector<Zone*> deps;
+    std::vector<std::string> args{argv, argv + argc};
+    for (size_t i = 2; i + 1 < args.size();)
+        if (args[i] == "--load")
+        {
+            auto dep = ZoneLoading::LoadZone(args[i + 1], std::nullopt);
+            if (!dep)
+            {
+                std::fprintf(stderr, "error: %s: %s\n", args[i + 1].c_str(), dep.error().c_str());
+                return 1;
+            }
+            deps.push_back(dep->get());
+            depZones.push_back(std::move(*dep));
+            args.erase(args.begin() + i, args.begin() + i + 2);
+        }
+        else
+            ++i;
+    // the rest of main() reads args[] instead of argv[]/argc (mode = args[2], --xmodel args[3..4], --game args[5..6])
     auto zone = ZoneLoading::LoadZone(path, std::nullopt);
@@
-        return exportXModels(z, argv[3], fs::path(argv[4]), search);
+        return exportXModels(z, deps, args[3], fs::path(args[4]), search);
```

Notes on the diff:
- `GameId::T4/T5/T6` and the `T*::XModel`/`T*::Material` names match OAT's `Common/Game/T*/T*.h` (`AssetXModel`,
  `AssetMaterial`) [V]. `numsurfs` and `materialHandles` are at `T4_Assets.h:615,624`, `T5_Assets.h:683,692` and
  `T6_Assets.h:561,570` [V].
- The probe included the T5 and T6 headers in one TU and built cleanly. Adding T4 is [I].
- Dep zones must stay loaded until export ends: the patched pointers and the ImageSource infos point into them.
- The BO2 ipaks are already added with `&z` as the owner. ImageToCommonConverter searches the whole repository
  (`OAT/src/ObjWriting/Image/ImageToCommonConverter.cpp.template:127-139`), so dep-zone images find them [V, probe].
- Patching only touches the in-memory copy of the zone. Nothing is written back.
