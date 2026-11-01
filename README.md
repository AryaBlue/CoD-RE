# CoD-RE

Our reverse-engineering notes and tools for Call of Duty: World at War (T4), Black Ops (T5), Black Ops II (T6),
Black Ops III (T7), Black Ops 4 (T8) and Modern Warfare 2 (IW4).

You will find struct layouts, file-format notes, OpenAssetTools (OAT) patches, small extractors and a few
converters. The OAT patches are GPL-3.0, like OAT itself. There are no game files here and no dumped assets. You
run the tools on your own install.

## Start here

- New to the repo? Read the [E115 notes index](shared/notes/e115/README.md) first. It lists every note with a one-line
  summary and explains the `[V]` `[M]` `[I]` `[U]` marks that say how sure each claim is.
- Each game folder has its own README: [WaW](games/t4-waw/README.md), [BO1](games/t5-bo1/README.md),
  [BO2](games/t6-bo2/README.md), [BO3](games/t7-bo3/README.md), [BO4](games/t8-bo4/README.md), [MW2](games/iw4-mw2/README.md).
- Long notes start with a Contents list. Click a heading to jump.
- Porting a BO1 map to BO2? Start at [converter/README.md](converter/README.md).

## Where things are

Each game has a folder under `games/`. Things that cover more than one game are in `shared/` and `converter/`.

| Folder | What is in it |
| --- | --- |
| `games/t4-waw/notes/e115/` | WaW notes from E115: zombies maps and AI, MP rules, pmove, damage, viewmodel, effects, sound |
| `games/t5-bo1/headers/` | BO1 asset struct headers we corrected (`T5.h`, `T5_Assets.h`) |
| `games/t5-bo1/oat-bsp/` | OAT checkout that adds a BO1 BSP dumper (`changes.patch` plus `new/`) |
| `games/t5-bo1/notes/e115/` | BO1 notes from E115: bots, Fx layout, colour/detail maps, sound volume groups, Kino and Five entities |
| `games/t6-bo2/headers/` | BO2 asset struct header (`T6_Assets.h`) |
| `games/t6-bo2/notes/` | BO2 Zombies runtime notes: Cbuf, server commands, sounds, materials, renderer, one frame from main loop to Present, techniques |
| `games/t6-bo2/notes/e115/` | BO2 notes from E115: vehicles, camo, reticles, lighting, sky, pathnodes, zbarriers, struct spawns, bots, spread and kick, script built-ins |
| `games/t6-bo2/t6match/` | matches functions and globals from the server exe to `t6zm.exe` |
| `games/t6-bo2/perks/` | Lua perks for BO2 Zombies: the `lua2gsc` compiler, a GSC runtime, `API.md`, examples, tests |
| `games/t6-bo2/oatfork/` | our faster OAT Linker/Unlinker fork and a T6 world dumper ([README](games/t6-bo2/oatfork/README.md)) |
| `games/t7-bo3/` | BO3 notes and small offline tools: `.xpak` and fastfile readers ([README](games/t7-bo3/README.md)) |
| `games/t8-bo4/` | BO4 offline research and a BO4 to BO3 map porting method ([README](games/t8-bo4/README.md)) |
| `games/iw4-mw2/` | MW2 notes: IWI version 8 images, the 2026 64-bit update, clipmap brushes |
| `shared/probe/` | `sizes.cpp`, an x86 `sizeof` probe (build with `b.bat`), and its output `sizes.txt` |
| `shared/tools/` | `structdiff.py` (T5 against T6 struct fields) and its output |
| `shared/notes/` | BO1 to BO2 porting notes |
| `shared/notes/e115/` | cross-game T4/T5/T6 notes from E115, plus an index of every E115 note and what the evidence marks mean |
| `shared/oat-patches/oat/` | changes to a base OAT checkout that span several games |
| `shared/oat-patches/oat_ext/` | OAT checkout that adds T4 Fx/World/Sound dumpers and a T5 world dumper |
| `converter/` | our BO1 to BO2 map converter ([README](converter/README.md)) |

An OAT patch can touch files for several games. So each OAT checkout sits under the one game it mostly serves. The
files inside its `new/` folder are already sorted per game (`Game/T4`, `Game/T5`, `Game/T6`).

Credits for every tool and piece of research we used are in [CREDITS.md](CREDITS.md).

## Apply an OAT or B2W patch

Each patch folder has a `BASE_COMMIT` (the upstream commit it was made against), a `changes.patch` and a `new/` folder.
Say your OAT checkout is `C:\src\OpenAssetTools`, this repo is `C:\src\CoD-RE`, and you want the BO1 BSP dumper:

    git -C C:\src\OpenAssetTools checkout <BASE_COMMIT>
    git -C C:\src\OpenAssetTools apply C:\src\CoD-RE\games\t5-bo1\oat-bsp\changes.patch
    xcopy /E /Y C:\src\CoD-RE\games\t5-bo1\oat-bsp\new\* C:\src\OpenAssetTools\

Then rebuild OAT as usual. You get the new dumper in `Unlinker.exe`.

If `git apply` fails, you are not on the base commit. Run `git checkout <BASE_COMMIT>` again. Read the `BASE_COMMIT`
file in the same folder as the patch you are applying, not the one from another folder.

## Refresh this repo (for us)

    C:\Python313\python.exe collect.py
    git add -A
    git commit -m "Refresh from projects"

`collect.py` copies our own RE output from the working projects. It rebuilds `shared/oat-patches/`,
`games/t5-bo1/oat-bsp/` and `converter/b2w-patch/`. It leaves `games/t6-bo2/oatfork/` alone, because that one is a
manual snapshot. It never copies game files. Run `git status` and look at what changed before you commit.

After editing a long note, run `python shared/tools/toc.py` to refresh its Contents list.
