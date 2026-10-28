# Other CoDs: what E115 could add next

A survey for the "one engine, many CoDs" roadmap (E115 architecture doc, D4), written 2026-10-26. It checks what's
on disk, what OAT already loads, how each game's formats differ from T4-T6, and what each would cost against the
current zonedump outputs. No game was run.

Tags:
- **[V]**: read in source or headers, cited.
- **[M]**: measured on the files on this machine.
- **[I]**: inferred.

Sources:
- `OAT/` is `<OAT checkout>/` (our vendored OpenAssetTools fork).
- `ACTS/` is the atian-cod-tools README (https://github.com/ate47/atian-cod-tools).
- `RE/` is this repo's `games/` folder.

## What's on disk [M]

| game | engine | location | state |
|---|---|---|---|
| WaW | T4 | `<game install>` (Plutonium T4) | full, already supported |
| BO1 | T5 | `<game install>` | full, already supported |
| BO2 | T6 | `<game install>` | full, already supported |
| **BO3** | **T7** | `<game install>` (124 GB) | **full** |
| | | `zone\`: 252 `.ff`, 108 `.fd`, 275 `.xpak`; `zone\snd\{all,en}\`: 163 `.sabl` + 163 `.sabs` | |
| | | Mod Tools (Steam app 455130) (`model_export`, `map_source`, `art_assets`, `gdtdb`, `AssetWorks`) | |
| MW2 | IW4 | `<game install>` (549 MB) | **IW4x client only**: 43 `.ff`, all `iw4x_*`/`patch_*`/`*_load`. No base-game map zones (largest is a 4 MB team-model patch). `zone\english` holds one 32 KB playlist ff, header `IWff0100` |
| CoD4 | IW3 | a `cod4\` subfolder | **configs only** (12 MB, 0 `.ff`) |
| MW3 | IW5 | none | **not installed** (only mod iwds, not the game) |
| IW | IW7 | `<game install>` (1.3 GB) | **partial**: `main\toc*/data*.dcache` only, no zones |
| BO4 | T8 | `<rip root>/black_ops_4` | **a rip, not the game**: 2,432 `.semodel` + `XMODEL_EXPORT` + `.mel`, 186k `.png`, 3k `.txt` (Greyhound output) |

## OAT support [V]

- OAT supports IW3, IW4, IW5, QOS, T4, T5 and T6 (`OAT/README.md:12-20`).
  - Our fork has zone loaders for all seven (`OAT/src/ZoneLoading/Game/{IW3,IW4,IW5,QOS,T4,T5,T6}`) and the Release_x86
    libs zonedump links against (`OAT/build/lib/Release_x86/ZoneLoading.lib`).
  - **There's no T7 or later.**
- "All asset types are supported to be loaded from other fastfiles in memory" (`OAT/docs/SupportedAssetTypes.md:2`).
  Dumping to disk is partial: IW3-IW5 don't dump GfxWorld, clipMap_t or snd_alias_list_t. That doesn't matter,
  because zonedump reads the in-memory structs itself, as it does for T4-T6 (E115 `tools/zonedump/World.cpp`,
  `Collision.cpp`, all templated on `T4::`/`T5::`/`T6::` structs).
  - So for IW3-IW5 the zone loading is done, and the work is new template instantiations plus readers wherever the
    structs differ.

## Format differences per game

### IW3 (CoD4), IW4 (MW2), IW5 (MW3): the IW lineage T4 forked from

| area | difference from T4-T6 | evidence |
|---|---|---|
| world | `GfxWorld` keeps the T4 shape: `GfxWorldVertex {xyz, binormalSign, color, texCoord, lmapCoord, …}`, `GfxLightmapArray {primary, secondary}` | `IW4_Assets.h:3648,3654`; `IW3_Assets.h:2189`; `IW5_Assets.h:2502` [V] |
| | Lightmap decode is probably T4's primary/secondary pair; IW4/IW5 images use the v8 IWI map-type bits | [assets_t4_t5_t6.md](assets_t4_t5_t6.md) (line ~576 in the source) [I] |
| light grid | IW3: `GfxLightGridColors {rgb[56][3]}`, the same entry and row layout as T4 | `IW3_Assets.h:2194-2222` [V] |
| | IW4/IW5: the same fields (IW5 adds `useSkyForLowZ`) | `IW4:3709`, `IW5:2566` [V] |
| | The T4 grid decoder should carry over, but its colour scale needs checking [I] | |
| collision | IW3/IW4 `clipMap_t`: planes, brushsides, brushEdges, nodes, leafs, aabbTrees, partitions, tri soup, cmodels, brushes, the T4 layout | `IW3:1824`, `IW4:3113` [V] |
| | IW5 moves brushes into `ClipInfo`, like T6 | `IW5:1950`, `T6` `ClipInfo` [V] |
| | So `Collision.cpp`'s T4 and T6 paths cover both shapes. Trace masks need reading from each exe | |
| xmodel | IW4/IW5 split surfaces into a separate `XModelSurfs` asset (`IW4:535`, `IW5:565`). One extra pointer hop | [V] |
| | OAT already dumps IW3/4/5 xmodels to GLB | `SupportedAssetTypes.md` [V] |
| | The T4/IW3 missing-triangle quirk applies to IW3 | [assets_t4_t5_t6.md](assets_t4_t5_t6.md) (line ~177 in the source) [V] |
| xanim | `XAnimParts` is present in all three (`IW3:288`, `IW4:405`, `IW5:429`), the same lineage as T4 | [V], details [I] |
| material | IW material/techset family (IW4 has separate vertex/pixel shader assets). `MaterialState.cpp` needs a statebits decode per game | `SupportedAssetTypes.md` IW4 rows [V]; [I] |
| sound | `snd_alias_t` uses floats in final units (`volMin/Max`, `pitchMin/Max`, `distMin/Max`, `probability`) and a single `SndCurve* volumeFalloffCurve`. No min curves, no reverb distance | `IW3:1591`, `IW4:1840`, `IW5:1653`; `SndCurve {filename, knotCount, knots[8][2]}` `IW3:1537` [V] |
| | Samples are Miles `LoadedSound {name, MssSound {AILSOUNDINFO info; data}}` in the ff, with `info.format/rate/bits/channels` | `IW3:1638-1650` [V] |
| | OAT's IW4 dumper handles PCM only and errors on other formats | `OAT/src/ObjWriting/Game/IW4/Sound/LoadedSoundDumperIW4.cpp:37-44` [V] |
| | Streamed sounds are separate files [I] | |
| script | IW3/IW4: GSC as rawfile source text, like T4 [I] | |
| | IW5: compiled `ScriptFile {compressedLen, len, bytecodeLen, buffer, bytecode}` | `IW5:4950` [V] |
| | GSC-Tool (xensik) handles IW5 | `SupportedAssetTypes.md` IW5 ScriptFile note [V] |

### T7 (BO3)

| area | state |
|---|---|
| container | `.ff` is `TAff0000` v`0x251`, a chain of zlib blocks, **not AES-encrypted** on PC core/frontend zones (`RE/t7-bo3/notes/t7_fastfile_format.md:6-27` [V]; header bytes `54 41 66 66 30 30 30 30 51 02` [M]) |
| | Our offline decompressor is `RE/t7-bo3/tools/zone/bo3_ff_dec.py` [V] |
| zone structs | **None in OAT.** BO3 is 64-bit, so OAT's 32-bit mirrored-struct loaders don't apply [I] |
| | A T7 zone loader (XFile blocks, pointer fixups, every asset struct) would have to be written from scratch |
| | **The exe can't be read statically:** it's Arxan-protected and encrypted on disk (`RE/t7-bo3/notes/t7_assetpool_offset.md:44-47` [V]) |
| | Struct layouts would come from public tools (C2M's GfxMap offsets, `t7_assetpool_offset.md:37-38`; Greyhound) and ACTS |
| streaming | Images and mesh LODs stream from `.xpak` (`KAPI` v10, LZ4 blobs). There's an offline image reader (`RE/t7-bo3/notes/t7_xpak_format.md:33-55`, `tools/xpak/`) [V] |
| | Mesh streaming isn't covered [I] |
| world | GfxMap via C2M's offsets, so far **read from a running game only** (`t7_assetpool_offset.md:3,51`). The current rules forbid dumping running games |
| | Offline GfxWorld needs the T7 zone loader [I] |
| material/lighting | New PBR material model and a different lighting model. Needs new engine fields, not just converters [I] |
| sound | **Closest to done.** The same `'2UX#'` bank family as T6, at **version 15**, `entrySize` **0x24** (36 B, T6 is 20), `checksumSize` 16, `dependencySize` 64 [M, `zone\snd\all\core_frontend.all.sabl`] |
| | The extra 16 bytes per entry need decoding against one file [I] |
| | Alias names and parameters live in the zone `SndBank` asset, so they need the T7 zone loader. Without it, samples export by hash only |
| script | ACTS decompiles and compiles T7 GSC offline (`ACTS:34,61,75-77`: `bo3` handler dumps `rawfile` + `scriptparsetree`; VM 1A/1C full, 1B partial) [V] |
| mod tools | The installed Mod Tools hold the **source** formats: `model_export` (xmodel_export), `map_source` (Radiant `.map`/prefabs), `gdtdb` [M] |
| | Mod Tools source is a cleaner route than retail zones for *user/mod maps*. It doesn't help with retail stock maps [I] |

### Not viable now
- **IW7:** no zones on disk [M].
- **T8 (BO4):** the zones are AES-encrypted (`t7_fastfile_format.md:27` contrast) [V], and we only have a Greyhound
  rip. The rip's `XMODEL_EXPORT` + `.semodel` + PNGs are already-converted models, a possible *model-only* import
  path (no maps, no sounds, no scripts) [M/I].
- **QOS:** OAT has partial support only [V], and the game isn't installed.

## Carry-over against zonedump's outputs

Outputs: `--world` (world glb + `e115_*` extras), `--lightgrid`, `--xmodel`, `--xanim`, `--collision`,
`--sounds`/`--all-sounds` (`sounds.json` + wav/flac), `--clip-materials`, `.ents`, and `--names`
(`tools/zonedump/main.cpp:1495-1600`). [zonedump_formats.md](zonedump_formats.md) was still being written, so this table uses the zonedump
modes.

| output | IW3 | IW4 | IW5 | T7 |
|---|---|---|---|---|
| `.ents` | carries over (MapEnts string) | carries over | carries over | needs a T7 zone loader |
| world glb | new instantiation of the T4 path. Lightmap and material decode need checking | same + `XModelSurfs` hop for smodels | same | new reader, new material fields |
| lightgrid | T4 decoder, verify the scale | same | same (+ `useSkyForLowZ`) | new (probe-based) [I] |
| xmodel | OAT path + T4 quirk | + `XModelSurfs` | + `XModelSurfs` | xpak mesh streaming |
| xanim | new instantiation, check the delta formats | same | same | new |
| collision | T4 path | T4 path | T6 `ClipInfo` path | new |
| sounds | **new effective-value conversion**: floats are already final; one `SndCurve` (no min curve, so write `allon` min plus the curve over [distMin, distMax]); Miles `AILSOUNDINFO` formats | same + `mixerGroup`, `velocityMin` | same + `volModIndex` | bank reader v15 (+16 B/entry); aliases need the zone loader |
| masks | read the player trace mask from each exe | same | same | the exe can't be read statically |
| engine | **nothing new** expected. The sound curve fields map onto the existing min/max curve model | nothing | nothing | PBR material + new lighting fields |

## Ranking (value / effort)

1. **IW4 (MW2): best value per effort, blocked on content.** OAT loads it, its structs are the T4 lineage, and only
   new template instantiations plus a Miles-sound and float-alias conversion are needed. But there's **no MW2 map
   zone on disk** [M]. It's worth doing when the user installs the base game.
2. **IW3 (CoD4): the same story as IW4, the closest to T4.** It's not installed.
3. **IW5 (MW3):** as IW4 plus T6-style `ClipInfo` and compiled scripts. It's not installed.
4. **T7 sounds only:** low effort, partial value. The bank reader at v15 gets every BO3 sample offline today, but
   only by hash: names need the zone.
5. **T7 full: highest value** (BO3 zombies maps are the most-asked-for content), **highest effort.**
   - It needs a 64-bit zone loader from scratch, with no static exe RE (Arxan) and only third-party struct layouts.
   - It also needs xpak mesh streaming, plus PBR material and new lighting fields in the engine.
   - The fastfile and xpak image readers already exist in CoD-RE, and ACTS covers scripts.
   - A smaller first step is to target the Mod Tools source formats (`model_export`, `map_source`) for mod maps.
6. **T8 models from the rip:** cheap for props and characters (`XMODEL_EXPORT` is a text format we could read), but
   it's not a map path.

**Recommendation.** Don't start a new zone game until there's content to test on. The only installed candidate
beyond T4-T6 is T7, and its full cost is an order of magnitude above IW4's. The cheap, contained next steps are:
- The T7 bank v15 reader (sounds by hash).
- A structural spike that decodes one T7 zone's asset list offline with `bo3_ff_dec.py`, to size the zone-loader work.
- Asking the user whether they own MW2 / CoD4 / MW3 base installs. With those, IW4 is roughly a week of converter work
  and no engine work [I].

## Open
- The meaning of the T7 bank entry's extra 16 bytes.
- IW3-IW5 player trace masks and Miles sound format codes (needs exe reads; no IW exes on disk except the IW4x client's).
- Whether IW3/IW4 lightmaps decode like T4's.
