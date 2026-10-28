# Zombies: T4 Nacht der Untoten

Rules for M2 (the Nacht game loop), read from WaW's own zombie scripts and the Nacht entity string. The M2 items come
first, then box, AI, ents, and the pathnode drop that a contributor asked about.

Tags:
- **[V]**: read in the source, with a file:line or address.
- **[I]**: inferred. Treat as a guess until checked.
- **[M]**: measured in the zone dump. This doc uses the same names.

Sources:
- **Scripts.** `nazi_zombie_prototype.ff` ships the scripts as plain-text rawfiles (39 of them). They include
  `maps/_zombiemode*.gsc`, `maps/nazi_zombie_prototype.gsc`/`.csc` and the aitypes [V, OAT Unlinker `--list`].
  `mp/zombiemode.csv` is a stringtable in `common.ff`, not in the Nacht zone [V].
- **Paths.** File paths below are rawfile names, as OAT dumps them. The dump is in a scratch folder outside the repo.
  No script text is copied here, only the numbers and rules.
- **Exe.** Plutonium `t4sp.exe`, static read only.

## patch.ff overrides (read this first) [V]

The shipped game also loads `patch.ff`, and it carries Nacht-specific forks of the zombie scripts. The patched map
script `maps/nazi_zombie_prototype.gsc` (patch.ff) calls `maps\_zombiemode_prototype::main()` (`:17`), **not**
`_zombiemode::main()`. That fork in turn uses `maps\_zombiemode_spawner_prototype`. `patch.ff` also replaces
`maps/_zombiemode_blockers.gsc` [I that the patch copy wins over the zone copy; the patched map script only makes sense
with it].

The line numbers in this doc are for the original zone scripts. Where the patch changes behaviour:

| what | change | source (patch.ff) |
|---|---|---|
| alive cap | `SetAILimit( 24 )` at start: the engine caps live AI at 24, so the script's `> 31` wait never matters. A failed spawn doesn't count, so the loop retries [I on the engine semantics] | `maps/_zombiemode_prototype.gsc:25` |
| breadcrumbs | new ring system, see the AI doc | `_zombiemode_prototype.gsc:1919-2001` |
| bad-path fallback | new search, see the AI doc | `maps/_zombiemode_spawner_prototype.gsc:1377-1477` |
| co-op respawn | spectators respawn at their own `initial_spawn_points` struct, no longer at a random `info_player_deathmatch` | `_zombiemode_prototype.gsc:722-723`, `:1915` |
| anti-exploit kills | every 0.2 s the player is killed (invulnerability forced off) if z > 145 before any debris is bought (`above_couches_death`, ends on the `junk purchased` notify), z > 235, z < −11, or outside 4 boxes | `maps/nazi_zombie_prototype.gsc:324-430` |
| anti-stuck nudges | 9 hard-coded spots, plus one couch spot until the upstairs debris is bought; within 10-15 units the player is teleported a few units away, every 0.5 s | `nazi_zombie_prototype.gsc:57-150` |
| debris | moved debris and junk set `notsolid`; extra sounds (`lightning_l`, `zombie_spawn`); `level notify("junk purchased")` | `maps/_zombiemode_blockers.gsc:371`, `:415`, `:435-438`, `:478` |
| repair rewards | logic unchanged; Sleight speeds up the repair, but Nacht has no perks | blockers `:604-716`, `:863-898` |

The 4 "inside the map" boxes are:
- (361, 591, −11)–(1068, 1031, 235)
- (−288, 591, −11)–(361, 1160, 235)
- (−272, 120, −11)–(370, 591, 235)
- (−272, −912, −11)–(273, 120, 235)

Unchanged by the patch: score, power-ups, weapons (box list identical), round loop, health, counts and the HUD. The
patch xanims are only weapon and revive anims, so the zombie anim timings stand.

## Rules checklist (the engine's zm lib) [V]

1. **`testy` spawner.** Nothing in the ents targets `testy`, so `is_spawner_targeted_by_blocker` is false and it isn't
   locked (`maps/_zombiemode_spawner.gsc:27-49`). It joins `enemy_spawns` at round 5 with nothing bought
   (`add_spawner`, `maps/_zombiemode_utility.gsc:453-475`).

   It sits at (−1257.5, 960.5, 14.5), far outside the play space. Its zombies must path in from there, or fall to the
   30 s failsafe [I].

   The other three `later_round_spawners` are named `zombie_spawner_door`, so they lock and unlock with the doors.
