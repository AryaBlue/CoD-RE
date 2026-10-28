# T5 vs T4 zombies: the framework differences

What BO1's `_zombiemode` changes against WaW's (Der Riese's framework is the baseline), for the per-game profile.

Tags:
- **[V]**: BO1 cites are `bo1:` paths relative to the BO1 mod tools' `raw/`. WaW cites are `waw:` paths relative to the
  Der Riese dump.
- **[I]**: inferred.

## BO1 vs WaW `_zombiemode`: what a per-game profile must cover 

Baseline: WaW Der Riese framework (`waw:` = `<scratch>/zm_factory/`). BO1: mod-tools raw (`bo1:` = `<BO1 mod tools>/raw/`).
Only differences are listed. Anything not mentioned matched between the two in the code I read.

Sources and caveats:
- BO1 level script: `zombie_theater.gsc` is **not** in raw/. `map_source/zombie_theater.map` (and the pentagon and cosmodrome .maps) are 50-byte "Blank" stubs [V]. So `bo1:maps/zombie_pentagon.gsc` is the only BO1 level script I used.
- Both games read tunables from `mp/zombiemode.csv` through `set_zombie_var`. The table value **overrides** the script default.
  - WaW reads column 1 only (`waw:maps/_zombiemode_utility.gsc:1260-1280`) [V]. The WaW table I used is `<scratch>/common_dump/mp/zombiemode.csv` [V].
  - BO1 adds difficulty columns: NAME, EASY, MEDIUM, HARD, VETERAN (`bo1:mp/zombiemode.csv:5`) [V].
    - `difficulty = 1`, so column = 2, which is MEDIUM (`bo1:maps/_zombiemode.gsc:466-467`) [V].
    - Only calls that pass `column` use it. Every other call reads column 1, which is EASY (`bo1:maps/_zombiemode_utility.gsc:2232-2257`) [V].
  - **A profile must model this lookup, or it will get Jugg and other values wrong** (see Perks).
- Nacht docs: the Nacht numbers (spawn delay 3, solo 24) are older than Der Riese. The Der Riese values are below, where they matter.

### 1. Rounds: counts, health, speed, timing

| area | WaW (Der Riese) | BO1 | profile field |
|---|---|---|---|
| base max | 24 + extra, where solo extra = int(0.5×6×mult) and co-op extra = int((p−1)×6×mult); mult = max(1, r/5), then ×(r×0.15) from r10 (`waw:maps/_zombiemode.gsc:1469-1491`) [V] | identical (`bo1:maps/_zombiemode.gsc:2139-2157`) [V] | `zm_count_base`, `per_player` |
| early-round scale | r1 ×0.2, r2 ×0.4, r3 ×0.6, r4 ×0.8 (`waw:…_zombiemode.gsc:1511-1527`) [V] | r1 ×0.25, r2 ×0.3, r3 ×0.5, r4 ×0.7, **r5 ×0.9**, in `default_max_zombie_func`, which `level.max_zombie_func` can override (`bo1:…_zombiemode.gsc:2091-2116, 2161-2168`) [V] | `early_round_scale[]` |
| solo r1-r6 | 5, 10, 16, 21, 27, 27 [I, computed] | 6, 8, 13, 18, 24, 27 [I, computed] | |
| 4p r1 | 8 [I] | 10 [I] | |
| spawn loop | runs `while count < max` (`waw:…:1535`) [V] | driven by `zombie_total`, and also waits on flag `spawn_zombies` (`bo1:…:2178-2186`) [V]. `zombie_total` is not reset when a kill-counter HUD round carries it over (`:2165-2168`) [V] | |
| alive cap | 31 in the script check; `SetAILimit(24)` (`waw:…:26`) [V] | same, 31 and 24 (`bo1:…:64, 2179`) [V] | |
| spawn delay | 2.0 at the start (`waw:…:525`) [V]; ×0.95 per round, with the 0.08 clamp applied **before** the multiply, so it settles at about 0.076 (`:2086-2093`) [V] | 2.0 (csv MEDIUM). ×0.95 while above 0.08, otherwise set to 0.08, so the floor is a true 0.08 (`bo1:…:2728-2736`) [V] | `spawn_delay_start`, `spawn_delay_floor_mode` |
| health | 150; +100 per round to r9, ×1.1 per round from r10, accumulated (`waw:…:2136-2148`) [V] | same numbers, but recomputed from round 1 every call (`bo1:…:2772-2787`) [V]. The result is identical [I]. EASY would be 80/80/0.075 (`bo1:mp/zombiemode.csv:10-12`) [V] | `health_*` |
| move speed | `round × 8` (`waw:…:2096`) [V] | `round × zombie_move_speed_multiplier`, which is 8 on MEDIUM (`bo1:…:2739`, csv:15) [V]. The walk/run/sprint thresholds are unchanged (`bo1:maps/_zombiemode_spawner.gsc:274-289`) [V] | `move_speed_mult` |
| last-zombie sprint | after spawning ends, from r > 3: one legged zombie left starts sprinting (`waw:…:1624-1638`) [V] | `zombie_speed_up`, rounds 4-9 only: waits until `zombie_total ≤ 4` and ≤ 3 alive, then sprints the last legged one (`bo1:…:2169-2172, 2266-2290`) [V] | `last_zombie_sprint_rounds` |
| late spawners | `add_later_round_spawners` each round (`waw:…:2058`) [V] | removed from `round_think` (`bo1:…:2684-2741`) [V] | flag |
| round start | no wait in `round_start` (`waw:…:1707-1735`) [V] | waits 2 s, or runs `level.round_prestart_func`. Then `game_start_delay` (0 on MEDIUM, 30 on HARD/VET) before `begin_spawning` (`bo1:…:2345-2377`, csv:34) [V] | `round_start_delay` |
| between rounds | waits `zombie_between_round_time` = 10 (`waw:…:2083`) [V] | `chalk_round_over`: (10−2) s, i.e. 8 blink steps of 1 s, plus 2 s, so about 10 s (`bo1:…:2626-2686`) [V]; ≈10 s total [I]. `round_wait` also adds 1 s at the start and checks every 1 s (`:2846-2868`) [V] | `between_round_time` |
| spectator respawn | every round | skipped in solo (`bo1:…:2720`) [V] | |
| failsafe | 30 s, < 24 units moved or below z −1000 kills the zombie (Nacht doc) | same, plus an optional `put_timed_out_zombies_back_in_queue`, which refunds `zombie_total` (`bo1:…:2795-2840`) [V] | `failsafe_requeue` |
| intermission | 15 s | 15 s (csv:35 is a single column, so the script default 15 applies) [V] | |

### 2. Spawners, zone manager, risers

- **WaW:**
  - `level.enemy_spawns` starts as every `zombie_spawner_init` (targetname) (`waw:maps/_zombiemode.gsc:28-35`) [V].
  - It is then edited incrementally by zones (add/remove, `waw:maps/_zombiemode_zone_manager.gsc:428-558`) and by doors (`add_new_zombie_spawners`) [V].
  - Spawners: script_noteworthy `zombie_spawner` or `later_round_spawners`. A spawner targeted by a door or debris gets `locked_spawner` (`waw:maps/_zombiemode_spawner.gsc:20-30`) [V].
- **BO1 is purely zone driven:**
  - There is no `zombie_spawner_init` and no per-door spawner add. `add_new_zombie_spawners` exists but nothing calls it (grep) [V].
  - Spawners: script_noteworthy `zombie_spawner`. Targeted by a door or debris means `is_enabled = false` (`bo1:maps/_zombiemode_spawner.gsc:9-18`) [V].
- **BO1 zone:**
  - Built from `info_volume` ents whose targetname is the zone name; only the classname `info_volume` counts (`bo1:…zone_manager.gsc:114-121`) [V].
  - `volumes[0].target` gives the spawners, which get `spawner.zone_name`. `actor_zombie_dog` spawners go to a separate dog list. `level.ignore_spawner_func` can filter (`:126-152`) [V].
  - Dog structs are `<target>_dog`, riser structs `<target>_rise` (targetname). Same naming as WaW (`:154-164`, `waw:…:112-115`) [V].
- **BO1 `manage_zones`:**
  - It takes a zone name or an array (`bo1:maps/zombie_pentagon.gsc:49-50`) [V].
  - It locks every `player_respawn_point` (each needs script_noteworthy = zone) until its zone is enabled. Then it waits for `begin_spawning` (`bo1:…zone_manager.gsc:419-450`) [V].
  - Every 1 s it **rebuilds** `enemy_spawns`, the dog locations and `zombie_rise_spawners` from zones that are enabled and active. Active means occupied, or adjacent with `is_connected` and enabled (`:458-557`) [V].
  - The fallback when no zone is occupied is the initial zone. WaW hard-codes `receiver_zone` (`waw:…zone_manager.gsc:418`) [V].
  - `level.random_spawners` plus `zone.num_spawners` randomly trims a zone's spawners (`bo1:…:522-531`) [V].
  - `enable_zone` also turns on the `<zone>_barriers` exterior_goals (script_noteworthy) (`:218-223`) [V].
  - Zone flags: `add_adjacent_zone(a, b, flag, one_way)` as in WaW. BO1 adds OR-ed multi-flags (`make_zone_adjacent`) and `add_zone_flags` (`:225-297`) [V].
- **Risers:**
  - Both trigger on spawner script_string `riser` (`bo1:…spawner.gsc:316-320`, `waw:…spawner.gsc:276`) [V].
  - WaW picks from the global zone list only for a hard-coded list of map names, otherwise from all `zombie_rise` structs (`waw:…spawner.gsc:3349-3358`) [V].
  - BO1 picks from **its own spawner's zone** `rise_locations`. Otherwise `rise_target_name`, then the global list (indexed by `script_index` if it is an array), then `zombie_rise` (`bo1:…spawner.gsc:3690-3713`) [V].
  - BO1 riser fx variants: script_string `in_water` / `in_snow` (`:3824-3857`) [V].
  - Spawn-chase overrides: spawner script_string `zombie_chaser`, or a rise struct `find_flesh`, skip the window teardown (`bo1:…spawner.gsc:290-302`) [V].
- **Profile:** `spawner_source = init_list+doors | zones_only`, `riser_pick = global | per_zone`, `initial_zone[]`.

### 3. Windows / barricades

- **The same in both:**
  - Ents: `exterior_goal` structs → chunks (targets) + a `clip` (script_noteworthy). The trigger location is a struct sharing the target (`bo1:maps/_zombiemode_blockers.gsc:862-968`, `waw:…blockers_new.gsc:550-583`) [V].
  - Repair trigger: radius 96, height 96 (overridable by struct keys), 4 units above the ground, 10 points per board, 1 s per board. The cap is min(50×round, 500) per player per round (`bo1:…blockers.gsc:1024-1226`, `bo1:…_zombiemode.gsc:2691-2696`) [V].
  - Attack spots: 3, at 36 units back and ±28 to the side (`bo1:…blockers.gsc:985-1003`) [V].
  - Board count: whatever the map's chunks are; neither script fixes it [V].
- **BO1 additions:**
  - Chunk kinds via `script_parameters`: `grate` (pieces 2-6 hidden at start), `repair_board` (with an `unbroken_section` target, which can be `glass`, destructible by player damage, or `metal`), `bar`. script_string `rock` is a material (`bo1:…blockers.gsc:877-918`, `970-984`) [V].
  - `window_shutter` ents (powered shutters, `:2396-2645`) [V].
  - Mutator `noBoards` starts every window destroyed (`:871-874, 937-943`) [V].
  - Repair stops if no "valid repairable" boards remain (`:1013-1016`) [V].
  - It uses `use_button_held` instead of `UseButtonPressed` (`:1145`) [V].
  - Pay goes through `player_add_points("rebuild_board")`, so the double-points multiplier applies at pay time. WaW recomputes the cost ×2 when doubler status changes and adds the raw value (`waw:…blockers_new.gsc:661-735, 765`) [V]. Same net result [I].
  - Speed Cola: BO1 also handles `specialty_fastreload_upgrade` (`bo1:…blockers.gsc:1693-1720`) [V].

### 4. Doors and debris

| area | WaW | BO1 | profile field |
|---|---|---|---|
| ents | trigger targetname `zombie_door` / `zombie_debris`, key `zombie_cost` (default 1000) | same (`bo1:…blockers.gsc:28-60, 61-118`) [V] | |
| door styles | `script_string` rotate / move / slide_apart / anim / clip | adds `physics`, plus counter parts `counter_1s/10s/100s` and `explosives` (`bo1:…:120-175, 437-529`) [V] | `door_styles` |
| door types (trigger script_noteworthy) | `electric_door` only; waits on flag **`electricity_on`** (`waw:…blockers_new.gsc:136`) [V] | `electric_door`, `electric_buyable_door` (power, then pay), `delay_door` (pay, then `script_int` s, default 5, explosives fx), `kill_counter_door`; power flag **`power_on`** (`bo1:…:530-576, 224-261`) [V] | `power_flag`, `door_types` |
| script_flag | one flag | comma-separated list, all set (`bo1:…:66-77, 578-585`) [V] | |
| spawners | door/debris targets add spawners | none; zones only (§2) [V] | |
| payment | player score | solo: player score. Co-op: team pool first, then the remainder from the player (`bo1:…:176-222, 723-746`) [V]. The team pool starts at 0 on MEDIUM (csv:29-32) [V] | `team_pool` |
| move time | door `MoveTo` with accel/decel 0.25×time | same; if time < 0.5 there is no accel (`bo1:…:500-507`) [V] | |
| debris | `script_linkTo` → struct move 0.5 s, then delete; clip deleted after `movedone` | same (`bo1:…:752-860`) [V] | |

### 5. Wall buys

- **Ents** (both): trigger targetname `weapon_upgrade`, key `zombie_weapon_upgrade`. It targets the hidden wall model, which shows on the first buy (`bo1:maps/_zombiemode_weapons.gsc:280-296`, `waw:…weapons.gsc:376-394`) [V].
  - BO1 applies `useweaponhidetags` to the model and passes the cost into the hint string (`bo1:…:286-291`) [V].
  - Chalk: neither script spawns chalk; it is map art [I]. The BO1 .map sources are stubs, so I can't check.
- **Price:** csv column 1 rounded up to 10, otherwise the script value. Ammo = csv column 2, otherwise round_up_to_ten(cost × 0.5). Same rule in both (`bo1:…:17-55`, `waw:…:16-63`) [V].
- **Upgraded ammo:** 4500 in both (`bo1:…:2026`, `waw:…:2076`) [V].
- **Registration:**
  - WaW registers `_upgraded` weapons as separate entries and refills by name + `_upgraded`.
  - BO1 gives `add_zombie_weapon` an `upgrade_name` field (e.g. `m16_zm` → `m16_gl_upgraded_zm`) and refills that (`bo1:…:179-229, 2046-2049`) [V].
- **Grenades:**
  - WaW sets ammo = cost for grenades (`waw:…:1997-2000`) [V].
  - BO1 does not, but the csv gives `frag_grenade_zm,250,250` (`bo1:mp/zombiemode.csv:134`) [V].
  - BO1 lethal-grenade wall buys replace the player's lethal-grenade slot (`bo1:…weapons.gsc:1993-1997`) [V].
- **BO1 blocks:**
  - It blocks a buy while holding a power-up weapon such as the Death Machine (`:1977-1981`) [V].
  - The weapon limit is 2 primaries, hard-coded (`:1708, 2146`) [V].
- **BO1 weapon toggles:** `magic_box_weapon_toggle` ents limit how many toggle weapons can be active (`:297-523, 1404-1417`) [V].

### 6. Mystery box

| area | WaW | BO1 | profile field |
|---|---|---|---|
| ents | `treasure_chest_use` (targetname); cost `level.zombie_treasure_chest_cost`, default 950 (`waw:…:722-728`) [V] | per-chest `zombie_cost` key, default 950 (`old_cost`) (`bo1:…:625-639`) [V] | `box_cost` |
| start chest | script_noteworthy == `start_chest` exactly (`waw:…:526, 611`) [V] | substring `start_chest`, or random if `level.random_pandora_box_start` (`start_exclude` key) (`bo1:…:655-697`) [V]. `<noteworthy>_rubble` ents show where the box isn't (`:698-726`) [V] | |
| weights | default 1; Der Riese ray gun/monkey weights are in the **level** script (`waw:maps/nazi_zombie_factory.gsc:528-576`) [V]; framework ray-gun func gated on `box_moved` (`waw:…weapons.gsc:103-131`) [V] | framework: default 1; tesla; `default_1st_move_weighting_func` (0 until the first move); `default_upgrade_weapon_weighting_func` (0 until move 2); monkey 3 (r<10), 5 (r≥10), 1 if anyone has one (`bo1:…:57-139`) [V]. Pentagon uses default weights for everything (`bo1:maps/zombie_pentagon.gsc:152-237`) [V] | `box_weight_funcs` |
| limited weapons | count held + in PaP | also counts weapons currently floating in any chest; toggle filter; final `array_randomize` (`bo1:…:1319-1415`) [V] | |
| joker rule | min 4 uses; 4-7 uses 15%; first move forced at ≥ 8; after the first move 30% at 8-12 and 50% at ≥ 13 (`waw:…:1410-1490`) [V] | same thresholds, using `chest_moves` instead of `magic_box_first_move`; skipped when opened during or by a fire sale (`bo1:…:1481-1550`) [V] | |
| refund on move | flat 950 (`waw:…:1493`) [V] | the price actually paid (`user_cost`), not when opened by a fire sale (`bo1:…:868-872`) [V] | |
| take timeout | 12 s (both) (`bo1:…:1290-1295`, `waw:…:1183-1189`) [V] | | |
| fire sale | none | every chest costs 10 and every hidden box shows for 30 s; boxes reset afterwards once closed (`bo1:…_powerups.gsc:856-875, 1374-1434`; `bo1:…weapons.gsc:1206-1231`) [V] | `fire_sale` |
| other | `magic_chest_movable` dvar 1 | same; mutator `noMagicBox` hides all (`bo1:…weapons.gsc:609-618`) [V] | |

### 7. Perks

- **Ents** (both): trigger targetname `zombie_vending`, with script_noteworthy = specialty. The machine model targetname is `vending_<x>`; it goes live on the level notify `<x>_on` and then `<specialty>_power_on`.
  - BO1 machine models: `vending_jugg`, `vending_revive`, `vending_sleight`, `vending_doubletap`, `vending_marathon`, `vending_divetonuke`, `vending_deadshot` (`bo1:maps/_zombiemode_perks.gsc:512-715`) [V].
- **New BO1 perks** are opt-in by level flags `zombiemode_using_marathon_perk` / `_divetonuke_perk` / `_deadshot_perk` (`:59-83`) [V].

| perk | specialty | WaW cost | BO1 cost |
|---|---|---|---|
| Juggernog | armorvest | 2500 | 2500 (`:823`) [V] |
| Quick Revive | quickrevive | 1500 | 1500 co-op, **500 solo** (`:830-835`) [V] |
| Speed Cola | fastreload | 3000 | 3000 (`:841`) [V] |
| Double Tap | rof | 2000 | 2000 (`:846`) [V] |
| Stamin-Up | longersprint | — | 2000 (`:852`) [V] |
| PhD Flopper | flakjacket | — | 2000 (`:858`) [V] |
| Deadshot | deadshot | — | 1500 (`:864`) [V] |
| default | — | 2000 (`waw:…perks.gsc:556-573`) [V] | 2000 (`:45`) [V] |
| Pack-a-Punch | trigger `zombie_vending_upgrade` | 5000 | 5000; 1000 during a bonfire sale (`:349-360`) [V] |

- **BO1 perk cap: 4 per player** (`num_perks >= 4` is denied, `:921`) [V]. WaW has no cap (`waw:…perks.gsc:529-700`) [V].
- **Mule Kick (`specialty_threeprimaries`)** is not functional in this drop [V]:
  - Only stubs exist: the HUD and bottle reuse Speed Cola's, `perk_think` returns early, and the Double Tap power-on also fires its power notify (`:652, 1124, 1179, 1323`).
  - There is no cost case, so it would cost the default 2000. The weapon limit stays 2 (`weapons.gsc:1708`).
  - So the real Mule Kick (Moon) needs a separate source [I].
- **Juggernog health:**
  - WaW: 160, script default, with no csv row (`waw:…perks.gsc:69`, WaW csv) [V].
  - **BO1: 250.** The script default is 160 (`bo1:…perks.gsc:53`), but the column-1 csv row `zombie_perk_juggernaut_health,250` wins (`bo1:mp/zombiemode.csv:59`) [V].
  - The upgrade value is 190, with no csv row. Mutator `susceptible` gives 80/95 (`:46-55`) [V].
  - BO1 applies it with `SetMaxHealth`, and losing it sets the max back to 100 (`give_perk` / `perk_think`, `:1059-1131`) [V].
- **PhD:**
  - Radius 300, damage 1000-5000, as `MOD_GRENADE_SPLASH` (`:63-74, 682-701`) [V].
  - Triggered by fall damage while `divetoprone`; that fall damage is cancelled.
  - Immune to projectile and grenade damage (`bo1:maps/_zombiemode.gsc:3269-3291`) [V].
- **Stamin-Up / Deadshot:** the script only sets the perk or a client flag (`:1059-1080`) [V]. The effects are engine-side [I].
- **Quick Revive solo:**
  - Solo is decided at `all_players_connected` with 1 player, which sets flag `solo_game` (`:767-780`) [V].
  - The machine works **without power** and its model is turned on at once (`:526-551`) [V].
  - Each buy sets `lives = 1` and `solo_lives_given++`. The trigger is hidden until that life is used (`solo_revive_buy_trigger_move`, `:1002-1021, 1071-1078`) [V].
  - **Machine disappearing:** at `solo_lives_given ≥ 3`, flag `solo_revive` is set. After 2 s the machine rises 40 units over 3 s and vibrates; then it is deleted and its clip removed, with ConnectPaths (`revive_solo_fx`, `:568-623`) [V].
  - **Solo QR also sets the default down-pistol to `m1911_upgraded_zm`** (`bo1:maps/_zombiemode.gsc:1820-1823`, called at perks `:778`) [V].
  - It needs a QR machine in the map [I].
- **Perks are lost when downed** in both games (`perk_think` waits on `player_downed`) [V]. Solo QR therefore keeps the life but not the perks [I].

### 8. Points

- **Same in both:**
  - Kill 50; bonuses melee 80, head 50, neck 20, torso 10, burn 10.
  - Penalties: downed 5%, no-revive 10%, died 0%.
  - Start score 500 on MEDIUM (`bo1:mp/zombiemode.csv:25-28`) [V].
- **Hit points:**
  - WaW: 5 base, rounded up to 10, so 10 (`waw:…_zombiemode_score.gsc:41-64`) [V].
  - **BO1: base 10** (`zombie_score_damage_normal` / `_light`, both 10, csv:47-48), rounded up to **5** (`bo1:maps/_zombiemode_score.gsc:64-73, 95`) [V]. Still 10 a hit.
  - BO1 "light" hits come from non-semi-auto weapons (`bo1:…spawner.gsc:2920-2928`) [V]; same value.
  - BO1 ADS points only happen on the flame path (`:3074-3079`) [V].
- **Rounding:**
  - WaW rounds to 10. BO1 rounds the event to 5 before the ×multiplier (`score.gsc:95`) [V].
  - Penalties still round to 10 in BO1 (`:215`) [V].
- **Double points:**
  - Both use `zombie_point_scalar` = 2 for 30 s.
  - BO1 also applies it to nuke (400) and carpenter (200), because they go through `player_add_points` (`bo1:…powerups.gsc:948, 1127`) [V].
  - WaW adds those raw, so they are never doubled (`waw:…powerups.gsc:826, 1072`) [V].
  - Mutator `doubleMoney` doubles again (`score.gsc:103-111`) [V].
- **Team pool (BO1):** a co-op kill also adds team points (30/35/45 for 4/3/2 players in the script). The csv column 1 sets them to 0 (csv:42-45, `_zombiemode.gsc:502-505`) [V]. So it is inert on stock [I].
- **New BO1 events:**
  - `reviver`: the reviver gets the points the downed player lost (`bo1:maps/_zombiemode.gsc:1342-1365`, `score.gsc:204-209`) [V].
  - `ballistic_knife_death` = kill + melee bonus.
  - `thundergun_fling`.

### 9. Last stand

| area | WaW | BO1 | profile field |
|---|---|---|---|
| bleed-out | the scripts never set the dvar, so the engine default applies (not found) [I] | `player_lastStandBleedoutTime` 45 (`bo1:maps/_zombiemode.gsc:543`) [V] | `bleedout_s` |
| revive radius | 60 (`waw:…_zombiemode.gsc:595`) [V] | 75 (`bo1:…:542`) [V] | |
| revive time | 3 s, halved with QR (`waw:maps/_laststand.gsc:633-637`) [V] | same (`bo1:maps/_laststand.gsc:519-522`) [V] | |
| pistol | best pistol owned, else `colt`, with ammo stock = 2 clips (`waw:…_zombiemode.gsc:118`, `_laststand.gsc:300-322`) [V] | best owned by a rank list (m1911 < cz75 < cz75dw < python < upgraded … < ray gun < freeze gun upgraded), else `m1911_zm` co-op / `m1911_upgraded_zm` solo; m1911 gets 2 clips of stock, other guns use their stored ammo (`bo1:…:440, 1556-1680`) [V] | `laststand_pistol`, `pistol_rank[]` |
| solo down | **no solo revive**: lethal damage means fake death, then `end_game` (`waw:…:2646-2653`) [V] | with a QR life: goes down normally, auto-revives after **10 s** (`wait_and_revive`), lives−1. Without one: end game (`bo1:…:3341-3369, 3403-3440`) [V] | `solo_revive` |
| zombie hit | engine melee, 60 (Nacht doc) | the script replaces the hit with the AI's `meleeDamage`, which normal zombies set to **60** at spawn (`bo1:maps/_zombiemode_spawner.gsc:166`); **50** is only the fallback (`bo1:…:3213-3227`) [V]. So 2 hits down at 100, 5 with Jugg 250 [I]. See `zombie_movement_t4_t5.md` T5 §4 | `zombie_hit_dmg` |
| falling | converted to explosive, capped at 75 while health > 75 (`waw:…:2578-2612`) [V] | not converted; explosives still capped at 75 (`bo1:…:3279-3291`) [V] | |
| anti-stuck | — | two players within 18 units (2D) and 60 (vertical) both take 1000 damage, checked every 0.5 s from 5 s (`bo1:maps/_zombiemode_spawner.gsc:21-90`) [V] | `player_overlap_kill` |

### 10. Power-ups

- **The list:**
  - WaW (Der Riese): nuke, insta_kill, double_points, full_ammo, carpenter (`waw:…powerups.gsc:49-54`) [V].
  - BO1 framework adds fire_sale, bonfire_sale, all_revive, free_perk, plus minigun/tesla by map. A map must `include_powerup` each one (`bo1:…powerups.gsc:53-76, 418-429`; pentagon `:244-257`) [V].
- **Normal-drop filter** (`get_valid_powerup`, `:266-324`) [V]:

| power-up | when it can drop normally |
|---|---|
| carpenter | only if at least 5 windows are fully destroyed (same as WaW) |
| fire_sale | only if the box has moved at least once and no fire sale is active |
| all_revive | only if someone is downed |
| minigun | not while anyone has one; before power, only in solo after a QR life has been bought (`:325-352`) |
| bonfire_sale, free_perk, tesla | never; specific or scripted drops only |

- **Drop rules:** the same as WaW, at the same numbers [V]:
  - First threshold: players × start score + 2000; increment ×1.14 each time.
  - 3% random drop regardless of the threshold.
  - Max 4 per round. Spawns 40 units above the death origin. Pickup radius 64.
  - BO1 also rolls back the per-round count when a drop is invalid (`:478-482`) [V].
- **Valid area:**
  - WaW: `playable_area` (targetname).
  - **BO1: `player_volume` (script_noteworthy)** (`bo1:…:466`, `waw:…:483`) [V].
- **Durations:**
  - Insta-kill, double points, fire sale and bonfire sale all last 30 s (`:865, 885, 1164-1165, 1200`) [V].
  - Lifetime on the ground: 15 s, then 40 blinks; same as WaW (`:1031-1061`) [V].
- **Carpenter:**
  - WaW repairs window by window, nearest first.
  - BO1's default `start_carpenter_new` repairs every window farther than 750 units from all players **instantly**, and repairs near windows board by board (up to 20 checks each). It pays 200 (doubled under double points) (`:49, 1914-2048`) [V].
- **Nuke:** 400 points to each player, plus team points (`:1062-1129`) [V].
- **Special drop** (`special_drop_setup`):
  - It is called only by map scripts.
  - Above round 10 it can become "nothing" or a dog. Above round 15 the "nothing" chance is (r−15)×5%.
  - Dog drops happen from round 15. Max ammo can turn into a random power-up (`:585-689`) [V].

### 11. Dogs

- **Both frameworks include dogs:**
  - WaW `_zombiemode_dogs` is called from main (`waw:…_zombiemode.gsc:67`) [V].
  - BO1 moved them to `_zombiemode_ai_dogs`. A map opts in via `level.custom_ai_type` (`bo1:maps/_zombiemode.gsc:105-110`, pentagon `:26-31`) [V].
- **Numbers are unchanged** [V]:
  - Dog rounds: first in rounds 5-7, then every 4-5 rounds.
  - Count: players × 6 for the first two dog rounds, then × 8.
  - Health: 400, 900, 1300, then 1600 cap.
  - Spawners: `zombie_dog_spawner` (script_noteworthy) / `zombie_spawner_dog_init` (`bo1:maps/_zombiemode_ai_dogs.gsc:56-113, 300-355`, `waw:…_zombiemode_dogs.gsc:78-149, 443-493`).
- **Mixed-round dog chance** inside normal rounds (r > 15, > 20, > 25, > 30) is identical (`bo1:…_zombiemode.gsc:2195-2249`) [V].
- BO1 adds framework AI types (quad, ape, thief, boss) as opt-in modules (file list) [V].

### 12. Other core changes

- **Mutators:** `level.mutators[...]` (noBoards, noPerks, noMagicBox, noPowerups, doubleMoney, friendlyFire, susceptible, fogMatch, …) gate framework systems (`bo1:maps/_zombiemode.gsc:548+`) [V]. Default off [I].
- **Difficulty columns** (EASY/HARD/VETERAN, csv) [V]:
  - Start score.
  - `starting_lives`: 0 on MEDIUM, 10 on VET.
  - `game_start_delay`.
  - Penalties.
  - Zombie health.
- **Lethal grenade per player:** `get_player_lethal_grenade` replaces the hard-coded `stielhandgranate` (`bo1:…:2353-2360, 2745-2771`) [V].
- **Sprint / dive-to-prone:** BO1 gameplay; there is no framework script for it except PhD's `divetoprone` check [I].
- **Freeze gun and placeable mines** never hurt players (`bo1:…:3259-3262`) [V].

### Couldn't verify

- **No BO1 theater files to read:** `zombie_theater.gsc` is absent from raw/, and every BO1 zombie `.map` is a blank stub. So I couldn't check theater ents (spawner, riser, door names, chalk).
- **WaW last-stand bleed-out:** the scripts never set it; the engine default needs RE.
- **Mule Kick:** not functional in these BO1 tools; needs another source (Moon).
- **Stamin-Up and Deadshot effects:** engine-side.
- **Fire sale and bonfire timers:** the 30 s are script values; the HUD timers weren't checked.
- Whether BO1's `round_up_score(…, 5)` ever changes a payout on stock values: none of the stock values I read produce a multiple of 5 that isn't also a multiple of 10 [I].
