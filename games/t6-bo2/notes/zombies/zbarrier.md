# Zombies windows: T6 (BO2) zbarriers

How BO2 boards its windows, for the T6 `WindowRules`. T4/T5 windows are brush models with a clip (`zombies_t4_nacht.md`,
`zombies_t5_vs_t4.md`). T6 replaces the brushes with one `zbarrier` entity per window. It's an animated, multi-piece
entity defined by a `zbarrier` asset.

Tags:
- **[V]**: read from:
  - OAT's `T6_Assets.h` (`ZBarrierDef`, `ZBarrierBoard`), `ZBarrierFields.h` and `ZBarrierDef.txt`
  - zbarrier, mapents and rawfile assets dumped with OAT Unlinker
  - the animstate def `animstatedefs/zm_transit_basic.asd` (a rawfile in `so_zclassic_zm_transit.ff`)
  - `maps/mp/zombies/_zm_blockers.gsc` and `_zm_spawner.gsc`: decompiled output already on disk from the earlier
    BO1MapConverter work (gsc-tool output under `<scratch>/allzm/dump/decompiled/t6`), not decompiled for this doc
- **[M]**: counted in the dumped ents and assets, or found with `e115_zonedump --names`.
- **[I]**: inferred.

Units are T6 inches.

## Asset: `ZBarrierDef` [V]

One asset per barrier kind. Sizes were computed from the OAT header for the 32-bit build [I]: `ZBarrierBoard` 0x50,
`ZBarrierDef` 0x230. They aren't static_asserted yet.

| field | meaning |
|---|---|
| `name` | e.g. `zmcore_basicwoodbarrier` |
| `numBoardsInBarrier` | pieces in use, up to 6 |
| `boards[6]` | one `ZBarrierBoard` per piece |
| `numAttackSlots`, `attackSpotHorzOffset` | the attack spots, see below |
| `taunts`, `zombieTauntAnimState` | whether zombies taunt at it, and the animstate (`zm_taunt`) |
| `reachThroughAttacks`, `zombieReachThroughAnimState` | whether zombies swipe through it, and the animstate (`zm_window_melee`) |
| `autoHideOpenPieces` | hide a piece once it's open |
| `generalRepairSound1/2`, `upgraded…`, `delayBetweenRepSounds…` | rebuild sounds (alias hashes) |
| `earthquakeOnRepair` + min/max scale, duration, radius | the camera shake on rebuild |

`ZBarrierBoard`, per piece:

| field | meaning |
|---|---|
| `pBoardModel` / `pAlternateBoardModel` / `pUpgradedBoardModel` | the piece model, alternate, and the upgraded (rebuild perk) model |
| `pTearAnim` | the piece's own anim when torn off (`o_zombie_board_N_pull`) |
| `pBoardAnim` | the piece's anim when rebuilt (`o_zombie_board_N_repair`) |
| `zombieBoardTearStateName` | the zombie's animstate for this piece (`zm_zbarrier_board_tear`) |
| `zombieBoardTearSubStateName` | the piece's substate token (`horz_1`, `vert_1`, …) |
| `numRepsToPullProBoard` | the extra tear loops for an upgraded piece (3) |
| `repairEffect1/2`, offsets, `boardRepairSound`, hover sound, pause min/max | rebuild fx and sound |

The anim and state names are strings, script strings in the zone. The models and fx are pointers.

## Assets per map [M]

| zone | zbarrier assets |
|---|---|
| `zm_nuked.ff` | `zmcore_magicbox` only |
| `zm_transit.ff` | `zmcore_basicwoodbarrier`, `zmcore_basicwoodbarrier_hide_pieces`, `zmcore_magicbox`, `zb_buswindow0`, `zb_buswindow5` |
| `zm_highrise.ff`, `zm_buried.ff` | basicwoodbarrier, _hide_pieces, magicbox |
| `zm_prison.ff` | basicwoodbarrier, _hide_pieces, `zmprison_magicbox` |
| `zm_tomb.ff` | basicwoodbarrier, `zmtomb_magicbox` |

`common_zm`, `patch_zm` and the `so_*` zones have none. The zbarrier asset is also used for the magic box: its
"pieces" are the box states (fake / arrive-leave / open-close / weapon rise / dual rise).

`zmcore_basicwoodbarrier` [M]:
- 6 boards, models `p6_anim_zm_barricade_board_01..06` (+`_upgrade`), no alternates.
- Tear anims `o_zombie_board_N_pull`, rebuild anims `o_zombie_board_N_repair`.
- Zombie state `zm_zbarrier_board_tear`, substates for boards 1..6 in order: `horz_1`, `vert_1`, `vert_2`, `horz_2`,
  `horz_3`, `horz_4`.
- `numAttackSlots` 3, `attackSpotHorzOffset` 28, taunts 1, reach-through 1, `numRepsToPullProBoard` 3.

