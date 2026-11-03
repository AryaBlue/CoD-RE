# Advanced Warfare (S1, PC x64) fastfile and asset layouts

<!-- toc -->
## Contents

- [1. Fastfile and stream](#1-fastfile-and-stream)
- [2. Which block data lands in](#2-which-block-data-lands-in)
- [3. XModel and XModelSurfs](#3-xmodel-and-xmodelsurfs)
- [4. XAnimParts](#4-xanimparts)
- [5. Sounds](#5-sounds)
- [6. Images and materials](#6-images-and-materials)
- [7. Name lookups and composite models](#7-name-lookups-and-composite-models)
- [8. Weapon definitions](#8-weapon-definitions)
  - [Anim arrays](#anim-arrays)
  - [Sounds](#sounds)
- [9. The convert job (Reforged)](#9-the-convert-job-reforged)
<!-- /toc -->

How E115's zone reader (`tools/zonedump/S1.cpp`) reads AW fastfiles without OAT. It only covers what the weapons track needs: xmodels,
xanims, sounds, and (in progress) materials and images. Our notes, in our own words; layouts were worked out from the
zone bytes, plus the 360 build's symbol map for the loader's block rules. No code or data was copied.

Marks: **[V]** read in the zone data or the 360 loader (address given), all static; **[I]** inferred, treat as a guess
until checked. The 360 build's `.map` and the `2-s1_mp` pdb are the game's own symbol files, read locally, not
included here.

## 1. Fastfile and stream

- [V] `S1ff0100` magic. A 0x38-byte file header, then LZ4 blocks `{u32 compressed, u32 decompressed <= 0x10000}`, each
  padded to 4. Other records sit between the blocks: a signature, and in big zones a stream table at file offset 0x34.
  The reader skips anything that doesn't parse as a block.
- [V] Decompressed stream: 0x40 bytes of XFile header (`u64 size, u64 externalSize, u64 blockSize[7]`), then the asset
  list. Script string count at 0x48. String pointers start at 0x70, 8 bytes each, and the strings follow in order.
- [V] Pointer fields, 8 bytes:
  - `ff ff ff ff ff fd fd fd` (follow): the data comes next in the stream, in field order, unaligned.
  - `fe ff ff ff ff fd fd fd` (insert): a slot allocated for later.
  - `{u32 offset + 1, f3 fd fd fd}` (back reference): data loaded earlier. The low nibble of the 0xf3 byte is the block,
    so every reference seen is block 3. The u32 is the offset inside that block [I: the nibble reading; the 360 packs
    `block << 28 | offset + 1` in 32 bits, DB_GetPackedOffsetStreamPos 0x82394470].

## 2. Which block data lands in

[V] 360 loader (`2-s1_mp.map` names; DB_PushStreamPos call sites with an immediate block):
- Every `Load_*Ptr` and `Load_MaterialHandle` pushes block 0 (temp). So an asset's top-level struct, loaded through its
  pointer, sits in temp memory, not block 3. Its sub-data goes to block 3 (`Load_Material`, `Load_GfxImage`,
  `Load_XModel`, `Load_XModelSurfs`, `Load_snd_alias_list_t`, `Load_LoadedSound` all push 3).
- `Load_GfxImagePixels` pushes 2 or 1: inline pixels aren't in block 3. `Load_XA2Sound` pushes 4.
- So a block 3 offset is the stream position less the temp headers (alias list 0x20, loaded sound 0x40, material
  0x1e0, image 0x60, xmodel 0x2a8, surfs 0x38, ...), less inline pixels, plus alignment padding. Measured between alias
  list anchors: each loaded sound costs 0x40 and each alias list 0x20, less 0 to 3 bytes of alignment [V].

A back reference to a shared *pointer* points at the earlier pointer slot, not the asset:
- xmodel material handles point at an earlier slot of the same array (`vm_ak12_base`: handle 1 = handle 0's material,
  4 to 9 = handle 3's) [I, consistent for every self-referencing xmodel found].
- A material's texture entry points at the image slot of an earlier material's texture table.

## 3. XModel and XModelSurfs

- [V] XModel header 0x2a8, then the name. `numBones` at 8, `numRootBones` at 9, `numMaterials` at 0xa. LOD info at 0x80,
  0x40 each: `{float dist, u16 numSurfs @4, u16 surfIndex @6, ptr @8}`.
- [V] After the name: bone names (u32 script strings), parents (u8, parent = index - value), quats (int16 x 4 / 32767,
  xyzw), trans (float3, the bone's local), part classification (u8), base matrices (32 bytes: quat xyzw, trans, weight),
  material handles (8 each), then inline materials.
- [V] XModelSurfs: 0x38 header (two follows, lod 0 surface count u16 at 16), the name, then 0x108-byte XSurfaces.
  Surface: flags 0, vertCount 2, triCount 4, rigid list count 6, blend counts u16[8] at 8.
  - Verts are 32 bytes: position, binormal sign, colour, half2 UV at 20, packed normal at 24, packed tangent at 28.
    Model-space bind pose.
  - Triangle indices at 0x18, 6 per triangle.
  - [V] 360 Load_XSurface loads the vertex union (0x10 there), then the index union (0x14): each is either allocated and
    loaded (`vc` verts, `tc * 3` indices) or a plain block offset (DB_ConvertOffsetToPointer). So a back-referenced
    buffer is an earlier surface's, loaded once by its first user; there is no "previous surface" rule.
  - [I] The reader places it structurally: every xmodelsurfs in the zone is indexed, and the target is the one earlier
    surface with the same count (and, for indices, all under this surface's vertex count) between the reference's own
    offset (block 3 never runs ahead of the stream) and here. Only a single fit is taken. The AK-12 still pairs surface
    1 with 0 and 7 with 6; VBR's and UTS-19's viewmodels now export.
  - Rigid lists at 0x48, 16 bytes each. Skinning at 0x60: a 32-byte record per vertex `{u16 bones[8], u16 weights[1..7] /
    65536 (w0 is the rest), u16 count}`.
  - A block at 0x90 isn't decoded; the reader skips it by finding the next surface's indices.
- [V] A model can share another's data whole. Header 0x38..0x60 (names, parents, quats, trans, part classes, base
  matrices) are then six back references, contiguous in block 3, and nothing is inline (bal27 `vm_bal27_base_black`).
  Its lod 0 pointer at 0x88 can be a back reference too: the whole XModelSurfs was loaded by an earlier model.
  - [I] The reader takes the one earlier model with the same bone counts and an inline skeleton (or several whose
    bytes are identical), and the one earlier XModelSurfs with this surface count between the reference and here.
  - [V] Handle back references then point at the source model's handle slots, 8-aligned after its base matrices
    (baseMat reference + 32 x bones, rounded up to 8). The refs land on slots exactly.
- [V] Anim translation = the bone's xmodel local + the anim value. Arms store zero locals, so theirs read as absolute.

- [I] A surface with the unread 0x90 (subdivision) block: the next surface starts where its triangles index all its own
  vertices and where, walked from there, the one after does too. A lone check took `npc_ameli_base`'s surface 5 two bytes
  early; the chained one lands it and the asaw world model converts. The block's own layout (a 0x40 header with the cache
  size at 0x20, then levels of counts and pointers) is not decoded.
- [I] Inferred, not data: `vm_asm1_base_loot` ships in no zone. The view job builds it from `npc_asm1_base_loot`'s parts
  as their `vm_` ones, in its order, and the convert log says so. This matches arx160, lsat, hbra3 and kf5 exactly;
  sn6's view adds a charging handle, so it is not a rule.

## 4. XAnimParts

- [V] 0xd8 header: counts at 8 (data byte/short/int, frames), flags 0x10, bone counts [12] at 0x11 (no quat, half,
  full, half const, full const, small trans, trans, trans const, no trans, all), notify count 0x1d, random data
  byte/short/int counts at 0x20/0x24/0x28, index count 0x2c, framerate 0x30, frequency 0x34.
- [V] After the name: bone names, notifies `{u32 name, f32 normalised time}`, then the data byte, data short, data int,
  random data short and random data byte streams.
- [V] Frame indices: u8 in data byte under 256 frames. At 256+ frames they are u16 in data short, except for tracks
  with 64+ keys: those have a lookup table of `((keys - 1) >> 8) + 2` shorts in data short, and the indices are in
  the u16 index array (count 0x2c, pointer 0x70), loaded after random data byte. Each trans part's key count sits in
  data short just ahead of its own frames. The streams add up exactly (lsat `vm_lsat_reload_empty`, 260 frames).
- [V] Notetracks are bare alias names; the engine plays them as `sndnt#<alias>`.
- [I] Delta part (pointer at 0x80): a 0x18-byte `{trans, quat2, quat}` header loaded after the notifies, before data
  byte. The Exo Zombies printer anims have it with all three null, and their streams then add up exactly. Non-null delta
  data isn't read yet (the reader stops with an error).

## 5. Sounds

- [V] Alias list `{name, aliases, 0, u64 count}` + name + count x 0xf0 aliases: name 0, subtitle 8, secondary 0x10,
  chain 0x18, sound file 0x20, squelch 0x28. Their followed data comes after the array in field order.
  [I] volume min/max 0x3c/0x40, pitch 0x48/0x4c, distance 0x50/0x54.
- [V] Sound file 0x30 `{u8 type, u8 exists, 6 zero, ptr @8}`. Loaded sound 0x40 `{name ptr, u16 localised, u16 pak,
  u64 offset, u64 length, ptr, u32 rate, u32 length, u32, u8 channels, u8 bits, u16 align, u32 format (1 pcm),
  u32 length}`, its name, then `length` zero bytes. The PCM sits at `{offset, length}` in `soundfile<pak>.pak`.
- [V] Sound file back references are placed exactly. 360 Load_snd_alias_t loads the sound file or converts an offset
  to a pointer (a direct pointer, not an alias). An anchor is an alias list whose first alias names it by back
  reference: that gives its name's exact block 3 offset. From there block 3 runs, list after list:
  - the list name (if inline; a later list's name can be a back reference), then the alias array 4-aligned;
  - each alias's followed strings, then the 4-aligned 0x30 sound file, then the loaded sound's name and its in-zone data
    (the data counts in block 3 on pc, unlike the 360's block 4). The 0x40 list and loaded sound headers don't count.
  - the list header is `{name, aliases, context list, u8 count, u8 context count}`; contexts (2 bytes each, 2-aligned)
    follow the aliases' data.
  Every anchor passed agrees with the walk, and the target lands exactly on a sound file (arx160, hbra3 fire sounds).
- Older fallback: a loaded sound by reference is taken only when a neighbouring record is referenced too,
  with the same stream gap less its 0x40 header (wpn_ak12_plr: pyatek shot_01..03). Otherwise the alias stays
  unresolved. Type 1 sounds whose name is itself a reference (claymore_armed) aren't read yet.

## 6. Images and materials

- [V] GfxImage 0x60 header, then the name. First 0x10 zero, DXGI format at 0x10. Streams[4] at 0x38 `{u16 w, u16 h, u32 packed}`, where
  the low 26 bits are the cumulative size and the top 6 the mip count.
- [V] The stream table at file offset 0x34 has 24-byte entries `{u16, u16 pak, u32, u64 offset, u64 end}` into
  `imagefile<pak>.pak`. Each entry is `{u32 total, u32 0, u32 flags}`, then LZ4 blocks. Streamed images take groups of
  4 entries from index 3, in stream order; stream j is entry 4g + 3 + j. Checked against every size.
- [V] Material: 0x1e0 header, then the name. Texture table entries are 16 bytes `{u32 sampler hash, char first, char
  last, u8 sampler state, u8 semantic (2 colour, 5 normal, 8 specular, 16 occlusion), ptr}`.
- [V] Weapon zones (`mp_vm_<gun>_tr`) hold only `,m/mtl_*` placeholders. The real materials are in common_mp under the
  same name.
- [V] Sampler hashes are R_HashString of the sampler name (`x = x * 33 ^ (c | 0x20)`, 360 0x82b40518), so a table's
  colour/normal/specular slots can be named without guessing.
- [I] A texture entry's back reference is not turned into a stream position (the block 3 accounting through pixel spans
  isn't modelled). It points at an earlier table's image slot, so it is resolved by the material's own name less its
  folder (`m/mtl_x` -> `mtl_x`): an earlier material of that name with a followed slot of the same sampler hash and
  semantic, taken only when there is exactly one. A miss leaves the slot untextured. On the AK-12 every gun slot
  resolves; the exo arm sleeves and gloves don't yet.
- [V] Gun materials carry `specularMap` "<x>_spc-rgb & <x>_cos-l" (BC3: rgb specular colour, alpha gloss) and
  `normalMap` "<x>_nml" (BC5 snorm, read as unorm after shifting the endpoints). Reforged draws them with t6's
  specular maths and a plain `2x - 1` normal decode (spec model "s1") [I: the lobe is t6's, not AW's own].
- [V] Top-level materials are placed in block 3 exactly, which textures the arm sleeves and exo gloves:
  - Material header 0x1e0 (block 0): name 0, counts at 0xe4 (textures, constants, state bits), techset 0xf0,
    table 0xf8, constants 0x100, state bits 0x108, constant buffer defs 0x1c8 (count u32 at 0x1d0).
  - Stream after the name: the table (16 x count), each followed image (0x68 bytes then its name), constants (0x20 each),
    state bits (0x28 each), buffer defs (0x80 each) and their data: pointers at 0x30/0x38 with byte sizes at 8/0xc,
    0x50/0x58 with u16 counts at 0x18/0x1c. Material ends land exactly on the next header (480 of 518 in a 12 MB window;
    the rest are other assets).
  - Block 3: the name, the 4-aligned table, image names, 16-aligned constants, 8-aligned state bits and defs, 16-aligned
    buffer data, 2-aligned offset arrays. Headers (material and image) don't count. Alignment is absolute, so each start
    mod 16 gives its own layout.
  - A run of back-to-back materials is known up to one offset. The zone's texture back references vote (same sampler
    hash), and the winner is kept only when every reference into the run's range lands on a followed slot (any sampler:
    an image can be shared). Runs must keep stream order and never gain on the stream. The big runs explain every
    reference that falls in them.
  - The sleeve `ms/mtl_mp_view_top_08a` lands on `ms/mtl_mp_view_top_08d` (spec, `mp_view_top_08a_occ-l`,
    `mp_view_top_08d_col`) and `ms/mtl_mp_view_top_03b` (normal); `m/mtl_mp_gloves_12a_exo` gets `mp_gloves_12_exo_col`.

- [V] The fastfile's stream table is a u32 count at 0x18, then 24-byte entries from 0x1c, then 16 bytes, then the
  `S1ffs100` signature. (Reading from 0x34 dropped entry 0.) Streamed images take groups of 4 entries in load order from
  entry 0; the scan skips forward to the next group whose sizes match exactly. All 4110 groups of `mp_zombie_lab` place,
  and the weapon zones gain textures they were missing before.
- [I] A handle that back references another model's handle slot resolves through that model's own anchored array: the
  earlier model (stream at or after the reference) whose own back references pin its array over the slot. The printer
  shell's interior and glass slots land on the printer's array exactly.

## 7. Name lookups and composite models

- [V] `find()` matches an asset name at its header's name position. A `,name` placeholder's tail can match too
  (`,m/mtl_ak12_base` holds `m/mtl_ak12_base`), so a hit right after a `,` is rejected.
- [V] Map zones (`mp_zombie_*`): headers of script-visible assets (models, anims) don't carry their name inline. The
  name field is a back reference to the asset's string in the zone's net const string lists (`ncs_mdl_level`,
  `ncs_anm_level`, ...). Each list is a 0x20 header `{name, u32 type, u32 count @0x10, list}` (block 0); its name, the
  8-aligned pointer array and the strings are block 3. Lists back to back form a run known up to one offset; the
  zone's back references pin it (most votes, and every reference into the run lands on a name, slot or string: 5 runs
  in `mp_zombie_lab`, none missing). An asset is then the one header whose name field references its string.
- [V] The Exo Zombies 3D printer: `dlc_weapon_mystery_box_01` (7 bones, the moving parts: print head, glass,
  monitor) on top of `dlc_weapon_mystery_box_01_static` (the shell, inline-named, placed by the map's
  `prefabs/zombies/magic_box_start.map`). Anims `dlc_weapon_mystery_box_01_{open,close,idle_open,malfunction}`
  read exactly. Their textures are streamed images the reader doesn't place yet.
- [I] Composite xmodels (a viewmodel built from parts): the part count byte sits at 0x202 or 0x203 depending on the
  model. The reader takes whichever one gives a count under 32 whose array slots all follow. Not pinned to a field.

## 8. Weapon definitions

- [V] PC WeaponDef in patch_common_mp: a 0xde8 header, then the name (`iw5_*_mp`). Display name and alt strings
  follow, then the followed sub-data in loader order. Loot variants and records failing the enum checks below are
  skipped.
- [V] Fields (PC header offsets), checked against known AK-12 / Bal-27 / ASM1 numbers:

  | field | offset | | field | offset |
  |---|---|---|---|---|
  | weapType (< 6) | 0x52c | | damage | 0x648 |
  | weapClass (< 21) | 0x530 | | melee damage | 0x650 |
  | penetrateType | 0x534 | | adsZoomFov | 0x8d0 |
  | inventoryType | 0x540 | | minDamage | 0xc84 |
  | fireType (< 7) | 0x544 | | maxRange / minRange | 0xc90 / 0xc94 |
  | startAmmo | 0x61c | | maxAmmo | 0x630 |
  | clipSize | 0x638 | | | |

  State timers are int milliseconds: fire 0x668, melee 0x684, reload 0x68c, reloadEmpty 0x694, drop 0x6c4, raise
  0x6c8, firstRaise 0x6dc, sprintIn 0x6ec, sprintOut 0x6f4. weapons.json stores them in seconds.
- [V] Enum names (type, class, fire type, inventory, penetration) come from the 2-s1_mp pdb.
- [V] adsIn 0x988, adsInFromSprint 0x98c, adsOut 0x990 (int ms): 250/350/250 on rifles, 200/300/200 on SMGs,
  350/450/400 on snipers. moveSpeedScale isn't read (the candidates were ambiguous); the engine takes 1.
- [I] worldModel: header 0x3d0 follows on every gun read. Its array loads like gunXModel's (2 slots, then a 0x2a8
  placeholder header and `,name`); the reader takes the first such after gunXModel's. 30 of 31 guns give their
  `npc_*` model; iw5_pbw_mp gives a reticle model, so pbw's def read is suspect overall. World models live in
  `mp_wm_<gun>_tr.ff`, composites like the viewmodels.
- [V] gunXModel: after the name strings, an array of 2 model pointers; the first placeholder name sits at
  name end + 16 + 0x2a9 (a 0x2a8 placeholder header, then `,`).

### Anim arrays

- [V] The 360 Load_WeaponDef loads three XAnimParts arrays of 0xb4 (180) slots: right hand (header 0x60), left hand
  (0x68) and szXAnims (0x80). Each array is followed by its placeholders: a 0xd8 header (follow at 0, the rest zero)
  then `,name`.
- [I] szXAnims is the array whose data is followed by AnimOverride entries (0x20 each `{u32 != 0, u32 0, ptr, ptr}`, two
  in a row needed) when the header slot at 0x88 follows, otherwise the last array. Akimbo guns (LSAT among them) have
  the r/l arrays first, which is why the first array isn't taken blindly.
- [I] Slot names: the 2-s1_mp pdb's weapAnimFiles enum has 175 names; the PC arrays have 180 entries. Three extra
  names sit at 35, somewhere in 54..63 and somewhere in 91..127. They were placed by lining up 19 guns' clip names
  (`*_reload`, `*_sprint_in`, ...) against the enum. Slots used: idle 1, fire 3, lastShot 5, rechamber 6, melee 9,
  reload 24, reloadEmpty 25, raise 36, firstRaise 37, drop 39, quickRaise 43, quickDrop 44, sprintIn 49, sprintLoop
  52, sprintOut 53, adsFire 64, adsUp 128, adsDown 129. Raw slot -> clip pairs go to weapons.json `animSlots` as well.
- A gun whose szXAnims slots are all back references (pbw, gm6, mors, a few more) gets no anims: nothing is guessed.
- [V] Some named clips are in no zone: vm_arx160_fire, vm_bal27_pullout/putaway/sprint_loop, vm_sn6_pullout/putaway and
  vm_knife_melee_slice are absent from every mp_vm_* (with the `_2` variants), knife and mp_zombie* zone, common_mp,
  patch_common_mp and common_zombie_mp (`--has`). Those slots keep the engine's fallbacks.

### Sounds

- [V] A sound field is a `{ptr, name}` lookup: a follow puts the name inline; in block 3 each lookup costs 8 + the
  name + 1, rounded up to 8. The lookups load back to back in field order.
- [V] The enum of sound fields differs by build (default_mp 119 entries, 2-s1_mp 175), so offsets were read from the
  data: PC 0x180 is fireSound (npc), 0x188 fireSoundPlayer (plr). Sound fields lie in 0x130..0x360.
- [V] SoundOverride entries (header 0x90) are 0x18 each `{u8, u8, u16, u32 0, ptr, ptr}`; their followed lookups come
  before the header's.
- [I] Followed header fields: skip the override lookups (counted from the entries), then the k-th followed header slot
  is the k-th lookup of the next run.
- [I] Back-referenced fields: refs from the header region and the override entries only. For every run of lookups seen
  so far, the bases putting at least 3 refs on its lookup starts. This def's own runs go first and must hit an entry
  ref; then greedily one base per run and one run per ref. A run with two equal free bases is ambiguous and gives
  nothing. A run's base must also lie between the bases of the placed runs before and after it (block 3 only grows).
- Result: the AK-12 reads wpn_ak12_npc / wpn_ak12_plr; most guns resolve as matching npc/plr pairs. Misses stay empty.

## 9. The convert job (Reforged)

- s1 is a content-source game like t4/t5/t6, with no maps of its own; its guns join the zombies weapon pack pool
  (`--zm-pack s1`, settings zm.weaponPack "s1").
- Game content plan: `--s1 patch_common_mp.ff --weapons weapons/weapons.json`, then per gun with a viewmodel, anims
  and an `mp_vm_<gun>_tr.ff` zone: the viewmodel with default mp arms at tag_weapon and its clips to
  `weapons/<def>.glb`, and its fire sounds plus the clips' notetrack sounds to `weapons/<def>/sounds/`. Per-gun jobs are
  optional: a gun that fails is left out.
- The world model goes to `weapons/<def>/script_models/<model>.glb` (wall buys and drops find it there), from
  `mp_wm_<gun>_tr.ff` with `--xanim -` (no clips).
- The Exo Zombies printer is a box look (data/boxes.json `s1`): `--s1 mp_zombie_lab.ff --xanim <open,close,idle_open,
  malfunction> dlc_weapon_mystery_box_01,dlc_weapon_mystery_box_01_static` to `_models/dlc_weapon_mystery_box_01.glb`.
  lidOpen/lidClose are its open/close clips; rise and teddy keep the map's own (where aw puts the printed gun isn't
  read yet, so no tag is bound).
- MP: aw has no class tables, so its list is the converted guns (pistols secondary, the rest primary [I]); a class
  pick of an aw gun loads it like any cross-game class gun.
