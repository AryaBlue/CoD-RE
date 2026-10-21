# BO3 (T7) zone / fastfile tools

Offline, read-only decoders for Black Ops III PC fastfiles and the assets they carry inline.
They read your own BO3 install's files; no game assets are stored in this repo. GPL-3.0.

Format is documented in [`../../notes/t7_fastfile_format.md`](../../notes/t7_fastfile_format.md).

## Tools

- **`bo3_ff_dec.py`** — decompress a BO3 fastfile (version `0x251`) to its raw zone stream.
  ```
  python bo3_ff_dec.py core_frontend.ff core_frontend.zone
  ```
- **`bo3_zone_images.py`** — extract the `GfxImage`s a zone carries inline (resident UI art) to
  PNG + `index.json`. Needs Pillow. Third arg is a name-filter regex (default: all).
  ```
  python bo3_zone_images.py core_frontend.zone out "^uie_"
  ```
- **`scan_ttf.py`** — locate (and optionally export) TTF/OTF font tables embedded in a zone.
  ```
  python scan_ttf.py core_ui.zone            # list offsets
  ```

## Notes

- BO3 PC core/frontend fastfiles are zlib-compressed and **not** AES-encrypted, so no key is needed.
- `bo3_zone_images.py` decodes the top mip of BC1/3/5/7 and RGBA8/BGRA8 images; other DXGI formats
  are listed as `unsupported_format` in `index.json` rather than decoded.
