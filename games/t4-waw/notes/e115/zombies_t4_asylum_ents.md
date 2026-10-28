# Zombies: Verrückt (`nazi_zombie_asylum`) ent checklist for M3

A per-ent checklist for the native route. It covers everything Verrückt's ents hold beyond Nacht's set, with counts, the
keys to read, and a suggested profile field for each. The behaviour behind each item is in `zombies_t4_later_maps.md`,
which this doc points to instead of repeating.

Tags:
- **[V]**: read. `ents:N` is the line of the ent's opening brace in the zone dump's `maps/nazi_zombie_asylum.d3dbsp.ents`.
  `asy:` is the map script `maps/nazi_zombie_asylum.gsc`, and `zm:`/`perks:`/`spawner:`/`weapons:` are Verrückt's own
  `_zombiemode*.gsc` copies.
- **[M]**: counted by script over the parsed ents (2746 ents; Nacht has 1037).
- **[I]**: inferred.

**Which scripts ship [V].** The patch fork applies here too: `patch.ff` replaces the zone's `nazi_zombie_asylum.gsc`
with a copy whose only changes are calls into `_zombiemode_asylum` / `_zombiemode_spawner_asylum`. Those forks add
`SetAILimit(24)` and the newer breadcrumbs, as on Nacht (`zombies_t4_nacht_ai.md` §1 "Chase"). Every map-script line
cited below is the same in both copies (diffed). The ents are only in the zone.

**Generic or Asylum-only?** "T4" means the same ent pattern and keys appear on Shi No Numa and/or Der Riese, so the
field belongs in the T4 `GameProfile`. "AS" means only Verrückt uses it, so it belongs in a per-map override.

---

## 0. Summary

