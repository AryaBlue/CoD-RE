# Killstreaks: WaW, BO1 and BO2 MP

This doc covers how the stock games run the common killstreaks, so Reforged's MP can make the selectable ones do something. For each streak it gives:
- the threshold;
- what it does, with its numbers;
- the assets it uses;
- how bots should use it.

Researched 2026-10-28.

## Conventions

- **Tags:**
  - **[V]** read in the game data or scripts, citing file and function;
  - **[I]** inferred;
  - **[U]** unknown or not in the data.
- **Script sources:**
  - WaW and BO1 ship their MP scripts as plain text: OAT Unlinker rawfiles of `common_mp.ff`, with BO1's `patch_mp.ff` overriding.
  - BO2 ships them as bytecode. They were decompiled with gsc-tool (`-m decomp -g t6 -s pc`) from `common_mp.ff`, `common_patch_mp.ff` and `patch_mp.ff`, patch last.
  - Script paths below are the in-game ones (`maps/mp/...`), sometimes shortened to `killstreaks/...` or `gametypes/...`.
- **Tables:**
  - `mp/statstable.csv` (BO1: `code_post_gfx_mp.ff`; BO2: `patch_mp.ff`), `mp/scoreinfo.csv`;
  - the weapon infostrings (`weapons/*_mp`);
  - BO2's vehicle defs, from `zonedump --vehicles` on `common_mp.ff`.
- No script text is copied here. Logic is described in prose with numbers, names and file:function references.
- **Related docs:**
  - WaW's earn and hold rules are also in [mp_t4_tdm_ffa.md](../../../games/t4-waw/notes/e115/mp_t4_tdm_ffa.md) §4.
  - The BO1/BO2 threshold columns and the default three streaks are in [mp_rules_t4_t5_t6.md](mp_rules_t4_t5_t6.md) §3. The numbers here agree with both.
  - Reforged's `games/reforged/mp/Killstreaks.{h,cpp}` already holds WaW's earn/hold/use state, but no effects.

## Summary

| | WaW (t4) | BO1 (t5) | BO2 (t6) |
|---|---|---|---|
| earned by | kills: a fixed 3 / 5 / 7 ladder, one item held [V] | kills: the player picks 3; counts in statstable col 5 [V] | score (momentum): the player picks 3; costs in statstable col 16 [V] |
| on death | streak to 0; the held item is kept [V] | kill count to 0; unused earned streaks are kept as a stack [V] | momentum to 0 at spawn; unused streaks are kept [V] |
| kills with a streak | count only if called in the same life [V] | never count [V] | give 25 points, not the kill's 100 [V] |
| recon | recon plane 3 kills, 30 s, minimap only (no plane) [V] | spy plane 3; about 40 s of radar (20 s orbit + 20 s exit) [V] | UAV 425; 25 s, fast sweep with two up [V] |
| counter | — | counter-spy plane 4, 30 s jam (client-side) [V] | counter-UAV 600, 30 s scramble [V] |
| package | — | care package 5 [V] | care package 550 [V] |
| others here | artillery 5, dogs 7 | RC-XD 3, napalm 5, mortar 6, attack helicopter 7, dogs 11 | RC-XD 450, hunter-killer 525, lightning strike 750, sentry 800 |

**Shared engine-side unknowns.** The scripts only switch radar on or off, or into a mode (normal or fast). The engine's compass code decides several things [U] for all three games:
- how pings are drawn and how often they refresh;
- what the sweep line looks like;
- what a counter-UAV jam draws.

WaW is the exception for the timing: its compass defaults were read from `t4mp.exe` (refresh 4 s, ping fade 4 s, range 2500) [V].

**For Reforged** [I]:
- Recon and counter are minimap state on a timer per team. For WaW and BO1 FFA the radar is per player.
- Care package, RC-XD, hunter-killer and lightning strike are mostly radius damage and timed movers.
- Dogs and the attack helicopter need AI. The sentry needs turret targeting.

## World at War (t4)

Sources: stock MP scripts and weapon infostrings (`weapons/`) from `common_mp.ff`, and its asset list, and for a handful of engine dvar defaults the Plutonium `t4mp.exe` (`<Plutonium install>/games/t4mp.exe`), read by disassembling its dvar registration calls. Short names used below: `HP` = `maps/mp/gametypes/_hardpoints.gsc`, `GL` = `maps/mp/gametypes/_globallogic.gsc`, `TW` = `maps/mp/gametypes/_tweakables.gsc`, `DOGS` = `maps/mp/_dogs.gsc`.

Tags: [V] read directly in data/script/exe, [I] inferred, [U] unknown.

### 0. Shared framework (applies to all three)

**Registration** [V] `HP init()`
- The hardpoint list is `level.hardpointItems`. Each entry maps a weapon name to a priority: `radar_mp`=0, `artillery_mp`=1, `dogs_mp`=2. An entry is only added when its tweakable is on: `scr_hardpoint_allowradar`, `scr_hardpoint_allowartillery`, `scr_hardpoint_allowdogs`, all defaulting to 1 (`TW` registerTweakables). If one is disabled, the priorities of the later ones shift down by one.
- `scr_game_hardpoints` set to 0 disables giving any hardpoint (`HP giveHardpointItem()`). If the dvar is empty, hardpoints are allowed.
- The location selector material `map_artillery_selector` and the shellshocks `artilleryblast_friendly` and `artilleryblast_enemy` are precached.
- Using a hardpoint awards XP event `"hardpoint"` worth 10 (`registerScoreInfo`).

**How streaks accrue** [V] `GL` Callback_PlayerKilled (around lines 6520–6540)
- `cur_kill_streak` goes up by one for each kill of an enemy player, but only when all of these hold:
  - the attacker is alive at the moment of the kill;
  - one of these is true: there is no eInflictor, or the eInflictor has no `requiredDeathCount`, or the attacker's `deathCount` equals the eInflictor's `requiredDeathCount`.
- After each increment, `HP giveHardpointItemForStreak()` runs.
- Killing a dog does not add to the streak. `GL Callback_ActorKilled` only gives `dogkill` score: 3 in team modes, 2 in FFA (`_rank.gsc init`). [V]

**Thresholds** [V] `HP giveHardpointItemForStreak()`
- These are hard-coded script constants with no dvar. They fire on exact equality: 3 gives `radar_mp`, 5 gives `artillery_mp`, 7 gives `dogs_mp`.
- From 10 upwards, every multiple of 5 shows only a "KILLSTREAK N" splash (`streakNotify`) with no reward.
- If `scr_game_forceradar` is 1, the table changes to 3 = artillery and 5 = dogs, with no radar reward. In that mode every player has the compass showing enemies all the time, because `g_compassShowEnemies` is set from that dvar on connect (`GL` around line 4666).
- There is a commented-out `kamikaze_mp` at 10/15. It is dead code.

**Reset** [V] `GL` Callback_PlayerKilled (around lines 6355–6375)
- `cur_kill_streak` is set to 0 on every death, including being team-killed and suicide.
- The streak is per life only. It is initialised to 0 on connect (`GL` around line 4812).
- `deathCount` goes up by one on each death.

**Do hardpoint kills count towards the next streak?** [V] for the mechanism, [I] for the summary.
- When an item is given, `self.pers["hardPointItemDeathCount"+type]` stores the current `deathCount` (`HP giveHardpointItem()`).
- That stored value is copied onto the damaging entity as `requiredDeathCount`: the artillery shell projectile (`callStrike_artilleryBombEffect`) and the first wave of dogs (`dog_set_owner`).
- Tweakable `scr_team_allowHardpointStreakAfterDeath` (default 0):
  - at 0, the stored death count is used;
  - at 1, the death count at the moment of use is used (`HP triggerHardPoint`, `HP useArtillery`).
- Net effect at defaults:
  - artillery or dog kills do count towards the next streak, as long as the owner earns and uses the item in the same life;
  - if the owner dies with the item unused, then uses it after respawning, its kills still score points but do not extend the new streak.
- Quirk [V]: replacement dogs (dogs 5 to 8) are spawned without a `requiredDeathCount` (`DOGS dog_manager_spawn_more_dogs_on_death` leaves out that argument). Their kills therefore always count towards the owner's streak, provided the owner is alive at the time [I].

**Inventory: one slot, priority-gated** [V] `HP giveHardpointItem()`
- A player holds at most one hardpoint, in `self.pers["hardPointItem"]`. It is given as a weapon with 1 ammo and bound to action slot 4.
- A new item is refused if its priority is lower than the item already held. So:
  - an unused artillery blocks a later radar;
  - reaching 7 while holding unused artillery replaces it with dogs, and the artillery is lost.
- If the player is currently in the location selector with a hardpoint equipped, `giveHardpoint` waits for `stop_location_selection` before giving the new item.
- The item survives death: `pers` keeps it, and `hardpointItemWaiter` → `giveOwnedHardpointItem` gives it back on spawn without updating its death count.
- Whether `pers` (and so the held item) carries across rounds in round-based modes is [U]. It is not explicitly cleared in the code read.

**Activation** [V] `HP hardpointItemWaiter()`
- A per-life thread is started from `GL` spawnPlayer (around line 826).
- It waits for `weapon_change`. When the new weapon is `radar_mp`, `artillery_mp` or `dogs_mp`, it calls `triggerHardPoint`.
- On success:
  - logs the use;
  - credits mission/challenge progress (`_missions::useHardpoint`);
  - gives the `"hardpoint"` XP;
  - takes the weapon away, clears slot 4 and clears `pers["hardPointItem"]`.
- Either way, the player is then switched back to their previous weapon.
- If the call fails (artillery cancelled or busy, dogs busy), the item stays.
- `triggerHardPoint` sends the notify `hardpoint_used` with the type.

**Earned notification** [V] `HP hardpointNotify()`
- It first waits for `playerKilledChallengesProcessed`, then 0.05 s.
- The splash title is `MP_KILLSTREAK_N` with the streak number. The text is from `level.hardpointHints` (`MP_EARNED_RADAR`, `MP_EARNED_ARTILLERY`, `MP_EARNED_DOGS`).
- Sound from `level.hardpointInforms`:

| Item | Sound |
|---|---|
| radar | `mp_killstreak_radar` |
| artillery | `mp_killstreak_jet` |
| dogs | `mp_killstreak_dogs` |

- Leader dialogue keys:

| Item | Key |
|---|---|
| radar | `radar` |
| artillery | `artillery` |
| dogs | `dogsupport` |

- Global dialogue keys set in `HP init()`:

| Event | Friendly | Enemy |
|---|---|---|
| Radar online | `ourradaronline` | `enemyradar` |
| Artillery inbound | `friendlyartillery` | `enemyartillery` |
| Dogs inbound | `friendlydogs` | `enemydogs` |

  The radar-offline keys are empty strings.

**Debug helpers** [V] `maps/mp/gametypes/_dev.gsc`: dvars `scr_giveradar`, `scr_giveartillery` and `scr_givedogs` give the item to all players; `scr_usedogs <name>` triggers dogs for the named player.

**Helicopter** [V]
- `maps/mp/_helicopter.gsc` and `maps/mp/gametypes/_copter.gsc` are present in the zone, but nothing calls them. A search across all `.gsc`/`.csc` files finds no `_helicopter::`, `_copter::` or `_ac130::` call.
- In `HP`, `helicopter_mp` appears only in commented-out lines. They are leftover CoD4 code and are unused in WaW MP.
- `HP doAirstrike` / `callAirStrike` / `doPlaneStrike` (a CoD4-style plane bombing run using model `vehicle_jap_airplane_zero_fly_player`) is also dead: the only caller is commented out in `useArtillery`.

### 1. Recon plane (`radar_mp`), 3 kills

**Earned**: streak exactly 3 (see §0) [V].

**What it does** [V] `HP useRadarItem()`, `useTeamRadar()`, `usePlayerRadar()`, `setTeamRadarWrapper()`, `RadarAcquiredPrintAndSound()`
- Use is instant: there is no target selection and no condition that can block it.
- **No plane exists.** Script spawns no entity, model or sound for a plane. The effect is HUD only. [V]
- **Duration**: `level.radarViewTime` = 30 s, a hard-coded constant with no dvar (`HP init()`) [V].
- **Team modes**:
  - calls the engine builtin `setTeamRadar(team, true)`;
  - sets the server-info dvar `ui_radar_allies` or `ui_radar_axis` to 1;
  - sends the level notify `radar_status_change`;
  - after 30 s, calls `setTeamRadar(team, false)`, clears the dvar and notifies again;
  - prints `MP_WAR_RADAR_EXPIRED` to the owning team and `MP_WAR_RADAR_EXPIRED_ENEMY` to the enemy team.
- **Refresh, not stack** [V] `useRadarItem`: a new use by the same team first sends `radar_timer_kill_<team>`, which ends the running timer. The 30 s restarts from the new use; the times do not add up.
- **Who sees whom**: every member of the calling team sees every enemy player on the compass/minimap for the duration. The visibility test itself is engine code; script only flips `setTeamRadar`. [V] for the call, [I] that it reveals all enemies.
  - In FFA (`!level.teambased`), only the caller gets radar. Script sets `self.hasRadar = true` and client dvar `ui_radar_client` = 1 for 30 s, then clears both and prints `MP_WAR_RADAR_EXPIRED`. That `hasRadar` is an engine-read client field is [I], because script never reads it.
- **Sweep vs constant**: enemies are shown as periodic pings, not continuously. [V] for these engine dvar defaults, read from the `t4mp.exe` dvar registration (around 0x432f40):

| Dvar | Default | Min | Max | Description string |
|---|---|---|---|---|
| `compassRadarUpdateTime` | 4 | 0.01 | 60 | "Time between radar updates" |
| `compassRadarPingFadeTime` | 4 | 0.01 | 60 | "How long an enemy is visible on the comp..." |
| `compassRadarLineThickness` | 0.4 | 0.01 | 10 | sweep-line thickness, relative to compass size |
| `compassMaxRange` | 2500 | | | max range from the player shown on the compass |
| `compassSoundPingFadeTime` | 2 | | | sound-overlay ping fade |
| `compassEnemyFootstepEnabled` | false | | | |
| `compassEnemyFootstepMaxRange` | 500 | | | |
| `compassEnemyFootstepMaxZ` | 100 | | | |
| `compassEnemyFootstepMinSpeed` | 140 | | | |

  So positions refresh every 4 s and each ping fades over 4 s. With the defaults, a dot is effectively visible the whole time and moves in 4 s steps. [I]
  - The exe contains the material `compass_radarline` and the dvar `cg_hudMapRadarLineThickness`. This points to a visible sweep line crossing the map once per update period. [V] for the strings, [I] for the behaviour.
  - Enemy ping materials: `compassping_enemy`, `compassping_enemyfiring`, `compassping_dog`, `compassping_friendly`, `compassping_player`. [V] in the exe and the zone list. Which one is used in which case is engine-side [I].
