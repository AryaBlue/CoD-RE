# T4 / T5 / T6 scripting: GSC and CSC storage, format and runtime

What E115 needs to load and run the zombies GSC (server) and CSC (client) logic of World at War (T4), Black Ops (T5)
and Black Ops II (T6) without the game executables. Researched 2026-10-26.

## Conventions

- **Path prefixes.**
  - `OAT/` is `<oat_ext checkout>/src/` (our OAT extension checkout). The copy vendored in our b2w fork
    (`<OAT checkout>/src/`) has the same `RawFile` / `ScriptParseTree`
    structs at the same lines.
  - `ACTS/` is `<acts checkout>/src/core/acts/tools/gsc/`, a local source copy of atian-cod-tools.
  - `RE/` is the root of this repository (CoD-RE).
- **Status tags.**
  - **[V]** verified. The source `file:line` or the command is cited.
  - **[I]** inferred or assumed, not checked against the game binary.
  - **[!]** a trap.
- **Scratch work.** Zone dumps, decompiler output and the analysis scripts were kept outside the repo:
  - dumps: `<scratch>/dump/` (OAT `Unlinker.exe --include-assets rawfile|script`);
  - analysis scripts: `<scratch>/py/`
    (`t6hdr.py`, `t6res.py`, `t6op.py`, `t6dev.py`, `txtres.py`).

  None of this content is in the repo, and none of it is quoted here.
- **Zones.** Relative to each game's install:
  - T4: `<WaW install>/zone/english`
  - T5: `<BO1 install>/zone/Common`
  - T6: `<BO2 install>/zone/all`

---

## 1. Storage in fastfiles

### 1.1 Asset types and structs

| Game | Asset type (enum index) | Struct | Buffer contents |
| --- | --- | --- | --- |
| T4 | `ASSET_TYPE_RAWFILE` (32), `OAT/Common/Game/T4/T4.h:47` | `RawFile { const char* name; int len; const char* buffer; }` `T4_Assets.h:4166` | plain text **[V]** |
| T5 | `ASSET_TYPE_RAWFILE` (36), `T5/T5.h:52` | same layout, `T5_Assets.h:5202` | `.gsc`/`.csc`: zlib; other rawfiles plain **[V]** |
| T6 | `ASSET_TYPE_SCRIPTPARSETREE` (48), `T6/T6.h:67`; OAT name `script` | `ScriptParseTree { const char* name; int len; byte32* buffer; }` `T6_Assets.h:2079` | compiled GSC bytecode **[V]** |
| T6 | `ASSET_TYPE_RAWFILE` (41), `T6/T6.h:60` | `RawFile { name; int len; buffer; }` `T6_Assets.h:1904` | `.atr` animtrees (raw deflate), rumble, vision and other files; no scripts **[V]** |

- The enum indices were counted from the `enum XAssetType` blocks (`T4.h:13`, `T6.h:17`), each starting at
  `ASSET_TYPE_XMODELPIECES` = 0 **[V]**.
- ZoneCode loads all three the same way: the name, then `len + 1` buffer bytes in `XFILE_BLOCK_TEMP`:
  `OAT/ZoneCode/Game/T4|T5|T6/XAssets/RawFile.txt` and `.../T6/XAssets/ScriptParseTree.txt` **[V]**.
  - **[!]** `XFILE_BLOCK_TEMP` may be freed after the zone loads **[I]**. E115 must copy the script bytes out while
    the zone is loaded.
- **T5 compression.** `OAT/ObjWriting/Game/T5/RawFile/RawFileDumperT5.cpp:18-113` **[V]**:
  - The buffer is `u32 uncompressedLen, u32 compressedLen`, then a zlib stream that `inflateInit` reads.
  - It applies only when the extension is `.gsc` or `.csc` (line 112).
  - Two T5 `code_post_gfx` scripts dumped as 0-byte files **[V]** (`file` reports `empty`). They are stubs; tolerate them.
- **T4 storage.** The T4 dumper writes the buffer as-is (`OAT/ObjWriting/Game/T4/RawFile/RawFileDumperT4.cpp`), and
  the output is ASCII text **[V]**.
- **T6 animtrees.** `.atr` rawfiles hold a `u32 outLen`, then raw deflate (`inflateInit2(-DEF_WBITS)`):
  `OAT/ObjWriting/Game/T6/RawFile/RawFileDumperT6.cpp:15-92` **[V]**. They decompress to ASCII text **[V]**.
