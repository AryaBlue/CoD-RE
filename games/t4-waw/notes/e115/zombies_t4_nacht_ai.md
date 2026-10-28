# Zombies: T4 Nacht AI, combat and player movement

How a Nacht zombie behaves from spawn to kill, how hits work in both directions, player health and regen, and the T4 SP
movement constants. This is the companion to `zombies_t4_nacht.md` (rules) and `zombies_t4_nacht_flow.md` (HUD and
flow).

Tags:
- **[V]**: read in the source, with a file:line or an exe address.
- **[I]**: inferred. Treat as a guess until checked in game.

Sources:
- **Scripts:**
  - Nacht's `maps/_zombiemode*.gsc`.
  - From `common.ff`: `animscripts/*.gsc`, `maps/_gameskill.gsc`, `maps/_load.gsc`.
- **Weapon files:** the `weapons/*` assets in `nazi_zombie_prototype.ff`.
- **Exe:** Plutonium `t4sp.exe`, static read only.
  - Dvar defaults are read at their registration calls. Floats are registered by `0x5eef10`: the default is in `xmm0`,
    the min at `[esp]`, the max at `[esp+4]`. Ints by `0x5eeea0` with the default in `eax`. Bools by `0x5eee20` with the
    default in `al`.

Script paths are rawfile names. No script text is copied here.

## 1. Zombie lifecycle [V]

### Spawn

`zombie_spawn_init` (`maps/_zombiemode_spawner.gsc:52-115`):
- Combat setup:
  - `ignoreall` is on until the zombie is inside.
  - Only the stand stance is allowed.
  - No pain, no arrivals or exits, no grenade or badplace awareness.
- Movement setup: the zombie pushes players aside (`PushPlayer`). Its health is `level.zombie_health`.
- Threads started: think, gib-on-damage and eye glow. The death function is `zombie_death_animscript`.
- The run anim is set by `set_run_speed` (walk, run or sprint; see the rules doc).

### Pick a window

`zombie_think` (`:212-288`):
- Takes the 3 `exterior_goal`s closest to the spawner's target, or to the spawner itself if it has none.
- Drops any that are more than 500 units further than the one before, then picks one at random.
- A spawner with `script_forcegoal` takes the single closest goal to its target.
- `zombie_assure_node` (`:344-374`): if the zombie gets `bad_path` within 2 s, it retargets the next goal. If none works,
  it dies after 3 s.

### Walk to it

`zombie_goto_entrance` (`:313-342`): goalradius 128 on the goal's origin, then wait for `goal`.

### Tear boards

`tear_into_building` (`:415-478`):
1. Stop when the goal is `no_blocker`, has no target, or all its chunks are destroyed.
2. Claim a random free attack spot of the window. There are 3, built in `_zombiemode_blockers.gsc:423-444`. If none is
   free, wait 0.5 s and retry.
3. Go to the spot with goalradius 4, facing the window's angles, and wait for `orientdone`.
4. Loop: pick the **closest standing chunk** to the zombie and play a tear anim with `AnimScripted`. The chunk is
   removed on the anim's `board` notetrack (`:528-553`), which runs `remove_chunk` and three wood-splinter FX. The loop
   repeats until no chunks are left.

So the tear rate is **one board per tear anim**. Several zombies on one window tear in parallel, one each.

Tear anims (`get_tear_anim`, `:555-587`). The pick depends on how high the chunk sits above the zombie's feet:

| chunk height | anim |
|---|---|
| more than 70 | `ai_zombie_door_tear_high` |
| less than 40 | `ai_zombie_door_tear_low` |
| otherwise | `ai_zombie_door_tear_left` / `_right`, at random |
| crawler (any height) | `ai_zombie_attack_crawl` / `_crawl_lunge` |

The anim lengths and `board` notetrack times are in the xanims, which I haven't read (see "Open items").

### Climb in

There is no climb code in the zombie script. Once the boards are gone:
- the window clip runs `ConnectPaths`
- the zombie gets `zombie_setup_attack_properties` (`:1273-1290`): `ignoreall` off, `pathEnemyFightDist` 64,
  `meleeAttackDist` 64

It then paths through the window over a **traversal (negotiation) node pair**. All 12 Nacht windows use
`"animscript" "wall_hop"` (ents). `animscripts/traverse/wall_hop.gsc:8-55`:
- zombies with legs play `ai_zombie_traverse_v1` or `_v2`, 50/50
- crawlers play `ai_zombie_traverse_crawl_v1`

`advancedTraverse` (`traverse/shared.gsc:6-60`):
1. Turns off gravity and clip and faces the start node's yaw.
2. Teleports by (node `traverse_height` − 39.875) so the anim lines up with the wall.
3. Plays the anim at rate 1.
4. Turns gravity back on at the `gravity on` notetrack, or after a fixed 1.03 s if the anim has none.

### Chase

