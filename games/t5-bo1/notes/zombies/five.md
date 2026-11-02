# BO1 "Five" (zombie_pentagon): elevators, thief, DEFCON pack-a-punch

Behaviour of the map's own systems, for native zombies. Doc only.

Tags: [V] read in script, [M] measured, [I] inferred, [U] unknown. Paths are BO1 `raw/maps/`. Values and line refs only, no script text.

Files: `zombie_pentagon.gsc` (main, bonfire hook :447-503), `zombie_pentagon_elevators.gsc`, `zombie_pentagon_teleporter.gsc` (portals and DEFCON), `_zombiemode_ai_thief.gsc`. Wiring: elevators init :56, DEFCON init :59, teleporters :296, `level.bonfire_init_func` :71. Custom AI: dogs, quads and the thief (:26-31). Dogs are loaded but no dog rounds are enabled [V].

## Floors

- There are three floors, set by trigger volumes `thief_floor_1/2/3` (targetname). 1 is the top (offices), 2 the war room, 3 the labs, 0 outside all of them [V thief :1349-1367; I for the names, from zone names].
- Everything uses the floor number: elevator zombie moves, the thief, vision changes (`change_pentagon_vision`, client `vis1..3`; thief rounds force `vis4`) [V].

## 1. Elevators

Two lifts, both bought for 250 points [V elevators :20, :26].

| | elevator1 | elevator2 |
|---|---|---|
| route | floor 2 to 3 (war room to labs) [I from the vox] | floor 1 to 2 [I] |
| travel | 201 units down from its start [V :25] | 320 units down [V :31] |
| move time | 5 s, MoveTo with no accel [V :334, :355] | 5 s |
| first ride down sets | flag `labs_enabled` [V :340-342] | flag `war_room_start` [V :343-346] |
| arrival vox | up `zmb_vox_pentann_level_2`, down `_level_3` [V :376-383] | up `_level_1`, down `_level_2`; loops `mus_elevator_muzak` [V :47, :364-371] |

Entities, by targetname / script_noteworthy [V :18-160, :821-860]:
- the lift `elevatorN`; its pieces are linked through `.target`;
- buy trigger: noteworthy `elevatorN_buy` (look-at required);
- call boxes: targetname `elevatorN_call_box`, each with a noteworthy station `elevatorN_up` / `_down`;
- door-safety volumes: noteworthy `elevatorN_safety`;
- rider volumes: `elevatorN_up_riders` / `_down_riders`;
- the inside volume `elevatorN_zombie_cleanup`;
- doors: elevator1 has `elevator1_doors_up/down` plus outer doors; elevator2 has `elevator2_doors` plus outer doors. Each door moves by its script_vector.

Using a lift [V :72-120, :195-252]:
- **Buy** (inside): needs 250 points, a valid player, not standing in a revive trigger, the safety volumes clear and no thief round on. Otherwise it plays `no_purchase`, and the hint flashes "blocked" or the pack-room text for 1 s.
- **Call box**: free. It works only when the lift is at the other station and idle, under the same blocked / thief-round checks.
- While it moves, buys and call boxes are disabled and re-enabled 0.1 s after arrival.

During the move [V :317-398]:
1. Doors close, and normal zombie spawning stops (flag `spawn_zombies` cleared) until arrival.
2. Corpses inside are cleaned up. elevator1 also swaps the zombie spawn closets between labs and war room (flags `no_labs_elevator_spawning` / `no_warroom_elevator_spawning`, :400-428). Zombies standing in the closet it leaves are killed and refunded to `zombie_total`.
3. Zombies come along [V :446-682]. Zombies on the riders' floor (not thieves, not inside the lift, not already teleporting) are moved:
   - up to 6 to the destination's `elevatorN_up_zombie` / `_down_zombie` structs (`forceteleport`). Solo, fewer go: from slot 6 (none) at round ≤5, slot 5 (one) at rounds 6-9, slot 3 (three) at round ≥10. In co-op, if someone is already on the next floor, none are placed at the doors;
   - up to 6 more to the `_up_hidden` / `_down_hidden` structs with a 0..22 unit jitter. Full-health ones are deleted and refunded instead;
   - the rest go through a floor portal, or are deleted and refunded.
   - This only runs when every player on that floor is riding. With a downed co-op player left behind, zombies are pulled from around them instead (:683-742).