- **T6 scripts.** The T6 script dumper writes the buffer verbatim: `OAT/ObjWriting/Game/T6/Script/ScriptDumperT6.cpp` **[V]**.

### 1.2 Which zones hold a zombies map's scripts

Counts come from `e115_zonedump.exe <zone> --names rawfile|script` and from the OAT dumps **[V]**.

| Game / map | Zone | gsc | csc | Notes |
| --- | --- | --- | --- | --- |
| T4 `nazi_zombie_prototype` | `nazi_zombie_prototype.ff` | 31 | 4 | Map scripts plus the whole `_zombiemode*` set; entry `maps/nazi_zombie_prototype.gsc` `main()` **[V]** |
| | `common.ff` | 245 | 17 | `maps/_load`, `_utility`, `animscripts/*`, 20 `.atr` animtrees; this is SP common, so it includes campaign-only files **[V]** |
| | `code_post_gfx.ff` | 3 | 0 | |
| T5 `zombie_theater` | `zombie_theater.ff` | 34 | 7 | Entry `maps/zombie_theater.gsc` `main()`; plus `clientscripts/zombie_theater.csc` **[V]** |
| | `zombie_theater_patch.ff` | 6 | 2 | Patch overrides **[I]** |
| | `common_zombie.ff` / `common_zombie_patch.ff` | 73 / 56 | 7 / 16 | Shared zombiemode scripts |
| | `code_post_gfx.ff` / `common.ff` | 158 / 92 | 30 / 0 | Engine-side `maps/_*`, `animscripts`, `clientscripts` |
| T6 `zm_nuked` | `zm_nuked.ff` | 24 | 18 | Mostly `character/` and `aitype/` scripts |
| | `zm_nuked_patch.ff` | 29 | 10 | Entry `maps/mp/zm_nuked.gsc` (`main` export **[V]**) and `clientscripts/mp/zm_nuked.csc` |
| | `patch_zm.ff` | 150 | 48 | The bulk of `maps/mp/zombies/_zm_*`, `gametypes_zm`, `animscripts` **[V]** |
| | `common_zm.ff` | 6 | 4 | `codescripts/*` etc. |

- **Patch layering [!].** The same script name appears in more than one zone (283 T6 files gave 266 unique paths
  **[V]**). The `_patch` / `patch_zm` copy should win, which fits load order **[I]**. E115 needs a
  "last loaded wins" script table.
- **Missing T6 includes.** Four includes are not in any of the four T6 zones loaded:
  - `maps/mp/gametypes_zm/_globallogic` (included 10×)
  - `maps/mp/gametypes/_hud_util`
  - `maps/mp/gametypes_zm/_rank`
  - `clientscripts/mp/_vehicle`

  Source: `t6res.py` **[V]**. They are probably in `common_mp`/`patch_mp` or another `_mp` zone **[I]**. Not checked.

---

## 2. Format

### 2.1 T4 and T5: source text

Both games ship the GSC/CSC **source text**. The game compiles it at load time **[V]** (the dumps are C-like text).

The directive counts below come from `txtres.py` over all dumped T4 (297 files) and T5 (481 files) scripts **[V]**.

| Feature | T4 | T5 |
| --- | --- | --- |
| `#include path\file;` (backslash paths, no extension) | 450 | 1071 |
| `#using_animtree("name");` (spacing varies) | 158 | 278 |
| `#animtree` (expression referring to the current tree) | 84 | 47 |
| `/# ... #/` dev blocks | 733 | 1749 |
| `#define`, `#insert`, `#if`, `#using` | 0 | 0 |

- **Scope of the grammar [V by grep; I for exact semantics].** E115 must parse:
  - functions as `name(params) { }` at column 0;
  - `if/else`, `while`, `for`, `switch/case/default`, `break`, `continue`, `return`;
  - `foreach` (T5: 3 hits, likely in comments or identifiers only);
  - `wait <expr>`, `waittillframeend` (T4 123, T5 189);
  - `ent waittill("ev", a, b)`, `ent waittillmatch(...)`, `ent notify("ev", args)`, `ent endon("ev")`;
  - `thread f()` and `ent thread f()`; `childthread` does not occur;
  - function pointers `::f`, `file::f`, and pointer calls `[[ expr ]](args)` (T4 316, T5 846);
  - `%animname` animation references (T4 2670, T5 7139);
  - localised strings `&"REF"` (T4 551, T5 1891);
  - arrays `a[k]` with `.size`;
  - vectors `(x, y, z)`;
  - the globals `level`, `game[...]`, `anim`, `self`;
  - `prof_begin/prof_end` (keyword-like calls).
