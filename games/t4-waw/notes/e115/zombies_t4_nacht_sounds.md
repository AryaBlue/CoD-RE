# Zombies: T4 Nacht sound aliases

Which sound alias plays at each moment of a Nacht match, and where the call is made. The alias data itself (files,
volumes, falloff) is in our `sounds.json` export. This doc only maps moments to alias names. It is the companion to
`zombies_t4_nacht.md` (rules), `zombies_t4_nacht_flow.md` (flow and HUD) and `zombies_t4_nacht_ai.md` (AI).

Tags:
- **[V]**: read in the source, with a file:line.
- **[I]**: inferred. Treat as a guess until checked.

Sources:
- Scripts were dumped with OAT to a scratch folder outside the repo. No script text is copied here.
- `patch.ff` overrides Nacht (see the rules doc). The effective files are:
  - from `patch.ff`: `maps/_zombiemode_prototype.gsc`, `_zombiemode_spawner_prototype.gsc`, `_zombiemode_blockers.gsc`
    and `nazi_zombie_prototype.gsc`
  - from the zone: `_zombiemode_powerups.gsc`, `_zombiemode_weapons.gsc`, `_zombiemode_radio.gsc`
  - from `common.ff`: `animscripts/*.gsc`, `clientscripts/_footsteps.csc`
- Notetrack times come from the zone's xanims (zonedump `--xanim`, in the glb extras).

## How sounds are named [V]

There are two layers:
- **Script refs.** `init_sounds` (`_zombiemode_prototype.gsc:202-241`) maps short refs to aliases with `add_sound`. The
  zombie scripts then play the ref, for example `play_sound_at_pos("purchase", ...)` plays `cha_ching`.
  `nazi_zombie_prototype.gsc:241` adds one more: `break_stone`.
- **Anim notetracks.** Zombie xanims carry notetracks named `sndnt#<alias>`. The engine plays `<alias>` on the zombie at
  that frame [I: engine-side, no script handles `sndnt#`; nothing in animscripts matches it].

### The ref table [V] (`_zombiemode_prototype.gsc:204-240`)

| ref | alias |
|---|---|
| `end_of_round` | `round_over` |
| `end_of_game` | `mx_game_over` |
| `chalk_one_up` | `chalk` |
| `purchase` | `cha_ching` |
| `no_purchase` | `no_cha_ching` |
| `playerzombie_*` | `attack_vocals` |
| `zombie_head_gib` | `zombie_head_gib` |
| `rebuild_barrier_piece` | `repair_boards` |
| `rebuild_barrier_hover` | `boards_float` |
| `debris_hover_loop` | `couch_loop` |
| `break_barrier_piece` | `break_boards` |
| `blocker_end_move`, `barrier_rebuild_slam` | `board_slam` |
| `door_slide_open`, `door_rotate_open` | `door_slide_open` |
| `debris_move` | `weap_wall` |
| `open_chest` | `lid_open` |
| `music_chest` | `music_box` |
| `close_chest` | `lid_close` |
| `weapon_show` | `weap_wall` |

## Zombie voice and body

| moment | alias | when | source |
|---|---|---|---|
| Ambient groan | `amb_vocals` | frame 0 of every walk cycle (`ai_zombie_walk_v1`-`v4`) and the idle (`ai_zombie_idle_v1_delta`), so once per loop | notetracks [V] |
| Sprint vocal | `sprint_vocals` | `ai_zombie_sprint_v1` at 0.30 s, `_v2` at 1.27 s | notetracks [V] |
| Crawler vocal | `crawl_vocals` / `crawl_vocals_slow` | `ai_zombie_crawl_sprint` 0.30 s; `ai_zombie_crawl_v1` 1.17 s | notetracks [V] |
| Crawler hands | `crawl_hands` | 4-6 per crawl cycle | notetracks [V] |
| Footsteps | `step_zombie`, plus `step_sweetner` at 0 s in walk v1 and v4 | each step in walk, fast-walk and sprint cycles | notetracks [V] |
| Attack vocal | `attack_vocals` | at the start of each melee: script call when a zombie melees, plus 0 s in all 4 attack anims (`attack_v2` also at 3.20 s) | `animscripts/melee.gsc:110`; notetracks [V] |
| Attack swipe | `attack_whoosh` | 2-5 per attack anim, for example `ai_zombie_attack_v1` at 0.67 s and 1.13 s | notetracks [V] |
| Death | `generic_death_german` | on death, unless the hit was to the head or helmet. The zombie's `deathFunction` returns false, so the stock death path runs on | `animscripts/death.gsc:50-57`, `:135-141`, `:513-519`; `face.gsc:60` builds `generic_<type>_<voice>`; voice is `german` (`character/char_ger_honorguard*_zombies.gsc:7`) [V] |
| Headshot death | `bullet_impact_headshot_helmet` or `bullet_impact_headshot` | instead of the death vocal on a head or helmet kill | `death.gsc:144-155` [V] |
| Head gib | `zombie_head_gib` | when the head comes off | `_zombiemode_spawner_prototype.gsc:607` [V] |
| Limb gib | `generic_gib_german`; `death_gibs` at the position | on a limb gib (if not dying quietly) | `death.gsc:1492`, `:2082` [V; whether zombies reach `:1490` (it checks `self.type == "human"`) is I] |
| Nuke kill | `nuked` on each zombie | | `_zombiemode_powerups.gsc:373` [V] |

## Barriers

