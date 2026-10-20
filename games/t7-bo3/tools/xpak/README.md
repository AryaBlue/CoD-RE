# BO3 (T7) XPAK image extractor

A small, dependency-light reader/extractor for Black Ops 3 `.xpak` packages
(magic `KAPI`, version 10). It parses the container, resolves image assets by
their self-describing text index, decompresses the data blobs, and writes DDS.
Written to recover HD textures that are streamed from the on-disk `.xpak` rather
than held in game memory (so a memory-based exporter sees names but gets 0 bytes).

Offline and read-only on the game files. No game assets are included here — this
is the tool only.

## Files
- `xpak.py` — container parser (header, hash table, self-describing text index).
- `extract.py` — `decompress()` (block-group / `DecompressPackageObject` port) and
  a single-asset CLI.
- `lz4blk.py` — pure-Python LZ4 *block* decoder (for `flag 0x3` blocks; many
  textures are stored raw and need no decode).
- `dds.py` — minimal DX10 DDS (DXGI) writer.
- `extract_images.py` — map-agnostic batch CLI (all images, or `--prefix`).
- `verify.py` — optional: decode BC7 DDS to PNG thumbnails + mean colour
  (needs `Pillow` and `texture2ddecoder`).

## Usage
```sh
# list every image entry in a package
python extract_images.py path/to/map.xpak out_dir --list

# extract all images (or a subset) to DDS
python extract_images.py path/to/map.xpak out_dir
python extract_images.py path/to/map.xpak out_dir --prefix i_foo

# one asset by name
python extract.py path/to/map.xpak i_foo_c out_dir/i_foo_c.dds
```

## Format
See [`../../notes/t7_xpak_format.md`](../../notes/t7_xpak_format.md) for the
container + decompression layout.

## Credit / licence
Format reverse-engineered with reference to **Scobalula's Greyhound**
(`XPAKCache.cpp`, `DBGameFiles.h`). Greyhound's own source is **not** vendored
here — only our independent implementation and notes. Licensed GPL-3.0, matching
this repository.