- **Built-in operators.** `isdefined` is called like a builtin: T4 5648 sites, T5 10917 **[V]**. In T6 it is an opcode
  (§2.2).
- **No preprocessor beyond includes, animtrees and dev blocks [V].** A hand-written recursive-descent parser is
  enough. A shared-subset grammar exists in xensik gsc-tool for the IW/T6 dialects (§3), but it has no T4/T5 front
  end.

### 2.2 T6: compiled bytecode

All 283 T6 scripts dumped from `zm_nuked`, `zm_nuked_patch`, `common_zm` and `patch_zm` start with the magic
`80 47 53 43 0D 0A 00 06` ("\x80GSC\r\n\0\x06", version 6) **[V]**. The file is little-endian on PC.

**Header (0x40 bytes).** `t6hdr.py` validated it on all 283 files **[V]**:

- every offset chains to the next section, with no gaps;
- `fixup_offset == profile_offset == file size`.

ACTS's own `T6GscObj` is a stub with `unk` fields (`ACTS/data/gsc_data_t6.hpp:4-17`). Its commented-out handler uses
the same field names (`ACTS/vm/gsc_vm_t6.hpp:9-286`).

| Off | Type | Field |
| --- | --- | --- |
| 0x00 | u8[8] | magic |
| 0x08 | u32 | source_crc |
| 0x0C | u32 | include_offset |
| 0x10 | u32 | animtree_offset |
| 0x14 | u32 | cseg_offset |
| 0x18 | u32 | stringtablefixup_offset |
| 0x1C | u32 | exports_offset |
| 0x20 | u32 | imports_offset |
| 0x24 | u32 | fixup_offset |
| 0x28 | u32 | profile_offset |
| 0x2C | u32 | cseg_size |
| 0x30 | u16 | name (offset of the C string) |
| 0x32 | u16 | stringtablefixup_count |
| 0x34 | u16 | exports_count |
| 0x36 | u16 | imports_count |
| 0x38 | u16 | fixup_count (0 in all 283) |
| 0x3A | u16 | profile_count (0 in all 283) |
| 0x3C | u8 | include_count |
| 0x3D | u8 | animtree_count |
| 0x3E | u8 | flags (0 in all 283) |

**Section order in the file [V]:** header, string pool, includes, code segment, exports, imports, animtrees, string
fixups, end.

- **Includes.** `u32[include_count]` offsets to path strings, using backslashes, normalised by the loader **[V]**.
- **Exports.** 12 bytes each: `u32 checksum, u32 address, u16 name, u8 param_count, u8 flags` **[V]**.
  - Every export address is 4-aligned.
  - The first byte is opcode `0x17` SafeCreateLocalVariables (4051) or `0x26` CheckClearParams (1131) (`t6op.py`) **[V]**.
- **Imports.** 8 bytes: `u16 name, u16 namespace, u16 num_address, u8 param_count, u8 flags`, then `u32[num_address]`
  code offsets **[V]**. `flags & 0xF` is the call kind. The opcode byte at each site matches **[V]**:

  | Kind | Meaning | Site opcode | Sites |
  | --- | --- | --- | --- |
  | 1 | function reference `::f` | `0x15` GetFunction | 766 |
  | 2 | call `f()` | `0x2E` ScriptFunctionCall | 13295 |
  | 3 | thread `thread f()` | `0x32` ScriptThreadCall | 188 |
  | 4 | method `e f()` | `0x30` ScriptMethodCall | 7757 |
  | 5 | method thread | `0x34` ScriptMethodThreadCall | 1628 |

  - `flags & 0x10` marks calls inside dev blocks. 852 imports and 410 names, e.g. assert, println, print3d, line
    (`t6dev.py`) **[V]**.
- **Animtrees.** Each entry is `u16 name, u16 num_tree_refs, u16 num_anim_refs, u16 pad`, then `u32[num_tree_refs]`,
  then `num_anim_refs × {u32 name, u32 address}`. The size is verified by chaining **[V]**. The field meanings are **[I]**.
