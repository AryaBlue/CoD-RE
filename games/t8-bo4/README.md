# Black Ops 4 (T8)

Reverse-engineering notes and offline tooling for Call of Duty: Black Ops 4 (T8 engine). Everything here was worked out from first principles, offline, against the user's own installed game — no game was run and no game assets are stored in this repo. The scripts read your own install's files; they ship the format knowledge and the code, not the content.

## What is solved
- **CASC/TVFS container reading** — a from-scratch reader for BO4's local CASC (Blizzard TACT) storage: `.build.info` -> build-config -> the `.idx` bucket index -> the `data.NNN` archives, plus BLTE frame decoding, and a TVFS `vfs-root` parser (radix-trie path table -> VFS spans -> content-key table) that resolves a named file such as `zone\zm_escape.ff` back to its archive bytes. Verified by an encoding-file md5 oracle and per-chunk byte-exactness checks.
- **Fastfile decompression recipe** — how to turn an extracted `TAff0000` (version `0x27F`, BO4 retail) fastfile into its raw asset stream offline, without the packed game module, using a generic reader (AES-decrypt + Oodle block-chain).
- **KAPI xpak decode** — the BO4 `.xpak` (KAPI version `0xB`) stream package: header, 24-byte hash table, 0x80-aligned block groups and the per-block codecs (raw / LZ4 / Oodle Kraken), decoded through the game's own Oodle DLL.
- **T8 clipMap layout** — the `clipMap_t` (asset 11) brush/plane/vert layout recovered by hand (BO3 as the hypothesis template), parsed from a decompressed zone into a brush/plane collision schema.
- **GfxWorld vertex format** — the render-world layout: split position / vertex-data buffers, global u16 index buffer, per-surface ranges, and the 10:10:10 packed normal / half-float UV vertex packing (cross-checked against the ripper-verified XModel mesh format).
- **T8 XModel name hash** — the FNV-1a-64 asset-name hash (lower-cased, `\`->`/` normalised, masked to the low 60 bits) with a reference implementation and test vectors.
- **Placement transform solve** — recovering each static-model placement's origin, rotation and scale from the collision static-model array (`invScaledAxis` -> world transform), with a bounds oracle that validates a resolved name against the record's own AABB.

## What is NOT here (and why)
No game data of any kind: no fastfiles, xpaks, decompressed zones, extracted placements, collision brushes, name dictionaries, vertex/index buffers, images, models, sounds or navmeshes. No AES keys. No Oodle or other game binaries. No verbatim third-party source. This folder is the research write-up and our own tooling only; you point the tools at your own legally-owned BO4 install.

## Contents
- [`PORTING_METHOD.md`](PORTING_METHOD.md): the end-to-end, repeatable recipe for porting a BO4 map to BO3 (Mod Tools), worked out on Blood of the Dead. Start here.
- `port/`: the build-stage tools the method uses (placement matching, entity list, spawns, textures, winding/z-fight fixes, collision budgeting and decimation, collmaps, the solid-but-invisible fill, lava/sea, zones and gameplay, and the import/map/build scripts).
- `notes/` — the format write-ups.
- `tools/` — offline, read-only Python/shell: the CASC reader + extractor and its test, the xpak reader, the clipMap and GfxWorld/placement extractors, the Havok tagfile + navmesh reader, the name-hash/dictionary builder, and the render-world emitter + validator. Some scripts need paths set to your own install, and the emitter targets the external B2W / BO1MapConverter (not included).

GPL-family research lineage; see [CREDITS.md](../../CREDITS.md). Nothing in here is a copy of another project's source.
