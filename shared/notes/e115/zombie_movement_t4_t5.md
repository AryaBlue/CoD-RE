# Zombies: movement and animation, T4 then T5

What drives a zombie's feet: the speed class, the move cycles, windows, melee, traversals and the crawler switch. It's for
the engine's native zombies and its NavActors. It fills the gaps in [zombies_t4_nacht_ai.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht_ai.md), which already has the
lifecycle (§1), the gibs (§3) and the per-anim timings (§7 and "which xanim plays when"). Facts that are already there
are only linked, not repeated.

Tags:
- **[V]**: read. `nacht:` paths are relative to the Nacht zone dump, and `df:` paths to the Der Riese
  (`nazi_zombie_factory`) dump. `common:` is the shared SP `animscripts` dump that both use. `bo1:` paths are relative to
  the BO1 mod tools' `raw/`.
- **[M]**: measured from the zone xanims with `e115_zonedump --xanim`. Times are seconds at 30 fps. Root motion is the
  `tag_origin` delta from the first key to the last, in CoD units (forward, side, up).
- **[I]**: inferred.

Parts:
- T4: 1 Speed class · 2 Move speeds and cycles · 3 Windows · 4 Melee · 5 Traversals · 6 Gibs and crawlers
- T5: the BO1 differences, same numbering
- One Reforged ruleset

---

# T4 (WaW)

Nacht is the baseline. Der Riese is the last WaW framework, so its changes are listed under each topic as "Der Riese".

## 1. Walk, run or sprint

### The rule [V]

- **Level speed.** `level.zombie_move_speed` starts at 1 (`nacht:maps/_zombiemode_spawner.gsc:8`). At each round's end
  it becomes round × 8 *before* the round counter goes up (`nacht:maps/_zombiemode.gsc:1222-1224`). So round N plays at
  **(N − 1) × 8**, and round 1 at 1. The shipped patch fork has the same rule (`_zombiemode_prototype.gsc:1223`).
- **Per zombie, once at spawn** (`set_run_speed`, `nacht:maps/_zombiemode_spawner.gsc:192-209`):
  1. Roll a uniform integer from S to S + 34, where S is the level speed. [I] `randomintrange`'s upper bound is
     exclusive.
  2. ≤ 35 means walk, ≤ 70 means run, anything higher means sprint.
- The class never changes after spawn in Nacht. Nothing re-rolls it.

### The odds per round [V for the rule, I for the arithmetic]

The average speed uses the per-class mean of the cycles in §2 (walk 40.5, run 74.9, sprint 140.8 u/s).

| round | S | walk | run | sprint | average speed (u/s) |
|---|---|---|---|---|---|
| 1 | 1 | 100% | 0 | 0 | 40.5 |
| 2 | 8 | 80% | 20% | 0 | 47.3 |
| 3 | 16 | 57% | 43% | 0 | 55.2 |
| 4 | 24 | 34% | 66% | 0 | 63.1 |
| 5 | 32 | 11% | 89% | 0 | 71.0 |
| 6 | 40 | 0 | 89% | 11% | 82.4 |
| 7 | 48 | 0 | 66% | 34% | 97.5 |
| 8 | 56 | 0 | 43% | 57% | 112.5 |
| 9 | 64 | 0 | 20% | 80% | 127.6 |
| 10+ | ≥72 | 0 | 0 | 100% | 140.8 |

### Per-zombie overrides

- **Crawlers** (§6) drop the class's cycle for a crawl cycle. `zombie_move_speed` keeps its old value [V], and the later
  WaW scripts still read it (Der Riese's window hop below) [V].
- **Nacht has no other override** [V]: no last-zombie rule and no burn slow-down.
- **Der Riese** adds two:
  - **The last zombie sprints.** From round 4 (`round_number > 3`), once spawning is done, the director polls every
    0.5 s. When exactly one axis AI is left and it has legs, it gets a random sprint cycle
    (`df:maps/_zombiemode.gsc:1624-1640`) [V].
    - Only the anim changes, not `zombie_move_speed` [V]. So that zombie still uses its old class's melee and window
      anims [I].
    - It re-applies every 0.5 s, so the sprint anim is re-picked each poll [V]. [I] In practice this restarts the blend
      each time; a port can set it once.
  - **Burning zombies** get `moveplaybackrate` 0.8 on `MOD_BURNED` damage (`df:maps/_zombiemode_spawner.gsc:2795`;
    Verrückt has it too, `zm_asylum` `:1833`) [V]. That scales the move cycle and so the speed by 0.8 [I].

## 2. Move speeds and cycles

### Where the speed comes from

**It comes from the anims, not the script.**
- The move cycle is played through `animscripts/run.gsc` as an override anim (`run_combatanim`, or
  `crouchrun_combatanim` for crawlers). Its parent `combatrun` uses `moveplaybackrate`
  (`common:animscripts/run.gsc:90-102`, `:320`) [V].
- `moveplaybackrate` defaults to 1 (`common:animscripts/init.gsc:489`) [V]. No Nacht script changes it [V].
- Nothing sets a speed value [V]. The engine moves the actor along its path by the anim's root-motion delta [I: the
  standard CoD actor model, consistent with every speed below being the clip's `tag_origin` delta].
- **So for a port:** ground speed = root distance ÷ clip length × play rate. Drive the NavActor's speed from the
  clip, or bake these numbers per clip.

### Nacht cycles

The lengths, distances and speeds per cycle are in `zombies_t4_nacht_ai.md` §7 [M]. Summary:

| class | xanims (`level.scr_anim["zombie"]`, `nacht:maps/_zombiemode.gsc:347-360`) | speed (u/s) |
|---|---|---|
| walk (1 of 4) | `ai_zombie_walk_v1`, `_v2`, `_v3`, `_v4` | 37.6, 39.0, 37.5, 47.7 |
| run (1 of 3) | `ai_zombie_walk_fast_v1`, `_v2`, `_v3` | 65.4, 80.8, 78.5 |
| sprint (1 of 2) | `ai_zombie_sprint_v1`, `_v2` | 142.1, 139.4 |
| crawl (1 of 3) | `ai_zombie_crawl`, `ai_zombie_crawl_v1`, `ai_zombie_crawl_sprint` | 16.4, 13.7, 39.6 |

- The variant is uniform within the class and also fixes the death anim (Nacht doc, "which xanim plays when") [V].
- For comparison, the player's base run is 190 u/s (Nacht doc §5). A sprinter at 140 is about 74% of that.

### Der Riese cycles [V for the tables, M for the speeds]

Der Riese picks by index (`df:maps/_zombiemode_spawner.gsc:211-242`). The picks are uniform but don't cover every table
entry, because the upper bound is exclusive:

| class | pick | table (`df:maps/_zombiemode.gsc:682-751`) | in play |
|---|---|---|---|
| walk | 1-7 | walk1-4 as Nacht, walk5 `ai_zombie_walk_v6`, walk6 `_v7`, walk7 `_v8`, walk8 `_v9` | walk8 (`walk_v9`) is never picked |
| run | 1-5 | run1-3 as Nacht, run4 `ai_zombie_run_v2`, run5 `_run_v4`, run6 `_run_v3` | run6 (`run_v3`) is never picked |
| sprint | 1-3 | sprint1 `_sprint_v1`, sprint2 `_v2`, sprint3 `_v1`, sprint4 `_v2` | `sprint_v1` gets 2 in 3 |

- The death anim is now random from a list, not tied to the cycle (`:215`) [V].
- **Measured speeds of the new cycles [M]** (Der Riese zone):

| xanim | length | distance | speed |
|---|---|---|---|
| `ai_zombie_walk_v6` | 4.200 | 96.3 | 22.9 |
| `ai_zombie_walk_v7` | 3.433 | 79.1 | 23.0 |
| `ai_zombie_walk_v8` | 3.900 | 106.7 | 27.4 |
| `ai_zombie_walk_v9` | 4.400 | 114.7 | 26.1 |
| `ai_zombie_run_v2` | 2.233 | 242.0 | 108.3 |
| `ai_zombie_run_v4` | 2.467 | 232.9 | 94.4 |
| `ai_zombie_run_v3` | 2.167 | 223.6 | 103.2 |

  So Der Riese's walkers are slower on average (7 picks, 3 of them about 23-27 u/s) and its runners faster (2 of 5 at
  94-108 u/s) than Nacht's.