2. **Power-up outside the playable area.** It is deleted and the function returns *before*
   `powerup_drop_count++` and before the flag clears. So it doesn't count towards the 4 per round, and the score
   threshold stays armed for the next death (`maps/_zombiemode_powerups.gsc:169-191`).
3. **Doubled repair points.** These count towards the cap. The doubled cost (20) is added to `rebuild_barrier_reward`
   *before* the check (patch blockers `:669-708`).

   The check is `reward < cap` after adding, so the board that reaches the cap isn't paid:
   - round 1 (cap 50): 4 boards × 10 = 40, or 2 × 20 = 40 under double points
   - from round 10 (cap 500): 490 per round
4. **First zombie of a round.** It spawns with no delay: the spawn comes before `wait(spawn_delay)` (`_zombiemode.gsc:862-883`).
   The round's first spawn still waits for `chalk_one_up`: about 6.75 s in round 1 and 0.5 s later (flow doc).
5. **`round / 5`** is float division. The GSC VM divide (`t4sp 0x691d40`) turns int ÷ int into float (`0x691d7d-0x691d96`:
   `cvtsi2ss` both, `divss`, result type 5 = float). So round 6 gives 1.2, not 1. The same holds for `set_zombie_var`'s
   `/ div`.
6. **DisconnectPaths.** See the AI doc, section 6.

## How tunables are set [V]

`set_zombie_var(var, value, div)` (`maps/_zombiemode_utility.gsc:687`) works in three steps:
1. It looks `var` up in column 0 of `mp/zombiemode.csv`.
2. If the csv has a value, that value replaces the script default.
3. If `div` is given, the value is then divided by it.

The defaults live in `init_levelvars` (`maps/_zombiemode.gsc:243-295`). The csv mostly matches them. One quirk: the csv
row for the start score is spelt `mbie_score_start`, so it never matches and the script's 500 is used. Same number either
way.

| var | value | source |
|---|---|---|
| `zombie_round_time` / `between_round_time` / `intermission_time` | 30 / 10 / 15 s | `_zombiemode.gsc:261-263` |
| `zombie_spawn_delay` | 3 s | `:266` |
| `zombie_health_increase` | 100 | `:269` |
| `zombie_health_increase_percent` | 10 / 100 = 0.1 | `:270` |
| `zombie_health_start` | 150 | `:271` |
| `zombie_max_ai` | 24 (a per-round total, not an alive cap) | `:272` |
| `zombie_ai_per_player` | 6 | `:273` |
| `zombie_score_start` | 500 | `:276` |
| kill / damage | 50 / 5 | `:277-278` |
| kill bonus: melee / head / neck / torso / burn | 80 / 50 / 20 / 10 / 10 | `:279-283` |
| penalty: no revive / died / downed | 10% / 0% / 5% | `:285-287` |
| `zombie_powerup_drop_increment` | 2000 | csv only |
| `zombie_powerup_drop_max_per_round` | 4 | csv only |
| `zombie_powerup_point_doubler_time` / `insta_kill_time` | 30 / 30 s | csv only |
| `rebuild_barrier_cap_per_round` | overwritten every round (see Barriers) | csv 500, `_zombiemode.gsc:1179-1182` |

## Round loop [V]

`round_think` (`maps/_zombiemode.gsc:1169-1228`) runs each round in this order:
1. Set the barrier reward cap.
2. `ai_calculate_health`.
3. `add_later_round_spawners`.
4. Bump the chalk round counter.
5. `powerup_round_start`, which resets the drop count.
6. Reset each player's barrier reward.
7. Award grenades.
8. Thread `round_spawning`.

Then it runs `round_wait`, which returns when no enemies are alive and `zombie_total` is 0 (`:1325`). After that:
- `first_round = false` (`:1202`)
- respawn spectators
- wait 10 s (`between_round_time`)
- `spawn_delay *= 0.95` (`:1212-1219`). The 0.08 floor is applied to the old value before the multiply, so the delay can
  settle at about 0.076.
- `zombie_move_speed = round × 8` (`:1222`)
- `round++`

### Zombie count per round [V]

