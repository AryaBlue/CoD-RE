# T6 MP bots: where they go and how a team spreads

Sources: the decompiled t6 `maps/mp/bots/_bot.gsc`, `_bot_combat.gsc` and the per-mode `_bot_*.gsc` (gsc-tool dump on disk), plus t6mp.exe strings. [V] means read in script or the exe; [I] means inferred.

## The think loop

- [V] `bot_main` wakes every `think_interval`: easy 0.5 s, normal 0.25 s, hard 0.2 s, fu 0.1 s (`bot_spawn_init`). On each wake it runs combat_think (which runs failsafe, crouch and crate first), then patrol, lookat, killstreak, **wander**, the c4, launcher and weapon updates, the tosses, and finally the gametype think.
- [V] tdm and dm have no gametype think (`gametype_void`). Their bots only patrol and wander.
- [V] Each `update_*` timer starts 1–3 s after spawn (`randomintrange(1000, 3000)`).

## Goals

The engine keeps named goals with priorities (`addgoal(node, radius, priority, name)`) and walks to the highest one. [V] goal radius 24.

| goal | priority | set by |
|---|---|---|
| wander | 1 | `bot_update_wander` |
| enemy_patrol | 2 (periodic) / 4 (hurt, or lost sight) | `bot_patrol_near_enemy`, combat_think |
| enemy_patrol (hold) | 3 | combat_think, lost a far enemy: stands there first |
| cover / flee | — | combat (rocket threats etc.) |
| failsafe | over all [I] | `botsetfailsafenode` |

- [V] **wander**:
  - Re-picked only when the bot has none, or is within 256 of its current one (65536 = 256²).
  - The spawns (`level.spawn_all`, otherwise spawnpoints or start spawns) are sorted by distance from the bot. It picks `randomintrange(size/2, size)`, a random one in the **far half**.
  - The goal is that spawn's nearest node.
- [V] **patrol** (`bot_update_patrol`):
  - Every 5–10 s it goes to the node nearest the **closest enemy on radar** (`getnearestnode`, otherwise the first of `getnodesinradiussorted(origin, 1024, 0, 512, "Path", 8)`).
  - If that enemy is within 512 of the bot and more than 128 from the current patrol goal, the goal is dropped and the timer reset.
  - Easy bots only look; they never patrol.