## 3. Windows (barriers)

The tear loop, the attack spots and the board-tear anims are in the Nacht doc §1 "Tear boards" and §7 "Tearing boards".
This adds the numbers that were missing.

### Attack-spot layout [V]

`blocker_attack_spots` (`nacht:maps/_zombiemode_blockers.gsc:423-444`) builds 3 spots per window at load:
- **Centre:** from the window's goal struct, along its forward, by (2D distance to the closest board − 36), dropped to
  the ground (`groundpos` from 60 up).
- **Flanks:** the centre ± 28 units along the struct's right, each dropped to the ground the same way.

### Claiming and tearing [V]

- **Claim** (`get_attack_spot_index`, `nacht:maps/_zombiemode_spawner.gsc:509-525`): uniform among the free spots. With
  none free, the zombie waits 0.5 s and retries (`:448-453`).
- **Arrive:** goal radius 4 on the spot, facing the struct's angles, and wait for `orientdone` (`:455-457`).
- **Board choice:** the closest standing board in 2D to the zombie (`get_closest_non_destroyed_chunk`,
  `nacht:maps/_zombiemode_utility.gsc:338-350`).
  - Two zombies can pick the same board. The second one's `board` notetrack then does nothing, because the board is
    already gone (`:540-542`). That anim is wasted.
- **Anim:** played with `AnimScripted` at the zombie's origin and the struct's angles (`:470`). Tear anims have no root
  motion (Nacht doc §7) [M].
- **When the last board is gone,** the zombie frees *all three* spots, not just its own (`:463-468`).
- **Board removal** (`remove_chunk`, `nacht:maps/_zombiemode_blockers.gsc:639-700`):
  - The board goes non-solid, plays `break_barrier_piece` and 3 FX.
  - It flies 100-199 units outward along the struct's reverse facing, onto the ground found by a trace.
  - It rotates pitch 180 over half the flight (60%), or 90 (40%).

### Climb-in [V for the rule, M for the timings]

- **Nacht:** every window is a `wall_hop` negotiation pair. Anims and timings are in the Nacht doc ("Climb in", §7
  "Window climb").
- **Der Riese:** its 28 windows also use `wall_hop` (`df` ents). Der Riese's own `wall_hop_zombie` script, which picks
  by speed class, isn't referenced by any of its ents. So Der Riese plays the shared `wall_hop`: v1/v2 50/50, or
  `traverse_crawl_v1` for crawlers (`common:animscripts/traverse/wall_hop.gsc:38-55`). [I] The traverse script is
  found by the node's `animscript` name.
- **Verrückt and Shi No Numa** use `wall_hop_zombie` on some windows (20 and 7 nodes).
  `df:animscripts/traverse/wall_hop_zombie.gsc:21-55`:

  | zombie | anims |
  |---|---|
  | walk | `ai_zombie_traverse_v1`, `_v2` |
  | run | `ai_zombie_traverse_v5` |
  | sprint | `ai_zombie_traverse_v6`, `_v7` |
  | crawler | `ai_zombie_traverse_crawl_v1`, `ai_zombie_traverse_v4` |

  Timings from the Der Riese zone [M]:

  | anim | gravity on | blend | length | root motion |
  |---|---|---|---|---|
  | `ai_zombie_traverse_v4` | 3.267 | 3.367 | 3.433 | 68.8, 15.7, 0 |
  | `ai_zombie_traverse_v5` | 1.400 | 1.533 | 1.567 | 62.7, 4.2, 0 |
  | `ai_zombie_traverse_v6` | 1.033 | 1.133 | 1.133 | 108.6, 5.7, 0 |
  | `ai_zombie_traverse_v7` | 1.367 | 1.400 | 1.400 | 71.4, 3.1, 0 |
  | `ai_zombie_traverse_crawl_v1` | 6.533 | 7.333 | 7.667 | 76.8, 2.6, 0 |

  - **`ai_zombie_traverse_crawl_v1` differs by zone.** Der Riese's copy is 7.667 s; Nacht's is 3.333 s (Nacht doc §7)
    [M]. Read the clip from the zone that's loaded; don't hard-code it.
  - `traverse_v1`/`_v2` are the same in both zones [M].
  - Verrückt's and Shi No Numa's copies of `wall_hop_zombie` are identical to Der Riese's [V: diffed].
- **Shi No Numa ships its own `wall_hop`** (`zm_sumpf:animscripts/traverse/wall_hop.gsc`), used by its 38 `wall_hop`
  windows [V]:
  - It picks by speed class like the table above, but walkers also get `ai_zombie_traverse_v3`.
  - **Before round 10,** it falls back to Nacht's set: v1/v2 with legs, `traverse_crawl_v1` without.
  - [I] So per map, the same `animscript` name can resolve to different scripts. Key the table by map.
- **How `advancedTraverse` ends** (`df:animscripts/traverse/shared.gsc:6-60`) [V]:
  1. The anim plays with a 0.15 s blend-in, at rate 1 unless `traverseplaybackrate` is set. No zombie script sets it.
  2. At `gravity on`, gravity comes back. With no such notetrack, it waits 1.23 − 0.2 = 1.03 s, then turns gravity
     on.
  3. The traverse ends at `blend`, or 0.2 s after `gravity on` if there's no `blend`. Then the move cycle takes over.

## 4. Melee

### Nacht

Range, facing, anims, `fire` times, hit rate and damage are all in the Nacht doc: §1 "Attack", §2 and §7 "Melee". In
short:

| item | value |
|---|---|
| range | `meleeAttackDist` 64, `anim.meleeRange` 64. The engine trace is 64 long, 20 wide, 10 high [V] |
| charge | none (`PrepareToMelee` returns at once) [V] |
| anims | `ai_zombie_attack_forward_v1`, `_forward_v2`, `ai_zombie_attack_v1`, `_v2`, uniform; crawlers always `ai_zombie_attack_crawl` [V] |
| damage frame | each `fire` notetrack calls the engine `melee()` [V] |
| damage | 150 (kar98k meleeDamage) × 0.4 = 60 per hit [V] |
| next swing | after the anim ends, if still in range; no `stop` notetrack, so no early out [M] |

### Der Riese [V for the tables and rule, M for the timings]

**The pick depends on the speed class** (`pick_zombie_melee_anim`, `df:animscripts/melee.gsc:714-746`):
- **Walker:** uniform over the 7 standing attacks plus the 4 walk attacks.
- **Runner or sprinter:** uniform over the 7 standing attacks plus the 3 run attacks.
- **No legs at all** (`gib_ref` `no_legs`): `ai_zombie_walk_on_hands_shot_a` / `_b`.
- **Other crawlers:** `ai_zombie_attack_crawl` / `_crawl_lunge`, now really 50/50.

The standing set (`df:maps/_zombiemode.gsc:738-744`) is the Nacht 4 plus `attack_v1` again, `attack_v4` and `attack_v6`.
So `attack_v1` is weighted twice. The walk set is `ai_zombie_walk_attack_v1..v4` (`:758-761`), and the run set
`ai_zombie_run_attack_v1..v3` (`:745-747`).

The new clips [M]:

| anim | `fire` at | length | root motion |
|---|---|---|---|
| `ai_zombie_attack_v4` | 0.267 | 1.033 | none |
| `ai_zombie_attack_v6` | 0.100, 1.633 | 2.333 | none |
| `ai_zombie_walk_attack_v1` | 0.200 | 1.067 | 52.3 fwd (49 u/s) |
| `ai_zombie_walk_attack_v2` | 0.933 | 1.567 | 69.2 fwd (44 u/s) |
| `ai_zombie_walk_attack_v3` | 0.467 | 1.233 | 54.6 fwd (44 u/s) |
| `ai_zombie_run_attack_v1` | 0.467 | 0.700 | 72.3 fwd (105 u/s) |
| `ai_zombie_run_attack_v2` | 0.167 | 0.733 | 63.0 fwd (86 u/s) |
| `ai_zombie_run_attack_v3` | 0.100 | 0.933 | 85.9 fwd (92 u/s) |