`find_flesh` (`:1292-1345`), goalradius 32:
1. Target = the closest valid player (`get_closest_valid_player`). Solo never ignores the player.
2. `zombie_follow_enemy` (`:1456-1474`) re-sets the goal to the player's origin **every 0.1 s**.
3. The target is re-chosen every 1-3 s (random each time).
4. On `bad_path`, the zombie falls back to the breadcrumbs. The shipped game uses the **patch.ff fork**, which differs
   from the zone scripts (see the rules doc, "patch.ff overrides").

   **Crumbs** (patch `maps/_zombiemode_prototype.gsc:1919-2001`):
   - When does a player drop a set? On the ground, whenever they've moved ≥24 units since the last set, and again on
     landing after being airborne.
   - It is checked every 0.1 s on the ground and every 0.05 s in the air.
   - **Each set replaces the old one.** It is 24 points around the player's position: 3 rings at 16, 32 and 48 units,
     each ring 4 points (±x, ±y), each at the feet and at +32.

   **Fallback** (patch `maps/_zombiemode_spawner_prototype.gsc:1377-1477`):
   1. Pick a crumb: the first not-yet-failed one in list order, or a random one with a 20% chance.
   2. Set the goal on it and add 1 s to the re-target timer.
   3. On `bad_path`, mark that crumb as failed and pick again.
   4. When all crumbs have failed, the goal becomes the player's `spectator_respawn` point.
   5. If the zombie is already inside its goal, it calls `Melee()`.
   6. If the player stops being valid, the timer resets to 0 so the zombie re-targets at once.

   The zone version's "ignore this player" and "go back to the window" branches are gone.

### Attack

`animscripts/melee.gsc`:
- **Range.** Zombies skip the charge (`PrepareToMelee` returns true at once, `:404-407`) and melee whenever the engine's
  combat code lets them, at `meleeAttackDist` 64. `anim.meleeRange` is also 64 (`animscripts/init.gsc:1562`).
- **Facing.** The zombie turns to face the enemy (`:95-101`).
- **Vocal.** It plays the `attack_vocals` line.
- **Anim.** One of 4 `level._zombie_melee` anims (crawlers have their own), picked by `pick_zombie_melee_anim`
  (`:627-660`).
- **Hit.** The hit is the engine's `melee()` at each `fire` notetrack (`:126-150`). One anim can hit more than once if it
  has several `fire` notes.
- **Next swing.** After `stop`, the zombie swings again if it is still in range (`CanContinueToMelee`).
- **Attack rate** = the melee anim length. I haven't read the anim lengths (see "Open items").

### Failsafe and death

- **Failsafe:** see the rules doc (every 30 s; less than 24 units moved means killed).
- **Death:** see section 3.

## 2. Zombie melee damage on the player

What sets the hit's size:
- **The engine's AI melee trace** uses `ai_meleeRange` 64, `ai_meleeWidth` 20 and `ai_meleeHeight` 10. They are
  registered at `t4sp 0x500ab6-0x500b50` [V]. Each is clamped to 0-1000, and they are read by the actor melee trace at
  `0x4c0318-0x4c034e`.
- **The zombie aitype's weapon** is `kar98k` (`aitype/axis_zombie_ger_ber_sshonor.gsc:17`). Its weapon file has
  meleeDamage **150** [V].
- **`player_meleeDamageMultiplier`.** The engine default is 1.0 (`t4sp 0x4ff921`, range 0-1000) [V]. `setSkill` sets it
  to **100/250 = 0.4** (`maps/_gameskill.gsc:428`) [V].
- **`player_damageMultiplier`** is set to 100 / (playerDifficultyHealth × co-op scalar) (`_gameskill.gsc:539`) [V].

So a zombie hit is **150 × 0.4 = 60** [V]. The player damage function (`t4sp 0x4f5d70`, `0x4f5e6b-0x4f5ea8`) applies
only the melee multiplier to melee, and `player_damageMultiplier` only to non-melee, non-radius damage. Details are in
`nacht_weapons_economy.md` §4.

The zombie AI never uses the `zombie_melee` weapon file (meleeDamage 50, meleeTime 0.7). That weapon is only given to a
*player* turned into a zombie, a mode that is off in Nacht (`_zombiemode.gsc:1363`).

## 3. Hits on zombies [V]

### Bullet damage

The engine does this from the weapon file: `damage` up to `maxDamageRange`, falling linearly to `minDamage` at
`minDamageRange`. The hit-location multipliers are also per weapon:

| weapon | damage → min | range | head / neck | torso upper / lower | arm/leg (upper) |
|---|---|---|---|---|---|
| zombie_colt | 20 → 20 | 425 → 1000 | 3.5 / 3.5 | 1.25 / 1.1 | 0.85 |
| kar98k | 100 → 80 | 1200 → 2200 | 3.5 / 3.5 | 1.8 / 1.7 | 1 |
| thompson | 120 → 80 | 800 → 1800 | 4 / – | 1 / – | – |

The full data is in weapons.json, below. The linear falloff is the standard CoD4-line rule
[I].

