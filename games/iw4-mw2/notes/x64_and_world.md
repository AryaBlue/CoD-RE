# IW4 (MW2): the 2026 64-bit Steam update, loading zones, clipmap brushes

From a recon of a Steam MW2 (2009, IW4) install on 2026-11-01. Nothing was written to the install. Tags: **[V]** read
or run, **[I]** inferred, **[U]** unknown.

## The 64-bit "IW4MS" update [V]

- In 2026 the Steam build gained 64-bit executables (`iw4mp` and `iw4sp`, x64). The community calls the new zone
  flavour **IW4MS**.
- The zone files keep the header magic `IWff0100` and version 276. But pointers inside the zone stream are serialised
  as 8 bytes instead of 4, so a 32-bit loader reads them wrongly.
- The base game is now fully installed (about 12 GB): roughly 100 English zones (4.5 GB), 16 multiplayer maps, about
  17 campaign zones and about 28 Spec Ops zones. A previous recon of an IW4x-only install is out of date.
- Images and loaded sounds are in the `.iwd` archives, not the zones (see [iw4_iwi_v8.md](iwi_v8.md)).

## How we load it [V]

- Our OpenAssetTools build gets x64 IW4MS zone loading by porting it from the `iw4x-x64/oat` fork (William Roy,
  GPL-3.0). Upstream: https://github.com/iw4x-x64/oat . Their asset definitions for the x64 layout:
  https://github.com/iw4x-x64/assets .
- In the game's zone-code commands file the word size is 64 (`wordsize 64`) and the allocation alignment word size
  is 32 (`allocalignwordsize 32`). Our reading **[I]**: allocation alignment keeps the 32-bit rules even though pointers are 8 bytes.
- Our fork is that port rebased onto our own OAT tree, plus a few converters to the common asset structs and null
  placeholders for object/zone-writing entries that were not ported. We did not publish it as a patch: it is mostly the
  upstream fork's own code, so use upstream.
- An old 32-bit Unlinker parses the small `*_load` zones but crashes on a full map zone from this install. The x64 path
  is what works.

## What we expect to reuse from the T4 path [I]

- `GfxWorld` and `clipMap_t` are the T4 lineage (vertex layout, primary/secondary lightmaps).
- MW2 has no sun light or probe set like T6.
- Materials use separate techset/shader assets with their own state bits. For our own shading a flat colour/normal/
  spec mapping is enough.
- Gameplay scripts are text rawfiles, not T6 bytecode, with different built-ins. The T4-T6 script VM does not run them.

## Clipmap brushes have no stored corners [V]

An IW4 brush stores planes and sides, not the corner vertices that T4, T5 and T6 keep. A converter that makes mesh
faces from corners has to solve them: take each set of three planes, intersect them, and keep the points that lie
inside all the other planes. Each face of the brush is then the corners that sit on one plane. E115's collision
exporter (`Collision.cpp`) does this for IW4 brushes.

## Sound [I]

The OAT IW4 dumper only handles PCM. Loaded sounds live in the `.iwd` archives.
