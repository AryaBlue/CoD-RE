# Black Ops (T5)

| Folder | What is in it |
| --- | --- |
| `headers/` | `T5.h` and `T5_Assets.h`, the BO1 asset structs with our corrections |
| `oat-bsp/` | an OAT checkout that adds a BO1 BSP dumper: `BASE_COMMIT`, `changes.patch`, `new/`. How to apply it is in the [top README](../../README.md#apply-an-oat-or-b2w-patch) |
| `notes/e115/` | how the stock game behaves: Combat Training bots, Fx layout, weapon colour and detail maps, sound volume groups, Kino and Five entities |

The BO1 to BO2 map converter that uses these headers is in [`converter/`](../../converter/README.md), and the porting
notes behind it in [`shared/notes/bo1_to_bo2_porting.md`](../../shared/notes/bo1_to_bo2_porting.md).

The full list of notes with one-line summaries is in the [E115 notes index](../../shared/notes/e115/README.md). The
`[V]` `[M]` `[I]` `[U]` marks used in every note are explained there too.
