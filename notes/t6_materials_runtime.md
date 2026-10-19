# T6 Zombies (Plutonium t6zm.exe) - materials and images at runtime

Reversed in 2026-10 while building live texture, camo and model replacement for BO2 Zombies, and used in game on
Plutonium t6zm (x86, image base 0x400000). Struct layouts come from the dedicated server's `CoDMPServer_PC.pdb`
and match t6zm's disassembly. Offsets are hex. The full asset structs are in `headers/T6_Assets.h`; this file covers
what the running game does with them.

## Layouts used live

### Material (0x70 bytes)

| offset | field |
|---|---|
| +0x00 | `MaterialInfo info` (0x30), `info.name` at +0x00 |
| +0x30 | `char stateBitsEntry[36]` |
| +0x54 | `u8 textureCount` |
| +0x55 | `u8 constantCount` |
| +0x56 | `u8 stateBitsCount`, then stateFlags, cameraRegion, probeMipBits |
| +0x5C | `MaterialTechniqueSet* techniqueSet` |
| +0x60 | `MaterialTextureDef* textureTable` |
| +0x64 | `MaterialConstantDef* constantTable` |
| +0x68 | `GfxStateBits* stateBitsTable` |
| +0x6C | `Material* thermalMaterial` |

`Material_Duplicate` puts the copy's name right after the struct, so for a copy `info.name == (char*)mat + 0x70`.

### MaterialTextureDef (0x10 bytes)

| offset | field |
|---|---|
| +0x00 | `u32 nameHash` |
| +0x04 | `char nameStart`, +0x05 `char nameEnd` (first and last letter of the sampler name) |
| +0x06 | `u8 samplerState` |
| +0x07 | `u8 semantic` |
| +0x08 | `bool isMatureContent`, 3 bytes pad |
| +0x0C | `GfxImage* image` |

Semantics seen on stock materials: **2** colour map, **5** normal map, **8** specular map, **0xD / 0xE** the extra
slots that weapon camo materials fill from the gun (see below).

### GfxImage (0x50 bytes)

| offset | field |
|---|---|
| +0x00 | `ID3D11ShaderResourceView* basemap` (the texture the shaders sample) |
| +0x14 / +0x16 / +0x18 | `u16 width / height / depth` |
| +0x1B | `u8 streaming` |
| +0x24 | `streamedParts` (0x18 bytes), `u8 streamedPartCount` at +0x3C |
| +0x48 | `const char* name` |
| +0x4C | `u32 hash` |

- **Texture swapping:** writing another view into `basemap` changes what every material using the image draws, from
  the next frame. The game releases `basemap` when it replaces or frees it, so the new view needs its own reference.
  Keep the old one alive: the renderer may still use it this frame.
- **Streaming:** it uploads a new texture into `basemap` whenever it raises or lowers a mip level, which undoes a swap.
  Re-check on a timer and put the swap back.
- **Spotting a reused slot:** after a zone unloads, the GfxImage can be reused. Compare `name` (pointer) and `hash`
  with the values you saw.
- **New images:** an image of your own works when you copy a loaded one (0x50 bytes), set `basemap`, the size,
  `streaming = 0`, clear `streamedParts` and the count, and give it a name and hash 0. It is never streamed.

### XModel (0xF8 bytes): material handles

`+0x00 name`, `+0x04 numBones`, `+0x06 numsurfs`, `+0x20 XSurface* surfs`, **`+0x24 Material** materialHandles`**
(one per surface), `+0x28 lodInfo[4]` (0x1C each). Pointing an entry at another registered material re-skins that
surface on every instance of the model.

## Asset database

| what | t6zm address |
|---|---|
| `DB_FindXAssetHeader` | 0x0043F460 |
| `DB_FindXAssetEntry` | 0x007FC9B0 |
| `DB_GetAllXAssetOfType(int type, void** list, int max)` | 0x0069DEB0 |
| `DB_LoadXAssets` | 0x00663090 |
| DB critical section (`s_criticalSection[0x43]`, 0x18 each) | 0x02B14EC8 + 0x43*0x18 |

Asset types used: 5 xmodel, 6 material, 8 image, 31 weapon camo.

- **Structures:** `db_hashTable` is a `u16[size]` of indices into `g_assetEntryPool`. Each entry is 16 bytes:
  `{int type; void* header; u8 zoneIndex; bool inuse; u16 nextHash; u16 nextOverride; u16 usageFrame}`, and the chain
  follows `nextHash`. Hold the DB critical section while walking it.
- **Plutonium moves both arrays** into its own memory at startup. On disk the table is at 0x012F25C0 and the pool at
  0x01409058. Live they are somewhere like 0x124BD0F8 / 0x124E28F8, and that can change per launch.
- **Reading the live addresses:** Plutonium patches `DB_FindXAssetEntry` to use the moved arrays, so read them from its
  live code:
  - 0x7FC9CB `imul edx, edx, <size>`: the size is the imm32 at 0x7FC9CD.
  - 0x7FC9D3 `movzx eax, word [ecx*2 + <table>]`: the table is the disp32 at 0x7FC9D7.
  - 0x7FC9E3 `add eax, <pool>`: the pool is the imm32 at 0x7FC9E4.

## Registering a material copy at runtime

| what | t6zm address |
|---|---|
| `Material* __cdecl Material_Duplicate(Material* src, const char* name)` (starts `83 EC 0C 56 57 8B 7C 24 1C`) | 0x00733120 |
| `rgp.sortedMaterials` (`Material*[0x1380]`) | 0x03579180 |
| `rgp.needSortMaterials` | 0x0357DF80 |
| `rgp.materialCount` | 0x0357DF84 |
| sorted-table rebuild: `push 6; call DB_GetAllXAssetOfType` (`6A 06 E8 3F D3 F8 FF`) | call at 0x00710B6C (block from 0x710B5B) |

