# Zombies: Kino der Toten (`zombie_theater`) ent checklist

A per-ent checklist for the native route, in the format of `zombies_t4_asylum_ents.md`. It covers what Kino's ents
hold, with counts, the keys to read, and a profile field for each: an existing one where there is one, otherwise a
suggestion. T5's general rules (spawners, zones, door types, the box, risers) are in `zombies_t5_vs_t4.md`, which this
doc points to instead of repeating.

Tags:
- **[V]**: read. `ents:N` is the line of the ent's opening brace in the zone dump's `maps/zombie_theater.d3dbsp.ents`
  (OAT Unlinker, `zombie_theater.ff`). The script refs are:
  - `zt:` = `maps/zombie_theater.gsc`, from `zombie_theater_patch.ff`
  - `tp:` = `maps/zombie_theater_teleporter.gsc`, from `zombie_theater_patch.ff`
  - `quad:` = `maps/zombie_theater_quad.gsc`, from `zombie_theater.ff`
  - `perks:` / `traps:` / `blockers:` / `dogs:` / `spawner:` / `zonemgr:` / `weapons:` = the
    `_zombiemode_*.gsc` from `common_zombie_patch.ff`
- **[M]**: counted by script over the parsed ents (2794 ents).
- **[I]**: inferred.

**Which scripts ship [V].** `zombie_theater_patch.ff` replaces the zone's `zombie_theater.gsc`. The diff only adds the
`zombie_theater_ffotd` start/end calls, `zombie_dog_pathing_hack` and `barricade_glitch_fix`, and drops `theater_exit_level`.
The patch also carries `_magic_box`, `_movie_screen` and `_teleporter`. Cite the patch copies. These are BO1 rawfiles, so
the GSC is source, not bytecode.

**Scope.** "T5" means the pattern comes from `common_zombie_patch.ff` and belongs in the T5 `GameProfile`. "KI" means only
Kino's map scripts use it, so it belongs in a per-map override.

---

## 0. Summary

| # | kind | ents [M] | scope | profile field | ref |
|---|---|---|---|---|---|
| 1 | perk machines | 4 triggers, 4 machines, 1 clip | T5 | `perks.*` (T4 only today; T5 needs its own) | §1 |
| 2 | Pack-a-Punch | 1 trigger, 1 machine, 1 jingle struct | T5 | new `perks.packAPunch*` | §2 |
| 3 | power switch | 1 trigger, 1 lever, 1 fx struct | T5 (`uses.powerSwitch` exists) | `uses.powerSwitch` | §3 |
| 4 | electric doors | 2 triggers, 1 door group | T5 (`uses.electricDoor` exists) | `uses.electricDoor` | §4 |
| 5 | teleporter + projector link | 2 triggers, 2 cables, 1 light, 4×3 destination origins, 2 POIs | KI | new per-map `teleporter.*` | §5 |
| 6 | mystery box | 9 chests (trigger, lid, box, origin each), 81 lights, 1 rubble | T5 + KI lights | `uses.box*` + new `box.*` | §6 |
| 7 | traps | 5 trap triggers, 10 buy triggers, 20 models, 27 fx structs | T5 | new `traps.*` | §7 |
| 8 | doors | 12 `zombie_door` triggers, 10 door groups | T5 (`blockers.*` exists) | `blockers.*` | §8 |
| 9 | zones | 24 `info_volume`s in 10 zones | T5 (`zones.*` exists) + KI adjacency | `zones.*` | §9 |
| 10 | spawners, risers | 28 regular, 21 quad, 1 dog spawner, 7 rise structs | T5 | `zombieSpawners.*`, `risers.*` | §10 |
| 11 | dogs | 1 spawner, 84 dog structs, 3 dog clips | T5 | new `dogs.*` | §11 |
| 12 | special rounds (quads) | 21 quad spawners in 7 groups | KI | per-map `quadRounds.*` | §12 |
| 13 | windows | 22 `exterior_goal`s, 22 board groups | T5 (`windows.*` exists) | `windows.*` | §13 |
| 14 | wall buys, Bowie, Claymore | 10 + 1 + 1 triggers | T5 (`uses.*` exists) | `uses.weaponKey` | §14 |
| 15 | extras | movie screen and reels, curtains, chandeliers, clock, easter eggs, ambience | KI | per-map | §15 |