- [V] **on radar** (`bot_get_enemies(1)`):
  - With a UAV or satellite up (team-based: the team's), every enemy counts.
  - Otherwise only enemies whose `lastfiretime` is within 2 s count. `lastfiretime` is set on every `weapon_fired`, silenced or not (`_weapons.gsc watchweaponusage`).
- [V] enemy_patrol is cancelled the moment the bot is at it (top of combat_think).
- [V] **hurt** (combat_idle with damage): it turns on the attacker (or the closest enemy on radar) at priority 4.
- [V] **lost sight of a player**:
  - Within 256: it goes to the target's origin at priority 4, predicting the look.
  - Further: it holds where it is (priority 3), may throw a lethal or tactical (cointoss, not easy), waits out `bot_combat_dead`, then goes to the last seen position at priority 4.

## Team spacing

- [V] **tdm has no team-mate spacing in script.** The only friend checks in the tdm path are in the failsafe: a node is invalid if a team mate stands within 32 of it.
- [V] The objective modes do spread their bots, always with `bot_friend_goal_in_radius(goal_name, origin, r)`: how many friendly bots have that named goal within r of a point. Examples:
  - ctf patrol 256, flag 16;
  - hq radio 128/64, hq patrol 256;
  - koth hill 64/128;
  - sd defend 256, defuse 16, pickup 64;
  - dom: `!bot_friend_in_radius(self.origin, 384)` before a cointoss.
- [V] t6mp.exe has no friend-spacing dvars. The bot_ dvars cover aim, reaction, ADS, crouch/sprint lookahead, strafe, grenades, melee, FOV and goal radius.
- [I] So the BO2 tdm spread comes from the far-half wander pick and the spawn influencers. Bots chasing the same shooter do converge; that's the original behaviour.

## Stuck handling

- [V] `bot_update_failsafe`:
  - Starts 7.5 s after spawn and runs every 3.5 s.
  - It acts when the bot isn't at its goal and has moved under 16 units (256 = 16²) since the last check.
  - It shuffles the nodes within 512, then takes the first valid one. Valid means: no `script_noteworthy`; at most 18 above the bot; not the bot's own nearest node; `nodesvisible` from that nearest node; no team mate within 32; and a `findpath` from it to the node nearest the closest spawn.
  - If none is valid, it takes a random node.
  - `botsetfailsafenode` for up to 4 s, and enemy_patrol is cancelled.
- [V] Mid-air or traversing: if a mantle `Begin` node is under the lookahead, it fails over to that node's target for 1 s.

## What Reforged does on top ([I], `GameProfile::MpBotGoals`)

The scripts give tdm no spacing. Reforged carries the objective modes' `bot_friend_goal_in_radius` idea over to the hunt and the wander:

- **wander friend radius** (kept, 384 and 4 draws): a far-half draw whose spawn has a team mate's wander goal, or a team mate, near it is drawn again.
- **patrol share** (built, off: 0): the periodic patrol is skipped while enough team mates already patrol near that enemy. A hurt bot still turns on its attacker.

### Measured [M]

The sim is `reforged_mp_sim_tests`: 6v6 TDM, 3 min, on mp_raid, mp_frostbite and mp_dockside, with seeds 1, 2, 3 and 5, on f6072bc. Every row has the wander also skipping a spawn a team mate stands near; each row is the total over the 12 runs.

| Step | Kills | Stuck failsafes | Samples within 128 | Nearest team mate (avg) |
|---|---|---|---|---|
| old `atgoal` axis, wander also skips a team mate's feet | 918 | 87 | 412 / 1778 (23.2%) | 536 |
| + `atgoal` on engine x/z | 953 | 63 | 355 / 1742 (20.4%) | 544 |
| + patrol share 512 / 1 | 928 | 82 | 342 / 1787 (19.1%) | 635 |

The `atgoal` fix is a clear gain: stuck failsafes 87 to 63, within-128 samples 23.2% to 20.4%.

The patrol share spreads the team further (nearest team mate +17%). But its within-128 gain is small (−1.3 points, inside the seed noise), and stuck failsafes rise to 82. Most of that rise is mp_raid seed 1 (41), at the hotspot the movement owner is fixing. So the patrol share isn't on.

## Objective modes: the gametype think

`bot_main` calls `[[level.bot_gametype]]()` last, after combat, patrol and wander [V `_bot.gsc` bot_main]. `bot_gametype_allowed` sets it to:

| Mode | Function |
|---|---|
| dm, tdm | `gametype_void` |
| ctf | `bot_ctf_think` |
| dem | `bot_dem_think` |
| dom | `bot_dom_think` |
| koth | `bot_koth_think` |
| hq | `bot_hq_think` |
| conf | `bot_conf_think` |

Any other mode returns false, so the game spawns no bots in it [V].

S&D is one of those modes: retail T6 has no bots in S&D. `_bot_sd.gsc` (`bot_sd_think`) ships in the scripts, but nothing references it [V: grep over the decompiled mp tree]. Reforged runs it anyway [I], because the alternative is S&D with no bot plan at all.

All the objective goals are named goals in the same table as the hunt goals. Their priorities are:
- 3: the mode's goals;
- 4: a must-do goal (a ctf carrier going home, retaking its own flag, a dropped bomb, a late plant, a defuse, a prone hold on a flag).

Against the hunt goals, priority 3 beats the patrol (2) and the wander (1). It ties a hurt patrol (4) only when the mode goal is itself priority 4.

`update_objective` throttles the dom, hq and ctf thinks to one every 500–1500 ms. It starts 1–3 s after the spawn, as do `update_lookat` and `update_objective_patrol` [V `_bot.gsc` bot_spawn_init].

### dom (`_bot_dom.gsc`)
- **At its `dom_flag` goal:** `bot_capture_flag` on the closest flag.
  - Not its team's flag yet: it holds where it stands (addgoal self.origin, 24, priority 3).
  - On each lookat (1.5–3 s), if any flag is taken, a coin toss with no team mate within 384 makes it go prone, and the hold becomes priority 4.
  - Its team's flag: the goal is cancelled.
- **Closest flag not its team's, within 384 (2D), and not already its goal:** it goes there.
- **Otherwise it picks a flag:**
  1. `dom_get_weighted_flag("neutral")`: the nearest at 70% odds, with a 29% chance of any.
  2. If there's none, `dom_get_best_flag`: the weighted enemy flag or the weighted contested flag (80%).
  3. If its team holds two uncontested flags, also `dom_get_best_flag`.
- **Going to a flag:** a random node within the flag radius, as goal `dom_flag` (24, priority 3).
- **Contested:** an enemy within 384 of the flag.
- **Not ported:** mp_frostbite's own node height (32) is a per-map special case, so it is skipped. Reforged uses the trigger's height for every map [I].

### hq (`_bot_hq.gsc`, radio nodes from `hq.gsc` setupnodes)
- **radio.nodes:** the nodes inside the radio trigger. `node_radius` is the distance from the centre to the corner.
- **Patrol:** when its team owns the radio and no enemy is within `node_radius`:
  - it guards a node the radio can see (`getvisiblenodes` of a random radio node);
  - the node must have no team mate's hq_radio within 128 and no hq_patrol within 256;
  - it stays 3–6 s, or until the spot no longer sees the radio.
- **Otherwise:** it goes to a random radio node that no team mate's hq_radio is within 64 of, then holds there (priority 3).

### koth / hardpoint (`_bot_koth.gsc`)
- **goal_radius:** the distance from the trigger's centre to its corner. The goal point is 8 above the ground under the zone.
- **Not yet on the hill:** it picks the nearest node within goal_radius (height 128) that has no team mate's koth_hill within 64 and that it can reach.
  - This is throttled to once per 4 s after its last pick (`update_objective + 4000`).
- **On the hill:** it holds.
  - On each lookat, if it is standing still, a coin toss moves it to another node. The node must be within goal_radius + 128, more than 32 away, have no team mate's koth_hill within 128, and be reachable.

### ctf (`_bot_ctf.gsc`)
- **Patrol (`bot_should_patrol_flag`):**
  - The carrier patrols when its own flag is away.
  - Anyone else patrols when its flag is home, the enemy flag is over 512 away, and no team mate's ctf_flag_patrol is within 1024 of home.
  - The patrol spot sees `base_nearest_node`, has no team mate's patrol within 256, and is held for 3–6 s.
- **Defend:** its own flag is away and it isn't the carrier.
  - **Dropped:** back to it (priority 4) when at most one team mate is already on it.
  - **Carried:** after it when the enemy flag isn't home, or when the bot is over 500 (2D) from the enemy's home. Otherwise it waits at the enemy's home.
- **Capture:**
  - The carrier goes home (priority 4).
  - Escorts take one of 8 nodes 64–512 from the carrier. They keep that spot while it is within 768 of the carrier.
  - The rest go for the enemy flag, at most a pair at once (≤1 team mate within 16).
- **No path to a spot (`bot_ctf_add_goal`):** a node within 384 that sees the spot, and the next think waits 3–5 s longer.
- **Respawn wait [V]:** `patch_mp` `mp/gamesettings_ctf.cfg` sets `playerrespawndelay 7.5` over the default cfg's 0, and `_globallogic_spawn.gsc` `timeuntilspawn` reads it. Reforged waits 7.5 s in t6 ctf; before this it waited its 2.5 s, so a carrier met a base refilled every few seconds. In hq, `gamesettings_hq.cfg` `playerObjectiveHeldRespawnDelay 60` with `delayPlayer 0` makes the holders wait until the radio goes (`hq.gsc` `getrespawndelay`).
- **Support [V]:** the escorts are as the script has them: nodes 64–512 from the carrier, set on each think once a team mate has the flag. In the sims they are set, but the runs start at home, 2000–3700 away, and the carrier dies 1–3 s after its grab, before they get there. There is nothing more in `_bot_ctf.gsc` to port.

### sd (`_bot_sd.gsc`, unused by retail as above)
- **Once planted, both teams defend the planted site:**
  - they pick visible nodes of the site's nearest node, scored 10000 − 2D distance + height;
  - a defender within 1000 (2D) goes to defuse (priority 4) when no team mate is already on the bomb.
- **Attackers:**
  - **The bomb at its start:** one attacker fetches it (no team mate's sd_pickup within 64).
  - **A dropped bomb:** every attacker goes for it (priority 4).
  - **The carrier:** every 2.5–5 s it plants with odds equal to the round fraction gone. Once 85% of the round is gone it always plants, at priority 4.
    - The plant spot is 32 ahead of or behind the bomb spot, or 48 to either side: the first one it can reach.
  - **Other attackers:** 30% guard the carrier, at a node within 256 of its plant spot.
- **Defenders before the plant:** a random site each think. They take the highest visible node of it that:
  - is at least 256 away from the bot;
  - has no team mate's sd_defend within 256.
  - They leave it on a coin toss every 2.5–5 s, or when their hunt patrol is within 512 of the closest site.
- **Plant and defuse:** within 48 of the spot it presses use for the plant or defuse time plus 1 s. The `wait` blocks bot_main, so it does nothing else meanwhile. The goal is then cancelled whether or not the plant or defuse took.

### What Reforged infers
- **`getvisiblenodes` [I]:** the engine's node visibility wasn't read, so Reforged uses a sight line at eye height within 2048, cached per node.
- **`findpath` [I]:** taken as both ends' nearest nodes being in one piece of the graph.
- **canclaimnode [I]:** no team mate's guard goal within 8.
- **sd [I]:**
  - The bomb model's spot is the site trigger's middle, and map x is its forward.
  - Plant spots are clamped inside the trigger so the plant takes.
  - The script's `!isplayer(carrier)` is true of no one, since bots are players too. As written, then, the carrier guard never runs; Reforged takes the evident meaning, a bot carrier.
- **Ctf escorts [I]:** `maxresults` 8 is read as the nearest 8.
- **The same goal added again [I]:** the scripts re-add their goals every think. When the name, priority and spot are all unchanged, Reforged keeps the bot's route. Starting a fresh route each time sent the bot back to its nearest node every think, and it circled.
- **Reachability [I]:** every goal pick (wander, patrol and each mode's nodes) skips nodes outside the bot's own piece of the nav graph. One example is the 8-node pocket on mp_raid that the glass cut seals off. `refreshNavGroups()` recomputes the pieces when links reopen.
- **Spawns:** a point that would telefrag is passed over [V `_spawnlogic.gsc` `getspawnpoint_final` / `getbestweightedspawnpoint`]. "Would telefrag" means a live body's hull within 32 flat and 72 up [I]. A point someone spawned on in the last second is passed over too [I].
- **hq and hardpoint between zones [I]:** their goals go, since there's nothing to go to.
- **Not modelled:** stances (prone, crouch, and the dive to prone), lookats, and the mode grenades, smoke and tactical insertions.
- **Removed:** Reforged's earlier objective plans, all marked [I] and from no script:
  - the sd/ctf roles and the hq/dom picks;
  - the ctf carrier that wouldn't fight;
  - the objective-mode bypasses of cover, melee, press and the lost-sight hunt;
  - the 2 s stuck repath.
  The objective modes now run the same combat, patrol, wander and failsafe as TDM, as bot_main does.
