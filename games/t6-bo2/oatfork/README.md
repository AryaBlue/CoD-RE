# oatfork: our faster OpenAssetTools fork

This is our OpenAssetTools (OAT) fork with a faster Linker and Unlinker, plus a T6 world dumper. It sits on top of
the waw2bo2 B2W OAT checkout. It is GPL-3.0, like OAT. The repo holds source only. There are no built binaries.

`BASE_COMMIT` is the commit the changes sit on: the `reference/b2w` OAT tree (Ticass/B2W `70bc049`, see
`../../converter/b2w-patch/BASE_COMMIT`) with our working-tree patches from 2026-10-19. `changes.patch` is our diff
against it. It is a snapshot from 2026-10-20. Later OAT world-dumper work (T6 layer data) is not in it yet.

## What the patch changes

Speed. We checked that outputs are equivalent by unlinking and diffing. They are not byte-identical, because
`.ff` output from the fork differs from run to run.

- XModel JSON parses in parallel (`LoaderXModel`).
- Zone chunks deflate in parallel (`XChunkProcessorDeflate`, `OutputProcessorXChunks`).
- The Unlinker has `--model-format NONE`, which skips model export when you only want other assets.

Dumper. `WorldConverterDumperT6` writes the T6 GfxWorld and ClipMap as `.bin` files:
`maps/mp/<map>.d3dbsp.gfx.bin` and `maps/mp/<map>.d3dbsp.clip.bin`. We use them to port BO2 multiplayer maps to Zombies.

## Worked example

Say your OAT checkout is `C:\src\oat` and this repo is `C:\src\CoD-RE`.

    git -C C:\src\oat checkout 14c04d0
    git -C C:\src\oat apply C:\src\CoD-RE\games\t6-bo2\oatfork\changes.patch
    xcopy /E /Y C:\src\CoD-RE\games\t6-bo2\oatfork\new\* C:\src\oat\

Rebuild OAT. Then dump a map from your BO2 install without exporting models (the map name here is only an example):

    Unlinker.exe --model-format NONE --output-folder C:\work\dump C:\Games\BO2\zone\all\mp_nuketown_2020.ff

You should get the `.gfx.bin` and `.clip.bin` files under `C:\work\dump\maps\mp\`.

If it fails:
- `git apply` errors mean you are not on `14c04d0`. Check it out again and retry.
- The Unlinker complains about missing assets: the map needs its common zones loaded too. Run `Unlinker.exe --help`
  to see how your build takes extra zones.