- **String fixups.** `u16 string, u8 count, u8 type`, then `u32[count]` code addresses where the loader writes the
  runtime string id **[V]** (size). `type` is 0 or 1, probably canonical vs dev string **[I]**.
- **Totals over 283 files [V].** 5182 exports, 10322 imports, 27845 string-fixup entries.

**Opcode table (T6 PC, 0x00-0x7C).** It is taken from the opcode map in a comment at `ACTS/opcodes/gsc_opcodes_t6_01.hpp:58-173`.
Lines ~44-56 register only 0x00-0x0B live.

The entry and site checks above confirm `0x15`, `0x17`, `0x26`, `0x2E`, `0x30`, `0x32` and `0x34` **[V]**. The
rest are **[I]**, but agree with gsc-tool decompiling every file cleanly (§3).

| Range | Opcodes |
| --- | --- |
| 00-0B | End, Return, GetUndefined, GetZero, GetByte, GetNegByte, GetUnsignedShort, GetNegUnsignedShort, GetInteger, GetFloat, GetString, GetIString |
| 0C-15 | GetVector, GetLevelObject, GetAnimObject, GetSelf, GetLevel, GetGame, GetAnim, GetAnimation, GetGameRef, GetFunction |
| 16-28 | CreateLocalVariable, SafeCreateLocalVariables, RemoveLocalVariables, EvalLocalVariableCached, EvalArray, EvalLocalArrayRefCached, EvalArrayRef, ClearArray, EmptyArray, GetSelfObject, EvalFieldVariable, EvalFieldVariableRef, ClearFieldVariable, SafeSetVariableFieldCached, SafeSetWaittillVariableFieldCached, ClearParams, CheckClearParams, EvalLocalVariableRefCached, SetVariableField |
| 29-35 | CallBuiltin, CallBuiltinMethod, Wait, WaitTillFrameEnd, PreScriptCall, ScriptFunctionCall, ScriptFunctionCallPointer, ScriptMethodCall, ScriptMethodCallPointer, ScriptThreadCall, ScriptThreadCallPointer, ScriptMethodThreadCall, ScriptMethodThreadCallPointer |
| 36-53 | DecTop, CastFieldObject, CastBool, BoolNot, BoolComplement, JumpOnFalse, JumpOnTrue, JumpOnFalseExpr, JumpOnTrueExpr, Jump, JumpBack, Inc, Dec, Bit_Or/Xor/And, Equal, NotEqual, LessThan, GreaterThan, LessThanOrEqualTo, GreaterThanOrEqualTo, ShiftLeft, ShiftRight, Plus, Minus, Multiply, Divide, Modulus, SizeOf |
| 54-5B | WaitTillMatch, WaitTill, Notify, EndOn, VoidCodePos, Switch, EndSwitch, Vector |
| 5C-6F | GetHash, RealWait, VectorConstant, IsDefined, VectorScale, AnglesToUp, AnglesToRight, AnglesToForward, AngleClamp180, VectorToAngles, Abs, GetTime, GetDvar, GetDvarInt, GetDvarFloat, GetDvarVector, GetDvarColorRed/Green/Blue/Alpha |
| 70-7C | FirstArrayKey, NextArrayKey, ProfileStart, ProfileStop, SafeDecTop, Nop, Abort, Object, ThreadObject, EvalLocalVariable, EvalLocalVariableRef, DevblockBegin, DevblockEnd |

- **[!] Intrinsics.** IsDefined, GetTime, GetDvar*, VectorScale, AnglesTo* and Abs are opcodes in T6, not builtin
  calls. In T4/T5 text they look like normal calls.
- **[!] Alignment.** Operands are aligned: export entries are 4-aligned **[V]**, and ACTS sets `VMF_ALIGN`
  (`gsc_opcodes_t6_01.hpp:12`). The exact padding rules per operand type are **[I]**. Take them from gsc-tool's T6
  disassembler.

**How a call is resolved (T6).**

1. The compiler always emits a *script* call opcode at the site and lists the callee in the import table **[V]**.
   This covers builtins too: `assert` sites carry `0x2E`.
2. An import with a non-empty `namespace` names `file::func` (e.g. `maps/mp/zombies/_zm_stats`).
3. An empty namespace (9122 of 10322 imports) means "this file or its includes".
4. If that lookup fails, the name is a builtin **[V]**. With this rule, every import resolved in `t6res.py` except
   the ones that go to the four missing includes.
