# Black Ops III (T7) — XModel asset-pool base offset

Reverse-engineered 2026-10-20 to repair the memory-based map extractor **C2M**
(vugi99 fork of Scobalula's Husky) for the current retail Black Ops III build.
Source-only RE; no game assets here.

## Target build
- `BlackOps3.exe`, Steam appid 311210 (retail), build string `100.2.2.7.109.0`.

## Finding
C2M/Husky locate every asset from a single hardcoded **assetPools table** base,
used as an RVA from the module base. That constant went stale after a Steam
auto-update, which is what makes C2M report
*"Black Ops 3 is supported, but this EXE is not"*.

| | value |
|---|---|
| old (C2M 1.0.6.2 / Husky) | `module_base + 0x94073F0` |
| **this build (100.2.2.7.109.0)** | **`module_base + 0x93883F0`** |
| delta | `-0x7F000` |

The struct **layout is stable across patches** — only this base constant moved.

## assetPools table layout (confirmed against live memory)
- Entry stride **0x20 bytes**, one entry per asset type: `{ void* pool; int itemSize; int itemCount; ... }`.
- **XModel pool = entry 4 → `base + 0x80`.** First pooled XModel derefs to the
  stock sanity model named `"void"`; `itemSize 0x188` (= `sizeof(XModel)` = 392),
  count 11264. This is the check C2M uses to accept the build.
- **GfxMap pool = `base + 0x200`** (entry 16).
- **mapEnts    = `base + 0x1E0`** (entry 15).

Validation: entry-4 first name read `"void"`; neighbours are pool-shaped
`{pointer, itemSize, count}` (e.g. the XAnim pool at entry 3 had count 25200);
decoys at `base-0x20` (xanim) and a nearby `itemSize 258 / count 0` block were
ruled out.

## GfxMap / GfxWorld read offsets (from C2M source, used with the corrected base)
- GfxMap: `name` @ 0x0, `surfaceCount` @ 0x18, `vertexCount` @ 0x268,
  positions @ 0x270 (12B x,y,z float), vtxData @ 0x288 (20B color/uv/normal),
  indices @ 0x2A0 (u16), surfaces @ 0x430
  (stride 0x60: vbOffset@0xC, vtxCount@0x28, faceCount@0x2A, faceIndex@0x2C, matPtr@0x48),
  staticModels @ 0x438 (stride 0x98: pos@0, 3x3 matrix@0xC, scale@0x30, modelPtr@0x58).

## Method / constraints
- **Static RE is not viable:** retail `BlackOps3.exe` is Arxan-protected — on-disk
  entropy is 7.9+ on both `.text` sections and `.rdata`, so code/strings/xrefs are
  encrypted until runtime. The offset is only recoverable from a **running**
  process. The assetPools table lives in `.data`'s BSS region — zero on disk,
  filled at runtime (`.data` raw size `0x3a3600`, virtual `0x175d6360` from
  va `0x3252000`), so the search window is `base+0x3252000+0x3a3600 .. +0x175d6360`.
- Recovered by **read-only** memory inspection (`ReadProcessMemory`) of the live
  game with the target map loaded. No modification to the game process.
- A signature scan of that BSS window for the table whose entry-4 deref reads
  `"void"` makes any tool **self-healing** across future BO3 patches — preferred
  over a hardcoded constant, which re-breaks on every update.

## Fix location
Applied in our C2M fork — `github.com/AryaBlue/C2M`,
`src/Husky/Husky/HuskyUtil.cs`, the `Games` dictionary `BlackOps3` row
(`GameDefinition` Item1 = assetPools base). The `+0x80 / +0x200 / +0x1E0` usage in
`Games/BlackOps3.cs` is unchanged. Credit chain: Scobalula (Husky) →
SHEILAN/vugi99 (C2M) → this fork. GPL-3.0.