| moment | alias | when | source |
|---|---|---|---|
| Zombie tears a board | `remove_boards` | notetracks in the tear anims: `ai_zombie_door_tear_v1` (7, from 0.27 s), `_high` 0.90 s, `_left` 1.03 s, `_right` 0.93 s. `_v1` and `_right` also have `attack_vocals` | notetracks [V] |
| Board breaks off | `break_boards` (ref `break_barrier_piece`) | at the chunk when it is torn away | `_zombiemode_blockers.gsc:755` [V] |
| Player repairs: start | `repair_boards` (ref `rebuild_barrier_piece`) | each board the player puts back | `:683` [V] |
| Board flies back | `boards_float` (ref `rebuild_barrier_hover`) | as the board moves into place, unless the chunk's `script_presound` overrides it | `:876-882` [V] |
| Board lands | `board_slam` (ref `barrier_rebuild_slam`) | when it is solid again, unless the barrier's `script_ender` overrides it | `:908-914` [V] |

## Window climb [V]

The climb-through anims have no `sndnt#` sounds. They have engine notetracks:
- `footstep_left_large` / `footstep_right_large`. The client plays `step_run_<ground>` (or `step_run_dirt` on default
  ground), plus `gear_rattle_run` (`clientscripts/_footsteps.csc:1-15`).
- `bodyfall large`. This plays `bodyfall_<ground>_large`, with ground `dirt` if not set (`animscripts/shared.gsc:801-812`).

| anim | notes |
|---|---|
| `ai_zombie_traverse_v1` | footstep R 0.47 s, footstep L 1.17 s |
| `ai_zombie_traverse_v2` | footstep L 1.27 s |
| `ai_zombie_traverse_crawl_v1` | footstep R 0 s, bodyfall large 1.97 s |

Whether zombie footstep notetracks reach `_footsteps.csc` is [I]. It is the stock path for AI footsteps.

## Doors and debris [V] (`_zombiemode_blockers.gsc`)

| moment | alias | source |
|---|---|---|
| Door bought | `cha_ching` (ref `purchase`) | `:160` |
| Door opens | `door_slide_open` (both refs) | `:172` rotate, `:187`, `:206` slide |
| Debris bought | `cha_ching` | `:361` |
| Debris lifts | `weap_wall` (ref `debris_move`), and `lightning_l` at its position | `:437`, `:438` |
| Debris lands | `couch_slam` | `:472` |
| Debris deleted | `zombie_spawn` at its position (it matches the particle) | `:478` |
| Can't afford | `no_cha_ching` (ref `no_purchase`) | `:257`, `:425` |

`couch_loop` (ref `debris_hover_loop`) is registered but its loop call is commented out at `:473`.

## Round and game

| moment | alias | when | source |
|---|---|---|---|
| Match start music | music states `SPLASH_SCREEN`, then `WAVE_1` | intro: wait 1 s, `SPLASH_SCREEN`, wait 0.2 s, `WAVE_1`. `round_think` sets `WAVE_1` again | `_zombiemode_prototype.gsc:398`, `:401`, `:1174` [V] |
| Round start | `chalk` (ref `chalk_one_up`) | when the tally mark appears: 1.5 s into round 1's intro, else 0.5 s after the chalk fades out | `:1052` [V] |
| Round end | `round_over` (ref `end_of_round`) | 2.5 s into the 10 s break | `:1122` [V] |
| Game over | `mx_game_over` (ref `end_of_game`) | 1 s after "GAME OVER" fades in | `:1735` [V] |

There is no per-round music change. The aliases for the music states live in the zone's music data [I: not traced].

## Power-ups [V] (`_zombiemode_powerups.gsc`)

| moment | alias | source |
|---|---|---|
| Spawn | `spawn_powerup`, then loop `spawn_powerup_loop` while it is on the ground | `:214`, `:224` |
| Grab | `powerup_grabbed` | `:271` |
| Insta-Kill | loop `insta_kill_loop` while active; `insta_kill` at the end | `:496`, `:519` |
| Double Points | loop `double_point_loop` while active; `points_loop_off` at the end | `:568`, `:584` |
| Max Ammo | `full_ammo` | `:623` |
| Nuke | `nuke_flash` at the flash, `nuked` on each zombie | `:379`, `:373` |

## Mystery box and wall weapons [V] (`_zombiemode_weapons.gsc`)

| moment | alias | source |
|---|---|---|
| Box opens | `lid_open` (ref `open_chest`) and the jingle `music_box` (ref `music_chest`) together | `:400-401` |
| Box closes | `lid_close` (ref `close_chest`) | `:410` |
| Purchase | `cha_ching` (ref `purchase`): box and wall buys | `:564`, `:633`, `:647`, `:660`, `:891`; direct alias `:945` |
| Can't afford | `no_cha_ching` | `:639`, `:653`, `:705`, `:784`, `:819` |
| Wall weapon shown | `weap_wall` (ref `weapon_show`) | `:849` |

## Radio [V]

The radio is client-side (`clientscripts/nazi_zombie_prototype_amb.csc`):
- `static` plays between songs (`:105`).
- The song is `level.radio_songs[level.radio_index]` (`:116`).
- `stopSound` cuts the current one (`:71`).

The server side triggers it with a level notify from `_zombiemode_radio.gsc`.

## Open items

- `sndnt#` handling is engine-side [I]. Check that our anim player fires these notetracks as sounds.
- The music-state aliases (`SPLASH_SCREEN`, `WAVE_1`) were not traced to alias names.