- **What `Material_Duplicate` does:** it copies a loaded material under a new name and registers the copy for drawing.
  - Run it on the game's main (client) thread, or it races the renderer's sorting.
  - The copy has its own texture table: writing new `GfxImage*` into it leaves the source material untouched.
- **Table limit:** draw surfaces reach a material through `rgp.sortedMaterials[drawSurf.materialSortedIndex]`. The
  table never shrinks within a map and holds 0x1380 entries, so stop before `materialCount` gets close.
- **Zone loads rebuild the table** (map load, gump load) at 0x710B5B:

  ```c
  count = DB_GetAllXAssetOfType(ASSET_MATERIAL, rgp.sortedMaterials, 0x1380);   // call at 0x710B6C
  rgp.materialCount = count;
  R_SortMaterials(rgp.sortedMaterials, count);                                    // reassigns every sort index
  ```

  A runtime copy is not a database asset, so it drops out of the table. Its draw surfaces then index an empty or wrong
  slot, which crashes at **0x741BA5** reading `material->techniqueSet`.
  - **Fix:** redirect the call at 0x710B6C to a wrapper that calls `DB_GetAllXAssetOfType` and then appends the live
    copies before the game sorts.
  - That runs on the game's own thread, so nothing races.

## Weapon camos

| what | t6zm address |
|---|---|
| `WeaponOptions::SetupWeaponCamoRender` `__thiscall(this, lc, float dist, Slot, uint camo, const WeaponDobjInfo*, int&)` (starts `83 EC 54 56 8B F1 8B 4C`) | 0x006EBBC0 |
| global `WeaponOptions` (`mov ecx, 0x1125F60; call 0x6EBBC0` at 0x6A1AB9) | 0x01125F60 |
| camo slot override step (replaceFlags -> semantics) | 0x006EBE40 |

| struct | layout |
|---|---|
| WeaponOptions | +0x000 `CamoLookup camoLookupTable[128]` `{int index; bool isMaterialCamo;}`, +0x400 `WeaponCamo* meleeCamo` |
| WeaponDobjInfo | +0x000 `u8 numModelMasks`, +0x00C `ModelMask[8]` `{Slot slot; bool weapon; const void* def; uint mask;}` |
| WeaponDef | +0x974 `WeaponCamo*` |
| WeaponAttachmentUnique | +0x0A4 `WeaponCamo*` |
| WeaponCamo | +0x04 / +0x08 the gun's own base images, +0x0C `WeaponCamoSet* camoSets`, +0x10 `numCamoSets`, +0x14 `WeaponCamoMaterialSet*`, +0x18 count |
| WeaponCamoSet (0x14) | +0 `GfxImage* solid`, +4 `GfxImage* pattern` |
| WeaponCamoMaterialSet (0x8) | `{uint num; WeaponCamoMaterial* materials}` |
| WeaponCamoMaterial (0x2C) | +0 `u16 replaceFlags`, +2 `u16 numBaseMaterials`, +4 `Material** baseMaterials`, +8 `Material** camoMaterials` |

- **When it runs:** `SetupWeaponCamoRender` runs every frame for each weapon being drawn. Hooking it gives you the
  camo index and draw distance of the nearest (first-person) weapon.
- **Image camos** (`isMaterialCamo == 0`) draw `camoSets[index].solid / pattern`.
- **Material camos** swap each base material for `camoMaterials[j]`. Then, for each `replaceFlags` bit, the game fills
  one camo-material slot with the gun's own texture:
  - **1** -> semantic 2 (colour)
  - **2** -> semantic 0xD
  - **4** -> semantic 0xE

  The camo design is in whichever camo-material textures are left: not overridden, not the gun's own images, and not
  normal or specular maps.

## HUD icon materials (built offline with OAT)

- **Stock perk icons** (`specialty_*_zombies`) live in each map's own zone, not in common_zm, and are 32x32 DXT5.
- **Material JSON:** technique set `trivial_9z33feqw` (in common_zm.ff and code_post_gfx_zm.ff), sortKey 40, one
  `colorMap` (semantic 2D) with clamped, linear, no-mip sampling.
  - State: alpha test gt0, srcalpha / invsrcalpha blending, no depth test or write, no culling.
  - Copying this JSON with another image name gives a working HUD material.
- **OAT Linker (v0.33) streams T6 images:** an image loaded from `images/<name>.iwi` is written only as a streamed
  reference.
  - Without `>ipak,<name>` in the zone file, the pixels are lost (the fastfile holds no data).
  - With it they go into `<name>.ipak`, which ships next to the .ff. A mod folder's .ipak loads in Plutonium.
- **IWI v27 header** (64 bytes, as OAT reads it):
  - `"IWi"`, version 27
  - `u8 format` (1 = RGBA8, 0xD = DXT5)
  - `u8 flags` (2 = no mips)
  - `u16 width, height, depth`
  - `float gamma`
  - `u8 maxGlossForMip[16]`
  - `u32 fileSizeForPicmip[8]` (offset 0x20; [0] = header + data size)

  The pixel data follows the header.

## Not known yet

- The function behind GSC `precacheshader` (find or register a material by name), and where HUD elements store their
  material. That is the missing piece for adding a material without a fastfile.
- How the game reads an image's data from a .ipak at runtime.
- `R_SortMaterials` itself and the T6 `GfxDrawSurf` sort-key layout. We call around them and haven't read them.
- Technique sets and state bits at runtime. We only borrow stock ones.
