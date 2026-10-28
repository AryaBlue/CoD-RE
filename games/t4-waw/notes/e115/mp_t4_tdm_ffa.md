# MP: T4 (WaW) Team Deathmatch and Free-for-All

The rules, spawn selection, health, killstreaks, bot support and HUD for WaW multiplayer TDM (`tdm`) and FFA (`dm`).
At the end there is a short diff for BO1 and BO2. This is groundwork for M4 (offline MP vs bots).

Tags:
- **[V]**: read in the source, with a file:line.
- **[I]**: inferred, or from general knowledge. Treat it as a guess until checked.

Sources:
- Scripts were dumped with OAT from `common_mp.ff` and `patch_mp.ff` to a scratch folder outside the repo. No script text
  is copied here.
- `patch_mp.ff` overrides `maps/mp/gametypes/_globallogic.gsc`, `sd.gsc` and `_serversettings.gsc`. **All
  `_globallogic.gsc` lines below are the patched file.** The patch changes little: a return value, a team-change lock
  after combat (`:2548-2553`, `:2604-2608`), and a dvar moved to `_serversettings`.
- All other files are from `common_mp.ff`, under `maps/mp/gametypes/` unless the path says otherwise.
- BO1 is from its own `common_mp.ff` and `patch_mp.ff` (same method).

Dvar defaults are the script's defaults. A playlist or server config can override any `scr_*` dvar [I: online playlists
did].

## 1. Rules

### Limits [V]

The limits are registered as `scr_<gametype>_<limit>`:

| | TDM (`tdm.gsc:63-66`) | FFA (`dm.gsc:54-57`) |
|---|---|---|
| time limit (min) | 10 (range 0-1440) | 10 |
| score limit | 500 (0-5000) | 1000 (0-5000) |
| round limit | 1 | 1 |
| lives | 0 = unlimited | 0 |
| teams | `level.teamBased = true` (`tdm.gsc:68`) | free-for-all |

If a gametype registers no limits, the fallback is 10 min and 100 points (`_globallogic.gsc:4512`, `:4515`).

### Points [V]

`_rank.gsc` holds two score tables. `dm.gsc` replaces some entries for FFA.

| event | team-based (`_rank.gsc:24-33`) | FFA (`dm.gsc:103-110`) |
|---|---|---|
| kill | 10 | 5 |
| headshot | 10 | 5 |
| assist (75/50/25 %/other) | 8 / 6 / 4 / 2 | 1 / 1 / 1 / 1 |
| suicide, teamkill | 0 | 0 |
| dog kill | 3 | 2 (`_rank.gsc:45`) |
| using a hardpoint | 10 (`_hardpoints.gsc`, in `init`) | 10 |

How scoring works:
- **A kill** calls `givePlayerScore("kill")` (`_globallogic.gsc:6570`). In TDM it also calls
  `giveTeamScore("kill", attacker's team)` (`:6585-6587`).
- **So in TDM a kill is +10 to the player and +10 to the team.** The score limit of 500 is 50 kills.
- **In FFA a kill is +5.** The 1000 limit is 200 kills [V for the arithmetic; real playlists likely set it lower, I].
- **A headshot gives no extra points.** Nothing calls `givePlayerScore("headshot")`. The `headshot` entry only feeds
  XP and stats [V, by grep].
- **Death penalties.** `scr_game_deathpointloss` and `scr_game_suicidepointloss` default to 0
  (`_tweakables.gsc:335-336`). If set, the player loses that many points on death (`_globallogic.gsc` after `:6587`).
- **Scores in the code:**
  - player score is `pers["score"]`, copied to `self.score` (`:2891-2914`)
  - team score is `game["teamScores"][team]`, pushed to the engine with `setTeamScore` (`:2981-2990`)

### Match end [V]

- **Score limit.** `checkScoreLimit` (`:2097-2117`) runs after every score change.
  - TDM: either team ≥ limit.
  - FFA: the scoring player ≥ limit.

  Then `default_onScoreLimit` (`:436`) picks the winner: the higher team, or "tie" if level. In FFA the winner is the
  highest-scoring player. `level.endGameOnScoreLimit` is true by default (`:45`).
- **Time limit.** `checkTimeLimit` (`:2055-2090`) measures time remaining as limit × 60000 minus time passed. The clock
  doesn't run in the prematch period. At 0, `default_onTimeLimit` (`:353-378`) picks the winner the same way. **Equal
  team scores give a tie. There is no overtime in TDM or FFA**: only `sab.gsc:246` ever sets `inOvertime`.
- **No lives limit and no rounds.** With round limit 1, the first score or time end ends the match. The TDM `onEndGame`
  (round-win counting) only runs when the round limit is not 1 and lives are set (`tdm.gsc:124-129`).
- **`endGame` sequence** (`_globallogic.gsc:1323` onwards):
  - Vision set `mpOutro` over 2 s.
  - `game["state"] = "postgame"`.
  - `postRoundTime` is 7 s (`:75`).
  - Final scoreboard wait 9 s (`:1723`).
  - Intermission `scr_intermission_time`, default 30 s (`:136-137`, `:1742-1743`), at the `mp_global_intermission`
    points (`:1153`).

### Start of match and respawn [V]

- **Prematch.** `prematchPeriod` = tweakable `scr_game_graceperiod`, 15 s, set on the first round (`:4408`).
  `startGame` adds a random ±2 s to it when it is over 2 s (`:4539-4540`).
