# T4 zombies: what Verrückt, Shi No Numa and Der Riese add to Nacht

What each later WaW map adds on top of the shared `_zombiemode`, so each mechanic is built once and reads its map's ents.
Nacht is the baseline (`zombies_t4_nacht*.md`, `nacht_weapons_economy.md`).

Tags:
- **[V]**: read in the dumped zone scripts, ents or weapon files, as `map path:line`. The map roots are the Unlinker dumps
  of `nazi_zombie_asylum` (Verrückt), `nazi_zombie_sumpf` (Shi No Numa) and `nazi_zombie_factory` (Der Riese).
- **[I]**: inferred.
- Nothing here is measured in game.

Parts:
1. Perk machines and power
2. Traps, flogger, zipline, zones and teleporters
3. Hellhounds, Pack-a-Punch, the Wunderwaffe and the box

[I] For one Reforged ruleset: where the maps disagree (trap cooldowns, teddy odds, dog health), keep the number per map
in data and keep the mechanic shared.

## T4 Zombies: perk machines and power (Verrückt, Shi No Numa, Der Riese)

Tags: [V] = read in the file (path:line, relative to that map's dump). [I] = inferred. Map keys: **AS** = zm_asylum (nazi_zombie_asylum), **SU** = zm_sumpf (nazi_zombie_sumpf), **FA** = zm_factory (nazi_zombie_factory), **NA** = nacht_dump.

The three maps each ship their own copy of `maps/_zombiemode_perks.gsc`. The copies differ (md5 differs, AS 848 lines, SU 1222, FA 1344) [V]. SU and FA branch on `level.script`, so one shared implementation can serve all three if it reads the ents and takes a per-map profile (see section 5) [I].

---

### 1. The perks

#### 1.1 Costs (identical on all three maps)

| Perk | specialty | Cost | Source |
|---|---|---|---|
| Juggernog | `specialty_armorvest` | 2500 | AS perks.gsc:241-242; SU :400-401; FA :559-560 [V] |
| Quick Revive | `specialty_quickrevive` | 1500 | AS :245-246; SU :404-405; FA :563-564 [V] |
| Speed Cola | `specialty_fastreload` | 3000 | AS :249-250; SU :408-409; FA :567-568 [V] |
| Double Tap | `specialty_rof` | 2000 | AS :253-254; SU :412-413; FA :571-572 [V] |
| Pack-a-Punch (FA only) | `specialty_weapupgrade` (ents) | 5000 | FA perks.gsc:153; ents line 14856 [V] |

- `zombie_perk_cost` is set to 2000 as a fallback, but the per-perk switch overrides it for all four perks (AS :41, SU :51, FA :68) [V].
- The same perk at the same price everywhere. There is no co-op or solo price difference [V: no player-count check in the buy loop].

#### 1.2 Juggernog
- On purchase: `maxhealth` and `health` are set to **160**. Base is 100 (perk_think resets `maxhealth` to 100) [V AS perks.gsc:346-349, :461; SU :509-512, :656].
- FA reads it from the zombie var `zombie_perk_juggernaut_health` = 160 instead (FA perks.gsc:69, :684-685) [V].
- **AS and SU only:** a level thread `check_for_jugg_perk` adds **+40 health every 0.5 s**, capped at 160, to any player with the perk who is not burning [V AS _zombiemode.gsc:93, :2919-2940; SU _zombiemode.gsc:100, :3137-3180].
  - SU: during a dog round the tick is **+3** instead of +40, and it skips players with magic bullet shield [V SU _zombiemode.gsc:3151-3162].
  - FA has no `check_for_jugg_perk` (grep finds none), so FA relies on normal engine health regen [V grep; regen behaviour I].
- Jugg vs electric traps: a player without Jugg (or with health ≤ 100) takes lethal radius damage. A Jugg player above 100 health takes **50** damage instead [V AS nazi_zombie_asylum.gsc:1267-1277; same check SU nazi_zombie_sumpf_trap_perk_electric.gsc:359, FA nazi_zombie_factory.gsc:1176].
- SU `zombie_damage_failsafe` (anti-exploit kill when a zombie stands touching you for 5 s) skips Jugg players [V SU _zombiemode_spawner.gsc:142-168].
- The engine has no zombie-specific Jugg dvar. The effect is pure script health [I: `perk_armorVest` dvar not found by dvarreg.py].

#### 1.3 Speed Cola (`specialty_fastreload`)
- Engine dvar **`perk_weapReloadMultiplier`**, default **0.5**, range 0..1, flags 0x80, description "Percentage of weapon reload time to use" [V t4sp.dis 0x4127d4-0x412801; string 0x846004/0x845fdc].
  - The dvar pointer is stored at 0x8f64c8 [V t4sp.dis 0x41282b]. It is read when the weapon state is one of the reload states (7-11) and perk bit 3 is set [V t4sp.dis 0x41ff9e-0x41ffc8, 0x4640f8-0x464127].
  - Perk bit 3 = `specialty_fastreload` in the engine perk-name table at 0x8e01dc (index 0 gpsjammer, 1 reconnaissance, 2 bulletaccuracy, 3 fastreload, 4 rof, ... 14 armorvest) [V binary table].
  - Net effect: the reload takes 50% of the normal time [I from the description; the exact arithmetic was not traced].
- Script bonus: faster barrier rebuild.
  - AS and SU: a global `level.sleightperk` flag is set from the player at the barrier. With it, a chunk moves in 0.05 s instead of 0.1 + rand(0.2) s, and the 0.2 s post-rotate wait is skipped [V AS _zombiemode_blockers.gsc:627-633, :861-893; SU _zombiemode_blockers.gsc:626-632, :866-891].
  - FA: per-call `has_perk`. Rotate takes 0.15 s plus a 0.1 s wait, and the move takes 0.05 s. Without the perk the times are 0.15/0.3 s plus a 0.2 s wait and a 0.1 s move [V FA _zombiemode_blockers_new.gsc:687-693, :928-982].
  - The AS/SU flag is level-wide, so two players repairing at once can leak the bonus [I].

#### 1.4 Double Tap (`specialty_rof`)
- Engine dvar **`perk_weapRateMultiplier`**, default **0.75**, range 0..1, flags 0x80, description "Percentage of weapon firing rate to use" [V t4sp.dis 0x412806-0x412833; string 0x846048/0x846020].
  - Pointer at 0x8f64d0 [V t4sp.dis 0x412861]. It is read when perk bit 4 (= `specialty_rof`) is set and the weapon state is a fire state (5/6) [V t4sp.dis 0x420022-0x420057, 0x464145].
  - The fire time is divided by the dvar there (the time held at weapon+0x28 is divided by the value) [V t4sp.dis 0x42006e-0x420074]. The exact meaning of that time field is [I].
  - Net effect: the shot interval becomes 75%, about 1.33× the rate of fire [I].
- WaW Double Tap does not add bullet damage. No script damage hook was found [V: no `specialty_rof` reference outside the perks file].
- Neighbouring dvar for reference: `perk_weapSpreadMultiplier` (pointer 0x8f64ac) goes with bit 2 = `specialty_bulletaccuracy` and is not used by zombies [V t4sp.dis 0x4127f9, 0x41dbfa-0x41dc20].

#### 1.5 Quick Revive
- Revive time is **3 s**. With the perk the reviver's time is halved to **1.5 s** [V AS _laststand.gsc:588-592; SU :620-624; FA :633-637].
- It speeds up **reviving others** only. There is **no solo self-revive** in WaW [V]:
  - `player_damage_override` counts players who are down or spectating. When everyone is down it calls `end_game` [V AS _zombiemode.gsc:2180-2205].
  - With one player, going down ends the game whether or not they have Quick Revive [I from that logic].
- The perk triggers hide from players inside a revive trigger, and you cannot buy while in one [V AS perks.gsc:264, :394].

#### 1.6 Losing perks
- On purchase, each perk starts its own `perk_think` thread. It waits for `fake_death`, `death` or `player_downed`, then calls `UnsetPerk`, sets `maxhealth` to 100 and destroys that perk's HUD icon [V AS perks.gsc:446-464; SU :641-660; FA :809-828].
- So **every perk is lost on going down** (or on death). Being revived does not restore any perk [I].
- HUD icon: a 24×24 shader at bottom-left, x = 30 × (number of icons), y offset -70. The shaders are `specialty_juggernaut_zombies`, `_quickrevive_`, `_fastreload_` and `_doubletap_zombies` [V AS perks.gsc:467-524].

---

### 2. Buying a perk

#### 2.1 Ents (all three maps; one parser can read them)
| Role | classname | targetname | Key fields |
|---|---|---|---|
| Buy trigger | `trigger_use` | `zombie_vending` | `script_noteworthy` = specialty name; `target` = machine targetname |
| Machine | `script_model` | `vending_jugg` / `vending_revive` / `vending_sleight` / `vending_doubletap` | `model` = off model (AS/FA) |
| Jingle point | `script_struct` | `perksacola` | `script_sound` = `mx_jugger_jingle` / `mx_revive_jingle` / `mx_speed_jingle` / `mx_doubletap_jingle` (FA also `mx_packa_jingle`) |
| Rattle bump | `trigger_multiple` | `audio_bump_trigger` | `script_sound` = `perks_rattle`, `script_activated` 1 |
| PaP trigger (FA) | `trigger_use` | `zombie_vending_upgrade` | `script_noteworthy` `specialty_weapupgrade`, target `vending_pack_a_punch` |

Ents evidence [V]:
- AS: nazi_zombie_asylum.d3dbsp.ents:12321-12360 (Jugg, Revive), :14374-14411 (Speed, Double Tap).
- SU: nazi_zombie_sumpf.d3dbsp.ents:2949-3069. SU has **no `perksacola` structs**. Instead `script_sound` sits on both the trigger and the machine. SU machines start with the lit `_price` models. There are 4 `script_origin`s with `script_noteworthy` `random_vending_start_location_0..3`.
- FA: nazi_zombie_factory.d3dbsp.ents:7693-7789, :9204-9229, :14856-14880. FA adds `script_string` tags (`jugg_perk`, `revive_perk`, `speedcola_perk`, `tap_perk`) [V]; no script reader for them was found [I].
- **Verrückt has all 4 perk machines** [V AS ents above]. The script also expects all four (AS perks.gsc:47-50).
- NA has no perks. NA's `_zombiemode.gsc` never calls perks init (NA _zombiemode.gsc:38-42) and its ents have no `zombie_vending` or `master_switch` [V].
- Init entry: AS calls perks init from nazi_zombie_asylum.gsc:54. SU and FA call it from _zombiemode.gsc:48 and :65. Init returns early if no `zombie_vending` triggers exist [V AS perks.gsc:7-12].

#### 2.2 Purchase flow (vending_trigger_think)
1. Before power, the hint is `ZOMBIE_FLAMES_UNAVAILABLE` and the trigger needs look-at [V AS perks.gsc:224-226]. SU skips the hint because power is "already on" [V SU :366-372].
2. The trigger waits for the level notify `<specialty>_power_on` [V AS :228-229].
   - Once that arrives, `check_player_has_perk` runs every 0.1 s. It hides the trigger from players within 128 units who already own the perk or are in a revive trigger [V AS :377-414].
   - The hint is then per-perk (`ZOMBIE_PERK_JUGGERNAUT` etc.). SU uses a single `ZOMBIE_PERK_GENERIC` [V AS :417-443; SU :380-391].
   - FA starts the `perks_machine_loop` hum on the trigger at this point [V FA :544-545].
3. The buy is rejected when:
   - the player is in last stand or in a revive trigger;
   - FA only: the player is throwing a grenade or switching weapons [V FA :587-597];
   - the player already has the perk: plays `deny` [V AS :269-285];
   - the player has too little score: plays `deny` [V AS :288-292].
   SU and FA also play `play_no_money_perk_dialog` (`vox_nomoney_perk_N`) on both deny cases [V SU :443, :454].
4. On a valid buy:
   - `bottle_dispense3d` plays at the trigger;
   - the sting for that perk plays once (`mx_jugger_sting`, `mx_revive_sting`, `mx_speed_sting`, `mx_doubletap_sting`). A per-perk `level.*_jingle` lock stops overlaps, and nothing plays if `level.eggs` ≠ 0 [V AS :295-321, :685-754].
5. Drink: the bottle weapon is given and switched to.
   - While drinking, the player loses offhands, weapon cycling, lean, ADS, sprint, prone and melee, and a prone player is forced to crouch [V AS :533-575].
   - The script waits for `weapon_change_complete`, down or death [V AS :327-329].
6. After the drink, if the player is not in last stand:
   - `SetPerk` is called, a blur of 4 is applied for 0.1 s, and the Jugg health is set;
   - **AS/SU charge the cost after the drink.** A player downed mid-drink pays nothing [V AS :335-367; SU :498-529];
   - **FA charges before the drink** (straight after the dispense sound), so a downed player loses the money [V FA :629-632];
   - SU/FA increment `stats["perks"]`. FA also writes a `bbPrint` [V FA :693-697].
7. Restore: the player switches back to the previous gun, or to the first primary when there was none. SU/FA also skip `mine_bouncing_betty` here. Then the bottle is taken [V AS :578-636; SU :816].

#### 2.3 Bottle weapons and anims (weapons/ raw files, identical on all 3 maps)
- Weapons: `zombie_perk_bottle_jugg`, `zombie_perk_bottle_revive`, `zombie_perk_bottle_sleight`, `zombie_perk_bottle_doubletap` [V AS perks.gsc:15-18, :552-569].
- weaponType/class `grenade`, inventoryType `item`, hands `viewmodel_hands_cloth` [V weapons/zombie_perk_bottle_*].
- Models: view model is `gunModel` = the weapon's own name; world model is `zombie_3rd_perk_bottle_<x>` [V].
- Anims [V]:
  - raise and firstRaise: `viewmodel_zombie_perksacola_drink`;
  - drop: `viewmodel_zombie_perksacola_lower`;
  - idle: `viewmodel_zombie_perksacola_idle`.
- Timings: raiseTime 2.1, **firstRaiseTime 2.8**, dropTime 0.9, quickRaise 2.1, quickDrop 0.26 [V].
  - The drink is therefore about 2.8 s, the first raise of a freshly given weapon [I].
- Notetrack sounds: `bottle_open`, `swallow`, `bottle_break`, `belch` [V].
- FA PaP uses `zombie_knuckle_crack` [V FA weapons/zombie_knuckle_crack; perks.gsc:27, :301-339]:
  - raise anim `viewmodel_zombie_packopunch`, gun model `viewmodel_usa_no_model`;
  - notetracks `knuckle_start`, `knuckle_left`, `knuckle_right`.

#### 2.4 Sounds and vox
- After drinking:
  - AS: `plr_<n>_vox_drink_jugga`, `_speed`, `_revive` or `_double`, played straight away and guarded by `level.player_is_speaking` [V AS perks.gsc:638-679].
  - SU/FA: after 1.0 s, `do_player_playdialog` with `vox_perk_jugga_0`, `vox_perk_speed_0`, `vox_perk_revive_0` or `vox_perk_doubletap_0` [V SU :833-869; FA :1003-1039]. The full alias is `plr_<n>_` plus that name [I from the helper signature, FA _zombiemode_spawner.gsc:2549].
- Pre-power nag (`electric_perks_dialog`): a player within 70 units for about 3 checks gets `vox_start`, once per machine. It ends on `switch_flipped` [V AS perks.gsc:185-218].
- Idle jingles (`perks_a_cola_jingle`):
  - A looped `perks_machine_loop` hum plays (AS/SU from the jingle thread; FA from the trigger, see 2.2).
  - Every random 60-120 s (AS) or 31-45 s (SU/FA), with a 15% chance and `level.eggs` = 0, it notifies `jingle_playing` and plays `electrical_surge` and then the point's `script_sound` jingle [V AS perks.gsc:755-818; SU :1127-1190; FA :1186-1260].
- Broken sounds between jingles: every 7-18 s an `electrical_surge` plays, and the Revive machine also plays `broken_random_jingle` [V AS :819-846].
  - The `electric_short_oneshot` FX plays on AS only; SU and FA have that FX commented out [V SU :1207, :1217].
- Who starts the jingles:
  - AS: `master_switch_activated` threads the jingle on all `perksacola` structs [V AS :680-684].
  - FA: one watcher per notify (`juggernog_on`, `sleight_on`, `doubletap_on`, `revive_on`, `Pack_A_Punch_on`) matches structs by `script_sound` [V FA :1041-1100].
  - SU: one watcher per `*_sumpf_on` notify starts the jingle on the `zombie_vending` **trigger** whose `script_sound` matches [V SU :889-953].

#### 2.5 Machine lighting
- **Off → on model swap** [V AS perks.gsc:58-169; FA :418-489]:
  - `zombie_vending_jugg` → `zombie_vending_jugg_on`;
  - `zombie_vending_revive` → `zombie_vending_revive_on`;
  - `zombie_vending_sleight` → `zombie_vending_sleight_on`;
  - `zombie_vending_doubletap` → `zombie_vending_doubletap_on`;
  - FA: `zombie_vending_packapunch` → `zombie_vending_packapunch_on`.
- SU on-models: `zombie_vending_jugg_on_price`, `zombie_vending_revive_on_price`, `zombie_vending_sleight_on_price`, `zombie_vending_doubletap_price` (note: no `_on`). SU has no off state [V SU perks.gsc:28-31, :197-312].
- Power-on effect on each machine: `vibrate((0,-100,0), 0.3, 0.4, 3)` and the `perks_power_on` sound [V AS :62-64].
- Light FX:
  - `sleight_light` = `misc/fx_zombie_cola_on`;
  - `doubletap_light` = `misc/fx_zombie_cola_dtap_on`;
  - `jugger_light` = `misc/fx_zombie_cola_jugg_on`;
  - `revive_light` = `misc/fx_zombie_cola_revive_on`;
  - all played on `tag_origin` [V AS :31-34].
- AS/SU flicker: a temporary FX object with `elec_current_loop` and `perks_rattle` sounds. The flicker step starts at 0.05 s and grows by 0.1 s per step until about 3 s have passed, then the light FX plays for good [V AS :65-82, :172-184].
  - The `specialty_*_power_on` notify fires **before** the flicker, so the machine is buyable during it [V AS :68].
- FA: no flicker. `perk_fx` waits 3 s and then plays the FX. FA handles multiple machines per targetname through `getentarray` [V FA :418-489].
- Client side:
  - AS `perk_wire_fx` runs a spark along struct chains (`revive_electric_wire`, `electric_fast_reload`, `electric_double_tap`, `electric_juggernog`, `electric_middle_door`). The trigger is the client notifies `revive_on`, `fast_reload_on`, `doubletap_on`, `jugger_on` and `middle_door_open` [V AS clientscripts/nazi_zombie_asylum_fx.csc:33-37, :237-249].
  - SU client amb waits for `jugg_on`, `fast_reload_on`, `revive_on` and `doubletap_on` [V SU clientscripts/nazi_zombie_sumpf_amb.csc:304-352].

#### 2.6 Shi No Numa: random perk machines
- Triggered by the magic-box/hut logic [V SU nazi_zombie_sumpf_magic_box.gsc:35-180; nazi_zombie_sumpf.gsc:22]:
  - When the first route flag (e.g. `nw_magic_box`) is set and `level.randomize_perks` is false, it calls `randomize_vending_machines`, fills `level.vending_model_info` with the 4 `_price` models, and sets `randomize_perks` to true [V magic_box.gsc:129-154].
- `randomize_vending_machines` [V SU nazi_zombie_sumpf_perks.gsc:6-43]:
  - shuffles the 4 `random_vending_start_location_*` origins;
  - links each trigger to a location;
  - moves each machine there, hides the machine and turns the trigger on.
- Each hut machine appears when its flag is set: `northwest_building_unlocked` (index 0), `northeast_` (1), `southeast_` (2) or `southwest_` (3). The same step also adds that hut's dog spawners [V magic_box.gsc:157-180].
- `vending_randomization_effect(index)` [V sumpf_perks.gsc:278-462]:
  - Sounds `rando_start` and `rando_perk`, plus a 2D `perk_lottery`.
  - FX `zombie_perk_start` (`misc/fx_zombie_perk_lottery_start`), or `zombie_perk_4th` (`..._lottery_4`) for the last machine [V nazi_zombie_sumpf_fx.gsc:79-82].
  - The machine rises 40 units over 5 s and vibrates. 30 cycles of 0.15 s (4.5 s) step through the remaining models, with `zombie_perk_flash` on each.
  - It settles on the true model, drops in 0.3 s, then plays `zombie_perk_end` and `perks_rattle`.
  - It calls `activate_vending_machine`, and removes that model from the pool.
  - The 4th machine skips the model cycle because the pool size is 1 by then [I: GSC array size shrinks when entries are set undefined].
- `activate_vending_machine` [V sumpf_perks.gsc:60-90]:
  - notifies `master_switch_activated`;
  - then the per-perk level notify (`juggernog_sumpf_on`, `doubletap_sumpf_on`, `revive_sumpf_on`, `sleight_sumpf_on`) and the client notify (`jugg_on`, `doubletap_on`, `revive_on`, `fast_reload_on`);
  - then nearby sight-checked vox `vox_gen_perk_<jugga|dbltap|revive|speed>_N` after 2 s.
- **Solo bias:** with fewer than 2 players, `first_time_opening_perk_hut` is true [V magic_box.gsc:22-27]. The first hut opened swaps its machine with Jugg or Speed Cola [V sumpf_perks.gsc:296-347].
  - The guard condition is written as "not Jugg OR not Speed", which is always true, so the swap always runs [V :300].
  - Result: in solo, the first hut always gets Jugg or Speed Cola (whichever is found first that is not already the hut's own machine) [I].
  - Co-op is fully random [I].
- SU perks have no cost or power gate beyond the hut arriving. Costs are as in 1.1.

---

### 3. Power switches

#### 3.1 Verrückt (AS) - has a switch
- Ents: trigger `trigger_use` targetname `use_master_switch` [V ents:10384]. Lever `script_model` targetname `master_switch`, model `zombie_power_lever_handle` [V ents:12755]. A `script_struct` `switch_fx` is read by the script [V nazi_zombie_asylum.gsc:1652].
- Function `master_electric_switch` [V nazi_zombie_asylum.gsc:1551-1709]:
  - hint `ZOMBIE_ELECTRIC_SWITCH`; the lever is notsolid;
  - an idle FX `electric_power_gen_idle` plays at a hard-coded origin (-674.9, -300.5, 284.1).
- Before power, the `zombie_door` triggers with `script_noteworthy` `electric_door` (2 in the ents, `zombie_cost` 750) are made unusable and get the door-deny dialog [V :1561-1564; ents:8307, :12726].
- Order after use:
  1. Door triggers off.
  2. Lever `rotateroll(-90, 0.3)` and the `switch_flip` sound.
  3. Client notifies `revive_on`, `middle_door_open`, `fast_reload_on`, `doubletap_on`, `jugger_on`.
  4. Level notify `switch_flipped`.
  5. Spark ambients, `SetClientSysState("levelNotify","start_lights")` and the PA system.
  6. **flag `electric_switch_used`**; the trigger is deleted.
  7. The `gas_access` traps become available [V :1589-1649].
  8. On `rotatedone`: `switch_sparks` FX, then **`master_switch_activated`** (jingles), then the generator FX swap to `electric_power_gen_on` with `elec_current_loop`, and the green zapper lights [V :1651-1667].
  9. **After 6 s:** `sleight_on`, `revive_on`, `electric_on_middle_door`, `doubletap_on`, `juggernog_on` [V :1673-1678].
  10. The electric doors open by script (`open_bottom_doors`), then exploder 101 [V :1683-1686].
- Turns on:
  - all 4 perks;
  - both electric traps: `gas_access` triggers north and south, cost 1000, usable only after the switch [V :908-911, :1016-1020; ents:10123, :10133];
  - the downstairs "middle" electric doors (opened free);
  - the lights: `elect_light_model` models swap `lights_tinhatlamp_off` → `_on` and `lights_indlight` → `lights_indlight_on`, and the magic-box lights drop to 0.01 intensity on `electric_switch_used` [V :326-367].
- The devgui "power" cheat looks up `use_master_switch` by name and reports that the map has no switch if it is missing [V SU _zombiemode_devgui.gsc:131-142]. So FA's differently named `use_power_switch` would not be found by that cheat [I].

#### 3.2 Shi No Numa (SU) - **no power switch**
- No `use_master_switch` or `master_switch` in the ents [V ents scan]. The SU perks code says "power is already turned on" [V SU perks.gsc:366].
- `master_switch_activated` is still notified, once per machine arrival [V sumpf_perks.gsc:63].
- Traps need no power: the electric perk trap (cost 1000), the pendulum (750) and the zipline (1500) are gated by doors and flags only [V nazi_zombie_sumpf_trap_perk_electric.gsc:62; _trap_pendulum.gsc:94; _zipline.gsc:256].

#### 3.3 Der Riese (FA) - has a switch
- Ents: trigger `trigger_use` targetname `use_power_switch` [V ents:9863]. Lever `script_model` targetname `power_switch`, model `zombie_power_lever_handle` [V ents:9869]. Struct `power_switch_fx` [V ents:11793].
- Function `power_electric_switch` [V nazi_zombie_factory.gsc:735-820]:
  - hint `ZOMBIE_ELECTRIC_SWITCH`;
  - on use: `rotateroll(-90, 0.3)`, `switch_flip`, then **flag `electricity_on`** (initialised in FA _zombiemode.gsc:635).
- Then, with `wait_network_frame` between each step:
  - client `revive_on`, `fast_reload_on`, `doubletap_on`, `jugger_on`;
  - level `sleight_on`, `revive_on`, `doubletap_on`, `juggernog_on`, **`Pack_A_Punch_on`**;
  - then directly `specialty_armorvest_power_on`, `specialty_rof_power_on`, `specialty_quickrevive_power_on`, `specialty_fastreload_power_on` [V :778-805].
- Then client `pl1` (power lights), exploder 600, trigger deleted, `switch_sparks` FX at `power_switch_fx`, and the zones `outside_east_zone` and `outside_west_zone` connect to `outside_south_zone` [V :808-819].
- `electricity_on` gates:
  - all 4 perks and Pack-a-Punch (PaP model swap, and it notifies `Carpenter_On`) [V FA perks.gsc:383-415];
  - the bridges lower (`wnuen_bridge`, `warehouse_bridge`), then flag `bridge_down` [V nazi_zombie_factory.gsc:373-414];
  - the electric traps `warehouse_electric_trap`, `wuen_electric_trap`, `bridge_electric_trap` (cost 1000). Each also needs `enter_warehouse_building`, `enter_wnuen_building` or `bridge_down` [V :824-833, :878-887];
  - the teleporter pads and core: hint `ZOMBIE_FLAMES_UNAVAILABLE` until power, then `ZOMBIE_POWER_UP_TPAD` / `ZOMBIE_LINK_TPAD` [V nazi_zombie_factory_teleporter.gsc:170-175, :652-688];
  - the electric doors: `zombie_door` with `script_noteworthy` `electric_door` (2 in the ents, target `outside_south_east_door` / `outside_south_west_door`, `zombie_cost` 10000) open on the flag [V _zombiemode_blockers_new.gsc:134-137; ents:13748, :13986]. The 10000 cost is never charged [I];
  - the light models and client lights on `pl1` [V clientscripts/_lights.csc:295, :378; nazi_zombie_factory_fx.csc:353].
- The old two-switch design (`wuen_electric_switch`, `warehouse_electric_switch`) is commented out [V nazi_zombie_factory.gsc:80-81, :763-771]. One switch powers everything.

#### 3.4 Nacht (NA): no switch, no perks [V section 2.1].

---

### 4. Notify and flag names, at a glance
| Name | Kind | Maps | Meaning |
|---|---|---|---|
| `switch_flipped` | level notify | AS | switch used; ends the nag dialogs |
| `electric_switch_used` | flag | AS | lights and traps on |
| `master_switch_activated` | level notify | AS (switch), SU (each machine arrival) | starts jingles (AS) |
| `electricity_on` | flag | FA | master power gate |
| `sleight_on`, `revive_on`, `doubletap_on`, `juggernog_on` | level notify | AS, FA | machine model and light on |
| `*_sumpf_on` (`juggernog_`, `doubletap_`, `revive_`, `sleight_`) | level notify | SU | same, SU variant |
| `specialty_<perk>_power_on` | level notify | all | arms the buy trigger |
| `Pack_A_Punch_on` | level notify | FA | PaP on |
| `electric_on_middle_door` | level notify | AS | middle door |
| `revive_on`, `fast_reload_on`, `doubletap_on`, `jugger_on` (`jugg_on` on SU), `middle_door_open`, `pl1`, `start_lights` | client notify | as listed | client FX, lights and ambience |

### 5. Shared-implementation notes [I]
- Ents give everything except the power source: the trigger (`zombie_vending` plus `script_noteworthy`), the machine (via `target`), and the jingle point (`perksacola` struct, or `script_sound` on the trigger on SU).
- Per-map profile fields:
  - power mode: `switch_flag` (AS, FA) or `random_huts` (SU);
  - whether cost is charged before or after the drink;
  - Jugg regen thread on or off (and the dog-round +3);
  - jingle interval (60-120 or 31-45 s);
  - flicker vs a flat 3 s light;
  - SU `_price` model names and generic hint.
- Off/on model names follow the pattern `<off model>` + `_on`, except SU, which has fixed names.

## T4 Zombies: traps, zipline, zones, teleporters (Verrückt, Shi No Numa, Der Riese)

Research draft for the clean-room reimplementation. Read-only study of the dumped scripts.

Tags: **[V]** = read in the file (map, path:line relative to that map's dump root). **[I]** = inferred.
Map roots: `zm_asylum` (Verrückt), `zm_sumpf` (Shi No Numa), `zm_factory` (Der Riese), `nacht_dump` (Nacht baseline).
Ent indices like `ent#1977` are the 0-based entity order in that map's `maps/<map>.d3dbsp.ents`.

---

### 1. Electric traps ("zappers")

All three maps share one design: a buy trigger, a throw-switch model found by link name, a damage `trigger_multiple`, a set of FX structs that share the damage trigger's targetname, and cage-light models. The differences are only in the numbers and in how the trap is gated.

#### 1.1 Numbers side by side

| | Verrückt | Shi No Numa | Der Riese |
|---|---|---|---|
| Cost | 1000 [V] asylum maps/nazi_zombie_asylum.gsc:1020 | 1000 [V] sumpf maps/nazi_zombie_sumpf_trap_perk_electric.gsc:62 | 1000 [V] factory maps/nazi_zombie_factory.gsc:881 |
| Active time | 25 s (each FX point waits 25 s, then notifies done) [V] asylum nazi_zombie_asylum.gsc:1188 | 25 s [V] sumpf trap_perk_electric.gsc:274 | 25 s [V] factory nazi_zombie_factory.gsc:1093 |
| Cooldown after it ends | 25 s [V] asylum :1085 | 90 s [V] sumpf trap_perk_electric.gsc:131 | 25 s [V] factory :989 |
| Power needed | Yes: starts "unavailable", enabled by the master switch [V] asylum :1018-1021, :1644-1649 | No power on this map; usable from load, but the traps sit inside the perk huts so you must open a hut door to reach one [V] sumpf nazi_zombie_sumpf.gsc:273; [I] reachability | Yes, plus a per-trap gate flag (see 1.4) [V] factory :887, :920-928 |
| Number of traps | 2 (north, south), one trigger each | 4 (one per hut: NE, NW, SE, SW), one trigger each | 3 (warehouse, Wnuen, bridge), **two triggers each** sharing one damage trigger |
| Ready alarm | `warning` at the `loudspeaker` struct [V] asylum :1089-1090 | `warning` at the `speaker_by_log` script_origin [V] sumpf trap_perk_electric.gsc:137-138 | none (commented out) [V] factory :993-995 |

- Payment is taken only after the switch finishes its 0.5 s throw animation (the "switch_activated" notify), not on press [V] asylum :1053-1057; sumpf trap_perk_electric.gsc:91-95; factory :957-959.
- Re-use guard: Verrückt and Shi No Numa use a per-trigger in-use flag [V] asylum :1046-1048, sumpf :86-88. Der Riese puts the in-use flag on the shared damage trigger so either of the pair locks both [V] factory :891-892, :948-953.
- All triggers of that trap are hidden for active time plus cooldown [V] asylum :1061-1062 (by shared script_noteworthy), :1086; sumpf :99, :133 (just itself); factory :953, :991 (all triggers with the same targetname).
- If the buyer is in a revive trigger the press is ignored [V] asylum :1027-1030, sumpf :72-75, factory :942-945.

#### 1.2 Damage and kill rule (identical logic on all three)

- The damage trigger is switched on for the active time and fires per entity touch [V] asylum :1066-1067, :1210-1230; sumpf :103-104, :296-323; factory :962, :1120-1139.
- **Zombies:** each is marked once ("marked_for_death") and then dies; random roll 0-99 [V] asylum :1225-1228.
  - Roll above 90 and fewer than 6 zombies already burning: set on fire, wait up to 1.25 s, die [V] asylum :1293-1300.
  - Otherwise: random gib from {guts, right arm, left arm, right leg, left leg, no legs, head}; 50% chance of electrocution FX and vocals; wait up to 1.25 s; die [V] asylum :1301-1321.
  - Death is damage of health + 666 [V] asylum :1323.
- Map quirks:
  - Shi No Numa skips dogs that have magic-bullet-shield, and skips electrocution FX during dog rounds [V] sumpf trap_perk_electric.gsc:310-313, :409-412. It records `trapped_used[<damage trigger targetname>] = round` on the buyer (achievement bookkeeping) [V] sumpf :319.
  - Der Riese never plays electrocution FX on dogs [V] factory :1224, and has a leftover debug on-screen print after every trap kill [V] factory :1234.
- **Players** (not in last stand, not already being shocked) [V] asylum :1253-1284:
  - Electrified screen effect for 1.25 s and "electrocution" shellshock for 2.5 s [V] asylum :1256-1259.
  - Without Juggernog, or with health 100 or less: killed (a radius damage of health + 100 at their feet, so last stand on solo/co-op as usual) [V] asylum :1267-1272; [I] goes through normal down logic.
  - With Juggernog and health above 100: 50 damage, then can be shocked again after 0.1 s [V] asylum :1274-1279. Same in sumpf :359-372 and factory :1176-1190.
  - The zombie_arc sound plays on each shock; the "play only once" guard writes a local variable by mistake so it never latches [V] asylum :1261-1265; [I] effect.

#### 1.3 FX, sounds, models

- FX are client-side: the server sends a client notify equal to the damage trigger's targetname; the client spawns `level._effect["zapper"]` (misc/fx_zombie_electric_trap) at every struct with that targetname and removes it on the notify `<script_string>off` [V] asylum clientscripts/nazi_zombie_asylum_fx.csc:25-26, :84; sumpf clientscripts/nazi_zombie_sumpf_fx.csc:19-22, :94-145; factory clientscripts/nazi_zombie_factory_fx.csc:20-22, :241; server sides: asylum :1162, :1070; sumpf trap_perk_electric.gsc:242, :112.
- Sumpf quirk: the client listens for `<light name>off` and the server sends `<script_string>off`, where script_string is the light name (e.g. `north_east_elec_light`), so they match [V] sumpf fx.csc:19-22, :141 and ents#5092.
- Verrückt also sends `north` / `south` (powerbox and wall-switch FX: `zapper_fx` = misc/fx_zombie_zapper_powerbox_on, `zapper_wall` = misc/fx_zombie_zapper_wall_control_on) and swaps the `zap_machine_<side>` model to `zombie_zapper_power_box_on` [V] asylum :1140-1153; asylum_fx.csc:28-29, :181-221, :324-325. Der Riese sends `warehouse` / `wuen` / `bridge` the same way [V] factory :1049-1060.
- Sounds (server): `purchase` on buy; `amb_sparks_l_b` on switch throw; `elec_start` + loop `elec_loop` per FX point; random `elec_arc` every 0.1-0.5 s; zombie death `zombie_arc`, `elec_vocals`, `exp_jib_zombie`, `elec_jib_zombie`, `ignite`; `warning` when ready [V] asylum :1043, :1117, :1183-1206, :1232-1240; sumpf :89, :189, :270-292.
- Verrückt plays the per-point sounds only where the struct has `script_sound` (set to `fire_med` on some points; the value is ignored, any value enables it) [V] asylum :1180-1185 and ents#1968, #1973. Sumpf and Der Riese always play them [V] sumpf :268-273; factory :1088-1090.
- Zombie electrocution FX: `elec_md` on a random elbow/knee, `elec_sm` on two random wrists/ankles; burn loop `fire_manager_0` for 12 s [V] sumpf trap_perk_electric.gsc:430-509; asylum :2155-2222.
- Cage lights: models `zombie_zapper_cagelight_red` / `_green` plus FX `zapper_light_ready` / `zapper_light_notready` (Verrückt and Sumpf: misc/fx_zombie_zapper_light_green/red; Der Riese: maps/zombie/fx_zombie_light_glow_green/red) [V] asylum maps/nazi_zombie_asylum_fx.gsc:126-127; sumpf nazi_zombie_sumpf.gsc:298-338; factory nazi_zombie_factory.gsc:1247-1289, maps/nazi_zombie_factory_fx.gsc:62-63.
- Switch: the `script_linkname` model rotates pitch 180 over 0.5 s, then back after cooldown [V] asylum :1101-1136; sumpf :179-238; factory :1008-1045. Direction sign differs per switch (Verrückt north is -180) [V] asylum :1111.

#### 1.4 Gates

- Verrückt: hint is "unavailable" and presses do nothing until the master switch sets every trap's available flag [V] asylum :1018-1019, :1035-1038, :1644-1649. Lights turn green at the switch [V] asylum :1667-1668.
- Shi No Numa: available from start, lights green [V] sumpf trap_perk_electric.gsc:61, :64.
- Der Riese: waits for `electricity_on`, then for its gate flag; while gated the trigger is off and the light red [V] factory :887, :920-931.
  - `warehouse_electric_trap` gated by `enter_warehouse_building`; `wuen_electric_trap` by `enter_wnuen_building`; `bridge_electric_trap` by `bridge_down` [V] factory :831-833.

#### 1.5 Ents

| Map | Buy trigger (trigger_use) | Keys on the trigger | Switch model | Damage trigger | Lights |
|---|---|---|---|---|---|
| Verrückt | targetname `gas_access` ×2 [V] ents#1977-1978 | script_noteworthy `north_gas_valves`/`south_gas_valves`; script_string `north`/`south`; script_linkto `4`/`3`; target `auto246`/`auto242` | script_model with script_linkname `4`/`3` [V] ents#2631-2632 | trigger_multiple (spawnflags 1) with targetname = trigger's target [V] ents#1975-1976; FX structs share that name (6 each) | `zapper_light_north`/`_south` ×2 each, machine models `zap_machine_north`/`_south` [V] ents#45-50 |
| Shi No Numa | targetname `elec_trap_trig` ×4 [V] ents#5092, #5103, #5106, #5121 | script_string `<side>_elec_light`; script_linkto `112`/`113`/`110`/`111`; target `north_east_tgt` etc. | script_model, script_linkname 110-113 [V] ents#5091, #5102, #5105, #5122 | trigger_multiple + 5 structs per side named `<side>_tgt` [V] ents#5085-5120 | models named `<side>_elec_light` (their target is the FX anchor) [V] ents#5093 etc. |
| Der Riese | `warehouse_electric_trap`, `wuen_electric_trap`, `bridge_electric_trap`, two each [V] ents#1677, #1837, #1682, #1833, #1691, #1838 | script_string `warehouse`/`wuen`/`bridge`; script_linkto 20/21, 10/11, 30/31; target `warehouse_trap`/`wuen_trap`/`bridge_trap` | script_model linknames 10, 11, 20, 21, 30, 31 [V] ents#1834, #1687, #2289, #2226, #2225, #2324 | trigger_multiple named by target | `zapper_light_warehouse`/`_wuen`/`_bridge` [V] ents#2290, #2325, #1831, #2340, #1693, #2224 |

- Der Riese maps link names to lights with a hard-coded table (10/11 Wnuen, 20/21 warehouse, 30/31 bridge) [V] factory :899-915.

#### 1.6 One implementation

- Data per trap: buy triggers (list), cost, active time, cooldown, gate (none / power / power + flag), alarm position (optional), light targetname, switch model per trigger, damage trigger, FX struct name, client-notify names.
- Read it from ents: buy triggers by a per-map targetname; `target` gives both the damage trigger and FX structs; `script_linkto` → model with matching `script_linkname`; `script_string` gives the side name for client FX. Lights: Sumpf uses `script_string` as the light targetname, Verrückt and Der Riese need a small per-map table [I].
- Kill rule, player rule and FX are one shared routine; the map profile only sets numbers and gates [I].

---

### 2. The flogger (pendulum / log trap, Shi No Numa)

- **Unlock:** set up when the north-west hut door is bought (flag `nw_magic_box`), not at load [V] sumpf maps/nazi_zombie_sumpf_magic_box.gsc:43-59. Until then the trigger shows "clear debris" and the light is red [V] sumpf nazi_zombie_sumpf.gsc:281-290. Setup turns the light green [V] sumpf trap_pendulum.gsc:24.
- **Cost:** 750 [V] sumpf trap_pendulum.gsc:94. Paid immediately on press (unlike the zappers) [V] :121.
- **Sequence:** lever rotates pitch 180 over 0.5 s, 0.5 s motor ramp, then the log spins [V] :123-133.
  - The log and pulley rotate 14040 degrees (39 turns) over 30 s with 6 s ease in and 6 s ease out [V] :177-186.
  - Direction depends on which trigger was used (script_noteworthy `1` = negative, `2` = positive) [V] :177-186.
  - The log is non-solid while running and becomes solid again once no player is touching it [V] :170, :196; zipline.gsc:757-782.
- **Cooldown:** lever returns (0.5 s), then 45 s, then `warning` on `speaker_by_log` and both triggers re-enable, light green [V] :137-145. Total cycle about 76.5 s [I].
- **Kill rule (zombies):** while active, touching the damage trigger [V] :259-281:
  - Not a dog round: ragdoll launch away from the log, then killed after 0.75 s (health + 600) [V] :312-357, :370-414.
  - Launch force: x ±200-250 (sign by direction), y -35..35, z 95-120, scaled by spin-up (time/6 for the first 6 s) [V] :329-353. The timer only counts to about 20 s, so the "spin-down" branch (above 24 s) never runs [V] :283-291; [I] effect.
  - At most 5 launches per two network frames; at most 5 vocal/FX plays (`flogger_vocals`, FX `trap_log` = maps/zombie/fx_zombie_log_trp) per two frames [V] :359-412; sumpf maps/nazi_zombie_sumpf_fx.gsc:73.
  - Dog round: the AI only gets "no death animation" set and no damage, so the log does not kill dogs [V] :316-319; [I] that dogs survive.
  - Sets `trapped_used["log_trap"]` on the buyer [V] :277.
- **Players:** solo: 100 melee damage through the normal player-damage path; co-op: killed (radius damage health + 100) unless already in last stand [V] :293-310.
- **Sounds:** `switch` (on `switch_left`/`switch_right`), `motor_start_left/right`, loops `motor_loop_left/right`, `wheel_loop`, `belt_loop`, stops after 11 s / 17 s, `blade_right` woosh when the log passes 90 degrees, `purchase`, `warning` [V] :29-53, :125-166, :205-258.
- **Ents** [V] sumpf ents:
  - `pendulum_buy_trigger` ×2 (trigger_use, script_noteworthy `1`/`2`) [ents#13, #16]. Each targets its own lever model (`pen_lever` and `pf4866_auto2`) [ents#19, #18].
  - Both levers target `pen_dmg_trigger` (trigger_multiple) [ents#14] → `pf4866_auto1` (script_brushmodel, the log) [ents#15] → `pf4866_auto3` (pulley).
  - Lights `pendulum_light` ×2 (targets `log_tag_out` / `log_tag_in`) [ents#21, #23].
  - Sound origins `engine_loop_left/right`, `blade_left/right`, `switch_left/right`, `speaker_by_log` [ents#888-1007, #919].
- The chain is resolved by following `target` four times from the buy trigger; only the first trigger's damage trigger is linked to the log [V] :11-22.

---

### 3. The zipline (Shi No Numa)

- **Unlock:** set up when the north-east hut door is bought (`ne_magic_box`) [V] sumpf magic_box.gsc:64-80. Before that a "deactivated" hint trigger is shown [V] sumpf nazi_zombie_sumpf.gsc:275-278.
- **Activation (free, once):** use `zip_lever_trigger`. The lever rotates, the deactivated hint is deleted, the line makes one empty run to the far end, the gate `zipline_blocker` swings 80 degrees open over 1 s, then after 40 s the static lever resets and the zipline becomes buyable [V] zipline.gsc:96-144.
- **Cost:** 1500 [V] zipline.gsc:256. **Cooldown:** 40 s after each run ends [V] :340-349. Only one run at a time [V] :284.
- **Two buy triggers:**
  - `nonstatic`: rides on the car; usable only if the buyer is inside the car volume [V] :262-269, :287. It is hidden by moving it 10000 units down/up, because it can't be switched off while linked [V] :380-397. Its hint is suppressed while a living player is trying to revive a downed player who is in the car [V] :399-443.
  - `static`: on the electric switch; only usable while the car is at the start end; it throws the lever (0.5 s) before charging [V] :304-307, :315-319, :368-369.
- **Riders:** every valid player touching the car volume, plus the buyer of the car trigger [V] :472-476.
  - Given god mode (magic bullet shield), forced to stand, crouch and prone off, and linked to the nearest free attach point (4 points: `pf6650_auto4` origins) with free look [V] :477-510; ents#64, #65, #73, #77.
  - On arrival: unlinked, shield removed, crouch/prone back on, `on_zipline` cleared [V] :659-669. A player stuck under the floor clip is lifted to 6 units above it [V] :794-849.
  - While riding, the player's breadcrumb is faked to a fixed point at the destination so zombies path there [V] :558-561, :600-604; and zombies chasing a rider aim at the zipline destination [V] sumpf maps/_zombiemode_spawner.gsc:2845-2848, maps/_zombiemode.gsc:2653-2654.
- **Movement:** the car moves through a node chain starting at `zipline_spline` (27 nodes with script_noteworthy `zipline_nodes`) [V] zipline.gsc:53, :563-593; ents#56 etc.
  - Each hop starts at 0.3 s, gets 0.017 s faster per hop in the first third and 0.017 s slower in the last third [V] :566-592.
  - Whole run is about 4.5 s out and 4.9 s back; about 1370 units from (10764, 1608, -431) to (11214, 2891, -575) [I] from the formula and node origins.
  - The return run walks the same nodes in reverse, recorded during the outbound run [V] :564-570, :605-631.
  - `zip_pulley` brushes spin yaw 1800 over 4.8 s [V] :784-791. Handle `zip_handle` tilts to ±65 roll for the run [V] :534-543.
- **Zombies:** any zombie inside the damage volume when it starts is killed (health + 600, ragdoll; dogs no-death-anim) [V] :451-464. While moving, zombies touching the damage trigger die the same way [V] :683-701, :744-755.
- **Non-rider players:** no damage (commented out); "death" shellshock for 3 s, once every 2 s, while the car is between hop 3/4 and hop 23 [V] :703-742, :574-582, :612-620. The shellshock is precached in the map [V] sumpf nazi_zombie_sumpf.gsc:61-62.
- **AI blocker:** `zipline_ai_blocker` is made solid and disconnects paths for the outbound run; it is cleared after the return run [V] :551-556, :635-637.
- **Clip:** `zip_temp_clip` brushes go non-solid during the run; afterwards the base (`zip_base`) goes solid at once at the start end, others when no player touches [V] :514-526, :642-650.
- **Sounds:** `zip_line_wheel` origins play `script_label` once and loop `script_sound` (`wheel_loop`, `motor_loop_left`, `belt_loop`; `motor_start_left`), `zip_line_rope` origins play `rope_creak` every 0.3-0.8 s; `motor_stop_left` and `platform_bang` at the end; `purchase` + `switch` at `zip_line_switch` [V] :147-202, :237-250, :652; ents#997-1006.
- **Ents** [V] sumpf ents:
  - `zipline_buy_trigger` ×2 (script_noteworthy `nonstatic`/`static`, target `zipline`) [ents#39, #79].
  - `zipline` script_brushmodel (the car) → attach points `pf6650_auto4`; `main_spot` → car volume `pf6650_auto24` → damage trigger `pf6650_auto25` → damage volume `pf6650_auto36` → `zipline_spline` [ents#80, #73, #40, #72, #57, #56].
  - Also `zipline_blocker`, `zipline_ai_blocker`, `zip_temp_clip` ×5, `zip_handle`, `zip_handle_box`, `zip_lever`, `zip_lever_trigger`, `zipline_deactivated_hint_trigger`, `zip_pulley` ×2 [ents#24-85].
- One implementation: a generic "mover on a node chain" with riders, a kill volume, an AI-blocker brush and a two-ended state; the per-map data is the chain head, cost, cooldown, shock window and fake crumb points [I].

---

### 4. Bridges and zone management

#### 4.1 Shi No Numa "bridge riser" — dead code

- `nazi_zombie_sumpf_bridge.gsc` defines `initBridgeRiser` for `br_nw` / `br_se` / `br_sw` (buy, blockers rise 82 units, 20/24/17 s open, insta-gib zombies left on it) [V] sumpf maps/nazi_zombie_sumpf_bridge.gsc:9-151.
- Nothing calls `initBridgeRiser`; the include remains [V] grep of sumpf maps and clientscripts; nazi_zombie_sumpf.gsc:14. The map has no `br_*` ents; only audio step triggers mention "bridge" [V] sumpf ents#1207-1209.
- Treat it as cut; do not implement [I].

#### 4.2 Der Riese bridge (part of power)

- At load the two bridges are raised: `wnuen_bridge` pitch +90, `warehouse_bridge` pitch -90, coils linked [V] factory nazi_zombie_factory.gsc:374-393.
- On `electricity_on`: both lower over 4 s, paths connect, exploder 500, `bridge_lower` / `bridge_hit` at `bridge_audio`; when done flag `bridge_down`, clips deleted, zones connected (`wnuen_bridge_zone`↔`bridge_zone`, `warehouse_top_zone`↔`bridge_zone`) [V] :397-425.
- Jumping down: touching `trig_outside_south_zone` connects `outside_south_zone` one-way to `bridge_zone` and `wnuen_bridge_zone` [V] :431-438; ents#1644.

#### 4.3 Verrückt zones (first version)

- Each managed info_volume is polled every 1 s [V] asylum nazi_zombie_asylum.gsc:456-610.
- Volumes polled: `north_upstairs_volume`, `south_upstairs_volume`, `south_spawners`, `south_west_upper_corner`, `north_spawners` [V] :304-308.
- If any player touches the volume, its `target` spawners join the live spawner list, unless locked by a door [V] :518-532.
- If nobody touches it, a spawner is removed only when its `script_string` equals the volume's targetname [V] :578-587; e.g. `south_zone_spawners` have script_string `south_spawners` [V] ents#351, #1143.
- Goal (barricade) control: `exterior_goal` structs with `script_string` = `<volume>_goal` are switched on/off with the zone [V] :550-568, :594-608. The two upstairs volumes have no target, so they gate goals only [V] ents#1802-1803.
- Magic-box rooms extend the upstairs zones once the box door flag is set (`magic_room_north_volume`, `magic_room_south_volume`) [V] :490-497; ents#2260, #2262.
- Door-locked spawners: four doors start with their spawners locked and their goals off until the door's `script_flag` is set [V] :297-300, :383-454.

#### 4.4 Shi No Numa zones

- **Building zones** (`manage_building_zone`, 1 s poll): the volume's `target` spawners (dogs filtered out) are added when a player is inside and removed and locked when not [V] sumpf nazi_zombie_sumpf_zone_management.gsc:12-194.
  - Start: `center_building_upstairs` (2 volumes, target `zombie_spawner_init`) [V] sumpf nazi_zombie_sumpf.gsc:264; ents#144, #146.
  - When the downstairs debris is bought (flag `unlock_hospital_downstairs`): the upstairs zone stops; `zombie_spawner_init` spawners are renamed to `center_building_combined_spawners`; zones `center_building_combined` and `center_building_upstairs_buy` (target `attic_buy_spawners`) start; stair dog spawners join; Bouncing Betty buy turns on [V] zone_management.gsc:358-402.
  - In the combined zone, each time a hut door flag (`sw/se/ne/nw_magic_box`) is set, that side's `<side>_center_building_spawners` are added to the zone's list [V] :38-100.
- **Outdoor zones** (`manage_outside_zone`): started per side when its hut door is bought [V] magic_box.gsc:43-120.
  - Uses volume `<side>_outside` and its target spawners, plus rise structs `<side>_outside_zombie_rise` [V] zone_management.gsc:196-346, :426-431.
  - When the perk-hut door flag `<side>_building_unlocked` fires, a second watcher starts for `<side>_building` [V] :433-436; [I] the notify comes from flag_set on level.
  - Rise structs join `level.zombie_rise_spawners` only while the zone is occupied; risers spawn only at those points [V] :303-340; sumpf _zombiemode_spawner.gsc:2977-2985.
- **Ent counts** [V] sumpf ents:

  | Side | Outside spawners | Hut spawners | Rise structs |
  |---|---|---|---|
  | NE | 9 | 4 | 12 |
  | NW | 8 | 5 | 7 |
  | SE | 8 | 6 | 8 |
  | SW | 7 | 4 | 13 |

- Doors: hut-area doors are `zombie_double_door` with script_flag `<xx>_magic_box` (1000), perk-hut doors with `<side>_building_unlocked` (750) [V] sumpf ents#90-123, #5042-5070.
- Dog spawners are added per area by renaming them to `zombie_spawner_dog_init` [V] zone_management.gsc:407-416.

#### 4.5 Der Riese zone manager (the general form)

- **Zone** = all info_volumes whose targetname is the zone name [V] factory maps/_zombiemode_zone_manager.gsc:74-117. From the first volume's `target`:
  - spawners with that targetname (dog classnames go to a separate list),
  - dog spawn structs `<target>_dog`,
  - rise structs `<target>_rise`.
- **Enable** a zone: unlock `player_respawn_point` structs whose script_noteworthy is the zone name, and switch on `exterior_goal` structs whose script_noteworthy is `<zone>_barriers` [V] :122-137. All goals with any script_noteworthy start off [V] :37-48.
- **Adjacency:** `add_adjacent_zone(a, b, flag(s), one_way)` [V] :142-206.
  - A single flag, or several separate calls for the same pair, means **any** of them connects the pair [V] :169-177, :260-279.
  - An array of flags in one call means **all** must be set [V] :281-299.
  - When a flag is set the link connects and the target zone is enabled [V] :242-304. `connect_zones` connects and enables at once, from script [V] :310-341.
- **Active rule (every 1 s):** a zone is active if it is enabled and occupied, or if it is connected to an occupied zone. If no zone is occupied, `receiver_zone` is treated as occupied. Active zones add their spawners, dog spawners, dog locations and rise points to the live lists; inactive ones remove them [V] :348-556.
- **Der Riese graph** [V] factory nazi_zombie_factory.gsc:187-226, :98-99:
  - Start zone `receiver_zone`.
  - receiver↔outside_east (`enter_outside_east`), receiver↔outside_west (`enter_outside_west`).
  - wnuen↔outside_east (`enter_wnuen_building`), wnuen↔wnuen_bridge (`enter_wnuen_loading_dock`).
  - warehouse_bottom↔outside_west (`enter_warehouse_building`), warehouse_bottom↔warehouse_top and warehouse_top↔bridge (`enter_warehouse_second_floor`).
  - tp_east↔wnuen (`enter_tp_east`), tp_east→outside_east one-way (needs `enter_tp_east` AND `enter_wnuen_building`).
  - tp_south↔outside_south (`enter_tp_south`).
  - tp_west↔warehouse_top (`enter_tp_west`), tp_west→warehouse_bottom one-way (needs `enter_tp_west` AND `enter_warehouse_second_floor`).
  - Power adds outside_east↔outside_south and outside_west→outside_south one-way [V] :816-817.
  - The bridge adds the links in 4.2.
- All player respawn points start locked [V] :359-369.
- **Ent typos (rise points never used):** rise structs are named `receiver_spawners_rise` and `wnuen_brdge_spawners_rise`, but the zone targets are `receiver_zone_spawners` and `wnuen_bridge_spawners`, so the manager looks for different names [V] factory ents (rise structs and info_volumes #749 etc.); [I] those 4 rise points are dead in the original.

#### 4.6 One implementation

- Use the Der Riese manager as the single model: zones from info_volumes, adjacency and flags from a per-map table, then the "occupied or adjacent to occupied" rule [I].
- Verrückt and Shi No Numa can be expressed in it [I]:
  - Each managed volume becomes a zone with no adjacency, so only occupancy counts.
  - Their extras become per-map hooks:
    - Verrückt: remove a spawner only if its script_string matches; goals keyed by `<volume>_goal` in script_string; door-locked spawners.
    - Shi No Numa: the center-building merge; side spawners added by hut flags; outdoor rise points per zone.
- Keep the original rule exactly where it changes spawns. Example: Verrückt north spawners stay live after you leave, because only spawners whose script_string matches are removed [V] asylum :578-587; [I] whether every spawner matches needs an ent pass.

---

### 5. Der Riese teleporters

#### 5.1 Linking to the mainframe

- Needs power (`electricity_on`); before that the pad hint is "unavailable" [V] factory maps/nazi_zombie_factory_teleporter.gsc:172-176.
- Pads link **in any order**. The PaP door counts links, not which pad was linked [V] :156-236, :699-707.
- Pressing an unlinked pad is free [V] :183-199:
  - it hides all pad triggers and shows the mainframe trigger,
  - sets the pad to "timer_on",
  - starts a **30 s** countdown (HUD timer of 31 s on every player; the wait is 31 s) [V] :199, :241-278.
  - Client notifies: `pac<i>`, `TRf` (receiver map light flashes); `vox_tele_count` for players within 64 units [V] :255-256, :200, :870-871.
- **Success:** using `trigger_teleport_core` while any pad is "timer_on" sets it "active" [V] :678-735:
  - links +1 and flag `teleporter_pad_link_<n>` (n = 1..3),
  - client notify `scd<i>` and core exploder 102/103/104,
  - the countdown and HUD timer stop; `TRs`.
  - The pad then sends `pw<i>` and `tp<i>`, waits 0.1 s per wire struct in its `pad_<i>_wire` chain (17/30/21 hops, so about 1.7/3.0/2.1 s), then **fires a free teleport** of whoever is on that pad [V] :209-222, :927-949; [I] hop timings from ents.
- **Third link:** exploder 101, client notify `pap1`, `vox_tele_linkall`, earthquake (0.3 strength, 2 s, radius 3700) at the core [V] :715-725. Achievement notify if round 7 or lower [V] :720-723.
- **Failure:** the countdown ends, the pad goes "timer_off", `TRs` is sent, the pad triggers show again and you can retry for free. No other penalty [V] :265-277, :223-230.
- The mainframe hint shows "link pad" during a countdown, "inactive" with no links, otherwise nothing [V] :647-673.

#### 5.2 Teleporting

- **Cost:** 1500; **delay** 2 s; **cooldown** 5 s, all global [V] :14-16.
- Usable when the pad is linked, the buyer is valid with enough points, and no cooldown is running [V] :283-312. Each paid use hides all pad triggers [V] :302-305.
- **Who goes:** every player within 176 units 2D of the pad trigger (radius 88 × 2) [V] :442-456, :514-521.
- **Sequence** [V] :318-379, :490-642:
  1. Pad exploder 202/302/402, global exploder 105, client notify `tpw<i>`.
  2. Players near the pad get `SetTransported` for the delay; `t2d` 2D audio every 1.7 s.
  3. Pad nuke: up to 20 zombies within 300 units, one every 0.2-0.3 s.
  4. After 2 s: pad exploder 201/301/401, then the players are moved.
  5. Each non-downed player has weapons and offhands disabled and controls frozen, and is moved to `teleport_room_<i>` (stance offset: prone +49 z, crouch +20 z). Client notify `black_box_start`: the client sets the "default" vision set [V] :523-551; clientscripts/nazi_zombie_factory_teleporter.csc:34-49.
  6. After 2 s: core nuke (any number within 300), `black_box_end` (vision restored), then players are placed on free `origin_teleport_player_0..3` slots (free = no player within 16 units 2D) [V] :557-622.
  7. Weapons and controls back, then a random aftereffect; `vox_tele_sick` (2% chance of a rare line instead); "five teleports" achievement notify [V] :618-637.
  8. Global exploder 106; client notify `tpc<i>`; cooldown starts and the hint shows "cooldown" for 5 s [V] :641, :354-360, :114-139.
  9. 2 s later: special powerup drop at `teleporter_powerup` [V] :363-368.
- **Destination** is always the mainframe; the pads are one-way [V] :620; hint `ZOMBIE_TELEPORT_TO_CORE` :131.
- A downed player on the pad is counted for teleport but never gets a staging origin. The later unlink-and-delete would hit an undefined entity [V] :523, :612-616; [I] original asserts or misbehaves. Our version should skip them or move them cleanly.
- **Aftereffects** [V] :53-64, :952-1001; client .csc:17-133:
  - The server picks one of 7 at random: FOV (not in splitscreen), "explosion" shellshock 4 s, "electrocution" shellshock 4 s, or one of four "vision" ones.
  - The FOV and vision picks just send `tae` to the client. The **client then picks again at random** from its own list (FOV only if one local player), so the visible effect is double-random and can be nothing [V] client .csc:51-65, :67-75; [I] net behaviour.
  - Client effects:
    - FOV: cg_fov ramps from 30 to 65 over 0.5 s.
    - B&W: `cheat_bw_invert_contrast` in 0.4 s, hold 1.25 s, back over 1 s.
    - Red: `zombie_turned` with the same timings.
    - Flashy: `cheat_bw_invert_contrast` → `cheat_bw_contrast` → `cheat_invert_contrast` → `cheat_contrast`, 0.4 s each, back over 5 s.
    - Flare: `flare`, same timings as B&W.
  - The dvar `factoryAftereffectOverride` (default -1) forces an index [V] :45, :954-961.

#### 5.3 Pack-a-Punch door and side effects

- `pack_door` [V] :70-109:
  - Snaps down 50 at load, then rises 50 over 1.5 s once all players have connected.
  - Drops 35 at link 1 (starts the `packa_door_hitch` reminder every 4-16 s), 25 at link 2, 60 at link 3.
  - Each drop takes 1.5 s; sound `packa_door_1` for the rise, `packa_door_2` for each drop.
  - At link 3 the `pack_door_clip` brushes connect paths and are deleted.
- **Dog trigger** [V] :371-378:
  - When: the previous teleport was less than 60 s ago, all 3 pads are linked, and round > 20.
  - Then: 4 special dogs spawn and `sam_nospawn` plays.
  - The fetched `special_dog_spawner` list is not passed in (undefined is passed) [V] :373-374; [I] the dog code picks its own spawn.
- **Teleporter powerup** [V] factory maps/_zombiemode_powerups.gsc:530-565, :594-660:
  - Rounds 1-10, or anyone down: a normal powerup.
  - Later: one from the special-drop list.
    - Above round 15: chance of "nothing" = (round - 15) × 5%.
    - "full_ammo" above round 10 is re-rolled with chance (round - 10) × 5%.
    - "dog" at round 15+ spawns 1 dog instead.
- **Ents** [V] factory ents:
  - `trigger_teleport_pad_0/1/2` (trigger_use) [ents#1280-1282]; `trigger_teleport_core` [ents#1279].
  - `origin_teleport_player_0..3` and `teleport_room_0..3` (script_origin) [ents#1337-1343, #1484].
  - `pad_<i>_wire` struct chains [ents#1283, #1992, #2073]; `pack_door` [ents#114]; `pack_door_clip` [ents#1554].
  - `tele_help_0..2`, `packapunch_see` (VO triggers) [ents#196-199]; `teleporter_powerup` struct [ents#2133]; `special_dog_spawner` (actor_zombie_dog) [ents#2353].
- One implementation: pads are indexed by the trailing number in the targetname; exploder numbers and the client-notify prefixes come from a small per-map table [I].

---

### 6. Verrückt split start, power doors, and Bouncing Betties

#### 6.1 Split start

- Players are split by `initial_spawn_points` structs with script_noteworthy `north_spawn` / `south_spawn` (4 each) [V] asylum nazi_zombie_asylum.gsc:1339-1384; ents#346-349, #1980-1983.
- A coin flip picks which side gets players 0-1; players 2-3 go to the other side, using index 2 and 3 of that side's list [V] :1351-1383.
- Each player's respawn point is their start struct; after spectating they respawn there (+10 z), and their Betties and burning state are cleared [V] :70, :2405-2451.
- Both sides' first exterior goals start active (`north_init_goal` / `south_init_goal`) [V] :278-288.

#### 6.2 Power switch and power doors

- `use_master_switch` / `master_switch` [V] :1551-1693; ents#2017, #2351.
- Before power, the `electric_door` doors (script_noteworthy `electric_door`) show "unavailable" and can't be bought. The blocker script returns early for them [V] :1561-1565, :1729-1734; asylum maps/_zombiemode_blockers.gsc:137-140.
- Near one of them, `door_deny` and a `vox_start` line play once [V] :1695-1727.
- On the switch:
  - the door triggers go off and the switch rolls -90 over 0.3 s with `switch_flip`,
  - client notifies for perks plus `middle_door_open`,
  - level `switch_flipped`, `start_lights` client state, PA,
  - flag `electric_switch_used`, traps enabled [V] :1590-1649.
- After the switch:
  - `master_switch_activated` (perks), generator FX idle → on, zapper lights green [V] :1652-1668;
  - after 6 s, the perk notifies; the middle doors slide open by their `script_vector` (±90 x) with `door_slide_open`; exploder 101 [V] :1672-1686, :1813-1840;
  - lights swap to the "on" models and the box-room lights dim [V] :320-380.
- **Ents:** two `electric_door` triggers (cost key 750, not used) both target `auto180`, which is two slide models (script_string `slide_apart`, script_vector `90 0 0` / `-90 0 0`) and two clip brushes [V] ents#1678, #2347, #2594-2597.

#### 6.3 Door and blocker differences vs Nacht

Nacht's door code: the door's `target` adds new spawners, and there is no flag or power support [V] nacht_dump maps/_zombiemode_blockers.gsc:164-167, :228-230. Verrückt adds:

- Optional `script_flag` on doors, initialised at init and set when opened [V] asylum _zombiemode_blockers.gsc:62-66, :241-244. Nacht only sets flags on debris [V] nacht :264-266.
- A "slide_apart" door type: the first target has script_string `slide_apart`; every target moves by its `script_vector` with 25% ease and `door_slide_open` [V] asylum :93-108, :194-229.
- Doors may have no spawner target [V] :231-238.
- `electric_door` script_noteworthy makes the door unbuyable [V] :137-140.
- On Verrückt only, debris parts with `script_linkTo` are non-solid [V] :322-334. Bought debris notifies "junk purchased" [V] :374.
- With Speed Cola, barricade repair runs faster (0.05 s per board, no 0.2 s wait) [V] :627-633, :861-897.
- Door-locked spawners and goals [V] nazi_zombie_asylum.gsc:383-454:
  - Doors `north_lower_door` (door and debris), `south_upstairs_debris` and `magic_door` start with their spawners locked and goals off, until the flag is set.
  - Doors in ents: costs 750 or 1000, flags such as `north_door1`, `upstairs_north_door1/2`, `south_access_1`, `magic_box_north/south`, `north_upstairs_blocker`, `south_upstairs_blocker` [V] ents#645-2601.
- The box-room volumes switch on only after both doors on that side are bought [V] :1776-1811.

#### 6.4 Bouncing Betty buy

| | Verrückt | Shi No Numa / Der Riese |
|---|---|---|
| Cost | 1000 (ent key `zombie_cost` 500 is overwritten) [V] asylum :719; ents#1995 | 1000, same override of 500 [V] sumpf nazi_zombie_sumpf_bouncing_betties.gsc:25; ents#427; factory ents#1353 |
| When buyable | from start, two `betty_purchase` triggers [V] asylum :272, :311; ents#1995-1996 | Sumpf: after `unlock_hospital_downstairs` [V] sumpf zone_management.gsc:397-401. Der Riese: from start, through `_zombiemode_betty::init` [V] factory maps/_zombiemode.gsc:70; factory _zombiemode_betty.gsc:11-21 |
| Kill radius | 200 units 3D, no height check [V] asylum :852 | 200 units and within ±80 z [V] sumpf betties.gsc:165 |
| Damage | via `MOD_EXPLOSIVE` [V] asylum :852-855 | via `MOD_ZOMBIE_BETTY` = round × 100-199 [V] sumpf :167; sumpf _zombiemode_spawner.gsc:2426-2436; factory _zombiemode_spawner.gsc:2702-2708 |

- **One-time buy per player:** the trigger disappears for that player after buying; it comes back if the flag is cleared, e.g. on respawn in Verrückt [V] asylum :740-753, :761-781, :2408.
- **On buy:** the weapon goes in action slot 4 with **5** in stock [V] asylum :811-818; sumpf :131-138. The model shows (Verrückt: plain show; Sumpf/Riese: the weapon-show animation, first buy only) [V] asylum :743; sumpf :56-61. Sumpf/Riese show a 3.5 s how-to hint [V] sumpf :53, :235-249.
- **Refill:** at every "between_round_over", owners get the weapon back with the **clip set to 2** [V] asylum :877-905; sumpf :189-207.
- **Mine behaviour** [V] asylum :827-867; sumpf :140-179:
  - Arms 2 s after landing; trigger radius 80, height 64.
  - On trigger: `betty_activated`, 0.1 s, pops up 32 units in 0.2 s with `betty_trail` FX, then `betty_explode` FX and an earthquake (1, 0.4 s, 512).
  - Betties never hurt players. The trigger can be any entity, so players set them off [V] asylum :848-856; [I] trigger filter.
- **Damage-path quirk:** Verrückt's explosive damage calls the engine random int with two arguments [V] asylum maps/_zombiemode_spawner.gsc:1781-1790. The engine function takes one argument, so the real range is unclear [I].
- **One implementation:** a per-map flag "betty buy enabled after flag X" plus a damage mode (Verrückt explosive vs later betty damage) [I].

---

### Open points

- Whether every Verrückt north spawner carries the matching script_string (decides if they ever deactivate) — needs an ent pass over all asylum spawners.
- The real damage of Verrückt's two-argument random int in the explosive branch.
- Exact zipline run time: the per-hop timing is computed [I]; confirm in game or with an engine trace.
- The client side of the teleporter notifies `pw`, `tp`, `tpw`, `tpc`, `scd`, `pac`, `TRf`/`TRs`, `pap1` was not read in detail (FX/lights only).
- Sumpf hut door blockers (`nazi_zombie_sumpf_blockers.gsc`) were only skimmed for flags.

## T4 Zombies (later maps): hellhounds, Pack-a-Punch, Wunderwaffe, mystery box

Research draft for a clean-room reimplementation. Sources are the dumped scripts, ents and weapon files under the scratch root.

**Tags**
- `[V map path:line]` means read in that file. The path is relative to that map's dump, so `factory maps/x.gsc:10` is `zm_factory/maps/x.gsc` line 10.
- `[I]` means inferred.
- Maps: asylum = Verrückt (`nazi_zombie_asylum`), sumpf = Shi No Numa (`nazi_zombie_sumpf`), factory = Der Riese (`nazi_zombie_factory`).
- For ents, the line number is where the key appears in `maps/<mapname>.d3dbsp.ents`.

---

### 1. Hellhounds (`_zombiemode_dogs.gsc`, sumpf and factory)

#### Enabling
- Dogs are switched on with `level.dogs_enabled = true` in the map script [V sumpf maps/nazi_zombie_sumpf.gsc:33] [V factory maps/nazi_zombie_factory.gsc:19].
- Asylum has no `_zombiemode_dogs.gsc` and no dogs [V asylum maps/ directory listing].
- Factory also sets `level.dog_spawn_func` to `dog_spawn_factory_logic` [V factory maps/nazi_zombie_factory.gsc:29]. Sumpf leaves it unset, so it uses the "old" spawner-based path [V factory maps/_zombiemode_dogs.gsc:176-203].
- Factory lets a map replace the round tracker through `level.dog_round_track_override`. Sumpf has no such hook [V factory maps/_zombiemode_dogs.gsc:66-71].

#### Which rounds
- First dog round is random: an integer in the range 5 to 7 inclusive [V sumpf maps/_zombiemode_dogs.gsc:393] [V factory maps/_zombiemode_dogs.gsc:471].
- After each dog round, the next one is the current round plus 4 or 5, chosen at random [V sumpf :415] [V factory :493].
- The check runs on `between_round_over`. If the round number equals the next dog round, these happen [V factory :487-494]:
  - the normal spawn function is saved;
  - `dog_round_start` runs;
  - `round_spawn_func` becomes `dog_round_spawning`.
- On the first round after a dog round, the flag is cleared, the saved spawn function is restored and `dog_round_count` goes up by 1 [V factory :498-504].
- Factory keeps the value as `level.next_dog_round`; sumpf keeps it in a local variable [V diff of the two files].
- That level variable is what lets factory's crawler-round tracker align itself to dog rounds (crawler round = next dog round + 2) [V factory maps/_zombiemode.gsc:3474-3476].
  - But that tracker only runs if `level.crawlers_enabled` is set [V factory maps/_zombiemode.gsc:140-143].
  - Nothing in the factory dump sets it [I: grep found no assignment].

#### How many dogs
- First two dog rounds: 6 × player count. Third onwards: 8 × player count [V sumpf :107-114] [V factory :134-141].
- At most 2 × (valid, i.e. not downed) players are alive at once; spawning waits in 2 s steps while that cap is reached [V factory :164-170].
- Gap between spawns is a base value minus count/max, where count is dogs spawned so far [V factory :215-238]. Base values:

| Dog round # | Base gap (s) |
|---|---|
| 1 | 3.0 |
| 2 | 2.5 |
| 3 | 2.0 |
| 4+ | 1.5 |

- Before the first spawn, the round waits 7 s while the intro plays [V factory :130].
- Each dog targets the least-hunted valid player. That player's `hunted_by` count goes up by 1 [V factory :401-431].

#### Health
- `level.dog_health` is set per dog round number, capped at the round-4 value [V sumpf :359-385] [V factory :437-462]:

| Dog round # | Sumpf | Factory |
|---|---|---|
| 1 | 350 | 400 |
| 2 | 700 | 900 |
| 3 | 1000 | 1300 |
| 4+ | 1250 (cap) | 1600 (cap) |

- Sumpf: spawn health = `level.dog_health` [V sumpf :546].
- Factory: spawn health = `dog_health` × `scr_dog_health_walk_multiplier` (default 4.0), so 4× while stalking [V factory :33-36, :632-639].
  - When the dog first notifies `dog_running` or `dog_combat`, health is cut back to `dog_health` if it is higher [V factory :920-931].
  - So factory dogs are very tanky only while trotting [I].
- The aitype default is 200, but script overrides it [V factory aitype/zombie_dog.gsc:17].

#### Movement and anims
- Anim set is `zombie`, via the dvar `zombie_dog_animset` [V factory :28-31, :616].
- Zombie-set anims [V factory animscripts/dog_init.gsc:236-320]:
  - run: `zombie_dog_run`, with lean variants `zombie_dog_run_lean_l` and `_r`;
  - walk: `zombie_dog_trot`;
  - attack: `zombie_dog_run_attack`;
  - traversals: `zombie_dog_traverse_*` and `zombie_dog_run_jump_*`;
  - attack distance: 64.
- Factory only: dogs trot ("stalk") until `need_to_run` passes, then switch to run [V factory animscripts/dog_move.gsc:126-132, :323-382]. It passes when any of these holds:
  - the dog has taken damage; or
  - it can see its enemy within `scr_dog_run_distance` (factory default 500, script fallback 384), within 64 height, yaw ≤ 20 and pitch ≤ 30 [V factory maps/_zombiemode_dogs.gsc:38-41].
- Sumpf's dog_move has no stalking switch [V diff sumpf/factory animscripts/dog_move.gsc].
- Speed comes from the anims' root motion, with no script speed value [I].
- Models: `zombie_wolf` or `zombie_wolf_variant_a`, picked at random [V factory aitype/zombie_dog.gsc:26-33] [V factory character/character_sp_zombie_dog*.gsc].

#### Attack
- Saved dvar `dog_MeleeDamage` = 100 on both maps [V sumpf :14] [V factory :47].
- Factory only: during dog rounds it sets `ai_meleeRange` 100, `ai_meleeWidth` 25 and `ai_meleeHeight` 20, then restores the saved values afterwards [V factory :43-45, :522-524, :540-542].
  - The save code stores `ai_meleeWidth` in a variable named "height" and the reverse [V factory :44-45]. The swap is harmless because the restore swaps back the same way [I].
- `pathEnemyFightDist` and `meleeAttackDist` = 64 [V factory :757-758].
- Final damage to the player probably depends on difficulty/melee multipliers. A comment says 40 [V factory :17]. [I] Not verified.

#### Spawn sequence (FX, sound)
- The dog spawns hidden with magic bullet shield [V factory :644-645].
- It is then teleported to the spawn point facing its target [V factory :308-311]. On sumpf it keeps the spawner origin and only turns [V sumpf ~:273-277].
- At the spawn point, in order [V factory :313-320] [V sumpf :258-265]:
  1. FX `lightning_dog_spawn` = `maps/zombie/fx_zombie_dog_lightning_buildup`, plus sound `pre_spawn`;
  2. wait 1.5 s;
  3. sound `bolt`;
  4. Earthquake (scale 0.5, 0.75 s, radius 1000) and rumble `explosion_generic`;
  5. sound `spawn`.
- Shield removed, wait 0.1 s, then the dog is shown [V factory :328-332].
- Eye glow: `dog_eye_glow` = `fx_zombie_dog_eyes`, on a `tag_origin` model linked to `J_EyeBall_LE` [V factory :52, :661-668].
- Trail [V factory :48, :672-693]:
  - 50 % chance (`dog_fire_trail_percent`) of a fire trail: `fx_zombie_dog_fire_trail`, loop sound `dog_trail_fire`.
  - Otherwise an ash trail: `fx_zombie_dog_ash_trail`, loop sound `dog_trail_fire_breath`.
  - Fire dogs explode on death (`a.nodeath`): FX `dog_gib` = `fx_zombie_dog_explosion` and sound `zombie_dog_death`, then the corpse is deleted [V factory :682, :725-744].
- Other sounds:
  - `hellhound_stalk` loops every 1–4 s while stalking (factory) [V factory :943-954].
  - `zdog_close` plays when the dog is behind a player more than 100 units away, checked every 0.25 s [V factory :774-797].

#### Dog-round intro and outro
- Start [V factory :509-520]:
  - 2D `dark_sting`;
  - flags `dog_round` and (factory) `dog_clips` set;
  - notify `dog_round_starting`;
  - client notify `dog_start`.
- Per-player intro [V factory :546-571]:
  1. local `dog_round_start`;
  2. +1 s: `ann_vox_dog_left` and `ann_vox_dog_right` at fixed world positions (8330, 592, -160) and (11793, 1632, -160);
  3. +3 s: one random player's `vox_dog_spawn_N`;
  4. +4.5 s: 2D `ann_vox_dog_start`.
- The two fixed announcer positions are the same in the sumpf script [V sumpf :469-470], so on factory they are probably leftover sumpf coordinates [I].
- Client fog: `dog_start` pulls in volumetric fog; `dog_stop` restores it.
  - Factory values: start 229/200/380/200, colour 0.16/0.204/0.274 over 7 s [V factory clientscripts/nazi_zombie_factory_fx.csc:319-344].
  - Sumpf values: start 729.34/971.99/338.336/398.623, colour 0.58/0.60/0.56 [V sumpf clientscripts/nazi_zombie_sumpf_fx.csc:232-250].
  - Both restore to 404.39/1543.52/460.33/-244.014, colour 0.65/0.84/0.79 over 6 s.
- End: the last dog's death fires `last_dog_down` when enemy count = 0 and `zombie_total` = 0 [V factory :701-706].
- `dog_clips` (factory): `trigger_on` and `DisconnectPaths` brushes with targetname `dog_clips`. They stay active while the flag is set and while any dog is alive [V factory :803-841] [V factory ents :15334].

#### End-of-round Max Ammo
- On `last_dog_down`, the code forces the next powerup index to `full_ammo` [V factory :261-284] [V sumpf :219-237]. It also:
  - plays 2D `bright_sting`;
  - sets `zombie_drop_item` = 1 and `powerup_drop_count` = 0;
  - drops the powerup at the last dog's position.
- So a dog round always ends with a guaranteed Max Ammo where the last dog died [I from V].
- Then 2 s later client `dog_stop`; 6 s after that `dog_intermission` = false [V factory :286-289].
- `round_wait` on a dog round waits 7 s, then polls `dog_intermission` instead of counting enemies [V factory maps/_zombiemode.gsc:2219-2226] [V sumpf maps/_zombiemode.gsc:1968-1975].

#### Effect on normal rounds
- The round number still goes up through a dog round. Zombie move speed is still set from the round number in `round_think` [V factory maps/_zombiemode.gsc:2096-2098].
- Zombie health is only increased inside `round_spawning` (`ai_calculate_health`) [V factory maps/_zombiemode.gsc:1458] [V sumpf maps/_zombiemode.gsc:1328].
  - So a dog round skips one zombie health step [I].
- Sumpf: Juggernog's regen loop adds +3 health per tick during dog rounds, +40 otherwise [V sumpf maps/_zombiemode.gsc:3155-3162].
  - Asylum's version has only the +40 branch [V asylum maps/_zombiemode.gsc:2930].
- Sumpf blocks the "initial outside zombies" spawn on door open during dog rounds [V sumpf maps/nazi_zombie_sumpf_magic_box.gsc:49].
- Factory extras that spawn dogs outside dog rounds, all through `special_dog_spawn` (refuses if 2 or more dogs already exist; does not touch `zombie_total`) [V factory maps/_zombiemode_dogs.gsc:845-918]:
  - **Teleporter overuse:** 4 dogs if teleported again within 60 s, with all 3 links active and round > 20 [V factory maps/nazi_zombie_factory_teleporter.gsc:371-376].
  - **Teleporter "dog" powerup:** at round ≥ 15 the special drop can be a dog instead, with sound `sam_nospawn` [V factory maps/_zombiemode_powerups.gsc:634-641].
  - **Mixed rounds:** a dog mixed into normal rounds after round 15 [V factory maps/_zombiemode.gsc:1557-1600]. This code only runs if `level.mixed_rounds_enabled` is 1, and nothing in the dump sets it [I].
- Scoring: a dog kill uses the normal `death` points path [V factory maps/_zombiemode_dogs.gsc:710-713].

#### Spawn ents
- **Spawner class** `actor_zombie_dog` [V factory aitype/zombie_dog.gsc:2].
  - Script finds spawners by `script_noteworthy` = `zombie_dog_spawner` (also `later_round_dog_spawners`).
  - The active list is `targetname` = `zombie_spawner_dog_init` [V factory maps/_zombiemode_dogs.gsc:78-95].
- **Sumpf (spawner per location):**
  - 112 `actor_zombie_dog` ents (`spawnflags` 3, `script_forcespawn` 1). Each targets a `script_struct` used as the FX point [V sumpf ents :28510-30650] [V factory maps/_zombiemode_dogs.gsc:296-303 comment].
  - 6 start active with targetname `zombie_spawner_dog_init` [V sumpf ents :29168…].
  - The rest are grouped by area targetname and renamed to `zombie_spawner_dog_init` when that area opens (`add_area_dog_spawners`) [V sumpf maps/nazi_zombie_sumpf_zone_management.gsc:407-416] [V sumpf maps/nazi_zombie_sumpf_magic_box.gsc:62-177]:

| Area targetname | Ents |
|---|---|
| `nw_magic_box_dog_spawners` | 19 |
| `ne_magic_box_dog_spawners` | 13 |
| `se_magic_box_dog_spawners` | 9 |
| `sw_magic_box_dog_spawners` | 9 |
| `nw_perk_hut_dog_spawners` | 8 |
| `ne_perk_hut_dog_spawners` | 8 |
| `se_perk_hut_dog_spawners` | 6 |
| `sw_perk_hut_dog_spawners` | 7 |

  - `center_stairs_blocker_dog_spawn` (27 ents) is added when flag `unlock_hospital_downstairs` is set [V sumpf maps/nazi_zombie_sumpf_zone_management.gsc:358-395].
  - Sumpf picks a spawn point with `dog_spawn_sumpf_logic`. It shuffles the points and takes the first one that meets all of these; if none does, it uses the first point [V sumpf :300-326]:
    - not the previous point;
    - between 200 and 700 units from the target;
    - within 100 units of the target's height.
  - Factory's copy of the sumpf picker uses 400–800 instead [V factory :350].
- **Factory (one spawner, many structs):**
  - One `actor_zombie_dog` with targetname `zombie_spawner_dog_init` at (379.1, 1221.9, 77.1) [V factory ents :15097-15106].
  - Locations are 95 `script_struct`s named `<zone volume target>_dog` [V factory ents :15106-15235]. Examples: `tp_south_spawners_dog`, `receiver_zone_spawners_dog`, `wnuen_bridge_spawners_dog`, `warehouse_top_spawners_dog`.
  - The zone manager reads them per zone [V factory maps/_zombiemode_zone_manager.gsc:112]. It adds a zone's structs to `level.enemy_dog_locations` when the zone becomes active and removes them when it goes inactive [V :463-473, :526-535].
  - `dog_spawn_factory_logic` shuffles them and takes the first one that is not the previous point and is 400–1000 units from the target. Otherwise it uses the first one [V factory maps/_zombiemode_dogs.gsc:377-398].
  - Special dogs use the targetname `special_dog_spawner` [V factory ents :15090].
- **Shared implementation [I]:** treat dog spawn points as an abstract list of positions per zone.
  - Sumpf: positions are the spawner origins/structs from area-named groups, unlocked by door flags.
  - Factory: positions are `*_dog` structs tied to zone volumes.
  - Use one spawner template and per-map distance bands (sumpf 200–700 plus a height check of 100; factory 400–1000).

---

### 2. Pack-a-Punch (Der Riese, `factory maps/_zombiemode_perks.gsc`)

#### Ents
- `trigger_use`, targetname `zombie_vending_upgrade`, `script_noteworthy` `specialty_weapupgrade`, at (-61, 577, 153) [V factory ents :14856-14863].
- It targets `script_model` `vending_pack_a_punch`, model `zombie_vending_packapunch` [V ents :14864-14872].
- That targets the sign `pf3788_auto1`, model `zombie_sign_please_wait`. Script uses it as `wait_flag` and flips it 179° while working [V ents :14888-14894] [V perks.gsc:129-133, :106-121].
- There is a jingle struct `perksacola`, `script_sound` `mx_packa_jingle` [V ents :14877].
- A `packapunch_see` trigger_multiple plays the "see" VO [V ents :2267] [V factory maps/nazi_zombie_factory_teleporter.gsc:47-50].
- Supports several machines; each trigger runs its own thread [V perks.gsc:14-18, :383-397].

#### Power and cost
- Inactive until `Pack_A_Punch_on` [V perks.gsc:139]. That is sent when the main power switch is flipped [V factory maps/nazi_zombie_factory.gsc:796].
- On power: the model swaps to `zombie_vending_packapunch_on` with sound `perks_power_on` [V perks.gsc:398-401].
- Loop sound `packa_rollers_loop` [V :144].
- Cost is hard-coded at 5000 [V :153].
- Refused when the player:
  - is drinking, holding the betty, or in a revive trigger (`can_buy_weapon`);
  - is in last stand, throwing a grenade or switching weapons [V :155-179];
  - holds a gun whose base or `_upgraded` name is not in `zombie_include_weapons` (no message) [V :182-185].
- Not enough points: sound `deny` plus VO [V :187-192].

#### Sequence and timing
- On purchase [V :194-206]:
  - `bottle_dispense3d`;
  - 8 % chance of VO `vox_perk_packa_wait`;
  - sting `mx_packa_sting`.
- The player's gun is taken away and `zombie_knuckle_crack` is played. They get `zombie_colt` if they had one primary or fewer [V :291-340].
- World-gun animation [V :92-125]:
  1. FX `packapunch_fx` = `maps/zombie/fx_zombie_packapunch` [V :55];
  2. the gun model rotates in 0.35 s and moves in 0.5 s;
  3. `packa_weap_upgrade`;
  4. +0.35 s gun hidden;
  5. +3 s `packa_weap_ready`;
  6. the upgraded model slides out in 0.5 s.
- About 4.35 s from purchase to collectable [I from V waits].
- Then only the buyer can see the trigger (hint `ZOMBIE_GET_UPGRADED`) [V :225-227]. The gun drifts back in over `level.packapunch_timeout` = 15 s [V :57-60, :123]. Sound `ticktock_loop` [V :249].
- **Take** (buyer only, not in last stand) [V :241-275]:
  - with 2 or more primaries: through `weapon_give`;
  - otherwise: GiveWeapon plus max ammo;
  - then switch to it and play `vox_perk_packa_get`.
- **Not taken in 15 s:**
  - `pap_timeout` fires, sound `packa_deny`, model deleted, machine reset [V :279-288, :232-238].
  - The original gun was already taken and is never returned, so the weapon is lost [I from V :324].
- While a gun sits in the machine, the trigger's `current_weapon` counts towards limited-weapon totals for the box [V factory maps/_zombiemode_weapons.gsc:1253-1262].
- Sumpf and asylum have no Pack-a-Punch triggers or `_upgraded` includes [I: no `zombie_vending_upgrade` ent; sumpf include list has no `_upgraded`].

#### Base → upgraded list
- Every pair is included in factory's include list with in-box = false for the upgraded name [V factory maps/nazi_zombie_factory.gsc:453-531].
- A `weapons/<name>_upgraded` file exists for each [V factory weapons/ listing].
- Display names are from the weapon files.

| Base | Upgraded | Upgraded displayName |
|---|---|---|
| zombie_colt | zombie_colt_upgraded | PATCH_COLT45_UPGRADED |
| zombie_sw_357 | zombie_sw_357_upgraded | PATCH_357MAGNUM_UPGRADED |
| zombie_kar98k | zombie_kar98k_upgraded | PATCH_KAR98K_UPGRADED |
| zombie_m1carbine | zombie_m1carbine_upgraded | PATCH_M1A1CARBINE_UPGRADED |
| zombie_m1garand | zombie_m1garand_upgraded | PATCH_M1GARAND_UPGRADED |
| zombie_gewehr43 | zombie_gewehr43_upgraded | PATCH_GEWEHR43_UPGRADED |
| zombie_stg44 | zombie_stg44_upgraded | PATCH_STG-44_UPGRADED |
| zombie_thompson | zombie_thompson_upgraded | PATCH_THOMPSON_UPGRADED |
| zombie_mp40 | zombie_mp40_upgraded | PATCH_MP40_UPGRADED |
| zombie_type100_smg | zombie_type100_smg_upgraded | PATCH_TYPE100_SMG_UPGRADED |
| ptrs41_zombie | ptrs41_zombie_upgraded | PATCH_PTRS41_UPGRADED |
| m1garand_gl_zombie | m1garand_gl_zombie_upgraded | PATCH_M7_LAUNCHER_UPGRADED_NONADE |
| m7_launcher_zombie (alt mode) | m7_launcher_zombie_upgraded | PATCH_M7_LAUNCHER_UPGRADED |
| m2_flamethrower_zombie | m2_flamethrower_zombie_upgraded | PATCH_M2_FLAMETHROWER_UPGRADED |
| zombie_doublebarrel | zombie_doublebarrel_upgraded | PATCH_SHOTGUN_DOUBLE_BARRELED_UPGRADED |
| zombie_shotgun | zombie_shotgun_upgraded | PATCH_SHOTGUN_UPGRADED |
| zombie_bar | zombie_bar_upgraded | PATCH_BAR_UPGRADED |
| zombie_fg42 | zombie_fg42_upgraded | PATCH_FG42_UPGRADED |
| zombie_30cal | zombie_30cal_upgraded | PATCH_30CAL_UPGRADED |
| zombie_mg42 | zombie_mg42_upgraded | PATCH_MG42_UPGRADED |
| zombie_ppsh | zombie_ppsh_upgraded | PATCH_PPSH_UPGRADED |
| panzerschrek_zombie | panzerschrek_zombie_upgraded | PATCH_PANZERSCHREK_UPGRADED |
| ray_gun | ray_gun_upgraded | PATCH_RAY_GUN_UPGRADED |
| tesla_gun | tesla_gun_upgraded | PATCH_TESLA_GUN_UPGRADED |

- Not upgradable: `molotov`, `stielhandgranate`, `zombie_cymbal_monkey`, `mine_bouncing_betty`. They have no `_upgraded` include [V factory nazi_zombie_factory.gsc:490-536].
- `zombie_doublebarrel_sawed_upgraded` and `zombie_type99_rifle_upgraded` are registered with `add_zombie_weapon` [V factory maps/_zombiemode_weapons.gsc:214, :264]. They are not included on factory and have no weapon file there, so they are unreachable [V include list, weapons listing].
- The GL rifle's alt weapon follows the upgrade: `m1garand_gl_zombie_upgraded` uses alt `m7_launcher_zombie_upgraded` [V factory weapons/m1garand_gl_zombie_upgraded altWeapon].

#### Stat changes (weapon files, factory)
- In the table, damage is `damage` / `minDamage`; fire is `fireTime` in seconds per shot (lower is faster); explosive columns are inner damage / radius.

| Weapon | Damage | Clip | Max ammo | Fire (s) | Explosive | Reload (s) |
|---|---|---|---|---|---|---|
| zombie_colt | 20/20 | 8 | 80 | 0.075 | – | 1.9 |
| …_upgraded | 1000/0, projectile | 6 | 40 | 0.8 | 1200 inner / 75 outer, r200 | 1.9 |
| zombie_mp40 | 100/60 | 32 | 192 | 0.112 | – | 2.3 |
| …_upgraded | 200/120 | 64 | 192 | 0.1 | – | 2.3 |
| zombie_thompson | 120/80 | 20 | 200 | 0.08 | – | 2.1 |
| …_upgraded | 200/120 | 40 | 250 | 0.065 | – | 2.1 |
| zombie_ppsh | 100/60 | 71 | 355 | 0.048 | – | 2.1 |
| …_upgraded | 150/80 | 115 | 700 | 0.038 | – | 2.1 |
| zombie_mg42 | 130/90 | 125 | 500 | 0.064 | – | 4.5 |
| …_upgraded | 130/90 | 125 | 750 | 0.044 | – | 4.5 |
| zombie_shotgun | 160/15 | 6 | 60 | 0.283 | – | 0.6 |
| …_upgraded | 300/30 | 10 | 60 | 0.283 | – | 0.6 |
| ray_gun | 1000, projectile | 20 | 160 | 0.33 | 1500 inner, r64 | 3 |
| …_upgraded | 1000, projectile | 40 | 200 | 0.33 | 2000 inner / 300 outer, r64 | 3 |
| panzerschrek_zombie | 600 | 1 | 20 | 0.33 | 600, r256 | 2.85 |
| …_upgraded | 1000 | 3 | 30 | 0.33 | 1200, r400 | 2.85 |
| tesla_gun | see §3 | 3 | 15 | 1 | r110 | 6 |
| …_upgraded | see §3 | 6 | 30 | 1 | r150 | 4.7 |

- [V factory weapons/<name> fields `damage`, `minDamage`, `clipSize`, `maxAmmo`, `fireTime`, `reloadTime`, `explosionInnerDamage`, `explosionOuterDamage`, `explosionRadius`, `weaponType`.]
- The upgraded Colt changes weapon class:
  - `weaponType` `projectile`, `projectileModel` `projectile_usa_m9a1_riflegrenade`, impact FX `explosions/default_explosion` [V factory weapons/zombie_colt_upgraded];
  - `fireType` is `Full Auto` in the file [V].
- Other notable changes:
  - 30cal: maxAmmo 500 → 750, fireTime 0.096 → 0.08.
  - FG42: clip 32 → 64.
  - PTRS: clip 5 → 8.
  - Kar98k: 100 → 200 damage, clip 5 → 8.
  - Double-barrel: 200 → 400 damage, reload 3 → 2.5.
  - [V factory weapons/ table extraction]

#### Camo / model
- The upgrade is a model swap.
  - The machine shows `GetWeaponModel(name + "_upgraded")` [V perks.gsc:116].
  - Each upgraded file names its own view model with an `_up` suffix [V factory weapons/*_upgraded `gunModel`].
- No script-side material swap exists [V perks.gsc; no material calls].
- Whether the `_up` xmodels carry a separate camo material can't be checked without xmodel files [I].

| Base gunModel | Upgraded gunModel |
|---|---|
| viewmodel_zombie_colt45_pistol | viewmodel_zombie_colt45_pistol_up |
| viewmodel_mp_357magnum | viewmodel_zombie_357magnum_up |
| viewmodel_zombie_thompson_smg | viewmodel_zombie_thompson_smg_up |
| viewmodel_zombie_mp40_smg | viewmodel_zombie_mp40_smg_up |
| viewmodel_zombie_ppsh_smg | viewmodel_zombie_ppsh_smg_up |
| viewmodel_zombie_mg42_mg | viewmodel_zombie_mg42_mg_up |
| viewmodel_zombie_trenchgun_rifle | viewmodel_zombie_trenchgun_rifle_up |
| viewmodel_zombie_panzerschreck | viewmodel_zombie_panzerschreck_up |
| viewmodel_usa_ray_gun | viewmodel_zombie_raygun_up |
| viewmodel_usa_tesla_gun | viewmodel_zombie_tesla_up |

- World models also get `_up` versions (e.g. `weapon_zombie_mp40_smg_up`). Three keep the base world model: `zombie_sw_357_upgraded`, `ray_gun_upgraded` and `tesla_gun_upgraded` [V factory weapons/ `worldModel`].

---

### 3. Wunderwaffe DG-2 (`_zombiemode_tesla.gsc`, weapons/tesla_gun*)

#### Availability
- Sumpf: `tesla_gun` only, no upgraded file [V sumpf weapons/ listing].
- Factory: `tesla_gun` and `tesla_gun_upgraded`.
- The script initialises only if `tesla_gun` is a registered zombie weapon [V factory maps/_zombiemode_tesla.gsc:10-13, :391-394].
- It is limited to 1 copy in the world [V factory maps/_zombiemode_weapons.gsc:319] [V sumpf maps/_zombiemode_weapons_sumpf.gsc:180].
- `add_limited_tesla_gun` also disables a `weapon_upgrade` wall trigger for `tesla_gun` after one use, if a map has one [V factory weapons.gsc:323-341].

#### Chain rules (zombie_vars, same on both maps)

| Var | Value |
|---|---|
| tesla_max_arcs | 5 |
| tesla_max_enemies_killed | 20 |
| tesla_radius_start | 300 |
| tesla_radius_decay | 20 per arc |
| tesla_head_gib_chance | 50 % |
| tesla_arc_travel_time | 0.5 s |
| tesla_kills_for_powerup | 15 |
| tesla_min_fx_distance | 128 |
| tesla_network_death_choke | 4 |

- [V factory :32-40] [V sumpf, same values; diff shows no change]

**Trigger**
- Damage from `tesla_gun` or `tesla_gun_upgraded` with MOD_PROJECTILE or MOD_PROJECTILE_SPLASH starts `tesla_damage_init` [V factory :416-419] [V factory maps/_zombiemode_spawner.gsc:2670-2672].
- Sumpf's check covers only `tesla_gun` [V sumpf :419].
- One chain per player at a time. A target already marked is ignored [V factory :50-60].

**Arc search**
- From the struck enemy's `j_head`, the search radius is 300 − 20 × arc_num [V factory :93-94].
- The candidate list is all axis AI, sorted by distance once per chain [V :154-158].
- Candidates are skipped if already hit, shielded, out of range, or with no clear line (BulletTracePassed) [V :164-193].
- Arcs are recursive and depth-first: each candidate becomes a new source with arc_num + 1 [V :99-114].
- A branch stops when any of these is true [V :118-139]:
  - arc_num reaches 5;
  - 20 enemies have been hit in the chain;
  - the radius would be ≤ 0.

**Per-jump delay**
- For arc_num > 1, the kill waits `RandomFloat(0.2, 0.6) × arc_num` [V :221-224].
- RandomFloat takes one argument in this engine, so the second value is probably ignored, giving 0–0.2 × arc_num [I].
- The bolt FX moves over 0.5 s [V :385].

**Damage**
- `health + 666`, so effectively an instant kill [V factory :300].
- Factory special case: `boss_zombie` takes `level.boss_tesla_damage`, default 1000 [V :290-297].
- Each kill gives the shooter normal death points [V :302].

**Powerup**
- When the chain reaches 15 hits, one forced powerup drops at that victim (once per chain) [V :304-309].

**Killstreak VO**
- 4 or more hits plays `vox_kill_tesla` and client notify `TGH` [V :73-76, :555-566].

**Death anims**
- `ai_zombie_tesla_death_a` to `_e`, or crawl variants [V factory maps/_zombiemode.gsc:781-791].
- Dogs instead have `a.nodeath` cleared so they die normally, without exploding [V factory tesla :243-246].

#### Upgraded differences
- The script has no separate arc numbers for the upgraded gun; all chain values are shared [V factory tesla.gsc; only the weapon-name checks mention `_upgraded`].
- Differences are in the weapon file and client FX only:

| Field | tesla_gun | tesla_gun_upgraded |
|---|---|---|
| clipSize / maxAmmo / startAmmo | 3 / 15 / 15 | 6 / 30 / 30 |
| reloadTime | 6 | 4.7 |
| explosionRadius | 110 | 150 |
| gunModel | viewmodel_usa_tesla_gun | viewmodel_zombie_tesla_up |
| fire sound (player) | wpn_tesla_fire_plr | weap_tesla_fire_ubershot_st |
| last shot (player) | wpn_tesla_fire_plr_last | weap_tesla_firelast_ubershot_st |
| projTrailEffect | maps/zombie/fx_zombie_tesla_electric_bolt | maps/zombie/fx_zombie_tesla_ug_elec_bolt |
| ammoName / clipName | tesla_gun / tesla_gun | tesla_gun / tesla_gun_upgraded |

- [V factory weapons/tesla_gun, tesla_gun_upgraded]
- The reserve ammo pool name is shared (`ammoName` = tesla_gun) [V].
- Client viewmodel rail/tube FX switch to `_ug` variants and track clip count [V factory clientscripts/_zombiemode_tesla.csc:12-20, :79-140].

#### Weapon file (projectile and ammo)
- `weaponType` projectile, `weaponClass` mg, `fireType` Full Auto, `fireTime` 1 s.
- `projectileModel` `tag_flash` (invisible carrier), `projectileSpeed` 2250, `projectileLifetime` 30.
- `projImpactExplode` 1, `projExplosionType` grenade, `impactType` tank_shell.
- `damage` 1; explosion inner/outer 1/1. The kill is entirely scripted [I from V].
- Sounds: `projectileSound` `wpn_tesla_proj_loop`; `projExplosionSound` `wpn_tesla_proj_impact`.
- Flash FX: `weapon/muzzleflashes/fx_tesla_view` and `_world`.
- `meleeDamage` 150.
- [V factory weapons/tesla_gun]
- The sumpf file differs from factory only in `notetrackSoundMap` [V field diff].

#### Self-damage ("humangun" rule)
- No `humangun` identifier exists in either dump [V grep].
- The rule lives in `tesla_pvp_thread` [V factory :485-531]. If a player is hit by their own tesla projectile (`weapon_pvp_attack`, MOD_PROJECTILE or MOD_PROJECTILE_SPLASH), and is not in last stand:
  - they lose 25 % of max health, minimum 25;
  - this never takes them below 1 health.
- Any tesla hit on a player (own or other) applies `setelectrified` 1 s, shellshock `electrocution` 1 s and sound `tesla_bounce` [V :528-530].

#### FX and sound aliases
- FX [V factory :15-28]:
  - `tesla_bolt` = `fx_zombie_tesla_bolt_secondary` (travelling arc);
  - `tesla_shock` (first victim) and `tesla_shock_secondary` (later arcs), on `J_SpineUpper`, or `J_Spine1` for dogs;
  - `tesla_shock_eyes` on `J_Eyeball_LE` when there is no head gib;
  - `tesla_head_light` = `fx_zombie_tesla_neck_spurt` on gib [V factory maps/_zombiemode.gsc:654].
- Sounds: `imp_tesla` (victim), `tesla_bounce` (each arc), `tesla_idle` loop while equipped [V :329, :383, :457].
- Arc FX is skipped when the two bodies are closer than 128 [V :371-377].

---

### 4. Mystery box (per map)

#### Common rules (all three maps)
- Cost: 950, or the trigger's `zombie_cost` (950 on every chest ent) [V factory maps/_zombiemode_weapons.gsc:724-732] [V sumpf maps/_zombiemode_weapons_sumpf.gsc:441] [V asylum maps/_zombiemode_weapons.gsc:360].
- **Ent chain:** `trigger_use` targetname `treasure_chest_use` → lid → weapon origin → box base [V factory weapons.gsc:661-676].
  - Ent names: lid `magic_box_lid_N`, base `magic_box_base_N`.
  - The location name is in `script_noteworthy` [V ents].
  - The hidden-box marker is the rubble/debris ent with `script_noteworthy` = `<chest noteworthy>_rubble`, shown when the box is absent [V factory weapons.gsc:626-643, :1072-1085].
- **Spin:** 40 cycles of model swaps.
  - Waits: 20 × 0.05, 10 × 0.1, 5 × 0.2, 3 × 0.3, about 4.4 s in all. The model rises 40 units over 3 s [V factory :1349-1401].
  - Pick-up window: 12 s; the gun sinks back over 12 s [V factory :1183-1188, :1552-1565].
  - The trigger is visible only to the buyer [V factory :800].
- **Teddy bear:** model `zombie_teddybear`.
  - The buyer gets the 950 back [V factory :1484-1496] [V sumpf :1227].
  - Flag `moving_chest_now`; weapon flies up 500 units over 4 s.
  - `chest_accessed` resets to 0 [V factory :1490, :1503-1510].
  - The whole teddy system needs dvar `magic_chest_movable` = "1", which is the default on all three maps [V asylum maps/_zombiemode.gsc:426-428] [V sumpf maps/_zombiemode.gsc:518-520] [V factory maps/_zombiemode.gsc:585-587].
  - `chest_accessed` goes up by 1 after each resolved spin, whether taken or timed out [V factory :845]. So during spin n it equals the number of earlier completed spins [I].
- **Move FX and sounds:**
  - `laugh_child` per player; `box_move`, `whoosh`, `ann_vox_magicbox`.
  - The box rises 50 units over 5 s while vibrating, then `poltergeist` FX and `box_poof` [V factory :979-1066].
  - It reappears 5 s later with `box_poof`, `box_poof_land` and `couch_slam` [V factory :683-720, :1092].
  - `poltergeist` FX differs per map: `misc/fx_zombie_couch_effect` (asylum, factory) or `maps/zombie/fx_zombie_debris_removal` (sumpf) [V asylum maps/nazi_zombie_asylum_fx.gsc:109] [V factory maps/nazi_zombie_factory_fx.gsc:37] [V sumpf maps/nazi_zombie_sumpf_fx.gsc:56].
- **Location beacon** (sumpf and factory): `lght_marker` on `level.pandora_light`; arrival flare `lght_marker_flare`.
  - Factory: `fx_zombie_factory_marker` / `_fl` [V factory maps/nazi_zombie_factory_fx.gsc:53-54].
  - Sumpf: `fx_zombie_lght_marker` / `_flare` [V sumpf maps/nazi_zombie_sumpf_fx.gsc:67-68].
  - Glow inside the box while it is open: `chest_light` = `env/light/fx_ray_sun_sm_short` [V factory maps/_zombiemode.gsc:645].
- **Box filter** (every map) removes:
  - weapons the player already has (factory also counts the upgraded version);
  - limited weapons at their cap;
  - `mine_bouncing_betty` [V factory :1211-1270] [V sumpf :928-1080].
  - Factory also counts a gun sitting in the PaP machine towards limits [V factory :1253-1262].
  - Factory uses `count >= limit`; sumpf and asylum use `count == limit` [V factory :1264; sumpf :1074; asylum :791].
- **Limited weapons:**
  - flamethrower = 1 on all maps; `tesla_gun` = 1 on sumpf and factory [V].
  - "Limit 0" names are never in the box: colt, gewehr43, m1garand on sumpf and factory; type99_rifle on sumpf [V sumpf maps/nazi_zombie_sumpf.gsc:181-184] [V factory maps/nazi_zombie_factory.gsc:539-542].

#### Asylum (Verrückt)
- Pool: every included name that also has an `add_zombie_weapon` entry [V asylum maps/nazi_zombie_asylum.gsc:621-683, cross-checked with weapons.gsc]:
  - sw_357, m1carbine, m1garand, gewehr43, stg44, thompson, mp40, ppsh, kar98k, springfield;
  - ptrs41_zombie, molotov, stielhandgranate, m1garand_gl_zombie, m2_flamethrower_zombie;
  - doublebarrel, doublebarrel_sawed_grip, shotgun;
  - fg42_bipod, mg42_bipod, 30cal_bipod, bar, bar_bipod;
  - panzerschrek_zombie, ray_gun.
- All weights are equal; no ray gun gating or boost [V asylum :741-799].
- `m7_launcher_zombie` is included but never registered, so it is not in the pool [I from V].
- **Teddy chance:** `chest_accessed` < 5 gives chance 0, but the test is `rand ≤ chance` with rand 0–99. So it is 1 % even on early pulls [V asylum :852-864]. [I] This is the bug later maps fixed with −1.
  - From then on the chance is (chest_accessed + 4) % [I from `+3` and `≤`].
- **Move:**
  - next index in the array, skipping same-origin entries [V asylum :597-607];
  - then, with `magic_box_explore_only` = "1" (asylum default) [V asylum maps/_zombiemode.gsc:431-433], it keeps stepping until the location is in `level.open_chest_location` [V asylum weapons.gsc:614-631].
- **Open list** [V asylum maps/nazi_zombie_asylum.gsc:2238-2290]:
  - always: `opened_chest`, `start_chest`;
  - door flags add `magic_box_south` (flags `magic_box_south` / `south_access_1`), `magic_box_bathroom` (flags `south_access_1` / `south_upstairs_blocker`) and `magic_box_hallway` (flags `north_door1` / `north_upstairs_blocker`).
- Chests (5): `start_chest`, `magic_box_hallway`, `magic_box_bathroom`, `opened_chest`, `magic_box_south` [V asylum ents :12067-15258].
- Asylum looks up rubble with a single `getent` (one rubble ent per chest) [V asylum :637].

#### Sumpf (Shi No Numa), `_zombiemode_weapons_sumpf.gsc`
- Uses its own copy of the weapons script [V sumpf maps/_zombiemode.gsc:43].
- Pool (one entry each to start) [V sumpf maps/nazi_zombie_sumpf.gsc:120-184] [V weapons_sumpf.gsc:76-181]:
  - sw_357, zombie_m1carbine, zombie_stg44, zombie_thompson, zombie_mp40, zombie_type100_smg;
  - molotov, stielhandgranate, m1garand_gl_zombie, m2_flamethrower_zombie;
  - zombie_doublebarrel, zombie_doublebarrel_sawed, zombie_shotgun;
  - zombie_bar, zombie_30cal, zombie_fg42, zombie_mg42, zombie_ppsh;
  - panzerschrek_zombie, ray_gun, tesla_gun.
- `ptrs41_zombie` is included, but its `add_zombie_weapon` line is commented out, so it is not in the box or registered here [V weapons_sumpf.gsc:122].
- **Ray gun:** excluded until the box has moved at least once since the last ray gun (`box_moved`) [V :950-959].
  - After a move, if the player lacks it, extra copies are appended when `pulls_since_last_ray_gun` > 7 (10 % of the filtered size) or > 11 (15 %) [V :970-998].
  - The loop adds ceil(n) − 1 copies, so the real share is lower than the comments say [I].
  - Getting a ray gun resets `box_moved` and the counter [V :1258-1263].
- **Wunderwaffe** extra copies [V :1003-1040]:
  - +20 % of the filtered size if anyone has ever swapped the tesla away (`player_drops_tesla_gun`);
  - if it has never been pulled (`player_seen_tesla_gun` false), also +15 % after round 5 or +20 % after round 10;
  - the same ceil − 1 effect applies.
- Counters go up per resolved spin [V :564-576].
- Sumpf runs the weighted filter on every one of the 40 cycles, not only the last [V :1101-1121].
- **Teddy chance** [V :1150-1220]:

| `chest_accessed` | Chance |
|---|---|
| < 4 | 0 (−1 sentinel) |
| 4–7 | 15 % |
| ≥ 8, before the first move | 100 % |
| 8–12, after the first move | 30 % |
| ≥ 13, after the first move | 50 % |

- **Box move** [V weapons_sumpf.gsc:745-800] [V sumpf maps/nazi_zombie_sumpf_magic_box.gsc:10-33, :184-210]:
  - Steps through the shuffled array until the location is in `level.open_chest_location`.
  - The array is reshuffled at wrap-around, avoiding an immediate repeat of the last name.
  - The open list starts as `start_chest` + `attic_chest`. Each opened swamp area adds `nw_chest`, `ne_chest`, `se_chest` or `sw_chest` (flags `nw_magic_box` etc.) [V magic_box.gsc:35-121].
  - First teddy (`weapon_fly_away_start`): the list becomes only the four hut chests, and `magic_box_first_move` = true. The first move always lands in a hut [V magic_box.gsc:184-198].
  - After that move (`magic_box_light_switch`), all six are valid [V :201-209].
- Chests (6): `start_chest`, `attic_chest`, `nw_chest`, `ne_chest`, `se_chest`, `sw_chest`, each with a `_rubble` ent [V sumpf ents :3079-3249].
- Beacon spawns at (-4200, 0, 0) at start [V weapons_sumpf.gsc:322].
- Sumpf also blocks box use while the player is drinking [V :468-473, :539].

#### Factory (Der Riese)
- Weighted: cycles 1–39 use the unweighted picker; only the final cycle (the result) uses `treasure_chest_ChooseWeightedRandomWeapon` [V factory weapons.gsc:1381-1387].
- Weighting functions are per weapon through `include_weapon(name, in_box, func)` [V factory maps/_zombiemode_utility.gsc:1898-1904] [V weapons.gsc:162-183]. The default weight is 1.
- Pool [V factory nazi_zombie_factory.gsc:453-536, cross-checked with weapons.gsc:185-320]:

| Weapon | Weight / rule |
|---|---|
| zombie_sw_357, zombie_kar98k, zombie_m1carbine, zombie_stg44, zombie_thompson, zombie_mp40, zombie_type100_smg, ptrs41_zombie, molotov, stielhandgranate, m1garand_gl_zombie, zombie_doublebarrel, zombie_shotgun, zombie_bar, zombie_fg42, zombie_30cal, zombie_mg42, zombie_ppsh, panzerschrek_zombie | 1 each |
| m2_flamethrower_zombie | 1, limit 1 |
| tesla_gun | 1, limit 1 |
| ray_gun | `factory_ray_gun_weighting_func`: 0 until box_moved; then 1, +int(0.05 × 53) = +2 after 8 pulls, +int(0.1 × 53) = +5 after 12 pulls |
| zombie_cymbal_monkey | `factory_cymbal_monkey_weighting_func`: 3 before round 10, 5 from round 10, 1 once any player owns one |

- Sources for the weighting rows:
  - include is called with `true` and no function [V nazi_zombie_factory.gsc:530];
  - limits [V weapons.gsc:318-319];
  - ray gun function [V nazi_zombie_factory.gsc:546-571];
  - monkey function [V :576-601].
- The include table has 53 names [V count], which is what the 0.05 and 0.1 multipliers apply to; the totals 1/3/6 are [I].
- The more generous `default_tesla_weighting_func` and `default_ray_gun_weighting_func` in `_zombiemode_weapons.gsc` are not referenced on factory [V grep], so the tesla stays at weight 1 [I].
- `m7_launcher_zombie` is included but not registered [I from V].
- Mine and upgraded names are in_box = false [V].
- **Teddy chance:** factory never sets `magic_box_first_move` [V grep], so [V factory weapons.gsc:1409-1478, gate :1417]:

| `chest_accessed` | Chance |
|---|---|
| < 4 | 0 (`chest_min_move_usage` = 4) |
| 4–7 | 15 % |
| ≥ 8 | 100 % |

  - So the box is guaranteed to move by the 9th spin at one location [I].
- **Move:**
  - The chest array is shuffled at start, keeping `start_chest` out of index 0, and the box starts at `start_chest` (unless `random_pandora_box_start` is set) [V weapons.gsc:519-550, :590-622].
  - On a move, the index goes up by 1. At the end the array is reshuffled, avoiding the same name twice [V :1103-1126].
  - There is no open-area check, so the box can move to rooms not yet opened [I from V; verify call commented out :1128].
- Chests (6): `start_chest`, `chest1`–`chest5`, each with a `_rubble` ent [V factory ents :8840-15349].

#### Cymbal monkey (factory)
- Box-only (weights above). There is no wall buy; the 2000 in `add_zombie_weapon` is unused for the box [V weapons.gsc:302].
- Getting one removes molotovs; getting a molotov removes the monkey [V factory maps/_zombiemode_weapons.gsc:1650-1672].
- Weapon file [V factory weapons/zombie_cymbal_monkey]:
  - offhand smoke-grenade class;
  - clip/max 3;
  - fuse 8 s;
  - explosion 5000 inner / 450 outer, radius 100.
- Once it settles, it becomes a zombie point of interest: range 1536, 96 attractor slots, attractor spacing 45 [V factory maps/_zombiemode_cymbal_monkey.gsc:24-62, :93].
- Glow FX `fx_zombie_monkey_light`; `monkey_song` (or `monkey_scream_vox` in an easter-egg trigger). The model anim is cleared at 6.4 s, then `monkey_explo_vox` [V :8, :131-168].
- Zombies within 500 units groan (`zombie_groan_monkey`) [V :217-239].

#### Bowie knife (factory)
- Trigger `bowie_upgrade` targets the model `knife_bowie` at (234, -2362, 158); the chalk outline is `knife_bowie_chalk` [V factory ents :10185-10207].
- Cost 3000, or `level.bowie_cost` [V factory maps/_zombiemode_bowie.gsc:20-29].
- It grants perk `specialty_altmelee`, with a flourish `zombie_bowie_flourish`. You can't buy it twice; the check is HasPerk [V :80-125].
- It is kept through spectator respawn via `has_altmelee` [V factory maps/_zombiemode.gsc:1256-1258].
- Melee with the perk gives a 75 % head-gib roll [V factory maps/_zombiemode_spawner.gsc:1762].
- The actual melee damage boost is applied by the engine perk, not script [I].

#### Shared box implementation [I]
- **Chest location record:**
  - trigger noteworthy (location name);
  - lid, origin and base ents;
  - rubble ents: all ents whose `script_noteworthy` is name + `_rubble`;
  - `zombie_cost`.
- **Per-map profile:**
  - teddy table (asylum linear; sumpf staged with a first-move flag; factory staged with no first-move);
  - picker style (asylum/sumpf weighted every cycle; factory weighted on the last cycle only);
  - move rule (asylum and sumpf: open-list filter; factory: none; sumpf: first move to huts);
  - weight functions per weapon (ray/tesla/monkey);
  - limit compare (`>=` versus `==`).