| # | kind | ents [M] | scope | profile field (suggested) | behaviour doc |
|---|---|---|---|---|---|
| 1 | perk machines | 4 triggers, 4 machines, 4 jingle structs | T4 | `perks.*` | later_maps "perk machines" §1-2 |
| 2 | power switch | 1 trigger, 1 lever, 1 FX struct | T4 (exists as `uses.powerSwitch`) | `power.*` | later_maps §3.1 |
| 3 | electric doors | 2 triggers, 1 door group | T4 (exists as `uses.electricDoor`) | `uses.electricDoor` | later_maps §3.1, §6 |
| 4 | electric traps | 2 buy triggers, 2 damage triggers, 13 FX structs, 2 handles, 2 boxes, 4 lights | T4 | `traps.*` | later_maps "traps" §1 |
| 5 | split spawn | 8 start structs, two rooms | AS | `starts.split*` | §5 here |
| 6 | Bouncing Betty buys | 2 triggers, 2 models | T4 | `betty.*` | later_maps §6.4 |
| 7 | moving box | 5 chests, 5 lids, 5 bases, 5 weapon origins, rubble | T4 | `box.*` | later_maps "mystery box" §4 |
| 8 | zones | 7 `info_volume`s | AS (Verrückt's first-version zones) | `zones.*` override | later_maps §4.3 |
| 9 | risers | 32 rise structs, 25 riser spawners | T4 | `risers.*` | §9 here |
| 10 | door flags, slide doors | 19 door/debris triggers | T4 | `blockers.*` (exists) | later_maps §6 |
| 11 | extras | waterfalls, fog/vision, toilet, chair, anti-exploit, hidden MG | AS | per-map | §11 here |
| - | zipline, flogger, dogs, PaP, teleporters | **none** [V] | - | - | - |

**Confirmed absent [V]:** Verrückt's ents have no zipline, flogger or pendulum, PaP (`zombie_vending_upgrade`),
teleporter or dog spawner (`actor_zombie_dog`). The ents have no `zipline` or `flogger` name, and no map script refers
to one. The only `actor_` class is `actor_axis_zombie_ger_ber_sshonor` (82 spawners) [M].

---

## 1. Perk machines (T4)

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| buy trigger | `trigger_use` | `zombie_vending` | `script_noteworthy` = specialty; `target` = machine | 4 | 12321, 12344, 14381, 14395 |
| machine | `script_model` | `vending_jugg` / `_revive` / `_sleight` / `_doubletap` | `model` = off model `zombie_vending_<x>` | 4 | 12329, 12352, 14374, 14403 |
| jingle point | `script_struct` | `perksacola` | `script_sound` = `mx_jugger_jingle` / `mx_revive_jingle` / `mx_speed_jingle` / `mx_doubletap_jingle` | 4 | 12337, 12360, 14389, 14411 |
| rattle bumps | `trigger_multiple` | `audio_bump_trigger` | `script_sound` | 45 (all kinds, not only perks) | - |

Per perk [V, ents + perks: per later_maps §1.1, §2]:

| perk | `script_noteworthy` | machine | on model | cost | sting | drink vox |
|---|---|---|---|---|---|---|
| Juggernog | `specialty_armorvest` | `vending_jugg` | `zombie_vending_jugg_on` | 2500 | `mx_jugger_sting` | `plr_<n>_vox_drink_jugga` |
| Quick Revive | `specialty_quickrevive` | `vending_revive` | `zombie_vending_revive_on` | 1500 | `mx_revive_sting` | `_revive` |
| Speed Cola | `specialty_fastreload` | `vending_sleight` | `zombie_vending_sleight_on` | 3000 | `mx_speed_sting` | `_speed` |
| Double Tap | `specialty_rof` | `vending_doubletap` | `zombie_vending_doubletap_on` | 2000 | `mx_doubletap_sting` | `_double` |

- **The cost isn't an ent key** [V]. No `zombie_vending` ent has `zombie_cost`; the price is per specialty in script
  (perks.gsc :241-254). The profile needs a specialty → cost table.
- **Other sounds:** `bottle_dispense3d` on buy, `deny` on a refused buy, the `perks_machine_loop` hum,
  `electrical_surge`, and `broken_random_jingle` (Revive only) [V, later_maps §2.2, §2.4].
- **Bottle weapons:** `zombie_perk_bottle_jugg` / `_revive` / `_sleight` / `_doubletap` [V].
- **Arming:** each trigger waits for the level notify `<specialty>_power_on` (later_maps §2.2).

Suggested fields:
- `perks.triggerTargetname = "zombie_vending"`
- `perks.specialtyKey = "script_noteworthy"`
- `perks.machineKey = "target"`
- `perks.jingleTargetname = "perksacola"`
- `perks.jingleSoundKey = "script_sound"`
- `perks.onModelSuffix = "_on"`
- `perks.costs` (specialty → int)
- `perks.chargeAfterDrink = true`: AS and SU charge after the drink; FA charges before it. Per-map.
- `perks.juggRegenTick = 40 / 0.5 s`: AS and SU. Per-map.
- `perks.jingleInterval = 60-120 s`: AS. Per-map.

## 2. Power switch (T4)

| role | classname | targetname | keys | ents |
|---|---|---|---|---|
| trigger | `trigger_use` | `use_master_switch` | none (no cost) | 10384 |
| lever | `script_model` | `master_switch` | `model` `zombie_power_lever_handle` | 12755 |
| spark point | `script_struct` | `switch_fx` | - | 10448 |
| generator models | `script_model` | `zombie_generator` | `spawnflags` 2 | 892, 900 |

- **On use** [V asy:1551-1709; later_maps §3.1]:
  - The lever rotates roll −90 over 0.3 s.
  - The level gets **flag `electric_switch_used`** and the notify `switch_flipped`. The jingles start on
    `master_switch_activated`.
  - The perks arm **6 s later** (`juggernog_on` etc.).
  - The electric doors open, and the traps become usable.
- **Hard-coded positions [V]:** the generator idle FX is at a fixed origin (−674.9, −300.5, 284.1), not an ent
  (later_maps §3.1).
- **Lights:** 14 `elect_light_model` script_models (`lights_tinhatlamp_*`, `lights_indlight_*`) and 14 `light` ents
  named `elect_light` [M]. They switch on with the power (later_maps §3.1). Two of the lamp models carry
  `script_noteworthy` `<chest>_model` (ents:555, :564); those drive the box-location lights (`magic_box_light`,
  asy:2295) [V for the names, I for the link].

Suggested fields: these already exist as `uses.powerSwitch` = {`use_master_switch`, `use_power_switch`}. Add:
- `power.leverTargetname = "master_switch"`
- `power.leverRoll = -90`, `power.leverTime = 0.3`
- `power.flag = "electric_switch_used"`: AS only; Der Riese uses `electricity_on`. Per-map.
- `power.perkDelay = 6`: AS. Per-map.
- `power.lightTargetname = "elect_light_model"`: AS.

## 3. Electric doors (T4)

| classname | targetname | keys | count | ents |
|---|---|---|---|---|
| `trigger_use` | `zombie_door` | `script_noteworthy` `electric_door`; `zombie_cost` 750; `target` `auto180` | 2 | 8307, 12726 |
| `script_model` | `auto180` | `script_string` `slide_apart`; `script_vector` ±90 0 0; `model` `prefab_berlin_asylum_dbldoor_dr`; `target` → spawners `auto202` / `auto204` | 2 | 14418, 14430 |
| `script_brushmodel` | `auto180` | `script_noteworthy` `clip` | 2 | 14442, 14450 |

- **The 750 cost is never charged.** The `electric_door` noteworthy makes the door unbuyable. The power opens it for free
  (later_maps §3.1, §6) [V].
- **The door's `target` also names spawners** (`auto202` ×2, `auto204` ×1) [M]. Those spawners go live when the power
  opens the door [I: the standard door → spawner rule].
- The field already exists: `uses.electricDoor = "electric_door"`. Also needed is the **`slide_apart` door type**: each
  piece moves by its `script_vector` with 25% ease (later_maps §6) [V]. Suggested `blockers.slideKey = "script_string"`,
  `blockers.slideValue = "slide_apart"`, `blockers.slideVectorKey = "script_vector"`.

### All door and debris triggers [M]

19 in all. Two triggers per flag, except one unflagged door:

| type | `script_noteworthy` | `zombie_cost` | `script_flag` |
|---|---|---|---|
| door | `north_lower_door` | 750 | `north_door1` |
| door | `north_lower_door` | 1000 | `north_upstairs_blocker` |
| debris | `south_upstairs_debris` | 1000 | `south_upstairs_blocker` |
| door | - | 750 | `south_access_1` |
| door | - | 1000 | `upstairs_north_door2` |
| door | `magic_door` | 750 | `magic_box_south` |
| door | `magic_door` | 750 | `magic_box_north` |
| door | `north_upper_door1` | 750 | `upstairs_north_door1` |
| door | `electric_door` | 750 (never charged) | - |
| door | - | 750 | - (×1) |

The flags feed the zones (§8) and the box (§7). The noteworthies `north_lower_door`, `south_upstairs_debris` and
`magic_door` gate locked spawners and goals (asy:297-300, later_maps §6) [V].

## 4. Electric traps (T4)

Full behaviour, numbers and ent indices are in later_maps "traps" §1. This is the checklist:

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| buy trigger | `trigger_use` | `gas_access` | `script_noteworthy` `north_gas_valves` / `south_gas_valves`; `script_string` `north` / `south`; `script_linkto` `4` / `3`; `target` `auto246` / `auto242` | 2 | 10133, 10123 |
| damage volume | `trigger_multiple` | `auto246` / `auto242` | `spawnflags` 1 | 2 | 10116, 10109 |
| FX points | `script_struct` | `auto246` / `auto242` | some carry `script_sound` `fire_med` (any value enables the per-point sounds) | **6 north, 7 south** | 10058-10103, 10416-10441 |
| switch handle | `script_model` | - | `script_linkname` `4` / `3`; `model` `zombie_zapper_handle` | 2 | 14712, 14719 |
| power box | `script_model` | `zap_machine_north` / `_south` | `model` `zombie_zapper_power_box` (→ `_on`) | 2 | 630, 652 |
| cage lights | `script_model` | `zapper_light_north` / `_south` | `model` `zombie_zapper_cagelight` (→ `_red` / `_green`) | 2 + 2 | 638-667 |
| wall-switch FX | `script_struct` | `zapper_switch_fx_north` / `_south` | - | 2 | 12651, 14343 |
| alarm | `script_struct` | `loudspeaker` | plays `warning` when ready | 1 | 14706 |

- **Numbers** (later_maps traps §1.1) [V]:
  - Cost 1000, **not an ent key**.
  - Active 25 s, cooldown 25 s.
  - Power needed.
  - Zombies die at health + 666. Players without Jugg are killed; with Jugg they take 50.
- **Correction:** later_maps §1.5 says "6 each" FX structs. The south trap (`auto242`) has **7** [M].
- **Client FX:** the server sends a client notify named after the damage trigger's targetname, plus `north` / `south`
  for the box and wall FX (later_maps §1.3).

Suggested fields:
- `traps.triggerTargetname = "gas_access"`: AS. SU uses `elec_trap_trig`; FA uses one per trap. Per-map list.
- `traps.damageKey = "target"`: T4. The damage volume and FX structs share that name.
- `traps.handleLinkKey = "script_linkto"` → `script_linkname`: T4.
- `traps.sideKey = "script_string"`: T4.
- `traps.cost = 1000`, `traps.active = 25`, `traps.cooldown = 25` (SU 90): per-map.
- `traps.gate = power`: AS.
- `traps.lightNames`: AS table `zapper_light_<side>`.
- `traps.alarmTargetname = "loudspeaker"`: AS.

## 5. Split spawn: two start rooms (AS)

| classname | targetname | `script_noteworthy` | count | ents |
|---|---|---|---|---|
| `script_struct` | `initial_spawn_points` | `north_spawn` | 4 | 2324, 2331, 10153, 10160 |
| `script_struct` | `initial_spawn_points` | `south_spawn` | 4 | 2338, 2345, 10167, 10174 |

**Rule** (`spawn_point_override`, asy:1339-1385) [V]:
1. The map sets flag `spawn_point_override` at init (asy:266). That makes the generic placement (`coop_player_spawn_placement`,
   zm:2431-2449, which puts player *i* on struct *i*) return early.
2. **Pick the sides:** side 1 is north, side 2 south. With `randomint(100) > 50` (49%), they swap.
3. **Place the players:**
   - Players 0 and 1 go to side 1's structs [0] and [1].
   - Players 2 and 3 go to side 2's structs **[2] and [3]**, because the index isn't reset [V].
   - Each player stores `respawn_point` and `spawn_side`.
4. **Solo:** always side 1's struct [0]. So a solo player starts north 51% of the time, south 49%.
5. **Respawn:** a co-op respawn (`spectator_respawn_new`, asy:2405) spawns the player at their own `respawn_point`,
   +10 z [V].

- Struct order is the ents order within each `getstructarray` result [I: engine order]. The two halves of each side
  sit in different parts of the ents file (lines ~2330 and ~10160).
- Per-player setup threads also start here: `player_zombie_awareness`, `player_killstreak_timer` and `fix_hax` (§11).
- **The zones depend on the spawn side.** The two rooms are the `north_spawners` and `south_spawners` volumes. Only the
  side with players feeds spawners (later_maps §4.3).

Suggested fields (AS override):
- `starts.splitKey = "script_noteworthy"`
- `starts.splitSides = {"north_spawn", "south_spawn"}`
- `starts.swapChance = 49`
- `starts.perSide = 2`
- `starts.secondSideOffset = 2` (keeps the index quirk)

The `StartRule` list already handles `initial_spawn_points` [I: the T4 default]. This only changes which struct each
player gets.

## 6. Bouncing Betty buys (T4)

| role | classname | targetname | keys | count | ents |
|---|---|---|---|---|---|
| buy | `trigger_use` | `betty_purchase` | `zombie_cost` **500 (ignored)**; `target` → model | 2 | 10244, 10252 |
| wall model | `script_model` | `auto252` / `auto253` | `model` `weapon_bbetty_mine` | 2 | 14465, 12367 |

Rule [V asy:711-895; later_maps §6.4]:
- **Cost 1000.** The script overwrites the ent's 500 (asy:719). It's once per player: after buying, the triggers turn
  invisible to that player.
- **Gives** `mine_bouncing_betty` in action slot 4 with stock 5 (asy:815-817). Each round end tops the clip up to 2 for
  every owner (asy:878-893).
- **Fuse:** 2 s after landing, it spawns a `trigger_radius` (spawnflags 9, radius 80, height 64) (asy:828-830).
  [I] Flags 9 = AI-triggered only.
  - When triggered: the `betty_activated` sound, a hop of 32 up over 0.2 s, and the `betty_explode` FX (asy:843-845).
  - Then every zombie within **200 units (3D)** takes `MOD_EXPLOSIVE` damage (asy:852-855).
- **Damage:** Verrückt's `MOD_EXPLOSIVE` branch is round × randint(100, 500) (spawner:1781-1790) [V].
- Hint strings: `ZOMBIE_BETTY_PURCHASE`, `ZOMBIE_BETTY_HOWTO`, `ZOMBIE_BETTY_ALREADY_PURCHASED`.

Suggested fields:
- `betty.triggerTargetname = "betty_purchase"`: T4.
- `betty.costOverride = 1000`: T4. All three maps override 500.
- `betty.stock = 5`, `betty.refill = 2`
- `betty.radius = 200`, `betty.heightLimit`: none on AS, ±80 on SU. Per-map.

## 7. Moving box (T4)

| role | classname | targetname | keys | count |
|---|---|---|---|---|
| chest trigger | `trigger_use` | `treasure_chest_use` | `script_noteworthy` = location; `zombie_cost` 950; `target` `magic_box_lid_N`; `hintstring` | 5 |
| lid / base / weapon origin | `script_model` / `script_model` / `script_origin` | `magic_box_lid_N` / `_base_N` / `_weapon_spawn_N` | N = 0, 1, 2, 4, 5 (no 3) | 5 each |
| clips | `script_brushmodel` | `magic_box_clip_0`, `_1` | - | 2 |
| rubble | by `script_noteworthy` `<location>_rubble` | - | shown when the box is away | - |

- **Locations** [V ents:12065-15250]:
  - `start_chest` (N 0) and `magic_box_hallway` (1)
  - `magic_box_bathroom` (2) and `opened_chest` (4)
  - `magic_box_south` (5)
- **Start** [V weapons:250-281]: with more than one chest, the order is shuffled until index 0 isn't `start_chest`.
  Then every chest except `start_chest` is hidden, and the box starts at `start_chest`.
- **Moves** (teddy odds and the open-location list) are in later_maps "mystery box" §4 "Asylum" [V]:
  - The move only goes to locations whose door flags are set (`magic_box_explore_only` = 1).
  - The vibrate axis depends on the location (weapons:562-569).
- `level.magic_box_uses = 1` (asy:260).

Suggested fields:
- `box.triggerTargetname` (exists as `uses.boxTargetname`)
- `box.locationKey = "script_noteworthy"`
- `box.startLocation = "start_chest"`: T4.
- `box.rubbleSuffix = "_rubble"`: T4.
- `box.exploreOnly = true`: AS.
- `box.locationFlags`: AS table, location → flags (later_maps §4).

## 8. Zones (AS override)

| classname | targetname | `target` | count |
|---|---|---|---|
| `info_volume` | `north_spawners`, `south_spawners`, `south_west_upper_corner` | spawner groups | 3 |
| `info_volume` | `north_upstairs_volume`, `south_upstairs_volume` | none (goals only) | 2 |
| `info_volume` | `magic_room_north_volume`, `magic_room_south_volume` | box rooms | 2 |

- **Polling:** each volume is checked every 1 s.
- **Spawners:** they're kept by `script_string` = volume name, and goals by `script_string` `<volume>_goal`. Spawners
  are locked behind doors until the door flag is set. Details in later_maps §4.3 [V].
- **The T4 zone rule doesn't fit.** The profile's T4 `zones` rule is Der Riese's zone manager (`info_volume` +
  `_barriers`). Verrückt's first-version zones need their own override: `zones.mode = asylumPoll`, the 5 polled names
  (asy:304-308), `zones.spawnerKey = "script_string"` and `zones.goalSuffix = "_goal"`.
