# T4 shooting: hit boxes, location damage, penetration, spread

Step 3 of Nacht (shooting). This is how a player's bullet finds a zombie, what each hit location is worth, how far a
bullet goes through things, and the hip/ADS cone for the Nacht start weapons.

It builds on:
- `zombies_t4_nacht_ai.md` §3: script extras on hits, and gibs
- `zombies_t4_nacht.md`: zombie health per round, and points
- `nacht_weapons_economy.md` §1: falloff, and the weapon table

Tags:
- **[V]**: read in the zone data, a raw file, or `t4sp.exe` (address given). All reads were static; nothing was run.
- **[M]**: measured in game. **None yet.**
- **[I]**: inferred. Treat as a guess until checked.

Sources:
- `nazi_zombie_prototype.ff`, inflated and parsed in scratch for the xmodel records (layout from OAT's T4 `XModel`)
- `common.ff` raw files `info/ai_lochit_dmgtable` and `info/bullet_penetration_sp`
- the zone's raw weapon files
- Plutonium `t4sp.exe`, read-only disassembly

## 1. How a bullet finds a hit location

### The zombie has no collision mesh, only per-bone boxes [V]

`char_ger_honorgd_body1_1` (the Nacht zombie body) has 73 bones, `numCollSurfs` 0 and `contents` 0. Its bounds are
(−9.4, −20.8, −0.1) to (14.5, 20.8, 62.6) and its radius is 62.8. The attached heads (`char_ger_honorgd_zombiehead*`)
also have 0 coll surfs. The only hit geometry is each bone's `XBoneInfo`:
- `bounds[2]`: a box in bone space, with X along the bone
- `offset`: the box centre. In every record I checked, it is exactly (min + max) / 2.
- `radiusSquared`: |half-extent|²

### The trace [V] (`t4sp.exe`)

- **Bone mask** (`0x609a00`):
  - Walks every model in the DObj, so the body **and the attached head** both count.
  - Bones with `radiusSquared` < 4 (radius < 2, constant at `0x83ec68`) are skipped, so all finger bones are out.
  - Bones in the hidden-part bits (`+0x50`) are skipped.
- **Per-bone test** (`0x609c20`):
  - Each kept bone's box centre is moved by the animated bone matrix (`0x455b20`).
  - The ray is rejected against the radius first, then tested against the box.
  - The closest hit wins. It records the fraction, the bone index and the bone name.
- **Caller** (`0x5ab060`):
  - Builds the mask, gets the skeleton (`0x54de20`) and runs the trace.
  - Keeps the hit if it's closer than the trace so far.
  - It's reached from `0x593db6` [I: the server's entity clip, so bullets come through here].
- **Hit location = `partClassification[hit bone]`** [I that the lookup sits in the caller; the per-bone table itself is
  V, below].

So E115 should do this: animate the skeleton, build one oriented box per bone with radius ≥ 2 (body and head models),
ray-test, take the closest, then map the bone to its location.

### Bone → hit location [V] (`partClassification` of `char_ger_honorgd_body1_1`)

The hitloc enum order is: none 0, helmet 1, head 2, neck 3, torso_upper 4, torso_lower 5, r/l arm upper 6/7,
r/l arm lower 8/9, r/l hand 10/11, r/l leg upper 12/13, r/l leg lower 14/15, r/l foot 16/17, gun 18.

| location | bones |
|---|---|
| helmet | `j_helmet` |
| head | `j_head`, `j_head_end` |
| neck | `j_neck` |
| torso_upper | `j_spineupper`, `j_spine4`, both clavicles, both shoulderraise, `tag_inhand`, `tag_stowed_back`, `tag_weapon_chest` |
| torso_lower | `j_mainroot`, `j_spinelower` |
| arm upper | `j_shoulder_*`, `j_elbow_bulge_*`, `j_shouldertwist_*` |
| arm lower | `j_elbow_*`, `j_wristtwist_*` |
| hand | `j_wrist_*`, all finger bones |
| leg upper | `j_hip_*`, `j_hiptwist_*` |
| leg lower | `j_knee_*`, `j_knee_bulge_*` |
| foot | `j_ankle_*`, `j_ball_*` |
| gun | `tag_weapon_left`, `tag_weapon_right` |
| none | `tag_origin`, `tag_sync` |

