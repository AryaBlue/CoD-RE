# BO1 Combat Training bots: how the brain works

How BO1 bots pick targets, move, aim, shoot and throw grenades. This is the reference for Reforged's offline MP bots
(M4).

The split is the one in [mp_t4_tdm_ffa.md](../../../t4-waw/notes/e115/mp_t4_tdm_ffa.md) §7:
- **Script** (`maps/mp/gametypes/_bot.gsc`) decides *what*: loadouts, goals for revives/crates/equipment, team help.
- **The engine** (`BlackOpsMP.exe`) decides *how*: the target, aim, firing, strafing, sprinting and grenades.

The per-difficulty dvar table is in that doc and isn't repeated here. This doc adds what the engine does with those
dvars.

Tags:
- **[V]**: script line, or VA in `BlackOpsMP.exe` (static read of the disassembly).
- **[M]**: measured in game. None yet.
- **[I]**: inferred, usually what a struct field means.

## 1. Spawning and setup [V] (`_bot.gsc`)

- **When bots exist:**
  - offline TDM/DM: `splitscreen_bot*` dvars
  - online: `xblive_basictraining` with `bot_friends`/`bot_enemies`/`bot_difficulty` (`init` `:4-173`)
- **Count:**
  - TDM: friendly bots = `bot_friends` − humans; enemy bots = `bot_enemies` − max(0, humans − `bot_friends`)
  - DM: `bot_enemies` − humans + 1
  - One bot is added every 0.25 s (`AddTestClient`).
- **Equipment:** per team, a random pick from {0,1,1,2,2,2,2,3,3,4} sets how many bots may use equipment.
- **Spawn:** each life, the bot answers the class menu with `smg_mp` (`bot_spawn_think` `:282-305`). `_class.gsc:1759`
  then calls `bot_give_loadout`: a random rank-legal weapon, attachment, perks and killstreaks (`:529-1200`).
- **Engine dvar defaults when the script doesn't set them** (`0x44efc0-0x44f53a`, registered as default / min-max):

  | dvar | default | range | role |
  |---|---|---|---|
  | `sv_botFov` | 65 | 1-160 | full view cone, degrees |
  | `sv_botGoalRadius` | 128 | 0-4096 | used when a script goal has radius 0 |
  | `sv_botCloseDistance` | 256 | 0-4096 | "close" threat range (§3, §4, §6) |
  | `sv_botSprintDistance` | 512 | 1-4096 | |
  | `sv_botCrouchDistance` | 32 | 1-4096 | |
  | `sv_botMeleeDist` | 80 | 0-256 | |
  | `sv_botTargetLeadBias` | 4 | 0-25 | int |
  | `sv_botYawSpeed` / `Ads` | 4 / 5 | 0-100 | |
  | `sv_botPitchSpeed` / `Ads` | 2 / 5 | 0-100 | **never set by script** |
  | `sv_botPitchUp` / `Down` | −10 / 20 | ±90 | |
  | `sv_botMin`/`MaxPitchTime` | 500 / 1000 ms | 0-10000 | **never set by script** |
  | `sv_botStrafeChance` | 0.1 | 0-1 | |

## 2. The frame [V] (`0x4dffc7-0x4e0111`, once per bot per server frame, 50 ms)

1. **View cone.** It caches cos(`sv_botFov` / 2) in `0x367cdcc`, recomputed only when the dvar changes. Normal's 70
   gives ±35°.
2. **The pipeline:**
   - `0x871f30` melee
   - `0x871ba0` threat list + choice (§3)
   - `0x871550` sight of the current threat
   - `0x874440` goal / path
   - `0x874a70`
   - `0x874520`
   - `0x874600`

   The aim (`0x8722e0` yaw, `0x8721e0` pitch) and fire (`0x874b30`) steps run inside the move build (`0x874e40`).
   [I] for which unnamed callee is which, beyond the ones read below.

## 3. Target choice [V] (`0x871ba0` → `0x871970`)

**Candidate list.** Up to **32** candidates, `0x38` bytes each: entity, view dot, distance², last re-check time.
- Dead targets, and ones unseen for over 10 s (`0x2710` checks at `0x871c77`), are dropped [I: the exact list rules].
- A candidate is "engageable" only within the bot's weapon range: dist² < weapon `+0x7ac`² (`0x871470`). [I] It's a
  weapon range field.