**Confirmed absent [V]:** none of the BO1-new perks is on Kino, so no Stamin-Up, PhD Flopper, Deadshot or Mule Kick.
- No `vending_marathon` / `_divetonuke` / `_deadshot` / `_additionalprimaryweapon` ent.
- Mule Kick is spawned by script only when `level.zombie_additionalprimaryweapon_machine_origin` is set (perks:111-117).
  Kino's scripts (zt, ffotd) never set it.

---

## 1. Perk machines (T5)

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| buy trigger | `trigger_use` | `zombie_vending` | `script_noteworthy` = specialty; `target` = machine; `script_string` = `<x>_perk`; `script_sound` = jingle; `script_label` = sting | 4 | 11338 |
| machine | `script_model` | `vending_revive` / `_sleight` / `_doubletap` / `_jugg` | `model` = off model; `script_string` = `<x>_perk` | 4 | 11349, 11394, 11413, 11441 |
| machine clip | `script_brushmodel` | `vending_revive` | `script_noteworthy` = `clip` | 1 | 11366 |
| rattle bumps | `trigger_multiple` | `audio_bump_trigger` | `script_sound` | 5 | 11357 |

| perk | `script_noteworthy` | `script_string` | jingle / sting (`script_sound` / `script_label`) | cost [V perks:1121-1163] | power notify → armed notify [V perks] |
|---|---|---|---|---|---|
| Quick Revive | `specialty_quickrevive` | `revive_perk` | `mus_perks_revive_jingle` / `_sting` | 1500, solo 500 | `revive_on` → `specialty_quickrevive_power_on` (:776) |
| Speed Cola | `specialty_fastreload` | `speedcola_perk` | `mus_perks_speed_jingle` / `_sting` | 3000 | `sleight_on` → `specialty_fastreload_power_on` (:757) |
| Double Tap | `specialty_rof` | `tap_perk` | `mus_perks_doubletap_jingle` / `_sting` | 2000 | `doubletap_on` → `specialty_rof_power_on` (:914) |
| Juggernog | `specialty_armorvest` | `jugg_perk` | `mus_perks_jugganog_jingle` / `_sting` | 2500 | `juggernog_on` → `specialty_armorvest_power_on` (:895) |

- The on model is `<off model>_on` for all four (perks:757-914).
- T5 changes from T4: the jingle and sting are now ent keys (`script_sound`, `script_label`), not a separate
  `perksacola` struct per perk. The `perksacola` struct is only left on Pack-a-Punch.
- The solo Revive price is 500 (perks:1128).
- The BO1 perks the common script supports, so other T5 maps may carry them [V perks]:

| specialty | perk | cost | machine targetname | on model | notify |
|---|---|---|---|---|---|
| `specialty_longersprint` | Stamin-Up | 2000 | `vending_marathon` | `zombie_vending_marathon_on` | `marathon_on` |
| `specialty_flakjacket` | PhD Flopper | 2000 | `vending_divetonuke` | `zombie_vending_nuke_on` | `divetonuke_on` |
| `specialty_deadshot` | Deadshot | 1000 | `vending_deadshot` | `zombie_vending_ads_on` | `deadshot_on` |
| `specialty_additionalprimaryweapon` | Mule Kick | 4000 | `vending_additionalprimaryweapon` | `zombie_vending_three_gun_on` | none (always on, :1005) |

Fields: T5 reuses `perks.triggerTargetname = "zombie_vending"` and `perks.specialtyKey = "script_noteworthy"` (T5),
with a T5 `PerkDef` list carrying the 8 rows and costs above, plus 500 for solo Revive. Suggested additions:
- `perks.jingleKey = "script_sound"`, `perks.stingKey = "script_label"` (T5)
- `perks.soloReviveCost = 500` (T5)

## 2. Pack-a-Punch (T5)

| role | classname | targetname | keys | ents |
|---|---|---|---|---|
| trigger | `trigger_use` | `zombie_vending_upgrade` | `script_noteworthy` = `specialty_weapupgrade`, `target` = machine | 11458 |
| machine | `script_model` | `vending_pack_a_punch_1` | `model` = `zombie_vending_packapunch` | 11474 |
| jingle | `script_struct` | `perksacola` | `script_sound` = `mx_packa_jingle` | 11481 |

- Cost 5000, or 1000 during Bonfire Sale (perks:519-530).
- It waits for `Pack_A_Punch_on` (perks:709), then becomes `zombie_vending_packapunch_on`.
- On Kino the `Pack_A_Punch_on` notify comes from the power switch (zt:368, §3).
- The trigger sits by the stage (`7 -473 359`).

