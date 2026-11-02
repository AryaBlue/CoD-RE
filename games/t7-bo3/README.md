# Black Ops III (T7)

Reverse-engineering notes and small offline tools for Black Ops III (T7 engine), retail Steam build (appid 311210).

## Notes

- [assetpool_offset.md](notes/assetpool_offset.md): the XModel `assetPools` table base offset for the current
  retail build, and the GfxMap read layout. We recovered it (read-only) to fix the C2M/Husky memory-based map
  extractor after a Steam update moved the pool base.
- [xpak_format.md](notes/xpak_format.md): the `.xpak` container (`KAPI` v10) and how its blobs decompress. Use
  it to get HD textures that stream from disk instead of sitting in memory.
- [fastfile_format.md](notes/fastfile_format.md): the BO3 PC fastfile (`TAff0000` v`0x251`), a chain of zlib
  blocks, and the inline `GfxImage` layout (the always-loaded UI art). Worked out from scratch.

## Tools

Both tools are read-only on your game files and ship no game data.

- [tools/xpak/](tools/xpak): reads an `.xpak` and writes its images as DDS.
- [tools/zone/](tools/zone): decompresses a fastfile, pulls inline images out of a zone as PNG, finds embedded fonts.

## Worked example: get the UI images out of a fastfile

Say your game is in `C:\Games\BO3`. You need Python 3 and Pillow (`pip install pillow`).

    cd games\t7-bo3\tools\zone
    python bo3_ff_dec.py "C:\Games\BO3\zone\core_frontend.ff" core_frontend.zone
    python bo3_zone_images.py core_frontend.zone out "^uie_"

The first command writes the raw zone stream. The second writes the matching images to `out\` as PNG, plus
`out\index.json` that lists everything it saw. The last argument is a name filter (a regex). Leave it out to take
every image.

If it fails:
- `bo3_ff_dec.py` rejects the file: it only reads version `0x251` fastfiles. Check you pointed it at a BO3 `.ff`.
- Some images are in `index.json` as `unsupported_format`: the script only decodes BC1/3/5/7 and RGBA8/BGRA8.
  The rest are listed but not written.