**Can-see test** (`0x871810`/`0x871280`):
- **The cone:** dot(view forward, direction to target) ≥ cos(fov/2). **Within 55 units the cone is fixed at dot ≥ 0.7**
  (±45.6°).
- **The trace:** a sight trace from the bot's eye to the target's eye (mask `0x2818011`). The eye is origin + view
  height; stance-aware via `0x4b1b80`.

**No current threat:** take the first candidate that passes the can-see test.

**Has a threat:** for each other candidate:
- **Within `sv_botCloseDistance`**, it switches **at once** if the candidate is seen.
- **Otherwise**, each candidate is re-checked at most every **500 ms**. If it's seen:

  | the candidate is | switch chance |
  |---|---|
  | closer **and** more centred in view | 100 % |
  | (the current threat flag `+0x5a550` is clear [I: e.g. not a player]) | 75 % |
  | closer | 50 % |
  | more centred | 50 % |
  | neither | no switch; it stamps the time |

On a switch the bot copies the record and sets "new threat" (flag `0x1`), with the acquire time at `+0x3f4`.

**Keeping track** (`0x871550`):
- Each frame it re-traces to the current threat (mask `0x2818001`). A threat at dist < 55 that falls outside the 0.7
  cone, or outside fov elsewhere, is dropped.
- **"Newly visible"** sets flag `0x20`. That flag starts the reaction timer (§5).
- **Last seen** (`+0x3f8`) is updated while the threat is visible.
- For 1 s after losing sight, the last-known position is kept at `+0x408`, and a second sample at `+0x414` is kept
  after 100 ms.
- **"Recently seen"** = not visible now, but seen within **5 s** (`0x871520`). This drives the hidden-enemy grenade
  (§6).
- [I] When a target dies, the bot holds on it for rand(`MinDeathTime`, `MaxDeathTime`) (`0x871d00`) before moving on.

## 4. Movement [V] (script goals; engine pathing)

**Goals:**
- Script sets them with `SetScriptGoal(pos, radius)` / `ClearScriptGoal`. Radius 0 means `sv_botGoalRadius` (128).
- The engine paths over the map's path nodes (`0x870dc0`/`0x871060`).
- Within the radius it notifies `goal`. When it can't path it notifies `bad_path` (`0x872ec0-0x872fe2`).
- [I] With no script goal the engine picks its own roaming destination (`0x874e40` draws a random value); the
  destination rule wasn't read.

**What the script uses goals for** (all with `waittill_any("goal", "bad_path")`):
- **Help:** a damaged bot calls `bot_cry_for_help` (`:1305-1369`), at most once a second.
  - Each living teammate bot within `scr_help_dist` has a 50 % chance to respond.
  - A responder sets a goal 128 units towards the attacker for 1 s.
  - The loop stops early with a 30 % chance after each responder.
- **Revive:** every 3-5 s it looks for a downed teammate within 2048 that has no other bot coming. It walks there
  (radius 32) and holds use for `revive_time_taken` + 1 (`:1403-1480`).
- **Crates, turrets, equipment and killstreaks:** `:1482-2780`.
  - Equipment is placed only when the bot is idle (no goal, no threat), not sprinting, and the path ahead is ≤ 64
    straight (≥ 384 for the camera spike), every 1-3 s.

**Strafing** (`0x872c90`). Only while the threat is **visible and in weapon range**:
- **When:** on a new sighting, or when the strafe timer runs out.
- **Decision:** with probability `sv_botStrafeChance`, pick a strafe direction (`0x870cd0`, flag `0x40`); otherwise
  stop strafing. The next decision comes after rand(`MinStrafeTime`, `MaxStrafeTime`).
- **While strafing,** each frame it traces the bot's box along the move (mask `0x2820011`). If it's blocked or hits a
  drop, it picks a new direction.

**Sprint** (`0x873ff4-0x874031`). It presses sprint when all of these hold:
- the yaw error is < 50° (flag `0x10`, §5)
- the remaining path is ≥ `sv_botSprintDistance`
- the sprint cooldown (`+0x440`) has passed

**Crouch / ADS / melee:** use `CrouchDistance`, `Min/MaxCrouchTime`, `Min/MaxAdsTime` and `MeleeDist`
(`0x873c90`, `0x871f30`). [I] Their exact rules weren't read: crouch/ADS hold for a random time in range; melee is
within `MeleeDist`.

## 5. Aim and fire [V]

