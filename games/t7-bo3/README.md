# Black Ops III (T7)

Reverse-engineering notes for Call of Duty: Black Ops III (T7 engine), retail
Steam build (appid 311210).

- [notes/t7_assetpool_offset.md](notes/t7_assetpool_offset.md) — the XModel
  `assetPools` table base offset for the current retail build and the GfxMap read
  layout, recovered (read-only) to repair the C2M/Husky memory-based map
  extractor after a Steam auto-update moved the pool base.
- [notes/t7_xpak_format.md](notes/t7_xpak_format.md) — the `.xpak` (`KAPI` v10)
  container + blob-decompression layout, for pulling HD textures that are streamed
  from disk rather than held in memory.
- [tools/xpak/](tools/xpak) — a small offline, read-only `.xpak` reader/extractor
  (image entries → DDS) implementing that format.
- [notes/t7_fastfile_format.md](notes/t7_fastfile_format.md) — the BO3 PC fastfile
  (`TAff0000` v`0x251`) zlib block-chain container and the inline `GfxImage` layout
  (resident UI art), recovered from first principles.
- [tools/zone/](tools/zone) — offline, read-only decoders for that format: fastfile
  decompressor, inline `GfxImage` → PNG extractor, and an embedded-TTF scanner.