- **The 82 spawners** [M]: 8 named groups (`north_stairs_blocker_spawners`, `north_upstairs_door1/2_spawners`,
  `south_stairs_blocker_spawners`, `south_upstairs_door2_spawners`, `south_zone_spawners`, `zombie_spawner_north_door`,
  `zombie_spawner_init`), plus `auto*` groups targeted by doors.

## 9. Risers (T4)

| classname | targetname | count | where [M] |
|---|---|---|---|
| `script_struct` | `zombie_rise` | 32 | all in the courtyard: x −384…576, y −240…280, z 54-56 |
| spawners with `script_string` `riser` | (various) | 25 | across the map (all 13 `zombie_spawner_init`, 3 `zombie_spawner_north_door`, 2 each in 4 more groups, 1 `auto204`) |

Rule [V spawner:386, :2377-2420]:
- **Who rises:** a spawner with `script_string` `riser` rises **74% of the time** (`randomint(100) > 25`).
- **Where:** a random `zombie_rise` struct **anywhere**, not one near the spawner. So on Verrückt every riser comes up
  in the courtyard, whichever spawner it came from [V for the rule, I for the effect].
- **Anim:** v1 or v2 for walkers, 50/50, and v1 for runners and sprinters. Version 2 starts 14 below the ground,
  version 1 starts 45 below. The rise anims are in `zombie_movement_t4_t5.md` (Der Riese "Risers").