The full per-weapon data (all 44 Nacht WeaponDefs) is in our zonedump's `weapons.json` (`e115_zonedump --weapons`, at
`assets/local/reforged/t4/nazi_zombie_prototype/weapons.json`).

### Script extras on every hit

`zombie_damage` (`maps/_zombiemode_spawner.gsc:1152-1195`) is called from the damage callback:
- **Points:** 10 per hit, or 10 from `damage_ads` (rules doc).
- **Grenades:** extra `round + randomint(100, 500)` damage.
- **Projectiles/explosives:** extra `round × randomint(100, 500)`.
- **Fire:** sets the zombie burning (`damage_on_fire`, `:1114-1150`): a % of zombie health every 2-5 s.
- **Insta-kill:** if it's active, the zombie is head-gibbed and given health + 666 (`_zombiemode_powerups.gsc:452-459`).

### Knife

The colt's meleeDamage is 150, so the knife one-shots round-1 zombies. The kill pays 130 (rules doc).

### Gibs

Gibs are cheap: an attach or model swap plus an anim set. `zombie_gib_on_damage` (`:757-918`):

1. **Does this hit gib at all?** (`zombie_should_gib`, `:920-984`)
   - Never from melee, fire, falls or similar damage types.
   - Never from player pistols or with no weapon.
   - The hit must take at least 10% of the zombie's health as it was before the hit.
2. **Head gib** (`head_should_gib`, `:648-725`). Needs all of:
   - a player attacker
   - the zombie at ≤10% health
   - a rifle or pistol bullet, or a shotgun (spread)
   - a head, helmet or neck hit
   - a weapon that isn't a pistol or the flamethrower
   - not the German build

   Grenade airbursts within 55 units of `j_head`, or projectiles within 10, also count.

   **Effect** (`:589-616`): the head model is swapped for `char_ger_honorgd_zomb_behead`, with blood FX and the
   `zombie_head_gib` sound. The eye glow stops. **The zombie keeps walking, losing 20% of its current health every 1 s
   until it dies** (`damage_over_time`, `:618-646`).
3. **Limb gib**, otherwise. The zombie must not be gibbed already and the hit must not be to the head. The location picks
   from a list:

   | location | possible gibs |
   |---|---|
   | torso | guts, right arm |
   | arm | that arm |
   | leg | that leg ×3 or no_legs ×1 — only if the hit kills |
   | other | any of the above |

   For grenades and projectiles, the closest gib tag decides.

   If a leg is lost while the zombie is still alive:
   - it becomes a **crawler**: `has_legs` false, crouch stance only
   - one of 3 crawl run cycles and its matching crawl death anim

   It then tears and traverses with the crawler anims.

### Death

`zombie_death_animscript` (`:1091-1112`):
- Frees the attack spot, pays the kill points, rolls the power-up drop, and starts flame FX if the zombie burned.
- Returns false, so the normal `animscripts/death.gsc` path runs.
- A no-legs gib uses `ai_gib_bothlegs_gib`.

The death is **an anim, then ragdoll**:
- The death anim plays (`death.gsc:84-110` and `:305-330`).
- **Ragdoll** starts at the anim's `start_ragdoll` notetrack. If it has none, it starts at **35% of the anim's length**
  (`waitForRagdoll`, `:220-240`).
- Some paths skip the anim and launch the ragdoll straight away, with force 60 × scale along the damage direction plus
  0.2 up, halved for head hits (`:2293-2330`).

## 4. Player health and regen [V]

There is no zombie-specific player health. Nacht uses SP's `_gameskill` (started from `_load.gsc:318`, and regen at
`:797`):
- **Max health:** 100 (`intermission` also sets 100).
- **Damage scale:** taken damage is scaled by `player_damageMultiplier` = 100 / playerDifficultyHealth (see section 2).

### Difficulty values

Easy and Normal *blend* the values at a fraction of 0.25 or 0.75 (`_gameskill.gsc:402-416`). Hardened and Veteran use
fixed values.

| setting | Normal (frac 0.75) | Hardened | Veteran | source |
|---|---|---|---|---|
| playerDifficultyHealth | 310 → ×0.32 | 165 | 115 | `:177-183` |
| regen delay (`playerHealth_RegularRegenDelay`) | 2400 ms | 1200 | 1200 | `:280-287` |
| very-hurt cutoff (`healthOverlayCutoff`) | 0.2 | 0.3 | 0.5 | `:158-163` |
| long regen time | 5000 ms | 5000 | 5000 | `:149-156` |
| `player_deathInvulnerableTime` | 1700 ms | 600 | 100 | `:136-140` |
| invul pre-shield / on-shield / post-shield | 0.35 / 0.5 / 0.3 s | 0.1 / 0.1 / 0.1 | 0 / 0.05 / 0 | `:256-278` |

Which `g_gameskill` the Zombies menu launches with I haven't checked [I]. Normal is the likely default.

### Regen

The regen loop is `playerHealthRegen` (`:1201-1434`) and ticks every 0.05 s:
- **Lightly hurt** (health ratio above the cutoff): once `RegularRegenDelay` has passed since the last hit, health jumps
  **straight to full**.
