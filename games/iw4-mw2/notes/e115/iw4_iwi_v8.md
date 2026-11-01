# IW4 (MW2) IWI version 8 images

How E115 reads MW2 `.iwi` images (the reader is `Iwi.cpp` in E115, not published here). Found 2026-11-01. Layout is
cross-checked against OpenAssetTools' IWI loader and our own T6 (v27) notes.

Tags: **[V]** read in code or data, **[I]** inferred.

## Header [V]

All values little-endian. The header is 32 bytes; image data follows at offset 32.

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 3 | magic `IWi` |
| 3 | 1 | version, 8 for MW2 |
| 4 | 4 | flags (u32) |
| 8 | 1 | format (u8) |
| 10 | 2 | width |
| 12 | 2 | height |
| 14 | 2 | depth |
| 16 | 16 | four u32 sizes, one per picmip level |

- Other versions for comparison: v6 (WaW) has the four sizes at 12 and data at 28; v13 (BO1) has a float gamma at 12,
  eight sizes at 16 and data at 48; v27 (BO2) has gamma at 12, 16 gloss bytes at 16, eight sizes at 32 and data at 64.
- Mips are stored smallest first. Each mip holds every face back to back (+x -x +y -y +z -z).
- Each picmip size is the header plus every level from the smallest up to and including that level.

## Flags [V]

- Bit 1 is "no mipmaps", the same bit as in v6/v13/v27.
- The map type moved to bits 16-17: 1 is a cube map, 2 is 3D, 3 is 1D. (v6/v13/v27 use bits 2 and 3.)
- Bit 18 marks a normal map.

## Pixel formats [V unless noted]

- The format byte uses the same values as the other games: 1 RGBA, 2 RGB, 3 luminance+alpha, 4 luminance, 5 alpha,
  6-10 wavelet variants, 0xB DXT1, 0xC DXT3, 0xD DXT5, 0xE DXN.
- Uncompressed colour is stored BGRA.
- Wavelet images (formats 6-10) decode with the same Huffman tables as WaW. Checked on the civilian suit colour
  textures in the main `.iwd` archives. The tables are not in the image; our reader finds them in a Mod Tools
  `AssetViewer.exe` (WaW or BO1), as the T4 path does.
- Colour is treated as sRGB, except that a normal-map image (bit 18) is linear. DXN normal maps are linear too.
  **[I]**: this is an assumption, the real answer lives in the material/techset.

## Where the images live [V]

MW2 keeps most images outside the zones, in the `.iwd` archives (ordinary zip files) under the install's main folder.
Zones reference them by name. So an exporter needs both: the zone for the material and image names, and the `.iwd`
for the pixels. E115 has dev modes for each (`--iwd-textures` and `--zone-images`).

## Related

- [iw4_x64_and_world.md](iw4_x64_and_world.md): the 2026 64-bit update and the world data.
