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