- **Very hurt** (at or below the cutoff):
  - the red overlay flashes and the screen blurs
  - after the regen delay *and* `longRegenTime` (5 s), health climbs 0.1 × max per tick, so full in about 0.5 s
- **Lethal hit cushion:** if a hit leaves 1 health or less, health is set to 2/max and an invulnerability window opens.
- **Invulnerability windows:** `playerInvul` gives a short window after "worthy" hits, which drop at least
  `worthyDamageRatio` (0.1). The length depends on the state: pre-shield, on-shield or post-shield.
- **Down rules:** going down is game over in solo (rules doc).

## 5. Player movement (T4 SP) [V]

All values are dvar defaults read at registration in `t4sp.exe`.

| dvar / constant | default | range | address |
|---|---|---|---|
| `g_speed` | 190 | int | `0x4ffa48` |
| `g_gravity` | 800 | 0-FLT_MAX | `0x4ffa5d` |
| `jump_height` | 39 | 0-1000 | `0x40bc66` |
| `jump_stepSize` | 18 | 0-64 | `0x40bc95` |
| `jump_slowdownEnable` | **false** | bool | `0x40bcd4` |
| `friction` | 5.5 | 0-100 | `0x40e36d` |
| `stopspeed` | 100 | 0-1000 | `0x40e3a3` |
| `player_strafeSpeedScale` | 0.8 | 0-20 | `0x40eba4` |
| `player_backSpeedScale` | 0.7 | 0-20 | `0x40ebda` |
| `player_sprintSpeedScale` | **1.5** | 0-5 | `0x40ec9d` |
| `player_sprintTime` | 4 s | 0-12.8 | `0x40ecee` |
| `player_sprintMinTime` | 1 s | 0-12.8 | `0x40ed24` |
| `player_sprintRechargePause` | 0 | 0-9000 | `0x40ed5a` |
| `player_sprintUnlimited` | false | bool | `0x40ecdc` |
| `player_sprintStrafeSpeedScale` | 0.667 | 0-5000 | `0x40ed8b` |
| `player_sprintForwardMinimum` | 105 | int 0-255 | `0x40ec88` |
| crouch speed scale | 0.65 | const `0x8af834` | stance scale fn `0x413040-0x413112` |
| prone speed scale | 0.15 | const `0x83c778` | same |
| `bg_fallDamageMinHeight` / `MaxHeight` | 200 / 350 | | `0x40e27c` / `0x40e2b2` |
| `player_meleeRange` / `Width` / `Height` | 64 / 10 / 10 | | `0x40f554` / `0x40f58a` / `0x40f5c0` |

Notes:
- **T4 has sprint.** It lasts 4 s at ×1.5 and needs a forward stick input of at least 105/127 [I on the stick scale]. The
  recharge rule is engine code and I haven't read it [I].
- **Stance scale.** The function at `0x413040` returns 1.0 standing, 0.65 crouched and 0.15 prone. While the stance is
  changing it blends between them by time (the branches at `0x41304f` and `0x4130a2`).
- **Weapon scales.** Each weapon also scales speed with `moveSpeedScale`, and with `adsMoveSpeedScale` while aiming down
  sights. The colt's are 1.0 / 1.5.
- **Slowdown.** `jump_slowdownEnable` defaults to false, unlike CoD4 MP. T4 SP has no jump-landing slowdown unless
  something sets it.

### Sprint meter (`0x412550`, `0x412ea0-0x412f37`) [V for the formula, I for the field names]

**Max sprint time** (ms) = weapon field `+0x50c` × `player_sprintTime` × 1000 (`0x412569-0x41258f`).
- [I] The weapon field is probably the weapon's sprint-duration scale.
- With a perk bit set, it is also multiplied by a perk dvar (`0x41259e`).

**Sprint left:**
- **Unlimited, or never sprinted:** the max.
- **While sprinting:** the time left at the start, minus the time since the start.
- **After sprinting:** it refills at **1 ms per ms**, clamped to 0..max. The formula is left + start + now − 2·end. If a
  recharge-pause flag is set, `player_sprintRechargePause` × 1000 is also subtracted. That dvar's default is 0, so there
  is no pause.

`player_sprintMinTime` (1 s) is read at `0x4135e3`. [I] It is the minimum meter needed to start a sprint.

### Move speed scale (`PM_CmdScale`, `0x413cd0-0x413eef`) [V for the order, I for the flag names]

The scale is one product of these factors:
1. **Input:** `ps.speed` (`g_speed`, `+0x78`) × max(|forward|, |right|) / (127 × |input|). Backward input is first
   × `player_backSpeedScale` and sideways input × `player_strafeSpeedScale`.
2. **×0.4** if `pm_flags & 0x40` (walk/slow-move [I]), or `ps+0x74` is non-zero, or a prone-related check at
   `0x413ce3` is true.
3. **×`player_sprintSpeedScale`** (1.5) if `pm_flags & 0x8000` (sprinting) and `viewHeightTarget` is 60, i.e.
   standing (`0x413def-0x413e0e`).
