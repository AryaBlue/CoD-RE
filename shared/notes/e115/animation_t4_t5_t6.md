# T4 / T5 / T6 skeletal animation: XModel skeletons and XAnimParts

How WaW (T4), BO1 (T5) and BO2 (T6) store skeletons and animations, and how `e115_zonedump` turns them into standard
glTF skins and animations. Researched 2026-10-26.

## Conventions

- **Path prefixes.** `OAT/` is `<OAT checkout>/src/` (our vendored OpenAssetTools fork).
  - Headers: `T4H` = `OAT/Common/Game/T4/T4_Assets.h`, `T5H` = `.../T5/T5_Assets.h`, `T6H` = `.../T6/T6_Assets.h`.
  - Code:
    - `FXR` = `OAT/ObjWriting/XAnim/FlatXAnimReader.cpp`
    - `XAD` = `OAT/ObjWriting/XAnim/XAnimDumper.cpp.template`
    - `ANIM` = E115 `tools/zonedump/Anim.cpp` (not published)
    - `ZD` = E115 `tools/zonedump/main.cpp` (not published)
- **Status tags.**
  - **[V]** verified in the source at `file:line`.
  - **[V-data]** verified by decoding real zone data. The anim, model and zone are named.
  - **[I]** inferred. It fits the data, but nobody has checked it in the game.
  - **[!]** a trap.
- **Units.** Cod units are inches, z-up. The glb keeps cod units under the `cod_to_engine` root node.
- **Test set.** Exports are in `<export root>/anim/{t4,t5,t6}`.

| game | anims | model |
|---|---|---|
| T4 | ai_zombie_walk_v1, ai_zombie_walk_fast_v1, ai_zombie_idle_v1, ai_zombie_attack_v1 | char_ger_honorgd_body1_1 |
| T4 | viewmodel_zombie_idle, viewmodel_zombie_fire | viewmodel_usa_marine_arms |
| T5 | ai_zombie_walk_v1, ai_zombie_idle_v1 | c_ger_honorguard_body1 |
| T5 | ai_zombie_quad_idle | c_zom_quad_body |
| T5 | viewmodel_thundergun_idle | t5_weapon_thundergun_viewmodel |
| T6 | ai_zombie_walk_v1 (zm_nuked) | c_zom_dlc0_zom_sol_body1 |

---

## 1. Skeleton (XModel)