In the head model (`zombiehead1_2`):
- every face bone is head
- `j_neck` is neck
- `j_helmet` is helmet
- `j_spine4` is **none** (multiplier `locNone`, 1 on all Nacht guns)

### Box sizes [V] (bone space, units; only bones with radius ≥ 2, the ones the trace keeps)

Body `char_ger_honorgd_body1_1`:

| bone | loc | min | max | radius |
|---|---|---|---|---|
| `j_mainroot` | torso_lower | (−3.9, −6.5, −8.2) | (2.4, 6.5, 8.2) | 10.9 |
| `j_spinelower` | torso_lower | (−6.0, −5.5, −7.7) | (4.9, 5.7, 7.7) | 11.0 |
| `j_spineupper` | torso_upper | (−1.5, −5.4, −6.9) | (5.0, 5.0, 6.9) | 9.2 |
| `j_clavicle_le` / `_ri` | torso_upper | (−1.9, −3.9, −5.0) / (−6.8, −3.9, −2.6) | (6.6, 3.9, 2.7) / (1.7, 3.9, 5.1) | 7.0 |
| `j_neck` | neck | (−2.1, −3.4, −2.7) | (2.2, 2.7, 2.7) | 4.6 |
| `j_head` | head | (−1.0, −4.7, −3.5) | (7.8, 4.0, 3.5) | 7.1 |
| `j_helmet` | helmet | (−1.7, −1.6, −3.2) | (2.6, 1.6, 0.0) | 3.1 |
| `j_shoulder_le` / `_ri` | arm upper | (−0.3, −2.5, −2.5) / (−12.2, −2.5, −2.5) | (11.5, 2.5, 2.5) / (0.6, 2.5, 2.5) | 6.9 / 7.3 |
| `j_elbow_le` / `_ri` | arm lower | (0, −2.4, −2.5) / (−10.4, −2.3, −2.1) | (10.3, 2.3, 2.1) / (0, 2.4, 2.5) | 6.1 |
| `j_wristtwist_le` / `_ri` | arm lower | (−0.4, −1.1, −1.0) / (−2.3, −1.6, −1.2) | (2.2, 1.6, 1.2) / (0.4, 1.1, 1.0) | 2.1 / 2.2 |
| `j_wrist_le` / `_ri` | hand | (−1.4, −1.1, −2.0) / (−4.3, −1.4, −2.1) | (4.1, 1.4, 2.1) / (0.7, 1.1, 2.0) | 3.6 / 3.5 |
| `j_hip_le` / `_ri` | leg upper | (0, −4.3, −3.8) / (−19.1, −4.3, −3.8) | (19.1, 4.3, 3.8) / (0, 4.3, 3.8) | 11.1 |
| `j_knee_le` / `_ri` | leg lower | (−1.8, −3.7, −3.0) / (−16.1, −3.7, −3.0) | (16.1, 3.7, 3.0) / (1.8, 3.7, 3.0) | 10.1 |
| `j_ankle_le` / `_ri` | foot | (−0.2, −3.3, −2.2) / (−4.7, −9.5, −2.2) | (4.7, 9.6, 2.2) / (0.2, 3.2, 2.2) | 7.2 |

