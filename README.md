# CoD-RE

Our reverse-engineering notes for Call of Duty WaW (T4), BO1 (T5), BO2 (T6), BO3 (T7) and BO4 (T8):
struct layouts, size probes, OpenAssetTools patches, binary-format notes. OAT patches
are GPL-3.0 like OpenAssetTools itself. No game files or dumped assets go in here.

Organised by game. Each `games/<game>/` folder holds the RE that is specific to one
engine; the cross-game pieces (tools and OAT checkouts that span several games, and the
BO1 → BO2 converter) live in `shared/` and `converter/`.

## `games/`

| Folder | What |
| --- | --- |
| `t5-bo1/headers/` | BO1 (T5) asset struct headers we corrected (`T5.h`, `T5_Assets.h`) |
| `t5-bo1/oat-bsp/` | OAT checkout adding the T5 BSP dumper (`changes.patch` against `BASE_COMMIT`, new files under `new/`) |
| `t6-bo2/headers/` | BO2 (T6) asset struct header (`T6_Assets.h`) |
| `t6-bo2/notes/` | T6 Zombies runtime notes: Cbuf, server commands, sounds, materials and images, renderer, a frame from main loop to Present, techniques; all t6zm function/global matches |
| `t6-bo2/t6match/` | match server-exe functions and globals to t6zm.exe by strings and call graph |
| `t6-bo2/perks/` | Lua perks for BO2 Zombies: `lua2gsc` compiler (C++ header + CLI), GSC runtime, `API.md`, examples, tests |
| `t6-bo2/oatfork/` | our optimized OAT Linker/Unlinker fork + the T6 GfxWorld/ClipMap `.bin` dumper (see its own README) |
| `t7-bo3/notes/` | BO3 (T7) RE: the XModel `assetPools` table base offset for the current retail build + GfxMap read layout (repairs the C2M/Husky memory-based map extractor) |
| `t8-bo4/` | BO4 (T8) offline RE: CASC/TVFS reader, fastfile + KAPI xpak decode, T8 clipMap/GfxWorld/placement extractors, XModel name hash — tooling only, no game assets |

## `shared/` and `converter/`

| Folder | What |
| --- | --- |
| `shared/probe/` | `sizes.cpp` (x86 `sizeof` probe, build with `b.bat`) and its output `sizes.txt` |
| `shared/tools/` | `structdiff.py` (T5 vs T6 struct field diff) and its output |
| `shared/notes/` | BO1 → BO2 porting notes |
| `shared/oat-patches/oat/` | base OpenAssetTools checkout changes (multi-game) |
| `shared/oat-patches/oat_ext/` | OAT checkout adding T4 (WaW) Fx/World/Sound dumpers and the T5 world dumper |
| `converter/` | our BO1 → BO2 map converter: `run_bo1.py`, `tools/`, and `b2w-patch/` = our changes to [Ticass/B2W](https://github.com/Ticass/B2W) (`changes.patch` against `BASE_COMMIT`, new files under `new/`) |

Each OAT checkout's `changes.patch` is a single unit that may touch shared and
several games' files, so a checkout lives under the one game it mainly serves; the
`new/` files inside it are already sorted per game (`Game/T4`, `Game/T5`, `Game/T6`).

## Updating

    E:\Documents\BO1MapConverter\python313\python.exe collect.py
    git add -A && git commit -m "Refresh from projects"

`collect.py` regenerates `shared/oat-patches/`, `games/t5-bo1/oat-bsp/` and
`converter/b2w-patch/` from the local checkouts; `games/t6-bo2/oatfork/` is a manual
snapshot and is left alone.

To re-apply an OAT or B2W patch: `git -C <checkout> checkout <BASE_COMMIT> && git -C <checkout> apply changes.patch`, then copy `new/` over the checkout.
