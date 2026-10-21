# Credits

The Call of Duty reverse-engineering in this repository builds on prior community work. All of the code and notes here were written by us, from first principles, against our own legally-owned game installs. **No third-party source file is copied into this repository, and no game assets are redistributed.** Where another project's published research, struct layouts or algorithms informed ours, we cite it below and re-implemented the work independently.

## BO4 / T8 world + collision research
- **Scobalula — Greyhound / Wraith / Husky.** The ripper-verified BO4 XModel mesh stream layout and 10:10:10 vertex packing, the `.xpak` (KAPI) container, and the BO4 XModel asset-name hash (FNV-1a-64, 60-bit mask) were cross-referenced against Greyhound's open source; Husky's BO3 `GfxWorld`/`GfxSurface` reader was the lineage template for the T8 render-world layout. https://github.com/Scobalula/Greyhound · https://github.com/Scobalula/Husky
- **ate47 — atian-cod-tools (ACTS).** The offline BO4 fastfile decompression route (generic `TAff0000` reader, AES + Oodle handling, `0x27F` retail header), the BO4 asset-pool enum, and partial `GfxWorld`/`ComWorld` struct sizes were taken as reference from ACTS's open source and documentation. https://github.com/ate47/atian-cod-tools
- **COD Engine Research wiki (codresearch.dev).** The BO3 `clipMap_t` / collision-map layout was the published reference we used as the hand-RE hypothesis for the (undocumented) BO4 `clipMap_t`. https://codresearch.dev
- **OpenAssetTools (Laupetin/rattp lineage).** Used locally for T6 struct reference while bringing the T8 world structs across; **not redistributed here** (the verbatim OAT T6 header is deliberately excluded). https://github.com/Laupetin/OpenAssetTools
- **B2W / BO1MapConverter.** The downstream render-world + collision pipeline our T8 emitter targets descends from the B2W converter/linker lineage. https://github.com/Ticass/B2W
- **Oodle (RAD Game Tools / Epic Games).** xpak and fastfile payloads are Oodle-compressed; our tools call the game's own `oo2core` DLL on the user's disk. The Oodle library is **not** included or redistributed.

## Licensing & compliance
Our OAT- and B2W-derived patches elsewhere in this repo are GPL-3.0, matching their upstreams. The BO4/T8 tooling is clean-room: it contains no copied third-party source. No AES keys, no proprietary binaries (Oodle, game executables, linker/exporter tools, Greyhound `.wni` data) and no extracted or decompressed game content are included in this repository — the tools operate only on files the user already owns.
