# Black Ops 4 (T8)

Reverse-engineering notes and offline tools for Black Ops 4 (T8 engine). We worked everything out offline, from your
own installed game. We did not run the game for any of it. No game assets are stored here. The scripts read your own
install's files. This repo has the format knowledge and the code, not the content.

## Start here

[`PORTING_METHOD.md`](PORTING_METHOD.md) is the full recipe for porting a BO4 map to Black Ops 3 (Mod Tools). We
worked it out on Blood of the Dead.

## What we have solved

- **CASC/TVFS reading.** A from-scratch reader for BO4's local CASC storage. It goes `.build.info`, then the build
  config, then the `.idx` bucket index, then the `data.NNN` archives. It decodes BLTE frames. Its TVFS `vfs-root`
  parser turns a path like `zone\zm_escape.ff` into the archive bytes. We checked it with an encoding-file md5 and
  with per-chunk byte comparisons.
- **Fastfile decompression.** How to turn an extracted `TAff0000` fastfile (version `0x27F`, BO4 retail) into its raw
  asset stream, offline, without the packed game module. It uses a generic reader (AES decrypt, then an Oodle block
  chain).
- **KAPI xpak decoding.** The BO4 `.xpak` (KAPI version `0xB`): header, 24-byte hash table, 0x80-aligned block
  groups, and the per-block codecs (raw, LZ4, Oodle Kraken). Oodle comes from the game's own DLL.
- **T8 clipMap layout.** The `clipMap_t` (asset 11) brush, plane and vertex layout, recovered by hand using BO3 as
  the template. It parses a decompressed zone into a brush and plane collision schema.
- **GfxWorld vertex format.** Split position and vertex-data buffers, one global u16 index buffer, per-surface ranges,
  and the 10:10:10 packed normal with half-float UV packing. We cross-checked it against the ripper-verified XModel
  mesh format.
- **XModel name hash.** FNV-1a-64 of the lower-cased name with `\` turned into `/`, masked to the low 60 bits. There
  is a reference implementation and test vectors.
- **Placement transforms.** Each static-model placement's origin, rotation and scale, solved from the collision
  static-model array (`invScaledAxis` to a world transform). A bounds check confirms a model name against the
  record's own AABB.

## What is not here

No game data of any kind: no fastfiles, xpaks, decompressed zones, placements, collision brushes, name dictionaries,
vertex or index buffers, images, models, sounds or navmeshes. No AES keys. No Oodle or other game binaries. No
copied third-party source. You point the tools at your own BO4 install.

## What is in the folders

- `port/`: the build-stage tools the method uses. Placement matching, entity list, spawns, textures, winding and
  z-fight fixes, collision budgeting and decimation, collmaps, the solid-but-invisible fill, lava and sea, zones and
  gameplay, and the import, map and build scripts.
- `notes/`: the format write-ups.
- `tools/`: offline, read-only Python and shell. The CASC reader and extractor and their test, the xpak reader, the
  clipMap and GfxWorld/placement extractors, the Havok tagfile and navmesh reader, the name-hash and dictionary
  builder, and the render-world emitter and validator.

## Worked example: get a map's zone out of BO4

The scripts in `port` read their folders from two environment variables (see `port\bo4cfg.py`), so nothing is edited by
hand: `BO4_WORK` is your work folder (default `C:\work`) and `BO3_TOOLS` is the BO3 Mod Tools folder (default is the
Steam path). The scripts in `tools` keep `PATH/TO/...` constants near the top. This example uses `zm_escape` and a BO4 install in `C:\Games\BO4`.

1. In `tools\casc_bo4.py` set `INSTALL` to `C:\Games\BO4`. In `tools\extract_zone.py` set `OUT` to an empty folder,
   say `C:\work\bo4_zone`.
2. Run the self-test once. It checks the reader against your install:

       python -I tools\test_casc.py

3. Pull the zone files out of CASC:

       python -I tools\extract_zone.py

   You get `zm_escape.ff`, the `.xpak` files and the others listed in the script's `TARGETS`, byte for byte.
4. Decompress the fastfile with ACTS (`tools\decomp_recipe.sh` has the exact commands):

       acts.exe fastfile -d C:\work\bo4_zone\zm_escape.ff -o C:\work\bo4_dec

   Do not pass `-r bo4`. That flag makes ACTS load a packed module that does not work offline. You get
   `zm_escape.ff.dec`, about 487 MB.
5. Read the collision brushes:

       python tools\clip_t8.py C:\work\bo4_dec\zm_escape.ff.dec C:\work\clip.json

If it fails:
- `test_casc.py` fails after a BO4 update: the reader needs a fix. The test says which of its five checks broke.
- The offsets in `clip_t8.py` are for one map. For another map you must find the inline ClipInfo block again; see
  `notes/t8_struct_refs.md`.
- ACTS aborts: make sure you left out `-r bo4`, and that the Oodle DLL is next to ACTS as `oo2core_8_win64.dll`.

Credits for the research and tools behind this are in [CREDITS.md](../../CREDITS.md).