4. **pm_type 2 / 3:** ×3 / ×6 (noclip / ufo [I]).
5. **Stance scale** from `0x413030`: 1 / 0.65 / 0.15.
6. **Water slowdown:** × (1 − n × 0.25) when `ps+0x944` = n ≥ 1. The constants are 1/3 at `0x8af5b0` and 0.75 at
   `0x83da80`. `ps+0x944` is waterlevel (see `t4_pmove.md` §0).
7. **Weapon:** one of two weapon fields, chosen by the same walk/ADS state as factor 2 (`0x413e8b-0x413eb8`). `+0x504`
   is [I] `adsMoveSpeedScale`, used while aiming. `+0x508` is [I] `moveSpeedScale`, used otherwise. Each applies only
   when it is > 0.
8. **×0.4 again** if `pm_flags & 0x10000` and a per-client bool is set.
9. **Script scale:** × `ps+0x8a4`, the script move-speed scale.

All factors multiply, so ADS and the weapon scale never add. For the port, the useful cases:

| state | speed (units/s) |
|---|---|
| standing run, colt | 190 × 1 = 190 |
| sprint | 285 |
| crouch | ≈124 |
| prone | ≈29 |

## 6. Pathnodes under debris (script_brushmodels)

**Question:** are the nodes under the closed stair debris (`*17`) disabled by the load-time floor drop?
**Answer:** no. Keep them. They are path-*disconnected* while the debris stands, not disabled, and buying the debris
reconnects them.

- **The drop trace is world-only [V].** The drop (`t4sp 0x559470`) calls the trace wrapper `0x5abdc0` with argument 8
  (`[ebp+0x24]`) = 0. Both of its traces push five zero arguments: at `0x559489-0x559491` and `0x5595e5-0x5595ed`.
  - The wrapper first runs the world trace `0x58cb70`.
  - It runs the entity clip `0x5932a0` only when that argument is non-zero (`0x5abe8b` / `0x5abed7`). So the entity
    clip is skipped.
- **So debris can't affect the drop [I].** Brush submodels like `*17` and `*49` are separate cmodels, reached only
  through entity clipping, so they can't block the drop or the standing-box check. Spawn order doesn't matter either.
- **While the debris stands [V for the load-time loop; I that `spawnflags 1` sets the `0x100`/`0x200` flags].** Both debris clips are `script_brushmodel`s with `spawnflags 1`, the
  DYNAMICPATH flag (ents: `upstairs_blocker` `*17` at 170 103 239, `upstairs_blocker2` `*49`). The engine runs
  `DisconnectPaths` for that flag at spawn, which cuts the links through the brush.
- **Disconnect rule** (`DisconnectPaths` → `t4sp 0x55d900`) [V]:
  - **Who may call it.** The script method (`0x51ced0`) needs the entity's `0x100` (DYNAMICPATH) flag, else it errors
    "script_brushmodel must have DYNAMICPATH set to disconnect paths" (`0x8626a8`).
  - **At load.** A loop (`0x55a3c0-0x55a3fc`) runs it for every in-use entity with flags `0x100` and `0x200`, so
    DYNAMICPATH brushes disconnect automatically.
  - **Candidate nodes.** The entity's absolute bounds (`ent+0x148..0x15c`) are grown by **266** units on every side
    (`0x869438`). A node is a candidate if its origin (`node+0x14`) is inside that box (`0x55d9fa-0x55da38`). Node types
    `0x10` and `0x11` are always candidates.
  - **Per link** (count `node+0x3e`, 12-byte links at `node+0x40`, target index at link `+4`): a box is swept from the
    node's origin to the linked node's origin **against that entity only** (`0x5ac710`). The box is mins
    **(−15, −15, 18)**, maxs **(15, 15, 72)** (`0x83a174`, `0x83a3b0`), with mask `0x2820011`.
  - **Cut.** If the sweep hits, the link is cut (`0x55d770`).
  - So a link is cut only when a standing-size box, lifted 18 units (step height), actually crosses the brush between
    the two nodes. Being near the brush is not enough.
  - [I] `0x55d770` probably also removes the reverse link.
  - If a test cuts every link with an endpoint in the bounds, it will over-cut. The 266 margin only selects candidates.

- **On purchase [V].** The debris trigger calls `ConnectPaths()` on every targeted piece, clip included
  (`maps/_zombiemode_blockers.gsc:275`). Then it deletes or moves the junk. That restores the links.

For the port: keep all 3 nodes. Block their links while `balcony_blocker` is unset and re-link when it is bought. The
longest route then depends on the debris state, not on the drop.

## 7. Zombie xanim timings [V]

Read from the zone's xanims with `e115_zonedump --xanim` into a scratch `.glb`. Values:
- **Times** are seconds from the start of the anim.
- **Speeds** are the `tag_origin` root-motion distance from the first key to the last, divided by the length, in CoD
  units/s.
