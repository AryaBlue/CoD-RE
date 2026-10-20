# oatfork — optimized OpenAssetTools fork (Linker / Unlinker)

Our performance fork of OpenAssetTools, plus a T6 world dumper, on top of the
waw2bo2 B2W OAT checkout. GPL-3.0, like OpenAssetTools itself. Source only — no
built binaries go in this repo.

`BASE_COMMIT` is the baseline the changes sit on: the `reference/b2w` OAT tree
(Ticass/B2W `70bc049`, see `../../converter/b2w-patch/BASE_COMMIT`) with the
working-tree patches installed 2026-10-19. `changes.patch` is our diff against it.

## What's in `changes.patch`

Speed (outputs proven equivalent by unlink + diff, not by bytes — fork `.ff`
output is nondeterministic run to run):

- **Parallel XModel JSON parse** — `LoaderXModel` loads model JSON across threads
  (templates + generated `build/src` copies for IW3/IW4/IW5/T5/T6).
- **Parallel XChunk deflate** — `XChunkProcessorDeflate` / `OutputProcessorXChunks`
  compress zone chunks in parallel.
- **Unlinker `--model-format NONE`** — skip model export when only non-model
  assets are wanted (`UnlinkerArgs`).

Dumper:

- **T6 GfxWorld / ClipMap `.bin` dumper** (`WorldConverterDumperT6`, new files
  under `new/`, wired through `ObjWriterT6` / `ObjWriting.h` / `ZoneCreator` /
  `AssetCreatorCollection`). Emits `maps/mp/<map>.d3dbsp.{gfx,clip}.bin` for the
  BO2 MP → Zombies port path.

## Apply

    git -C <oatfork-checkout> checkout 14c04d0 && git -C <oatfork-checkout> apply changes.patch
    # then copy new/ over the checkout and rebuild

Snapshot as of 2026-10-20. Later OAT world-dumper work (T6 layer data) is not
included here yet.