- **Bone order: parents first.** OAT's `XModelCommon::m_bones` gives each bone a name, an optional `parentIndex`, a
  global bind (`globalOffset`/`globalRotation`, from baseMat) and a local TRS (`localOffset`/`localRotation`, from the
  model's trans/quats).
  - Every model exported so far has parents before children, so a single pass builds the hierarchy **[V-data]**.
  - Root bones (no parent) have identity locals in OAT, so their global bind is their local **[V-data]**.
- **[!] The model's own local translations are not always the rest pose.**
  - `viewmodel_usa_marine_arms` (T4) stores zero local translation on 66 of its 70 bones. Chaining those locals misses
    baseMat by up to 25 units, but the rotations are exact **[V-data]**.
  - Characters agree with baseMat on every bone: char_ger_honorgd_*, c_ger_zombie_head4,
    c_zom_dlc0_zom_sol_body1 (73 bones) and t5_weapon_thundergun_viewmodel (49) **[V-data]**.
  - So zonedump derives every rest local from baseMat (`inverse(parentBind) * bind`, `ZD:484`). That makes the rest
    pose match the inverse bind matrices by construction. The model's own locals are only compared, in the
    "model locals disagree" warning.
- **Weights.** OAT gives each vertex an (offset, count) into a weight list; weight 0 is `1 - sum(others)`.
  - zonedump keeps the strongest 4 and renormalises them.
  - Unweighted vertices ride bone 0 with weight 1.
  - Every vertex's weights sum to 1 within 1.2e-7 on all six models above **[V-data]**.
- **glTF layout.**
  - Node 0 is `cod_to_engine`; node 1 is the mesh, with `skin: 0`; bone *i* is node 2+*i*.
  - Root bones are parented to node 0.
  - IBM = `inverse(translate(globalOffset) * rotate(globalRotation))`.

## 2. XAnimParts layout

The fields are the same in all three games, apart from a few flags **[V]** (`T4H:315`, `T5H:409`, `T6H:493`):

| field | T4 | T5 | T6 | meaning |
|---|---|---|---|---|
| `names` | `ScriptString*` | `uint16_t*` | `uint16_t*` | bone names as zone script-string indices, `boneCount[PART_TYPE_ALL]` of them |
| `numframes`, `framerate` | ✓ | ✓ | ✓ | length = numframes / framerate. The `end` notetrack lands exactly there **[V-data]** |
| `bLoop`, `bDelta` | ✓ | ✓ | ✓ | looped; has root motion |
| `bDelta3D` | — | — | ✓ | root motion rotates in 3D (full quat) rather than yaw only |
| `bStreamable` | — | ✓ | — | data is streamed, not in the zone. zonedump refuses these (`ANIM:148`) |
| `bLeftHandGripIK` | — | ✓ | ✓ | not used yet |
| `assetType` | ✓ | ✓ | ✓ | see §4 |
| `boneCount[10]` | ✓ | ✓ | ✓ | bones per `XAnimPartType` |
| `dataByte/Short/Int`, `randomDataByte/Short`, `indices` | ✓ | ✓ | ✓ | packed track data, read in order (§3) |
| `notify[notifyCount]` | ✓ | ✓ | ✓ | notetracks: `{name (script string), time}` |
| `deltaPart` | `{trans, quat}` | `{trans, quat}` | `{trans, quat2, quat}` | root motion. `quat` is 2D on T4/T5; on T6 `quat2` is 2D and `quat` 4D (`T6H:2702`) |

Part types, identical in all three games (`T4H:299`, `T5H:393`, `T6H:477`) **[V]**:

- Rotation: 0 `NO_QUAT`, 1 `HALF_QUAT`, 2 `FULL_QUAT`, 3 `HALF_QUAT_NO_SIZE`, 4 `FULL_QUAT_NO_SIZE`.
- Translation: 5 `SMALL_TRANS`, 6 `TRANS`, 7 `TRANS_NO_SIZE`, 8 `NO_TRANS`.
- 9 `ALL` is the total bone count.

## 3. Decoding

- **Order.** `names` is sorted by rotation type: the no-quat bones first, then half, full, half-constant and
  full-constant.
  - Rotation tracks are read in that order.
  - Each translation record starts with a byte bone index (`FXR:331`), so translations come in any bone order.
  - zonedump uses OAT's `xanim::CreateBoneTracksFromFlatData` (`FXR:266`). It checks that every pool is used up
    exactly.
- **Keyed track.**
  - A track stores `size` (u16); key count = `size + 1`.
  - Next come the key frame numbers: u8 when `numframes < 256`, otherwise u16 (`XAD:74`).
  - u16 frame numbers sit in `indices` once `size >= 64`. In that case `dataShort` also holds checkpoint copies,
    which the reader skips (`FXR:28-35`) **[V]**.
  - The 533-frame ai_zombie_quad_idle (T5) takes the u16 path and decodes with time increasing on every channel
    **[V-data]**.
  - Key times = frame / framerate. *_NO_SIZE tracks are a single constant.
- **Full quat.** Four int16 values (x, y, z, w), normalised; 32767 ≈ 1 (`ANIM:21`) **[V-data]**.
  - Checked on ai_zombie_walk_v1: j_clavicle_le keeps its rest (≈ 0.73, 0, 0.68, 0) and j_knee_le bends 23–71°.
- **Half quat.** Two int16 values (z, w), with x = y = 0, so the bone only rotates about its local z (`ANIM:28`) **[I]**.
  - It fits: fingers and bulge bones on half tracks stay continuous.
  - Not checked one bone at a time.
- **Translation.**
  - `SMALL_TRANS`: `mins + size * u8`. `TRANS`: `mins + size * u16`. So `size` is already divided per step (`ANIM:34`)
    **[V-data]**.
  - With that reading, j_mainroot comes out at a 31–37-unit hip height through the walk.
- **[!] Translations are offsets on the xmodel's own local translation, not absolute** (`ANIM:282`) **[I, strong]**.
  - Zombie anims give j_mainroot (-1…13, -8…1, -6…0). The model's local is (-3.4, 0, 37.2). Taken as absolute, the
    pelvis would sit on the floor. Added, it bobs between 31 and 37.
  - WaW viewmodel anims give j_elbow_le (12.09, 0, 0). The arms model stores 0 there and baseMat says 12.09. Added
    to 0, that is also right.
  - So channel value = model local trans + anim trans. Bones with no translation track get a constant channel at the
    model's local translation, when that differs from the baseMat rest (the viewmodel case).
- **Rotations are absolute locals** **[V-data]**. They replace the rest rotation (clavicle example above).
- **`NO_QUAT` bones** are written as a constant identity rotation (`ANIM:194`) **[I]**.
  - The zombie anims have 1–3 such bones each, and 0–2 of those have a non-identity rest rotation (thumb_1,
    tag_sync).
  - Whether the game uses identity or the model rotation there isn't settled. It only affects those few bones.
- **Root motion (`deltaPart`).**
  - Written as channels on the `tag_origin` joint, or on the first joint if the model has no tag_origin.
  - Translation decodes like a bone's; the 2D quat rotates about z only.
  - Raw values, cod units, relative to the anim's start.
  - The animation gets `e115_delta: true`. The player decides whether to apply it to the node or to the entity.
  - Example: ai_zombie_walk_v1 moves tag_origin 155.6 units forward over 4.133 s, ≈ 0.95 m/s **[V-data]**.
- **Notetracks.** `time` is normalised 0..1; seconds = time × length (`ANIM:257`) **[V-data]**: `end` lands on 4.133 s.
  Names are kept raw (`footstep_left_large`, `sndnt#step_zombie`, …).
- **Quaternion hemisphere.** Consecutive keys are sign-flipped onto one hemisphere so linear blending takes the short
  arc (`ANIM:187`).

## 4. Asset types and additive anims

`assetType` across the test set **[V-data]**:

| value | seen on | reading |
|---|---|---|
| 1 | viewmodel_zombie_idle/fire (T4), viewmodel_thundergun_idle (T5) | viewmodel / absolute **[I]** |
| 2 | ai_zombie_walk*, attack, idle_v1_delta, quad_idle (T4/T5/T6) | ordinary pose anim, usually with root motion **[I]** |
| 6 | ai_zombie_idle_v1 (T4, T5) | **additive** **[I]** |
| 0 | `void`, `void_loop` (T6) | empty placeholder **[I]** |

A sweep decoded every anim in three zones with zero errors **[V-data]**:

| game | zone | anims | type 1 | type 2 | type 6 | type 0 |
|---|---|---|---|---|---|---|
| T4 | nazi_zombie_prototype + common | 1976 | 461 | 1358 | 157 | — |
| T5 | zombie_theater + common + common_zombie | 3375 | 1127 | 2005 | 243 | — |
| T6 | zm_nuked + code_post_gfx_zm + common_zm | 2532 | 1657 | 873 | — | 2 |

- No `bDelta3D` anim turned up.
- The type-6 names are aim and look layers (`combatrun_head_2/4/6/8`, `cornerstndl_lean_aim_*`), the classic use of
  additive anims, which supports the reading.
- T6 zm_nuked has no type 6 at all.

- In a type-6 anim every rotation sits within ~2° of identity and there is no root motion. The same bones are turned
  up to 180° at rest, so this cannot be a full pose. It is a layer of offsets.
- zonedump sets `e115_additive: true` (`ANIM:255`), writes those translations raw (not added to the model's), and
  adds no constant-translation channels.
- Composition is the player's job **[I]**: `rotation = base * offset` and `translation = base + offset`. The order of
  that rotation product is not verified.

## 5. Binding anims to models

- **By bone name.** An anim names its bones; the model names its joints. zonedump binds by exact name (`ANIM:249`).
  - Anim bones the model doesn't have are listed in the export line, for example the face, coat and collar bones that
    the separate head model carries.
  - Joints the anim doesn't name keep their rest pose.
- **Partial anims.**
  - A zombie body binds 72 of the walk's 108 bones; the rest belong to the head or gear models.
  - The viewmodel arms bind 65 of 70; the other five are gun bones (j_gun, j_bolt, tag_flash…) that belong to the
    weapon model.
  - So one anim drives several attached models, each by name **[V-data]**.
- **Shared across games.** T6's zm_nuked `ai_zombie_walk_v1` decodes to the same values as T4's (same keys, same
  extremes), so Treyarch carried the asset forward **[V-data]**.
- **Merging attached models** (`--xanim <anims> body,head,gun@tag out.glb`):
  - Later models share joint nodes with earlier ones by bone name; new bones are appended under their parent.
  - Each mesh keeps **its own skin** (its own inverse binds) over those shared nodes. Heads are bound in their own
    bind pose: char_ger_honorgd_zombiehead1_1 and the body share 5 bones whose IBMs differ by up to 52 units, so one
    shared skin would misplace the head **[V-data]**.
  - `@tag` puts a model's unshared root under that joint. The kar98 `j_gun` goes on the arms' `tag_weapon` (the CoD
    attach point [I]).
    - The rifle then lies along +x between the hands (right wrist x -7.4 by the bolt, left x +7.3 under the
      fore-end) and follows the rechamber.
    - One small kar98 part sits at y ≈ 37 in the bind itself, probably the stripper clip parked off-screen until the
      reload [I].
  - Head placement at rest, CPU-skinned from the glb: head z 57.7–71.4 around j_head 63.5, on a body topping out at
    62.6. During the walk it follows j_head (T4, T5 and T6) **[V-data]**.
- **Foot plant** (ai_zombie_walk_v1, root motion applied, j_ball_le/ri world positions per frame) **[V-data]**:
  - The lowest foot is 0.27–0.85 units off the ground (median 0.38).
  - The stance foot slides at a median 1.7 units/s while the body travels at 37.6 units/s. For example, j_ball_le
    holds x ≈ 103.5 from frame 70 to frame 90.
  - walk_fast_v1 is the same picture: 1.8 against 65.4.
  - This checks rotations, additive translations and root motion together.
- **Tags in anims.** tag_weapon_right, tag_inhand and tag_sync carry large translations in zombie anims (up to ~400
  units). They are attach and sync points, not deforming bones, and the export stats skip `tag_*`.

## 6. zonedump usage

```
e115_zonedump <zone.ff> [--load <dep.ff>]... --game <install> --xanim <anim[,anim...]|*> <xmodel> <out.glb>
```

- Models and anims are searched in the zone and every `--load` zone.
- Output: one glb with the skinned model and one glTF animation per anim.
- Animation extras:
  - `e115_frame_rate`
  - `e115_looped`
  - `e115_delta`
  - `e115_additive`
  - `e115_notetracks: [{name, time (s)}]`
- Each anim prints a stats line:
  - asset type, frames, fps, length and last key;
  - flags;
  - bones bound / total;
  - largest frame-0 deviation from rest;
  - no-quat bone count;
  - bones the model lacks.

## 7. Open questions

1. `NO_QUAT`: identity or model rotation **[I]**.
2. Half-quat axis: (0, 0, z, w) **[I]**.
3. The rotation order for composing additive anims, and whether the other `assetType` values exist and what they mean.
4. T5 streamed anims (`bStreamable`): their data lives in an external file, which zonedump doesn't read.
5. Root-motion conventions on T6 `bDelta3D` anims (full-quat delta). None in the test set yet.
6. In-engine visual check of all of the above. That is the lead's player (GltfLoader + GPU skinning).
