# Black Ops II (T6)

The biggest folder. Two kinds of work live here: notes on how `t6zm.exe` runs (read from the exe and its scripts),
and tools built on that.

| Folder | What is in it |
| --- | --- |
| `headers/` | `T6_Assets.h`, the BO2 asset structs |
| `notes/` | the runtime of `t6zm.exe` itself: one frame from the main loop to Present (`t6_frame_walkthrough.md`), the renderer (`t6_renderer.md`), materials and techniques, Cbuf, `SV_SendServerCommand`, `playsound`. The `.tsv` files are the function and global address tables those notes cite |
| `notes/` (360 builds) | the BO2 Xbox 360 symbol builds: decrypting and loading them (`t6_360_xex_route.md`), the script built-in tables (`t6_script_builtin_tables.md`), actor/entity built-ins and the entity-type enum (`t6_actor_cmds.md`), the zombies round font (`t6_zm_round_font.md`), fall damage, slick sliding and melee (`t6_movement_slide_fall_melee.md`), grenade splash and actor repath rules (`t6_grenade_splash.md`) |
| `notes/e115/` | how the stock game behaves: vehicles (the TranZit bus), weapon camo, reticles, hero lighting, sky, pathnode links, zbarriers, struct spawns, bot goals, spread and kick, actor teams and round counts, and the script built-ins our VM still lacks |
| `t6match/` | matches functions and globals from the named server exe (`CoDMPServer_PC.exe` with its pdb) to `t6zm.exe`, which has no symbols. This is where the `.tsv` tables come from |
| `perks/` | Lua perks for BO2 Zombies: the `lua2gsc` compiler, its GSC runtime, `API.md`, examples and tests ([README](perks/README.md)) |
| `oatfork/` | our faster OAT Linker and Unlinker, plus a T6 world dumper ([README](oatfork/README.md)) |

Where to start:

- Want to know what the game does each frame? `notes/t6_frame_walkthrough.md`.
- Looking for a function address in `t6zm.exe`? `notes/t6zm_all_functions.tsv`, then `t6match/` for how it was found.
- Implementing a script built-in? `notes/t6_script_builtin_tables.md` and `notes/t6_actor_cmds.md`.
- Writing a perk? `perks/README.md`.
- Dumping a map? `oatfork/README.md`.

The full list of notes with one-line summaries is in the [E115 notes index](../../shared/notes/e115/README.md). The
`[V]` `[M]` `[I]` `[U]` marks used in every note are explained there too.