- **Perk counter** [V]: in `_gameobjects.gsc shouldShowCompassDueToRadar()`, an objective carrier with `specialty_gpsjammer` (WaW's Camouflage perk) does not reveal the carried objective to an enemy team's radar. That the engine also hides `specialty_gpsjammer` players from radar pings is [I]: it is standard IW-engine behaviour, but not visible in script.
- **Objectives** [V] `_gameobjects.gsc updateVisibilityAccordingToRadar()`: carried game objects (flags, bombs) recompute their compass icons on each `radar_status_change`. While a team has radar, an enemy carrying an objective shows that objective on their compass.
- **Announcements** [V] `RadarAcquiredPrintAndSound()`:
  - the owning team gets leader dialogue `radar_online` and the enemy gets `enemy_radar_online`, at most once per 30 000 ms per team (`level.radarTimers`);
  - inside that window, only the caller hears `radar_online`;
  - battle chatter `onKillstreakUsed("recon", otherTeam)` plays;
  - `iprintln`: the owner's team gets `MP_WAR_RADAR_ACQUIRED` (caller, 30) and the enemy team gets `MP_WAR_RADAR_ACQUIRED_ENEMY` (30);
  - in splitscreen, the friendly sound plays locally on player 0.
- **Stats**: `pers["uav_used"]`++ (`triggerHardPoint`); it is reported as `ps_r` / `numUavCalled` (`GL` around line 1400).
- In the `koth` and `sur` gametypes, `mp_killstreak_radar` is reused as a generic alert sound [V].

**Assets** [V] (`weapons/radar_mp`, `HP`)

| Kind | Names |
|---|---|
| Weapon def | `radar_mp`: weaponType grenade, inventoryType item, ammo 1/1, ammoName/clipName `calldown`, sharedAmmoCapName `WEAPON_HARDPOINT` |
| Models | view `viewmodel_mp_handheld_radio`, world `prop_mp_handheld_radio`, hands `viewmodel_hands_no_model` |
| Anims | `radio_handheld_idle`, `radio_handheld_pullout`, `radio_handheld_putaway`; playerAnimType `radio` |
| HUD / d-pad / kill icon | `hud_icon_spyplane` (image `hud_spyplane`) |
| Minimap | `compass_radarline`, `compassping_enemy`, `compassping_enemyfiring` (engine-side) |
| Weapon sounds | raise `weap_c4detpack_safetyoff_npc` / `_plr`, putaway `weap_c4detpack_safety_npc` / `_plr` |
| Notification sound | `mp_killstreak_radar` |
| Dialogue suffixes | `ourradaronline`, `enemyradar` (prefixed with `game["voice"][team]`) |
| Strings | `MP_EARNED_RADAR`, `MP_RADAR_NOT_AVAILABLE` (precached but unused for radar), `MP_WAR_RADAR_ACQUIRED`, `MP_WAR_RADAR_ACQUIRED_ENEMY`, `MP_WAR_RADAR_EXPIRED`, `MP_WAR_RADAR_EXPIRED_ENEMY` |

**Bots** [I] (stock has no bot logic, see §4)
- Use it as soon as it is earned. It cannot be wasted or blocked, and holding it only blocks lower items.
- Exception: hold it briefly if the team already has radar with more than about 20 s left, then fire it when the current one is close to expiring. Re-use resets the timer rather than adding to it, so firing early wastes it.
- While the bot's team has radar, give bots perfect knowledge of enemy positions at 4 s granularity, as last-known positions: no wall-hacks between pings. Skip enemies with `specialty_gpsjammer`.
- When the enemy has radar, bots should value Camouflage, or keep moving, since a ping only shows positions.

### 2. Artillery strike (`artillery_mp`), 5 kills

**Earned**: streak exactly 5 (or 3 with `scr_game_forceradar`) [V].

**Targeting** [V] `HP triggerHardPoint`, `selectArtilleryLocation()`, `useArtillery()`
- If `level.artilleryInProgress` is set (one strike at a time, server-wide, across both teams), the player gets `MP_ARTILLERY_NOT_AVAILABLE` and keeps the item.
- Otherwise, `beginLocationSelection("map_artillery_selector", 900)` opens the map selector. The radius is `artilleryDangerMaxRadius` 750 × 1.2.
- The selection ends on cancel, death, disconnect, use or game end; the item is kept unless a location was confirmed.
- On `confirm_location`, the in-progress flag is checked again. Then the target height is worked out:
  - a trace from 10 000 units above the caller down to the caller;
  - the hit Z minus 514 is used as the start height;
  - `doArtillery` then traces 10 000 units straight down from there at the chosen XY to find the ground;
  - map-hole failsafe: if nothing is hit, the caller's Z is used.
- The target gets a random offset of 0–9 units (`randPointRadiusAway` with `RandomIntRange(0,10)`).
- A compass marker is shown with the builtin `artilleryiconlocation(targetpos, team, 1)`. `artilleryWaiter()` hides it when the strike ends (on `artillery_status_change`).
  - The exe has the materials `compass_objpoint_flak_friendly` and `compass_objpoint_flak_busy` [V strings]. That these are the marker icons is [I].

**Firing direction** [V] `HP getBestFlakDirection()`, `get_random_artillery_origins()`
- If the map has entities with targetname `artillery_<team>`, their origins are the candidate gun positions.
- Otherwise, 6 random points are generated beyond the spawn bounds along the map's long axis: 3 per end. The bounds used are `level.spawnMins`/`spawnMaxs` expanded by 1000.
- The candidate chosen is the one whose map-centre line passes closest to the target, preferring candidates on the far ("negative") side of the map centre.
- The yaw is the direction from that candidate to `level.mapcenter`. So shells arrive along a map-wide axis, not straight from the gun spot.

**Shells, timing and spacing** [V] `HP callArtilleryStrike()`, `startArtilleryCanon()`, `doArtilleryStrike()`
- **3 cannons**, hard-coded as three threads.
  - Cannon A: yaw −(1 or 2)°, firing distance 10 000 − rand(−100..100).
  - Cannon B: exact yaw and distance 10 000.
  - Cannon C: yaw +(1 or 2)°, distance 10 000 − rand(−100..100).
  - Each cannon starts after a random delay of 0–3 s.
- **5 shells per cannon** (tweakable `scr_hardpoint_artilleryCanonShellCount`, default 5), giving **15 shells total**.
  - `scr_hardpoint_artilleryCanonCount` (default 3) only feeds the in-flight shell counter `level.artilleryShellsInAir` = cannons × shells. It does not change the number of cannon threads, so a value other than 3 desyncs the end-of-strike wait. [V] for the code, [I] for the consequence.
- **Volleys**: `volleyCount` = 1. Each cannon picks an aim point exactly r units from the target in a random direction, r ∈ [0, 500].
- Each shell then waits rand(2–4) s and lands at randint(0..519) units from that aim point. Shells therefore spread up to about 1020 units from the target, most within a few hundred units [I]. Per cannon, shells are 2–4 s apart; with 3 cannons overlapping, there is roughly one impact every 0.7–1.3 s [I].
- **Ballistics**:
  - each shell is a real projectile, `owner launchbomb("artillery_mp", firePos, velocity)`;
  - firePos is 10 000 units back along the yaw from the shell's own strike position;
  - pitch is `scr_artilleryAngle` (if 0 or unset, 60° upward), with a random offset of −3 to +2°;
  - the speed is solved from the range formula using `g_gravity` (engine default **800** [V], from the exe registration around 0x4fc650).
- Flight time = distance / (v·cos pitch). At 60° with g = 800 that is v ≈ 3040 u/s and **about 6.6 s from launch to impact** [I, computed]. That makes the first impact land about 8.5–13.5 s after the call: 0–3 s cannon delay + 2–4 s shell wait + about 6.6 s flight.
- Player-facing delay after confirming: about 9–14 s to the first shell. The last shell lands about 16–29 s after the call [I, computed]. A safety cap in `doArtillery` ends the strike 45 s after the call regardless [V].
- The in-progress flag clears when all 15 projectiles have sent `death` (`referenceCounter`), or at the 45 s cap. Only after that can anyone call a new strike.

**Damage** [V] `weapons/artillery_mp`
- Each shell is an impact-exploding (`projImpactExplode` 1) splash: **explosionRadius 512, explosionInnerDamage 200, explosionOuterDamage 50**, damageConeAngle 180. Weapon `damage` is 1000 (direct hit).
- Player max health is 100 (`scr_player_maxhealth` in `TW`), so roughly the inner two-thirds of the radius kills outright, if falloff is linear [I].
- Per-impact extras [V] `HP artilleryImpactEffects()`, `radiusArtilleryShellshock()`:
  - rumble `artillery_rumble`;
  - shellshock `artilleryblast_enemy` on every living player within 1.1 × the impact radius (about 563), for **3 s at the centre down to 1.5 s at the edge**, applied to every player near the impact, both teams;
  - screen shake `earthquake(0.7, 0.75 s, pos, 1000)`.
- Further rules:
  - vehicles take ×2.75 from `artillery_mp` (`GL GetVehicleProjectileScalar`) [V];
  - with friendly fire off, a teammate takes no damage but still gets the shellshock/rumble (`GL` around line 5907, `damageShellshockAndRumble`) [V];
  - the team-kill penalty for artillery is ×0.25 (`scr_team_artilleryTeamKillPenalty`) [V];
  - artillery is excluded from `isPlayerExplosiveWeapon` (`_class.gsc`) [V].
- Kills are tracked in `pers["artillery_kills"]` (`GL incKillstreakTracker`) [V]. The killcam treats `artillery_mp` as an inflictor-cam weapon (`GL` around lines 6671 and 6699) [V].
- The unused `losRadiusDamage` (512 radius, 200→30, indoor ×4 distance advantage) belongs only to the dead plane-strike path [V].

**Danger awareness / spawning** [V]
- A danger centre is registered at the target for the strike's duration: min radius 300 (danger 1), max 750 (danger 0), linear between (`HP getSingleArtilleryDanger`). The plane-strike oval values (×6 stretch, push 1.5) only apply to the dead airstrike path, because artillery uses a zero forward vector.
- A spawn influencer is created at the target with radius 937.5 (750 × 1.25) and score −800, linear curve (`scr_spawn_artillery_influencer_score`, `_spawning.gsc create_artillery_influencers`).
- Warnings, not in hardcore: teammates of the caller within 937.5 units (2D) get the bold message `MP_WAR_ARTILLERY_INBOUND_NEAR_YOUR_POSITION`. The caller's team gets `MP_WAR_ARTILLERY_INBOUND` (caller name).
- Dialogue: `artillery_inbound` for the caller's team and `enemy_artillery_inbound` for the enemy team, plus battle chatter `onKillstreakUsed("artillery")`. In FFA, only the caller hears it.
- The air-raid siren `air_raid_a` plays on the entity `air_raid_1`, if the map has one.
- `GL waitForTimeOrNotifyNoArtillery` keeps a pending wait (for example the round-end delay) going while a strike is in progress [V].

**Assets** [V]

| Kind | Names |
|---|---|
| Weapon def | `artillery_mp`: weaponType bomb, impactType `mortar_shell`, guidedMissileType Ballistic, projectileLifetime 20, projExplosionType rocket |
| Models | projectile `weapon_mp_shell`; view/world handheld radio as for radar |
| FX | trail `weapon/rocket/fx_lci_rocket_geotrail`; `weapon/artillery/fx_artillery_strike_dirt_mp` is loaded into `level.artilleryfx` but never used in script; the explosion FX key is not set in the def [U] |
| Sounds | `artillery_whistle` (projectile), `artillery_launch` (ignition), `artillery_impact` (explosion), `air_raid_a`, `mp_killstreak_jet` (earned) |
| Rumble / shock | `artillery_rumble`; `artilleryblast_enemy`, `artilleryblast_friendly` (the latter precached but unused) |
| HUD | hud / d-pad icon `compass_objpoint_flak`; kill icon `hud_icon_artillery` (image `hud_artillery`); selector `map_artillery_selector` |
| Strings | `MP_EARNED_ARTILLERY`, `MP_ARTILLERY_NOT_AVAILABLE`, `MP_WAR_ARTILLERY_INBOUND`, `MP_WAR_ARTILLERY_INBOUND_NEAR_YOUR_POSITION` |

**Bots** [I]
- Fire when not `level.artilleryInProgress`.
- Choose the target as the centroid of the densest cluster of known enemies, using radar pings or last-seen positions. Weight positions by how long the enemies have stayed there, since impacts start about 9 s after the call.
- Reject any point within about 1000 units of a teammate when friendly fire is on. Even with it off, avoid them because of the shellshock.
- Good fallback: aim at the enemy spawn area or a held objective.
- While a strike is active, every bot should treat the danger centre (radius 750, centre to 300 fully dangerous) as a no-go area and route out of it. Enemy bots should do this when they hear `enemy_artillery_inbound`; spawning already avoids it through the influencer.
- Bots should not sit on unused artillery near 7 kills: the dogs would replace it.

### 3. Attack dogs (`dogs_mp`), 7 kills

**Earned**: streak exactly 7 (or 5 with `scr_game_forceradar`) [V].

**Gating** [V] `HP triggerHardPoint`, `DOGS dog_manager_spawn_dogs`
- Only one dog pack exists server-wide. If `level.dogs` is defined, the player gets `MP_DOGS_NOT_AVAILABLE` and keeps the item.
- Requirements: the map must have an actor spawner with targetname `dog_spawner` and usable path nodes (`level.no_dogs`).
  - If either is missing, the spawn function just returns, but `triggerHardPoint` has already returned true, so **the item is consumed for nothing** [V].
- `scr_dog_hardpoint_interval` (default 180, into `level.dogsInterval`) is set up but never read: dead [V].

**Numbers** [V] `DOGS dog_dvar_update()`. These are re-read every 1 s by `dog_dvar_updater`.

| Dvar | Default | Meaning |
|---|---|---|
| `scr_dog_count` | 8 | dogs in the pack in total; capped so that it plus any dogs already in the BSP is at most 16 (engine maximum) |
| `scr_dog_max_at_once` | 4 | dogs alive at once (clamped to ≤ count) |
| `scr_dog_health` | 100 | health per dog |
| `scr_dog_time` | 60 | lifetime in seconds, from the call |

- **Spawning**:
  - the first 4 spawn one after another, with a wait `randomfloat(2, 5)` between each. The GSC `randomfloat` takes one argument, so the effective gap is [U]: either 0–2 s or 2–5 s;
  - after that, each `dog died` notify triggers the same wait and one replacement, until the 4 replacements are used up, giving 8 in total;
  - spawn node choice: nodes with `script_noteworthy` `spawn`, or 20 random path nodes. In team modes the choice favours nodes far from enemies and near allies (`dog_pick_node_near_team`); in FFA it favours nodes about 1600 units from all players, with a penalty under 1200 (`dog_pick_node_away_from_enemy`). Both avoid line of sight to the two closest enemies (penalty 100 000) and reuse within 3 s.
- **End**:
  - after 60 s, `dogs leaving` is sent. Each dog sets `ignoreall`, uses goal radius 30 and runs to the closest exit node (`script_noteworthy` `exit`, or 20 random nodes), then is deleted;
  - failsafe: a dog that moves less than 10 units in 2 s is deleted, and any remaining dog is deleted 22 s after leaving begins;
  - game end also triggers leaving;
  - when all dogs are dead or gone (checked every 1 s once all have spawned or leaving has started), the dogs are deleted, `level.dogs` is cleared and `dogs done` is sent. Only then can another pack be called.
- **Dog AI** [V] `DOGS init_dog`, `dog_patrol`:
  - aiteam = the owner's team (`"free"` in FFA); owner set with `setentityowner`;
  - `aiweapon` `dog_bite_mp`;
  - goalradius 128, `pathEnemyFightDist` 512, `meleeAttackDist` 102 (with a 30-unit buffer in `animscripts/dog_combat.gsc`);
  - `ignoreSuppression` on, accuracy 0.2;
  - with no enemy, it patrols random nodes from a pool of 200 path nodes; enemy selection is engine AI.
- **Bite**:
  - `animscripts/dog_combat.gsc` uses the engine `melee()` with notetracks `dog_melee` and `dogbite_damage`;
  - the victim gets shellshock `dog_bite` for 1 s;
  - after an attack starts, another dog must wait 200 ms before attacking the same player (`setNextDogAttackAllowTime(200)`);
  - `level.maxDogsAttackingPerPlayer` = 2 is set but unused [V].
  - Bite damage: `dog_bite_mp` has meleeDamage **90** [V def]. That `melee()` uses this value is [I]. So one bite leaves a 100-health player on 10 and the second kills, unless the knockdown/neck-snap anim sequence (`player_view_dog_knockdown*` xanims) kills outright [U].
  - Kill credit goes to the owner (`GL` around line 6305). The obituary means of death is changed to pistol to hide the melee icon (around line 6322). Kills are counted in `pers["dog_kills"]`.
- **Health regen** [V] `DOGS dogHealthRegen`:
  - regen is enabled with a delay of 5 s;
  - a dog that took damage returns to full health once the delay has passed without new damage;
  - if it dropped to 55 % or below, it instead climbs by 0.1 of max health every 0.05 s once more than 3 s have passed since it was badly hurt. This is gated by the same 5 s delay.
- **Damage rules** [V] `GL` Callback_ActorDamage: the owner cannot damage their own dogs except in hardcore, and dogs with the same owner cannot damage each other. Flash and concussion on dogs: `DOGS flash_dogs` applies `setFlashBanged(true, 500)` to enemy dogs in the area, at most once per 1.5 s.
- **Spawn influence** [V] `_spawning.gsc`: each dog gets a sphere influencer of radius 15 × player height, score −300 linear (`scr_spawn_dog_influencer_score`), against the enemy team.
- **Announcements** [V] `triggerHardPoint`: dialogue `dogs_inbound` for the caller's team and `enemy_dogs_inbound` for the other team, battle chatter `onKillstreakUsed("dogs")`, and `MP_DOGS_INBOUND` (caller) to the team. In FFA, the caller hears `dogs_inbound` and everyone else hears `enemy_dogs_inbound`.
- Killing a dog: `dogkill` score of 3 in team modes (2 in FFA), plus the challenge notify `selfdefense_dog`. It does not add to the killer's kill streak.

**Assets** [V]

| Kind | Names |
|---|---|
| Weapon defs | `dogs_mp` (calldown item, ammo 1, sharedAmmoCap `WEAPON_HARDPOINT`, view model `viewmodel_usa_no_model`, world `prop_mp_handheld_radio`); `dog_bite_mp` (AI bite weapon, meleeDamage 90) |
| Models | friendly view `german_shepherd`, enemy view `german_shepherd_black` (`setEnemyModel`), `zombie_wolf` if dvar `use_zombie_dog` is set |
| Anim tree | `dog.atr`; scripts `maps/mp/animscripts/dog_*.gsc`; player xanims `player_view_dog_knockdown`, `_late`, `_saved`, `_neck_snap`, `_neck_miss` |
| FX | `impacts/fx_deathfx_dogbite`, `impacts/fx_deathfx_dogbite_dmg` |
| Shock | `dog_bite` (`shock/dog_bite.shock`) |
| Sounds | barks `anml_dog_bark`, `anml_dog_bark_close`, `anml_dog_bark_attack_mid`, `anml_dog_bark_attack_close` (`clientscripts/mp/_dogs.csc` movement-state table: normal every 1–4 s; mid every 0.5–2 s within 1500; close every 0.01–0.1 s within 1000); `anml_dog_attack_fence`, `anml_dog_attack_jump`, `anml_dog_attack_kill_player`, `anml_dog_attack_miss`; `mp_killstreak_dogs` (earned) |
| HUD | hud / d-pad / kill icon `compass_objpoint_dogs` (image `hud_dogkill`); `hud_dog_melee` (hint `hint_dog_melee`); minimap ping `compassping_dog` (exe string) |
| Strings | `MP_EARNED_DOGS`, `MP_DOGS_NOT_AVAILABLE`, `MP_DOGS_INBOUND` |
| Map requirements | actor spawner targetname `dog_spawner`; optional path nodes with `script_noteworthy` `spawn` / `exit` |

**Bots** [I]
- Use immediately unless `level.dogs` is defined. If it is, keep the item and retry every few seconds.
- In the engine, refuse or skip the item when the map has no dog spawner or nav. Stock silently wastes it, which a reimplementation need not copy.
- Enemy bots should:
  - treat dogs as high-priority, fast melee threats: target them before players within about 500 units;
  - back into corners or face the approach direction, because two bites kill;
  - expect the pack to last at most 60 s, or until 8 dogs have died.

### 4. Stock bot behaviour

- There is no bot AI for hardpoints in WaW MP [V].
- The only bots are dev test clients: `maps/mp/gametypes/_dev.gsc addTestClients()`, driven by `scr_testclients`, which sets `pers["isBot"]`. They spawn but never use hardpoints. No script reads `isBot` for killstreaks (in `GL` it is only checked for class and leaderboard handling).
- The commented-out `GL testHPs()` gives `radar_mp` every 20 s and is test code only.
- All the bot rules in sections 1–3 are therefore [I].

### 5. Unknowns

- [U] The engine-side radar reveal: the exact sweep visuals and how pings are drawn per enemy; whether `hasRadar` is the FFA engine hook; whether gpsjammer players are hidden from pings. These need RE of `t4mp.exe` around the `compassRadar*` users.
- [U] The effective gap between dog spawns, since `randomfloat` is called with two arguments.
- [U] Whether the dog knockdown sequence kills outright, separate from the 90-damage bites.
- [U] The artillery explosion FX: no effect key in `artillery_mp` and the `level.artilleryfx` load is unused, so the visible blast may come from impactType `mortar_shell` surface FX.
- [U] Whether `pers["hardPointItem"]` persists across rounds in round-based modes.
- [U] The exact damage falloff curve inside the 512 radius. It is engine radius-damage, and linear is assumed.

## Black Ops (t5)

Source: zone dump `t5/common_mp` with `t5/patch_mp` overriding. Of the files used here, only `_dogs.gsc` (one null-guard on `script_owner` in `dog_owner_kills`), `_globallogic_player.gsc` and `_utility.gsc` are overridden by patch_mp. None of those changes alter killstreak numbers. Paths below are relative to `maps/mp/` unless they start with `clientscripts/`, `weapons/` or `vehicles/`.

Tags: [V] read directly in data or script, [I] inferred, [U] unknown or not in the dump.

**Kill counts and HUD icons** come from `mp/statstable.csv`, which ships in `code_post_gfx_mp.ff`, not in common_mp or patch_mp (column 5 kills, column 6 HUD icon, column 11 `all` = available to everyone) [V].

---

### 0. Shared framework (applies to every streak)

#### 0.1 Earning
- **Kill threshold is per-streak, from a table.** It comes from `mp/statsTable.csv`: the row whose reference column (index 4, `level.cac_creference`) equals the menu name (e.g. `killstreak_spyplane`), read from the count column (index 5, `level.cac_ccount`). This happens in `gametypes/_hardpoints.gsc registerKillstreak()`, and the index constants are in `gametypes/_class.gsc`. [V]
- **Custom override.** When dvar `custom_killstreak_mode` is 2, the thresholds for slots 0/1/2 come from `custom_killstreak_1_kills` / `_2_kills` / `_3_kills` instead (`_hardpoints.gsc getKillstreakLevel()`). [V]
- **Hardline.** Perk `specialty_killstreak` subtracts dvar `perk_killstreakReduction` from the threshold, clamped to at least 1 (`_hardpoints.gsc giveKillstreakIfStreakCountMatches()`). The dvar's value is engine/config-side and not in the dump. [V] for the logic, [U] for the value (retail is generally 1). [I]
- **Exact-match award.** A streak is awarded only when the life's kill counter equals the threshold exactly. There is no rollover: the cycling code `check_running_killstreak` is commented out. Only the player's 3 chosen slots are checked (`giveKillstreakForStreak()`). [V]
- **Round-based modes.** `pers["killstreaksEarnedThisKillstreak"]` stops the same slot being re-awarded during the same unbroken streak. [V]
- **Which kills count** (`_globallogic_player.gsc` kill handling, patch_mp version): [V]
  - The attacker must be alive at the moment of the kill.
  - If the inflictor carries `requiredDeathCount`, the attacker must not have died since launching it.
  - The weapon must not be a killstreak weapon. `_hardpoints.gsc shouldGiveKillstreak()` returns false for any weapon in `level.killstreakWeapons`, which holds each streak's own weapon plus its registered alt weapons, unless dvar `scr_allow_killstreak_building` is 1 (default 0).
  - So kills with `radar_mp`, `rcbomb_mp`, `mortar_mp`, `napalm_mp`, `dogs_mp`, `dog_bite_mp`, `supplydrop_mp`, `helicopter_comlink_mp`, `cobra_20mm_comlink_mp`, `minigun_mp`, `m202_flash_mp`, `m220_tow_mp` and so on do **not** advance the streak.
- **Reset.** On death the counters `cur_kill_streak`, `totalKillstreakCount` and `killstreaksEarnedThisKillstreak` reset to 0. Being team-killed resets them without counting a death (`_globallogic_player.gsc` death handling). Changing team clears the counters and the stored streak inventory (`_hardpoints.gsc onJoinedTeam()`). [V]
- **Earned streaks survive death.** They live in `pers["killstreaks"]`, a LIFO stack, and are re-given on spawn (`giveOwnedKillstreak()`). [V]

#### 0.2 Inventory and activation
- **The stack.** `pers["killstreaks"]` is a LIFO stack with parallel arrays `killstreak_has_been_used` and `killstreak_unique_id`. Only the top entry's weapon is given, and it is bound to action slot 4 (`giveKillstreakWeapon()`, `activateNextKillstreak()`). [V]
- **Activation is a weapon switch.** `killstreakWaiter()` waits for `weapon_change` to the top streak's weapon and then runs `useKillstreak()`, which calls `triggerKillstreak()`, which calls the registered use function. When that returns true, the code notifies `killstreak_done` (true) and `removeKillstreakWhenDone()` pops that entry and gives the next one. On false the entry stays. [V]
- **Round-start delay.** Streaks registered with `delayStreak = true` cannot be used for `level.killstreakRoundDelay` seconds after round start. The delay comes from `scr_<gametype>_killstreakDelayTime` (`gametypes/_weapons.gsc`); the game prints "unavailable for N seconds". [V]
  - Delayed: mortar, napalm, dogs, attack helicopter, M220 TOW.
  - Not delayed: spy plane, counter-spy plane, care package, RC-XD.
- **XP for use** (`getXPAmountForKillstreak()`), by the streak's kill level: 1–4 kills give 100, 5 gives 150, 6–7 give 200, 8 gives 250, 9 gives 300, 10–11 give 350, 12–15 give 500. RC-XD pays its XP when control starts rather than in `triggerKillstreak`. [V]
- **"Inbound near you" warning.** Uses a radius of 1.25 × the streak's danger radius, 2D (`pointIsInDangerArea()`). [V]

#### 0.3 Team limits (`_killstreakrules.gsc init()`) [V]

**Rules** (global max / per-team max):

| Rule | Global max | Per-team max |
|---|---|---|
| vehicle | 7 | 7 |
| firesupport | 1 | 1 |
| airsupport | 1 | 1 |
| playercontrolledchopper | 1 | 1 |
| chopperInTheAir | 1 | 1 |
| chopper | 2 | 1 |
| dog | 1 | 1 |
| turret | 7 | 7 |
| weapon | 3 | 3 |
| satellite | 2 | 1 |
| supplydrop | 3 | 3 |
| rcxd | 3 | 2 |
| targetableent | 32 | 32 |

**How the rules apply:**
- In non-team modes `createRule()` clamps the global max down to the per-team max, and the per-team check is skipped. So in FFA "chopper" allows 1 globally and "rcxd" allows 2. [V]
- Each streak lists its rules with *counts* and *checks* flags. `isKillstreakAllowed()` fails if any checked rule is at its cap, or if the player is in last stand. On failure it prints the streak's "not available" string. [V]

**Rules per streak covered here:**

| Streak (hardpointType) | Rules (counts / checks) |
|---|---|
| radar_mp (spy plane) | targetableent (c/c) only, so effectively unlimited |
| counteruav_mp | targetableent (c/c) only |
| supply_drop_mp | vehicle, supplydrop, targetableent (all c/c) |
| rcbomb_mp | rcxd (c/c) |
| mortar_mp | firesupport (c/c) |
| napalm_mp | vehicle, airsupport (c/c) |
| dogs_mp | dog (c/c) |
| helicopter_comlink_mp | vehicle (c/c), chopper (c/c), playercontrolledchopper (check only), chopperInTheAir (count only), targetableent (c/c) |

#### 0.4 Kill thresholds

Kills from `mp/statstable.csv` column 5, in `code_post_gfx_mp.ff` [V]. Rows tagged `all` in column 11 (spy plane, care package, attack helicopter) are the defaults anyone can pick.

| Menu name | hardpointType | Weapon | Kills [V] | HUD icon [V] |
|---|---|---|---|---|
| killstreak_spyplane | radar_mp | radar_mp | 3 | `hud_icon_u2_spyplane` |
| killstreak_rcbomb | rcbomb_mp | rcbomb_mp | 3 | `hud_icon_rcbomb` |
| killstreak_counteruav | counteruav_mp | counteruav_mp | 4 | `hud_icon_counter_uav` |
| killstreak_supply_drop | supply_drop_mp | supplydrop_mp | 5 | `hud_supply_drop` |
| killstreak_napalm | napalm_mp | napalm_mp | 5 | `hud_icon_air_napalm` |
| killstreak_mortar | mortar_mp | mortar_mp | 6 | `hud_mortarshell` |
| killstreak_helicopter_comlink | helicopter_comlink_mp | helicopter_comlink_mp | 7 | `hud_ai_helicopter` |
| killstreak_dogs | dogs_mp | dogs_mp | 11 | `compass_objpoint_dogs` |

Registration sites: `_radar.gsc init()`, `gametypes/_supplydrop.gsc init()`, `_rcbomb.gsc init()`, `_mortar.gsc init()`, `_napalm.gsc init()`, `_dogs.gsc initKillstreak()` and `_helicopter.gsc init()`. All are gated by tweakables `scr_hardpoint_allow<name>`, which default to 1 (`gametypes/_tweakables.gsc`). [V]

**Not a killstreak in this build.** `_artillery.gsc` registration is commented out [V]. The `artilleryCanon*` tweakables (3 cannons, 5 shells) exist but are unused by mortar. [V]

#### 0.5 Stock bot framework (`gametypes/_bot.gsc`) [V]
- **Loadout picks** (`bot_setKillstreaks()`): 3 random streaks with distinct kill levels.
  - Any bot can draw spy plane, care package or attack helicopter.
  - At rank ≥ 9, or offline, the pool adds turret drops, napalm, counter-spy, mortar, blackbird, airstrike, dogs and RC-XD.
- **Use loop** (`bot_killstreak_think()`): every 3–5 s, take the top streak. If `isKillstreakAllowed` fails, wait 5 s. Otherwise use it according to type (described per streak below). A fail-safe switches back to `lastNonKillstreakWeapon` if the bot is still holding the streak weapon.
- **Hardline for bots.** Bots holding perk `specialty_noname` get `specialty_killstreak` set (`bot_revive_think()`).

---

### 1. Spy Plane (`radar_mp`), most thorough

#### 1.1 Earning
See 0.1. The threshold is 3 kills (statstable col 5) [V]. Activation is instant on switching to `radar_mp` (`_radar.gsc useKillstreakRadar()` → `_spyplane.gsc callspyplane()`). It is not round-delayed. [V]

#### 1.2 Mechanics
**Duration and timeline** (`_radar.gsc init()` / `useRadarItem()`, `_spyplane.gsc spyplane_timeout()`): [V]
- Time in air is `level.spyplaneViewTime` = **20 s**.
- Then `plane_leave()` unlinks the plane and moves it 20000 units forward over `level.spyplaneExitTime` = **20 s**.
- **The team's radar stays on during the exit.** `removeActiveUAV()` (which turns the radar off and calls `killstreakStop`) runs only after that further 20 s. So an undisturbed spy plane gives about **40 s** of radar. [V]
- The plane can still be shot down while leaving, because the damage monitor does not end on "leaving". [V]
- Unused values: `level.spyplaneEntranceTime` = 5 is set but unused [V]. `level.radarViewTime` = 30 belongs to the counter-spy plane, and `level.radarLongViewTime` = 45 to the Blackbird (`radardirection_mp`). [V]

**Flight path** (`generatePlane()`, `rotateUAVRig()`): [V]
- An invisible rig sits at the centre of the box spanned by the two `minimap_corner` ents, or at (0,0,0) if they are missing. Its start yaw is 115°.
- It rotates 360° every **60 s**: the spy-plane rig turns clockwise, the counter-spy rig anticlockwise.
- Each plane links to the rig at a random angle. The horizontal offset is 5000–7000 and the height offset 3000–5000; that offset vector is then normalised and rescaled to a length of 6000–7000.
- Attach yaw is −90 for the spy plane and +90 for the counter-spy plane.

**Minimap reveal, server side** (`_spyplane.gsc UAVTracker()`, `updateTeamUAVStatus()`, `updatePlayersUAVStatus()`; `_radar.gsc setTeamSpyplaneWrapper()`): [V]
- The status is recomputed on every `uav_update` notify.
- **Team modes:**
  - An active Blackbird (satellite count > 0) takes precedence: spyplane 0, satellite 1.
  - Otherwise the code calls the engine builtin `setTeamSpyplane(team, mode)` with mode **0** for no UAV, **1** for exactly one active, and **2** for more than one active ("fast sweep").
  - It also sets match flags `radar_allies` / `radar_axis` and notifies `radar_status_change`.
- **FFA:**
  - The count is per player (`level.activeUAVs[entnum]`).
  - The player gets `hasSpyplane` 1 or 2 and the client UI flag `radar_client` = 1.
  - The radar also counts as on if `pers["hasRadar"]` is set by game modes (`hlnd`, `_wager`, `_gv_actions`).
  - Each FFA spawn re-triggers `uav_update` (`watchFFASpawn()`).
- **Who sees whom:** the calling team (FFA: the calling player) sees enemies on the minimap. [V]
- **Not in script, engine side** [U]:
  - whether the reveal is a rotating sweep or a periodic ping;
  - the refresh period for mode 1 and mode 2;
  - how the icons fade.

  The labels "normal = 1, fastSweep = 2" in `useRadarItem()` imply sweep pings at two speeds. [I]
- **Ghost.** Perk `specialty_gpsjammer` (Ghost) is referenced only by challenge stats ("kill while enemy has radar", `_properks.gsc`). Exempting Ghost players from the reveal is an engine job. [I]

**Health and destruction** (`generatePlane()`, `plane_damage_monitor()`, `plane_health()`): [V]

| Property | Value |
|---|---|
| Max health | `level.u2_maxhealth` = 700. Damage accumulates in `damageTaken`; the entity's real health is held at 99999 and refunded, and the plane is destroyed when `damageTaken` exceeds 700. |
| Bullets (rifle/pistol) | Full damage. With `specialty_armorpiercing` the damage becomes damage × `level.cac_armorpiercing_data`; this is an assignment, not an addition. |
| `MOD_PROJECTILE` | Instant kill (701). |
| Any other damage type | Full damage. |
| Who can damage it | Only enemy players: owner and teammates are ignored, and the friendly-fire check applies. |
| Lock-on missiles | When a fully locked missile targets the plane, `missileProximityDetonate()` detonates it once it starts moving away, if within 1536 units, with `radiusDamage` of radius 1536 and 600/600 damage (`handleIncomingMissile()`). |
| Damage trail | Plays at ≥ 350 damage (`health_low` = 50 %), repeating every 10 s. |
| On destruction | `u2_crash()`: explosion fx, then model swapped and deleted after 0.3 s. Then `removeActiveUAV`, popup `KILLSTREAK_DESTROYED_UAV` to all, and XP `spyplanekill` (100 team / 25 FFA, `gametypes/_rank.gsc`). |
| Visibility | Visible **only to the enemy team** (`SetVisibleToTeam(otherteam)`). In FFA it is visible to everyone except the owner (`updateVisibility()`). It is a lock-on target (`Target_Set`). |

**Limits:** "targetableent" (32) only, so there is effectively no per-team cap and stacking two gives fast-sweep mode 2. [V]

**Dialogue throttle** (`_hardpoints.gsc playKillstreakStartDialog()`): in team modes the team-wide "spy plane up" / "enemy spy plane" leader lines play at most once per 30 s per team. Within that window only the caller hears it. [V]

#### 1.3 Assets
- **Weapon:** `radar_mp`. Its viewmodel is `viewmodel_c4` (detonator anims), and it uses HUD, dpad and kill icon `hud_icon_u2_spyplane`. [V] (`weapons/radar_mp`)
- **Model:** `t5_veh_jet_u2`. [V]
- **FX:** [V]
  - `vehicle/exhaust/fx_exhaust_u2_spyplane_afterburner` (on leave)
  - `trail/fx_trail_u2_plane_damage_mp`
  - `vehicle/vexplosion/fx_vexplode_u2_exp_mp`
- **Strings:** `KILLSTREAK_EARNED_RADAR`, `KILLSTREAK_RADAR_NOT_AVAILABLE`, `KILLSTREAK_RADAR_INBOUND`, `KILLSTREAK_DESTROYED_UAV`. [V]
- **Sound and dialogue:** inform `mpl_killstreak_radar`; dialogue keys `kls_u2_used`, `kls_u2_enemy`, `kls_u2_ready`. [V]
- **Dev dvar:** `scr_giveradar`. [V]

#### 1.4 Bots
- **Stock** (`_bot.gsc bot_killstreak_think()`): the bot simply switches to the weapon as soon as it is on top of its stack (3–5 s polling), with no tactical condition. [V]
- **Reading radar:** stock bots do not consume radar information, except in wager modes, where a bot with `hasSpyplane` paths to a random live enemy (`bot_wager_think()`). [V]
- **Suggested rule** [I]:
  - Use immediately when earned unless the team already has one active. A second plane gives only the faster refresh.
  - While the team radar is on, add each enemy's position to the bot's known-enemy memory at every sweep tick, and bias roaming goals towards the nearest revealed enemy.
  - Bots carrying a launcher should shoot visible enemy spy planes. `MOD_PROJECTILE` one-shots them.

---

### 2. Counter-Spy Plane (`counteruav_mp`), most thorough

#### 2.1 Earning
See 0.1. The threshold is 4 kills (statstable col 5) [V]. Use is instant (`_radar.gsc useKillstreakCounterUAV()` → `_spyplane.gsc callcounteruav()`). It is not round-delayed. [V]

#### 2.2 Mechanics
**Duration** (`counteruav_timeout()`): [V]
- Time in air is `level.radarViewTime` = **30 s**.
- At 30 s the client flag `const_flag_counteruav` (11) is cleared, which ends the jamming.
- The plane then exits over 20 s (`counteruavplaneExitTime`). Only after that does `removeActiveCounterUAV()` run, which handles bookkeeping, challenges and the rule release.
- `level.counteruavLength` = 25 is set but unused. [V]

**Effect, client side** (`clientscripts/mp/_scrambler.csc`):
- The flagged script_mover registers as a *global* (non-localised) scrambler (`spawnedGlobalScramber()`).
- Every 0.25 s, `scramblerUpdate()` calls the engine builtin `SetEnemyGlobalScrambler(1)` on each local client for whom it is an enemy scrambler, i.e. when `friendNotFoe` is false; otherwise it passes 0. [V]
- **Result:** the whole enemy team's minimap is jammed. In FFA that is every player except the owner. [V]
- The caller's own team gets no benefit and no friendly scrambler entry. [V]
- What the jam does to the compass (static overlay, hidden enemy and friendly blips, whether it suppresses the enemy's spy-plane pings) is engine-side. [U]
- **Spy planes are not affected server side.** `UAVTracker()` ignores counter-UAVs, so the enemy's spy plane stays "active". Any suppression of its effect happens in the client compass. [V]/[I]
- **Sound:** enemies hear a looping `mpl_scrambler_static` on a sound ent spawned at the plane's spawn origin; it does not follow the plane. On deletion `mpl_scrambler_burst` plays. [V]
- `snd_futz` voice distortion is distance-driven and effectively 0 for the global scrambler. [I]

**Flight, health and destruction:** identical to the spy plane (same `generatePlane()`, 700 health, projectile one-shot, enemy-only visibility). On the anticlockwise rig the plane's yaw offset is +90. On destruction the code clears the flag, shows popup `KILLSTREAK_DESTROYED_COUNTERUAV` and gives XP `spyplanekill`. [V]

**Limits:** targetableent only. [V]

#### 2.3 Assets
- **Weapon:** `counteruav_mp` (C4 detonator viewmodel; icon `hud_icon_counter_uav`). [V]
- **Model:** `t5_veh_jet_u2`, shared with the spy plane. [V]
- **Sounds:** `mpl_scrambler_static`, `mpl_scrambler_alert`, `mpl_scrambler_ping`, `mpl_scrambler_burst`; inform `mpl_killstreak_radar`; dialogue `kls_cu2_used`, `kls_cu2_enemy`, `kls_cu2_ready`. [V]
- **Strings:** `KILLSTREAK_EARNED_COUNTERUAV`, `KILLSTREAK_COUNTERUAV_NOT_AVAILABLE`, `KILLSTREAK_COUNTERUAV_INBOUND`. [V]
- **Dev dvar:** `scr_givecounteruav`. [V]

#### 2.4 Bots
- **Stock:** activates immediately, same branch as the spy plane. [V]
- **Suggested rule** [I]:
  - Activate when the enemy team has an active spy plane (`level.activeUAVs[enemy] > 0`), or else at once.
  - While jammed, bots should drop radar-derived enemy memory and fall back to sight and sound.

---

### 3. Care Package (`supply_drop_mp`, weapon `supplydrop_mp`), most thorough

#### 3.1 Earning
See 0.1. The threshold is 5 kills (statstable col 5) [V]. It is not round-delayed. Assists are allowed (`allowKillstreakAssists`). [V]

#### 3.2 Mechanics
**Marker** (`gametypes/_supplydrop.gsc useKillstreakSupplyDrop()`, `supplyDropWatcher()`, `useSupplyDropMarker()`): [V]
- `supplydrop_mp` is a thrown grenade (weapon def: fuse 1 s, `projectileSpeed` 960, relative up 120, `projExplosionType` smoke).
- The rule is taken when the marker comes out (`killstreakStart`). It is released if the player switches weapon before throwing.
- Use and pick-up are disabled while it is cooked (`_disableUsability`). Dying while holding a pulled-back marker consumes the streak (`supplyDropGrenadePullWatcher()`).
- If the thrown marker never comes to rest within 10 s, it is deleted and the rule released (`supplyDropGrenadeTimeout()`).
- Once it stops moving, the heli is called to the marker origin (`doSupplyDrop()`). If it explodes first, the explosion position is used instead.
- After the fuse, `do_supply_drop_detonation()` plays smoke fx `env/smoke/fx_smoke_supply_drop_blue_mp` on `tag_fx` and a 6 s smoke sound, then deletes the canister 3 s later.

**Delivery helicopter** (`heliDeliverCrate()`, `spawn_helicopter()`, `speedRegulator()`, `supplyDropHeliStartPath()` / `EndPath()`): [V]

| Step | Values |
|---|---|
| Vehicle | `heli_supplydrop_mp`. Models `vehicle_ch46e_mp_light` (friendly) and `vehicle_ch46e_mp_dark` (enemy). |
| Height | `_airsupport.gsc getMinimumFlyHeight()`: the z of the map's `air_support_height` struct, else 850 × `scr_airsupportHeightScale`, plus any `level.forceAirsupportMapHeight`. |
| Start | 10000 units back (`scr_supplydropIncomingDistance`) along a random yaw, ±2° and ±100 units of jitter. Up to 12 tries, rotating 30° each time, to find a path that avoids `no_fly_zone` cylinders. |
| Goal offset | 400 forward (`scr_supplydropOffset`, the rear hatch). |
| Speed in | `SetSpeed` 125, accel 100, max roll 45. After 3 s it slows to 75 / accel 40, yaw speed 100, and 1 s later max pitch 25 / roll 35. All are dvars (`scr_supplydrop*`). SetSpeed units are engine-side (likely mph). [I] |
| Drop | At goal + 0.2 s, the crate spawns at the heli origin − 200 z (`scr_supplydropOffsetHeight`) minus the rotated 400 offset (`heliDropCrate()`). |
| Exit | Speed 150 / accel 40, a 60–120° turn to either side, 15000 units out (`scr_supplydropOutgoingDistance`) with ±150 jitter. Then deleted. |
| Rule release | When the **chopper** is deleted or destroyed (`refCountDecChopper()`), not when the crate is taken. |
| Health | `maxhealth` 1500, using the `_helicopter.gsc heli_damage_monitor()` model: bullets × 0.3 (`scr_heli_armor_bulletdamage`); rockets one-shot (`rocketDamageOneShot` = 1501); no chaff. |
| Shot down (`heliDestroyed()`) | Slows to 25, spins at 180–220°/s, and **still drops the crate** after 0.5–1.5 s, from wherever it is. Then it explodes. Destroying it gives XP `helicopterkill`. |
| SAM turrets | Cannot acquire it until it is within 1500 of the drop point or inside the spawn bounds (`SAMTurretWatcher()`). |

**Crate** (`dropCrate()`, `crateSpawn()`, `cratePhysics()`): [V]
- **Entity:** a physics `script_model` with `script_noteworthy` "care_package". Models: friendly `mp_supplydrop_ally`, enemy `mp_supplydrop_axis`, booby-trapped `mp_supplydrop_boobytrapped`.
- **Physics launch:** random force point within ±200, vertical velocity −100..100.
- **Timeouts:** deleted if not stationary within 20 s (`timeoutCrateWaiter()`). After landing it times out after **90 s** (`crateTimeOut`).
- **Crush** (`crateKill()`): while its vertical speed exceeds 15 per tick, any live player touching it (bounds +10) takes health + 1 damage (`MOD_HIT_BY_OBJECT`, weapon `supplydrop_mp`, sounds `mpl_supply_crush` and `phy_impact_supply`). It counts as stationary after 20 ticks below 2.
- **Equipment:** the crate also detonates or deletes enemy equipment it lands on (+10 bounds) and fizzles tactical insertions (+15).
- **Restacking:** when a crate is deleted, other crates and items within 70 drop to the ground. Its 9-point down-trace re-kill logic is `crateDropToGroundKill()`.

**Capturing** (`crateUseThink()`, `crateUseThinkOwner()`, `useHoldThink()`): [V]
- **Hold times:** owner `level.crateOwnerUseTime` = **0.5 s**; anyone else `level.crateNonOwnerUseTime` = **3.0 s**.
- **Hacker:** with `specialty_fastinteract` an enemy captures in 0.5 s, but teammates of the owner still take 3 s.
- **Conditions:** the player must be alive, on the ground, holding Use, not throwing a grenade, not meleeing and not in a vehicle. The player is frozen with weapons disabled while capturing, and a progress bar (`KILLSTREAK_CAPTURING_CRATE`) is shown.
- **Steal sounds:** an enemy steal plays `mpl_crate_enemy_steals` to the owner; a team steal plays `mpl_crate_friendly_steals`.
- **Ownership:** an owner who changes team loses ownership.

**Contents, rolled at spawn** (`getRandomCrateType("supplydrop_mp")`): cumulative weights summing to 100, so each weight is a percentage [V].

| Contents | Weight |
|---|---|
| Ammo | 20 |
| Spy plane (radar_mp) | 15 |
| Counter-spy (counteruav_mp) | 15 |
| RC-XD | 9 |
| M220 TOW | 5 |
| Mortar | 5 |
| Sentry (autoturret_mp) | 5 |
| SAM (auto_tow_mp) | 5 |
| Airstrike (Rolling Thunder) | 3 |
| Grim Reaper (m202_flash_mp) | 3 |
| Napalm | 3 |
| Blackbird (radardirection_mp) | 3 |
| Attack helicopter | 3 |
| Death Machine (minigun_mp) | 2 |
| Chopper Gunner | 2 |
| Dogs | 1 |
| Gunship (helicopter_player_firstperson_mp) | 1 |

**Contents rules:**
- **One of each heavy weapon.** If a Death Machine, Grim Reaper or TOW is already held, on the ground or in another crate, the roll shifts to the neighbouring table entry (`validate_crate_type()`). [V]
- **Gambler** (`specialty_gambler`, Hardline Pro): double-tap Use on a crate re-rolls it once from the "gambler_mp" table, never giving the same item (`crateGamblerThink()`). That table weights ammo 9, spy plane 9, counter-spy 9, RC-XD 9, TOW 9, mortar 9, sentry 9, SAM 9, airstrike 4, Grim Reaper 4, napalm 4, Blackbird 4, attack heli 4, Death Machine 3, Chopper Gunner 3, dogs 1, gunship 1. [V]
- **Killstreak contents** are pushed onto the capturer's streak stack (`giveCrateKillstreak()` → `giveKillstreak`). [V]
- **Ammo** refills every weapon to max, except the four killstreak weapons. Grenades go to start ammo, or max ammo with `specialty_twogrenades` (`giveCrateAmmo()`). [V]

**Hacker booby-trap** (`specialty_disarmexplosive`): [V]
- When a hacker captures an enemy crate, they still receive its contents. A booby-trapped copy is spawned in its place: friendly-looking to the owner's team and usable only by them (team modes).
- When that copy is captured it beeps (`wpn_semtex_alert`, starting at a 0.15 s interval and shrinking ÷1.2 each beep until below 0.08). It then explodes with `RadiusDamage` 256, 300 → 75, `MOD_EXPLOSIVE`, credited to the hacker (`watch_explosive_crate()`).

**Minimap and HUD** (`crateActivate()`): [V]
- Objective icon `compass_supply_drop_green` for the owner's team and `compass_supply_drop_red` for enemies. A hacked crate shows `compass_supply_drop_black`.
- Head icon is `<killstreak icon>_drop`, or `hud_ammo_refill_drop` for ammo.
- In FFA the green icon is shown to the owner only.

**Limits:** vehicle (7/7), supplydrop (3 global / 3 per team), targetableent. [V]

**Bug spotted:** `refCountDecChopperOnDisconnect()` waits on the misspelt notify "disconnecct", so it never fires. Rule release relies on the chopper's death path instead. [V]

#### 3.3 Assets
- **Weapon:** `supplydrop_mp`. View model `t5_weapon_supply_drop`, world/projectile model `t5_weapon_supply_drop_world`, HUD/dpad `hud_supply_drop`, kill icon `hud_obit_crate`, throw sound `wpn_grenade_throw`. [V] (`weapons/supplydrop_mp`)
- **Vehicle:** `heli_supplydrop_mp` (compass icon `hud_anim_chinook`, `addToCompassEnemy` 1). [V] (`vehicles/heli_supplydrop_mp`)
- **Models:** `vehicle_ch46e_mp_light`, `vehicle_ch46e_mp_dark`, `mp_supplydrop_ally`, `mp_supplydrop_axis`, `mp_supplydrop_boobytrapped`. [V]
- **FX:** `env/smoke/fx_smoke_supply_drop_blue_mp`, `explosions/fx_grenadeexp_default`, `vehicle/props/fx_seaknight_main_blade_full`, `vehicle/props/fx_seaknight_rear_blade_full`. On shoot-down it also uses the helicopter fx from `_helicopter.gsc`. [V]
- **Shaders:** `compass_supply_drop_black`, `compass_supply_drop_green`, `compass_supply_drop_red`, `waypoint_recon_artillery_strike`, `hud_ks_minigun(_drop)`, `hud_ks_m202(_drop)`, `hud_ammo_refill(_drop)`, `headicon_dead`. [V]
- **Sounds:** `phy_impact_supply`, `mpl_supply_crush`, `mpl_crate_enemy_steals`, `mpl_crate_friendly_steals`, `uin_gamble_perk`, `evt_hacker_hacking`, `wpn_semtex_alert`, `wpn_grenade_explode`; inform `mpl_killstreak_supply`; dialogue `kls_supply_used`, `kls_supply_enemy`, `kls_supply_ready`. [V]
- **Strings:** `KILLSTREAK_EARNED_SUPPLY_DROP`, `KILLSTREAK_AIRSPACE_FULL` (the not-available text), `KILLSTREAK_CAPTURING_CRATE`, `KILLSTREAK_HACKING_CRATE`, plus per-contents hint strings (`KILLSTREAK_*_CRATE`, `PLATFORM_*_GAMBLER`). [V]
- **Dev dvar:** `scr_givesupplydrop`. [V]

#### 3.4 Bots
- **Throwing** (`_bot.gsc bot_use_supply_drop()`), checked every 1 s: [V]
  - The bot must be idle: alive, not in last stand, no script goal, no threat.
  - Path lookahead must be ≥ 96 units, view pitch ≥ 7° (looking down), and lookahead yaw within 2° of facing.
  - The point 384 units ahead must have clear sky (sight traces to 2048 above, from that point and from the bot) and solid ground within 32 below.
  - It then steps 64 forward, switches to the marker and presses Attack (`bot_use_item()`), switches back, and waits up to 10–15 s for its crate (`bot_crate_landed`).
- **Collecting** (`bot_crate_think()`), every 3–5 s while idle: [V]
  - Pick a random crate that is not still dropping, with at most 1 bot already assigned.
  - A teammate's crate is skipped 70 % of the time.
  - A crate further than 2048 is ignored unless it is the bot's own.
  - Path to it with goal radius 100, then hold Use for crate time + 0.5 s (own crate) or + 1.0 s (other).
- **Anti-stuck** (`bot_crate_touch_think()`): every 3 s, with no threat, press Use on any crate within `player_useRadius`. [V]
- **Suggested addition** [I]: abort a capture when an enemy becomes visible, since capturing freezes the player.

---

### 4. RC-XD (`rcbomb_mp`)

#### 4.1 Earning
See 0.1. The threshold is 3 kills (statstable col 5) [V]. It is not round-delayed, and assists are allowed. [V]

#### 4.2 Mechanics
**Deploy** (`_rcbomb.gsc useKillstreakRCBomb()`, `calculateSpawnOrigin()`, `testSpawnOrigin()`): [V]
- **Placement rules:**
  - The player must be on the ground.
  - The car is placed 70 units ahead, trying yaw offsets 0, +20, −20, +45 and −45.
  - Trace start height above the player is 50 standing, 30 crouched, 15 prone.
  - A position needs at least 3 of 4 wheel traces to touch ground, or at least 2 as a fallback (wheels at ±13 forward, ±10 side).
  - It must not telefrag anyone (a 24×24×15 box), and a swept trace from the player must be clear.
  - If no valid position is found the game prints `KILLSTREAK_RCBOMB_NOT_PLACABLE`.
- **Screen fades:**
  - Fade in: delay 0.25, in 0.5, black 0.5, out 0.5 (`scr_rcbomb_fadeIn_*`).
  - Fade out on detonation: delay 0.5, in 0.5, black 0.25, out 0.5 (`scr_rcbomb_fadeOut_*`).
- **Taking control:** the player is frozen for 0.9 s, then put into seat 0 (`usevehicle`) in `givePlayerControlOfRCBomb()`. XP for the streak is given at this point.

**Vehicle `rc_car_medium_mp`** (`vehicles/rc_car_medium_mp`): [V]
- Type "4 wheel" with nitrous physics; remote-controlled; third-person camera (range 45, height 15).
- `healthDefault` 800 (min 100, max 1001).
- `maxSpeed` 19 and `accel` 30, in vehicle-def units, probably mph. [I]
- Boost burst: ×2 speed, ×3 accel, `boostDuration` 2, `boostInterval` 60. [V] for the values, [U] for the exact runtime meaning.
- `addToCompass` 1 and `addToCompassEnemy` 1 with `compassIcon` `hud_objective_rcbomb`, so **enemies see it on their minimap**. [V]
- Takes bullet, grenade, projectile and splash damage. `turretWeapon` is `rc_car_weapon_mp`.

**Timer** (`carTimer()`), with host-migration pauses: [V]
- At 20 s: countdown client flag (blinking lights).
- 6 s later: timeout flag.
- 4 s later: forced detonation.
- So **30 s** in total. Dvar `scr_rcbomb_notimeout` disables it.

**Detonation** (`carDetonateWaiter()` → weapon-object watcher "rcbomb" detonate = `blowup()`): [V]
- **Triggers:** the driver presses Attack. Also forced by trigger_hurt (`trigger_monitor()`), minefields, the KOTH radio sphere (75), game end, and the timer.
- **Damage:** `radiusDamage` at origin + 10 z, radius **256**, max **350**, min **25**, `MOD_EXPLOSIVE`, weapon `rcbomb_mp`. Plus a physics explosion sphere and the RC earthquake.
- The weapon def's own explosion values (256 / 200 / 50) are not used by this script path. [V]
- **Destroyed by an enemy:** the enemy gets XP `rcbombdestroy` (50 team / 30 FFA). [V]

**Other rules:** [V]
- **Friendly fire:** with FF off only the owner, or inflictors linked to the car, can damage it (`RCCarAllowFriendlyFireDamage()`). In FFA the owner can damage it (`gametypes/_globallogic_vehicle.gsc`).
- **Enemy scramblers:** an enemy scrambler within the inner radius sets the stunned client flag (`watchForScramblers()`, re-checked every 0.25–0.5 s).
- **Ending control:** exiting the vehicle ends control. Changing team deletes the car.

**Limits:** rcxd, 3 global / 2 per team. In FFA the effective cap is 2. [V]

#### 4.3 Assets
- **Weapon:** `rcbomb_mp`. Controller view model `t5_veh_rccontroller_blockout`, world model `t5_veh_rccontroller_world`, anims `viewmodel_rc_carbomb_*`, HUD/ammo `hud_icon_rcbomb`, dpad `hud_icon_rcbomb_32x32`, kill icon `hud_obit_rcbomb`. [V]
- **Vehicle:** `rc_car_medium_mp`. Models `t5_veh_rcbomb_allies` (friendly, also the death model) and `t5_veh_rcbomb_axis` (enemy). [V]
- **FX:** [V]
  - `maps/mp_maps/fx_mp_exp_rc_bomb`
  - `weapon/grenade/fx_spark_disabled_rc_car`
  - `vehicle/light/fx_rcbomb_blinky_light`, `_solid_light`, `_light_green_os`, `_light_red_os`
  - `vehicle/treadfx/fx_treadfx_rcbomb_<dust|concrete|snow>[ _drift | _peel | _first_person | _reverse | _trail | _slow ]`
- **Sounds:** [V]
  - Engine and wheels: `mpl_veh_rc_idle_npc`, `mpl_veh_rc_idle_plr`, `mpl_veh_rc_eng_npc`, `mpl_veh_rc_eng_plr`, `mpl_veh_rc_load_npc`, `mpl_veh_rc_load_plr`, `mpl_veh_rc_road`, `mpl_veh_rc_slide`, `mpl_veh_rc_peel`.
  - Explosion: `mpl_sab_exp_suitcase_bomb_main`.
  - Client: `veh_collision`, `veh_engine_stutter`.
  - Rumbles: `rcbomb_engine_stutter`, `rcbomb_slide`.
  - Inform `mpl_killstreak_rcbomb`; dialogue `kls_rcbomb_used`, `kls_rcbomb_enemy`, `kls_rcbomb_ready`.
- **Strings:** `KILLSTREAK_EARNED_RCBOMB`, `KILLSTREAK_RCBOMB_NOT_AVAILABLE`, `KILLSTREAK_RCBOMB_INBOUND`, `KILLSTREAK_RCBOMB_NOT_PLACABLE`. [V]

#### 4.4 Bots
- **Deploy** (`_bot.gsc bot_killstreak_think()`, rcbomb case): the bot deploys only when it has no threat, path lookahead is ≥ 128, and lookahead yaw is within 5° of facing. It then switches to the weapon and starts `bot_rccar_think()`. [V]
- **Detonate:** every 0.5 s, if any enemy is within **200** units of the car (**512** on "easy"), the bot presses Attack. [V]
- **Stuck fail-safe** (`bot_rccar_kill()`): if the car moved less than 16 units in 1 s and still has not moved after 2 more s, it detonates. [V]
- **Steering:** no script steers the car. Stock bot driving must happen in engine bot code. [U]
- **Suggested driving** [I]: path the car along the navmesh towards the nearest known enemy (radar or last seen), boost on straight segments longer than about 300 units, and keep the 200-unit detonation rule.
- **Countering:** all bots except "easy" ones shoot enemy RC-XDs they can see, even without a launcher (`bot_vehicle_think()`). [V]

---

### 5. Mortar Team (`mortar_mp`)

#### 5.1 Earning
See 0.1. The threshold is 6 kills (statstable col 5) [V]. It **is** round-delayed (`delayStreak` true). [V]

#### 5.2 Mechanics
**Selection** (`_mortar.gsc selectMortarLocation()`): [V]
- Location selector `map_mortar_selector`, radius `level.mortarSelectorRadius` = 800.
- The player confirms **3 points** (`level.mortarSelectionCount`). Cancelling any of them aborts the streak.
- The streak can be cancelled by death, weapon change or game end (`_airsupport.gsc endSelectionThink()`).

**Strike** (`useMortar()`, `doMortar()`, `callMortarStrike()`, `startMortarCanon()`, `doMortarStrike()`, `callStrike_mortarBombEffect()`): [V]
- **Rule:** taken on confirm (firesupport 1/1) and released when all shells are gone, or after a 10 s safety timeout (`doMortar()`).
- **Ground point:** each point is traced down 1000 units. If the trace falls more than 999 below the start, the owner's z is used instead. The code first lowers each point to the ground under the owner minus 514, so this fallback probably fires often and the owner's height is used. [V]/[I]
- **Order:** points fire **2.5 s apart** (`scr_timeBetweenMortars`).
- **Shells per point:** `mortarCanonShellCount` = **2** (tweakable `scr_hardpoint_mortarCanonShellCount`), spaced 1.3 ± 0.2 s (`scr_timeBetweenShells`). Accuracy radius is **0**, so both shells land on the exact point.
- **Total:** 6 shells in about 6–7 s (`level.mortarShellsInAir` = `mortarCanonCount` 3 × 2).
- **Firing direction:** from `mortar_<team>` map ents if present, else from random origins outside the spawn bounds, choosing the one most behind map centre (`getBestFlakDirection()`).
- **Ballistics:**
  - Firing position 6000 units back (`scr_mortarDistance`), pitch 75° (`scr_mortarAngle`).
  - Muzzle speed is solved ballistically from `bg_gravity`.
  - The projectile is spawned already 30 % of the way along its arc (`scr_mortarStartRatio` 0.3) via `launchbomb("mortar_mp")`.
  - Assuming `bg_gravity` 800: speed is about 3098 u/s and the remaining flight about 5.2 s. [I]
- **Launch audio:** three `mpl_kls_mortar_launch` sounds 0.3 s apart at the firing position.
- **Incoming audio:** `prj_mortar_incoming_0<0..2>` before impact, plus tinnitus sound `mpl_kls_exlpo_tinitus` for players within 800.

**Damage, from the weapon def** (`weapons/mortar_mp`): [V]
- `explosionRadius` **512**, inner **600**, outer **75**, `damageConeAngle` 180, impact type `mortar_shell`, `projectileSpeed` 9999.
- Impact sound `mpl_kls_artillery_impact`, whistle `mpl_kls_mortar_whistle`.

**Shellshock** (`mortarImpactEffects()`, `radiusMortarShellshock()`): [V]
- Applied within 1.1 × the impact radius: shock `mortarblast_enemy` for int(3 → 1.5 s by distance), plus `_shellshock.gsc mortar_earthquake`.
- It applies to all players, team-mates included.

**Warning and spawns:** [V]
- In non-hardcore modes, teammates within 375 (300 × 1.25, 2D) of a point get `MP_WAR_MORTAR_INBOUND_NEAR_YOUR_POSITION`.
- Spawn influencers of radius 900 (300 × 3) avoid the points (`create_artillery_influencers`).
- The minimap shows the strike icon via `artilleryiconlocation()`; the icon asset name is [U].
- The "danger oval" constants (max 300, min 200, forward push 1.5, oval scale 6) are used only for danger and spawn evaluation, not for damage.

**Kills credited:** `mortar_mp` is a killstreak weapon, so its kills do not count towards streaks. [V]

#### 5.3 Assets
- **Weapon:** `mortar_mp` (radio view model `t5_weapon_radio_viewmodel`, world model `t5_weapon_radio_world`, projectile `mortar_shell`, HUD `hud_mortarshell`, kill icon `hud_obit_mortar`). [V]
- **Selector:** `map_mortar_selector`. **Shellshock:** `mortarblast_enemy`. [V]
- **Sounds:** `mpl_kls_mortar_launch`, `prj_mortar_incoming_00`, `prj_mortar_incoming_01`, `prj_mortar_incoming_02`, `mpl_kls_exlpo_tinitus`, `mpl_kls_artillery_impact`, `mpl_kls_mortar_whistle`, `air_raid_a`, `uin_alert_slideout`; inform `mpl_killstreak_mortar`; dialogue `kls_mortars_used`, `kls_mortars_enemy`, `kls_mortars_ready`. [V]
- **Strings:** `KILLSTREAK_EARNED_MORTAR`, `KILLSTREAK_MORTAR_NOT_AVAILABLE`, `KILLSTREAK_MORTAR_INBOUND`. [V]

#### 5.4 Bots
- **Stock** (`bot_killstreak_location(3, weapon)`): [V]
  - The bot switches to the weapon and freezes. If selection mode has not started within 1 s it gives up.
  - It waits 2 s, then sends 3 confirm points. Each is a random **enemy** player in "playing" state plus a random ±512 offset in X and Y, sent 0.25 s apart.
- **Suggested refinement** [I]: weight targets towards clusters, or towards radar-revealed and last-seen enemies, and avoid points within 512 of teammates.

---

### 6. Napalm Strike (`napalm_mp`)

#### 6.1 Earning
See 0.1. The threshold is 5 kills (statstable col 5) [V]. It is round-delayed. [V]

#### 6.2 Mechanics
**Selection** (`_napalm.gsc selectNapalmLocation()`): [V]
- Selector `map_napalm_selector`, size 3000 (`scr_napalmSelectorSize`).
- The player confirms a location and a **yaw** (the run direction); map north is added via `getnorthyaw()`.

**Run** (`doNapalm()`, `callNapalmStrike()`): [V]
- **Rule:** vehicle 7/7 and airsupport 1/1, released after the run.
- **Flight line:** 24000 units each side of the target along the yaw, at the minimum fly height raised to clear any crossed no-fly zones.
- **Target:** traced 4000 down and clamped to spawn z ± 200.
- **Plane:** F-4 `t5_veh_jet_f4_gearup` at **7000 u/s**, so the 48000 run takes about 6.9 s. It plays `plane_rumble` to everyone and sets client flag `const_flag_napalm` (3).
- **Exit:** one of two turn styles, radius 25000 (`planeExit()`).
- **Spawn influencers:** placed for `burnNapalmDuration` + 5.5 = 18.5 s.

**Bombs** (`releaseNapalm()`, `callStrike_bombEffect()`): [V]
- **3 bombs**, released 0.2 s apart.
- Each is launched as `napalm_mp` at half the plane speed. Release time comes from `_airsupport.gsc calculateReleaseTime()` (fall time from `bg_gravity`).
- The weapon def's `explosionRadius` is 1, so all damage is scripted.
- 0.5 s before computed impact, fx `weapon/napalm/fx_napalm_drop_mp` plays.

**Impact points per bomb:** [V]
- Each bomb makes **7** ground traces spaced **200** units along the bomb direction (`scr_napalm_seperation`), pitched 60° down (`scr_napalm_maxAngles`), one every 0.5 s.
- A point counts only if the surface normal z > 0.5. That gives up to 21 points per strike.
- Interior points whose height differs from the previous point by less than 12 get a large flame of radius **200** (`level.burnNapalmEffectRadiusLarge`). Others get a small flame of radius **100**.
- Large and small use weapons `napalmground_lg_mp` and `napalmground_sm_mp` via `SpawnNapalmGroundFlame`.

**Impact damage per point** (`napalmLosRadiusDamage()` with `_airsupport.gsc entLOSRadiusDamage()`): [V]
- Linear fall-off from **200** at the centre to **30** at radius **512** (`scr_napalmImpactDamageRadius`), `MOD_BURNED`, weapon `napalm_mp`.
- For players and actors with a roof overhead (a trace up 800 is blocked) and no line of sight to the impact, the distance counts ×4, which usually zeroes the damage.
- Players within 5 s of spawning are immune (`scr_napalm_spawnprotection`).
- Glass is damaged too (`doGlassDamage()`).

**Ground fire** (`watchNapalmBurn()`, `gametypes/_burnplayer.gsc doNapalmGroundDamage()`): [V]
- Each flame lasts **13 s** (`burnNapalmDuration`), polled every 0.25 s.
- A player within the flame radius (3D distance) and within −100..+80 z of it starts burning: **51 damage per second** (`level.napalmGroundDamage`) for up to **3 s** (`level.groundBurnTime`), `MOD_BURNED`.
- Burning stops early in water or if the flame entity is gone.
- **Immune:** Flak Jacket (`specialty_fireproof`), the owner's teammates in team modes, and spawn-protected players.
- Dogs use `doDogNapalmGroundDamage`.
- The ground-flame loop sound `mpl_kls_napalm_fire` stops after 13 s.

#### 6.3 Assets
- **Weapons:** [V]
  - `napalm_mp`: radio view model; projectile `projectile_napalm_bomb`; impact fx `weapon/napalm/fx_napalm_ground_burst_mp`; sound `mpl_kls_napalm_exlpo`; whistle `mpl_kls_artillery_whistle`; HUD `hud_icon_air_napalm`; kill icon `hud_obit_napalm`.
  - `napalmground_lg_mp` and `napalmground_sm_mp`: fx `weapon/napalm/fx_napalm_ground_fire_lg_mp` and `_sm_mp`.
  - `napalmblob_mp` exists. [V]
- **Model:** `t5_veh_jet_f4_gearup`. **Selector:** `map_napalm_selector`. **Rumbles:** `plane_rumble`, `artillery_rumble`. [V]
- **Client FX:** `trail/fx_geotrail_jet_contrail`, `vehicle/exhaust/fx_exhaust_jet_afterburner`; client sound `evt_us_napalm_wash`. [V]
- **Sounds:** `mpl_kls_napalm_exlpo`, `mpl_kls_napalm_fire`; inform `mpl_killstreak_napalm`; dialogue `kls_napalm_used`, `kls_napalm_enemy`, `kls_napalm_ready`. [V]
- **Strings:** `MP_EARNED_NAPALM`, `KILLSTREAK_NAPALM_NOT_AVAILABLE`, `MP_WAR_NAPALM_INBOUND`, `MP_WAR_NAPALM_INBOUND_NEAR_YOUR_POSITION`. [V]

#### 6.4 Bots
- **Stock** (`bot_killstreak_location(1, weapon)`): one confirm at a random enemy ±512 in X/Y, with a **random yaw** in 0–359. [V]
- **Suggested refinement** [I]: aim the yaw so the 7 × 200 = 1400-unit flame line runs through the most enemy positions, e.g. along a corridor or between two known enemies.

---

### 7. Attack Dogs (`dogs_mp`)

#### 7.1 Earning
See 0.1. The threshold is 11 kills (statstable col 5) [V]. It is round-delayed. Dog kills (`dog_bite_mp`, registered alt weapon) are credited to the owner (`_globallogic_player.gsc updateAttacker()`) but do not advance the owner's streak. [V]

#### 7.2 Mechanics
**Prerequisites** (`_dogs.gsc useKillstreakDogs()`, `dog_manager_spawn_dogs()`): [V]
- The map needs path nodes (otherwise `level.no_dogs` is set) and a `dog_spawner` ent. If there is no spawner the function just returns, but the rule is already taken.

**Numbers** (`dog_dvar_update()`): [V]

| Value | Setting |
|---|---|
| Total dogs | `scr_dog_count` 8 |
| Alive at once | `scr_dog_max_at_once` 4 |
| Health | `scr_dog_health` 100 |
| Duration | `scr_dog_time` 60 s |
| Engine cap | 16 AI dogs, including any pre-placed in the BSP |

**Spawn and replacement:** [V]
- The first 4 spawn one after another, waiting `randomfloat(2, 5)` between each.
- `randomfloat` takes a single argument, so the real wait is probably 0–2 s. [I]
- After that, each dog death spawns one replacement after the same wait, until 8 have spawned.
- Spawn node: in team modes `dog_pick_node_near_team()`; in FFA `dog_pick_node_away_from_enemy()`.

**End:** [V]
- At 60 s the code notifies "dogs leaving". Each dog then ignores everything, runs to the nearest exit node and is deleted.
- Fail-safe deletion if a dog is stuck for 2 s, or after 22 s.
- The rule is released once no dogs are alive (`dog_manager_dog_alive_tracker()`).
- Game end, or the owner disconnecting, also triggers leaving.

**AI** (`init_dog()`, `dog_patrol()`, `animscripts/dog_combat.gsc`, `animscripts/dog_init.gsc`): [V]
- Accuracy 0.2, goal radius 128, `pathEnemyFightDist` 512, `meleeAttackDist` 102.
- With no enemy, a dog patrols random patrol nodes that are more than 1024 apart, skipping nodes that have a `script_noteworthy`.
- Attack is a code `melee()` on an animation notetrack, plus shellshock `dog_bite` for 1 s.
- **Per-bite damage** is engine/AI melee and is not in the script. [U]
- `level.dog_hits_before_kill` = 1 and the comment "a little more than one bite does" at health 25 suggest a bite deals somewhat under 25 with knockdown logic. However the instant-kill check returns early, so the exact MP behaviour is [U]. [I]
- `level.maxDogsAttackingPerPlayer` = 2 is set, but its consumer is not in script. [U]

**Regen** (`dogHealthRegen()`): after 5 s without damage, a dog regenerates to full. Below 55 % it regenerates gradually, +0.1 of max per tick after 3 s. [V]

**Ownership:** [V]
- `setentityowner(owner)`, team = owner's team (FFA: "free").
- If the owner changes team, ownership is cleared.
- Friendly models `german_shepherd`; enemy model `german_shepherd_black`.

**Countering:** [V]
- Killing a dog gives XP `dogkill` (30 team / 20 FFA).
- Flash and concussion grenades stun dogs: `setFlashBanged` for 500 ms, at most once per 1.5 s (`flash_dogs()`).
- Attack helicopters target dogs (`_helicopter.gsc canTargetDog_*`).

**Minimap:** the weapon's HUD icon is `compass_objpoint_dogs`. Whether dogs appear on any minimap is not set in script. [U]

**Limits:** dog, 1 global / 1 per team. Only one pack can exist on the map at any time. [V]

#### 7.3 Assets
- **Weapons:** `dogs_mp` (radio world model `t5_weapon_radio_world`; HUD/dpad `compass_objpoint_dogs`; kill icon `hud_obit_dogs`) and `dog_bite_mp` (shellshock `dog_bite`). [V]
- **Models:** `german_shepherd`, `german_shepherd_black`; animtree `dog.atr`. [V]
- **Client sounds** (`clientscripts/mp/_dogs.csc`): `aml_dog_bark`, `aml_dog_bark_close`, `aml_dog_bark_mid`, `aml_dog_death`, `aml_dog_lock`, `aml_dog_pain`, `aml_dog_run_gear`, `aml_dog_run_gear_enemy`, `aml_dog_run_gear_enemyteam`, `aml_dogstep_run_*`, `fly_dog_step_run_default`. [V]
- **Inform and dialogue:** inform `mpl_killstreak_dogs`; dialogue `kls_dogs_used`, `kls_dogs_enemy`, `kls_dogs_ready`. [V]
- **Strings:** `KILLSTREAK_EARNED_DOGS`, `KILLSTREAK_DOGS_NOT_AVAILABLE`, `KILLSTREAK_DOGS_INBOUND`. [V]

#### 7.4 Bots
- **Using:** a stock bot simply switches to the weapon (instant use). [V]
- **Defending** (`bot_dogs_think()`): every 1 s, if any enemy dog is within 1024, the bot sets it as its script enemy. [V]
- **Suggested addition** [I]: for engine-run dogs, reuse the stock patrol and attack values above, and have bots throw flash or concussion grenades at a dog within 300.

---

### 8. Attack Helicopter (`helicopter_comlink_mp`)

#### 8.1 Earning
See 0.1. The threshold is 7 kills (statstable col 5) [V]. It is round-delayed. Kills with its gun (`cobra_20mm_comlink_mp`, alt weapon) do not count towards streaks. [V]

#### 8.2 Mechanics
**Call-in** (`_helicopter.gsc useKillstreakHelicopter()`, `selectHelicopterLocation()`): [V]
- The map needs `heli_start` / `heli_loop_start` paths.
- The player picks a location with `beginLocationComlinkSelection` (icon `compass_objpoint_helicopter`, size 1500), which becomes the protect point.
- **Rules:** vehicle 7/7, chopper (2 global, 1 per team), `playercontrolledchopper` checked (blocked while a player-controlled chopper is up), `chopperInTheAir` counted, targetableent.

**Vehicle and health** (`heli_think()`): [V]

| Property | Value |
|---|---|
| Vehicle | `heli_ai_mp` (`maxSpeed` 90, accel 20, compass icon `hud_anim_cobra`, `addToCompassEnemy` 1) |
| Models | `vehicle_cobra_helicopter_mp_light` (friendly), `vehicle_cobra_helicopter_mp_dark` (enemy) |
| Max health | 1500 (`scr_heli_armored_maxhealth`), tracked in `damageTaken` |
| Bullet damage | × 0.3 (`scr_heli_armor_bulletdamage`); `specialty_armorpiercing` adds a further × `cac_armorpiercing_data` before that scaling |
| Rockets (`MOD_PROJECTILE`) | One-shot (1501), but `tow_turret_mp` (SAM) takes 2 shots (751 each) |
| Chaff | 1 charge: the first lock-on missile is diverted to a decoy and detonated about 1.5 s later (`heli_fire_chaff()`) |
| Damage stages | ≥ 33 %: light smoke. ≥ 66 %: heavy smoke and evasive. Over 100 %: crash. Missile regen speeds up when damaged, but missiles are off for this variant. |
| Owner leaves | If the owner changes team or disconnects, the helicopter leaves (`watchForEarlyLeave()`) |
| XP for the killer | `helicopterkill` 200 (FFA 100); assist tiers 25/50/75 % give 50/100/150 (`processCopterAssist()`) |
| SAM turrets | Can acquire it only after its first `turret_on_target`, path start or near-goal event (`SAMTurretWatcher()`) |

**Flight** (`heli_protect()`): [V]
- It is in the air for **60 s** (`scr_heli_protect_time`).
- It flies to the chosen point at the highest node height on its start path, plus 800 for axis, raised to clear no-fly zones.
- It then hovers **12 s** per spot (`scr_heli_protect_pos_time`), or 2 s when evasive, before moving to a random point **400–1600** from the chosen spot (radius 2000 with a 20 % margin).
- **Speeds:** normal 30–49 (accel 10–14), evasive 50–69, hover 20. Hover is interrupted by a lock-on.
- **Leaving:** speed 105 to a random leave node, then deleted, which releases the rule (`heli_leave()`, `destroyHelicopter()`).

**Targeting** (`heli_targeting()`, `canTargetPlayer_turret()`, `update_player_threat()`): [V]
- Scans every 0.5 s.
- A player is a valid target if they are alive and playing, not the owner, not a teammate, within **3500**, and not carrying `specialty_nottargetedbyai`.
- They must also be more than 5 s past spawning (`scr_heli_target_spawnprotection`), and `sightConeTrace` from the gun point (160 below, 144 forward) must see at least 50 % of them.
- **Threat score:**
  - (3500 − distance) / 3500 × 100,
  - +100 if they were the last attacker,
  - +200 if carrying a game object,
  - + 4 × score,
  - − antithreat (100 per burst already fired at them).
- The highest-threat target is chosen; enemy dogs are included. The helicopter yaws to face its primary target once a second.

**Gun** (`attack_primary()`): [V]
- The turret must be within **35°** (`scr_helicopterTurretMaxAngle`).
- Aim is target + 50 z, then + 40.
- Spin-up 0.75 s, then a **20-round** burst (`scr_heli_turretClipSize`) at the weapon fire time. `cobra_20mm_comlink_mp` has `fireTime` 0.05, so the burst lasts about 1 s.
- Then a **1.5 s** reload.
- If the target is lost mid-burst, the gun keeps firing at the last known position.

**Round damage, from the weapon def** (`weapons/cobra_20mm_comlink_mp`): [V]
- Bullet type with medium penetration.
- `damage` 10, `minDamage` 30, `maxDamageRange` 15000, `minDamageRange` 16000.
- `explosionRadius` 64 at 10/10, `projectileSpeed` 10000.
- How the engine resolves damage 10 against minDamage 30 is [U]. Measure it in game.

**Missiles:** disabled for this streak. `missilesEnabled` is true only for `helicopter_x2_mp`. [V]

#### 8.3 Assets
- **Weapons:** `helicopter_comlink_mp` (radio models; HUD `compass_objpoint_helicopter`; dpad `hud_ai_helicopter`; kill icon `hud_obit_cobra`) and `cobra_20mm_comlink_mp` (fire sound `mpl_wpn_heli_fire_npc`). `cobra_20mm_mp` is also precached. [V]
- **Vehicle:** `heli_ai_mp`. **Models:** `vehicle_cobra_helicopter_mp_light`, `vehicle_cobra_helicopter_mp_dark`, `t5_veh_helo_hind_killstreak`, `projectile_hellfire_missile`. [V]
- **FX:** [V]
  - `explosions/fx_exp_tanker`
  - `vehicle/vexplosion/fx_vexplode_helicopter_exp_mp`, `vehicle/vexplosion/fx_vexplode_heli_killstreak_exp_sm`
  - `explosions/fx_exp_aerial`
  - `trail/fx_trail_heli_killstreak_engine_smoke_33`, `_66`, `trail/fx_trail_heli_killstreak_tail_smoke`, `trail/fx_trail_heli_black_smoke`, `trail/fx_trail_heli_killstreak_engine_smoke`
  - `vehicle/props/fx_cobra_rotor_main_run_mp`, `vehicle/props/fx_cobra_rotor_small_run_mp`, `vehicle/props/fx_huey_small_blade_dmg`
  - `vehicle/treadfx/fx_heli_dust_default`, `vehicle/treadfx/fx_heli_water_spray`
  - `vehicle/vexplosion/fx_hind_chaff`, `vehicle/vexplosion/fx_heli_chaff`
  - `vehicle/light/fx_cobra_exterior_lights_red_mp`
- **Sounds:** [V]
  - `evt_helicopter_hit`, `evt_helicopter_spin_loop`, `evt_helicopter_spin_start`, `evt_helicopter_midair_exp`
  - `wpn_hellfire_fire_npc`, `wpn_hind_pilot_fire_loop_npc`
  - `veh_huey_chaff_drop_plr`, `veh_huey_chaff_explo_npc`
  - Inform `mpl_killstreak_heli`; dialogue `kls_cobra_used`, `kls_cobra_enemy`, `kls_cobra_ready`
  - Pilot VO per teamset, e.g. `vox_ops_2_kls_attackheli_approach`, `_hit`, `_kill`, `_down`, `_ready`, `_shoot` (`gametypes/_teamset_*.gsc`)
- **Strings:** `KILLSTREAK_EARNED_HELICOPTER_COMLINK`, `KILLSTREAK_HELICOPTER_COMLINK_NOT_AVAILABLE`, `KILLSTREAK_HELICOPTER_COMLINK_INBOUND`, `KILLSTREAK_DESTROYED_HELICOPTER`, `MP_DESTROYED_HELICOPTER`. [V]

#### 8.4 Bots
- **Using** (`bot_killstreak_location(1, weapon)`): one confirm at a random enemy ±512 in X/Y. [V]
- **Countering** (`bot_vehicle_think()`): every 1 s, bots other than "easy" ones engage any enemy `script_vehicle` they have line of sight to. That includes helicopters, the supply chopper and the RC-XD. They only engage aircraft if they hold `m72_law_mp`, `strela_mp`, `m202_flash_mp`, `minigun_mp` or `rpg_mp` with ammo, and they keep the vehicle as script enemy for 7–10 s. [V]
- **Suggested addition** [I]: bots without a launcher should break line of sight from an enemy helicopter, i.e. move indoors or under cover.

---

### 9. Points the engine team should know (summary)
- **Spy plane: about 40 s, not 20 s.** Its radar effectively lasts 40 s (20 s orbit plus 20 s exit while still counted). The counter-spy plane jams for 30 s, and its bookkeeping lasts 50 s. [V]
- **Counter-spy jamming is client-side.** It is a "global scrambler" (`SetEnemyGlobalScrambler`) and does not change server radar state. The compass sweep period and visuals are all engine-side. [U]
- **Your own spy plane is invisible to your team**, visible only to enemies (`SetVisibleToTeam(otherteam)`). [V]
- **A shot-down supply chopper still drops its crate.** The supplydrop rule frees when the chopper leaves, not when the crate is taken. [V]
- **RC-XD script damage differs from its weapon file.** The script uses 350 → 25 over 256, while the weapon def says 200 → 50. The script wins. The car also appears on enemy minimaps. [V]
- **Mortar accuracy radius is 0**, so both shells of a point land on the same spot. Mortar shellshock also hits teammates. [V]
- **Probable script bugs:** [V]
  - The `refCountDecChopperOnDisconnect` notify is misspelt.
  - `_dogs.gsc` passes two arguments to `randomfloat`.
  - `_helicopter.gsc destroyHelicopter()` reads `self.hardpointType` after `self delete()`.
  - The mortar and napalm death-count key (`hardPointItemDeathCount*`) does not match the key `_hardpoints.gsc` writes (`killstreakItemDeathCount*`), so the owner death count is usually undefined. This does not matter, because killstreak-weapon kills never count anyway.

## Black Ops II (t6)

Sources: the decompiled common_mp + common_patch_mp + patch_mp scripts (patch last), the tables and the weapon infostrings. Tags: [V] read directly (file + function cited), [I] inferred, [U] not found in this data. File paths below are relative to `maps/mp/` unless noted.

### 0. Shared system: how scorestreaks are earned, held and used

**Cost source** [V]: `killstreaks/_killstreaks.gsc registerkillstreak()` reads `mp/statstable.csv`, looks the row up by column 4 (the killstreak reference, e.g. `killstreak_spyplane`) and takes:
- column 16 = momentum cost (`momentumcost`)
- column 6 = icon material (`iconmaterial`)
- column 5 = level/quantity (empty for all seven streaks here)

The header row of statstable is just `a0,b1,...,q16,...`, so the cost column is `q16`.

| Streak | Script type (hardpoint) | Menu ref (statstable col 4) | Cost (col 16) | Loadout slot group (col 13) | Icon (col 6) |
|---|---|---|---|---|---|
| UAV | `radar_mp` | `killstreak_spyplane` | **425** | killstreak1 | `hud_ks_u2_spyplane` |
| RC-XD | `rcbomb_mp` | `killstreak_rcbomb` | **450** | killstreak2 | `hud_ks_rcbomb` |
| Hunter Killer | `missile_drone_mp` / `inventory_missile_drone_mp` | `killstreak_missile_drone` | **525** | killstreak1 | `hud_ks_harpy_single` |
| Care Package | `supply_drop_mp` / `inventory_supply_drop_mp` | `killstreak_supply_drop` | **550** | killstreak3 | `hud_ks_supply_drop` |
| Counter-UAV | `counteruav_mp` | `killstreak_counteruav` | **600** | killstreak3 | `hud_ks_counter_uav` |
| Lightning Strike | `planemortar_mp` | `killstreak_planemortar` | **750** | killstreak3 | `hud_ks_planemortar` |
| Sentry Gun | `autoturret_mp` (crate variant `turret_drop_mp`) | `killstreak_auto_turret` | **800** | killstreak2 | `hud_ks_auto_turret` |

[V] all from `mp/statstable.csv`. For reference, other costs in the same column: Guardian 650, Hellstorm 700, Death Machine 850, War Machine 900, Dragonfire 975, AGR 1000, Stealth Chopper 1100, Orbital VSAT 1200, Escort Drone 1250, EMP 1300, Warthog 1400, Lodestar 1500, VTOL 1600, K9 1700, Swarm 1900.

When two types share a menu ref (care package, hunter-killer), the type registered **last** owns the menu ref, because `level.menureferenceforkillstreak[menuname]` gets overwritten (`registerkillstreak()`). The loadout therefore resolves `killstreak_supply_drop` → `supply_drop_mp` (weapon `supplydrop_mp`) and `killstreak_missile_drone` → `missile_drone_mp`. The `inventory_*` variants are what a care package hands out [V `_supplydrop.gsc init()`, `_missile_drone.gsc init()`].

**How momentum accrues** [V `gametypes/_globallogic_score.gsc giveplayerscore()/giveplayermomentum()`, `gametypes/_rank.gsc initscoreinfo()`]:
- Every score event goes through `_scoreevents.gsc processscoreevent()`. That adds the **same** value to `pers["score"]` and to `pers["momentum"]`.
- The value comes from `mp/scoreinfo.csv`, in the column "`<gametype> score`" (looked up via `getscoreeventcolumn(level.gametype)`).
- The `kill` value is multiplied by (1 + gametype setting `killEventScoreMultiplier`); that setting is 0 in `gamesettings_default.cfg`.
- The momentum change is ignored while the player is dead (`giveplayermomentumnotification()` only calls `_setplayermomentum` when `isalive`).

TDM values (scoreinfo `tdm score` column) [V]:

| Event | Score |
|---|---|
| kill | 100 |
| assist_75 / assist_50 / assist_25 | 50 / 25 / 25 |
| uav_assist, counter_uav_assist, satellite_assist | 10 each |
| headshot, first_kill, longshot and other medals | 0 (XP only) |
| destroyed_uav / destroyed_counter_uav | 75 / 100 |
| destroyed_helicopter_supply_drop, destroyed_rcbomb, destroyed_missile_drone, destroyed_plane_mortar, destroyed_sentry_gun | 125 each |
| rcxd_kill, missile_drone_kill, plane_mortar_kill, sentry_gun_kill | 25 each |
| share_package_uav / _rcbomb / _counter_uav etc. (team-mate takes your crate) | 50 |
| kill_enemy_with_care_package_crush | 25 |
| disarm_hacked_care_package | 50 |
| capture_enemy_crate | 0 |
| death | 0 |

**Kills with a killstreak weapon give no `kill` score** [V `_scoreevents.gsc processscoreevent()`]. If the weapon is a killstreak weapon, the event only scores when scoreinfo column 4 ("Killstreaks Allowed Score") is TRUE (`_rank.gsc killstreakweaponsallowedscore()`). `kill` does not have it; the `*_kill` and `destroyed_*` rows do. So a streak kill is worth 25, not 100.

**Hardline** (`specialty_earnmoremomentum`) multiplies positive gains by dvar `perk_killstreakMomentumMultiplier`, rounded to the nearest 5 [V `giveplayermomentumnotification()`]. Value [U].

**Momentum cap and looping** [V `_globallogic_score.gsc _setplayermomentum()`, `_giveplayerkillstreakinternal()`]:
- Momentum is clamped to 0–2000.
- On each increase, every equipped streak whose cost lies in (old, new] is awarded.
- If momentum then reaches the most expensive equipped streak's cost, that cost is subtracted and the award check runs again from 0. The three streaks therefore loop within one life.

**Scorestreak mode vs momentum mode** [V `_rank.gsc init`]:
- `level.usingmomentum` is always 1.
- `level.usingscorestreaks` comes from dvar `scr_scorestreaks` (default [U]; stock public BO2 behaves as scorestreaks [I]).

In scorestreak mode [V `_giveplayerkillstreakinternal()`, `_killstreaks.gsc changekillstreakquantity()`, `gametypes/_class.gsc` loadout code]:
- An earned streak becomes +1 "ammo" (quantity) on its killstreak weapon, capped at dvar `scr_scorestreaks_maxstacking` (value [U]).
- Quantities live in `pers["killstreak_quantity"]`, so **earned, unused streaks survive death** and are re-applied as clip ammo on respawn.
- Changing team wipes them (`_killstreaks.gsc onjoinedteam()`).

**Death resets progress** [V `gametypes/_globallogic_player.gsc` killed handler, `_globallogic_spawn.gsc`]:
- On death, `pers["resetMomentumOnSpawn"]=1` is set.
- On the next spawn, `resetplayermomentumonspawn()` sets momentum to 0, but only when `usingscorestreaks` is on.
- In plain momentum mode, momentum is kept and using a streak subtracts its cost instead (`_killstreaks.gsc removekillstreakwhendone()`).

**Crate-given streaks** are a separate stack [V `_killstreaks.gsc givekillstreakinternal()`]:
- They go to `pers["killstreaks"]` and the "inventory" weapon slot (`setinventoryweapon`).
- The stack holds at most `scr_maxinventory_scorestreaks` items (default 3, `_rank.gsc`); the oldest is removed when full.

**Activation** [V `_killstreaks.gsc killstreakwaiter()`, `triggerkillstreak()`, `usekillstreak()`]:
- Each streak is a weapon. Switching to it (`weapon_change`) triggers use. The weapon is ignored if its ammo is 0 (scorestreak mode) or momentum is below cost (momentum mode).
- Bots count as having pressed the inventory button (`pers["isBot"]`).
- The use function returns true or false. On true, quantity is decremented (or the inventory item removed) and the player is switched back to their last non-killstreak weapon.
- Loadout streaks are bound to action slots 4, 2, 1 in ascending cost order (`_class.gsc`, end of the loadout-streak loop).

**Round-start delay** [V]: `shoulddelaykillstreak()` blocks "delayable" streaks for `level.roundstartkillstreakdelay` seconds. Delayable here means hunter-killer and lightning strike (registered with delaystreak=1). Held weapons and first or single rounds are exempt. The script default is 0 (`_killstreaks.gsc init`); `gamesettings_default.cfg` has `roundStartKillstreakDelay 15`, but no script reads that setting [V grep]. Whether the engine sets the level var is [U].

**Team limits** [V `killstreaks/_killstreakrules.gsc init()`, `createrule(rule, max_global, max_per_team)`, `iskillstreakallowed()`]:
- A streak is refused if any rule it checks is at its global max or its per-team max.
- It is also refused while the player is in last stand or EMP-jammed.
- In non-team modes, the global max is lowered to the per-team value.

| Streak | Rules counted & checked (global / per team) |
|---|---|
| UAV `radar_mp` | radar 20/10, targetableent 32/32 |
| Counter-UAV | counteruav 20/10, targetableent 32/32 |
| Care package `supply_drop_mp` / `inventory_supply_drop_mp` | vehicle 7/7, supplydrop 4/4, targetableent 32/32 |
| RC-XD | rcxd 3/2 |
| Hunter Killer (both types) | missiledrone 3/3 |
| Lightning Strike | planemortar 1/1 |
| Sentry `autoturret_mp` | turret 8/4 (shared with Guardian and the TOW turret); `turret_drop_mp` counts toward vehicle 7/7 and supplydrop 4/4 |

### 1. UAV (`radar_mp`)

**Earned**: 425 (see §0).

**Mechanics** [V `killstreaks/_radar.gsc useradaritem()/usekillstreakradar()`, `killstreaks/_spyplane.gsc callspyplane()/generateplane()/spyplane_timeout()/updateteamuavstatus()/updateplayersuavstatus()/plane_damage_monitor()`]:
- **Duration**: `level.spyplaneviewtime` = 25 s from call-in.
  - When it times out, the radar effect stops immediately: `removeactiveuav()` runs before the exit flight.
  - The plane then unlinks and flies 20,000 units forward for 10 s (`level.spyplaneexittime`), with afterburner FX. It dodges no-fly zones by trying yaw offsets up to 10 times (`plane_leave()`).
  - `level.spyplaneentrancetime` = 5 is defined but not used for timing [V grep].
- **Effect**:
  - **Team modes**: increments `level.activeuavs[team]`, then `uavtracker()` / `updateteamuavstatus()` calls the engine with `setteamspyplane(team, mode)`.
    - mode 1 = normal, mode 2 = **fast** when the team has 2 or more active UAVs.
    - It also sets match flag `radar_allies`/`radar_axis`, plus UI flag `radar_client` per player in multi-team modes.
    - An active Orbital VSAT (`radardirection_mp`) overrides it: spyplane is set to 0 and satellite to 1.
  - **FFA**: per player `hasspyplane` = 1, or 2 with more than one UAV, plus UI flag `radar_client` (`updateplayersuavstatus()`).
  - Only the owner's team (FFA: the owner) gets enemies on the minimap [I from the per-team flag].
  - The sweep itself (sweep vs constant, refresh period of mode 1 vs 2) is engine compass code, not script: [U] in this data. Mode 2 is named "fastsweep" in `useradaritem()`, which implies a sweeping radar with a faster sweep for two or more UAVs [I].
- **Plane placement** (cosmetic, but it is the shootable target):
  - The model is a script_model linked to `level.uavrig`. The rig sits at the centre of the two `minimap_corner` ents, 1100 units up (mp_hydro adds +1200 Y).
  - The rig rotates 360° every 60 s clockwise (`rotateuavrig(1)`) and bobs ±100–200 units over 3–5 s (`swayuavrig()`).
  - The plane is offset in a random direction: horizontal radius 4000–4999, Z 4000–4999. The offset is normalised and rescaled to a length of 4000–4999.
  - It is visible to everyone **except its own team** (`updatevisibility()`; FFA: everyone except the owner).
  - It is lock-on-able (`target_set`), shows in thermal (`setdrawinfrared`), and makes incoming missiles proximity-detonate.
- **Health**: `level.u2_maxhealth` = 700. The entity health is a dummy 99999; damage is tracked in `damagetaken` and the plane dies when that exceeds 700.
  - Rifle and pistol bullets: full damage. With FMJ (`specialty_armorpiercing`) a bullet adds only `int(damage × 0.4)`. `perk_armorpiercing` defaults to 40 (`_class.gsc`), so FMJ actually *reduces* UAV damage. That is a stock quirk/bug [V code; "bug" is I].
  - Any `MOD_PROJECTILE` is a one-shot (adds 701).
  - Everything else adds raw damage.
  - The damage-trail FX starts at 40% (280 damage).
  - Only enemy players count. Owner and team-mates are ignored.
- **On destroy**: team popup, owner dialog `uav_destroyed`, score event `destroyed_uav` (75) to the attacker, crash FX, rule slot freed.
- The owner changing team, disconnecting or going spectator destroys it (`spyplane_watchfor_gamerules_destruction()`).
- **Assist score** [V `_globallogic_score.gsc processkillstreakassists()`]:
  - When a team-mate gets a non-killstreak-weapon kill, every other team-mate with their own UAV active gets `uav_assist` (+10).
  - This is suppressed if any enemy counter-UAV is active and the killer lacks Hardwired (`specialty_immunecounteruav`).
- **Limits**: radar 20 global / 10 per team, so they stack (§0).

**Assets** [V]:
- Weapon `radar_mp` (radio item). View model `t6_wpn_uav_radio_view`, world `t6_wpn_uav_radio_world`, hud/dpad/kill icon `hud_ks_u2_spyplane`.
  - `killstreak_uav_mp` is an identical-looking def that no script references [V grep].
- Plane model `veh_t6_drone_uav`.
- FX: `vehicle/light/fx_u2_lights_red`, `vehicle/exhaust/fx_exhaust_u2_spyplane_burner`, `.../fx_exhaust_u2_spyplane_afterburner`, `trail/fx_trail_u2_plane_damage_mp`, `vehicle/vexplosion/fx_vexplode_u2_exp_mp`.
- Sounds: `veh_uav_engine_loop`, `veh_kls_spy_afterburner`, `evt_helicopter_midair_exp`, `mpl_killstreak_radar` (earned).
- Dialog keys: `kls_u2_used`, `kls_u2_enemy`, `kls_u2_ready`; leader dialog `uav_destroyed`.
- Strings: `KILLSTREAK_EARNED_RADAR`, `KILLSTREAK_RADAR_NOT_AVAILABLE`, `KILLSTREAK_RADAR_INBOUND`.

**Bots**:
- [V `bots/_bot.gsc bot_update_killstreak()`]: every 1–3 s a bot scans its weapons for any killstreak weapon with ammo that `iskillstreakallowed`. UAV falls into the default case, so the bot simply switches to it and it fires at once. Net effect: a bot uses a UAV as soon as it has one.
- [V `bot_has_radar()`, `bot_get_enemies(on_radar)`]: while the bot's team has a UAV or satellite, patrol logic uses every enemy as a known position. Without one, it only uses enemies who fired within the last 2 s.
- [V `_bot_combat.gsc threat_requires_rocket()`]: bots shoot enemy UAVs and CUAVs only with a launcher (SMAW / FHJ-18), and ignore them for 3.5 s when the elevation is outside a band.
  - The check is pitch < 290 in `_bot_combat.gsc bot_best_enemy()`. [I] It reads as "engage only if the target is between level and ~70° above the eye".

### 2. Counter-UAV (`counteruav_mp`)

**Earned**: 600.

**Mechanics** [V `_spyplane.gsc callcounteruav()/counteruavplane_timeout()/addactivecounteruav()`, client `_counteruav.csc spawned()/counteruav_think()`]:
- **Duration**: `level.counteruavviewtime` = 30 s (`_radar.gsc init`).
  - At timeout the effect flag is cleared at once. The plane then flies out for 10 s (`level.counteruavplaneexittime`), and the rule slot is only freed after that exit.
  - `level.counteruavlength` = 25 is defined but unused [V grep].
- **Effect**:
  - The server sets client flag 11 on the CUAV script_model. Client script `_counteruav.csc` registers flag 11 for scriptmovers.
  - Each local client that gets the flag set increments a per-client counter and calls `setenemyglobalscrambler(1)`. It reverts to 0 when the counter drops to zero, which happens on entity shutdown or flag clear.
  - The plane is visible to all except its own team (same `updatevisibility()`), so only enemy clients ever receive the entity and get scrambled [I]. In FFA, everyone except the owner.
  - What "global scrambler" does to the compass (blank, noise, or hiding enemy dots) is engine-side [U]. Stock behaviour is that enemies' minimaps are jammed [I].
  - Hardwired (`specialty_immunecounteruav`, statstable row 153 "PERKS_HARD_WIRED") grants immunity [V perk name]; the immunity is applied by the engine [I].
  - The server also tracks `level.activecounteruavs[team]` (used for assist and challenge logic).
- **Plane**:
  - `veh_t6_drone_cuav` on `level.counteruavrig`, at map centre +1500 Z.
  - The rig rotates 360° every 40 s, counter-clockwise; same sway as the UAV.
  - Horizontal radius 3000–3999, overall offset length 4000–4999, roll −10°.
- **Health / destroy**: identical to the UAV (700, projectile one-shot, the same FMJ quirk). Score `destroyed_counter_uav` (100), leader dialog `cuav_destroyed`.
- **Assist**: the CUAV owner gets `counter_uav_assist` (+10) on each team-mate's non-killstreak kill [V `processkillstreakassists()`].
- **Limits**: counteruav 20/10, targetableent 32/32.

**Assets** [V]:
- Weapon `counteruav_mp` (same radio models), icon `hud_ks_counter_uav`.
- Model `veh_t6_drone_cuav`.
- FX: `vehicle/light/fx_cuav_lights_red`, `vehicle/exhaust/fx_exhaust_cuav_burner`, `.../fx_exhaust_cuav_afterburner`, plus the shared u2 damage and explode FX.
- Sounds: `veh_uav_engine_loop`, `veh_kls_uav_afterburner`, `evt_helicopter_midair_exp`, `mpl_killstreak_radar`.
- Dialog keys: `kls_cu2_used`, `kls_cu2_enemy`, `kls_cu2_ready`.
- Strings: `KILLSTREAK_EARNED_COUNTERUAV`, `KILLSTREAK_COUNTERUAV_NOT_AVAILABLE`, `KILLSTREAK_COUNTERUAV_INBOUND`.

**Bots** [V `bot_update_killstreak()` default case]: used immediately once earned and allowed. [I] A better rule would be to fire it when the enemy team has an active UAV, or right after spawn if not.

### 3. Care Package (`supply_drop_mp`, weapon `supplydrop_mp`; crate-given `inventory_supply_drop_mp` / `inventory_supplydrop_mp`)

**Earned**: 550.

**Use flow** [V `killstreaks/_supplydrop.gsc usekillstreaksupplydrop()/usesupplydropmarker()/supplydropwatcher()/dosupplydrop()/helidelivercrate()/helidropcrate()/dropcrate()`]:
1. Equipping the marker grenade checks the rules. `supplydropwatcher()` immediately calls `killstreakstart("supply_drop_mp")`, so the slot is reserved while it is held.
   - The slot is released if the player switches weapon, dies before throwing, gets EMP-jammed, or if the thrown marker never comes to rest within 10 s (`supplydropgrenadetimeout()`, which deletes it).
2. The marker is thrown like a grenade: `supplydrop_mp` projectileSpeed 960, fuseTime 1 s, smoke-type explosion, fireTime 0.36.
   - When it stops moving (or explodes), the helicopter is called to that point.
   - After the fuse, it plays the blue smoke FX `env/smoke/fx_smoke_supply_drop_blue_mp` for about 3 s. No smoke if an enemy EMP is active.
3. An enemy EMP active at that moment (and the owner lacking `specialty_immuneemp`) cancels the delivery and frees the slot.
4. **Helicopter**:
   - `spawnhelicopter`, vehicle def `heli_supplydrop_mp`, model `veh_t6_drone_supply` (enemies see `veh_t6_drone_supply_alt`).
   - It starts `scr_supplydropIncomingDistance` (default 10,000) units from the drop point, on a random yaw with ±2° jitter and ±100 position jitter.
   - Up to 12 tries rotate the yaw by 30° to find a `gethelipath` route whose start is outside no-fly zones; otherwise it flies straight.
   - It flies at `getminimumflyheight()`: the `air_support_height` struct Z, default 850 [V `_airsupport.gsc getminimumflyheight()`].
   - Speeds (all dvar defaults):
     - Start: 125 with accel 100, max roll 45, pitch 0.
     - 3 s after spawning: 75 with accel 40, yaw speed 100, pitch/roll limits 25/35 (`speedregulator()`).
     - At the goal: waits 1.2 s, releases the crate, waits 0.7 s, then leaves at 150 with accel 40.
   - Exit: to a point 15,000 away, turned ±60–120° (`getheliend()`, 5 path tries, then `heli_leave` nodes). It is deleted on arrival.
   - Air-defence acquisition is enabled only once it is within 1500 of the drop point or inside the spawn bounds (`samturretwatcher()`).
5. **Heli health** [V `spawn_helicopter()`, `_helicopter.gsc heli_damage_monitor()`]:
   - maxhealth 1500, tracked in `damagetaken`.
   - Bullets ×0.5 (dvar `scr_heli_armor_bulletdamage` default 0.5); FMJ adds +40% before that.
   - Any projectile is a one-shot (1501), except the XM-25, which does raw damage.
   - When destroyed (`helidestroyed()`) it slows, spins, and **still drops the crate** after 0.5–1.5 s, then explodes. Score `destroyed_helicopter_supply_drop` (125).
6. **Crate** [V `dropcrate()`, `cratephysics()`, `cratekill()`, `is_touching_crate()`]:
   - Spawned 200 units below the heli (`scr_supplydropOffsetHeight`), then `physicslaunch` with a random force point ±200 XY and vertical velocity ±100.
   - **Crush**: while the crate's per-0.05 s Z delta exceeds 15 units, any living player touching it (bounds +10) takes health+1 damage (`MOD_HIT_BY_OBJECT`, weapon `supplydrop_mp`, attacker = crate owner). Equipment it touches detonates or is deleted; tactical insertions fizzle.
   - The crush check stops after 20 consecutive near-still frames.
   - Crates that never settle are deleted after 20 s (`timeoutcratewaiter()`).
   - A settled crate lasts **90 s** (`cratetimeoutthreader()` → `cratetimeout(90)`).
7. **Contents** [V `cratespawn()` → `getrandomcratetype("supplydrop_mp")`, weights from `init()`; the weights sum to exactly 1000, so they read as per-mille]:

| Contents | Weight / 1000 |
|---|---|
| UAV `radar_mp` | 100 |
| Counter-UAV | 100 |
| RC-XD | 100 |
| Hunter Killer (`inventory_missile_drone_mp`) | 100 |
| Guardian (`microwaveturret_mp`) | 120 |
| Hellstorm (`remote_missile_mp`) | 85 |
| Lightning Strike | 80 |
| Sentry Gun | 80 |
| Death Machine (`inventory_minigun_mp`) | 60 |
| War Machine (`inventory_m32_mp`) | 60 |
| Escort Drone, Orbital VSAT, Dragonfire, AGR, Stealth Chopper | 20 each |
| EMP | 5 |
| Lodestar, VTOL Warship, K9, Warthog, Swarm | 2 each |

   The `inventory_supplydrop_mp` category has the same weights. A separate `gambler_mp` table exists for a perk/variant [V].

8. **Capture** [V `crateusethink()`, `crateusethinkowner()`, `useholdthink()`, `givecratecapturemedal()`, `default_land_function()`]:
   - The player must be alive and on the ground.
   - Owner hold time 0.5 s (`crateownerusetime` 500). Anyone else takes gametype setting `crateCaptureTime` × 1000 = **3 s** (default 3 in `gamesettings_default.cfg`).
   - The user is frozen with their weapon disabled while holding, and a personal use bar is shown.
   - Contents are given via `givekillstreak()` into the inventory stack (§0).
   - A team-mate taking the crate gives the owner the crate type's share score (e.g. `share_package_uav` 50). An enemy taking it gets `capture_enemy_crate` (XP only) and the owner hears `mpl_crate_enemy_steals`.
9. **Booby-trapping** [V `default_land_function()`, `spawn_explosive_crate()`, `watch_explosive_crate()`]:
   - If an enemy with Engineer (`specialty_showenemyequipment`), or one using the Black Hat hack (`remote_hack`), captures it, a trapped crate is spawned in its place.
   - When an enemy without those perks opens the trapped crate, it beeps and explodes: radius 256, max 300, min 75, `MOD_EXPLOSIVE`, credited to the hacker.
   - Black Hat hack radius is 60 and time is `crateCaptureTime` × 500 ms (`_hacker_tool.gsc`).
10. **Map and head icons** [V `crateactivate()`]: objective icon `compass_supply_drop_green` for the owner team, `compass_supply_drop_red` for enemies, `compass_supply_drop_black` if hacked. Head icon is the contents' icon + `_drop` (e.g. `hud_ks_u2_spyplane_drop`).

**Assets** [V]:
- Weapons `supplydrop_mp` and `inventory_supplydrop_mp`:
  - View `t6_wpn_grenade_supply_view`, world `t6_wpn_grenade_supply_world`, projectile `t6_wpn_grenade_supply_projectile`.
  - Icon `hud_ks_supply_drop`, kill icon `hud_obit_crate`, fire sound `wpn_grenade_throw`.
- Crate models: `t6_wpn_supply_drop_ally`, `t6_wpn_supply_drop_axis` (enemy view), `t6_wpn_supply_drop_detect` (hacker), `t6_wpn_supply_drop_trap`, `t6_wpn_drop_box` (AGR).
- Heli: `veh_t6_drone_supply` / `veh_t6_drone_supply_alt`, vehicle `heli_supplydrop_mp`. Anims `o_drone_supply_care_idle` / `o_drone_supply_care_drop`, attach tag `tag_care_package`, clientfield `supplydrop_care_package_state`.
- FX: `env/smoke/fx_smoke_supply_drop_blue_mp`, `explosions/fx_grenadeexp_default`, heli death FX from `level.chopper_fx`.
- Sounds: `veh_supply_drop`, `phy_impact_supply`, `mpl_supply_crush`, `mpl_crate_enemy_steals`, `mpl_crate_friendly_steals`, `wpn_semtex_alert`, `wpn_grenade_explode`, `mpl_turret_alert`, `mpl_killstreak_supply`.
- Dialog keys: `kls_supply_used`, `kls_supply_enemy`, `kls_supply_ready`, and `kls_full` when the airspace is full.
- Strings: `KILLSTREAK_EARNED_SUPPLY_DROP`, `KILLSTREAK_AIRSPACE_FULL`, `KILLSTREAK_SUPPLY_DROP_INBOUND`.

**Bots**:
- [V `_bot.gsc bot_use_supply_drop()`]: the bot only throws a care package **within 5 s of spawning**. The point 384 units ahead (by yaw) must have open sky 2048 up, from both the point and the bot, and ground within 32 units below. The bot stops, looks at the point for 0.5 s, switches to the marker and presses fire up to 11 times.
- [V `bot_update_crate()`, called from `_bot_combat.gsc`]: every 1–3 s, if a crate is within `player_useRadius`, the bot crouches and holds use for the capture time + 0.5 s. A bot with the Black Hat (`pda_hack_mp`) also hacks visible friendly-objective crates.
- `crateactivate()` notifies `bot_crate_landed` on a bot owner, but nothing listens for it [V grep].
- [I] Suggested: also walk to its own crate when it lands, since there is no stock pathing to a distant crate.

### 4. RC-XD (`rcbomb_mp`)

**Earned**: 450.

**Mechanics** [V `killstreaks/_rcbomb.gsc usekillstreakrcbomb()/usercbomb()/spawnrcbomb()/calculatespawnorigin()/cartimer()/blowup()/cardetonatewaiter()`]:
- **Use**: the player must be on the ground and not remote-controlling.
  - Placement is 70 units ahead, testing yaw offsets 0, ±20, ±45.
  - It needs at least 3 of 4 wheel traces touching (else 2), a clear 12×12×15 box, and a clear sweep from the player; it fails on telefrag.
  - The player goes through a ride intro (`initridekillstreak`), then drives the vehicle (`usevehicle`). Their body is frozen in place [I].
- **Vehicle**: `spawnvehicle` with vehicle def `rc_car_medium_mp`, model `veh_t6_drone_rcxd` (enemy `veh_t6_drone_rcxd_alt`). Aim-assist target, thermal-visible, spawn influencers.
  - Speed and handling come from the vehicle def [U]. A jump helper exists but is never started [V].
- **Duration**: when gametype setting `vehiclesTimed` is 1 (default 1), total **30 s**: 20 s, then countdown clientfield step 1 for 6 s, step 2 for 4 s, then auto-detonate.
- **Detonate**: the attack button detonates it, with a fade-to-black for the owner.
  - **Explosion**: radius **256**, max **350**, min **25**, `MOD_EXPLOSIVE`, weapon `rcbomb_mp`, plus a physics push and an earthquake.
  - Touching a `trigger_hurt` force-detonates it (a water exception on mp_castaway).
- **Destroyed** by enemy damage through `_globallogic_vehicle.gsc callback_vehicledamage()`. Health comes from the vehicle def [U].
  - Killed by an EMP weapon: no explosion.
  - Kill credit: `destroyed_rcbomb` (125) to an enemy attacker.
  - Flashbangs (`monitorrcbombflash`) and stuns freeze controls.
  - Inside an enemy scrambler's inner radius it gets client flag 9 (jammed visuals) [V `watchforscramblers()`].
- **Limits**: rcxd 3 global / 2 per team. A streak kill gives `rcxd_kill` (25).

**Assets** [V]:
- Weapon `rcbomb_mp`: view `t6_wpn_tablet_view`, world `t6_wpn_tablet_world`, icon `hud_ks_rcbomb`, kill icon `hud_obit_rcbomb`.
- Vehicle `rc_car_medium_mp`, models `veh_t6_drone_rcxd` / `veh_t6_drone_rcxd_alt`.
- FX:
  - `maps/mp_maps/fx_mp_exp_rc_bomb`, `weapon/grenade/fx_spark_disabled_rc_car`.
  - `vehicle/light/fx_rcbomb_blinky_light`, `_solid_light`, `_light_green_os`, `_light_red_os`.
  - Tread FX `vehicle/treadfx/fx_treadfx_rcbomb_{dust,concrete}[_drift|_peel|_first_person|_reverse|_trail|_slow]`.
- Sounds: `mpl_rc_exp`, `mpl_killstreak_rcbomb`. Rumbles `rcbomb_engine_stutter`, `rcbomb_slide`.
- Dialog keys: `kls_rcbomb_used`, `kls_rcbomb_enemy`, `kls_rcbomb_ready`.
- Clientfields: `rcbomb_death`, `rcbomb_countdown`.

**Bots**:
- [V `bots/_bot_loadout.gsc` `level.bot_banned_killstreaks`]: RC-XD is **banned** from bot loadouts, and `bot_update_killstreak()` returns early for it.
- `_bot.gsc` contains `bot_rccar_think()` / `bot_rccar_kill()`, but nothing calls them [V grep]. That dead code:
  - Polls every 0.5 s and detonates when any living enemy is within 200 units (512 on easy).
  - Detonates if the car has moved less than 16 units over about 3 s (stuck).
- [I] Port that as the bot rule, with Detour pathing toward the nearest radar-known or recently-seen enemy.

### 5. Hunter Killer (`missile_drone_mp`; crate-given `inventory_missile_drone_mp`)

**Earned**: 525 (delayable at round start).

**Mechanics** [V `killstreaks/_missile_drone.gsc missile_drone_killstreak()/usemissiledrone()/missiledronewatcher()/domissiledrone()/drone_target_search()/projectile_find_target*()/check_target_lost()/watchdamage()/updatetargetting()`]:
- **Held phase**:
  - `killstreakstart` runs when it is equipped; the slot is released on weapon change or death before the throw.
  - While held, every 0.5 s (`scr_missile_drone_update_wait`) it pre-acquires a target within cos ≥ 0.9 (about 25.8°, `scr_missile_drone_min_cos`) of the player's view.
  - Clientfield `missile_drone_active` = 1 means searching, 2 means a target is locked.
- **Launch**: on the throw (`grenade_fire`), the grenade is hidden and deleted after 0.05 s.
  - A guided projectile `missile_drone_projectile_mp` is `magicbullet`-spawned at the throw point, aimed 10,000 units along the player's view, with a script_model goal.
  - Sound `wpn_hunter_ignite`.
- **Targeting** (every 0.25 s; the acceptance cone widens per pass: dot 0.9 → 0.7071 → 0.5 → 0, then stays at 0):
  - **Killstreak candidates**:
    - Anything `target_set` (UAV, CUAV, helis, turrets, etc.), RC-XDs and dogs, excluding own and team-mate items and supply-drop helis.
    - The first one with a clear trace is taken.
  - **Player candidates** (`player_valid_target` in `_missile_swarm.gsc`):
    - Excluded: dead players, the owner, team-mates, Blind Eye users (`specialty_nottargetedbyairsupport`, via `_airsupport.gsc cantargetplayerwithspecialty()`), and anyone who spawned less than 3 s ago.
    - Score per target: +4 for a clear trace to the feet, +3 to the head, +2 for a clear trace from the head to 96 above.
    - A score of 9 or more is taken immediately; otherwise the best score of at least 3.
  - If both a killstreak and a player qualify, the one more aligned with the drone's heading (higher dot) wins.
  - The target is lost after 3 consecutive failed line-of-sight traces at 0.25 s; then it re-searches.
  - With no target, the goal is placed 1024 units ahead at Z = map centre + **2400** (`level.missile_drone_flyheight`), so it loiters over the map.
  - The target gets a `stinger_fired_at_me` notify, so missile-warning HUD and flares react.
- **Projectile** (`missile_drone_projectile_mp` def):
  - guidedMissileType Drone, maxSteeringAccel 50, projectileSpeed 200, projectileLifetime **25 s**.
  - Explosion radius **300**, inner **350**, outer **75**; direct-hit damage 350.
  - Effective cruise speed is an engine guided-missile behaviour [U].
- **Destruction**: any damage from an enemy player detonates it (health 100,000, but `watchdamage()` calls detonate on any valid hit). Score `destroyed_missile_drone` (125). The owner disconnecting or changing team also detonates it.
- Sentries take ×10 damage from it.
- Team-kill penalty scale 0.
- **Limits**: missiledrone 3/3. Kill gives `missile_drone_kill` (25).

**Assets** [V]:
- Weapons:
  - `missile_drone_mp` / `inventory_missile_drone_mp`: view `veh_t6_drone_hunterkiller_viewmodel`, world `veh_t6_drone_hunterkiller`, icon `hud_ks_harpy_single`.
  - `missile_drone_projectile_mp`: model `veh_t6_drone_hunterkiller_viewmodel`, kill icon `hud_obit_hk_drone`.
- Anim `o_drone_hunter_launch`.
- FX: `weapon/missile/fx_missile_drone_light_red`, `weapon/harpy_swarm/fx_hrpy_swrm_explosion`, `weapon/harpy_swarm/fx_hrpy_swrm_exhaust_trail_close`, `explosions/fx_exp_equipment_lg` (dud).
- Sounds:
  - Drone: `wpn_hunter_loop`, `wpn_hunter_fire_npc`, `wpn_hunter_pullback_npc`, `wpn_hunter_ignite`, `wpn_hunter_dud`, `veh_harpy_drone_swarm_incomming`.
  - Weapon handling: `fly_hunter_raise_npc`, `fly_hunter_first_raise_npc`, `fly_hunter_put_away_npc`.
  - Other: `wpn_grenade_explode`, `mpl_killstreak_missile_drone`.
- Dialog keys: `kls_hkdrone_used`, `kls_hkdrone_enemy`, `kls_hkdrone_ready`.
- Clientfields: `missile_drone_active` (toplayer), `missile_drone_projectile_active`, `missile_drone_projectile_animate`.

**Bots** [V `bot_update_killstreak()` → `bot_use_supply_drop()`]: same open-sky / ground test as the care package, but with no 5 s spawn restriction. The bot looks 384 units above the point and throws. Because targeting is automatic, that is all a bot needs.
- [I] Better: only throw when `projectile_find_target` (cos 0.5) would already return something, or when the enemy team has air streaks up.

### 6. Lightning Strike (`planemortar_mp`)

**Earned**: 750 (delayable at round start).

**Mechanics** [V `killstreaks/_planemortar.gsc usekillstreakplanemortar()/selectplanemortarlocation()/singleradarsweep()/useplanemortar()/doplanemortar()/dobombrun()/dropbomb()/planewatchforemp()`]:
- **Selection**:
  - The map location selector is `map_mortar_selector`, with an 800-unit circle passed to `beginlocationmortarselection`. The player picks **3** points.
  - On opening, if the owner has no UAV/satellite and `forceRadar` is off, there is one 0.2 s enemy reveal on the owner's compass: the `g_compassShowEnemies` UI flag is toggled on, then off.
    - It is skipped if the previous selection was cancelled (`pers["mortarRadarUsed"]`).
  - Cancelling, or an EMP during selection, returns false: the streak is not consumed.
  - Rules are re-checked after the third pick.
- **Run**:
  - `killstreakstart`, wait 1.25 s, then one bomb run per point, **0.8 s apart**.
  - Plane yaw: random start, then alternately +35° and +290°.
  - Each plane (script_model `veh_t6_air_fa38_killstreak`, enemy `_alt`) spawns 12,000 units before the point at height `getminimumflyheight()` + 2000 (raised to clear no-fly zones). It moves to 18,000 units past the point over **2.5 s**.
  - The bomb is released 1 s after spawn.
- **Bomb aim-snap**: at release, if any enemy is within **500** units (2D, squared 250,000) of the chosen point with a clear vertical trace from plane height, the bomb is retargeted to that enemy's position.
  - It is launched straight down with velocity −5000 Z via `launchbomb("planemortar_mp")`.
- **Damage** (`planemortar_mp` def): explosion radius **600**, inner **600**, outer **75**, direct 600. Explosion sound `mpl_kls_artillery_impact`, whistle `mpl_kls_mortar_whistle`.
- **Countermeasures**: there is no damage monitor on the plane. Only an EMP (`emp_deployed`) removes it, giving `destroyed_plane_mortar` (125) to the EMP user.
  - The owner being EMP-jammed aborts remaining runs.
  - The kill cam follows the bomb.
- After the runs, battle-damage-assessment dialog plays based on `planemortarbda` (0 / 1 / 2 / 3 / more kills).
- Team-kill penalty is reduced (`level.teamkillreducedpenalty`).
- **Limits**: planemortar **1 global / 1 per team**, so only one lightning strike in the air at a time. Kill gives `plane_mortar_kill` (25).

**Assets** [V]:
- Weapon `planemortar_mp`: weaponType bomb, view `t6_wpn_tablet_view`, world `t6_wpn_tablet_world`, projectile `projectile_hellfire_missile`, icon `hud_ks_planemortar`, kill icon `hud_obit_mortar`.
- Location selector `map_mortar_selector`.
- Models `veh_t6_air_fa38_killstreak` / `_alt`.
- FX `vehicle/exhaust/fx_exhaust_f35_afterburner`; clientfield `planemortar_contrail`.
- Sounds: `mpl_lightning_flyover_boom`, `mpl_lightning_bomb_incoming`, `mpl_kls_mortar_whistle`, `mpl_kls_artillery_impact`, `mpl_killstreak_planemortar`.
- Pilot dialog: `a10_used`, `kls_killn` / `kls_kill1` / `kls_kill2` / `kls_kill3` / `kls_killm`, with the team prefix and voice number.
- Dialog keys: `kls_planemortar_used`, `kls_planemortar_enemy`, `kls_planemortar_ready`.
- Strings: `MP_EARNED_PLANEMORTAR`, `KILLSTREAK_PLANEMORTAR_NOT_AVAILABLE`, `MP_WAR_PLANEMORTAR_INBOUND`, `MP_WAR_PLANEMORTAR_INBOUND_NEAR_YOUR_POSITION`.

**Bots** [V `_bot.gsc bot_killstreak_location(3, weapon)`]:
- Runs only if the bot has any enemies. It switches to the weapon, waits up to 1 s for `selectinglocation`, then waits 2 s.
- It then sends 3 `confirm_location` notifies 0.25 s apart, each on a **random enemy's current origin**. That is omniscient: `getenemies` is not filtered by radar.
- [I] For fairness, restrict to radar-visible or recently-seen enemies; prefer clusters within 500 units, because the aim-snap covers the rest.

### 7. Sentry Gun (`autoturret_mp`; crate-drop variant `turret_drop_mp`)

**Earned**: 800.

**Mechanics** [V `killstreaks/_turret_killstreak.gsc usesentryturretkillstreak()/usesentryturret()/setupturrethealth()/initturret()/watchdamage()/watchturretlifespan()/watchownerdeath()/turret_sentry_think()`, `_mgturret.gsc burst_fire_unmanned()/init_turret_difficulty_settings()`]:
- **Use**: spawns turret classname `auto_turret` with turret weapon `auto_gun_turret_mp`, held by the player.
  - Placement preview uses model `t6_wpn_turret_sentry_gun_yellow` (valid) or `t6_wpn_turret_sentry_gun_red` (invalid).
  - It cannot be placed in hurt triggers, minefields or `no_turret_placement` triggers.
  - The streak only counts as used on `turret_placed`. If the owner dies before ever planting it, it returns to inventory.
- **Activation**: model `t6_wpn_turret_sentry_gun`, mode `auto_nonai`, startup sound, head icon 70 units up, spawn influencers.
  - Difficulty "fu": convergence 0.4 s, suppression 3.0 s, accuracy 0.38, aiSpread 2, playerSpread 0.5.
  - After **1.6 s** (`turretinitdelay`) it starts `burst_fire_unmanned`:
    - While the engine says it is firing, it shoots every **0.112 s** for bursts of **0.5–4.5 s**, with pauses of **0.2–0.7 s**.
    - It plays `mpl_turret_alert` at each burst start.
  - The owner can take manual control via `killstreak_remote_turret_mp` (`_remote_weapons.gsc`). Bots are excluded from the remote trigger.
- **Turret weapon** `auto_gun_turret_mp` [V def]:
  - Damage **35 → 25** between 1200 and 2000 units, maxRange **1800**.
  - Arcs: left / right **65°**, top **45°**, bottom **20°**.
  - Pitch convergence 0.5 s, yaw convergence 1 s; large penetration; unlimited ammo.
  - Weapon fireTime 0.051, but the script loop paces fire at 0.112 s.
  - Target selection is engine turret code [U].
- **Lifetime**: **240 s** (`level.auto_turret_timeout`), counted only while placed (not while carried). After that it self-destructs.
- **Health**: 650, tracked in `damagetaken`.
  - Bullets ×0.6 (FMJ +40% first; shotguns ×5 first).
  - Explosives ×2.
  - Hellstorm missile, Lodestar and Hunter Killer ×10.
  - SMAW / FHJ-18 direct hit = 400.
  - Melee does nothing.
  - EMP grenade splash = instant destroy, and also a 5 s stun.
  - Crush = destroy.
  - Damage FX appears past 650 / 1.8 ≈ 361.
  - Team-mates do no damage unless friendly fire is on.
- **On destroy by enemy**: `destroyed_sentry_gun` (125), owner dialog `sentry_destroyed`, explode FX.
- **Other**: the owner can pick it up and re-place it (`spawnturretpickuptrigger()`). Black Hat hack radius 80, time 4000 ms (`_hacker_tool.gsc`). Scramblers and tactical grenades stun it.
- **Owner death while carrying**: if it was never planted, it returns to inventory. If it had been planted and the spot is valid, it is auto-placed. Otherwise it is destroyed.
- **Limits**: turret **8 global / 4 per team** (shared with Guardian and TOW). Kill gives `sentry_gun_kill` (25).

**Assets** [V]:
- Weapons:
  - `autoturret_mp` (thrown item; icon `hud_ks_auto_turret`, kill icon `hud_obit_turret`).
  - `auto_gun_turret_mp`: detect model `t6_wpn_turret_sentry_gun_detect`; flash FX `weapon/talon/fx_muz_talon_gun_flash_1p`, `weapon/muzzleflashes/fx_muz_snpr_flash_3p`; shell eject `weapon/shellejects/fx_minigun`.
  - `turret_drop_mp` (icon `hud_ks_auto_turret_marker`).
  - `killstreak_remote_turret_mp`.
- Models: `t6_wpn_turret_sentry_gun`, `_yellow`, `_red`.
- FX: `weapon/sentry_gun/fx_sentry_gun_emp_stun`, `.../fx_sentry_gun_damage_state`, `.../fx_sentry_gun_death_state`, `.../fx_sentry_gun_exp`, `explosions/fx_exp_equipment_lg`.
- Sounds:
  - Firing: `wpn_mp_auto_turret_fire_loop_npc`, `wpn_mp_auto_turret_fire_loop_ring_npc`, `wpn_mp_auto_turret_fire_loop_start_npc`.
  - Spin: `wpn_mp_auto_turret_loop_npc` / `_plr`, `wpn_mp_auto_turret_start_npc` / `_plr`, `wpn_mp_auto_turret_stop_npc` / `_plr`.
  - Servo: `mpl_turret_servo`, `mpl_turret_servo_stop`.
  - Other: `mpl_turret_startup`, `mpl_turret_alert`, `fly_riotshield_impact_knife`, `mpl_killstreak_auto_turret`.
- Dialog keys: `kls_turret_used`, `kls_turret_enemy`, `kls_turret_ready`.
- Strings: `KILLSTREAK_EARNED_AUTO_TURRET`, `KILLSTREAK_AUTO_TURRET_NOT_AVAILABLE`, `KILLSTREAK_SENTRY_TURRET_PICKUP`.

**Bots**:
- [V `_bot.gsc bot_turret_location()`]: the bot places it only when all of these hold:
  - Its closest enemy is within 45° of its view (dot ≥ 0.707).
  - There is a `getvisiblenode` between them, at least 512 units from the bot, and also within 45° of view.
  - It then switches to the turret, freezes for 1 s and presses fire, which places it at its feet.
- [V `_bot_combat.gsc`]: against an enemy sentry, bots mark nearby nodes dangerous (`bot_turret_set_dangerous`), throw smoke, EMP and lethals at it, and skip carried or inactive turrets. When killed by a turret, they flag the 384-unit area around the death spot dangerous for their team for up to 25 s (`_bot.gsc bot_killstreak_dangerous_think()`).
- [I] Place on a chokepoint node facing the enemy spawn direction. Pick it back up if it has not fired for about 30 s.

### Unknowns / engine-side ([U])

- Minimap radar sweep period and shape for mode 1 vs mode 2 ("fastsweep"), and what `setenemyglobalscrambler` renders: compass code, not script.
- Dvar defaults: `scr_scorestreaks`, `scr_scorestreaks_maxstacking`, `perk_killstreakMomentumMultiplier`, `perk_nottargetedbyai_graceperiod`, `player_useRadius`.
- Vehicle defs: both are in `common_mp.ff` (read with `zonedump --vehicles`) [V]. `rc_car_medium_mp` is a "4 wheel" type with maxSpeed 20 mph (352 in/s) and accel 30 mph/s. `heli_supplydrop_mp` is a helicopter with maxSpeed 90 mph and accel 20, world model `veh_t6_drone_supply`. The RC-XD's health is still [U]: script sets vehicle health, and the export doesn't carry it.
- Hunter Killer cruise speed (engine Drone guidance).
- Sentry target-acquisition rules (engine turret code).
- Whether the engine populates `level.roundstartkillstreakdelay` from the `roundStartKillstreakDelay` gametype setting (15).