- **Frame rate:** every clip is 30 fps.
- **Missing `tag_origin` track:** a clip without one has no root motion.

### Move cycles

Mapped in `maps/_zombiemode.gsc:338-372`. All loop.

| script name | xanim | length | distance | speed |
|---|---|---|---|---|
| walk1 | `ai_zombie_walk_v1` | 4.133 | 155.6 | **37.6** |
| walk2 | `ai_zombie_walk_v2` | 3.133 | 122.1 | **39.0** |
| walk3 | `ai_zombie_walk_v3` | 3.567 | 133.7 | **37.5** |
| walk4 | `ai_zombie_walk_v4` | 2.867 | 136.8 | **47.7** |
| run1 | `ai_zombie_walk_fast_v1` | 2.733 | 178.8 | **65.4** |
| run2 | `ai_zombie_walk_fast_v2` | 2.467 | 199.3 | **80.8** |
| run3 | `ai_zombie_walk_fast_v3` | 2.267 | 177.9 | **78.5** |
| sprint1 | `ai_zombie_sprint_v1` | 2.133 | 303.1 | **142.1** |
| sprint2 | `ai_zombie_sprint_v2` | 1.967 | 274.3 | **139.4** |
| crawl1 | `ai_zombie_crawl` | 5.533 | 90.7 | **16.4** |
| crawl2 | `ai_zombie_crawl_v1` | 4.067 | 55.7 | **13.7** |
| crawl3 | `ai_zombie_crawl_sprint` | 2.300 | 91.1 | **39.6** |

Footsteps are the `footstep_left_large` / `footstep_right_large` notetracks.

`set_zombie_run_cycle` (`maps/_zombiemode_spawner.gsc:117-190`) also gives each variant a death anim, `ch_dazed_a..d_death`.
The `ch_dazed_*` cycles themselves (26-39 u/s) aren't used as move cycles in Nacht.

### Tearing boards

One `board` notetrack per anim; the board is removed at that point (`:528-553`).

| anim | board at | length | root motion |
|---|---|---|---|
| `ai_zombie_door_tear_high` | 1.167 | 2.600 | none |
| `ai_zombie_door_tear_left` | 1.267 | 2.400 | none |
| `ai_zombie_door_tear_right` | 1.267 | 3.033 | none |
| `ai_zombie_door_tear_low` | 1.100 | 2.267 | none |
| `ai_zombie_attack_crawl` (crawler) | 1.000 | 2.633 | none |
| `ai_zombie_attack_crawl_lunge` (crawler) | 0.533 | 1.433 | none |

The two crawler anims also have `fire` notetracks, at 0.8 / 1.8 and at 0.4. During tearing those do nothing, because
the tear loop only listens for `board`.

So one zombie removes **a board every 2.3-3.0 s**: 1.1-1.27 s to the first. Five boards take about 12-14 s for one zombie
[I: assumes no blend gap between anims].

`ai_zombie_door_tear_v1/v2` (multi-board, `board_one..five`) and `door_pound_v1/v2` are in the zone but Nacht's script
doesn't use them.

### Melee

`level._zombie_melee[0..3]`:

| anim | `fire` at | length | root motion |
|---|---|---|---|
| `ai_zombie_attack_forward_v1` | 0.967, 1.400 | 2.333 | 23.5 forward |
| `ai_zombie_attack_forward_v2` | 0.867, 1.400 | 3.333 | 62.6 forward |
| `ai_zombie_attack_v1` | 0.833, 1.300 | 1.800 | none |
| `ai_zombie_attack_v2` | 0.700, 2.333, 3.833, 4.467, 5.333 | 7.167 | 2.4 |

Crawler melee is `ai_zombie_attack_crawl` (fire 0.8, 1.8) or `_crawl_lunge` (fire 0.4). In practice it is always
`ai_zombie_attack_crawl`: the pick uses `randomintrange( 0, 1 )`, which is always 0 (`animscripts/melee.gsc:657`) [V].
Board tearing does pick either one, 50/50 (`_zombiemode_spawner.gsc:578-583`).

- **No early exit.** None of these anims has a `stop` notetrack, so `CanContinueToMelee` is never checked mid-anim. The
  whole anim plays, and each `fire` calls `melee()` (`animscripts/melee.gsc:126-150`).
- **Rate.** That works out to **2 swings per 1.8-3.3 s**, or 5 in 7.2 s for `attack_v2`.
- **Missed swings.** A swing only lands if the engine melee trace (64/20/10) reaches the player at that moment [I].

### Window climb

`wall_hop`, all three with a `gravity on` notetrack, so the fixed 1.03 s in `advancedTraverse` isn't used:

| anim | gravity on | length | root motion (forward, up) |
|---|---|---|---|
| `ai_zombie_traverse_v1` | 1.733 | 1.933 | 64.6, +10.9 |
| `ai_zombie_traverse_v2` | 1.367 | 1.467 | 70.1, +18.6 |
| `ai_zombie_traverse_crawl_v1` | 2.133 | 3.333 | 68.8, 0 |

