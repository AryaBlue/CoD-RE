# BO3 (T7) fastfile + inline GfxImage layout

Worked out on BO3 PC (`version 0x251`) core/frontend fastfiles. Offsets are little-endian.
Decoders live in [`../tools/zone/`](../tools/zone/).

## Fastfile container

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[8] | magic `TAff0000` |
| `0x08` | u32 | version `0x251` |
| `0x90` | u64 | total decompressed size |
| `0x248` | — | start of the block chain |

The body is a chain of blocks, each a single zlib stream:

```
u32 compressed      bytes of zlib payload
u32 decompressed    bytes after inflate
u32 stored          payload span used to advance (>= compressed)
u32 offset          == the block header's own file position (integrity check)
... compressed bytes ...
```

Advance by `16 + stored`. A block with `decompressed == 0` is **filler**: skip to the next
`0x800000` (8 MB) boundary. Stop once the written total reaches the header's decompressed size.
BO3 PC core/frontend fastfiles are **not** AES-encrypted (unlike T8), so zlib alone recovers the zone.

## Inline GfxImage

UI art is *resident* in the zone (not streamed to a `.xpak`), so the pixels sit inline. Each record
ends with its asset name as a NUL-terminated string; fields are read **relative to the name**:

| Rel. to name start | Type | Meaning |
|--------------------|------|---------|
| `-72` | u16, u16 | width, height |
| `-48` | u64 | `0xFFFFFFFFFFFFFFFF` — inline pointer sentinel |
| `-32` | u64 | data size |
| `-24` | u64 | DXGI format id |
| `-16` | u64 | `0xFFFFFFFFFFFFFFFF` — inline pointer sentinel |
| after name's NUL | — | pixel data (mip 0 first) |

Top-mip size = block-compressed: `ceil(w/4)*ceil(h/4)*blockBytes` (BC1/4 = 8, BC2/3/5/6/7 = 16);
uncompressed: `w*h*bpp`. DXGI sRGB ids share bits with their UNORM twin (`72→71`, `75→74`,
`78→77`, `99→98`); decode via the UNORM id. BGRA8 (ids 87/91) needs an R/B swap.