- **Shared with Der Riese:** Der Riese uses the same rule with its own structs (`zombie_rise`, plus `riser` /
  `find_flesh` keys) [V df spawner:271-276].

Suggested fields:
- `risers.structTargetname = "zombie_rise"`
- `risers.spawnerKey = "script_string"`, `risers.spawnerValue = "riser"`
- `risers.chance = 74`
- `risers.pickNearest = false` (true would be a deliberate fix, not faithful)

## 10. Windows: bigger than Nacht's (T4, no new field)

Verrückt's 20 `exterior_goal`s include **three wall breaks** of **15 boards plus a clip** each [M]:
- `north_wall_break` (ents:1068-1202)
- `upper_wall_chunk`
- `upper_wall_chunk2`

They use the existing window rule (`windows.goalTargetname = "exterior_goal"`, boards by the goal's `target`, clip by
`script_noteworthy` `clip`) [V], so nothing new is needed. But the loader must not assume Nacht's board count: with
one zombie, a 15-board wall break takes about 40 s to clear [I: 15 × 2.3-3.0 s].

Initially active goals are marked `north_init_goal` / `south_init_goal` by `script_noteworthy`, and two stair goals by
`<volume>_goal` (asy:278-295) [V].

## 11. Extras (AS)

| item | ents | rule | needed for M3? |
|---|---|---|---|
| waterfalls | `trigger_multiple` `waterfall` ×5 (ents:15427-15451) | touching one gives the player `setwatersheeting(true, 3)`, a 3 s camera water effect, unless in last stand (asy:2333-2347) | visual only |
| fog/vision | `trigger_radius` `trigger_fog` ×2 (ents:345, :361) | the generic `_load` fog trigger. Keys `script_start_dist` 167, `script_halfway_dist` 400 / 416, `script_halfway_height` 200, `script_base_height` 124, `script_color` 0.46 0.38 0.29, `script_vision` `zombie_asylum2` / `zombie_asylum` | visual |
| toilet egg | `trigger_use` `toilet` (ents:11078) | look-at use plays `toilet_flush`. On the **3rd** flush: `cha_ching`, `level.eggs` = 1 and music state `eggs` for 245 s, then `WAVE_1`. The counter never resets, so it happens **once per game** (asy:914-946) | optional |
| dentist chair | `trigger_use` `dentist_chair` (ents:12045) | every 3rd use plays `chair`, then resets (asy:951-) | optional |
| radio | `script_model` `kzmb` | the same as Nacht: damage → next song (`_zombiemode_radio.gsc`) | already in Nacht's set |
| anti-exploit | none (hard-coded) | every 0.5 s, `fix_hax` pushes players off 3 fixed spots, plus 2 more before power (asy:2353-2402) | yes for fidelity; keep as data |
| fountain MG | `misc_turret` `fountain_mg` + `script_brushmodel` / `script_model` `fountain_turret`, `fountain_top` | hidden at load (asy:75-80). Its activate function (asy:1433) is **never called**, and there's no `trig_courtyard_mg` ent | **no**: hide it |
| loose turrets | `misc_turret` ×12, unnamed: bar, 30cal, mg42 and fg42 bipod stand/crouch/prone | not read by any zombie script [I]. They're probably the weapon defs the bipod wall buys need loaded | no |
| ambience | `amb_*` structs, `ambient_package` ×3, `electrical_surge` ×25, `electrical_circuit` ×6, `audio_bump_trigger` ×45 | client and ambient audio | audio pass |
| rope | `rope` `morgue_rope` ×1 | no script reads it [M] | no |