4. On arrival it sets `elevator_grounded` and `spawn_zombies`, opens the doors, and 2 s later rechecks for empty floors [V :385-398].

## 2. Teleporters

- Pads are `portal_trigs` (targetname); each pad's script_noteworthy is its zone [V teleporter :24-33]. Their screens open on power (:641-676).
- Use: freeze 1 frame, go to the pad's `player_pos` struct (+49 prone, +20 crouch), stepping back 32 units if a player is within 18. Controls return after 0.5 s [V :333-450].
- Destination: random among the enabled zones' pads, never the same pad and never the pack room (`conference_level2`) [V :473-529].
  - The power room pad (script_string `power_room_portal`) goes only to war_room_zone_north or conference_level1 [V :481-499].
- Cooldown: you can't come back through the pad you arrived at for 20 s, or until DEFCON goes active [V :319-332].
- Zombies near the user follow through the portal (`no_zombie_left_behind`, :696-742).
- Sounds: `evt_teleporter_out`, then `evt_teleporter_go`. Fx: `transporter_start` / `transporter_beam` [V].

## 3. DEFCON pack-a-punch

Machine: trigger `zombie_vending_upgrade`, which links to the turntable `pack_hideaway` [V :34-50].

Switches [V :802-915]:
- Switches are `punch_switch` (targetname); they need power.
- Each switch's `.target` holds a bulb (noteworthy `defcon_bulb`) and a handle (`defcon_handle`, pitched −180 over 0.5 s, sound `zmb_defcon_switch`).
- `level.defcon_level` starts at 1. Each pull raises it by one (DEFCON 2, 3, 4). The announcer says `zmb_vox_pentann_defcon_<n>` unless a bonfire sale is on.
- The 4th pull sets 5. It sets the flag `defcon_active`, plays the alarms (structs `defcon_alarms`) and switches the portal fx to the pack colour. [I: with four switches, any order works; each switch can be pulled once until the reset.]
- Signs: `defcon_sign` models `p_zom_pent_defcon_sign_01..05`, indexed by the level [V :933-957].