`_hide_pieces` is the same with `autoHideOpenPieces` 1.

The bus windows `zb_buswindow*` [M]:
- 5 boards `p6_anim_zm_barricade_board_bus_0N`, state `zm_zbarrier_bus_board_tear`.
- 1 attack slot, no taunts, no reach-through, autoHide 1.

The models and piece anims (`p6_anim_zm_barricade_board_*`, `p6_anim_zm_barricade_board_collision`,
`o_zombie_board_*`) are in `zm_transit.ff`. The zombie anims are in `so_zclassic_zm_transit.ff` [M].

## Map ents [V][M]

- **Classname** `zbarrier_<asset>`, e.g. `zbarrier_zmcore_BasicWoodBarrier`. `type` holds the asset name.
- **Keys:** `origin`, `angles`, `targetname`, `script_string`, `zbarriernumboards`, `barrieranimtime`,
  `showalternatemodel`, `showupgradedmodel`, and per board `zbarrierboardmodelN`, `zbarrierupgradedboardmodelN`,
  `zbarriertearanimN`, `zbarrierboardanimN`. The per-board keys repeat the asset's values; Radiant writes them.
- **Window goal:** a `script_struct` with targetname `exterior_goal`. Its `target` is the zbarrier's `targetname`
  (auto names like `pf0_auto1`). Its `script_string` names the window (`vault_baricade1`, `diner_baricade2`), and the
  zbarrier carries the same `script_string`.
  - `_zm_blockers::blocker_init` takes the goal's targets. The one that `iszbarrier()` becomes the window. It also gets
    collision model `p6_anim_zm_barricade_board_collision` and `chunk_health[]` zeroed per piece.
- **Mode filter:** zbarriers are deleted when the game type isn't classic, standard or grief (`should_delete_zbarriers`).

Counts [M]:

| map | ents | windows (exterior_goal → zbarrier) | other zbarriers |
|---|---|---|---|
| zm_nuked | 1533 | **0**, and no `exterior_goal` at all | 5 `zbarrier_zmcore_MagicBox` (script_noteworthy `start_chest1_zbarrier`, …) |
| zm_transit | 8102 | **38**: 34 BasicWoodBarrier + 4 _hide_pieces, every one linked | 6 MagicBox, 10 bus windows (9 BusWindow5, 1 BusWindow0), not linked to a goal |

- All 38 transit windows have `zbarriernumboards` 6.
- Nuketown has no boarded windows, so its zombies only rise or drop in [I from the 0 count]. A T6 window rule finds
  nothing there, which is correct.
- The bus windows are driven by the bus scripts, not `exterior_goal`. Leave them out.

## How a zombie attacks a window [V]

From `_zm_spawner.gsc` (decompile output already on disk) and the `.asd`:

1. **Pick the goal.** If the spawn has a `find_flesh_struct_string`, the goal is the `exterior_goal` whose
   `script_string` matches it. Otherwise it's chosen from the 3 closest goals.
2. **Walk to it.** `setgoalpos(goal.origin)` with goalradius 128.
3. **Take an attack spot** (`blocker_attack_spots`):
   - `numslots` = `max(numAttackSlots, 1)`.
   - With an odd count, spot 0 = the ground below `zbarrier.origin + 60 up`.
   - Then pairs at ± `attackSpotHorzOffset × k` along the goal's right vector. Spot 1 is `+right`, spot 2 is `-right`.
   - Basic wood: 3 spots, centre and ±28.
   - The spot is picked at random from the free ones. With none free, the zombie taunts (`zm_taunt`, if the barrier
     allows) and retries every 0.5 s.
4. **Line up.** goalradius 2, goal = the spot, facing `zbarrier.angles`. It waits for `orientdone`, at most 1 s.
5. **Tear one piece at a time:**
   - The piece is the closest one not yet destroyed. Its state goes to `targetted_by_zombie`.
   - The zombie plays `<state>_in`, then `<state>_loop` while `chunk_health[piece] > 0` (each loop takes 1), then
     `<state>_out`. All three are scripted at the zbarrier's origin and angles.
   - The substate is `spot_<spot>_piece_<boardSubState>`. A crawler gets the `_crawl` states.
   - The piece goes to `opening` on the zombie's `board`, `destroy_piece` or `bar` notetrack.
   - Plain boards have `chunk_health` 0, so `_loop` never plays. An upgraded board starts at the piece's upgraded
     lives (`getupgradedpiecenumlives`; the asset says 3).
   - If the zombie dies or goes inert, the piece goes back to `closed`.
6. **Between pieces: reach-through** (`zm_window_melee`). Needed: the zombie has legs, the barrier allows it, a live
   player (not downed, no zombie blood) is within 2D distance 109.8 of the zombie, and a roll against dvar
   `zombie_reachin_freq` (default 50) passes. Where in the loop this is called wasn't read [I].