**Yaw** (`0x8722e0`). err = AngleDelta(target yaw, current yaw), from −180 to 180; s = `YawSpeed` (or `YawSpeedAds`).

| \|err\| | rate |
|---|---|
| < 100° | s × (1 + \|err\|/180) |
| ≥ 100° | s × (1 − \|err\|/180), minimum 1 |

- **The step:** `DiffTrackAngle` (`0x69b240`): new = cur + err × rate × **0.05**, and it snaps if that overshoots or
  \|err\| < 0.001.
- **So each 50 ms frame closes `rate × 5 %` of the error.** It's exponential, and slow when the target is behind.
  - Normal, 30° off: about 23 % per frame.
  - fu (s 14): about 82 %.
- **\|err\| ≥ 50°** sets flag `0x10`, which blocks sprint (§4) [I: probably fire too].

**Pitch** (`0x8721e0`): the same, with `PitchSpeed`/`PitchSpeedAds`, but always rate = s × (1 + \|err\|/180) (no ≥ 100°
branch). [I] `PitchUp`/`PitchDown` clamp the aim pitch.

**Lead** (`0x872430`). The aim point is the target trajectory evaluated at **level.time + `TargetLeadBias` × 50 ms**
(`BG_EvaluateTrajectory` `0x594c60`, base = target origin, delta = velocity):
- normal 4 → 200 ms
- easy 8 → 400 ms
- hard/fu 2 → 100 ms

[I] So a higher bias over-leads, which is a deliberate error that makes the bot worse.

**Fire** (`0x874b30`):
- **Reaction.** On a new sighting (flag `0x20`), if the threat is beyond `sv_botCloseDistance` (256), the bot can't fire
  until rand(`MinReactionTime`, `MaxReactionTime`) ms have passed. **Within 256 there's no reaction delay.**
- **The trigger.** It needs the weapon ready (`0x459680`). For any fire type except full-auto (type 0) and type 6, it
  also waits for the next-fire time (`+0x43c`).
  - On each press, next-fire = now + rand(`MinFireTime`, `MaxFireTime`).
  - **So Min/MaxFireTime is the gap between semi-auto trigger pulls.** Full-autos just hold the trigger.
- Bolt-action/charge weapons get an extra hold: the weapon's `+0x478` time + 500 ms (`0x874c62-0x874cb2`) [I: fire
  time].

## 6. Grenades [V] (`0x8727d0`; needs `sv_botAllowGrenades`, and the offhand idle)

**Preconditions:**
- a live, non-special (`0x870af0`) threat in the view cone
- no grenade check until `+0x444`

Then:

| situation | throw chance per check |
|---|---|
| **threat hidden but seen in the last 5 s**, and hidden for longer than rand(`MinGrenadeTime`, `MaxGrenadeTime`) | **75 %**; otherwise retry in 2 s |
| threat visible but **out of weapon range** | 25 % |
| visible, bot is ADS, has ammo | 0.5 % |
| visible, bot is ADS, out of clip | 1 % |
| out of ammo | 25 %, then retry in 2 s |

- **No grenades at threats within `sv_botCloseDistance`**, unless the bot is out of ammo.
- [I] The aim and arc of the throw weren't traced.

## For one Reforged ruleset [I: design pick]

- **One bot brain, built on BO1's model, for every era's maps.** WaW never had bots (§5 of the MP doc), so there's
  nothing to reconcile.
- **Use the four BO1 difficulty presets as data**, with the engine defaults above for the unset fields.
- **Rebuild the core loop as above:**
  - a candidate list with the cone + sight test
  - the 500 ms re-check with the switch odds
  - reaction delay only beyond 256
  - exponential yaw/pitch tracking at a 20 Hz tick
  - lead by bias × 50 ms
  - fire-time gaps for semi-autos
  - the strafe-chance timer
  - the hidden-enemy grenade
- **Run the brain at a fixed 20 Hz** even if the sim runs faster, so the tuning numbers mean the same thing.
- **Goals:** our Detour navmesh replaces path nodes. Keep the `goal`/`bad_path` events and the script-level jobs (help,
  revive, objectives) as game-mode code.

## Open

- [I] The engine roam-destination rule when a bot has no script goal (`0x874e40`).
- [I] Crouch, ADS and melee timing (`0x873c90`, `0x871f30`).
- [I] The grenade aim.
- [I] The meaning of fire type 6, and of weapon `+0x7ac`/`+0x478`.
- [M] All of it in game.
