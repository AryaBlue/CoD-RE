# BO2 Xbox 360 symbol builds: getting them readable

How we turned the BO2 Xbox 360 builds (`CoDMP.exe`, `CoDSP.exe` and their `.map` files, from the user's own copy) into
something we could read: a flat decrypted image for scripted table dumps, and a Ghidra project with the `.map` names.
Marks are explained in the [notes index](../../../../NOTES.md).

## What the files are

- [V] `CoDMP.exe` / `CoDSP.exe` and the `_fast`, `_rd`, `_PixProfile` variants are XEX2 files (magic `XEX2`), not PE.
  Each comes with an MSVC linker `.map` holding every public symbol (mangled names, section:offset and the full
  address, with `f` marking functions). Preferred load address `0x82000000`.
- [V] Zombies runs in the MP binary on BO2: `CoDMP` holds the zombies code paths (session-mode checks, `_zm` script
  paths), so it is the reference for zombies. `CoDSP` is the campaign.
- [V] Optional header `0x3FF` (file format info) gives encryption type 1 (normal) and compression type 1 (basic) for
  `CoDMP.exe`, `CoDMP_rd.exe` and `CoDSP.exe`.

## Decrypting without Ghidra

- [V] The image key sits at offset `0x150` of the security info block. It decrypts with the devkit key (all zeros), not
  the retail key: these are devkit builds.
- [V] The payload from the PE data offset to the end is AES-128-CBC with that image key and a zero IV.
- [V] Basic compression is a list of (data size, zero size) pairs after the file-format header: copy that many bytes,
  then append that many zeros. The result starts with `MZ` and is the PE image as mapped, so image offset = address -
  `0x82000000`.
- [M] `CoDMP` gives a 0x34a8000-byte image; `CoDSP` 0x3228000.
- [V] Data is big-endian PowerPC. Tables of pointers can then be read straight from the image and named from the `.map`.

## Ghidra

- [M] Ghidra 12.1.3 with zeroKilo's XEXLoaderWV 12.1.3 extension imports `CoDMP.exe` directly (it handles the
  decryption itself) and auto-analyses it headless.
- [M] We applied the `.map` names with a small pre-analysis script (each row becomes a label; `f` rows also get a
  function). That gave 95,584 labels. After analysis most functions still carried default names, so a second pass
  renamed every function to the `.map` label at its entry, de-mangled to `Class::Name` (22,098 renamed), and a third
  made functions at the 4,488 code labels that had none.
- [M] PowerPC register save/restore helpers (`__savegprlr_*`, `__restgprlr_*` and friends) are taken as no-return by the
  analyser, so most callers decompile to a single call. Clearing no-return on the 82 helpers, marking them inline and
  re-disassembling after each call fixed about 13,000 function bodies.
- [M] A few decompiles still stop with "bad instruction" (e.g. `PM_GroundTrace`). For those we read the same function in
  the PC dedicated server (`CoDMPServer_PC.exe`, x86 with its `.map`/`.pdb`), which is the same 2013 codebase. Every
  spot check so far matched the console code (setanimstate, setteam, setzbarrierpiecestate).

## Credits

- XEXLoaderWV by zeroKilo (Warranty Voider), Ghidra by the NSA, capstone for the x86 spot reads.
- The symbol builds and the PC server pdb are the user's own files; nothing from them is published here.
