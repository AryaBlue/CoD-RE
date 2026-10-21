# BO4 / T8 XModel Asset-Name Hash — spec + reference impl + test vectors

Blocker-fix deliverable: the EXACT function to turn a BO4 XModel name (or a Greyhound rip folder
name) into the 64-bit value stored in the zone's `XModel.name` / `NamePtr` field, so hashed
xmodel pointers can be matched to rip folder names without false matches.

**TL;DR:** It is a standard **FNV-1a-64** (offset basis `0xCBF29CE484222325`, prime
`0x100000001B3`) over the **lower-cased, backslash→forward-slash normalised bare name**, then
**masked to the low 60 bits** (`& 0x0FFFFFFFFFFFFFFF`). Mask BOTH the computed hash AND the
stored `NamePtr` to 60 bits before comparing. The XModel name hash is **NOT** the same value as
the XPAK mesh stream key (see §4).

---

## 1. Algorithm (confidence: RIPPER-VERIFIED + UNLINKER-SOURCE, cross-confirmed)

| Parameter | Value | Note |
|---|---|---|
| Scheme | FNV-1a, 64-bit (XOR byte, then multiply) | not FNV-1 |
| Offset basis (seed) | `0xCBF29CE484222325` | ACTS calls this `FNV1A_PRIME` (misnamed) |
| Prime (multiplier) | `0x100000001B3` | ACTS calls this `IV_DEFAULT` |
| Result mask | `& 0x0FFFFFFFFFFFFFFF` (low **60 bits**) | top nibble = type/flag bits, must be cleared |
| Extra seed / XOR | **none** | plain FNV-1a, no salt |

- **Greyhound `BO4CalculateHash` (RIPPER-VERIFIED):** `Result = 0xCBF29CE484222325; for each
  byte: Result ^= b; Result *= 0x100000001B3; return Result & 0xFFFFFFFFFFFFFFF;` — i.e. FNV-1a
  with a **60-bit** mask. Greyhound's BO4 pool loader also masks the stored pointer:
  `Asset.NamePtr &= 0xFFFFFFFFFFFFFFF;`. Because Greyhound provably resolves real BO4 model
  names via its `fnv1a_xmodels.wni` using exactly this, **60-bit is the correct width** — a
  63-bit or unmasked compare leaves stray high bits and causes exactly the false/missed matches
  seen (this is almost certainly the "wrong variant" bug).
- **ACTS `hash::Hash64` (UNLINKER-SOURCE):** same FNV-1a core (`FNV1A_PRIME` basis, `IV_DEFAULT`
  prime). ACTS additionally **lower-cases A→a and converts `\`→`/`** per-char (its `lowerc()`
  helper) before hashing, and its generic `Hash64` masks to **63 bits** (`MASK63 =
  0x7FFFFFFFFFFFFFFF`). The 63-bit mask is ACTS's cross-game default; for BO4 the real stored
  width is 60-bit, so use 60. Take the **normalisation from ACTS** (lowercase + backslash) and
  the **60-bit mask from Greyhound** — this is the safe union. (Greyhound skips normalisation
  only because its `.wni` names are already lower-case; feeding any upper-case/`\` name without
  normalising would mis-hash.)

## 2. Input normalisation (confidence: UNLINKER-SOURCE)

1. Hash the **bare asset name as stored** (e.g. `p7_zm_escape_tacsit_table`), **not** a full
   path and **no** added prefix/extension. (The `xmodel/` virtual prefix etc. is not part of the
   hashed string.)
2. **Lower-case** ASCII `A`–`Z` → `a`–`z`.
3. Convert every backslash `\` → forward slash `/`.
4. Hash the resulting bytes (ASCII/UTF-8 single bytes) with FNV-1a, then mask 60-bit.

Steps 2–3 are no-ops for already-lower-case, slash-free model names (the common case), which is
why Greyhound's un-normalised function still matches — but keep them for correctness.

## 3. Reference implementation (self-contained Python)

```python
def bo4_xmodel_name_hash(name: str) -> int:
    """BO4/T8 XModel asset-name hash: FNV-1a-64, normalised, masked to 60 bits.
    Matches Greyhound's BO4CalculateHash and the zone XModel.name (after &0x0FFF.. on both)."""
    FNV_OFFSET = 0xCBF29CE484222325   # seed  (ACTS 'FNV1A_PRIME')
    FNV_PRIME  = 0x100000001B3        # mult  (ACTS 'IV_DEFAULT')
    MASK60     = 0x0FFFFFFFFFFFFFFF   # low 60 bits; clears the top type-tag nibble

    h = FNV_OFFSET
    for ch in name:
        c = ord(ch)
        if 0x41 <= c <= 0x5A:   # 'A'..'Z' -> lower-case
            c += 0x20
        elif c == 0x5C:         # '\' -> '/'
            c = 0x2F
        h = (h ^ (c & 0xFF)) * FNV_PRIME
        h &= 0xFFFFFFFFFFFFFFFF  # keep 64-bit during the loop
    return h & MASK60