5. At link time the engine looks the name up (the retail server has `Scr_GetFunctionHandle` in
   `cscr_obj_compiler.obj`, `RE/games/t6-bo2/notes/t6zm_all_functions.tsv:5171`, and `Scr_GetFunction`, line 2590).
   It then patches each site: the opcode becomes CallBuiltin/CallBuiltinMethod or keeps the script call, and the
   aligned operand slot gets the resolved pointer or function id **[I]**.
6. The string fixups do the same for string constants, via `SL_GetCanonicalString` (`tsv:5170`) **[I]**.

E115 can do the same linking in its own VM. No original IDs are needed, because T6 stores names, not indices **[V]**.

---

## 3. Is the source recoverable?

| Game | Status |
| --- | --- |
| T4, T5 | Nothing to recover: the zones hold the source **[V]**. |
| T6 | **xensik gsc-tool** 1.6.1 (`gsc-tool.exe -m decomp -g t6 -s pc`) decompiled **283/283** dumped scripts, each reporting `decompiled`, with no errors **[V]**. The output kept all 1109 `#include` and 21 `#using_animtree` directives, and `zm_nuked.gsc` has `main()` **[V]**. gsc-tool also has `comp`, `asm` and `disasm` for T6 PC/PS3/X360/WiiU, plus a `--t6fixup` flag for files from broken compilers (help output **[V]**; https://github.com/xensik/gsc-tool **[V]**). |
| T6 in ACTS | atian-cod-tools does **not** support T6. Its T6 handler is commented out in full (`ACTS/vm/gsc_vm_t6.hpp:9-286`, `REGISTER_GSC_VM` at line 285 is inside the comment). Only opcodes 0x00-0x0B are registered (`ACTS/opcodes/gsc_opcodes_t6_01.hpp`). It targets `VMI_T6_01 = 0x01000a0d43534780` (version byte 0x01), but PC files are version 0x06; `VMI_T6_06` is declared but unused (`ACTS/gsc_opcodes_load.hpp:20-21`) **[V]**. The README's GSC table lists T7-T10/JUP/SAT, not T6 (https://github.com/ate47/atian-cod-tools **[V]**). |

**Two routes for E115's T6 support:**

- **(a)** Run the bytecode directly. This is the faithful route, and the format above is fully mapped.
- **(b)** Decompile at install time to text and use one front end for all three games. Decompiler output is not
  guaranteed to round-trip.

---

## 4. Runtime model

Unless a line is tagged otherwise, this section is **[I]**: it is long-standing community knowledge of the
Quake3-derived CoD script VM, consistent with the opcodes and keyword counts above.

### 4.1 Threads

- Every `thread` call creates a cooperative coroutine with its own locals and its own `self`.
- Nothing pre-empts a thread. It runs until it reaches `wait` (time, in server frames: 20 Hz in T4/T5 SP and T6 ZM
  servers), `waittillframeend`, `waittill`, or until it returns.
- Execution is single-threaded and deterministic in order: the scheduler resumes the wait queues once per frame.

### 4.2 Events

- `ent notify("ev", args...)` wakes every thread in `ent waittill("ev", ...)` on that object. It runs them
  synchronously, before `notify` returns.
- `ent endon("ev")` kills the calling thread when `ent` gets `"ev"`, or when `ent` is freed: the `"death"` and
  `"entityshutdown"` paths.
- `waittillmatch` filters on the first argument. AI notetracks, for example, use it.
- Usage in the shipped scripts **[V]** (`txtres.py`):

  | | endon | notify | waittill | wait |
  | --- | --- | --- | --- | --- |
  | T4 | 1729 | 1004 | 794 | 1001 |
  | T5 | 2974 | 1717 | 1298 | 2024 |

  T6 encodes the same as opcodes 0x54-0x57, 0x2B and 0x2C **[V]** (table).

### 4.3 Values and objects

- **Types.** undefined, int, float, string, localised string, vector, array, struct (`spawnstruct()`), entity,
  function pointer, animation, animtree.
- **Copy rules.** Arrays are copied on assignment. Structs and entities are references. CoD-RE's reference VM uses
  these rules: `RE/games/t6-bo2/perks/tests/livevm.cpp:1-3` **[V]** (our own code).
- **Global objects.** `level` (one global struct), `game` (survives map restarts), `anim` (the animscripts global)
  and `self`. T6 has GetLevel, GetGame, GetAnim and GetSelf as opcodes, and ACTS registers `level`, `game` and
  `anim` as VM globals (`gsc_opcodes_t6_01.hpp:20-22`) **[V]**.
- **Fields.** Entities, structs and hud elements carry script-defined fields, which are dynamic, plus *code fields*
  backed by engine memory. Code fields: `origin`, `angles`, `classname`, `targetname`, `target`, `health`,
  `maxhealth`, `model`, `team`, `script_noteworthy`, `spawnflags`, `radius`, `height`, `takedamage`, `goalradius`
  (AI) and `sessionstate` (player).

  The T5 usage counts are **[V]**: `.origin` 3839, `.angles` 1128, `.script_noteworthy` 753, `.target` 397,
  `.health` 396, `.team` 372. Whether each one is a code field is **[I]**.
- **Entity lookup.** Most lookups are `getent`/`getentarray(value, key)` keyed by `targetname`, `classname` or
  `script_noteworthy` **[V]**. E115's map entity strings, which already load, are the data source.
- **Engine-side symbols for T6 [V]** (`RE/games/t6-bo2/notes/t6zm_all_functions.tsv`, matched by name from the
  symbolled `CoDMPServer_PC.exe`):
  - `Scr_AddEntity` (2646), `Scr_ExecEntThread` (2650), `Scr_Notify` (2651);
  - `Scr_SetObjectField` / `Scr_GetObjectField` (2661-2662), `Scr_LoadScript` (5155);
  - `VM_CancelNotify` (5294) and the `SL_*` string list (5200-5224).
- **Builtin implementations per family in that table [V]** (rough proxies, not table sizes):

  | Family | Count |
  | --- | --- |
  | `GScr_` | 245 |
  | `Scr_` | 246 |
  | `PlayerCmd_` | 85 |
  | `ScrCmd_` | 42 |
  | `CScr_` (client) | 150 |
  | `CScrCmd_` | 28 |

- **Not determined.** The exact size of each game's builtin function and method tables (T4/T5/T6). Extract it from
  the function-def arrays behind `Scr_GetFunction` / `Scr_GetMethod` in t6zm.exe, and the equivalents in
  T4/T5, with REA if needed.

---

## 5. Builtins the zombies scripts actually call

| Game | Script set | Functions | Methods | Call sites | Method |
| --- | --- | --- | --- | --- | --- |
| T6 GSC | 198 files of zm_nuked + patch, common_zm, patch_zm | 274 (253 outside dev blocks) | 421 (415) | 9866 (8242) | Imports not resolved to any loaded export, after include-chasing (`t6res.py`) **[V]** |
| T6 CSC | 73 files | 142 (134) | 100 (100) | 1544 (1282) | same **[V]** |
| T4 GSC | 276 files (prototype + SP `common`) | 247 | 372 | 20450 | Text heuristic: `name(` not defined in any loaded file, split function/method by the preceding token (`txtres.py`) **[V]** |
| T4 CSC | 21 files | 75 | 18 | 878 | same **[V]** |
| T5 GSC | 419 files (theater + patches, common_zombie(+patch), code_post_gfx, common) | 274 | 444 | 36287 | same **[V]** |
| T5 CSC | 62 files | 185 | 78 | 4003 | same **[V]** |

Caveats:

- **[!] T4/T5 overcount.** The T4/T5 counts include campaign-only scripts from the SP `common`/`code_post_gfx` zones,
  so they are high.
- **[!] False positives.** Script functions from unloaded files count as builtins, e.g. T4 `destructible_state` and
  `destructible_part`, and T6 names from the four missing includes.
- **Reading the counts.** Treat them as "about 600-700 server and about 200-250 client builtins per game to reach
  full coverage". In each game, about 20 names cover most call sites.

**Most-called names [V] (identifier list only):**

- Functions:
  - T6 GSC: assert, println, setdvar, loadfx, getentarray, precachemodel, int, isplayer, spawnstruct, randomint,
    spawn, isalive, distancesquared.
  - T4/T5 add isdefined, gettime and getdvar, which are opcodes in T6.
- Methods: delete, playsound, setmodel, sethintstring, settext, hasperk, getentitynumber, getcurrentweapon,
  fadeovertime, hasweapon, giveweapon, takeweapon, linkto, setanim, clearanim, gettagorigin.
- CSC: println, loadfx, playsound, playfx, playfxontag, getlocalplayers, registerclientfield (T6), getarraykeys.

---

## 6. Licensing

| Source | Licence | Reuse in GPL-3 E115 |
| --- | --- | --- |
| OpenAssetTools (oat_ext and vendored copy) | GPL-3 (`oat_ext\LICENSE`, `vendor\OpenAssetTools\LICENSE`) **[V]** | Yes. The struct and ZoneCode definitions above can be used directly. |
| xensik gsc-tool | GPL-3 (https://raw.githubusercontent.com/xensik/gsc-tool/dev/LICENSE; also ACTS's `licenses/licenses.md`, "GPL-3 dependencies") **[V]** | Yes, with attribution. This is the best reference for the T6 disassembler, operand alignment and IW-family VM semantics. Only the local binary is present, not the source. |
| atian-cod-tools (ACTS) | Dual GPL-3 or MIT (ACTS `licenses/licenses.md:1`); its GPL-3 build pulls in xensik/gsc **[V]** | Yes, but there is little T6 code to reuse (§3). Its T7+ VM and decompiler are useful as design references. |
| CoD-RE | GPL-3 (`LICENSE`, README line 5) **[V]** | Yes. It is our own work; credit the sources per CoD-RE `CREDITS.md`. |
| Game scripts, dumps, decompiled output | Activision copyright **[I]** | Never commit or ship them. Load them at runtime from the user's install, the same as the other assets. |
| Plutonium, retail exes | Closed **[I]** | Facts and names only (e.g. the tsv), no copied code. |

---

## Implications for E115

### Smallest first vertical slice

Headless T6 bytecode, because the format is fully mapped and needs no parser:

1. **Load.** Pull every `script` asset from the map's zone stack into a name→buffer table, last loaded wins, and
   copy the buffers out of TEMP memory.
2. **Link.**
   - Parse the header, exports, imports and string fixups.
   - Resolve imports: namespace first, then the file and its includes, then a builtin table.
   - Unknown builtins bind to a logging stub, so a link never fails.
3. **Run.**
   - Write an interpreter for about 40 opcodes: constants, locals, fields on `level` and structs, calls, `wait`,
     `notify`, `waittill`, `endon`, jumps, compares and arithmetic.
   - Add a cooperative scheduler stepped at 20 Hz on a fixed clock.
4. **Builtins.** Start with about 10: `println`, `assert` (and skip dev-flag sites), `spawnstruct`, `getentarray`
   over the parsed map entities, `isplayer`, `randomint`, `int`, `gettime`, `setdvar`/`getdvar*` on a dvar map.
5. **Test.** Call `main` of `maps/mp/zm_nuked.gsc` headless. It is expected to run until it hits the first missing
   builtin **[I]**.

Before that, a unit test on a hand-assembled or gsc-tool-compiled tiny script, built locally and never committed,
should prove that `thread`, `wait 0.05`, `notify`, `waittill` and `endon` behave correctly.

**Then T4/T5.** Write one lexer and parser for the shared text dialect (§2.1) that compiles into the same internal IR
or bytecode. This reuses the T6 VM and scheduler. The text front end is the larger piece of work.

### Main risks

1. **Builtin surface.** About 700 server and 250 client builtins per game (§5), many tied to subsystems that do not
   exist yet: AI and animscripts, weapons, HUD, sound, physics, navmesh, vehicles. Plan for stubs plus a call-count
   log to prioritise.
2. **Semantics fidelity.**
   - notify ordering, `endon` on entity free, array copy semantics, `waittillframeend`;
   - string canonicalisation, which is case-insensitive;
   - int/float rules, undefined propagation.

   Subtle differences break round logic silently. A differential test harness against a real game, such as the
   existing livevm approach, is valuable.
3. **Animscripts.** `animscripts/*` and the `#using_animtree`/`%anim` paths need the xanim and animtree runtime. Zombie
   AI cannot run without them.
4. **Client/server split.** CSC needs a client-side VM instance with `localClientNum` semantics and clientfields (T6),
   which is a second runtime context.
5. **T6 unknowns.**
   - operand alignment per opcode;
   - the meaning of the animtree record fields and of string fixup `type`;
   - the four includes not found yet.

   Confirm them with gsc-tool `disasm` before writing the interpreter.
6. **T4/T5 parser coverage.** It is undocumented: the grammar is inferred from the corpus, and the T4 files that
   come from mods may differ. Test-parse every shipped script as a CI gate, using local files only.