Head `zombiehead1_2` (`1_1` is the same rig, but my scan didn't pin its record):

| bone | loc | min | max | radius |
|---|---|---|---|---|
| `j_spine4` | none | (0, −2.0, −3.4) | (10.1, 3.6, 3.4) | 6.7 |
| `j_neck` | neck | (0, −2.0, −2.5) | (0.9, 3.4, 2.5) | 3.7 |
| `j_head` | head | (−2.1, −4.7, −3.8) | (8.1, 6.3, 3.8) | 8.4 |
| `j_jaw` | head | (−2.2, −4.7, −2.8) | (2.2, 0, 0) | 3.5 |

Notes:
- **Bones with no box:** the twist bones, `j_ball_*`, `tag_*` and `j_head_end` have radius 0.
- **Overlaps:** the head's own `j_head` box (r 8.4) overlaps the body's (r 7.1). Either one gives "head".
- **E115 takes these straight from the zone.** zonedump writes them as node `e115_hitboxes` ([zonedump_formats.md](../../../../shared/notes/e115/zonedump_formats.md)) and
  `physics/HitTest` traces them. The re-exported `char_ger_honorgd_body1_1` + `zombiehead1_1` matches both tables above
  to 0.1 units, so `zombiehead1_1`'s record is the same as `1_2`'s **[V-data]**.

## 2. Location damage multipliers

### The engine rule for damage to an actor [V] (`G_Damage`-like `0x4f5d70`, block `0x4f5f59-0x4f6006`)

This applies when the target has an actor (`ent+0x184`) and the means of death isn't melee (MOD 7):

1. **Weapon index 0** → `info/ai_lochit_dmgtable[hitloc]` (table at `0x173c678`, loaded at `0x4f53a0-0x4f5427`).
2. **Bullet weapon** (`weapDef+0x144` == 0, so `weaponType bullet`) → the weapon's own `loc*` multiplier
   (`weapDef+0x930 + 4·hitloc`).
3. **Anything else** (grenade, projectile, and so on) → `ai_lochit_dmgtable[hitloc]`.
4. **`zombiemode` dvar on and the actor's type is 1 (`dog`)** → multiplier = min(multiplier, 1.0).
   - The type field is the actor's first script field `type` at `actor+8` (field table `0x83d0c8`).
   - The type names table is `0x8dc46c`: 0 `human`, 1 `dog`.
   - Nacht zombies are `human`, so they take full head multipliers.
5. **Multiplier 0** → no damage at all; the function returns. So `locGun` 0 means shots to the weapon tags do nothing.
6. **Otherwise**, damage = int(damage × multiplier), at least 1.

`ai_lochit_dmgtable` [V], used for non-bullet weapons, no-weapon damage and melee-less cases:

| none | helmet | head | neck | torso up/low | arm up/low | hand | leg up/low | foot | gun |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 4 | 4 | 4 | 0.9 / 0.8 | 0.7 / 0.7 | 0.5 | 0.4 / 0.4 | 0.2 | 0 |

### Weapon multipliers [V] (raw weapon files)

| weapon | helmet | head | neck | torso up/low | arm up/low | hand | leg up/low | foot |
|---|---|---|---|---|---|---|---|---|
| `zombie_colt` | 3.5 | 3.5 | 3.5 | 1.25 / 1.1 | 0.85 / 0.6 | 0.35 | 0.85 / 0.6 | 0.35 |
| `kar98k` | **1** | 3.5 | 3.5 | 1.8 / 1.7 | 1 / 1 | 0.7 | 1 / 1 | 0.7 |
| `kar98k_scoped_zombie` | 3 | 10 | 5 | 2.25 / 2.25 | 0.8 | 0.8 | 0.8 | 0.8 |
| `ptrs41_zombie` | 3 | 10 | 5 | 2.25 / 2.25 | 2 / 1 | 1 | 1 / 1 | 1 |
| `m1garand` | 2.7 | 2.7 | 2.7 | 1.25 / 1.25 | 0.8 / 0.7 | 0.6 | 0.8 / 0.7 | 0.6 |
| `thompson` | 4 | 4 | **1** | 1 | 1 | 1 | 1 | 1 |
| `doublebarrel` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

- `locNone` is 1 and `locGun` is 0 on all of them.
- The full set for all 44 weapons is in `weapons.json` (0 disagreements, economy doc §0).
- Note **kar98k helmet = 1 but head = 3.5**: the small `j_helmet` box on top of the head is a weak spot for it.

### Script overrides [V]

- **None on the multiplier.** No `_zombiemode*` script hooks actor damage before the engine applies it. There is no
  actor damage callback override. `player_damage_override` (`_zombiemode.gsc:1651`) is for players only.
- **The script reacts after the hit** (AI doc §3):
  - extra grenade and projectile damage
  - fire
  - insta-kill
  - points by location on the kill (`zombies_t4_nacht.md`, score table: head 100, neck 70, torso 60, limbs 50)
- **Head and neck gib rules** are AI doc §3 "Gibs":
  - needs ≤10% health, a rifle/pistol/spread bullet, a non-pistol weapon, and a head/helmet/neck hit
  - then damage over time, 20% of current health every 1 s
  - so the starting `zombie_colt` **never** head-gibs

## 3. Bullet penetration

### Per-shot flow [V] (`t4sp.exe`)

- **Per pellet** (`0x4e6b46-0x4e6ba7`):
  - If `bullet_penetrationEnabled` (default **true**, `0x4ffad9`) and the weapon's `penetrateType` (`weapDef+0x14c`)
    isn't none, it goes the penetrating route `0x4e61f0`.
  - Otherwise it goes the single-hit route `0x4e6100`.
- **Penetrating route** `0x4e61f0`:
  1. Trace (`0x4e5b80`) and apply the first hit (`0x4e5d10`).
  2. Loop up to `penetrationCount` times. That's dvar `0x2fcda8c`, an int, default **2**, range 0-5 (`0x632f8c`).
  3. **Entry depth** = `pen_table[penetrateType][surfaceType]` (`0x41ccb0`, 4 rows × 31 floats at `0x8f6db8`).
     - Row 0 (none) is all zeros, and surface type 0 gives 0.
     - The depth is × a perk dvar (`0x8f64a8`) if the shooter's client has perk bit 6 (`client+0x20a8`).
       [I: this is `specialty_bulletpenetration` with `perk_bulletPenetrationMultiplier` 2. Nacht has no perks.]
     - Depth ≤ 0 → stop.
  4. **Stop if the thing just hit was a player** (`hitEnt->client`). Also stop if it was an actor **and the shooter is
     an actor** (`0x4e6374-0x4e6391`). So **a player's bullet carries on through zombies**; AI bullets don't.
  5. Find the exit with a back-trace. Thickness = |exit − entry|, at least 1.0.
     - If there's an exit surface, depth = min(entry depth, exit depth).
  6. **`damageMultiplier -= thickness / depth`** (`bp+8`, `0x4e66d1-0x4e66e6`). At ≤ 0 → stop.
  7. Spawn FX past `bullet_penetrationMinFxDist` (30, `0x40f76b`), then apply the next hit with the reduced
     multiplier.
- **Each later hit's damage is scaled by the remaining multiplier** [I: applied inside `0x4e5d10` like CoD4's
  `Bullet_Process`].