While `defcon_active` [V :351-362, :958-1011]:
- Any pad except the pack room's sends the player to the pack room. The first such teleport starts the countdown.
  - On the first activation, war_room_entry or war_room_special is set (depending on whether the war room's south zone is open).
  - The turntable then opens: a 180° yaw over 2.5 s, with `evt_packapunch_revolve_start` / `_loop` / `_end`.
- Countdown: 30 s, stepping down one DEFCON level every 7.5 s. When it hits 1, `defcon_active` is cleared, the normal portal fx return and `defcon_reset` is sent.
- While the level is ≥3, zombies don't spawn in the pack room (`no_pack_room_spawning`, :1012-1023).
- If every player teleported in, zombies are drawn to POI `pack_room_poi1` (south war-room zone open) or `pack_room_poi2` (:1042-1074). Both POIs are 30 units with 4 attractors at 45 [V :15-22].
- The machine stays usable for 40 s after the turntable opens, then waits until any pack in progress finishes and turns away [V :62-107].

Leaving [V :109-181, :182-216]:
- The door `pack_room_door` opens on `defcon_reset` / `player_in_pack` while the pack room is occupied, if the war room's south zone is enabled (1 s open, 0.25 s close).
- The room counts as clear when no player is touching `slam_pack_door`, the conference_level2 zone is empty, and, in a thief round, no thief is inside.
- Leftover zombies are deleted and refunded, or sent out by portal (:252-286).
- After that, `pack_room_reset` sets the switches back to green and plays `zmb_vox_pentann_defcon_reset`.

Bonfire sale [V zombie_pentagon.gsc:447-503]: if DEFCON isn't active, the sale pulls all switches itself (0.5 s apart) without the vox. The countdown starts straight away if someone is in the pack room. If the countdown is already running, it's refilled (30 s, level 5).

## 4. The pentagon thief

Round schedule [V thief :350-382]:
- After power-on, the first thief round is 1..3 rounds later (randomintrange(1,4)). Then every 4..5 rounds.
- It swaps in its own round spawn/wait functions: 1 thief, a 7 s intro, and 6 s after it's gone [V :301-348].
- Start: flag `thief_round`, vox `zmb_vox_pentann_thiefstart`, alarms after 7 s, music `dog_start`, vision `vis4` for everyone [V :383-409].
- During a thief round the elevators refuse to run [V elevators :92-99, :216-222].

Health [V :484-499, :515-523]:
- round × 2000, capped at 60000.
- Then scaled by players: 4 = ×1, 3 = ×0.8, 2 = ×0.6, 1 = ×0.3.
- The `scr_thief_health_*` dvars are set at :14-28 but never read for this. `thief_adjust_health` is never called [V grep].
- Claymores add round × 50..99 bonus damage (:1739-1754). A nuke kills it outright (:1755-1762).

Behaviour [V :501-560, :1006-1118, :1262-1303]:
- Spawns at the `thief_zombie_spawner` farthest from the players (:469-585). Fx `ape_spawn` plus sound `zmb_bolt`; trail fx `tech_trail`.
- It visits every player once, in random order.
  - Each victim: it portals to that player's floor, then stalks at a walk. Being hit makes it chase (run2). Once the hits during the chase reach 15% of its max health, it sprints.
- At 64 units it grabs (anim `ai_zombie_tech_grab`) and steals a weapon [V :735-805]:
  - It takes the current weapon. If the player is holding an offhand, knife, perk bottle or nothing, or is downed, it takes a random primary instead.
  - An attachment is stolen as its base weapon. The death machine is just removed.
- Then the victim is teleported to the struct whose script_noteworthy is `player_pos` and script_string is `thief_player_pos`. The thief goes to `thief_start`, and the victim's power-room pad gets the 20 s cooldown [V :1368-1431].
- Freeze gun damage doesn't count toward its speed changes, and the freeze gun slows it one step [V :1722-1738].

Escape [V :1486-1584]:
- After the last victim it goes to floor 3 and runs through 4 bottom-floor portals in a fixed order: index 3, 2, 1, 0, each time coming out of a random other portal. One light (client notify `por<n>`) goes off per hop.
- Then it exits through the power room portal.
  - On escape: max ammo at `thief_start`, vox `zmb_vox_pentann_thiefend_bad`, and the stolen weapons are lost [I: thief_return_loot only runs on death].
  - In escape mode, more than 2000 damage (`scr_thief_speed_damage`) slows it one step (run2 → run → walk) [V :1595-1636].

Death [V :631-697]:
- Max ammo drops 32 units behind it.
- If it dies before stealing anything: bonfire sale, unless insta-kill was active when it was hit (:1299-1300); the trap achievement goes to whoever damaged it.
- Otherwise: fire sale.
- The stolen weapons go back (`thief_return_loot` :806-857): a weapon is given back with its pack options, replacing the current one if the player already has 2 primaries.
- Vox `zmb_vox_pentann_thiefend_good`, music `dog_end`.

Unknown: thief anim lengths and speeds, the spawner placement, the lab shutters' thief-round behaviour (`zombie_pentagon.gsc`:520-550, not traced), the traps' effect on the thief (`zombie_pentagon_traps.gsc`, `thief_trap_watcher` :424-468) [U].
