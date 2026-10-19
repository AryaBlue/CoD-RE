# CoD-RE

Our reverse-engineering notes for Call of Duty WaW (T4), BO1 (T5) and BO2 (T6):
struct layouts, size probes, OpenAssetTools patches, binary-format notes. OAT patches are GPL-3.0 like OpenAssetTools itself.
No game files or dumped assets go in here.

| Folder | What |
| --- | --- |
| `headers/` | T5/T6 asset struct headers we corrected, plus `sizes.cpp` (x86 sizeof probe, build with `b.bat`) and its output `sizes.txt` |
| `tools/` | `structdiff.py` (T5 vs T6 struct field diff) and its output |
| `oat-patches/<tree>/` | our changes to each local OpenAssetTools checkout: `changes.patch` against `BASE_COMMIT`, new files under `new/` |
| `converter/` | our BO1 → BO2 map converter: `run_bo1.py`, `tools/`, and `b2w-patch/` = our changes to [Ticass/B2W](https://github.com/Ticass/B2W) (`changes.patch` against `BASE_COMMIT`, new files under `new/`) |
| `perks/` | Lua perks for BO2 Zombies: `lua2gsc` compiler (C++ header + CLI), GSC runtime, `API.md`, examples, tests |
| `notes/` | BO1 → BO2 porting notes, and T6 Zombies runtime notes (Cbuf, server commands, sounds, materials and images) |

## Updating

    E:\Documents\BO1MapConverter\python313\python.exe collect.py
    git add -A && git commit -m "Refresh from projects"

To re-apply an OAT or B2W patch: `git -C <checkout> checkout <BASE_COMMIT> && git -C <checkout> apply changes.patch`, then copy `new/` over the checkout.