### Depths [V] (`info/bullet_penetration_sp`; units of material per unit of damage multiplier)

| surface | small | medium | large |
|---|---|---|---|
| **flesh** | 32 | 96 | 128 |
| wood | 72 | 128 | 192 |
| brick / concrete / rock | 0 / 0 / 0 | 24 / 8 / 36 | 64 / 24 / 48 |
| metal / painted metal | 4 / 4 | 8 / 8 | 16 / 16 |
| plaster | 16 | 48 | 128 |
| dirt / grass / mud | 72 / 72 / 0 | 72 / 72 / 96 | 72 / 72 / 128 |
| glass / foliage / paper / plastic / fruit | 192 | 192 | 192 |
| carpet / cloth | 20 | 20 | 20 |
| cushion / rubber | 8 | 24 | 32 |
| sand / snow / ice / water | 0 | 32 / 128 / 96 / 128 | 32 / 128 / 128 / 128 |
| bark / gravel / asphalt / ceramic | 0 / 32 / 0 / 0 | 36 / 32 / 24 / 192 | 48 / 32 / 32 / 192 |

The Nacht weapons' `penetrateType` [V]:
- small: `zombie_colt`
- medium: `kar98k`, `kar98k_scoped_zombie`, `m1garand`, `thompson`, `doublebarrel`
- large: `ptrs41_zombie`
- none: `ray_gun` (a projectile)