### Death

| anim | `start_ragdoll` at | length |
|---|---|---|
| `ai_zombie_death_v1` | 0.400 | 2.000 |
| `ai_zombie_death_v2` | 0.733 | 2.267 |
| `ch_dazed_a..d_death` | none, so ragdoll at 35% of the length | 2.133 / 2.667 / 4.433 / 4.500 |
| `ai_zombie_crawl_death_v1/v2` | none | 1.367 / 1.200 |

## Open items for M2

Not covered yet, roughly in order of need:
1. ~~Xanim timings~~: done, see section 7.
2. **Zombie melee damage.** The 60 figure needs checking in the engine's actor-melee damage path or in game.
3. ~~Zombies difficulty~~: solved.
   - The Solo Zombies button runs `set ui_gametype zom; ...; devmap nazi_zombie_prototype` and never sets
     `g_gameskill` (`ui.ff` menu script, inflated).
   - The co-op path sets `zombiemode 1` and the map name, again without `g_gameskill` (`patch.ff`).
   - So Zombies inherits the profile's campaign difficulty, which defaults to **1 = Normal**. The `g_gameskill`
     registration has default 1 and range 0-3 (`t4sp 0x632b26-0x632b2c`).
   - Normal uses the blended values at frac 0.75 in section 4.
4. ~~Sprint recharge and `PM_CmdScale`~~: done, see section 5.
5. ~~Zombie move speeds~~: done, see section 7.
6. **Sounds.** Zombie vocal aliases (ambient, attack, death) and the sound alias tables, if M2 wants audio parity.
7. Weapon data: covered by `weapons.json`.

## Addendum: the round director, solo [V]