Suggested fields: `perks.packTargetname = "zombie_vending_upgrade"`, `perks.packCost = 5000`, `perks.packSaleCost = 1000`,
`perks.packPowerNotify = "Pack_A_Punch_on"` (T5).

## 3. Power switch (T5 pattern, KI wiring)

| role | classname | targetname | ents |
|---|---|---|---|
| trigger | `trigger_use` | `use_elec_switch` | 1451 (`-488 1246 34`) |
| lever | `script_model` | `elec_switch` (`zombie_power_lever_handle`) | 1457 |
| sparks | `script_struct` | `elec_switch_fx` | 1464 |

On use, Kino's `electric_switch` (zt:347) deletes the trigger and sets flag `power_on`. Then `wait_for_power` (zt:368):
- rolls the lever −90 over 0.3 s, then fx `switch_sparks`
- runs `teleporter_init` (§5)
- notifies one per network frame: `revive_on`, `juggernog_on`, `sleight_on`, `doubletap_on`, `Pack_A_Punch_on`
- sets `level.quads_per_round = 4 × players` and starts `quad_wave_init` (§12)

`power_on` also lights the chandeliers and the box lights, and opens the theater zone's adjacency (§9).

Fields: `uses.powerSwitch = {"use_elec_switch"}` already holds [M→V]. Suggested: `power.flag = "power_on"` (T5), and a
per-map list of the notifies (KI: the order above).

## 4. Electric doors (T5)

- 2 `zombie_door` triggers, `script_noteworthy` = `electric_door`, `zombie_cost` 750 (ignored), `target` =
  `theater_to_foyer_door` (5 brush models) [V ents:370, 449].
- `blockers:145` hints "needs power"; `blockers:717` `flag_wait("power_on")` and opens it free.
- `electric_buyable_door` is supported but unused on Kino [M].

Field: `uses.electricDoor = "electric_door"` (exists, T5).

## 5. Teleporter and projector link (KI)

| role | classname | targetname | keys | ents |
|---|---|---|---|---|
| pad trigger (stage) | `trigger_use` | `trigger_teleport_pad_0` | `target` = `pf16_auto1` | 545 (`-304 1114 75`) |
| link trigger (projector room) | `trigger_use` | `pf16_auto1` | - | 720 (`2 -1266 181`) |
| link cable | `script_brushmodel` | `teleporter_link_cable_off` / `_on` | - | 726, 732 |
| pad light | `script_model` | `teleporter_indicator_lights` | `script_noteworthy` = `teleporter_indicator_light1` | 648 |
| projector-room spots | `script_origin` | `projroom_teleport_player0..3` | - | 521-539 |
| bonus-room spots | `script_origin` | `ee_teleport_player0..3` | `script_noteworthy` = room (e.g. `ar`) | 574-696 |
| return spots | `script_origin` | `theater_teleport_player0..3` | `script_noteworthy` = `theater` | 738-759 |
| holding spots | `script_origin` | `teleport_room_0..3` | - | 552-678 |
| zombie lures | `script_origin` | `teleporter_poi1`, `_poi2` | - | 564, 569 |
| pad fx / sounds | `script_struct` | `telepad` (6), `telepad_looper_0/1` | `script_sound` | 12680-12727 |
| bonus-room vision | `trigger_multiple` | `trigger_eeroom_visionset` | - | 966 (4) |
| powerups after a trip | `script_struct` | `struct_random_powerup_post_teleport` | - | 946 (4) |

Flow [V tp]:
1. **Init:** `teleporter_init` (tp:8) runs on power. `teleport_delay` 1.8 s, cost 0. Flags `core_linked` and
   `teleporter_linked`. The POIs pull zombies while a trip is on.
2. **Link:** use the pad trigger (`ZOMBIE_THEATER_LINK_CORE`) → `core_linked` (tp:146-170). The pad's `target` (the
   projector-room trigger) then says `ZOMBIE_THEATER_LINK_PAD`. Using it sets `teleporter_linked`, hides the off cable
   and shows the on cable (tp:196-225).
3. **Use:** with `teleporter_linked` set, the pad trigger teleports the players standing on it (tp:77-130):
   - the light goes red, and players go to `projroom_teleport_player*`
   - after 30 s (tp:278), a roll: if `randomint(100) > 24` (75 %) and the bonus rooms are free, they go to
     `ee_teleport_player*` for 4 s (tp:284-320); else straight back
   - then back to `theater_teleport_player*`