### Multiple zombies per bullet [V rule, I numbers]

Yes, up to 1 + `penetrationCount` = **3 hits per bullet**, while the multiplier lasts.
- **Kar98k** (medium flesh 96): a torso about 13-16 units thick costs about 0.15 per zombie, so the second zombie takes
  about 85% damage [I: thickness depends on which boxes the exit trace crosses].
- **Colt** (small, 32): the same body costs about 0.45.
- **Walls and cover:** brick and concrete stop small rounds dead (depth 0). Wooden boards (wood 72/128/192) let all
  three types through.

The non-penetrating route `0x4e6100` still continues past some surfaces (a surface flag `0x10` check, and a vehicle case
that scales the multiplier). It isn't used by any Nacht bullet weapon, because they all have a `penetrateType`.

## 4. Health and points (cross-reference only)

- **Zombie health:** `zombies_t4_nacht.md` "Zombie health".
  - It starts at 150 and goes up 100 per round to round 9.
  - From round 10 it goes up 10% per round.
- **Points per hit and per kill by location:** `zombies_t4_nacht.md` score table.
  - 10 per hit.
  - Kill: 50 + head 50, neck 20, torso 10, melee 80, burned 10.
- **Worked examples** [I arithmetic from the above]:
  - Colt head = 20 × 3.5 = 70, so a round-1 zombie (150) needs 3 head shots or 6 upper-torso shots (25 each).
  - Kar98k head = 350, a one-shot kill to the head up to round 3 (health 350).

## 5. Spread: `zombie_colt` and `kar98k` [V fields]

| field | `zombie_colt` | `kar98k` | `kar98k_scoped_zombie` |
|---|---|---|---|
| `hipSpreadStandMin` / `DuckedMin` / `ProneMin` | 3 / 2.5 / 2 | 8 / 7.5 / 7 | 8 / 7.5 / 7 |
| `hipSpreadMax` / `DuckedMax` / `ProneMax` | 6 / 5 / 4 | 10 / 9.5 / 9 | 10 / 9.5 / 9 |
| `hipSpreadDecayRate` | 4 | 5 | 5 |
| `hipSpreadFireAdd` | 1 | 1 | 1 |
| `hipSpreadMoveAdd` | 4.5 | 5 | 5 |
| `hipSpreadTurnAdd` | 0 | 0 | 0 |
| `hipSpreadDuckedDecay` / `ProneDecay` | 1 / 1 | 1 / 1 | 1 / 1 |
| `adsSpread` | 0.2 | 0.05 | 0 |
| ADS in / out (s) | 0.245 / 0.25 | 0.2 / 0.4 | 0.3 / 0.4 |

How these combine [I: the CoD4-line rule; T4 code not read yet]:
- **Hip spread** = min + (max − min) × `aimSpreadScale`. The min and max pick the stance's pair, in degrees.
- **`aimSpreadScale`** (0-1):
  - goes up by `FireAdd` per shot, by `MoveAdd` × speed fraction while moving, and by `TurnAdd` × turn rate
  - decays at `DecayRate` per second, × the ducked/prone decay factor
- **ADS:** spread lerps to `adsSpread` by the ADS fraction.
- **The shot direction** is a random point in a disc of radius tan(spread) at unit distance.

So the kar98k's hip cone is 8-10°, nearly useless, and ADS is 0.05°. The colt's hip cone is 3-6°.

## Open

- [I] The spread formula (§5): read T4's spread function to confirm it.
- [I] The hitloc lookup in `0x5ab060` / `0x593db6`. The `0x609c20` per-bone "class ≥ min" check (`0x609ecf`) isn't
  decoded yet.
- [I] How the remaining `damageMultiplier` scales damage inside `0x4e5d10`.
- [M] All of it in game: head vs helmet hits, collateral counts, how much brick and wood stop.