Most of this is already in `zombies_t4_nacht.md` ("Round loop", "Zombie count per round", "Spawn rules", "Zombie
health"). `zombies_t4_nacht_flow.md` has the timings ("Round change", "Game over"). This adds only the gaps and one
lookup table.

**Per-round table for solo.** It's computed from those rules:
- count: 4/9/14/19 for rounds 1-4, then 24
- health: +100 per round, then ×1.1 with int truncation from round 10
- delay: 3 × 0.95^(N−1)
- move speed: (N−1) × 8, but round 1 is 1

| round | count | health | spawn delay (s) | move speed |
|---|---|---|---|---|
| 1 | 4 | 150 | 3.000 | 1 |
| 2 | 9 | 250 | 2.850 | 8 |
| 3 | 14 | 350 | 2.707 | 16 |
| 4 | 19 | 450 | 2.572 | 24 |
| 5 | 24 | 550 | 2.444 | 32 |
| 6 | 24 | 650 | 2.321 | 40 |
| 7 | 24 | 750 | 2.205 | 48 |
| 8 | 24 | 850 | 2.095 | 56 |
| 9 | 24 | 950 | 1.990 | 64 |
| 10 | 24 | 1045 | 1.891 | 72 (all sprint) |
| 11 | 24 | 1149 | 1.796 | 80 |
| 12 | 24 | 1263 | 1.706 | 88 |
| 13 | 24 | 1389 | 1.621 | 96 |
| 14 | 24 | 1527 | 1.540 | 104 |
| 15 | 24 | 1679 | 1.463 | 112 |
| 20 | 24 | 2701 | 1.132 | 152 |

**Max alive:** 24, via the patched `SetAILimit( 24 )`. The script's own guard is > 31. Solo never has more than 24 in
a round anyway.

**The gaps:**
- **No dog rounds in Nacht.** No Nacht script mentions dogs (none of `nacht_dump/maps/*`). Dogs arrive with Verrückt-era
  `_zombiemode_dogs`. The only dog reference is the generic `G_Damage` dog clamp (`t4_hits_damage.md`).
- **`zombie_round_time` (30 s) does nothing.** It's copied to `level.round_timer` each round (`_zombiemode.gsc:1185`),
  and nothing reads it. There's no round time limit.
- **Round-end condition** (`round_wait`, `:1325-1333`):
  - It waits 1 s first, then polls every 0.5 s until **all** of these hold:
    - axis AI count = 0 (`GetAiArray("axis").size`, so any axis AI counts, `_zombiemode_utility.gsc:13-18`)
    - `zombie_total` = 0 (`round_spawning` decrements it per successful spawn)
    - `level.intermission` is false
  - So the round can end up to 0.5 s after the last kill. Then the 10 s break follows (flow doc).
- **Game over** (`_zombiemode.gsc:1660-1687`):
  - It's checked when a player takes lethal damage.
  - If every player is the victim, a zombie, in last stand or spectating, it sets `intermission` and calls `end_game`.
  - **In solo, the first down ends the game** (Nacht has no solo revive).
- **Spawn-delay floor.** The clamp to 0.08 is applied before the ×0.95, so the delay never goes below 0.076. It takes
  until about round 72 to get there, so it doesn't matter in practice.

**For one Reforged ruleset** [I: design pick]:
- Keep Nacht's numbers as the WaW preset.
- Make the director data-driven: a per-round count/health/delay/speed table plus a hook for special rounds.
- Dogs (and later Kino-era specials) then become a per-map special-round schedule rather than code. Nacht's schedule
  is empty.

## Addendum: which xanim plays when [V]

The timings for every anim named here are in §7. This section adds which anim gets picked.

**Move cycle.** It's picked once per zombie at spawn (`set_zombie_run_cycle`, `_zombiemode_spawner.gsc:117-190`). The
speed class (walk/run/sprint) is set first (§1). Then within the class it's uniform random, and **each move variant
fixes the zombie's death anim**:

| class | variant (`level.scr_anim["zombie"][…]`, `_zombiemode.gsc:347-355`) | death anim |
|---|---|---|
| walk (1 in 4) | `walk1` `ai_zombie_walk_v1` | `ch_dazed_a_death` |
| | `walk2` `ai_zombie_walk_v2` | `ch_dazed_b_death` |
| | `walk3` `ai_zombie_walk_v3` | `ch_dazed_c_death` |
| | `walk4` `ai_zombie_walk_v4` | `ch_dazed_d_death` |
| run (1 in 3) | `run1` `ai_zombie_walk_fast_v1` | `ch_dazed_a_death` |
| | `run2` `ai_zombie_walk_fast_v2` | `ch_dazed_b_death` |
| | `run3` `ai_zombie_walk_fast_v3` | `ch_dazed_c_death` |
| sprint (1 in 2) | `sprint1` `ai_zombie_sprint_v1` | `ch_dazed_c_death` |
| | `sprint2` `ai_zombie_sprint_v2` | `ch_dazed_d_death` |

**Death.**
- **It doesn't depend on hit direction or location.** Every zombie has `self.deathanim` set from spawn.
  `animscripts/death.gsc:84-101` plays `self.deathanim` whenever it's defined, so the generic per-direction death
  tables are never reached.
- **Ragdoll timing:** at the `start_ragdoll` notetrack, or at 35% of the length if the anim has none (`:96-98`).
- **The exceptions** (`_zombiemode_spawner.gsc`):
  - **Legs shot off on the killing hit**, while still standing (`gib_ref == "no_legs"`): `ai_gib_bothlegs_gib`
    (`:1094-1099`).
  - **Crawlers** use the death anim picked when they lost their legs (below).
- `ai_zombie_death_v1/v2` (`death1/2`) are in the anim table, but **nothing in Nacht plays them** (grep, both zones'
  scripts).

**Idle.**
- **Standing:** `ai_zombie_idle_v1_delta` (weight 10, `_zombiemode.gsc:381`). In combat, exposed idle is
  `ai_zombie_idle_v1`, on the base `ai_zombie_idle_base` (`animscripts/combat.gsc:541-542`).
- **Crawling:** `ai_zombie_idle_crawl_delta` (`_zombiemode.gsc:386`), and in combat `ai_zombie_idle_crawl` on
  `ai_zombie_idle_crawl_base` (`combat.gsc:632-633`).
- Zombies rarely idle: only when they have no path or no target.

**Becoming a crawler** (`_zombiemode_spawner.gsc:868-904`):
- **When:** a non-fatal hit picks a leg gib (`right_leg`, `left_leg` or `no_legs`).
- **What it sets:** `has_legs = false` and `AllowedStances("crouch")`. Then it picks uniformly from three:

  | pick | crawl cycle (`crouchRunAnim`) | death anim |
  |---|---|---|
  | 0 | `crawl1` `ai_zombie_crawl` | `ai_zombie_crawl_death_v1` |
  | 1 | `crawl2` `ai_zombie_crawl_v1` | `ai_zombie_crawl_death_v2` |
  | 2 | `crawl3` `ai_zombie_crawl_sprint` | `ai_zombie_crawl_death_v2` |

  - The script also sets the *standing* run anim to the crawl death (`set_run_anim("death3"/"death4")`), but standing
    is no longer allowed, so the crouch run anim is what plays [I].
- **The stand-to-crawl transition** is the combat array's `stand_2_crouch`, `ai_zombie_shot_leg_right_2_crawl`
  (`combat.gsc:543`). The crouch set has `ai_zombie_shot_leg_left_2_crawl` (`:634`).
  - [I] Only the right-leg one plays on the stand→crouch change, whichever leg was lost.
- **Window climb:** `ai_zombie_traverse_crawl_v1` (§1).

**Window tear and climb.** Board tear is by board height, with crawlers 50/50 between `attack_crawl` and
`attack_crawl_lunge`. The climb is `traverse_v1`/`_v2` 50/50, or `traverse_crawl_v1` for crawlers (§1, "Tear boards",
"Climb in").

**Attack.**
- With legs: uniform from `ai_zombie_attack_forward_v1`, `_forward_v2`, `ai_zombie_attack_v1`, `_v2`
  (`animscripts/melee.gsc:627-652`, table `_zombiemode.gsc:362-366`).
- Crawlers: always `ai_zombie_attack_crawl` (see §7).