4. **Cooldown:** the cables reset, then `wait(90)` (tp:128). Then both flags clear and the light goes green, so it has
   to be relinked each time.
5. **After a trip:** a random aftereffect (fov, shellshock, vision; tp:783-830), and a powerup at a
   `struct_random_powerup_post_teleport` (tp:988).

Suggested per-map fields: `teleporter.padTargetname`, `linkKey = "target"`, `cableOff`, `cableOn`, `destinations`
(`projroom_teleport_player`, `ee_teleport_player`, `theater_teleport_player` + index), `roomTime = 30`,
`bonusChance = 75`, `bonusTime = 4`, `cooldown = 90`, `relink = true`, all KI [V].

## 6. Mystery box (T5, lights KI)

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| use trigger | `trigger_use` | `treasure_chest_use` | `script_noteworthy` = `<loc>_chest`, `target` = lid, `zombie_cost` 950; `start_exclude` 1 on `foyer_chest` | 9 | 7088 |
| lid | `script_model` | `<loc>_chest_lid` (`zombie_treasure_box_lid`) | `target` = `<loc>_chest_org` | 9 | 7105-7424 |
| box | `script_model` | `<loc>_chest_box` (`zombie_treasure_box`) | - | 9 | - |
| weapon origin | `script_origin` | `<loc>_chest_org` | `target` = box | 9 | - |
| rubble | `script_model` | `theater_chest_rubble` (`zombie_coast_bearpile`) | `script_noteworthy` | 1 | 7313 |
| location lights | `script_struct` | `magic_box_loc_light` | `script_noteworthy` = `<loc>_chest_loc`, `model` = `zombie_zapper_cagelight` | 81 (9 each) | 13769 |

- The locations, in Kino's order (`magic_box_init`, `zombie_theater_magic_box.gsc:11`): start, foyer, crematorium,
  alleyway, control, stage, dressing, dining, theater.
- `level.random_pandora_box_start = true` (zt:50) picks a random start chest, skipping `start_exclude` ones
  (weapons:856-858).
- The lights show where the box is once the power is on, flash while it moves and on Fire Sale (`_BOX_INDICATOR_*`).

Fields: `uses.boxTargetname = "treasure_chest_use"` and `boxCost = 950` exist (T5). Suggested:
- `box.randomStart` (T5 flag, KI value true)
- `box.startExcludeKey = "start_exclude"` (T5)
- `box.lightTargetname = "magic_box_loc_light"` (KI)

## 7. Traps (T5)

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| trap | `trigger_multiple` | `zombie_trap` | `script_noteworthy` = type (`electric` ×4, `fire` ×1); `script_string` = id (`e1`-`e4`, `f1`); `target` = group; `script_parameters` `ft1` on the fire one | 5 | 1016 |
| buy triggers | `trigger_use` | `<room>_room_trap` | - | 2 per trap | 1010-1370 |
| handles / lights | `script_model` | `<room>_room_trap` | `zombie_zapper_handle` = switch, `zombie_zapper_cagelight` = light | 4 per trap | 1026-1376 |
| fx points | `script_struct` | `<room>_room_trap` | `script_sound` `fire_med`; `script_string` `use_this_angle` marks the facing struct | 3-8 per trap | 1060-1356 |

Rooms: dressing, vip, control, crematorium, foyer.

From `trap_init` (traps:20-270):
- The parts are told apart by classname and model, not keys: `trigger_use` = buy trigger; `script_model` whose model is
  the switch / light model = switch / light; the structs are fx points.
- `zombie_cost` falls back to 1000 when it's missing, and Kino's traps carry none.
- With no `script_flag_wait`, the trap waits for `power_on`.
- Electric: 40 s on, 60 s cooldown (traps:498-501). Fire: 40 s on (traps:547-548).
- The type sets the switch/light models: `zombie_zapper_handle` / `zombie_zapper_cagelight` here (traps:1203-1214).

Suggested fields (T5): `traps.targetname = "zombie_trap"`, `typeKey = "script_noteworthy"`, `idKey = "script_string"`,
`defaultCost = 1000`, `flag = "power_on"`, and per type `{duration, cooldown}`: electric 40/60, fire 40/60 [I: fire's
cooldown comes from the same 60].

## 8. Doors (T5)