7. **When every piece is gone:** the zombie plays `zm_barricade_enter`, substate `barrier_<walk|run|sprint>_<m|r|l>`,
   with m/r/l for spot 0/1/2. Then `find_flesh`. `level notify("last_board_torn", origin)`.
8. **Rebuild:** a player sets a piece to `closing` (the anim length is scaled), with the upgraded lives if the perk is
   on. Points `rebuild_board` up to `rebuild_barrier_cap_per_round`.

The piece states seen in script are `closed`, `targetted_by_zombie`, `opening` and `closing` [V]. An "open" state is
implied by `all_chunks_destroyed` [I].

## Board-tear xanims [V]

From `zm_transit_basic.asd`. The other maps' `.asd` weren't read [I: the same names are in every map's zone, see
`animation_t4_t5_t6.md` / the zombie model table].

| state (+`_crawl`) | substate | xanim |
|---|---|---|
| `zm_zbarrier_board_tear_in` | `spot_S_piece_P` | `ai_zombie_[crawl_]boardtear_aligned_<m,r,l>_<1..6>_grab` |
| `zm_zbarrier_board_tear_loop` | same | `…_hold` |
| `zm_zbarrier_board_tear_out` | same | `…_pull` |

- S 0/1/2 → m/r/l.
- P → index: `horz_1` 1, `vert_1` 2, `vert_2` 3, `horz_2` 4, `horz_3` 5, `horz_4` 6. That's board order, so board N
  uses `_N_`.
- `zm_board_tear_in/loop/out` (no "zbarrier") are the T5-style brush-board states, with the same `m_*` anims.

| state | xanims |
|---|---|
| `zm_window_melee` | `ai_zombie_window_attack_arm_l_out`, `ai_zombie_window_attack_arm_r_out` |
| `zm_taunt` | `ai_zombie_taunts_4`, `_7`, `_9`, `_5b`…`_5f` |
| `zm_barricade_enter` (+`_crawl`) | walk m `ai_zombie_barricade_enter_m_v1/v2`, run m `_m_v5`, sprint m `_m_v6/v7`; r: `_enter_r` / `_enter_run_r` / `_enter_sprint_r`; l the same with `_l` |
| `zm_zbarrier_bus_board_tear_*` | the bus set (`ai_zombie_bus_boardtear_<l,r>_<1..5>_<grab,hold,pull>`) |

The same `.asd` confirms the T6 idle and death states:
- `zm_idle` = `ai_zombie_idle_v1_delta`
- `zm_death` = `ch_dazed_a/b/c/d_death`

## Proposed T6 `WindowRules` [I]

Today's fields are `goalTargetname`, `boardClassname` and `clipNoteworthy`. A T6 window has no brush boards and no clip
brush, so I'd extend it rather than overload those fields.

| field | t4/t5 | t6 |
|---|---|---|
| `goalTargetname` | `exterior_goal` | `exterior_goal` (unchanged) [V] |
| `boardClassname` | `script_brushmodel` | empty: not brushes |
| `clipNoteworthy` | `clip` | empty: the collision is a model |
| `barrierClassPrefix` (new) | empty | `zbarrier_`: the goal's target whose classname starts with this is the window [V] |
| `barrierAssetKey` (new) | empty | `type`: the zbarrier asset name [V] |
| `pieceKeyPrefixes` (new) | - | `zbarrierboardmodel`, `zbarriertearanim`, `zbarrierboardanim`, `zbarrierupgradedboardmodel` + N, count `zbarriernumboards` [V] |
| `collisionModel` (new) | - | `p6_anim_zm_barricade_board_collision` [V] |
| `attackSlots`, `attackSlotOffset` (new) | t4/t5 fixed spots | read from the asset; fallback 3 / 28 [V] |
| `tearStates` (new) | t4/t5 anims | `zm_zbarrier_board_tear` `_in/_loop/_out`, substate `spot_S_piece_P` → `ai_zombie_boardtear_aligned_<mrl>_<n>_<grab,hold,pull>` [V] |
| `enterState` (new) | - | `zm_barricade_enter` `barrier_<speed>_<mrl>` [V] |
| `reachThrough` (new) | - | range 109.8, frequency 50 % [V] |

Reading the attack slots from the asset needs a small zbarrier export: name, numAttackSlots, offset, per-board
model/anim/substate. It's not built. The zonedump side is a contributor's. Until it exists, the 3 / 28 / 6-board defaults cover every
`zmcore_basicwoodbarrier*` window.

## Not read

- The other maps' `.asd`.
- Where reach-through and the taunt sit in the tear loop.
- The zone manager's window gating on T6.
- The zbarrier piece anims' notetracks and lengths.
- How `barrieranimtime` is used.
