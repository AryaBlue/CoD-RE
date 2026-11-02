# Black Ops II (T6)

The biggest folder. Two kinds of work live here: notes on how the game runs (read from the exes, the Xbox 360 symbol
builds and the scripts), and tools built on that.

| Folder | What is in it |
| --- | --- |
| `headers/` | `T6_Assets.h`, the BO2 asset structs |
| `notes/render/` | one frame from the main loop to Present, the renderer, techniques and vertex formats, materials at runtime, hero lighting, sky, reticles, weapon camo |
| `notes/engine/` | Cbuf, `SV_SendServerCommand`, `playsound`, grenade splash, fall damage and sliding, pathnode links, Fx layout, vehicles, and how we made the Xbox 360 symbol builds readable |
| `notes/script/` | the script built-in tables, actor and entity built-ins, GSC bytecode and VM semantics, built-ins our VM had to add |
| `notes/zombies/` | zbarriers, struct spawns, box models, zombie anims and wall-buys, the round font, actor teams and round counts |
| `notes/mp/` | bot goals, weapon spread and kick |
| `notes/tables/` | `.tsv` tables of `t6zm.exe` function and global addresses that the notes cite |
| `t6match/` | matches functions and globals from the named server exe (`CoDMPServer_PC.exe` with its pdb) to `t6zm.exe`, which has no symbols. The `.tsv` tables come from here |
| `perks/` | Lua perks for BO2 Zombies: the `lua2gsc` compiler, its GSC runtime, `API.md`, examples and tests ([README](perks/README.md)) |
| `oatfork/` | our faster OAT Linker and Unlinker, plus a T6 world dumper ([README](oatfork/README.md)) |

Where to start:

- What does the game do each frame? `notes/render/frame_walkthrough.md`.
- Need a function address in `t6zm.exe`? `notes/tables/t6zm_all_functions.tsv`, then `t6match/` for how it was found.
- Implementing a script built-in? `notes/script/builtin_tables.md` and `notes/script/actor_cmds.md`.
- Writing a perk? `perks/README.md`.
- Dumping a map? `oatfork/README.md`.

Every note is listed with its title in [NOTES.md](../../NOTES.md), which also explains the `[V]` `[M]` `[I]` `[U]`
marks.