---

## 12. Perk effects Reforged must implement

Values only. The sources are in `zombies_t4_later_maps.md` "perk machines" §1.2-1.6 [V there].

| perk | effect | value | where it lives |
|---|---|---|---|
| Juggernog | max health | **160** (base 100) | script |
| | regen (AS, SU) | +40 every 0.5 s up to 160, unless burning | script, per-map |
| | trap hit | 50 instead of death, while health > 100 | script |
| Speed Cola | reload time × | **0.5** (`perk_weapReloadMultiplier`) | engine dvar |
| | barrier repair (AS) | 0.05 s per board, no 0.2 s wait; a level-wide flag (bug) | script |
| Double Tap | fire interval × | **0.75** (`perk_weapRateMultiplier`), about 1.33× the rate | engine dvar |
| | damage | unchanged in WaW | - |
| Quick Revive | revive time | 3 s → **1.5 s** for the reviver | script |
| | solo | **no self-revive**: going down solo ends the game | script |
| all | on down or death | every perk is lost and `maxhealth` resets to 100 | script |
| all | HUD | 24×24 icons, bottom-left, 30 px apart | script |

[I] For one Reforged ruleset: model the two dvars as weapon-time multipliers on the player and keep the script effects
as perk hooks. BO1's Quick Revive solo self-revive then becomes a per-preset flag on the same perk.