`round_spawning`, `maps/_zombiemode.gsc:797-888`, as our pseudocode (not the script):

```
max = 24
mult = max(1, round / 5)
if round >= 10: mult *= round * 0.15
max += int((players - 1) * 6 * mult)
round 1: max = int(max * 0.2)   (level.first_round, :841)
round 2: max = int(max * 0.4)
round 3: max = int(max * 0.6)
round 4: max = int(max * 0.8)
```

- The multiplier only scales the extra-player term. **Solo is 4, 9, 14, 19, then 24 every round after.**
- 4 players: round 1 is int(42 × 0.2) = 8. Round 10 is 24 + int(18 × 3) = 78.
- `round / 5` is float division in the GSC VM (see the checklist above), so co-op rounds 6-9 scale smoothly [V].

### Spawn rules [V]

- **Delay.** One zombie every `spawn_delay` s (`:883`). Round N uses 3 × 0.95^(N−1).
- **Spawner choice.** Uniform random over `level.enemy_spawns` (`:862`).
- **Max alive.** Before each spawn the loop waits while `get_enemy_count() > 31` (`:864-867`), which would allow 32.
  **But the patched script calls `SetAILimit( 24 )`, so the real alive cap is 24** (see patch.ff overrides).
  `zombie_max_ai` is the per-round total.
- **Failed spawns.** If a spawn fails, `count` doesn't go up and the loop retries on the next pass.
- **Failsafe.** Each spawned zombie runs `round_spawn_failsafe` (`:1278`). Every 30 s it kills the zombie if:
  - it moved less than 24 units in that time, or
  - it fell below z −1000 (`below_world_check`).

  A zombie that tore a board in the last 5 s is exempt.

### Which spawners are active, per zone [V]

- **Start state.** `level.enemy_spawns` starts as every spawner with targetname `zombie_spawner_init`
  (`maps/_zombiemode.gsc:24`).
- **Init.** Spawner init is at `maps/_zombiemode_spawner.gsc:6-25`. A spawner is *locked* if a `zombie_door` or
  `zombie_debris` trigger targets it, directly or through a chain (`:27-49`).
- **Buying a door or debris.** It unlocks the spawners it targets, plus those named by its `script_string`, and adds them
  to `enemy_spawns` (`add_new_zombie_spawners`, `maps/_zombiemode_blockers.gsc:789-815`).
- **Late spawners.** `later_round_spawners` join at round start once `round >= script_start` and they are unlocked
  (`add_later_round_spawners`, `maps/_zombiemode_utility.gsc:445`).

How this plays out on Nacht (ents, see below):

| zone | spawners | becomes active |
|---|---|---|
| start room | 16 × `zombie_spawner_init` | round 1 |
| help room (behind the 2 doors) | 5 × `zombie_spawner_door` | when either `zombie_door` is bought |
| upstairs | 19 × `zombie_spawner_upstairs` | when the `balcony_blocker` debris is bought |
| late | 3 × `zombie_spawner_door` + 1 named `testy`, `later_round_spawners`, `script_start 5` | round 5+, and only if unlocked by the matching door |

### Zombie health [V]

- `ai_calculate_health` (`maps/_zombiemode.gsc:1260-1274`) runs at round start:
  - round ≥ 10: `health += int(health × 0.1)`, and nothing else
  - otherwise, round > 1: `health += 100`
- The start value 150 is set at `maps/_zombiemode_spawner.gsc:9` and `maps/_zombiemode.gsc:941`.
- Results: round 1 is 150; rounds 2-9 are 150 + 100(N−1) (round 9 = 950); round 10 is 1045; round 11 is 1149; then
  ×1.1 each round.

### Walk/run/sprint mix [V]

`set_run_speed` (`maps/_zombiemode_spawner.gsc:192-209`) runs per zombie at spawn:
- r = randomintrange(speed, speed + 35)
- r ≤ 35 is walk, ≤ 70 is run, otherwise sprint

`speed` is `level.zombie_move_speed`. It starts at 1 (`spawner.gsc:8`) and becomes (N−1) × 8 in round N ≥ 2. So:
- round 1: all walk
- round 2: 28/35 walk
- round 5: 4/35 walk, 31/35 run
- round 9: 7/35 run, 28/35 sprint
- round 10 and later: all sprint