- **Grace period** (`:4543-4547`, `:3510-3519`): 5 s, or 15 s if lives or wave spawns are on. During it a player's first
  spawn has no delay (`:3793`).
- **Respawn delay.** `scr_<gt>_playerrespawndelay` is unset by default, so 0. `scr_player_forcerespawn` is 1
  (`_tweakables.gsc:351`). Wave spawning is off unless `scr_<gt>_waverespawndelay` is set (`:4526-4530`, `:3790-3814`).
  So TDM and FFA respawn as soon as the killcam and death sequence end (timings in §8).
- **Max health.** `scr_player_maxhealth`, 100 (`_tweakables.gsc:349`, applied at `_globallogic.gsc:666-669`).

### For one Reforged ruleset [I: design pick]

WaW and BO1 differ on the scale of scores, not the shape: both are 10 min, with no overtime and no rounds. BO1's kill
values are WaW's × 10 (TDM 100 vs 10, assists 80/60/40/20 vs 8/6/4/2). The limits are what really differ.
- **TDM:** 50 kills in WaW (500 at 10), 75 kills in BO1 (7500 at 100).
- **FFA:** 200 kills in WaW (1000 at 5), 20 kills in BO1 (1000 at 50).

Recommendation:
- **Points:** adopt **BO1's scale**: kill 100 in team modes and 50 in FFA, with assists 80/60/40/20. BO2 uses the same
  ×100 scale, so one score table covers every source game.
- **Limits:** TDM **7500** (75 kills) and FFA **1000** (20 kills), 10 min, 1 round. WaW's 200-kill FFA is unplayable
  against bots in 10 min.
- **No score for using a killstreak, and none for dog kills:** XP only, as in BO1.
- **Headshots:** no bonus score, only XP and medals. Both games agree on this [V for WaW; BO1 has a `headshot` entry,
  but I didn't check whether it's ever paid on top of the kill].
- **Everything else as both games do it:**
  - tie on equal team scores at the time limit
  - 15 s prematch, then 5 s grace
  - instant respawn after the killcam
  - 100 max health
