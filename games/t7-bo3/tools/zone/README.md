# BO3 (T7) zone and fastfile tools

Offline, read-only tools for Black Ops III PC fastfiles and the assets they carry inline. They read your own install.
No game assets are stored in this repo. GPL-3.0.

The format is written up in [`../../notes/t7_fastfile_format.md`](../../notes/fastfile_format.md).
BO3 PC core and frontend fastfiles are zlib-compressed and not AES-encrypted, so you need no key.

## Tools

### `bo3_ff_dec.py`: fastfile to raw zone

Decompresses a BO3 fastfile (version `0x251`).

    python bo3_ff_dec.py "C:\Games\BO3\zone\core_frontend.ff" core_frontend.zone

You get `core_frontend.zone`, the raw zone stream.

### `bo3_zone_images.py`: inline images to PNG

Extracts the `GfxImage`s a zone carries inline (the always-loaded UI art) to PNG, and writes `index.json`. It needs
Pillow. The third argument is a name filter (a regex). The default is all images.

    python bo3_zone_images.py core_frontend.zone out "^uie_"

You get PNG files in `out\` and `out\index.json`. The script decodes the top mip of BC1, BC3, BC5, BC7, RGBA8 and
BGRA8. Other formats are listed in `index.json` as `unsupported_format` and not written.

### `scan_ttf.py`: find embedded fonts

Finds TTF and OTF tables inside a zone, and can export them.

    python scan_ttf.py core_ui.zone

This prints the offsets of every font it finds.

## If it fails

- `bo3_ff_dec.py` refuses the file: it only reads version `0x251`. Make sure the file is a BO3 `.ff`.
- `bo3_zone_images.py` writes nothing: your filter matched no names. Run it without the third argument first and look
  at `index.json`.
- Missing `PIL`: run `pip install pillow`.
