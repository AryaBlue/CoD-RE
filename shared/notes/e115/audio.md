# Sound data: T4 / T5 / T6

Base for the zonedump audio exporter and engine audio. This page covers the alias records, where the
sample data lives, the codecs, curves, units and alias-list selection.

Tags:
- **[V]**: read in source. Mostly OAT's struct definitions and its T6 sound loader/dumper, plus the codresearch wiki.
- **[M]**: measured on the installed game files (BO1 iwds, BO2 `sound/*.sab*`). The games weren't run.
- **[I]**: inferred.

Sources:
- OAT is the vendored copy at `<OAT checkout>/src` (vendored in our b2w fork), cited below as `OAT/`.
- The codresearch wiki pages "Sound Asset" (<https://codresearch.dev/index.php/Sound_Asset>) and "SABS & SABL Files"
  (<https://codresearch.dev/index.php/SABS_%26_SABL_Files>) give struct listings only. They don't describe playback
  behaviour.

## Summary

| | T4 (WaW) | T5 (BO1) | T6 (BO2) |
|---|---|---|---|
| alias record | `snd_alias_t`, floats | `snd_alias_t`, u16/u8 packed | `SndAlias`, u16/u8 + bitfields |
| alias container | `snd_alias_list_t` asset | `SndBank` asset holding lists | `SndBank` asset holding lists |
| loaded samples | `LoadedSound` in the ff | `LoadedSound` (`snd_asset` header + data) in the ff | `zone.lang.sabl` bank file |
| streamed samples | file on disk (`StreamFileName`) | `.wav`-named files in iwds, actually `snd_asset` + MS-ADPCM [M] | `zone.lang.sabs` bank file |
| codec seen | ? (no WaW install here) | MS-ADPCM only, 28,481 files [M] | sabl PCM s16, sabs FLAC [M] |
| volume / pitch | float | u16 | u16 |
| curves | index into `SndDriverGlobals.curves[32]` | `dryCurve`/`wetCurve` u8 index | 6-bit indices in flags |
| distance | float, game units | u16, game units | u16, game units |

Game units are the world's units (inches) [I]. T6 doubles the stored distances at run time [V, see Falloff].

## T4: `snd_alias_t` (`OAT/Common/Game/T4/T4_Assets.h:1749`) [V]

`snd_alias_list_t` (`:1799`) = `{aliasName, head, count}`. It's an asset in its own right, and `head` points to
`count` contiguous aliases.

Alias fields, in order:
- `aliasName`, `aliasNameHash`, `subtitle`, `secondaryAliasName`, `chainAliasName`, `SoundFile* soundFile`, `int sequence`
- floats:
  - `volMin`, `volMax`, `pitchMin`, `pitchMax`
  - `distMin`, `distMax`, `distReverbMax`
  - `slavePercentage`, `probability`, `lfePercentage`, `centerPercentage`
  - `envelopMin`, `envelopMax`, `envelopPercentage`
  - `minPriority`, `maxPriority`, `minPriorityThreshold`, `maxPriorityThreshold`
  - `reverbSend`, `teamVolMod`, `teamPitchMod`
  - `occlusionLevel`, `occlusionWetDry`, `moveTime`
- ints:
  - `startDelay`, `speakerMap`, `flags`
  - `volumeFalloffCurve`, `reverbFalloffCurve`, `volumeMinFalloffCurve`, `reverbMinFalloffCurve`
  - `limitCount`, `limitType`, `entityLimitCount`, `entityLimitType`, `randomizeType`
- floats: `cylInnerRadius`, `cylOuterRadius`, `cylOuterLevel`

Sample data:
- `SoundFile` (`:1742`) = `{type, exists, SoundFileRef u}`.
- `type` is `SAT_LOADED 1`, `SAT_STREAMED 2` or `SAT_PRIMED 3`.
- `SoundFileRef` (`:1727`) is either a `LoadedSound*` or a `StreamedSound {StreamFileName {hash, dir, name}, PrimedSound* primeSnd}`.
- `LoadedSound` (`:1701`) = `{name, snd_asset {char* data; int data_size}}` (`:1695`). It's just a blob.
  - Whether the blob is a full RIFF `.wav` is [I]. There's no WaW install here to measure.
  - The exporter should sniff for `RIFF`.

Enums:
- `snd_limit_type_t`: `NONE, OLDEST, REJECT, PRIORITY, SOFTEST`.
- `snd_randomize_type_t`: `INSTANCE 0, ENTITY_VOLUME 1, ENTITY_PITCH 2, ENTITY_VARIANT 4`. It's a bit set apart from 0.

Curves:
- `snd_curve_t` (`:3928`) = `{char name[32]; int pointCount; float points[8][2]}`.
- They live in `SndDriverGlobals` (`:3959`, `curves[32]`, alongside `reverbPatches[64]`, `buses[64]`, `speakerMaps[32]`,
  `masterEffects[16]`).
- The alias's `*FalloffCurve` ints index that array [I by name and range].

## T5: `snd_alias_t` (`OAT/Common/Game/T5/T5_Assets.h:1998`) [V]

`snd_alias_list_t` (`:2042`) = `{name, id, head, count, sequence}`. Lists sit inside a `SndBank` asset (`:2092`).

Alias fields:
- `name`, `id`, `subtitle`, `secondaryname`, `SoundFile*`, `flags`, `duck`, `contextType`, `contextValue`
- u16:
  - `fluxTime`, `startDelay`, `reverbSend`, `centerSend`
  - `volMin`, `volMax`, `teamVolMod`, `pitchMin`, `pitchMax`, `teamPitchMod`
  - `distMin`, `distMax`, `distReverbMax`
  - `envelopMin`, `envelopMax`, `envelopPercentage`
- u8:
  - `minPriorityThreshold`, `maxPriorityThreshold`, `probability`
  - `occlusionLevel`, `occlusionWetDry`, `minPriority`, `maxPriority`, `pan`
  - `dryCurve`, `wetCurve`, `dryMinCurve`, `wetMinCurve`
  - `limitCount`, `entityLimitCount`, `snapshotGroup`

The scaling is as for T6 below [I: same packed types, same tool lineage].

Sample data:
- `SoundFile` (`:1991`) = `{u, type, exists}`. `StreamedSound` = `{filename, primeSnd}`. `PrimedSound` = `{name, buffer (2048-aligned), size}`.
- `LoadedSound` (`:1955`) holds a full `snd_asset` (`:1937`):

| off | field | BO1 streamed files [M] |
|---|---|---|
| 0x00 | version | 1 |
| 0x04 | frame_count | |
| 0x08 | frame_rate | 44-51 kHz, mostly 47-48 kHz, *not* a fixed 48000 |
| 0x0C | channel_count | 1 or 2 |
| 0x10 | header_size | 0x830 (2096) on every file |
| 0x14 | block_size | 0x10600 |
| 0x18 | buffer_size | 0x83000 |
| 0x1C | format | 6 (MS-ADPCM) on every file |
| 0x20 | channel_flags | L 1, R 2, … RB 0x80 |
| 0x24 | flags | `LOOPING 1`, `PAD_LOOP_BUFFER 2`; seen 0 and 3 |
| 0x28 | seek_table_count | 0 |
| 0x2C | seek_table (ptr) | 0 |
| 0x30 | data_size | = file size − 0x830 |

`snd_asset_format` (`:1904`): `PCMS16 0, PCMS24 1, PCMS32 2, IEEE 3, XMA4 4, MP3 5, MSADPCM 6, WMA 7`.

Streamed files [M]:
- They're the 28,481 `.wav`-named files in `main/iw_*.iwd`: `sound/...` (4,028) and `english/...` (24,453, voice).
- Despite the extension they are not RIFF. Each is the `snd_asset` header above (as in memory, pointers zeroed),
  padded to 0x830, then the codec data.
- Example: `sound/amb/alarms/buzz/buzz_00.wav`, 37,466 B, 69,120 frames mono, data 35,370 B.
- The data is standard MS-ADPCM (7 coefficient pairs, a 7-byte header per channel per block): **blockAlign = 262 × channels,
  512 frames per block** [M].
  - Every file is exactly 262 B per 512 frames per channel, and frame counts are multiples of 512.
  - A contributor checked this across 4,026 files, and air_raid, siren and buzz decode cleanly to their exact frame counts.
- The odd per-file `frame_rate` values look like the authoring tool's resample result. Play them at the stored rate [I].

Loaded sounds are in the ff with the same header [V by struct]. Their formats aren't measured yet: the exporter
should switch on `format`.

### T5 playback: XAudio2, MS-ADPCM and xWMA [V, BlackOps.exe]

The PC game plays sound through **XAudio2 2.7** (DirectX June 2010):
- It calls `CoCreateInstance` with `CLSID_XAudio2` `5a508685-…` or `CLSID_XAudio2_Debug` `db05ea35-…`, and
  `IID_IXAudio2` `8bcf1f58-…` (`0x4aaca3`, `0x8b1820`).
- It doesn't import or load any WMA, ACM, DMO or Media Foundation decoder. XAudio2 decodes xWMA itself.

The source voice format is built from the `snd_asset` at `0x8b12a0`:

| `format` | WAVEFORMATEX |
|---|---|
| 0 PCM | plain PCM |
| 6 MS-ADPCM | tag 2, `nBlockAlign = 262 × ch` (`0x106`), 4 bits, `cbSize 32`, `wSamplesPerBlock = 2·blockAlign/ch − 12 = 512`, 7 standard coefficient pairs |
| 7 WMA | **tag `0x161` (WMAv2, xWMA)**, `nChannels = channel_count`, `nSamplesPerSec = frame_rate`, `nAvgBytesPerSec = 6000 × channels` (48 kbit/s per channel), **`nBlockAlign = 2230` mono / `4096` otherwise** (`channel_count != 1`, `0x8b12e0`), 16 bits, `cbSize 0` |

Anything else logs an error and plays nothing.

For format 7, the buffer is an `XAUDIO2_BUFFER_WMA` (`0x8b1561`):
- `pDecodedPacketCumulativeBytes = seek_table` (`+0x2C`)
- `PacketCount = seek_table_count` (`+0x28`)
- `AudioBytes = nBlockAlign × seek_table_count`

The voice is then created through IXAudio2 vtable `+0x20` (`CreateSourceVoice`, `0x8b1679`).

So the data is raw xWMA packets of `nBlockAlign` bytes each, and the seek table is one u32 per packet: the
cumulative decoded PCM bytes after that packet (XAudio2's definition). For example, Kino's `bang_00` is 37,910 B =
17 × 2230, with `seek_table_count` 17 [M, lead]. Its last entry should equal `frame_count × channels × 2` [I].

To decode at export, wrap the data as an xWMA RIFF:
```
"RIFF" size "XWMA"
"fmt " 18 bytes: the WAVEFORMATEX above
"dpds" 4×N bytes: the seek table
"data" the packets
```
ffmpeg's `xwma` demuxer reads that and decodes WMAv2. When the fmt has no extradata, it supplies the WMAv2 extradata
itself [I, from ffmpeg's xwma.c; check on one file]. 2230/4096 and 6000/12000 are in XAudio2's xWMA tables of
allowed block-align and byte-rate values [I].

Curves:
- `snd_curve` (`:4881`) = `{char name[32]; int id; float points[8][2]}`. There's no point count: all 8 points are
  always used [I].
- `SndDriverGlobals` (`:4953`) holds `groups`, `curves`, `pans`, `snapshotGroups`, `contexts`, `masters`.
- `dryCurve`/`wetCurve` (+`Min`) are u8 indices into `curves` [I by name].

## T6: `SndAlias` (`OAT/Common/Game/T6/T6_Assets.h:6355`) [V]

The `SndBank` asset (`:988`) holds:
- `name`, `aliasCount`, `SndAliasList* alias`, `SndIndexEntry* aliasIndex`
- `radverbs`, `ducks`
- `streamAssetBank`, `loadAssetBank` (runtime state)
- `SndLoadedAssets loadedAssets` (`:964`) = `{zone, language, loadedCount, entryCount, entries, dataSize, data}`
- `scriptIdLookups`

`SndAliasList` (`:3101`) = `{name, id, head, count, sequence}`.

Alias fields:
- `name`, `id`, `subtitle`, `secondaryName`
- `assetId`, `assetFileName`
- `SndAliasFlags flags` (8 bytes)
- `duck`, `contextType`, `contextValue`, `stopOnPlay`, `futzPatch`
- u16:
  - `fluxTime`, `startDelay`, `reverbSend`, `centerSend`
  - `volMin`, `volMax`, `pitchMin`, `pitchMax`
  - `distMin`, `distMax`, `distReverbMax`
  - `envelopMin`, `envelopMax`, `envelopPercentage`
- s16: `fadeIn`, `fadeOut`, `dopplerScale`
- u8:
  - `minPriorityThreshold`, `maxPriorityThreshold`, `probability`, `occlusionLevel`
  - `minPriority`, `maxPriority`, `pan`
  - `limitCount`, `entityLimitCount`, `duckGroup`

`SndAliasFlags` (`:6321`), bitfields in declaration order (MSVC packs from the low bit):
- `flags0`:
  - `looping:1`, `panType:1`, `distanceLpf:1`, `doppler:1`, `isBig:1`, `pauseable:1`, `isMusic:1`, `stopOnEntDeath:1`, `timescale:1`
  - `voiceLimit:1`, `ignoreMaxDist:1`
  - `busType:4`, `loadType:2`, `volumeGroup:5`, `fluxType:3`
  - `limitType:2`, `entityLimitType:2`, `randomizeType:3`
- `flags1`:
  - `neverPlayTwice:1`, `unk:1`
  - `volumeFalloffCurve:6`, `reverbFalloffCurve:6`, `volumeMinFalloffCurve:6`, `reverbMinFalloffCurve:6`
  - `unk`, `isCinematic:1`, `unk:4`

The enum values come from OAT's `ObjCommon/Game/T6/SoundConstantsT6.h`, taken from the executable:
- `loadType` (`SOUND_LOAD_TYPES`, `:155`): `0 unknown, 1 loaded, 2 streamed, 3 primed`. Loaded aliases read from the
  `.sabl`, streamed and primed from the `.sabs` [I by name; measured codecs agree].
- `busType` (`:163`): `bus_reverb, bus_fx, bus_voice, bus_pfutz, bus_hdrfx, bus_ui, …`.
- `limitType` / `entityLimitType`: `none, oldest, reject, priority`.
- `randomizeType` (`:177`): bits `volume 1, pitch 2, variant 4` (`SND_RANDOMIZE_INSTANCE 0, ENTITY_VOLUME 1, …`,
  `T6_Assets.h:6311`).
- Curve names (`SOUND_CURVES`, `:42`): `default, defaultmin, allon, alloff, rcurve0-5, steep, sindelay, cosdelay, sin, cos,
  rev60, rev65`.

`SndCurve` (`:5235`) = `{char name[32]; uint id; vec2 points[8]}`. The 6-bit `*FalloffCurve` fields index the driver
globals' curve array [I by name], which for stock data holds the list above.

### Hashes [V]

T5 has the identical function (BlackOps.exe `0x661b40`, called on the alias name before the lookup at `0x5bb9d1`). T5 alias ids are therefore the same hash.


`SND_HashName` (`OAT/Common/Game/T6/CommonT6.h:51`) is sdbm-like and lowercases the string:

```
h = 0x1505; for c in str: h = tolower(c) + 0x1003F * h  (u32 wrap); return h ? h : 1;   empty/null -> 0
```

- `alias.id = SND_HashName(name)` and `alias.assetId = SND_HashName(assetFileName)` (`OAT/ObjLoading/Game/T6/Sound/LoaderSoundBankT6.cpp:513,520`).
- `SndAliasList.id` = its first alias's id (`:630`).
- Lookup by name goes through `aliasIndex`, an open hash table. The slot is `id % aliasCount`, with collisions
  chained by `next` into free slots (`:696-752`).
- The bank entry `id` equals `alias.assetId`: OAT's dumper finds sample data by `assetId` across all loaded banks
  (`OAT/ObjWriting/Game/T6/Sound/SndBankDumperT6.cpp`, `FindSoundDataInSoundBanks`).

### `.sabs` / `.sabl` bank files [V OAT `ObjCommon/ObjContainer/SoundBank/SoundBankTypes.h`, wiki; M]

Each file is named `<zone>[.<language>].sabl` (loaded) or `.sabs` (streamed), e.g. `cmn_root.all.sabl` (`SoundBank.cpp:245`).
The game ships 197 of them in `Black Ops II/sound/` [M].

The header is at 0, and data starts at 0x800 (`OFFSET_DATA_START`):

| off | type | field | stock value [M, all 197 files] |
|---|---|---|---|
| 0x00 | u32 | magic | `'2UX#'` |
| 0x04 | u32 | version | 14 |
| 0x08 | u32 | entrySize | 20 |
| 0x0C | u32 | checksumSize | 16 |
| 0x10 | u32 | dependencySize | 64 |
| 0x14 | u32 | entryCount | |
| 0x18 | u32 | dependencyCount | 8 |
| 0x1C | u32 | pad | |
| 0x20 | i64 | fileSize | = file size |
| 0x28 | i64 | entryOffset | entry table, near the end of the file |
| 0x30 | i64 | checksumOffset | right after the entries |
| 0x38 | 16 B | checksumChecksum | shared between a `.sabs` and its zone's loaded assets (wiki); OAT compares it in `VerifyChecksum` |
| 0x48 | 8 × 64 B | dependencies | names; slot 0 is the file's own name (`cmn_root.all.sabl`) |

Entry (`SndAssetBankEntry`, `T6_Assets.h:3173`), **20 bytes**:

| off | type | field |
|---|---|---|
| 0x00 | u32 | id (= `SND_HashName(assetFileName)`) |
| 0x04 | u32 | size (bytes) |
| 0x08 | u32 | offset (absolute, from file start) |
| 0x0C | u32 | frameCount |
| 0x10 | u8 | frameRateIndex |
| 0x11 | u8 | channelCount |
| 0x12 | u8 | looping |
| 0x13 | u8 | format (`snd_asset_format`) |

The checksums are `entryCount × 16 B`. The wiki says they are MD5 of each audio file.

Frame rates (`SndBankDumperT6.cpp:114`): `0 8000, 1 12000, 2 16000, 3 24000, 4 32000, 5 44100, 6 48000, 7 96000, 8 192000`.

`snd_asset_format` (`T6_Assets.h:3156`) is T5's list plus `FLAC 8, WIIUADPCM 9, MPC 10`.

Measured over all 40,755 stock entries [M]:
- Every `.sabl` entry is format 0 (PCM s16, raw, no header), 7,041 of them.
- Every `.sabs` entry is format 8 (FLAC, a complete `fLaC` stream), 33,714 of them.
- Every entry is `frameRateIndex 6` (48 kHz). 36,630 are mono and 4,125 stereo; 1,864 are looping.
- Offsets are **not** 2048-aligned (40,525 of 40,755), so don't assume sector alignment.

That matches OAT's dumper, which handles only PCMS16 (wraps it in a RIFF header) and FLAC (passes it through). For
the engine, PCM s16 plays as is and FLAC needs a decoder (dr_flac is a single header).

## Units and conversions (T6 per `OAT/Common/Game/T6/CommonT6.cpp`; T5 assumed the same) [V; T5 I]

| field | stored | meaning |
|---|---|---|
| `volMin/Max`, `teamVolMod` | u16 | linear gain = v / 65535. The tool csv shows dB SPL = 20·log10(lin) + 100 (≤ −95 dB → 0) |
| `pitchMin/Max` | u16 | frequency ratio = v / 32767; cents = 1200·log2(ratio) |
| `probability`, priority thresholds, `occlusionLevel` | u8 | v / 255 |
| `distMin/Max/ReverbMax` | u16 | game units (inches [I]). **T6 uses stored × 2** (see Falloff) |
| `startDelay`, `fadeIn/Out`, `fluxTime` | int | milliseconds [I by csv column names] |

T4 stores everything as floats already in these units: volume 0..1 linear, pitch as a ratio [I by type].

## Falloff [V, BlackOps.exe; Plutonium t6mp.exe]

T5 and T6 run the same code. The per-voice update first takes `d` = 3D distance from emitter to listener.

Two gains follow:
- `dry = F(dryMin, dryMax, distMin, distMax, d)`
- `wet = F(wetMin, wetMax, distMin, distReverbMax, d) × reverbSend / 65535`

```
F(minCurve, maxCurve, lo, hi, d) = d < lo ? curve(minCurve, clamp(d / lo, 0, 1))
                                          : curve(maxCurve, clamp((d - lo) / (hi - lo), 0, 1))
curve(c, t) = t <= p0.x ? p0.y : t >= p7.x ? p7.y : lerp of y on the segment [p(i-1).x, p(i).x] holding t
```

- **The min curves are a distance curve inside `distMin`, not a minimum-volume curve.** The volume is full inside
  `distMin` only when the min curve is `allon`.
- All 8 points are always used, and T5's `snd_curve` has no point count. If no segment matches, the game logs an
  error and returns 0.
- The curve is `SndDriverGlobals.curves + index × 100` (T5 `0x417600`, T6 `0x5c1970`).
- `vol` (randomised in `[volMin, volMax]`) multiplies the dry gain separately.

Where each game reads the inputs:
- T5 (BlackOps.exe):
  - distance and calls: `0x672f68`-`0x673081`
  - `F`: `0x8affa0`
  - sampler: `0x500550`
  - `curve()`: `0x58cc20`
  - The alias bytes are `dryCurve +0x4C`, `wetCurve +0x4D`, `dryMinCurve +0x4E`, `wetMinCurve +0x4F`.
- T6 (t6mp.exe):
  - caller: `0x5ece64`-`0x5ecf5c`
  - `F`: inlined at `0x4140d0`
  - `curve()`: `0x62d8d0`, byte-identical to T5's
  - The curves come from `flags1` (alias `+0x1C`): max `(f>>2)&63`, wet max `(f>>8)&63`, min `(f>>14)&63`,
    wet min `(f>>20)&63`. That matches the bitfield order above.
- **T6 multiplies `distMin`, `distMax` and `distReverbMax` by 2.0** (constant at `0xd30a50`) before use. T5 uses the
  stored values as is.
  - OAT's csv loader stores the csv numbers unchanged (`LoaderSoundBankT6.cpp:538-540`).
  - So either the stock linker halves them, or stock T6 ranges are 2× the csv values. Comparing one stock alias with
    its csv would settle it.
  - The engine should use stored × 2 for T6 either way.

The mod-tools csv agrees [M, a mod-tools sound alias csv, `sounds/aliases/mp40_zm.csv`]. `wpn_mp40_fire_npc` has
DistMin 900 = DistMaxDry, DryMinCurve `cosdelay` and DryMaxCurve `alloff`. The min curve does the whole 0-900 fade,
and the `_dist` secondary takes over beyond that. The csv names the fields `DistMaxDry`/`DistMaxWet` and
`Dry/WetMin/MaxCurve`.

`ignoreMaxDist` (T6) presumably stops the voice being culled past `distMax` [I].

## Picking from an alias list [V, BlackOps.exe; Plutonium t6mp.exe]

The picker is the same code in T5 (`0x494780`) and T6 (`0x691ad0`). It takes the list and `entnum & 0xfff`:

1. Look at the first `min(count, 64)` aliases (stride 0x54 in T5, 0x60 in T6).
   - An alias is a candidate if `contextType == 0` or `contextValue == 0`, or if `contextValue` equals the current
     value of that context.
   - T6 also checks a per-entity context table for `entnum < 0x700`.
   - With no candidates, nothing plays. With one, it plays.
2. If the first candidate has **randomise entity variant** (T5 `flags` bit 31, T6 `flags0` bit 31 = `randomizeType & 4`):
   - `idx = seededRand(list ptr + entnum) % n`. The same entity always gets the same variant.
3. Otherwise:
   - `idx = rand() % n`, rerolled while `idx == list.sequence`, up to 100 tries.
   - The reroll only happens when there are **more than 2** candidates, so a 2-variant list can repeat.
   - A global debug seed, when set, replaces `rand()` with the seeded generator.
4. Store `list.sequence = idx`. That's the "last played" variant, and the reason `sequence` exists.

**`probability` is not a weight.** The pick is uniform. After the pick, `p = probability / 255`. If `p > 0`, the sound
plays only when `random01() <= p`, and `p == 0` always plays. See T5 `0x5bbbba` and T6 `0x421e0a`.

**`neverPlayTwice`** (T6 `flags1` bit 0) is checked after the pick (`0x421b94`). If bit 1 of `flags1` (the field OAT
calls `unk`) is also set, the play is refused. That bit is presumably set at runtime once the alias has played [I], so
the alias plays at most once. It's not a no-repeat rule.

Volume and pitch rolls (T5 `0x8af1a0`; T6 `0x659183`-`0x6591ae`, same tests):
- The voice stores `rVol` at voice `+0xD4` and `rPitch` at `+0xDC`. Both are `random01()`.
- With **randomise entity volume** (bit 29 = `randomizeType & 1`), `rVol` comes from a cache of random values keyed by
  `(alias.id << 16) + (entnum & 0xfff)`, so it's stable per entity and alias for a while. The same goes for
  **entity pitch** (bit 30 = `& 2`) and `rPitch`. See "Playback rules" below for the cache.
- In T5 this only applies while a dvar is on. T6 always applies it.
- T5 has no `randomizeType` field: its `flags` bits 29/30/31 carry the same meaning.

Applying them (T5) [V]:
- `volume = lerp(volMin, volMax, rVol) / 65535 × voice script scale` (`0x4e8442`). The lerp is linear in gain, not dB.
- `pitch = lerp(pitchMin, pitchMax, rPitch) / 32767` (`0x68b6d6`), then × the timescale factor when `flags` bit 10 is
  set, then × another voice factor (`+0x108`, likely doppler [I]).

## Playback rules [V, BlackOps.exe; Plutonium t6mp.exe]

What happens between "play alias X on entity E" and a voice starting.

T5 runs these steps at `0x5bbbba`-`0x5bbc69`. T6 runs them at `0x421b86`-`0x421ef7`, after the picker and the
`neverPlayTwice` check:
1. the `probability` gate
2. compute priority
3. the **alias limit**
4. the **entity limit**
5. T6 only: `voiceLimit` and volume-group gates (`0x913ac0`)
6. start

### Limits (`limitCount`/`limitType`, `entityLimitCount`/`entityLimitType`)

The policy is T5 `0x8b0000` and T6 `0x9139f0`. The voice matcher is T5 `0x8afc80` and T6 `0x9131e0`, the same
logic unrolled.

**What "the same" means.** A playing voice matches when its alias **id** equals the new alias's id. The id is
`SND_HashName(name)`, so **every variant of the alias name counts together**. The search covers all voices: 74 in
T5 (`cmp eax, 0x4a`), 68 in T6 (`0x7700 / 0x1c0`). **It isn't per bus or per group.** For the entity limit, the
voice's entity must also equal `E`.

The matcher returns three things:
- the match count
- the matching voice with the **smallest start stamp** (the oldest)
- the matching voice with the **lowest priority**

When `count >= limitCount`, the 2-bit type decides (alias limit: T5 `flags` bits 25-26, T6 `flags0` bits 25-26;
entity limit: bits 27-28):

| type | effect |
|---|---|
| 0 none | play. There's no limit, even when the count is over |
| 1 oldest | stop the oldest matching voice, then play |
| 2 reject | don't play the new one |
| 3 priority | if `newPriority > lowestVoice.priority + ε`, stop that voice and play; otherwise reject. ε is the dvar `snd_playing_priority_boost` in T5 (default 3.0) and a constant 3.0 in T6 (`0xc883d4`) |

There's no SOFTEST in T5/T6 (the field is 2 bits).

The count fields are `limitCount`/`entityLimitCount`: T5 `+0x50`/`+0x51`, T6 `+0x5D`/`+0x5E`. Priority is computed as in
"Priority" below.

T6 adds two entity-limit details:
- A matching voice on the same entity whose stamp equals the global at `0x2e3d8a0` rejects the play outright. That's
  most likely "already started this frame", so same-frame duplicates are dropped [I on what the global holds].
- `0x913ac0`:
  - **voiceLimit** (`flags0` bit 9): before starting, stop every voice on the same entity whose alias also has
    `voiceLimit`. So there's one voiceLimit voice per entity, and the newest wins (typically dialogue).
  - If the alias's `volumeGroup` (`flags0` bits 17-21) equals the global at `0x2e3d9d8`, the play is **rejected**
    while any voice of that group is active. That makes the group exclusive [I on which group].

### Priority

Priority is computed by T5 `0x8af8c0` + `0x8af820` and by T6 `0x912d80` + `0x4916d0`.

1. **Closeness `f`, 3D voices only** (pan type 3d: T5 `flags` bit 1, T6 `flags0` bit 1). A 2D alias gets `f = 0`.
   - `d` is the 3D distance from the voice origin to the listener. T6 picks the nearest listener (`0x534970`).
   - `f = 1 − clamp(d / R, 0, 1)`.
   - The range `R`:
     - T5: `distReverbMax` (as stored).
     - T6: `distReverbMax × 2`. If a per-curve flag table (`0x2e3d8d8[curve]`) is set for the alias's volume or
       reverb falloff curve, `R` is `distMin × 2` instead (`0x912dfe`, `0x912e29`). The meaning of that table is
       unknown, possibly "curve is silent past distMin" [I].
2. **Thresholds.** `lo = minPriorityThreshold / 255` and `hi = maxPriorityThreshold / 255` (the u8 fields; T6
   `+0x56`/`+0x57`).
   - `f <= lo` → `minPriority`
   - `f >= hi` → `maxPriority`
   - otherwise `t = (f − lo) / (hi − lo)` and `priority = minPriority × (1 − t) + maxPriority × t`
   - If `lo == hi`, `t = 0.5` (constant `0x9b449c` in T5, `0xc519c8` in T6).
3. **Units.** Priority is the raw u8 `minPriority`/`maxPriority` value (T6 `+0x5A`/`+0x5B`), not divided by 255. The
   mod-tools csv uses values like 40-90 with thresholds 0.25/0.8 [M, `mp40_zm.csv`]. The limit check's ε is in the
   same units (3.0).
4. **Recomputed while playing.** The T6 voice update recalculates `f` and the priority from the voice's current
   origin every update and stores it at voice `+0xE4` (`0x5ecb0e`-`0x5ecb30`, `0x5ecff8`-`0x5ed00c`). The limit and
   priority checks compare against that live value.
   - A routine at `0x912f30` also scans voices by this priority, most likely to steal the lowest-priority voice when
     all voices are busy [I].

### neverPlayTwice (T6)

The check is on the **picked variant entry** (`0x421b94`):
- If `flags1` bit 0 (`neverPlayTwice`) and bit 1 are both set, the play fails, with no reroll to another variant.
- Bit 1 is set on that alias entry **after every successful start** (`or [alias+0x1c], 2` at `0x422167`, `0x422215`,
  `0x42222c`).

So each neverPlayTwice variant plays **at most once**, until the alias data is reloaded (the flag lives in the
loaded asset) [I on the reset point]. It isn't a "don't repeat the last variant" rule; `sequence` does that (see
"Picking"). T5 has no such flag.

### startDelay, fadeIn, fadeOut (milliseconds)

- **startDelay**:
  - T5 `0x63f2da`: the voice's elapsed time is `(now − startTime − startDelay) × 0.001` s. While that's negative,
    the voice is skipped (silent), so the start is **delayed by startDelay ms**.
  - T6 copies it into the play request (`0x421fb6`). Its consumer isn't traced, so assume the T5 meaning [I].
- **fadeIn** (T6 `+0x50`, s16, `0x6591d5`): when it's non-zero, it **replaces** the play request's own fade-in time
  (the script-supplied one). Its unit is ms, like fadeOut [I].
- **fadeOut** (T6 `+0x52`, s16), in the entity stop routine `0x4abea4`:
  - The routine stops voices on the entity that are **looping** (`flags0` bit 0), plus, on a death stop, those with
    **stopOnEntDeath** (bit 7).
  - If `fadeOut != 0`, the voice fades instead of cutting, at `rate = 1 / (fadeOut × 0.001)` per second
    (`0x4abf16`-`0x4abf4a`).
  - If it's 0, the voice stops immediately (`0x4fc8c0`).
  - **So fadeOut runs on stop.** Whether script `stopsound` takes the same path isn't traced. T6 registers script methods by id (`stopsound` = `0x78b`, table entry at `0xd46e78`), so its handler is behind the method dispatch [I: likely the same fade].

### Randomise-entity seeds

**Volume and pitch** (`randomizeType & 1`, `& 2`; T5 `0x8af1a0`, T6 `0x659167`):
- The key is `(alias.id << 16) + (entnum & 0xfff)`, with `| 0x80000000` for volume and `& 0x7fffffff` for pitch.
- The value comes from a **random-value cache** (T5 `0x5440b0`, 148 slots; T6 `0x4f4e30`, 136 slots). Entries are
  stamped with the sound clock and **expire after 30,000 ms** (`cmp …, 0x7530`).
- So a given alias on a given entity reuses the same volume/pitch roll for up to 30 s, then rerolls. The exact
  refresh-on-use and eviction rules aren't traced [I].
- Without the bits, each play calls `random01()`.

**Variant** (`randomizeType & 4`, picker):
- `seed = (list pointer) + (entnum & 0xfff)`.
- One step of the ANSI LCG: `s = s × 1103515245 + 12345`, value `(s >> 16) & 0x7fff` (T6 `0x6a84f0`).
- Then `% n` candidates.
- The list pointer varies between runs, so the variant is stable per (list, entity) within a session only. For the
  engine, `hash(list name) + entnum` gives the same behaviour.

## Exporter notes

- T6:
  - Read `SndBank` from the zone and open `sound/<zone>.<lang>.sabl` / `.sabs` next to the ff (`zone` and
    `language` come from `loadedAssets`, or from the bank name plus `all`).
  - Find each alias's entry by `assetId` across that bank and the common banks (`cmn_root.all`, etc.).
  - Write PCM as `.wav` and FLAC as `.flac`.
- T5:
  - Streamed: open `assetFileName`'s path from `StreamedSound.filename` inside the iwds, strip 0x830 bytes and decode
    MS-ADPCM (blockAlign 262 × ch, 512 frames per block).
  - Loaded: take the `snd_asset` in the ff and switch on `format`.
- T4: dump `LoadedSound.data` as is if it starts with `RIFF`. Streamed files resolve to `dir/name` on disk.
- Write a json/csv sidecar per alias with the fields above, converted to linear gain / ratio / units, plus curve names,
  so the engine never has to know per-game packing.

## Open

- Whether any T5 asset uses a format other than 0/6/7. The game plays only those three.
- T4 loaded-sound blob format (no WaW install to measure).
- Whether stock T6 aliases store csv distances halved (the ×2 at run time).