There are 12 `zombie_door` triggers [V ents:207-476]. Each has `zombie_cost` (750 ×4, 1000 ×3, 1250 ×5), `target` = the
door group, and `script_flag` = the zone flag it sets (10). The flags: `magic_box_west_balcony1/2`, `magic_box_foyer1`,
`magic_box_crematorium1`, `magic_box_alleyway1`, `magic_box_dressing1`, `vip_to_dining`, `dining_to_dressing`. The 2 without
a flag are the electric ones (§4). Door groups: `backstage_door`, `vip_top_door`, `foyer_top_door`, `foyer_bottom_door`,
`dress_door`, `dining_room_door`, `alleyway_fencedoor`, `alley_door2`, `theater_to_foyer_door`.

Field: `blockers = {{"zombie_door","zombie_debris"}, "script_flag", "zombie_cost", …}` already holds (T5).

## 9. Zones (T5 rule, KI adjacency)

There are 24 `info_volume`s in 10 zones [M ents:1480-1648]: `foyer_zone`, `foyer2_zone`, `vip_zone`, `dining_zone`,
`dressing_zone`, `stage_zone`, `theater_zone`, `west_balcony_zone`, `alleyway_zone`, `crematorium_zone`. Each has
`script_noteworthy` = `player_volume` and `target` = the zone's spawner targetname.

The start zones are `foyer_zone` and `foyer2_zone` (zt:97). Adjacency (`theater_zone_init`, zt:430):

| from | to | flag |
|---|---|---|
| foyer | foyer2 | always_on |
| foyer | vip | magic_box_foyer1 |
| foyer2 / foyer | crematorium | magic_box_crematorium1 |
| vip | dining | vip_to_dining |
| crematorium | alleyway | magic_box_alleyway1 |
| dining | dressing | dining_to_dressing |
| dressing | stage | magic_box_dressing1 |
| stage | west_balcony | magic_box_west_balcony2 |
| west_balcony | alleyway | magic_box_west_balcony1 |
| theater | foyer2, stage | power_on |

Fields: `zones = {"info_volume", "_barriers"}` exists (T5). The adjacency table is per map: add a KI `zones.links` list.

## 10. Spawners and risers (T5)

- Regular: `actor_zombie_ger_zombie` ×28, `script_noteworthy` = `zombie_spawner`, `count`, `script_forcespawn`,
  `export`. targetname = the zone's group (`zombie_spawner_<zone>`, `foyer_zone_spawners`, `foyer2_zone_spawners`).
  2 of the 4 in `zombie_spawner_theater` have `script_string` = `riser` [M ents:10359].
- Quad: `actor_zombie_quad` ×21, see §12.
- Rise structs: `zombie_spawner_theater_rise` ×7, `script_noteworthy` = `find_flesh` [M ents:7432]. Only the theater zone
  has any.
  - The zone manager reads `<volume target>_rise` (zonemgr:231).
  - A riser picks from its zone's rise locations, else the global `zombie_rise` structs (spawner:4442-4462).
  - A `find_flesh` struct makes it chase instead of going for a window (spawner:398-401, 422-431).

Fields: `zombieSpawners` (`actor_`, `zombie_spawner`, dog class `actor_zombie_dog`) and `risers = {"script_string",
"riser", 100, "zombie_rise", "_rise", …, "find_flesh", "zombie_chaser"}` already match Kino [V]. Both T5.

## 11. Dogs (T5)

| role | classname | targetname | keys | ents |
|---|---|---|---|---|
| spawner | `actor_zombie_dog` | `zombie_spawner_dog_init` | `script_noteworthy` = `zombie_dog_spawner`, `model` `zombie_wolf` | 10347 |
| spawn points | `script_struct` | `<volume target>_dog` (9 groups, 84 total) | `script_noteworthy` = `find_flesh` | 9759-9948 |
| dog clips | `script_brushmodel` | `dog_clips` | - (×3) | 10326 |

- `level.dogs_enabled = true` (zt:49), `enable_dog_rounds` (zt:88). Spawning uses `dog_spawn_factory_logic` (zt:61).
- The zone manager reads `<volume target>_dog` (zonemgr:224).
- The first dog round is `randomintrange(5, 8)`, so 5-7; then `+ randomintrange(4, 6)`, so +4-5 (dogs:446, ~470).
- [I] The dog clips block dogs from map areas; their script wasn't read.

Suggested fields (T5): `dogs.spawnerNoteworthy = "zombie_dog_spawner"`, `dogs.zoneSuffix = "_dog"`, `dogs.firstRound =
{5, 7}`, `dogs.gap = {4, 5}`, `dogs.clipTargetname = "dog_clips"` [I].