- **The walk and run attacks move.** They carry the zombie forward at near its move speed, so a moving zombie keeps
  closing while it swings. The run attacks are flagged looped in the zone [M].
- `ai_zombie_walk_attack_v4` wasn't in my dump list; its timing isn't measured.
- **The hit rate rises a lot:** a run attack lands one `fire` every 0.7-0.93 s, against Nacht's 2 per 1.8-3.3 s.

## 5. Traversals

### How a node maps to an anim [V for the scripts, I for the engine lookup]

- A traversal is a `node_negotiation_begin` / `node_negotiation_end` pair. The begin node's `animscript` key names a
  script in `animscripts/traverse/`, whose `main()` runs when an actor paths across [I: the engine side isn't read].
- Inside the script, the anim is picked by `is_zombie`, `has_legs` and sometimes `zombie_move_speed`. Dogs get their own
  path.
- Ordinary `node_pathnode`s have no anim; zombies just walk the link.

### What each map uses [V, from the ents]

| map | negotiation scripts (node count) |
|---|---|
| Nacht | `wall_hop` ×12 (windows only); plus 634 `node_pathnode` |
| Verrückt | `wall_hop_zombie` ×20 |
| Shi No Numa | `wall_hop` ×38, `wall_hop_zombie` ×7, `crouch_jump_down_40` ×2 |
| Der Riese | `wall_hop` ×28, `zombie_jump_down_72` ×7, `_96` ×5, `_127` ×5, `_184` ×4, `_190` ×2, `zombie_jump_up_to_climb` ×6 |

So **Nacht has no traversal except the windows.** Jump-downs and climbs first matter on Der Riese.

### Der Riese scripts [V for the mapping, M for the timings]

The `zombie_jump_down_<h>` scripts play `ai_zombie_jump_down_<h>` (crawlers `ai_zombie_crawl_jump_down_72` in the 72
script) through `DoTraverse` (`df:animscripts/traverse/zombie_jump_down_72.gsc:5-42`; the others follow the same
pattern). `zombie_jump_up_to_climb` plays `ai_zombie_jump_up_2_climb`, or `ai_zombie_crawl_jump_up_2_climb` for
crawlers (`df:animscripts/traverse/zombie_jump_up_to_climb.gsc:5-44`).

| anim | gravity on | land | length | root motion |
|---|---|---|---|---|
| `ai_zombie_jump_down_72` | 0.900 | 0.967 | 1.133 | 58.9, 0, −71.0 |
| `ai_zombie_jump_down_96` | 0.900 | 0.967 | 1.133 | 58.9, 0, −95.1 |
| `ai_zombie_jump_down_120` | none | none | 1.300 | 56.7, −1.4, −116.1 |
| `ai_zombie_jump_down_127` | 1.067 | 1.133 | 1.300 | 56.7, −1.4, −128.0 |
| `ai_zombie_jump_down_184` | 1.067 | 1.133 | 1.300 | 56.7, −1.4, −184.9 |
| `ai_zombie_jump_down_190` | 1.067 | 1.133 | 1.300 | 56.7, −1.4, −189.9 |
| `ai_zombie_crawl_jump_down_72` | 0.867 | 0.933 | 1.200 | 72.9, 0.2, −72.3 |
| `ai_zombie_jump_up_2_climb` | none | none | 3.733 | 24.3, 7.3, +98.4 |
| `ai_zombie_crawl_jump_up_2_climb` | none | none | 5.967 | 34.9, 19.2, +96.9 |

- **The number in the name is the drop height,** and the clip's vertical delta matches it to within a unit or two [M].
  So a node pair needs the drop that its anim was authored for.
- **`DoTraverse`** (`df:animscripts/traverse/shared.gsc:121-204`) [V]:
  1. Faces the start node's yaw.
  2. Turns off gravity and clip.
  3. Plays the anim with a 0.2 s blend.
  4. Turns gravity back on when the anim ends. A `gravity on` notetrack also turns it on, through the generic notetrack
     table (`common:animscripts/shared.gsc:514`).
  5. Restarts the move cycle.
- **There is no height fix-up.** None of these clips has `traverse_align` or `traverse_drop`, and the zombie scripts don't
  pass `traverseHeight`. So the alignment step teleports nothing, and the drop step never runs [V]. The clip has to
  fit the geometry.
- `zombie_jump_down_120` is shipped but used by no Der Riese node.
- **Shi No Numa's `crouch_jump_down_40`** isn't in its dump folder. I didn't trace where it comes from.

### Risers (Der Riese, not Nacht)

Der Riese zombies can spawn out of the ground (`zombie_rise`, `df:maps/_zombiemode_spawner.gsc:34`, `:271-276`), with
rise anims per speed class (`df:maps/_zombiemode.gsc:824-845`) [V]. That's a spawn behaviour, not a traversal. It's
listed so the port knows it's there; I didn't read it further.

## 6. Gibs and the crawler switch

The full gib flow is in the Nacht doc §3 "Gibs". These are the thresholds and the one rule that's easy to miss.

### The thresholds [V]

- **Gate** (`zombie_should_gib`, `nacht:maps/_zombiemode_spawner.gsc:920-984`):
  - The hit must be ≥ **10%** of the zombie's health *before* the hit: damage ÷ (damage + health after) ≥ 0.10
    (`:972-977`).
  - No gibs from melee, burn, crush, fall or trigger-hurt damage, from pistols, or with no weapon.
- **Head gib:** the zombie at ≤ **10%** health, from a non-pistol bullet or a shotgun to the head, helmet or neck.
  After that, it loses **20% of its current health every 1 s** (Nacht doc §3).
- **Leg-hit refs** are right/left leg ×3 and `no_legs` ×1, so `no_legs` is 25%.

### Bullets to the legs never make a crawler in T4 [V]

- A direct leg hit adds leg refs **only when the hit kills** (`self.health <= 0`, `nacht:maps/_zombiemode_spawner.gsc:824-846`).
- The crawler switch needs the zombie **still alive** (`:876`).
- So a leg shot either does nothing or kills with the leg gib. **Live crawlers come only from:**
  - **Explosives and projectiles** (`MOD_GRENADE`, `MOD_GRENADE_SPLASH`, `MOD_PROJECTILE`, damage location `none`). The
    closest gib tag to the impact picks the refs (`derive_damage_refs`, `:986-1036`):
    - a hip, knee or ankle tag gives that leg or `no_legs`, 50/50
    - a spine tag gives guts or right arm
    - an arm tag gives that arm
  - **The catch-all location** (`:847-866`): any other non-`none` location rolls uniformly over all six refs, legs
    included, with no kill check. [I] This is rare for bullets, since the usual hit locations all have their own case.
- Der Riese keeps the same kill-only leg rule (`df:maps/_zombiemode_spawner.gsc:1602-1610`) [V].

### The switch [V]

- **Nacht:** `has_legs` false, crouch stance only, and one of 3 crawl cycles with its death anim (Nacht doc, "Becoming a
  crawler"). The stand→crouch transition is `ai_zombie_shot_leg_right_2_crawl`.
- **Der Riese** (`df:maps/_zombiemode_spawner.gsc:1652-1720`):
  - **`no_legs`** picks `ai_zombie_walk_on_hands_a` or `_b`, 50/50. They move at 16.1 and 20.4 u/s [M]. Those zombies
    melee with the `walk_on_hands_shot` anims (§4).
  - **One leg** picks 1 of 5: `crawl1`-`crawl5`. These are `ai_zombie_crawl` and `_crawl_v1` as in Nacht, plus
    `_crawl_v2`, `_v3` and `_v4` at 63.3, 88.9 and 57.8 u/s [M]. So some Der Riese crawlers are faster than Nacht's
    runners.
  - The death anims alternate between `ai_zombie_crawl_death_v1` and `_v2` by pick.
  - **Melee can gib:** `MOD_MELEE` gibs when the attacker has `specialty_altmelee` and a random roll > 0.25, a 75%
    chance (`df:maps/_zombiemode_spawner.gsc:1761-1766`). The Bowie knife script grants that perk
    (`df:maps/_zombiemode_bowie.gsc:113`) [V], so this is the Bowie gib. [I] Whether Der Riese's ents actually place a
    Bowie buy isn't checked.
  - `make_crawler` exists (`:3606`) but its only call is commented out (`:135`).

---

# T5 (BO1)

The BO1 changes against the Der Riese framework, topic by topic, plus extra Nacht notes where Der Riese already
differs from Nacht.

Extra source roots for this half:
- `bo1cz:` is a dump of BO1's shipped `common_zombie_patch` fastfile, from another session. The mod-tools `raw/` has no
  SP `animscripts/`, so every `zombie_*` animscript fact comes from it.
  - **Cross-checked [V]:** I dumped the installed `common_zombie.ff` + `common_zombie_patch.ff` again with OAT's Unlinker.
    All 56 of its `maps/` and `animscripts/` files match my dump byte for byte (line endings aside). So the `bo1cz:`
    citations are the shipped scripts.
  - The `maps/` files also match `bo1:` on every number used here.
- `bo1th:` is a Kino (`zombie_theater`) zone dump (`<scratch>/theater/`).
- `waw:` here means the same as `df:` (Der Riese), and `wawc:` the same as `common:`.

## 1. Walk / run / sprint per round

**Same as Der Riese:**
- **Roll.** Each zombie rolls once at spawn: a random int in [S, S+35). It walks at ≤35, runs at ≤70, otherwise sprints
  (`bo1:maps/_zombiemode_spawner.gsc:274-289`, `waw:maps/_zombiemode_spawner.gsc:244-262`) [V].
- **S.** It starts at 1 (`bo1:maps/_zombiemode.gsc:451`; `waw:…spawner.gsc:9`) [V]. At the end of each round, S = round × mult, and
  then the round number goes up (`bo1:…_zombiemode.gsc:2739-2740`, `waw:…_zombiemode.gsc:2096-2098`) [V]. So during round N
  (N ≥ 2), S = (N−1) × mult [I].

| | WaW | BO1 |
|---|---|---|
| multiplier | hard-coded 8 (`waw:…_zombiemode.gsc:2096`) [V] | `zombie_move_speed_multiplier` read from csv via the difficulty column (`bo1:…_zombiemode.gsc:480`). EASY 6, MEDIUM/HARD/VET 8 (`bo1:mp/zombiemode.csv:15`) [V]. Default difficulty uses MEDIUM, so 8 (see `zombies_t5_vs_t4.md`) |
| cap | none. Once S ≥ 71 every zombie sprints [I] | none [V: no clamp at `:2739`] |
| all sprint from | round 10 (S=72) [I] | round 10 on MEDIUM. EASY: round 13 [I] |

Odds per round with mult 8, computed [I]. They are the same in both games:

| round | walk | run | sprint |
|---|---|---|---|
| 1 | 100% | – | – |
| 2 | 80% | 20% | – |
| 3 | 57% | 43% | – |
| 4 | 34% | 66% | – |
| 5 | 11% | 89% | – |
| 6 | – | 89% | 11% |
| 7 | – | 66% | 34% |
| 8 | – | 43% | 57% |
| 9 | – | 20% | 80% |
| 10+ | – | – | 100% |

**Last-zombie sprint:**

| | WaW | BO1 |
|---|---|---|
| rounds | every round > 3 (`waw:…_zombiemode.gsc:1624-1638`) [V] | only rounds 4-9: started when round < 10, returns at once if ≤ 3 (`bo1:…_zombiemode.gsc:2169-2172, 2266-2270`) [V] |
| starts when | the spawn loop has finished | `zombie_total ≤ 4`, then ≤ 3 alive. Both are polled every 2 s (`:2276-2286`) [V] |
| who | the one remaining zombie, if it has legs. Re-checked every 0.5 s | same. BO1 counts `GetAiSpeciesArray("axis","all")`, so dogs and specials count too (`:2287-2297`) [V] |
| anim | `sprint1..3` at random | same. It sets the run anim directly and doesn't change `zombie_move_speed` (`:2291-2293`) [V] |

- [I] BO1's run animscript only re-applies the run anim when `needs_run_update` is set. The last-zombie sprint doesn't
  set it, so the switch shows up the next time the move script starts, which sets it at entry
  (`bo1cz:animscripts/zombie_run.gsc:155-169`, `bo1cz:animscripts/zombie_move.gsc:73`) [V for the gate].

**Per-zombie overrides (BO1 only):**
- **`set_zombie_run_cycle( new_move_speed )`.** It takes an optional forced class. Without one it rolls and stores
  `zombie_move_speed_original`. Either way it sets `needs_run_update` (`bo1:…spawner.gsc:241-253`) [V]. WaW has no
  parameter (`waw:…spawner.gsc:211`) [V].
- **Freeze gun.** It downgrades the class by the share of health the freeze gun has dealt (`bo1:maps/_zombiemode_weap_freezegun.gsc:270-291`) [V]:
  - at 66% or more: walk
  - at 33% or more: sprint becomes run, run becomes walk
- Pentagon's teleporter and elevators save and restore `zombie_move_speed`
  (`bo1:maps/zombie_pentagon_teleporter.gsc:755-795`) [V]. Specials set their own class (ape, boss, thief) [V, not detailed].
- **Crawlers** are covered in §6.

## 2. Move anims per class

Der Riese already has the 8/6/4-entry tables, and so does BO1. **Variant pick:** `randomintrange(1,8)` for walk,
`(1,6)` for run and `(1,4)` for sprint, so the last entry of each table is **never** used
(`bo1:…spawner.gsc:255-272`, `waw:…spawner.gsc:224-241`) [V].

| key | WaW Der Riese (`waw:maps/_zombiemode.gsc:682-751`) | BO1 (`bo1:maps/_zombiemode.gsc:739-758`) |
|---|---|---|
| walk1-4 | `ai_zombie_walk_v1..v4` | same |
| walk5, walk6 | `walk_v6`, `walk_v7` | same |
| **walk7** | **`ai_zombie_walk_v8`** | **`ai_zombie_walk_v9`** |
| walk8 (never picked) | `walk_v9` | `walk_v9` |
| run1-3 | `ai_zombie_walk_fast_v1..v3` | same |
| run4, run5 | `ai_zombie_run_v2`, `run_v4` | same |
| run6 (never picked) | `run_v3` | `run_v3` |
| sprint1-3 | `sprint_v1`, `sprint_v2`, `sprint_v1` | same, so `sprint_v1` gets 2/3 of sprinters [I] |

- **The one table difference:** BO1 drops `walk_v8` and uses `walk_v9` for 1/7 of walkers [V].
- **Death anim** (already a Der Riese change from Nacht). It's a uniform pick from `ch_dazed_a..d_death`, **not tied to
  the variant** (`bo1:…spawner.gsc:253-254`, `waw:…spawner.gsc:213-215`) [V].
- **Playback rate (BO1).**
  - `moveplaybackrate` = 1 for every zombie, and all run-anim calls pass it (`bo1cz:animscripts/zombie_init.gsc:317-321`,
    `zombie_run.gsc:164-165`) [V].
  - `animplaybackrate` = 0.9 + random(0.2), the same rule as WaW (`wawc:animscripts/init.gsc:488-489`) [V].
  - No zombie script changes `moveplaybackrate` (grep of `bo1:maps`). Only the boss resets it to 1.0
    (`bo1:maps/_zombiemode_ai_boss.gsc:670`) [V].
  - So **move speed comes from the anim's root motion alone, with no per-zombie scale** [I].
- **Run-anim refresh gate (BO1).** `MoveStandCombatOverride` and its crouch versions re-knob the anim only when
  `needs_run_update` is true. Otherwise they just wait (`bo1cz:animscripts/zombie_run.gsc:155-169, 222-234, 277-288`) [V].
- **Short paths.** If the goal is under 64 units away (4096 squared), the move mode is forced to walk
  (`bo1cz:animscripts/zombie_move.gsc:66-71`) [V].
- **Sidestep code** exists (`zombie_move.gsc:121-290`). It is gated on `zombie_can_sidestep`, which nothing in `bo1:maps`
  sets, so it's off for normal zombies (it's for the Spetsnaz DLC zombies) [V for the gate, I for the DLC].
- **`PushPlayer(true)`.** WaW sets it at spawn and again when entering (`waw:…spawner.gsc:90, 2899`) [V]. **BO1's zombie
  framework never calls it** (grep of `bo1:maps/_zombiemode*.gsc`) [V]. The effect on player blocking is not checked [I].

## 3. Windows and barriers

**Window pick** (`zombie_think`):
- WaW: `script_forcegoal` → the single closest goal to the target. Otherwise the 3 closest to the target (or to self), with
  the 500-unit drop rule and a random pick (`waw:…spawner.gsc:301-349`) [V].
- BO1: **any spawner with a non-empty `target`** gets the single closest goal to that target, with no random pick
  (`bo1:…spawner.gsc:347-356`) [V]. Untargeted spawners use the 3-closest + 500 rule from their own origin (`:375-403`) [V].
- BO1 skips teardown when the rise struct says `find_flesh` or the spawner's `script_string` is `zombie_chaser`
  (`:290-303, 359-375`) [V].
- WaW's Der Riese-only `riser_door` branch is gone [V].
- `zombie_assure_node` is unchanged (2 s, then the 20 closest, then death after 20 s). BO1 also counts
  `zombies_timeout_spawn` (`bo1:…:493-553`) [V].

**Tear loop** (`tear_into_building`, `bo1:…spawner.gsc:583-748` vs `waw:…:614-720`):

| | WaW | BO1 |
|---|---|---|
| no free attack spot | wait 0.5 s, retry | taunt roll (`do_a_taunt`), then wait 0.5 s (`:620-626`) [V] |
| goal radius at the spot | 4 (`waw:651`) | **2** (`bo1:630`) [V] |
| AnimScripted origin | the zombie's current origin (`waw:691`) | the **attack spot** origin, mode "normal", rate 1, blend 0.3 (`bo1:705`) [V] |
| chunk claim | `target_by_zombie` flag (`waw:690`) | chunk `state` = `"target_by_zombie"` (`bo1:691`). Selection only takes `state == "repaired"` chunks at their original origin (`bo1:maps/_zombiemode_utility.gsc:1688-1747`) [V] |
| no pickable chunk, but window not clear | return: free all spots, then connect paths [V]. [I] a second zombie can leave early while another is still tearing | stay: taunt (if it has legs and reach-in didn't fire) or wait a network frame, then retry (`bo1:664-684`) [V] |
| `endon` | death | death, plus `teleporting` (`:589`) [V] |
| after tear | clip `connectpaths` only (`waw:486`) | clip `disable_trigger` + `connectpaths` (if not already disabled). Then it waits for `zombie_start_traverse` / `zombie_end_traverse` before flagging "completed emerging" (`bo1:467-491`) [V] |
| `crash_into_building` | present, unused [I] | removed [V] |

**Which chunk next** (BO1 `get_closest_non_destroyed_chunk`, `bo1:…_zombiemode_utility.gsc:1588-1625`) [V]:
- **Chunks need `script_team` plus `script_parameters`, or they are never picked:**
  - `classic_boards` + `board`
  - `new_barricade` + `repair_board`
  - `6_bars_bent` / `6_bars_prestine` + `bar`
- Board-type chunks: closest 2D (`:965-990`).
- Bars: noteworthy 4 or 6 first, then the closest (`:991-1048`).
- Grate: fixed order 1→6, and the next piece is shown being pulled (`:1049-1150`).
- `bar_board_variant1/2/4/5`: fixed noteworthy order per variant (`:1152-1500`). From the returns: v1 2,3,4,6,5,1; v2 1,2,3,5,4,6;
  v4 1,6,3,4,2,5; v5 1,6,3,2,5,4.
- WaW only needs the chunk not destroyed and not claimed, and takes the closest 2D (`waw:maps/_zombiemode_utility.gsc:890-938`) [V].
- **[I] Porting WaW maps:** their chunks lack `script_team`, so the BO1 rules would never pick them. A profile must map them
  to `classic_boards`.

**Tear anim** (`get_tear_anim`, `bo1:…spawner.gsc:1430-2127` vs `waw:…:1023-1311`):
- **Same in both:** standing zombies with a `script_noteworthy` 1-6 use `ai_zombie_boardtear_{m,r,l}_{1..6}`, with
  m/r/l = attack spot 0/1/2. Crawlers use `ai_zombie_boardtear_crawl_{m,r,l}_{1..6}` [V].
- **WaW fallback** (no noteworthy): by height. Over 70 high, under 40 low, otherwise left/right at random. Crawlers:
  `attack_crawl` / `_lunge` (`waw:1160-1176`) [V].
- **BO1 is keyed on `script_parameters`:**

| chunk | standing | crawler |
|---|---|---|
| `board` / `repair_board` | boardtear table (`:1443-1619`) | boardtear crawl table (`:1878-1990`) |
| `repair_board` still `unbroken`, metal | noteworthy 1 `boardtear_m_1`, 2 `m_4`, 3 `door_tear_low`, 4 `m_5`, 5 `door_tear_low`, 6 `m_6` (`:1452-1478`) | crawl table |
| `repair_board` still `unbroken`, other material (glass) | `door_pound_v1` at spot 0, otherwise `door_pound_v2` (`:1480-1488`) | crawl table |
| `bar` | `bartear_{m,r,l}_{2,3,5,6}` and `bar_bend_{m_1,m_2,r,r_2,l,L_2}`, per spot × noteworthy (`:1620-1748`) | `bartear_crawl_{m,r,l}_{1..6}` (`:1991-2110`) |
| `grate` | boardtear table (`:1749-1877`) | **no crawler branch**, so the random fallback |
| none / no noteworthy | **random from 8:** `door_tear_high/low/left/right`, `door_tear_v1/v2`, `door_pound_v1/v2` (`:1433-1442`). There is no height rule any more [V] | same fallback |

- The crawler fallback (`attack_crawl` / `_lunge`) sits in an else-if whose condition can never be true, so it's
  dead code (`:2114-2120`) [V].

**Notetracks during tear** (`zombie_tear_notetracks`, `bo1:…:938-1123`). WaW only listens for `board` [V]. BO1:
- `board`: remove the chunk, plus horizontal splinter FX for noteworthy 1/4/5/6 or vertical for the rest.
- `bar_bend`: noteworthy 3/5 swap in a bent-bar model until it's repaired.
- `bar`: remove the chunk.
- Each removes via `remove_chunk(…, zomb)`, which sets the state to `mid_tear` and makes the chunk non-solid
  (`bo1:maps/_zombiemode_blockers.gsc:1301-1324`) [V].

**Reach-in attack through the boards** (`should_attack_player_thru_boards`, `bo1:773-852` vs `waw:749-813`):

| | WaW | BO1 |
|---|---|---|
| trigger range | any player within 72 units 2D | an alive, **not downed** player within **90** 2D (`bo1:804`) [V] |
| blocked when | crawler | crawler, **or any chunk still `unbroken`** (`:784-790`) [V] |
| chance | `zombie_reachin_freq` 50 (51% roll) | same |
| anims | `window_attack_arm_l_out` / `_r_out` by spot | same, plus vocals |
| hit at `fire` | engine `melee()` (`waw:834`) | scripted: a player within 90 2D and 90 height of the zombie **and** within 51 2D / 51 height of the window's `trigger_location` takes `DoDamage(meleeDamage, MOD_MELEE)`, one player per `fire`. It falls back to `melee()` only when there's no `first_node` (`bo1:869-893`) [V] |

- Taunt: the same 5% dvar. BO1 uses `ForceTeleport` back to the start origin instead of `teleport`, and adds a vocal
  (`bo1:749-771`) [V].
- New barrier types (BO1): `repair_board` with glass/metal `unbroken_section`, `bar`, `grate`, `window_shutter`, and the
  `noBoards` mutator. Details are in `zombies_t5_vs_t4.md` §3 (`bo1:…blockers.gsc:862-968`) [V].
  - The glass section has health 99999 and breaks on the **first** damage from a valid or downed player (`:970-984`) [V].

## 4. Melee

| | WaW Der Riese | BO1 |
|---|---|---|
| script | `animscripts/melee.gsc`, shared with human AI (`waw:animscripts/melee.gsc`) | `animscripts/zombie_melee.gsc`, zombie-only (`bo1cz:`) [V] |
| range | `meleeAttackDist` 64, `anim.meleeRange` 64 | same: 64 / 64. `chargeRangeSq` 200² (`bo1cz:animscripts/zombie_init.gsc:1063-1067`; `bo1:…spawner.gsc:3268-3269`) [V] |
| facing gate | – (not compared) | 60° to start, 110° to keep going (`zombie_melee.gsc:370`) [V] |
| throttle | at most 3 zombies start a swing per network frame (`waw:animscripts/melee.gsc:13-23, 122-135`) [V] | **none** (`zombie_melee.gsc:13-225`) [V] |
| swing | `fire` → `melee()`; `stop` → `CanContinueToMelee`; `end` breaks | same loop (`:141-182`) [V]. Adds: an exit when `marked_for_death` is set, and a `melee_miss_func` per AI or per level |
| anim knob | blend 0.2, rate 1 | same (`:141`) [V] |

**Anim pick** (the `pick_zombie_melee_anim` logic is the same: Der Riese `waw:animscripts/melee.gsc:714-745`, BO1 `bo1cz:…zombie_melee.gsc:680-711`) [V]:
- Walkers: base + walk set.
- Runners and sprinters: base + run set.
- `no_legs`: stumpy set.
- Other crawlers: crawl set. Both are uniform; the Nacht always-index-0 bug is gone in both.

The tables differ:

| set | WaW Der Riese (`waw:maps/_zombiemode.gsc:738-778`) | BO1 (`bo1:maps/_zombiemode.gsc:789-822`) |
|---|---|---|
| base | 7: `attack_forward_v1`, `forward_v2`, `attack_v1`, `v2`, `v1` (again), `v4`, `v6` | **6:** `attack_v2`, `v4`, `v6`, `v1`, `forward_v1`, `forward_v2`. `attack_v1` is no longer doubled |
| run | `run_attack_v1..v3` | same |
| walk | `walk_attack_v1..v4` | same |
| crawl | `attack_crawl`, `attack_crawl_lunge` | same |
| stumpy | `walk_on_hands_shot_a/b` | same |

So a BO1 walker picks from 10 anims (6 + 4), and a runner from 9 (6 + 3) [I].

**Damage per hit (BO1):**
- `player_damage_override` (`bo1:maps/_zombiemode.gsc:3167-3385`) replaces the damage when the attacker `is_zombie`
  (`:3213-3227`) [V], in this order:
  1. `custom_damage_func`, if the attacker has one
  2. otherwise the attacker's `meleeDamage`
  3. otherwise **50**
- **Correction to `zombies_t5_vs_t4.md` §9:** normal zombies set `meleeDamage = 60` at spawn
  (`bo1:maps/_zombiemode_spawner.gsc:166`) [V]. So **the script gives 60 per hit, and 50 is only the fallback**.
- The override returns `finalDamage` to `Callback_PlayerDamage`, which passes it on
  (`bo1:maps/_callbackglobal.gsc:437-445`) [V].
- `player_meleeDamageMultiplier` is still set to 0.4 outside versus mode (`bo1:maps/_gameskill.gsc:393-396`) [V].
  - **It's applied before the callback, so a hit lands as 60** [V, `BlackOps.exe`, the SP exe]:
    - The dvar's pointer lives at `0x1c01820` (registered at `0x7e0d4e-0x7e0d69`). It's read **once** in the whole exe, at
      `0x5406e5`, inside `G_Damage` (`0x5405c0`).
    - There the client branch scales the raw damage: × `player_radiusDamageMultiplier` for radius damage (`dflags & 1`,
      `0x5406cb`), × `player_meleeDamageMultiplier` for means of death 7, `MOD_MELEE` (`0x5406e0-0x5406f3`), and ×
      `player_damageMultiplier` otherwise (`0x5406f9`). The result is truncated, with a minimum of 1 (`0x540726-0x54072f`).
    - `G_Damage` then calls the script callback wrapper `0x437030` with that damage (`0x540ae2`). The wrapper uses the
      `CodeCallback_PlayerDamage` handle at `0x1c79b44`, which is set at `0x6126ea`.
    - The script replaces the damage with `meleeDamage` (60), and `finishplayerdamage` applies it. Its handler
      (`0x7da700`, from the method table at `0xa53140`) never reads the multiplier dvar.
    - So the 0.4 only scales the engine's own melee damage, which the script then throws away.
    - The engine damage comes from the `ai_meleeDamage` dvar: int, default 100, range 0-1000, at `0x1bd9b44`
      (`0x7e1b84-0x7e1b8b`). It's read at `0x5848be`. [I] So without the script override, a hit would be 100 × 0.4 = 40.
- **Same-attacker immunity:** 0.4 s (`level.ignore_enemy_timer`), the same as WaW (`bo1:…_zombiemode.gsc:3147-3160`,
  `waw:…_zombiemode.gsc:2555-2568`) [V].
- **Reach-in hits** go through the same override, so 60 [I].
- **Failsafe:** a zombie touching its player for 5 s+ without moving 60 units kills the player, unless the player has
  Jugg. This is the same as Der Riese (`bo1:…spawner.gsc:191-240`) [V].

## 5. Traversals

**Framework:**

| | WaW | BO1 |
|---|---|---|
| shared script | `animscripts/traverse/shared.gsc`: `advancedTraverse` (window) and `DoTraverse` (jumps) | `animscripts/traverse/zombie_shared.gsc`, `DoTraverse` only, for every zombie traverse (`bo1cz:…:72-189`) [V] |
| height alignment | `DoTraverse` teleports by (start node `traverse_height` − start z − anim height) unless the anim has a `traverse_align` note. `advancedTraverse` always offsets by 39.875 (`waw:animscripts/traverse/shared.gsc:6-60, 148-151, 230-238`) [V] | **`DoTraverse` never aligns.** `handleTraverseAlignment` only runs from `zombie_wall_crawl_drop` (`bo1cz:…zombie_shared.gsc:282-292`; `traverse/zombie_wall_crawl_drop.gsc`) [V] |
| gravity | `advancedTraverse`: at `gravity on`, else after a fixed 1.23 − 0.2 s (`waw:…shared.gsc:38-55`) [V] | no gravity for the whole anim, back on at the end (`:100, 157`). Generic `gravity on` / `gravity off` / `gravity code` notes switch AnimMode (`bo1cz:animscripts/zombie_shared.gsc:180-182, 274-289`) [V] |
| variants | one anim per script | `traverseAnim` may be an array, picked uniformly (`:136-139`). Supports a trans-in, a sequence and a trans-out (`:192-241`) [V] |
| end | – | sets the run anim (blend 0.2), waits 0.2 s, then notifies `zombie_end_traverse`. `zombie_start_traverse` fires at the start (`:78, 183-188`) [V] |
| death mid-traverse | – (not compared) | the `traverse_death` notetrack plus a ragdoll thread (`:260-300, 357+`) [V] |

**Window climb:**
- **Der Riese** ents use `"animscript" "wall_hop"` ×28 (`waw:maps/nazi_zombie_factory.d3dbsp.ents`) [V]. That resolves to
  common `wall_hop.gsc`: `traverse_v1` / `_v2` 50/50, crawlers `traverse_crawl_v1`, all through `advancedTraverse` at
  39.875 (`wawc:animscripts/traverse/wall_hop.gsc:44-53`) [V].
  - The zone also carries a speed-aware `wall_hop_zombie.gsc` (`waw:animscripts/traverse/wall_hop_zombie.gsc:29-54`) [V].
    No Der Riese node references it [I].
- **BO1 Kino** ents use `"animscript" "zombie_mantle_over_40"` ×27 (`bo1th:maps/zombie_theater.d3dbsp.ents`) [V].
  `bo1th:animscripts/traverse/zombie_mantle_over_40.gsc:33-85` [V]:

| zombie | anims (uniform) |
|---|---|
| walk | `ai_zombie_traverse_v1`, `_v2` |
| run | `ai_zombie_traverse_v5` |
| sprint | `ai_zombie_traverse_v6`, `_v7` |
| crawler | `ai_zombie_traverse_crawl_v1`, `ai_zombie_traverse_v4` |
| quad (legs) | `ai_zombie_traverse_v3` |
| dog | `dog_wall_and_window_hop("wallhop", 40)` |

- The walk/run/sprint class used is `zombie_move_speed`, so the last-zombie sprint (§1) still climbs with the class it
  rolled at spawn, and the freeze gun's slowdown does change it [I].

**Node `animscript` → anim.** Every jump script picks by `has_legs` and then by animname (director, monkey, quad)
(`bo1cz:animscripts/traverse/*.gsc`, `bo1th:animscripts/traverse/*.gsc`) [V]:

| node animscript | zombie | crawler | in WaW Der Riese |
|---|---|---|---|
| `zombie_jump_down_40` | `ai_zombie_jump_down_40` | **same anim, no crawler branch** | – |
| `zombie_jump_down_72` | `jump_down_72` | `crawl_jump_down_72` | yes |
| `zombie_jump_down_96` | – (not in BO1 common) | – | yes: `jump_down_96` / `crawl_jump_down_97` |
| `zombie_jump_down_120` (Kino) | `jump_down_120` (quads: `quad_jump_down_128`) | `crawl_jump_down_120` | yes |
| `zombie_jump_down_127` | `jump_down_127` | `crawl_jump_down_127` | yes |
| `zombie_jump_down_184` | `jump_down_184` | `crawl_jump_down_184` | yes |
| `zombie_jump_down_190` | `jump_down_190` | `crawl_jump_down_189` | yes |
| `zombie_jump_down_222` | `jump_down_222` | `crawl_jump_down_222` | – |
| `zombie_jump_down_240` | `jump_down_240` | `crawl_jump_down_240` | – |
| `zombie_jump_down_286` (Kino) | `jump_down_286` | `crawl_jump_down_286` | – |
| `zombie_jump_up_222` | `jump_up_222` | `crawl_jump_up_222` | – |
| `zombie_jump_up_to_climb` | – | – | yes: `jump_up_2_climb` / `crawl_jump_up_2_climb` |
| `zombie_wall_crawl_drop`, `_quick` (Kino) | quad wall-crawl intro (walk vs other speed), then `quad_wall_jump_off`, with its own wall-death anims | – | – |

Kino node counts: `jump_down` 40 ×1, 72 ×3, 120 ×1, 127 ×1, 190 ×5, 240 ×2, 286 ×2; `wall_crawl_drop` ×5; `_quick` ×7
(`bo1th:…ents`) [V].

Dogs use `dog_jump_down(h, 7)` / `dog_jump_up(h, 7)`, as in WaW [V].

## 6. Gibbing and crawlers

**Should-gib gate** (`zombie_should_gib`, `bo1:…spawner.gsc:2532-2597` vs `waw:…:1739-1812`):

| rule | WaW Der Riese | BO1 |
|---|---|---|
| melee | Bowie (`specialty_altmelee`) gibs 75% of the time (`waw:1761-1766`) | **never**. The Bowie line is commented out (`bo1:2565-2568`; `bo1cz:maps/_zombiemode_spawner.gsc:3084-3093`) [V] |
| bullet filter | no weapon, or **any pistol class** | no weapon, or **`m1911_zm` only** (`bo1:2577`). Other pistols can gib [V] |
| extra blocks | – | `is_mature()` off, `no_gib`, freeze-gun damage (`:2534-2547`) [V] |
| threshold | the hit ≥ 10% of the health before it | same (`:2587-2594`) [V] |

**Head gib** (`head_should_gib` / `zombie_head_gib`, `bo1:2141-2289` vs `waw:1326-1485`):
- **Same:**
  - ≤ 10% health
  - grenade within 55 units of `j_head`, projectile within 10
  - spread allowed
  - head/helmet/neck hit
  - at most 4 head gibs per network frame
  - then 20% of the health at that moment every 1 s
- **Weapon block:** WaW blocks any pistol class (`waw:1478`); BO1 blocks only `m1911_zm` (`bo1:2284`) [V].
- **How the head comes off:**
  - WaW attaches `char_ger_honorgd_zomb_behead` [V].
  - BO1 detaches the head (and hat), attaches the character's `torsoDmg5` if set, and calls engine `gib("normal")`
    with the head piece index (`bo1:2172-2193`) [V].
  - BO1's damage-over-time passes the means of death and the damage location (`:2196-2215`) [V].

**Limb gib and crawler:**
- **Same as Der Riese:**
  - The location → refs table (legs only on a killing hit; `none` + explosive → closest gib tag).
  - The crawler rule (a leg ref on a non-killing hit) (`bo1:2341-2440`, `waw:1570-1660`) [V].
- **Crawler pick** (the same in both; Der Riese already differs from Nacht's 3) (`bo1:2441-2520`) [V]:
  - `no_legs`: `crawl_hand_1` / `_2` (`ai_zombie_walk_on_hands_a/b`) 50/50, with death `crawl_death_v1`.
  - Other leg refs: uniform over `crawl1..5`:

    | crawl | anim | death |
    |---|---|---|
    | crawl1 | `ai_zombie_crawl` | `crawl_death_v1` |
    | crawl2 | `crawl_v1` | `crawl_death_v2` |
    | crawl3 | `crawl_v2` | `crawl_death_v1` |
    | crawl4 | `crawl_v3` | `crawl_death_v2` |
    | crawl5 | `crawl_v4` | `crawl_death_v1` |

  - `crawl6` (`crawl_v5`) and `crawl_sprint1..3` are in both tables but never assigned [V].
- **BO1 addition:** `setPhysParams(15, 0, 24)` on becoming a crawler (`bo1:2450`) [V]. [I] This shrinks the collision
  capsule (radius 15, height 24).
- **Unchanged:** the stand → crawl transition (`ai_zombie_shot_leg_right_2_crawl` in the stand set,
  `_left_2_crawl` in the crouch set, `bo1cz:animscripts/zombie_combat.gsc:97, 110, 151`), crawl idles
  (`:149-150`), and `ai_gib_bothlegs_gib` when the legs go on the killing hit (`bo1:…spawner.gsc:2810-2812`) [V].
- **Limb models:** BO1 swaps the torso and legs to the character's `torsoDmgN` / `legDmgN` and throws gib pieces by piece
  index (`bo1cz:animscripts/zombie_death.gsc:1508-1600`) [V]. WaW used per-model attaches [I, not compared in depth].
- **`make_crawler()`** (`bo1:…spawner.gsc:3933-4038`) forces a random right/left leg crawler. Nothing in `bo1:maps`
  calls it [V].

## BO1 xanim timings [M]

Dumped from the installed BO1 zones: `zombie_theater.ff` with `common_zombie.ff` loaded, bound to `c_ger_honorguard_body1`
(257 clips). Same conventions as the T4 tables: seconds at 30 fps, root motion as (forward, side, up).

**Clips shared with WaW measure the same.** That covers all the walk, run and sprint cycles, `walk_v6..v9`,
`run_v2..v4`, the crawl cycles, `door_tear_*`, `attack_*`, `walk_attack_v1..v3`, `run_attack_*`, `traverse_v1/v2/v4..v7`,
`traverse_crawl_v1` (the 7.667 s version) and the Der Riese jump-downs. So the T4 tables apply to BO1 unchanged. The
one difference found: `ai_zombie_crawl_v1` is 4.067 s and 58.2 units in BO1 (14.3 u/s), against 55.7 units (13.7 u/s) in
Nacht.

### New in BO1

| anim | length | notes | root motion |
|---|---|---|---|
| `ai_zombie_run_v1` | 1.900 | loop | 228.0 fwd, **120.2 u/s** |
| `ai_zombie_walk_attack_v4` | 1.467 | `fire` 0.633 | 71.1 fwd, 48.6 u/s |
| `ai_zombie_traverse_v3` | 3.567 | gravity on 3.233, blend 3.367 | 75.3, 5.5, 0 |
| `ai_zombie_jump_down_40` | 1.033 | gravity on 0.800, land 0.867 | 32.0, −2.9, −38.8 |
| `ai_zombie_jump_down_240` | 1.300 | gravity on 1.033, land 1.067 | 56.7, −1.4, −240.0 |
| `ai_zombie_jump_down_286` | 1.300 | gravity on 1.133, land 1.200 | 56.7, −1.4, −286.2 |
| `ai_zombie_crawl_jump_down_97` | 1.367 | gravity on 1.067, land 1.133 | 70.4, 0.1, −97.1 |
| `ai_zombie_crawl_jump_down_127` | 1.333 | gravity on 1.033, land 1.100 | 77.9, 0.3, −127.1 |
| `ai_zombie_crawl_jump_down_184` | 1.300 | gravity on 1.133, land 1.167 | 72.9, 0.2, −184.1 |
| `ai_zombie_crawl_jump_down_189` | 1.300 | gravity on 1.167, land 1.200 | 72.9, 0.2, −189.1 |
| `ai_zombie_quad_jump_down_128` | 1.500 | none | 90.5, 0, −128.1 |
| `ai_zombie_walk_on_hands_shot_a` | 5.067 | `fire` 1.133 | none |
| `ai_zombie_walk_on_hands_shot_b` | 2.167 | `fire` 0.800 | none |

- `run_v1` is in the table but never picked (§2 above), so in practice no BO1 runner reaches 120 u/s.
- `jump_down_222`, `jump_up_222` and the `crawl_jump_down_120/222/240/286` clips aren't in these two zones. They live
  in other maps' zones and aren't measured.

### Window clips

**Board tear,** standing: `board` time / length per attack spot (m/r/l = spot 0/1/2) and chunk noteworthy 1-6:

| spot | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| m | 1.87 / 3.13 | 1.47 / 3.17 | 1.07 / 2.83 | 1.70 / 3.00 | 1.40 / 2.83 | 1.47 / 2.83 |
| r | 1.63 / 2.83 | 1.30 / 2.50 | 1.20 / 2.50 | 1.67 / 3.17 | 1.77 / 3.33 | 1.33 / 2.67 |
| l | 1.27 / 2.30 | 1.20 / 2.57 | 1.57 / 3.07 | 1.50 / 3.00 | 1.40 / 2.63 | 1.10 / 2.50 |

**Board tear,** crawler (`boardtear_crawl_*`):

| spot | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| m | 1.90 / 3.40 | 3.33 / 4.87 | 4.37 / 5.57 | 4.40 / 5.90 | 2.83 / 4.40 | 1.47 / 3.10 |
| r | 3.13 / 4.40 | 2.93 / 4.43 | 3.80 / 5.03 | 3.77 / 5.00 | 4.13 / 5.33 | 4.13 / 5.70 |
| l | 1.80 / 2.80 | 2.17 / 3.13 | 2.03 / 3.53 | 3.00 / 5.10 | 2.07 / 3.30 | 1.10 / 2.50 |

- None of these has root motion.
- **Bar tear** (`bartear_*`, `bar` notetrack) mostly reuses these timings:
  - On the l and r spots, noteworthy 4 and 5 swap.
  - On m, 4 and 5 are near-swaps (`bar` 1.37 / 1.73 against `board` 1.40 / 1.70), and m_1's `bar` is at 1.90.
  - The crawler bar tears match the crawler board tears exactly.
- A standing zombie removes a board every **2.3-3.3 s**. A crawler takes **2.5-5.9 s**, so crawlers tear about half as
  fast.

**Other window clips:**

| anim | length | notetracks |
|---|---|---|
| `ai_zombie_bar_bend_m_1` / `_m_2` | 3.333 / 2.833 | `bar_bend` 1.933 / 1.667 |
| `ai_zombie_bar_bend_r` / `_r_2` | 3.167 / 2.833 | `bar_bend` 1.800 / 1.667 |
| `ai_zombie_bar_bend_l` / `_l_2` | 2.300 / 3.400 | `bar_bend` 1.300 / 2.100 |
| `ai_zombie_door_pound_v1` | 4.667 | `board` 0.467, 1.267, 1.900, 2.467 |
| `ai_zombie_door_pound_v2` | 2.700 | `board` 1.033, 1.633 |
| `ai_zombie_door_tear_v1` / `_v2` | 9.200 / 11.767 | no `board` notetrack |
| `ai_zombie_window_attack_arm_l_out` | 2.267 | `fire` 0.300, 1.500 |
| `ai_zombie_window_attack_arm_r_out` | 2.833 | `fire` 0.367, 2.233 |
| `ai_zombie_window_attack_crawl_l` / `_m` / `_r` | 5.633 / 4.867 / 5.833 | `fire` 2.733 / 2.367 / 3.200 |

- `door_pound_v1` has 4 `board` notes. In BO1, on a glass `repair_board`, each one is a chance to break a piece [I].
- **`door_tear_v1/v2` have no `board` notetrack.** They're in BO1's random-of-8 fallback (§3), so a zombie that picks
  one removes nothing for 9-12 s [I: from the notetrack list; not seen in game].
- The reach-in arm attacks hit twice each, about 1.2-1.9 s apart.

## Not verified

- **Map-only clips.** `jump_down_222`, `jump_up_222` and the `crawl_jump_down_120/222/240/286` clips need a dump of the
  map zones that carry them. Everything else is measured (see "BO1 xanim timings").
- **`zombie_mantle_over_40` in common.** It's only confirmed for Kino. Whether `common_zombie` ships its own copy for
  other maps wasn't checked (the dump's traverse folder doesn't have it).
- **`PushPlayer`.** The player-blocking effect of BO1 not calling it.

---

# One Reforged ruleset [I: design picks]

- **Speed class:** keep the roll (S to S + 34, cut at 35 and 70). Make S per round data, with the WaW preset (N − 1) × 8.
  Store the class on the actor, since melee, window and rise anims all read it.
- **Move speed from the clip:** speed = root delta ÷ length × play rate. Keep a per-actor play-rate multiplier for burn
  (0.8) and any later slows. Don't store speeds as script constants.
- **Cycle sets per map in data:** Nacht's 4/3/2/3 set and Der Riese's larger set, each with a weight per entry (Der
  Riese's off-by-one picks become weights of 0).
- **Last-zombie sprint:** a director flag, on from round 4 for the Der Riese preset, off for Nacht.
- **Traversals:** map each negotiation node's `animscript` name to a small table of (anim per has_legs / speed class). Fit
  nothing at runtime, since WaW doesn't either.
- **Crawlers:** keep the kill-only rule for direct leg hits. It decides how often crawlers appear, so it matters for
  feel.
- **BO1 preset:** speed multiplier from the difficulty table (8 on the default), last-zombie sprint in rounds 4-9 only,
  and windows keyed by chunk type (`script_parameters`), not height. Give WaW chunks a default type (`classic_boards` /
  `board`) at load, so one tear rule serves both games.
- **Zombie hit damage:** 60 in both presets, reached two ways. WaW: weapon meleeDamage 150 × 0.4. BO1: scripted 60, with
  the engine's 0.4 scaling a value the script then discards. Keep one `zombie_hit_dmg` number per preset.
