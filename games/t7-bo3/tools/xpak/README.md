# BO3 (T7) XPAK image extractor

This reads Black Ops 3 `.xpak` packages (magic `KAPI`, version 10) and writes the images in them as DDS. It needs only
Python 3. It never writes to your game folder and no game assets are in this repo.

We wrote it for HD textures that stream from the `.xpak` on disk. A memory-based exporter sees their names but gets 0
bytes, because the pixels are not in memory.

## Files

- `xpak.py`: the container parser (header, hash table, the text index that describes each entry).
- `extract.py`: `decompress()` and a one-asset command line.
- `lz4blk.py`: a pure-Python LZ4 block decoder. Needed for `flag 0x3` blocks. Many textures are stored raw and
  never touch it.
- `dds.py`: writes a DX10 DDS.
- `extract_images.py`: the batch command line. Lists or extracts every image, or the ones with a given prefix.
- `verify.py`: optional. Decodes BC7 DDS files to PNG thumbnails and prints a mean colour. Needs `Pillow` and
  `texture2ddecoder`.

## Worked example

Say the game is in `C:\Games\BO3` and the map is `zm_example`.

List every image in a package:

    python extract_images.py "C:\Games\BO3\zone\zm_example.xpak" out --list

Extract them all, or only the names that start with a prefix:

    python extract_images.py "C:\Games\BO3\zone\zm_example.xpak" out
    python extract_images.py "C:\Games\BO3\zone\zm_example.xpak" out --prefix i_foo

Extract one image by name:

    python extract.py "C:\Games\BO3\zone\zm_example.xpak" i_foo_c out\i_foo_c.dds

You get one `.dds` per image in `out\`. Open them in any DDS viewer that handles DX10 headers (for example Paint.NET
with the DDS plugin, or `texconv` to convert).

If it fails:
- An asset name is not found: run the `--list` form and copy the name exactly.
- Output looks flat or wrong: the image may use a block format the viewer cannot read. Convert with `texconv`.
- The package is not `KAPI` v10: BO4 packages are a different version. See `games/t8-bo4`.

## Format

[`../../notes/t7_xpak_format.md`](../../notes/t7_xpak_format.md) describes the container and the decompression.

## Credit and licence

We worked the format out with reference to Scobalula's Greyhound (`XPAKCache.cpp`, `DBGameFiles.h`). Greyhound's source
is not copied here. This is our own implementation and notes, GPL-3.0 like the rest of this repo.