## 12. Special rounds: quads (KI)

- `actor_zombie_quad` ×21: `script_noteworthy` = `quad_zombie_spawner`, `script_string` = `zombie_chaser`,
  `script_int` 150 [M].
- Groups: `zombie_spawner_theater` (5), `foyer_zone_spawners` (4), `initial_theater_round_quad_spawner` (3),
  `initial_first_round_quad_spawner` (2), `_second_wave` (2), `theater_round_quad_spawner_second_wave` (2),
  `zombie_spawner_dining` (2), `zombie_spawner_stage` (1).
- **Gating** (`theater_ignore_spawner`, zt:465):
  - no quads until the curtains open (`curtains_done`)
  - during a special quad round, only quads
  - foyer quads need `lobby_occupied`, dining quads `dining_occupied`
- **Waves** (`quad_wave_init` / `time_for_quad_wave`, zt:510-590): after the power, foyer, theater, stage and dining
  each run their own wave check.
  - Every round where `round % 3 == 0` (chance 100, never on a dog round), if that zone is occupied, `special_quad_round`
    is set and the zone's spawners are reinit.
  - It holds until `zombie_total` drops below half the round's max, then clears.
  - `quads_per_round` = 4 × players.
- The intro rounds (`begin_quad_introduction`, quad:149) aren't called; the call is commented out at zt:409.
- `level.quad_move_speed = 35`, `quad_explode = true` (zt:54-56). The roof-crumble fx origins
  (`quad_roof_crumble_fx_origin_0..15`) are where quads drop in through the roof.

Suggested per-map fields: `quadRounds.every = 3`, `zones = {foyer, theater, stage, dining}`, `holdUntil = 0.5`,
`gateFlags`.

## 13. Windows (T5)

There are 22 `script_struct exterior_goal`s, each `target` = a 7-piece `script_brushmodel` group (`pf37_auto1`…
`pf67_auto1`) [M ents:7557]. That fits T5's board-and-clip pattern (6 boards + clip) [I: the pieces weren't split by
key here].

Field: `windows = {"exterior_goal", "script_brushmodel", "clip"}` exists (T5).

## 14. Wall buys, Bowie, Claymore (T5)

- 10 `trigger_use weapon_upgrade`, with `zombie_weapon_upgrade` = the weapon (`ithaca_zm`, `mp5k_zm`, `m14_zm`, `mp40_zm`,
  `m16_zm`, `frag_grenade_zm`, `rottweil72_zm`, `pm63_zm`, …) and `target` = the chalk model [V ents:17].
- 1 `claymore_purchase` (`claymore_zm`, ents:77).
- 1 `bowie_upgrade` (`script_noteworthy` = `knife_bowie`, ents:108).
- No cost key: the prices come from `mp/zombiemode.csv` (the existing `uses.price*`).

## 15. Extras (KI)

- **Movie screen and reels:**
  - `movie_screen`, `struct_theater_screen`, `struct_theater_projector_beam`, `theater_extracam(_screen)`.
  - Reel triggers `trigger_movie_reel_clean_bedroom` / `_bear_bedroom` / `_interrogation` / `_pentagon` (3 each, one
    picked at random per set; `zombie_theater_movie_screen.gsc:214-237`).
  - `trigger_change_projector_reels`.
- **Curtains:** `theater_curtains` + `_clip`. The `curtains_done` flag gates the quads.
- **Chandeliers:** `theater_chandelier` ×7, swapped to `_on` at power (zt:595).
- **Clock:** `zom_clock_*_hand`, driven by the teleporter.
- **Easter eggs:** `meteor_egg_trigger`, `portrait_egg`, `location_egg`, `audio_egg_radio`, `trigger_fly_me_to_the_moon`,
  `trigger_jump`.
- **Ambience:** `amb_*` structs, `ambient_package`.
- **Other:** `intercom` origins, ropes, 2 `misc_turret`s.
- **Respawns:** `player_respawn_point(_<zone>)` ×45. `initial_spawn_points` ×4 with `script_int` 1-4. `intermission` ×3.

## Not read

- The dog clip script.
- The fire trap's own cooldown.
- What `script_int` 150 does on the quad spawners.
- The `ee_teleport_player` rooms' names past `ar`.
- The movie-reel easter egg's outcome.
- The `ffotd` patch fixes in detail.