Anim sets: 4 walk, 3 run and 2 sprint variants (`spawner.gsc:117-190`).

## Points [V]

`player_add_points` (`maps/_zombiemode_score.gsc:9-49`) computes `points = round_up_to_ten(base) × point_scalar`, where
`point_scalar` is 2 under double points. `round_up_to_ten` is at `maps/_zombiemode_utility.gsc:107-115`.

| event | base | paid |
|---|---|---|
| hit (`damage`) | 5 | **10** |
| hit while aiming down sights (`damage_ads`) | int(5 × 1.25) = 6 | **10** |
| kill | 50 + bonus | |
| kill, melee (`MOD_MELEE`) | 50 + 80 | **130** |
| kill, burned (`MOD_BURNED`) | 50 + 10 | **60** |
| kill, head or helmet | 50 + 50 | **100** |
| kill, neck | 50 + 20 | **70** |
| kill, upper/lower torso | 50 + 10 | **60** |
| kill, limbs | 50 | **50** |
| barrier board repaired | 10 | **10**, capped per round (below) |

Notes:
- The melee and burn checks come before the hit location (`score.gsc:53-61`), so a melee kill is always 130.
- **Penalties** (`score.gsc:85-126`): the score loses round_up_to_ten(score × percent), floored at 0.
  - downed: 5%
  - another player who doesn't revive you: 10%
  - died: 0%
- **Start score:** 500.
- The hit and kill calls come from the zombie damage callback in `maps/_zombiemode_spawner.gsc` around `:1078`. That
  callback also calls `powerup_drop` at the death origin.

## Barriers (windows) [V]

All in `maps/_zombiemode_blockers.gsc`.

**Repair trigger** (`blocker_trigger_think`, `:461-609`):
- A script-spawned `trigger_radius`, radius 96, height 96, placed 4 units above the ground under the window.
- Holding use repairs one board at a time: wait 0.4 s, then 1 s per board (`:585-588`). [I] The 0.4 s is the start
  delay and the 1 s is the per-board anim.
- Each board pays 10 points (20 under double points).
- The pay only happens while the player's accumulated repair reward this round is below the cap. The cap is
  min(50 × round, 500) (`_zombiemode.gsc:1179-1182`) and resets per player each round.

**Tearing** (`remove_chunk`, `:639-733`):
- A zombie at the window removes one chunk (board) at a time.
- When every chunk is gone, the window clip runs `ConnectPaths`, so zombies can path through.

**Repair** (`replace_chunk`, `:735-787`) puts the board back. When the first board returns, the clip blocks again [I].

**Attack spots** (`:423-444`): three per window, at the ground below a point 36 units back from the chunks along the
window's facing, at offsets 0 and ±28 to the side.

## Doors and debris [V]

`maps/_zombiemode_blockers.gsc`.

- **door_init** (`:54-99`):
  - The cost is the trigger's `zombie_cost`, defaulting to 1000.
  - When bought, the door does `MoveTo(origin + script_vector)` over `time` (default 1 s), with accel and decel each
    0.25 × time.
- **debris** (`:217-385`):
  - Bought the same way.
  - The junk is deleted or moved away and the debris's `script_flag` is set.

On Nacht:
- 2 × `zombie_door`, cost 1000, `script_vector 90 0 0`, target `auto34`. They unlock `zombie_spawner_door`.
- 4 × `zombie_debris`, cost 1000, flag `balcony_blocker`. They target `upstairs_blocker` / `upstairs_blocker2`, which
  unlock `zombie_spawner_upstairs`. `upstairs_blocker2` also has `script_string zombie_spawner_door`.
- `flag_blocker` waits on `balcony_blocker`.

## Power-ups [V]

`maps/_zombiemode_powerups.gsc`.

- **The four:** `nuke`, `insta_kill`, `double_points`, `full_ammo` (`:30-41`).
  - They are drawn from a shuffled bag: all four come out once each before a reshuffle (`get_next_powerup`, `:48-63`).
- **Score threshold** (`watch_for_drop`, `:65-90`):
  - First threshold: players × 500 + 2000.
  - Every 0.5 s the script sums each player's lifetime `score_total`.
  - When the sum passes the threshold, it sets the drop flag, multiplies the increment by 1.14, and sets the next
    threshold to the current total + the new increment.