- Keep the round-win limit (BO1's `registerRoundWinLimitDvar`, default 0) so modes with rounds can use it later.

## 2. Spawn selection

There are two systems. Which one runs is decided per spawn.

### Which system [V]

1. `_globallogic.gsc:697-700` calls `level.onSpawnPlayerUnified` unless `scr_disableunifiedspawning` is 1 (default 0).
   That leads to `_spawning.gsc:onSpawnPlayer_Unified` (`:1015-1093`).
2. **That function uses the legacy gametype logic instead** (`level.onSpawnPlayer`) while `level.useStartSpawns` is true,
   and always in S&D (`:1052-1061`).
   - `useStartSpawns` is set at game start (`_globallogic.gsc:4437`).
   - It is cleared the first time any player takes damage from an enemy (`:6036-6037`).
   - **So everyone uses start spawns until the first enemy hit, then the unified system.**

### Legacy path, used before the first hit [V]

**TDM** `onSpawnPlayer` (`tdm.gsc:140-166`):
- **In the grace period:** a random point from `mp_tdm_spawn_<team>_start`, falling back to `mp_sab_spawn_<team>_start`
  and then the team spawns.
- **Otherwise:** `getSpawnpoint_NearTeam` over the `mp_tdm_spawn` points.
- Both teams use the same `mp_tdm_spawn` set (`tdm.gsc:102-103`).

**FFA** `onSpawnPlayer` (`dm.gsc:130-134`) runs `getSpawnpoint_DM` over all `mp_dm_spawn` points.

`_spawnlogic.gsc` scoring is the CoD4 system. Both functions start from a base weight, then subtract penalties:

- **NearTeam base** (`:817-950`): weight = (sum of enemy distances − 2 × sum of ally distances) / number of players.
  - The distance sums are 2D.
  - They come from a background update that refreshes **one spawn point every 0.05 s** (`spawnPerFrameUpdate`
    `:1883-1908`, `spawnPointUpdate` `:1909-2012`).
  - A squad-mate near the point adds 25000, or 12500 if they aren't the squad leader.
- **DM base** (`:1036-1100`):
  - ideal distance 1600, bad distance 1200
  - weight = (1600 − mean |dist − 1600|) / 1600 − 2 × Σ (1200 − d) / 1200 for players closer than 1200
  - plus a random 0-0.2
- **Penalties** (both, if `scr_spawnpointnewlogic` is not "0"):

  | penalty | amount | source |
  |---|---|---|
  | same point as your last spawn | −50000 | `avoidSameSpawn` `:2255` |
  | an enemy (TDM) or anyone (FFA) spawned within 1024 units in the last 10 s and is still alive | −5000 × (1 − d²/1024²) × (1 − t/10 s) | `avoidSpawnReuse` `:2205` |
  | a live grenade within 250 units | −100000 each | `avoidWeaponDamage` `:1831` |
  | inside artillery danger | danger × 100000 | `avoidWeaponDamage` `:1831` |
  | each enemy with line of sight in the last update | −100000 | `avoidVisibleEnemies` `:2076` |

  Line of sight is traced from the player's origin + 50 up to the point's trace point. It is skipped when the player and
  the point face away from each other (`_spawnlogic.gsc:1970`).

  `scr_spawn_enemyavoidweight` defaults to 0, so the near-enemy penalty is off (`:1148-1151`).
- **Final pick** (`getBestWeightedSpawnpoint` `:275-327`):
  - Take the highest weight, choosing at random among ties, and skip any point where the spawn would telefrag.
  - Up to 3 times: do a last-minute sight trace on it. If an enemy can see it, subtract 100000 and pick again.

### Unified path, used after the first hit [V for script; scoring is engine]

`get_best_spawnpoint` (`_spawning.gsc:1178-1235`):
1. Calls the engine builtin `getsortedspawnpoints(team)`. **The influencer maths is in the exe, not script.**
2. Walks the sorted list:
   - skips any point where the spawn would telefrag
   - remembers the first good one
   - returns the first point no enemy can see (`isspawnpointvisible`)
3. Stops checking sight after `scr_spawn_visibility_check_max` points, default 35 (`:78-89`), and returns the first good
   one.

The point pool (`gatherSpawnEntities` `:1237-1282`) is placed `mp_uspawn_point` entities plus the gametype's legacy
points. FFA puts both teams' pools into "free" (`updateAllSpawnPoints` `:783-808`).

The script feeds the engine influencers. Each is a shape with a score and a falloff curve; all are linear unless marked.
`k_player_height` is 70 (`_utility.gsc:550-553`).

| influencer | shape | score | size | applies to | source |
|---|---|---|---|---|---|
| each enemy player | sphere | −150 | r = 15 × 70 = 1050 | the other team (everyone in FFA) | `_spawning.gsc:388`, `:894-896` |
| each enemy's "weapon" | cylinder | −400 | r 350, length 1750 | the other team; also own team if friendly fire is on | `:397`, `:899-902` |
| each friend (weak) | sphere | +75 | r 700 | own team, TDM only | `:414`, `:884-886` |
| each friend (strong) | cylinder, backwards | +175 | r 700, length 1050 | own team, TDM only | `:423`, `:878-881` |
| squad leader | sphere | +150 | r 700 | own squad | `:535`, `:889-891` |
| dead body | sphere | −100, lasts 20 s | r 700 | own team | `:555-572`, `:905-909` |
| grenade | sphere | −500 (7 s for tabun gas and molotov) | r 560 | enemies of the thrower | `:574-612`, `:927-929` |
| dog | sphere | −300 | r 1050 | the dog's enemies | `:614-634`, `:917-919` |
| artillery | sphere | −800 | radius given at call | everyone | `:636-647`, `:922-923` |
| vehicle | cylinder | −50, leads 3 s | | | `:649-680`, `:912-914` |

Other settings:
- Score randomness: `scr_spawn_randomness_range` 50, passed to `setspawnpointrandomvariation` (`:873`, `:996`).
- **Cylinder axes** (`:381-386`, `:411-412`). The script passes forward = (0,0,1) and up = (1,0,0) to every cylinder.
  For friends it passes up = (−1,0,0). The engine treats these as **local to the owner** and the cylinder runs along
  the `up` argument, see "Cylinder" below.
  - The weapon cylinder ends up pointing **along the enemy's view**.
  - The friend strong cylinder ends up pointing **behind the friend**.

### The engine scorer [V] (static read of `t4mp.exe`)

This is what `getsortedspawnpoints(team, influencerTeam, player)` does.
- **Builtins.** The builtin table at `0x8cf700` has `{name, func, devOnly}` entries:
  - `getsortedspawnpoints` `0x520e80`
  - `isspawnpointvisible` `0x521010`
  - `addsphereinfluencer` `0x521170`
  - `addcylinderinfluencer` `0x521320`

  These were checked against their `USAGE:` strings: `addsphereinfluencer` references the one at `0x869240`.
- **Flow.** `0x520e80` calls `0x53c020`, which calls `0x53bfa0`. `0x53bfa0` loops over every spawn point (44-byte
  records at `0x22081c8`) whose team mask matches, and scores each with `0x53bd70`. `0x53d790` (std::sort) then orders
  them, best first. The script gets them back as an array.

**Score of one point** (`0x53bd70`): base weight + random + the sum of the influencer buckets.
- **Base** is the per-team base weight from `setspawnpointsbaseweight`.
  - It's three floats per spawn record (free/axis/allies, record `+0x18..+0x20`). `addspawnpoints` (`0x520cc0` →
    `0x53abe0`) zeroes them when it adds a point.
  - **TDM and FFA never call `setspawnpointsbaseweight`** (only `ctf.gsc` and `twar.gsc` do, for the objective-facing
    bonus). **So their base weight is 0.**
  - The record's origin is the spawn point's origin with z + 35 (`0x8d96d8`). The team mask is `|= 1 << team`.
- **Random** = `rand15() / 32768 × variation`, only if |variation| > 0.001.
  - `rand15` is the game's own LCG: state at `0x8cb280`, ×214013 + 2531011, >> 17 (`0x53bf18`).
  - The variation comes from `setspawnpointrandomvariation` (stored at `0x22070cc`), `scr_spawn_randomness_range` 50.
  - **Seed:** `G_InitGame` (`0x4fecd0`) sets the state to its `randomSeed` argument (`0x4fed70`), and calls the CRT's
    `srand` with it too. The caller (`0x57a606`) passes **`timeGetTime()`** at map load. So the seed isn't
    reproducible; E115 can seed any way it likes (fixed for tests).
- **Culling.** Influencers are kept sorted on one axis. The loop skips any whose [min, max] range on that axis
  misses the point, and stops at the first that starts past it.
