# Black Ops (T5)

| Folder | What is in it |
| --- | --- |
| `headers/` | `T5.h` and `T5_Assets.h`, the BO1 asset structs with our corrections |
| `oat-bsp/` | an OAT checkout that adds a BO1 BSP dumper: `BASE_COMMIT`, `changes.patch`, `new/`. How to apply it is in the [top README](../../README.md#apply-an-oat-or-b2w-patch) |
| `notes/zombies/` | Kino der Toten entities, Five (elevators, thief, DEFCON Pack-a-Punch) |
| `notes/mp/` | Combat Training bots |
| `notes/engine/` | Fx layout, weapon colour and detail maps, sound volume groups |

The BO1 to BO2 map converter that uses these headers is in [`converter/`](../../converter/README.md). The porting
notes behind it are in [`shared/notes/bo1_to_bo2_porting.md`](../../shared/notes/bo1_to_bo2_porting.md).

Every note is listed with its title in [NOTES.md](../../NOTES.md), which also explains the `[V]` `[M]` `[I]` `[U]`
marks.