- **The drop itself** (`powerup_drop`, `:143-204`) runs on every zombie death:
  - If 4 have already dropped this round, nothing.
  - 3% of deaths (`randomint(100) <= 2`) drop regardless of the flag. Every other death drops only if the flag is set.
  - The power-up spawns 40 units above the death origin. It is deleted at once if it isn't touching the
    `playable_area` trigger.
  - On success the drop count goes up and the flag clears.
- **Pickup:** any player within 64 units (`:238`).
- **Lifetime:** 15 s, with blinking near the end (`:310-344`).

**Effects:**

| power-up | effect | lines |
|---|---|---|
| nuke | kills every zombie, awards no points | `:347-375` |
| double points | `point_scalar` 2 for 30 s | `:405-419` |
| max ammo | `GiveMaxAmmo` on each player's primaries | `:421-436` |
| insta-kill | 30 s, any damage kills | `:438-459` |

## Player [V]

- **Health:** the script never sets max health in play, so the engine default applies, 100 [I]. Intermission sets it to
  100 (`_zombiemode.gsc:2100`).
- **Regen:** the script has none; it is the engine's player regen [I].
- **Solo death** (`player_damage_override`, `maps/_zombiemode.gsc:1651-1687`):
  - When lethal damage would leave every player down, a zombie or spectating, the player goes to last stand with a fake
    death and `end_game` runs.
  - Solo, that means **going down is game over**: no solo revive.
  - `end_game` (`:1689`) runs a 15 s intermission, then mission failed.
- **Grenades** (`award_grenades_for_survivors`, `:1230`): each round, survivors' `stielhandgranate` clip is set to 2, 3
  or 4, by the fraction of max ammo.

## Wall weapons and cabinet [V]

`weapon_spawn_think` (`maps/_zombiemode_weapons.gsc:722-823`):
- The price comes from `get_weapon_cost`, which reads the csv and script table. It does **not** read the trigger's
  `zombie_cost`. Several Nacht triggers carry a stale `zombie_cost`.
- Ammo costs round_up_to_ten(int(cost × 0.5)). Grenades always cost full price.

| Nacht wall buy | ent `zombie_cost` | **actual price (csv)** |
|---|---|---|
| kar98k | 200 | **200** |
| m1carbine | 400 | **600** |
| doublebarrel | 700 | **1200** |
| shotgun (trench gun) | 500 | **1500** |
| doublebarrel_sawed_grip | 1200 | **1200** |
| thompson | 1200 | **1200** |
| bar | 1500 | **1800** |
| stielhandgranate | 500 | **250** |

Weapon cabinet (`weapon_cabinet_use`, `kar98k_scoped_zombie`, `:571-708`): 1500 the first time, then the weapon's cost
(750) for ammo.

## Mystery box [V]

`treasure_chest_think` (`maps/_zombiemode_weapons.gsc:251-350`):
- Cost is the trigger's `zombie_cost`: 950 (Nacht ents, `treasure_chest_use`).
- The weapon is a uniform random pick from the included list, minus weapons the player already holds. The flamethrower is
  limited to one in play (`:413-453`).
- No weights.
- The lid rolls 105°. The model cycles 40 times, and the player has 12 s to take the weapon.
- **No teddy bear and no box move in Nacht.** Neither exists in this script.

The included list is in `maps/nazi_zombie_prototype.gsc:29-87`. `m7_launcher` is listed but never registered, so it can
never come out.

Other csv prices, for reference:

| weapon | price |
|---|---|
| colt | 50 |
| sw_357 | 100 |
| gewehr43 | 600 |
| m1garand | 600 |
| ptrs41 | 750 |
| kar98k_scoped | 750 |
| mp40 | 1000 |
| stg44 | 1200 |
| m1garand_gl | 1200 |
| fg42_bipod | 2000 |
| panzerschrek | 2000 |
| flamethrower | 3000 |
| mg42_bipod | 3250 |
| 30cal_bipod | 3500 |
| ray_gun | 10000 |

## Zombie AI [V]

All in `maps/_zombiemode_spawner.gsc` unless noted.

1. **Choosing a window** (`zombie_think`, `:212-288`):
   - The zombie finds the 3 closest `exterior_goal` structs, ignoring any more than 500 units further than the closest,
     and picks one at random.
   - A spawner with `script_forcegoal` goes straight to its target's origin instead.