- **Skips.** Disabled influencers, team-mask mismatches, and influencers owned by the spawning player are skipped.
- **Buckets** by influencer type (the script's `eINFLUENCER_TYPE_*`, `_spawning.gsc:120-126`):
  - **0 normal, 2 weapon, 3 dog, 4 vehicle, 5 squad: summed.**
  - **1 player: negatives are summed, but only the single largest positive counts.** This is the friendly
    non-stacking rule. Dvar `spawnsystem_friend_influencer_stacking` (bool, default false; registered at `0x53aafe`)
    sums positives too.
  - **6 game mode: only the influencer with the largest |value| counts.**

**Shapes** (`0x53bb50` sphere, `0x53bc10` cylinder). With d the distance, r the radius and s the score:
- **Sphere:** contributes 0 if d ≥ r. Otherwise it applies the curve to t = d² / r².
- **Cylinder** (corrected 2026-10-26; the earlier "centred on the origin" was wrong):
  - **Axis:** record `+0x44`. It is the script's **`up` argument**: `addcylinderinfluencer` passes forward → `+0x38`
    and up → `+0x44` (`0x521320` → `0x53b6d0` → `0x53b3b0`).
  - **Centre:** `+0x60` = origin + axis × length/2 (`0x53b7b4-0x53b7f7`). So the cylinder runs **from the origin to
    origin + axis × length**, not both ways.
  - **Value:** 0 if |axial offset from the centre| ≥ length/2, or if radial² ≥ r². Otherwise the curve uses
    t = radial² / r² (`0x53bad0`). The axial position has no effect on the value.
  - **Owner orientation** (`0x53b210`): when the influencer has an owner entity, its stored local rotation (a
    quaternion at `+0x50`) is composed with the owner's each update, giving world `+0x38`/`+0x44`.
    - A **weapon**-type influencer whose owner is a client uses the client's view angles (`client+0x124`).
    - Everything else uses the entity's angles (`ent+0x170`) [I for the field names; V for the branch].
  - **So in WaW TDM/FFA:**
    - **Enemy weapon cylinder** (up (1,0,0)): from the enemy's origin **along their aim**, 1750 long, r 350.
    - **Friend strong cylinder** (up (−1,0,0)): from the friend's origin, **1050 straight behind them** (yaw), r 700.
      Its centre is 525 behind.
  - The origin follows the owner [I: the position refresh wasn't traced].

**Curves** (the script's `eINFLUENCER_CURVE_*`, `:128-131`):

| curve | value | note |
|---|---|---|
| 0 constant | s | |
| 1 "linear" | s × (1 − d²/r²) | **quadratic in distance, not linear** |
| 2 "inverse_linear" | s × d²/r² | never used: the script maps "inverse_linear" to curve 1 (`get_score_curve_index` `:315-328`) |
| 3 "negative_to_positive" | s × (2·d/r − 1) | linear in d, from −s at the centre to +s at the edge |

Every TDM/FFA influencer defaults to "linear" (`:879-928`).

**Weapon cylinder sight check** (dvars registered at `0x53aa40-0x53ab3d`, xmm0 = default):

| dvar | default | range |
|---|---|---|
| `spawnsystem_weapon_influencer_sight_check` | true | bool |
| `spawnsystem_weapon_influencer_push_through` | 50 | ±1024 |
| `spawnsystem_weapon_influencer_min_length` | 0.1 | 0.01-1 |
| `spawnsystem_weapon_influencer_update_interval` | 151 ms | 0-5000 |
| `spawnsystem_sight_check_max_distance` | 1800 | 1500-3500 |

The weapon cylinder's length is set in `0x53b050` [V]. The dvar pointers are `0x22081c4` (sight check), `0x2207828`
(push), `0x22081ac` (min length) and `0x22081a8` (interval).
- **When:** for type 2 only, with the sight check on, when `level.time` > last update + interval (`+0x70`).
- **The trace** (`0x500f80`, mask `0x806833`, the owner skipped) runs from the origin to origin + axis × full length
  (`+0x6c`), giving fraction f.
- **The length** (`+0x28`):
  - **1** if f < 0.001
  - otherwise full × max(f, min_length) + push_through, capped at full
- **Vehicles (type 4)** get length = base × 0.5, plus a speed term, instead [I: the speed field wasn't named].

**For E115:** the unified scorer can be rebuilt exactly from this plus the influencer table above, and the sight test
below.

### `isspawnpointvisible(point, angles, team, ignorePlayer)` [V] (`t4mp` `0x521010` → `0x53c320`)

`_spawning.gsc:1212` passes the scored point's origin and angles, **`other_team`** and the spawning player. It returns
true if **any** player on `team` can see the point.

**Loop:** over the 64 client entities (stride `0x330`, `0x1f8e484-0x1f9b084`), skipping a client if:
- it's `ignorePlayer`
- it isn't connected (`client+0x39d4` ≠ 2) [I: field names]
- it isn't playing (`client+0x39ac` ≠ 0, so dead and spectating players don't count)
- it isn't on `team` (`client+0x3a80`)
- **its 2D distance**² is over `spawnsystem_sight_check_max_distance`² (1800 by default; z ignored)

**Facing cull** (no trace if both of these hold):
- d = enemy.xy − point.xy, **not normalised**, with z treated as 0.
- **A:** d · forward(point angles) < 0.2. The enemy is behind or beside the way the spawn faces.
- **B:** d · forward(enemy entity angles, `ent+0x170`/`+0x174`) > −0.2. The enemy isn't facing towards the point.
- Because d isn't normalised, the ±0.2 thresholds are effectively **sign tests**.

**Trace** (`0x501070`, mask `0x806833`, the same as the weapon cylinder; no entity ignored):
- From point + (0, 0, **60**) to enemy origin + (0, 0, **60**).
- **Fixed eye heights, so stance is ignored.**
- It's a world sight trace (`0x556500`), then a second sight check (`0x55b5a0`) [I: probably entities/brush models].
  Both must be clear.
- **The first clear trace returns true.**

**Debug:** dvars `spawnsystem_debug_visibility` (bool) and `spawnsystem_debug_visibility_time` (500 ms, 0-100000).
- On a false result, `0x521010` runs the whole loop **a second time** with a draw flag, only to draw lines and a 16×16×72
  box.
- E115 needs only the first pass.

**For E115:**
- For each live enemy within 1800 2D: skip it if it's behind the spawn's facing and not facing the point.
- Otherwise do a world line trace between the two +60 points.
- **Visible if any trace is clear.**

## 3. Health and regen [V] (`_healthoverlay.gsc`)

- **Max health** 100.
- **Regen delay** = `scr_player_healthregentime`, 5 s (`_tweakables.gsc:350`, `_healthoverlay.gsc:6-11`).
- **Very hurt** means health ≤ 55 % of max (`:5`). Crossing it sets `atBrinkOfDeath`, the red overlay and breathing at
  ≤ 35 % (`:99`).
- **The loop runs every 0.05 s** (`playerHealthRegen` `:79` onwards). Regen starts once 5 s have passed since the last
  damage:
  - **Not very hurt:** health snaps straight to full (`:154`).
  - **Very hurt:** +0.1 of max each tick (`regenRate` `:94`), so about 0.25 s from 55 % to full. The extra
    "hurtTime + 3 s" gate inside is always met once the 5 s delay has passed.
  - **In effect, full health 5 s after the last hit.** `breathing_better` plays when regen starts.
- **Damage** resets the timer and sets `breathingStopTime` to the hit time + 6 s (`:183`).
- **No regen in last stand** (Second Chance perk, `:118`).

## 4. Killstreaks (hardpoints) [V] (`_hardpoints.gsc`)

| kills | streak | notes |
|---|---|---|
| 3 | `radar_mp` (Recon Plane) | team radar for 30 s (`radarViewTime` `:108`) |
| 5 | `artillery_mp` | pick a location. 3 cannons × 5 shells (`scr_hardpoint_artilleryCanonCount` 3, `…ShellCount` 5, `_tweakables.gsc:368-369`). Danger radius 300-750, forward push 1.5, oval scale 6. Only one artillery strike at a time (`level.artilleryInProgress`) |
| 7 | `dogs_mp` | `_dogs.gsc:122-125`: 8 dogs total, at most 4 at once, 60 s, 100 health each. Only one pack at a time (`level.dogs`). Dog kills score 3 |
| 10, 15, 20… | streak notify only | `:1345-1348` |

How streaks work:
- **Thresholds** are hard-coded in `giveHardpointItemForStreak` (`:1328-1372`). Nothing below 3.
- **Force-radar mode.** With `scr_game_forceradar` (radar always on) the ladder shifts to 3 = artillery, 5 = dogs
  (`:1350-1360`).
- **One item held at a time,** on action slot 4. Priority: radar 0, artillery 1, dogs 2. A lower item never replaces a
  higher one you are holding (`giveHardpointItem` `:1444-1479`). An unused item survives death, because it is stored in
  `pers` [I from `giveOwnedHardpointItem` `:1554`].
- **The kill counter.** `cur_kill_streak` goes up on each kill while the attacker is alive
  (`_globallogic.gsc:6537-6545`). A kill by a hardpoint only counts if the owner hasn't died since calling it
  (`requiredDeathCount`). The counter resets to 0 on death (`:6376`, `:6387`).
- **Streak after death.** The tweakable `scr_team_allowHardpointStreakAfterDeath` is 0 (`_tweakables.gsc:338`).
- **Unused setting.** `scr_dog_hardpoint_interval` (180 s) is set but nothing reads it (`:81-86`; grep).

## 5. Bots and testclients [V]

**WaW MP ships no bot AI in script.** What exists is dev-only:
- `_dev.gsc:addTestClients` (`:515-548`) adds `scr_testclients` N clients with the builtin `addtestclient()`.
  - Each one is marked `pers["isBot"]`.
  - It auto-assigns a team, then on every spawn picks a random stock class (`TestClient` `:553-581`).
  - There is no movement or aim logic: they stand still.
- `_dev::init` is wrapped in a dev-only `/# #/` block (`_globallogic.gsc:4560-4562`), so it doesn't run in a ship build.
- `_spawnlogic.gsc:1368-1450` `loopbotspawns` (`scr_killbots`) randomly kills players named "bot…" to test spawns.
- `isBot` only skips some setup and the stats path (`_globallogic.gsc:4983`, `:7123`).

So bots for M4 have to be ours. BO1 is the reference: see §7.

## 6. HUD

| element | what script does | source |
|---|---|---|
| Score bar | Shown for 5 s on spawn: `ui_score_bar` 1, then 0 (`showClientScoreBar`). The bar itself is drawn by the HUD menu from team or player scores. Scores reach it through `setTeamScore` and `self.score` | `_hud.gsc:153-163`; called at `_globallogic.gsc:766`, `:799` [V] |
| Score and time limits | `ui_scorelimit`, `ui_timelimit` dvars | `:2195-2235` [V] |
| Minimap (compass) | `_compass.gsc:setupMiniMap(material)` reads the 2 `minimap_corner` ents, aligns them to `getnorthyaw()`, corrects the aspect ratio with `scr_requiredMapAspectRatio`, then calls `setMiniMap(material, nw.x, nw.y, se.x, se.y)`. The materials are `compass_overlay_map_<map>` | `_compass.gsc:1-71` [V] |
| Enemy dots | Radar shows enemies via `ui_radar_<team>` and the team radar flag. Hardcore hides them (`g_compassShowEnemies` 0) | `_hardpoints.gsc:7-11`; `_globallogic.gsc:1477-1479` [V] |
| Killfeed | Engine `obituary(victim, attacker, weapon, MOD)` on each death. A suicide passes the victim as the attacker | `_globallogic.gsc:6342-6344` [V]; drawing is engine and menu [I] |
| Hardcore | `ui_hud_hardcore` 1 hides most of the HUD | `:1477`, `:3467` [V] |
| Hit marker | `_damagefeedback::updateDamageFeedback` | `:6029` [V] |

**Not dumped:** the HUD menus (`ui_mp/hud.txt` lists them, inside `common_mp.ff`). OAT doesn't unlink T4 menus, so
layout and positions are open. Use an in-game GPU readback screenshot, or a T4 menu parser.

## 7. BO1 and BO2 differences

### BO1 (T5) [V unless marked], from BO1's `common_mp.ff` and `patch_mp.ff`

| | WaW | BO1 |
|---|---|---|
| TDM score limit | 500 | **7500** (`tdm.gsc:64`, max 50000) |
| FFA score limit | 1000 | 1000 (`dm.gsc:55`) |
| kill points | TDM 10, FFA 5 | **TDM 100, FFA 50** (`_rank.gsc:29`, `:50`; `dm.gsc:125`), so TDM is still 75 kills |
| round-win limit | none | `registerRoundWinLimitDvar` added, default 0 |
| health and regen | 100, 5 s, 55 % cutoff, 0.1 per tick | same defaults (`_tweakables.gsc:351-352`, `_healthoverlay.gsc:5`, `:94`), but the regen rate can be changed per class (`_customClasses::getHealthRegenModifier` `:100`) |
| spawn system | unified, same structure | same structure. `scr_spawn_force_unified` added (`patch _spawning.gsc:1196-1199`). Weights re-tuned (below) |
| killstreaks | hard-coded 3/5/7, one held | **chosen by the player.** `registerKillstreak` (`_hardpoints.gsc:46`). The kill count comes from `mp/statstable.csv` (`:63`), with `custom_killstreak_N_kills` overrides (`:206-214`). Hardline-style reduction at `:246-256`. Logic is split over `_killstreakrules.gsc`, `_supplydrop.gsc`, `_dogs.gsc`, `_airstrike.gsc`, `_napalm.gsc`, `_mortar.gsc`, `_helicopter*.gsc` |
| bots | dev testclients only | **real Combat Training bots** in `_bot.gsc` (3178 lines) |

BO1 spawn influencer defaults (`patch/_spawning.gsc:1019-1136`; `k_player_height` 70, `_utility.gsc:477-480`;
corrected 2026-10-26):

| influencer | type | score | curve | size |
|---|---|---|---|---|
| randomness | | 10 | | |
| enemy player | 1 player | −150 | steep | sphere r 30 × 70 = **2100** |
| friend (weak) | 1 player | +10 | steep | sphere r 700 |
| friend strong cylinder | | **not created** | | the creation call and its defaults are commented out (`:407`, `:1038-1041`) |
| enemy weapon cylinder | | **not created** | | commented out (`:379`, `:1054-1057`) |
| dead friend | 0 normal | −100, 20 s | steep | sphere r 700 |
| vehicle | 4 vehicle | −50, leads 3 s | linear | cylinder |
| dog | 3 dog | −150 | steep | sphere r 15 × 70 = 1050 |
| artillery | 0 | −600 | linear | sphere r 1200 |
| grenade / grenade endpoint | 0 | −300 / −300 | linear | sphere r 8 × 70 = 560 each |
| claymore | 0 | −450 | linear | sphere r 9 × 70 = 630 |
| napalm | 0 | −500 | linear | sphere r 750 |
| auto turret | 0 | −650 | linear | sphere r 1200 |
| RC-XD | 0 | −200 | steep | sphere r 25 × 70 = 1750 |
| helicopter | 0 | −500 | linear | cylinder r 2000, length 3500 |
| TV missile | 0 | −400 | linear | cylinder r 2000, length 3000 |
| **enemy spawned** | **7 (new)** | TDM −200 r 1100; FFA −100 r 400; lasts 7 s | constant | sphere at the spawn point just used (`:961-976`, `:1113-1122`, called at `:1209`) |
| objective-facing bonus | | 50 | | for `setspawnpointsbaseweight` in objective modes |

BO1 enum changes [V] (`_spawning.gsc:123-142`):
- **Types:** `SQUAD` (5) is gone. `ENEMY_SPAWNED` = 7 is new.
- **Curves are renumbered:** 0 constant, 1 linear, **2 steep (new)**, 3 inverse_linear, 4 negative_to_positive.
  "inverse_linear" still maps to linear.
- **The "steep" formula is in BO1's engine and wasn't found yet** [open]. Until then, use linear on t (s × (1 − d/r))
  [I: a guess at "steeper than the quadratic"].
- `AddSphereInfluencer` gains a debug-name string argument (e.g. `"enemy_spawned,r,s"`).

So BO1 keeps only spheres for players: a wide enemy repulsion (2100) and a small friend pull (+10). There's no aim
cylinder, plus a 7 s "someone just spawned here" penalty for the other team.

BO1's `statstable.csv` wasn't in the dumped zones, so the per-streak kill counts are [I, from general knowledge]: Spy
Plane 3, RC-XD 3, Counter-Spy Plane 4, SAM Turret 4, Care Package 5, Napalm 5, Sentry Gun 6, Mortar Team 6, Attack
Helicopter 7, Valkyrie Rockets 7, Blackbird 8, Rolling Thunder 8, Chopper Gunner 9, Attack Dogs 11, Gunship 11.

**BO1 bot model [V]: script picks the "what", the engine does the "how".**
- **Script side:**
  - spawns `addtestclient` bots
  - gives rank, random loadout, perks and killstreaks
  - thinks about crates, turrets, killstreaks, dogs, revives and equipment (`_bot.gsc:529-2780`)
- **Engine side:** movement, aim and shooting, tuned by `sv_bot*` dvars that `bot_set_difficulty` (`:402-528`) sets per
  difficulty:

  | dvar | easy | normal | hard | fu |
  |---|---|---|---|---|
  | `MinDeathTime`/`MaxDeathTime` (ms) | 1000/2000 | 500/1000 | 250/500 | 250/500 |
  | `MinFireTime`/`MaxFireTime` | 900/1000 | 600/800 | 400/600 | 100/300 |
  | `YawSpeed` / ADS | 2 / 2.5 | 4 / 5 | 8 / 10 | 14 / 14 |
  | `PitchUp`/`PitchDown` | −20/40 | −10/20 | −5/10 | −5/10 |
  | `Fov` | 50 | 70 | 100 | 160 |
  | `MinAdsTime`/`MaxAdsTime` | 3000/5000 | 3000/5000 | 3000/5000 | 3000/5000 |
  | `MinCrouchTime`/`MaxCrouchTime` | 4000/6000 | 2000/4000 | 100/400 | 100/400 |
  | `TargetLeadBias` | 8 | 4 | 2 | 2 |
  | `MinReactionTime`/`MaxReactionTime` | 1200/1600 | 800/1200 | 400/700 | 30/100 |
  | `StrafeChance` | 0.1 | 0.6 | 0.9 | 1 |
  | `Min/MaxStrafeTime` | 3000/6000 | 3000/6000 | 3000/6000 | 3000/6000 |
  | `AllowGrenades` | 0 | 1 | 1 | 1 |
  | `Min/MaxGrenadeTime` | n/a | 1500/4000 | 1500/4000 | 1500/4000 |
  | `SprintDistance` | 1024 | 512 | 512 | 512 |
  | `MeleeDist` | 40 | 80 | 80 | 80 |
  | `scr_help_dist` | 256 | 256 | 384 | 512 |

  All dvar names are `sv_bot` + the name, except `scr_help_dist`. The default difficulty is "normal" (`:109-112`).
  One in the Chamber overrides fu's reaction and ADS times, and hard/fu's sprint distance (`:515-527`).

These dvars are a ready-made difficulty spec for our bot brain. What the engine does with each one is in
[bo1_bots.md](../../../t5-bo1/notes/e115/bo1_bots.md).

### BO2 (T6) [I, not checked against files]

BO2's MP scripts ship compiled, not as source, so this section is general knowledge only:
- **Scores.** TDM score limit 7500 at 100 per kill, as in BO1. FFA counts kills, with a 30-kill limit in playlists.
- **Scorestreaks.** Streaks charge on points from all actions (kills, assists, objectives), not just kills.
  - Costs run from 400 (UAV) to 1600 or more (Swarm, VTOL Warship).
  - Points from a streak's own kills don't count towards the next streak [I].
- **Pick 10.** The class system.
- **Spawn logic.** Same influencer architecture, re-tuned.
- **Bots.** Combat Training bots carried over (`sv_bot*`-style tuning) [I].

These can be verified later with ACTS decompiling the T6 `.gsc` from BO2's `common_mp`/`patch_mp` (ate47's tools
handle T6).

## 8. Answers to the rules-lib open items [V] (`maps/mp/gametypes/*`)

- **Regen after crossing 55 %** (`_healthoverlay.gsc:79-188`): no snap. `veryHurt` is sticky: it is set when the ratio
  first drops to ≤ the cutoff and only cleared at full health (`:108-112`, `:122-130`). So once a player has been at ≤ 55 %,
  regen after the 5 s delay is +0.1 of max per 0.05 s tick until full (55 % → full in 5 ticks, 10 % → full in 10). The snap to
  full (`newHealth = 1`) only happens if the player never went ≤ 55 % since last being full.
- **FFA with a shared top score** (`getHighestScoringPlayer` `_globallogic.gsc:2022-2052`): returns undefined on a
  shared top score (or if nobody has ≥ 1 point), so `endGame` runs with no winner. Stats count it as a tie for everyone
  (`updateWinLossStats` `:3648`), and nobody gets the victory music (`:1654-1657`). The HUD title (`_hud_message.gsc:540`
  onwards) uses placement, sorted by score then fewer deaths (`updatePlacement` `:2813`): it shows "tie" only if the top
  two also have equal deaths; otherwise the one with fewer deaths sees "victory". At the score limit a tie can't happen
  in practice (the first to reach it ends the match), so it's a time-limit case.
- **Grace period covers prematch.** `level.inGracePeriod = true` is set at init (`:4535`). `startGame` (`:3344-3357`) runs
  the prematch first, then threads `gracePeriod` (`:3499`), which waits a further 5 s (15 s with lives or waves) before
  clearing it. So start spawns (`tdm.gsc:144`) apply for prematch + 5 s. Players are frozen during prematch (`:743`).
- **Killcam and respawn timing** (`_globallogic.gsc:6750-6800`, `_killcam.gsc`):
  - death: 0.25 s watching yourself, then 1.75 s more (`waitForTimeOrNotifies`), so 2.0 s. A quick tap of use (< 0.5 s)
    during it cancels the killcam (`cancelKillCamOnUse` `:6996-7058`).
  - no killcam for suicides, world deaths, or direct kills by artillery, betty, molotov or short frag without a killcam
    entity (`:6420`, `:6700`). `scr_game_allowkillcam` 1 (`_tweakables.gsc:329`).
  - camtime 2.5 s; 4.25 s for frag/short frag/molotov/sticky; 5 s if the player won't respawn; 2.5 s artillery. Post time
    2 s. Override dvars `scr_killcam_time`, `scr_killcam_posttime`. Clipped to the time left in the match.
  - the replay starts camtime + 2.0 s back and lasts camtime + 2 s, so it shows 2.5 s before the death and 2 s after:
    **4.5 s** normally. Use skips it ("press to respawn").
  - then `spawnClient` with no respawn delay (TDM/FFA). So death → respawn ≈ **6.5 s** with a full killcam (8.25 s for
    grenades), **2 s** without.

- **BO1 points** (`t5 common _rank.gsc:27-75`, `dm.gsc:125-132`):

  | event | team-based | FFA (`_rank` else-branch, then `dm.gsc`) |
  |---|---|---|
  | kill, headshot | 100, 100 | 50, 50 |
  | assist 75 / 50 / 25 % / other | 80 / 60 / 40 / 20 | 1 each (`dm.gsc:127-130`) |
  | dog kill / dog assist | 30 / 10 | 20 / 0 |
  | helicopter kill / assist (75/50/25 %) | 200 / 150, 100, 50 (other 50) | 100 / 0 |
  | spy plane kill / assist | 100 / 50 | 25 / 0 |
  | RC-XD destroyed | 50 | 30 |
  | win / loss / tie (multipliers) | 1 / 0.5 / 0.75 | same |

  - **Dog kills are XP only.** The `givePlayerScore("dogkill")` call is commented out, with the comment that dogs no
    longer give team or player score (`_globallogic_actor.gsc:226-233`). The same holds for helicopter kills
    (`_helicopter.gsc:1397`, `giveRankXP`).
  - **No score for using a killstreak.** BO1 removed WaW's 10 "hardpoint" points. Using one gives "medal" XP instead
    (`_hardpoints.gsc:1054-1062`). By streak level (`getXPAmountForKillstreak` `:998-1035`): 1-4 +100, 5 +150, 6-7 +200, 8 +250, 9 +300, 10-11 +350, 12-15 +500.
  - **Time limits:** TDM and FFA are both 10 min (0-1440), the same as WaW. Score limits are TDM 7500 and FFA 1000
    (`tdm.gsc:63-67`, `dm.gsc:54-55`).
  - **For one Reforged ruleset [I: design pick]:** use this BO1 table as the single score table, as §1 says.
    - **Regen timings:** the WaW ones above. BO1 has the same defaults (§7).
    - **Killcam timings:** the WaW ones above. BO1's weren't checked.
    - **FFA ties:** WaW's rule (placement by score, then fewer deaths).
    - **Turned-off WaW extras:** the 3-point dog kill and the 10-point hardpoint use.
    - **OIC:** comes over as a mode on the same table. Kill 100 fits it without change.
- **BO1 One in the Chamber** (`oic.gsc`):
  - **Limits:** 10 min, no score limit (0), 1 round, **3 lives** (`:65-69`).
  - **Loadout:** the `m1911_mp` with 1 in the clip and 0 stock, plus `knife_mp`, plus `specialty_unlimitedsprint`
    (`:105-135`).
  - **Ammo:** a kill gives +1 bullet to the clip (`:356-366`). Ammo carries over when a wager round starts
    (`saveOffAllPlayersAmmo`).
  - **Damage:** any pistol, rifle or head bullet is set to 999999, so a bullet always kills (`:91-100`). Knife damage is
    unchanged.
  - **Turned off** (`:200-211`): CaC, weapon drop, perks, killstreaks and hardpoints. The ammo counter and action slots
    are hidden.
  - **Score:** kill 100, and everything else 0 (`:226-244`). When any player is eliminated, every player still alive or
    with lives gets +10 survivor (`watchElimination`). With multiple rounds and lives, the round winner gets +1
    (`onEndGame`).
  - **Spawns:** `getSpawnpoint_DM` (`:272-276`). The scoreboard shows kills / deaths / stabs / survived (`:88`).
  - **Bot overrides** (`_bot.gsc:515-527`):
    - fu: reaction 400-500 ms, ADS 1000-2000 ms
    - hard and fu: sprint distance 256

## Open items

- The two sight-check callees `0x556500`/`0x55b5a0` are not named (§2 has the visibility rule [V]).
- HUD menu layout (score bar, minimap size and position, killfeed position): menus are not dumped.
- BO1 per-streak kill counts (`mp/statstable.csv`) and all BO2 numbers.