def matches_zone_namePtr(name: str, stored_namePtr: int) -> bool:
    # ALWAYS mask the stored field too — the zone value carries a top-nibble tag.
    return bo4_xmodel_name_hash(name) == (stored_namePtr & 0x0FFFFFFFFFFFFFFF)
```

## 4. CRITICAL: XModel name hash vs XPAK data-key — DIFFERENT (flag)

**They are not the same value.** (confidence: HIGH for models; the function is only *reused* for
image keys, not model-mesh keys.)
- The **XModel asset-name hash** (this doc) identifies the asset in the zone's XModel pool.
- The **XPAK mesh stream key** is the model LOD's `LODStreamKey` — an opaque per-LOD content/
  stream key stored in the LOD struct and looked up directly in the `.xpak` hash table
  (`BO3XPakHashEntry.Key`). A single model has several LODs each with its *own* distinct key, so
  it **cannot** be the model-name hash. Do **not** try to match xmodel folder names via any xpak
  key.
- Caveat / nuance: XPAK **image** entries *are* keyed by the 60-bit FNV-1a of the image **name**
  (the same core function as §1, via the index `name:` property masked `& 0x0FFF...F`). So the
  function is reused for image keys — but that is images, not model meshes, and still is a hash
  of a *name*, not a model's mesh stream key. For the xmodel-matching task, use §3 only.

## 5. Test vectors (verify your implementation)

**5a. Core FNV-1a-64 (unmasked) — official FNV reference vectors**, independently reproduced by
Zig/Go/Rust/Boost test suites. Use these to prove your FNV-1a core (basis/prime, XOR-then-mul)
is right before masking:

| input | FNV-1a-64 (full) | & 0x0FFFFFFFFFFFFFFF (BO4 60-bit) |
|---|---|---|
| `""` (empty) | `0xCBF29CE484222325` | `0x0BF29CE484222325` |
| `"a"` | `0xAF63DC4C8601EC8C` | `0x0F63DC4C8601EC8C` |
| `"foobar"` | `0x85944171F73967E8` | `0x05944171F73967E8` |

(All three inputs are already lower-case and slash-free, so normalisation is a no-op — they
isolate the FNV core + the 60-bit mask. The 60-bit column = clear the top hex nibble.)
Sanity guard: FNV-1 (non-"a") of `"a"` is `0xAF63BD4C8601B7BE` — if you get that, you wrongly
implemented FNV-1 (multiply-then-XOR) instead of FNV-1a.

**5b. Ground-truth for REAL model names:** cross-check against Greyhound's own
`package_index/fnv1a_xmodels.wni` (a binary hash→name index of actual BO4 models; 60-bit keys).
That file is the authoritative "source/test data" for live model-name↔hash pairs — pick any
entry, feed its name through §3, and confirm you reproduce its stored 60-bit key. (I did not
read the binary `.wni` here — it is the recommended on-disk verification set for the worker.)

## 6. Sources (read-only; nothing cloned or run)

- Scobalula/Greyhound @ `22c3d17`, `src/WraithXCOD/WraithXCOD/GameBlackOps4.cpp` —
  `BO4CalculateHash` (L738-751, 60-bit mask) + pool loader `NamePtr &= 0xFFFFFFFFFFFFFFF`
  (L779) + `.wni` cache load (L2586-2593).
  https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/GameBlackOps4.cpp
  (local copy: `E:\ClaudeWork\bo4_recon\_src\gh_GameBlackOps4.cpp`)
- ate47/atian-cod-tools @ `main`, `src/core/shared/utils/hash.hpp` (`Hash64`/`Hash64A`/`lowerc`
  normalisation, `MASK63`) and `src/core/shared/utils/hash_mini.hpp` (`FNV1A_PRIME =
  0xcbf29ce484222325`, `IV_DEFAULT = 0x100000001b3`, `MASK60 = 0xFFFFFFFFFFFFFFF`, `MASK63 =
  0x7FFFFFFFFFFFFFFF`). `XHash` struct uses `hash::Hash64` for name equality
  (`src/core/shared/games/bo4/pool.hpp`, local `_src\act_bo4_pool_enum.hpp`).
  https://github.com/ate47/atian-cod-tools/blob/main/src/core/shared/utils/hash_mini.hpp
- FNV-1a 64-bit reference test vectors confirmed across Zig std, Go, Rust, Boost.hash2
  implementations (`"a"`=0xAF63DC4C8601EC8C, `"foobar"`=0x85944171F73967E8, `""`=offset basis).

**Confidence:** algorithm + 60-bit mask = **HIGH** (RIPPER-VERIFIED by Greyhound, which resolves
real BO4 names with it). Normalisation details = **HIGH** (ACTS source). "Different from XPAK
mesh key" = **HIGH** for model meshes (per-LOD opaque keys), with the noted caveat that the same
hash function is reused for xpak *image-name* keys.