2. **Reaching it:** goalradius 128 (`:328`).
3. **Tearing in** (`tear_into_building`, `:415-478`):
   - The zombie claims a free attack spot (goalradius 4) and pulls boards until the window is open.
   - It swipes at players through the window [I].
4. **Inside:**
   - `ignoreall` off; `pathEnemyFightDist` and `meleeAttackDist` both 64 (`:1283-1284`).
   - `find_flesh` (`:1292-1345`): target the closest valid player, goalradius 32, re-choose every 1-3 s.
   - On `bad_path`, the zombie walks the target's breadcrumbs (`:1377-1454`). Players drop a crumb every 0.1 s while on
     the ground, at least 20 units from every other crumb, keeping the latest 20 (`_zombiemode.gsc:1917-1950`).
5. **Melee damage:** the engine's `melee()`, called at the `fire` notetrack of the attack anim
   (`animscripts/melee.gsc:131-137` in `common.ff`). The damage number is the engine's own; not read yet [I].

**Damage zombies take** (`:1152-1195`):
- grenades: + round + randomint(100, 500)
- projectile or explosive: round × randomint(100, 500)
- flame: damage over time (`:1114-1150`). In rounds 9-10 it calls `RandomFloatRange(0.8, 0.16)` with min > max, which
  is a script bug.

## Nacht entities [V]

From `maps/nazi_zombie_prototype.d3dbsp.ents`. The counts match the [M] numbers.

**Zombie spawners:**

| targetname | count | notes |
|---|---|---|
| `zombie_spawner_init` | 16 | start room |
| `zombie_spawner_upstairs` | 19 | some have `script_forcegoal`; targets `auto31` / `32` / `51` / `52` |
| `zombie_spawner_door` | 5 | help room |
| `zombie_spawner_door`, noteworthy `later_round_spawners` | 3 + 1 (`testy`) | `script_start 5` |

**Map structure:**

| entity | count |
|---|---|
| `exterior_goal` structs | 12 |
| window chunk groups (`pfNNN_auto1/2`, clip noteworthy) | per window |
| `initial_spawn_points` | 4 |
| `info_player_start` | 1 |
| intermission structs | 8 |
| `info_intermission` | 4 |
| `trigger_multiple` `playable_area` | 1 |

**Buyables:**

| entity | count |
|---|---|
| `zombie_door` | 2 |
| `zombie_debris` | 4 |
| `weapon_upgrade` (wall buys) | 8 |
| `treasure_chest_use` | 1 |
| `weapon_cabinet_use` | 1 |

## Pathnodes dropped to the floor at load [V]

Yes, T4 drops every pathnode at load. The engine's assumption is right. The function is in Plutonium `t4sp.exe` at
`0x559470`, called once per node from the loop at `0x559440`.

1. **Trace down.** A box trace (`0x5abdc0`, mask `0x820011`) runs from node + (0, 0, 1) to node − (0, 0, 256).
   - Constants: 1.0 at `0x826a4c`, 256.0 at `0x839f30`.
   - The box uses ±15 in x/y and 30 in z (`0x83da84`, `0x83da94`, `0x7f0428`). My reading is mins (−15, −15, 0) and
     maxs (15, 15, 30) [I on the axis assignment].
2. **Failure cases:**
   - Starts in solid: logs "Pathnode (%s) at (%g %g %g) is in solid" (`0x868f34`).
   - Hits nothing within 256 units (fraction == 1.0, `0x55959b`): logs "... is floating" (`0x868f64`).
   - Either way the node's first dword is cleared (`0x559723`). [I] That disables the node.
3. **Standing check.** The hit point is start + fraction × (end − start). A second box trace runs at that point with
   mins (−15, −15, 0) and maxs (15, 15, 72) (`0x83da94`, `0x83daa0`). If it is in solid, the node gets the "in solid"
   error.
4. **Write-back.** Otherwise the hit point is written over the node origin at node + 0x14/0x18/0x1c
   (`0x55968a-0x5596a6`).

So the dropped position is where a 30×30 box swept down from 1 unit above the node first touches the floor. For a box
whose bottom sits at the origin, that is the floor height. A node more than 256 units up is not dropped; it is disabled.
