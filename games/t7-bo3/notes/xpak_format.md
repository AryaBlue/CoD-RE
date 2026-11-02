# BO3 (T7) XPAK format

Container for streamed assets (images, etc.) in Black Ops 3. Magic `KAPI`
(`0x4950414B`), version `0x0A`. Reverse-engineered with reference to Scobalula's
Greyhound (`XPAKCache.cpp`, `DBGameFiles.h`); the implementation in
[`../tools/xpak`](../tools/xpak) is our own.

## Header (offsets; all uint64 unless noted)
```
0x00 Magic u32  | 0x04 Unknown1 u16 | 0x06 Version u16
0x10 Size       | 0x18 FileCount    | 0x20 DataOffset | 0x28 DataSize
0x30 HashCount  | 0x38 HashOffset   | 0x40 HashSize
0x48 Unknown3   | 0x50 UnknownOffset| 0x58 Unknown4
0x60 IndexCount | 0x68 IndexOffset  | 0x70 IndexSize
```

## Hash table  (at HashOffset, HashCount entries × 24 bytes)
```
{ u64 Key; u64 Offset; u64 Size; }
```
`Offset` is **relative to DataOffset**, so the real file offset of a blob is
`DataOffset + Entry.Offset`. `Size` is the compressed/stored size.

## Index table  (at IndexOffset) — self-describing text metadata, per entry
```
{ u64 Key; u32 TextLen; u32 reserved; char Text[TextLen] }
```
`Text` is `key:value` lines including `name`, `type`, `format` (e.g. `BC7_SRGB`),
`width`, `height`, `levels`, `semantic`, and per-mip `offsetN` / `sizeN`. `Key`
matches the hash-table `Key`. Because the package names and describes its own
images, no `.ff` parsing and no FNV name-hashing are needed to pull assets.

## Data blob decompression (`DecompressPackageObject`)
A blob is a sequence of 128-byte group headers:
```
{ u32 Count; u32 Offset; u32 Commands[30]; }   // sizeof = 128
```
For each `i` in `0 .. Count`:
```
blockSize = Commands[i] & 0xFFFFFF
flag      = Commands[i] >> 24
  flag 0x0 = raw memcpy
  flag 0x3 = LZ4 block
  flag 0x6 / 0x8 = Oodle (later titles only)
```
After a group's commands are consumed, align the read position **up** to the next
`0x80` boundary, then read the next group.

## Observed in practice
Many large textures are stored **raw** (`flag 0x0`), in groups of 8 blocks of
`0x7FF0` bytes per `0x40000` region — e.g. `BC7_SRGB` 1024×1024, `levels=1`
(single mip), blob ≈ `1048576` raw + framing. BO3 uses **LZ4** (not Oodle) for its
compressed blocks; a stock BO3 install ships no `oo2core` DLL, consistent with no
Oodle on this title. Later CoD titles that reuse the XPAK container do use Oodle
(`flag 0x6/0x8`), which this offline reader does not implement.
