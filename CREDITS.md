# Credits

The Call of Duty reverse-engineering in this repository builds on prior community work. All of the code and notes here were written by us, from first principles, against our own legally-owned game installs. **No third-party source file is copied into this repository, and no game assets are redistributed.** Where another project's published research, struct layouts or algorithms informed ours, we cite it below and re-implemented the work independently.

## BO4 / T8 world + collision research
- **Scobalula — Greyhound / Wraith / Husky.** The ripper-verified BO4 XModel mesh stream layout and 10:10:10 vertex packing, the `.xpak` (KAPI) container, and the BO4 XModel asset-name hash (FNV-1a-64, 60-bit mask) were cross-referenced against Greyhound's open source; Husky's BO3 `GfxWorld`/`GfxSurface` reader was the lineage template for the T8 render-world layout. https://github.com/Scobalula/Greyhound · https://github.com/Scobalula/Husky
- **ate47 — atian-cod-tools (ACTS).** The offline BO4 fastfile decompression route (generic `TAff0000` reader, AES + Oodle handling, `0x27F` retail header), the BO4 asset-pool enum, and partial `GfxWorld`/`ComWorld` struct sizes were taken as reference from ACTS's open source and documentation. https://github.com/ate47/atian-cod-tools
- **COD Engine Research wiki (codresearch.dev).** The BO3 `clipMap_t` / collision-map layout was the published reference we used as the hand-RE hypothesis for the (undocumented) BO4 `clipMap_t`. https://codresearch.dev
- **OpenAssetTools (Laupetin/rattp lineage).** Used locally for T6 struct reference while bringing the T8 world structs across; **not redistributed here** (the verbatim OAT T6 header is deliberately excluded). https://github.com/Laupetin/OpenAssetTools
- **B2W / BO1MapConverter.** The downstream render-world + collision pipeline our T8 emitter targets descends from the B2W converter/linker lineage. https://github.com/Ticass/B2W
- **C2M (SHEILAN / vugi99, descended from Scobalula's Husky).** Used to export the BO4 world mesh and the material -> texture JSON that the porting method builds from. https://github.com/vugi99/C2M
- **Treyarch BO3 Mod Tools.** The build stages target the official cod2map / linker / gdtdb toolchain and copy stock prefabs and settings from the user's own install at runtime; none of it is included here.
- **Oodle (RAD Game Tools / Epic Games).** xpak and fastfile payloads are Oodle-compressed; our tools call the game's own `oo2core` DLL on the user's disk. The Oodle library is **not** included or redistributed.

## BO2 / T6 Lua perks (`games/t6-bo2/perks/`)
- **xensik — gsc-tool.** The T6 GSC compiler/decompiler the perk builds and tests run through (`-m comp -g t6 -s pc`); the stock scripts the link checker reads are decompiled with it from the user's own game files. Not included here. https://github.com/xensik/gsc-tool
- **Plutonium.** The T6 client whose `scripts\zm` loading the runtime is written for. https://plutonium.pw
- **LÖVE (LuaJIT).** Runs the live-bytecode test's real-Lua side (`tests/live/lua`). https://love2d.org
- **ate47 — bo3-source.** Decompiled stock BO3 scripts, the reference for what BO3 perk mods call when we bring their ideas to BO2. https://github.com/ate47/bo3-source

## E115 research notes, T4 / T5 / T6 (`games/*/notes/e115/`, `shared/notes/e115/`)
These notes came out of E115, our from-scratch engine that loads the user's own WaW, BO1 and BO2 installs. They quote no game script; where they lean on a tool or someone else's research, it is listed here.
- **OpenAssetTools (Laupetin, GPL-3.0).** Our zone dumper (`e115_zonedump`) is built on our vendored OAT fork. The notes rely on OAT's T4/T5/T6 struct headers and ZoneCode, zone loading, the Unlinker (rawfile scripts, string/stat tables, weapon infostrings, `--list` zone listings), the XAnim reader, the vertex/normal/image decode paths and the T6 sound loader. Nothing from OAT is copied into the notes. https://github.com/Laupetin/OpenAssetTools
- **xensik — gsc-tool (GPL-3.0).** Decompiled the stock BO2 (T6) zombies and MP scripts from the user's own fastfiles so the notes could cite file and function and paraphrase the logic. It was also the opcode/alignment reference in the scripting note. https://github.com/xensik/gsc-tool
- **ate47 — atian-cod-tools (ACTS).** Its T6 opcode map and GSC VM headers were a reference for the scripting note. The other-games note cites it for T7 GSC decompile/compile. https://github.com/ate47/atian-cod-tools
- **COD Engine Research wiki (codresearch.dev).** Its "Sound Asset" and "SABS & SABL Files" pages were the struct and checksum reference for the audio note. https://codresearch.dev
- **B2W / BO1MapConverter (Ticass/B2W lineage).** Its light-grid, lightmap, entity and hull decodes are cited (marked "[V by b2w]") in the lighting and world notes. https://github.com/Ticass/B2W
- **OpenBLOPS.** Its `R_DecodeLightGridColors` reconstruction is referenced second-hand, through B2W, in the lighting note.
- **Scobalula — Greyhound,** and **C2M (vugi99).** Named in the other-games note as the source of the BO4 rip and of the T7 GfxMap offsets. https://github.com/Scobalula/Greyhound · https://github.com/vugi99/C2M
- **Plutonium.** We read its `t4sp`/`t4mp`/`t6mp`/`t6zm` client executables statically, by disassembly only, never patched, for addresses, dvar defaults and trace masks. The WaW zones were read from the user's Plutonium install. https://plutonium.pw
- **Capstone.** Disassembled `t6zm.exe` and `BlackOps.exe`. https://www.capstone-engine.org
- **Microsoft D3DCompiler / fxc (`D3DDisassemble`).** Disassembled shader bytecode for the sky, camo, reticle, hero-lighting, water, colour-detail and lighting notes.
- **Treyarch BO1 Mod Tools.** We compared against the user's own `raw/` script copies and the `mtl_water` material template; none of them is included.
- **Libraries named in the zonedump-formats and audio notes:** nlohmann/json (https://github.com/nlohmann/json), miniaudio (https://miniaud.io), stb (https://github.com/nothings/stb), Khronos glTF-Sample-Assets Sponza (https://github.com/KhronosGroup/glTF-Sample-Assets), plus FFmpeg's xWMA demuxer and dr_flac, which are mentioned only as references.

## Licensing & compliance
Our OAT- and B2W-derived patches elsewhere in this repo are GPL-3.0, matching their upstreams. The BO4/T8 tooling is clean-room: it contains no copied third-party source. No AES keys, no proprietary binaries (Oodle, game executables, linker/exporter tools, Greyhound `.wni` data) and no extracted or decompressed game content are included in this repository — the tools operate only on files the user already owns.
