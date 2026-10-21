# BO4 (T8) recon — offline, read-only

Prepared by the offline recon worker, 2026-10-21. Target: Black Ops 4 install at
`E:\SteamLibrary\steamapps\common\bo4_game_files` (142 GB). Everything below is from a
first-hand read of the install and of the tooling already on this disk, plus the ACTS
README on disk and the Cordycep/Greyhound GitHub READMEs. No game or launcher was run;
nothing was modified, pushed or uploaded.

Legend: **[fact]** = verified first-hand this session. **[inference]** = my reasoning, not
yet proven; the probe that would settle it is named.

---

## 0. TL;DR (read this first)

- **Storage is CASC** (Blizzard/Battle.net TACT), confirmed from `.build.info`
  (`tpr/b04`, build `1.23.4.13869365`, branch `us`) and the on-disk layout. **[fact]**
- **BO4 assets live inside the CASC**, not as loose files. A whole-tree glob found **no**
  loose `.xpak/.xsub/.ipak/.xmodel/.xanim/.xsound/.sab*`; the only loose `.ff` are 12 tiny
  patch fastfiles under `LPC\` (ffotd + playlists, ~10 MB total). **[fact]**
- **The one realistic offline route is ATIAN-COD-TOOLS (ACTS), already on disk at
  `E:\ClaudeWork\acts\release_3.3.0`.** Its `fastfile` tool has a native `-C --casc` +
  `-G --game-path` mode — it reads the CASC install **cold, no running game** — and the
  BO4 AES keys are bundled (`keys_aes.csv`), so fastfiles decrypt offline. **[fact]**
- ACTS dumps offline: **GSC/CSC scripts (decompiled), Lua, strings/localize, DDL,
  scriptbundles, weapons, map tables (incl. preview images), gfxworld/comworld/entity
  metadata, sounds metadata, asset-name listings, compiled zones.** Images are behind a
  `--graphic` flag (needs a probe to confirm BO4 coverage). **Models/anims are not in the
  BO4 dumper pool list.** **[fact for the list; inference for image/model coverage]**
- **Greyhound and Wraith need the game running** (attach-to-process) for BO4, so they are
  **out** under our no-launch rule. **[inference, strong]**
- **Recommended first project: an offline GSC + string/table dump + study of BO4 Zombies**,
  using ACTS `--casc` against the user's install. First concrete step is a dry
  `acts casctest <install>` + a single-zone scripts-only dump — **this needs your OK to run
  against the 142 GB install** (see §7).

---

## 1. Storage format — CASC confirmed

`.build.info` (pipe-delimited TACT build file) reads: **[fact]**

```
Branch us | Active 1 | ... | CDN Path tpr/b04 | CDN Hosts level3.blizzard.com us.cdn.blizzard.com
Tags: US? enUS speech?:US? enUS text? | Version 1.23.4.13869365 | Product (tpr/b04)
```

This is the Battle.net/CASC (Content Addressable Storage Container) format Blizzard uses as
Activision's launcher back-end. Layout under `Data\`: **[fact]**

| Path | Count / notes | Role |
|---|---|---|
| `Data\data\*.idx` | 32 files, 64 KB each | CASC local index: maps 9-byte content-key prefixes to (archive #, offset, size). File names like `0e00000099.idx` = bucket id + version. |
| `Data\data\data.NNN` | 148 archives, ~1 GB each (`data.000`..) | The actual content archives. Every asset blob (encrypted + BLTE-framed) lives here. This is ~142 GB. |
| `Data\config\3e`, `Data\config\a9` | hashed config | CASC build-config and CDN-config (buildconfig/cdnconfig) by hash prefix. |
| `Data\indices\*.index` | 7 files | Archive-group `.index` (the CDN "archive index" that maps keys to the big archives). |
| `Data\ecache\*.idx` | many 64 KB | "ecache" — a second CASC-style index set (encoding cache / download-order cache). |
| `Data\viper\*.idx` + `.residency` | 131 KB idx + residency marker | **Viper = BO4's streaming/ecache layer.** `.residency` tracks which streamed blocks are resident on disk. Viper indexes stream data (audio/large textures) separately from the main `data\`. |

`manifest.json` holds one SHA-256 (`bo4: 96600B…`); `.build.info` holds the Build/CDN/Install
keys and KeyRing. Together these are a normal, complete CASC/TACT install. **[fact]**

### Loose-asset glob (whole tree, depth 8) **[fact]**

| Extension | Loose files found | Where |
|---|---|---|
| `.ff` | 12 | `LPC\` only — `*_core_ffotd_tu23_*.ff`, `*_core_playlists_tu23_*.ff` (+ region-safe & `en_` variants). ~10 MB total. These are **Local Patch Content**: title-update "fastfile of the day" + playlist patches that overlay the CASC. |
| `.csv`, `.gsic` | 7 | `project-bo4\internals\T8ShieldSupport\` — belong to the REV/shield mod platform, not stock game assets. |
| `.xpak .xsub .ipak .xmodel .xanim .xsound .sabl .sabs .lua .bik .gsc .gscc` | **0** | none anywhere |

**Conclusion:** all real game content (scripts, images, models, sounds, zones) is sealed
inside the CASC `data.NNN` archives. To get at any of it you must go through a CASC-aware
reader. The loose `LPC\*.ff` are patch overlays only and are tiny.

### What the REV / project-bo4 files are (noted, NOT run)

`BlackOps4.exe` (114 MB), `BlackOps4_boot.exe`, `Black Ops 4 Launcher.exe`,
`Launch Project BO4.exe`, `REV.Runtime.dll`, `bindings.json`, `project-bo4.json/.log`, and
`project-bo4\` (with `internals\ mods\ zone\ zone_mods\ plugins\ acts-plugin.log`) are a
**REV Battle.net-emulator + project-bo4 "shield-development" mod platform** set up to *run*
BO4 offline. `project-bo4\zone\support.ff` and `zone_mods\T8ShieldSupport_FF` are the
shield support fastfile; `acts-shield-plugin.dll` (in the ACTS bin) is its plugin. **This is
the runtime the game worker would use; it is irrelevant to offline recon and I did not run
it.** **[fact]**

---

## 2. Toolchain survey (the core of this report)

### 2.1 What's already on this disk **[fact]**

| Tool | Location | State |
|---|---|---|
| **ACTS 3.3.0** (ate47) | `E:\ClaudeWork\acts\release_3.3.0\unpacked\acts` | Extracted, runnable. Ships `acts.exe`, `Cordycep.CLI.exe`, `acts-bo3/bocw/shield` plugin DLLs, `data\games\bo4.json`, `data\keys\keys_aes.csv` (incl. BO4 keys). |
| **Greyhound** (Scobalula fork) | `E:\ClaudeWork\bo3\greyhound\app\Greyhound.exe` | Present; was used on BO3 by attaching to the running game. |
| **CoDLuaDecompiler** | `E:\ClaudeWork\t6_ui_mod\tools\CoDLuaDecompiler` | Source + built DLLs; has `Games\BlackOps4.cs` → decompiles BO4 `luafile`. |
| BO3 `.xpak` extractor (ours) | `E:\ClaudeWork\xpak_extract` | Our Python KAPI/xpak image extractor, built for **BO3**; BO4 xpak framing may differ (see §2.5). |
| HydraX / Wraith / Cordycep(standalone) | — | **Not on disk** (searched the user's drives). |

### 2.2 ACTS — the primary offline route (first-hand verified)

Running `acts.exe` (help only — not a dump) and `acts.exe -t list / search / fastfile`
gives this, first-hand: **[fact]**

- `acts list` categories include a dedicated **`bo4`** category and a **`fastfile`**
  category.
- `acts search fastfile` lists: `fastfile` (reader), `fastfilelinker`, **`casctest [path]`**
  (test CASC), `ffexe/fftest/ffexe` (test a `.ff`), `ffxpakr` (read xpak), `ffsndr` (read
  snd), `h32ck`.
- The **`fastfile` reader** exposes exactly the flags we need:
  - **`-C --casc [c]`  "Use casc db"** ← reads the CASC storage directly
  - **`-G --game-path [g]`  "Game path"** ← point it at the install
  - `-r --handler` / `-R --handlers` (pick `bo4`), `-D --decompressors`
  - `-a --assets` (restrict to asset types), `-n --name` (restrict by name)
  - `-p --patch` ("Use patch files (fd/fp)") — handles the LPC overlays
  - `--graphic` **"Dump graphic assets (do not share graphic assets)"**
  - `--dumpAssetNames`, `--dumpBinaryAssets`, `--dumpBinaryAssetsMap`,
    `--dumpCompiledZone`, `--dumpXStrings`
  - `--scriptsFormatter`, `--disableScriptsDecomp` (GSC decompile is built into the dump)
  - `--decrypt-t8` (BO4 decryption algorithm selector)
- **`keys_aes.csv` already contains BO4 keys** (`1080_zm_common`, `4k_zm_common`,
  `cp_common`, `cp_common_script`, … all tagged `BO4`), and `archive_checksums.csv` has a
  `bo4` + `bo4dev` row. So **fastfile decryption is offline and key-complete**; no running
  process is needed to recover keys. **[fact]**
- `data\games\bo4.json` (62 KB) defines the BO4 handler: `commonFastFiles` (zone/core_common,
  mp_common, zm_common, zm_common_all, zm_common_script, wz_common…), a `firstAssetName`
  /`endAssetName`, and `scans` (byte signatures for `Load_XAsset`, `Load_Stream`, …) against
  a `"module": "BlackOps4_dump.exe"`. **[fact]**

**Does ACTS read CASC directly, or need extracted fastfiles?** **Directly.** The `-C --casc`
+ `-G --game-path` pair is a native CASC mode, and `casctest [path]` is a CASC self-test that
takes the install path. ACTS reimplements the fast-file loaders ("the Atian Tools fastfile
loaders", per `Cordycep.CLI.exe`'s own banner), so it does **not** require a running game to
load a zone. **[fact that the mode exists; inference that a full BO4 ZM zone dumps cleanly
cold — settle with the probe in §7].**

**The `BlackOps4_dump.exe` module reference** in `bo4.json` is the *Cordycep* style
(run a patched game module to load FFs). That harness is **not on disk**, and ACTS's own
`--casc` loader is the path that avoids it. So we do **not** need to produce or run a patched
game executable for the script/table/string work. **[fact that no dump exe is present;
inference that `--casc` fully substitutes for it for the pools we want].**

**ACTS BO4 dumpable pools (README on disk, `bo4` handler):** **[fact]**
`aitype, arenaseasons, bgcache, character, characterbodytype, cpu_occlusion_data,
customization, ddl, entitlement(+list), firstpartyentitlement(+list), gametypetable,
hierarchical_task_network, keyvaluepairs, localize_entry, luafile, comworld, entity_list,
gfxworld, maptable, maptable_list, maptable_preview_images, trigger_list, objective,
player_outfit, player_role_* , playlists, playlist_global_settings, playlist_schedule,
rank(+table), prestige(+table), rawstring, scriptbundle(+list), scriptparsetree,
scriptparsetreedbg, sound, sprayorgestureitem(+list), storagefile(+list), storeproduct,
storecategory(+list), labelstore(+list), sku, streamkey, stringtable, structured_table,
unlockable_item(+table), weapon, weapon_camo, weapon_tunables, zbarrier`.

> **Important correction to the memory note.** The note says "the `image` pool appears in
> ACTS's BO4 **linker** list, so BO4 image handling exists." That is the **linker** (packing
> an image *into* a new fastfile), line 62 of the README — **not** the dumper. The BO4
> **dumper** pool list above has **no `image`, no `xmodel`, no `xanim`, no `material`.** The
> CLI does expose a `--graphic` flag ("Dump graphic assets"), so *some* image extraction
> likely works, but whether it covers BO4 textures is unconfirmed and must be probed. Treat
> "ACTS extracts BO4 images/models offline" as **unproven**. **[fact + flagged inference]**

### 2.3 GSC / CSC and Lua for BO4 (ACTS + CoDLuaDecompiler) **[fact]**

- **GSC/CSC:** ACTS decompiles BO4 (T8) script. README GSC table: revs **31, 34, 36 =
  full decompiler + compiler**; rev **35 = partial decompiler, no compiler**. The dump path
  decompiles `scriptparsetree` inline (`--scriptsFormatter`, `--disableScriptsDecomp`
  toggles). So: **offline GSC recovery of BO4 Zombies/MP logic is realistic today.**
- **Lua (menus/HUD/LUI):** ACTS dumps the raw `luafile` pool; **CoDLuaDecompiler** (on disk,
  `Games\BlackOps4.cs`) decompiles BO4 Lua to source. This is the BO4 LUI route and pairs
  with the existing [[bo3-ui-port]] work.

### 2.4 Cordycep / Greyhound / Wraith / HydraX — offline vs attach

| Tool | Reads BO4? | Offline (cold files)? | How it works / output | Source |
|---|---|---|---|---|
| **ACTS** (ate47) | **Yes** | **Yes — `--casc`** | Reimplemented FF loaders over CASC; dumps scripts(+decompile), strings, tables, weapons, map/gfx/ent metadata, sounds meta, asset-name lists, compiled zones; `--graphic` for images. | github.com/ate47/atian-cod-tools |
| **Cordycep** (Scobalula/dest1yo) | Yes (via module) | Partly | "Utilises **modified game executables** to load fast files" — patches a game exe and runs its loader to expose asset/string tables for other tools. Built to dodge modern anti-cheat. For BO4 this is the `BlackOps4_dump.exe` route (harness not on disk). ACTS is a "Cordycep-compatible" consumer and also has its own loaders. | github.com/Scobalula/Cordycep (GPL-3) |
| **Greyhound** (Scobalula fork) | Yes (BO4 era) | **No** | Wraith-Archon fork; asset extractor (XModels `.cast/.semodel`, XAnims `.seanim`, images→DDS, sounds). For BO4 it works by **attaching to the running game**. Note on repo: "For titles using Ricochet, Cordycep must be used" (BO4 isn't Ricochet → classic attach). | github.com/Scobalula/Greyhound |
| **Wraith / Wraith Archon** | Older titles + some | **No** | Predecessor of Greyhound; attach-to-process asset ripper. Superseded by Greyhound. | Scobalula |
| **HydraX** | WaW–BO3 era | Yes (loose `.ff`) | Offline fastfile extractor for the *loose-`.ff`* era; does **not** target BO4 CASC. | Scobalula |

**Verdict:** Under our no-launch rule, **ACTS is the only tool that extracts BO4 content
offline from a cold install.** Greyhound/Wraith would give us models/anims/images, but only
by running the game (attach-to-process) — a game-worker job, needs your explicit OK, and is
outside offline recon. **[inference, strong — based on the Cordycep/Greyhound READMEs + our
own BO3 memory note that Greyhound attached to running BO3].**

### 2.5 Realistic offline route per asset class

| Want | Offline route (no running game) | Confidence |
|---|---|---|
| **(a) GSC/CSC scripts** | ACTS `fastfile --casc -G <install> -r bo4` → `scriptparsetree` dumped + decompiled | **High** — core ACTS BO4 feature |
| **(e) asset/string tables** | ACTS same run → `stringtable`, `localize_entry`, `rawstring`, `ddl`, `maptable(_list)`, `weapon*`, `playlists`, `--dumpAssetNames`, `--dumpCompiledZone` | **High** |
| **Lua (LUI)** | ACTS `luafile` pool → CoDLuaDecompiler | **High** |
| **(b) images/textures** | ACTS `--graphic` (unproven for BO4); else Greyhound = **needs game running** | **Low offline / Medium with game running** |
| **(c) models** | Not in ACTS BO4 dumper list → Greyhound = **needs game running** | **Low offline** |
| **(d) sounds** | ACTS dumps `sound` **metadata**; actual audio (viper stream / `.sabs`) likely needs Greyhound/`ffsndr` + running game | **Low offline for audio data** |

---

## 3. Asset inventory (best-effort, offline)

I did **not** extract anything (that is the §7 decision), so no full zone/file listing yet.
What is known cold: **[fact]**

- `bo4.json commonFastFiles` names the zone set the game loads: `core_common`, `mp_common`,
  `mp_common_all`, `mp_common_script`, `wz_common(+all+script)`, **`zm_common`,
  `zm_common_all`, `zm_common_script`** — i.e. MP, Blackout (wz), and **Zombies (zm)** are
  all present as zones inside the CASC.
- `keys_aes.csv` BO4 entries (`cp_common`, `mp_common`, `wz_common`, `zm_common`, 1080/4k
  variants, `*_script`) corroborate the same partition and confirm each has a known key.
- No per-map (`zm_*` / `mp_*`) manifest is readable without a CASC reader; the CASC
  index is content-hash-keyed, not human-named.

**What WOULD produce a full zone/map/file listing (offline):**
`acts fastfile --casc -G <install> -r bo4 --dumpAssetNames --noAssetDump` (list only, no blob
dump) — or `acts casctest <install>` to enumerate the CASC content keys and the loadable
zones. This is light relative to a full dump but still touches the 142 GB index/archives, so
it is part of the §7 "needs your OK" set. **[inference — the flags exist and are the
intended listing path].**

---

## 4. RE angle (flag only — not started)

- `BlackOps4.exe` 114 MB + `BlackOps4_boot.exe` 217 KB (a small bootstrap that launches the
  main exe via the launcher/REV). **[fact]**
- BO4 retail is **packed/anti-tamper protected** (Arxan-style) and the retail exe is
  Battle.net-DRM wrapped — static RE of the stock exe is hard. This is exactly why Cordycep
  exists (patched module to load FFs) and why ACTS ships **byte-pattern `scans`** in
  `bo4.json` rather than fixed offsets. **[inference, consistent with the scan-based design
  on disk].**
- **We do not need to RE the exe to start.** ACTS already publishes BO4 asset-pool structure
  and the `Load_XAsset`/`Load_Stream` scan signatures in `bo4.json`, and the GSC/Lua bytecode
  formats are solved. For a CoD-RE contribution, the cheap win is **documenting the BO4 asset
  pool / XAsset struct from ACTS's open `bo4.json` + bo4-source**, not hand-REing the 114 MB
  packed binary.
- REA/rizin note from [[cod-re-repo]]: native Windows RE of these exes has hit
  `ERR_REA_WINDOWS_NATIVE` here before; don't assume the MCP RE tools will load `BlackOps4.exe`
  directly. **Recommend: do not start exe RE now.**

---

## 5. How it relates to our existing work

- **T6 map porting (our main line):** BO4 ZM is **T8**, a much later IW-engine revision; its
  gfxworld/comworld/xmodel formats are **not** load-compatible with T6/Plutonium. A BO4→T6
  map port is a large, separate porting problem — not a quick win. BO4 assets are more useful
  to us as **study/reference** (how Treyarch built T8 ZM scripts, perks, zbarriers, weapon
  tunables) feeding the T6 tooling than as drop-in content.
- **OAT / our Linker fork:** our OAT fork builds **T5/T6 (and the BO3/BSP work)** fastfiles.
  **Neither OAT nor our fork links T8.** The T8 linker that exists is **ACTS's own `bo4`
  linker** (pools incl. `scriptparsetree`, `luafile`, `image`, `stringtable`, `rawfile`,
  `zbarrier`, …). So if we ever author BO4 content, the toolchain is ACTS + the project-bo4
  shield runtime, a different stack from our OAT line. **[fact from the ACTS README linker
  table].**
- **CoD-RE repo:** a BO4 asset-pool / XAsset struct note derived from ACTS `bo4.json` +
  bo4-source would slot into a new `games/t8-bo4/` folder, consistent with the per-game
  reorg. Same rule as always: **no game assets, no vendored third-party source** — notes and
  our own code only.
- **The "BO4 project later" note:** this recon is that project's groundwork. The tool to
  start from is confirmed: **ACTS**.

### Candidate first projects (ranked by effort ÷ payoff)

| Rank | Project | Needs | Main risk |
|---|---|---|---|
| **1** | **Offline GSC + string/table dump & study of BO4 ZM** (scripts, perks, weapon_tunables, maptable, localize) via ACTS `--casc`. Pure study + a reusable dump script. | Your OK to run ACTS against the install (§7); disk for output (scripts are small). | Decompiler rev mismatch (rev 35 is partial). Low: BO4 PC is rev 34/36 = full. |
| **2** | **BO4 asset-pool / XAsset struct note into CoD-RE** (`games/t8-bo4/`), derived from ACTS `bo4.json` + bo4-source. No game files touched. | Nothing beyond reading ACTS source. | Keeping it clean (no vendored source/assets). Low. |
| **3** | **BO4 image/texture extraction, offline** — prove or disprove ACTS `--graphic` for BO4; if it fails, document that models/images need the game-worker + Greyhound. | §7 OK; a probe. | `--graphic` may not cover BO4 → fallback is attach-to-process (game worker). Medium. |
| 4 | **BO4→T6 ZM asset port** (a model, a zbarrier, a weapon). | Models need Greyhound (game running) + heavy format reconciliation. | Format gulf T8→T6; highest effort. Do not start here. |

---

## 6. Not verified (and the probe that settles each)

1. **ACTS `--casc` dumps a full BO4 ZM zone cold on THIS build (1.23.4.13869365).** Probe:
   `acts casctest <install>` then `acts fastfile --casc -G <install> -r bo4 -a scriptparsetree
   --disableScriptsDecomp -o <out>` on one zone; success = non-zero scripts dumped, no key error.
2. **`--graphic` extracts BO4 images.** Probe: add `--graphic -a image` to a single zone dump;
   success = DDS/image files written.
3. **LPC patch overlay handling.** Probe: `-p` flag against the `LPC\*.ff` + CASC; success =
   patched assets load without `fd`/`fp` errors.
4. **Greyhound BO4 = attach-only (no offline).** Settle via Greyhound wiki/Discord or a
   game-worker test (needs game running — your call).
5. **Exe packing/anti-tamper.** Settle only if/when exe RE is actually wanted (not now).

## 7. Needs your OK before I go further (no-launch / heavy-op gates)

- **Running ACTS against the 142 GB install** — even a listing (`casctest` /
  `--dumpAssetNames`) or a single-zone scripts dump. It is read-only toward the install and
  does **not** launch the game, but it is the "run a dumper against the install" action you
  asked me to flag. **I have not run it.**
- **Anything via Greyhound/Wraith for models/images** requires the game running →
  game-worker territory, explicit OK.
- I did **not** run `BlackOps4.exe`, the launcher, `Launch Project BO4.exe`, or REV.

## 8. Files & hashes

- This report: `E:\ClaudeWork\bo4_recon\RECON.md`
- Hashes recorded in `E:\ClaudeWork\bo4_recon\HASHES.txt` (generated alongside).
