# Nacht: weapons, box, economy, damage feedback, grenades, game over

The player-facing gameplay gaps for M2's solo Nacht loop. This builds on `zombies_t4_nacht.md` (rules, prices) and
`zombies_t4_nacht_ai.md` (hits on zombies, player health and regen). Where those docs already answer a point, this one
points to them.

Tags:
- **[V]**: read in the source, with a file:line or a `t4sp.exe` address.
- **[I]**: inferred. Treat as a guess until checked.

Sources:
- Effective scripts (patch.ff overrides first, see the rules doc):
  - from `patch.ff`: `maps/_zombiemode_prototype.gsc`, `nazi_zombie_prototype.gsc`
  - from the zone: `maps/_zombiemode_weapons.gsc`
  - from `common.ff`: `maps/_gameskill.gsc`, `mp/zombiemode.csv`
- Weapon files are the zone's raw weapon assets. No script text is copied here.

## 0. weapons.json cross-check [V]

I compared our zonedump's `weapons.json` with the raw zone weapon files for all 44 weapons, on these fields:
- damage, min damage, both ranges, melee damage
- fire, rechamber, raise, drop, all reload times, ADS in/out
- clip, start and max ammo
- explosion radius and inner/outer damage
- the head multiplier

**There are 0 disagreements.** weapons.json is a faithful source for weapon data. This doc uses the same raw files.

## 1. Weapon handling

### Damage model

- **Base and falloff** [V for the fields, I for the formula]:
  - Full `damage` out to `maxDamageRange`.
  - Then linear down to `minDamage` at `minDamageRange` and beyond.
  - The interpolation itself is engine code, the standard CoD4-line rule (AI doc §3).
- **Hit location** [V fields]: × the weapon's `loc<Part>` multiplier.
  - **Head and helmet are 4 on SMGs** and 2.7-3.5 on most rifles and pistols.
  - They are **1 on shotguns** and 0 on explosives and the ray gun.
  - `locGun` is 0.
- **Shotguns** fire `shotCount` 8 pellets. Each pellet gets the full falloff.
- **Script extras on zombies** are in AI doc §3: insta-kill, the score per hit location, gibs and the like.

### The Nacht weapon set [V] (raw weapon files)

Damage is max→min over the range in units. "head" is `locHead`. Times are in seconds, ammo is clip / start / max, and
"move" is `moveSpeedScale` / `adsMoveSpeedScale`.

| weapon | fire type | damage (range) | head | fire time | reload / empty | ADS in/out | ammo | move |
|---|---|---|---|---|---|---|---|---|
| `zombie_colt` (start) | semi | 20→20 (425-1000) | 3.5 | 0.075 | 1.9 / 2.65 | 0.245 / 0.25 | 8 / 40 / 80 | 1 / 1.5 |
| `sw_357` | semi | 1000→300 (384-1500) | 1.5 | 0.32 | 3 / 3 | 0.245 / 0.25 | 6 / 80 / 80 | 0.9 / 1.2 |
| `kar98k` | bolt (rechamber 1.0) | 100→80 (1200-2200) | 3.5 | 0.33 | 2.5 / 2.5 | 0.2 / 0.4 | 5 / 50 / 50 | 0.9 |
| `springfield` | bolt (1.0) | 100→80 (1200-2200) | 2 | 0.33 | 3.2 / 3.2 | 0.2 / 0.4 | 5 / 50 / 50 | 0.9 |
| `m1carbine` | semi | 68→50 (1024-2400) | 2.7 | 0.135 | 2.9 / 3.7 | 0.3 / 0.4 | 15 / 120 / 120 | 0.9 |
| `m1garand` | semi | 68→50 (1024-2400) | 2.7 | 0.135 | 3.4 / **1.6** (empty is faster, en-bloc) | 0.25 / 0.25 | 8 / 96 / 128 | 0.9 |
| `gewehr43` | semi | 90→50 (1024-2400) | 2.7 | 0.125 | 3 / 4 | 0.3 / 0.4 | 10 / 96 / 120 | 0.9 |
| `kar98k_scoped_zombie` | bolt (1.2) | 300→300 (4000-5000) | 10 | 0.33 | per round: start 1.8, 0.6 each, end 0.77 | 0.3 / 0.4 | 5 / 50 / 50 | 0.9 / 0.75 |
| `ptrs41_zombie` | semi | 1000 | 10 | 0.8 | 4 / 5.3 | 0.4 / 0.6 | 5 / 30 / 60 | 0.75 |
| `thompson` | auto | 120→80 (800-1800) | 4 | 0.08 | 2.1 / 2.45 | 0.22 / 0.3 | 20 / 200 / 200 | 1 / 1.3 |
| `mp40` | auto | 100→60 (800-1800) | 4 | 0.112 | 2.3 / 2.9 | 0.25 / 0.3 | 32 / 192 / 192 | 1 / 1.3 |
| `stg44` | auto | 100→70 (1024-2400) | 2.7 | 0.112 | 2.15 / 2.8 | 0.35 / 0.4 | 30 / 180 / 180 | 1 / 1.3 |
| `bar` | auto | 100→85 (1024-2400) | 2.7 | 0.16 | 2.75 / 3.25 | 0.32 / 0.37 | 20 / 140 / 140 | 1 / 0.85 |
| `fg42_bipod` | auto | 100→85 | 2.7 | 0.064 | 2.4 / 3.5 | 0.22 / 0.4 | 32 / 192 / 192 | 0.8 |
| `mg42_bipod` | auto | 130→90 | 3 | 0.064 | 4.5 / 4.5 | 0.7 / 0.9 | 125 / 500 / 500 | 0.75 |
| `30cal_bipod` | auto | 130→90 | 3 | 0.096 | 7 / 6 | 0.22 / 0.4 | 125 / 500 / 500 | 0.75 |
| `doublebarrel`, `_sawed_grip` | 8 pellets | 200→15 (256-800) per pellet | 1 | 0.283, rechamber 0.8 | 3 / 4 | 0.24 / 0.29 | 2 / 60 / 60 | 1 / 1.2 |
| `shotgun` (trench) | 8 pellets, pump | 160→15 (256-800) | 1 | 0.283, rechamber 0.8 | per shell: start 0.9, 0.6 each, end 0.95 | 0.24 / 0.29 | 6 / 60 / 60 | 1 / 1.2 |
| `m1garand_gl` | semi (+ launcher) | as m1garand | 2.7 | 0.135 | 3.4 / 1.6 | 0.25 | 8 / 96 / 128 | 0.9 |
| `panzerschrek` | rocket (1 in clip), speed 2100 | 1000 direct; splash r 256, 300→150 | 0 | 0.33 | 2.85 | 0.5 / 0.6 | 1 / 1 / 4 | 0.75 / 0.6 |
| `m2_flamethrower_zombie` | auto (gas) | 30 | 0 | 0.2 | 1.83 | 0.2 / 0.25 | 100 / 100 / 300 | 0.8 / 0.7 |
| `ray_gun` | auto, projectile speed 3200 | 1000 direct; splash r 64, 1500→300 | 0 | 0.33 | 3 | 0.245 / 0.25 | 20 / 160 / 160 | 1 |

Notes:
- No weapon uses burst fire. Fire types are `Single Shot` or `Full Auto`, and there is no `burstCount` key.
- **Fire rate** = 1 / fireTime, plus the rechamber time on bolts and pumps.
- **Movement:** the speed scale applies through CmdScale (see `t4_pmove.md` §3). The colt runs at 1.0, and 1.5 while
  aiming.

## 2. Mystery box [V] (`_zombiemode_weapons.gsc`)

- **Cost:** 950. The charge is the trigger's `zombie_cost` (`:277`), and the hint is built from a default of 950
  (`:253`). Both are 950 on Nacht.
- **Pool:** every weapon registered with `add_zombie_weapon` that the map also `include_weapon`s
  (`:11-15`, `nazi_zombie_prototype.gsc:246-303`, the patch file). On Nacht that is **25 weapons**:
  - sw_357, m1carbine, m1garand, gewehr43, stg44, thompson, mp40, kar98k, springfield
  - ptrs41_zombie, kar98k_scoped_zombie, molotov, stielhandgranate, m1garand_gl, m2_flamethrower_zombie
  - doublebarrel, doublebarrel_sawed_grip, shotgun, fg42_bipod, mg42_bipod, 30cal_bipod, bar, panzerschrek, ray_gun
  - `m7_launcher` is included but never registered, so it can't appear. The patch comments out colt, colt_dirty_harry,
    walther and fraggrenade.
- **The pool includes wall weapons and grenades.** The box can give a kar98k, a thompson or a stielhandgranate.
- **Pick** (`treasure_chest_ChooseRandomWeapon` `:413-453`):
  - **uniform** over the pool, minus anything the player already holds
  - the flamethrower is removed when any player has it (limit 1, `:166`)
  - **no weights**
- **No teddy bear and no box move on Nacht.** Neither exists in the script.
- **Timing:**

  | t (s) | what happens | source |
  |---|---|---|
  | 0 | lid rolls 105° over 0.5 s; `lid_open` and `music_box` play | `:394-402` |
  | 0 | the weapon model rises 40 units over 3 s and starts cycling | `:462-463` |
  | 0 → 3.9 | 40 model swaps: 20 × 0.05 + 10 × 0.1 + 5 × 0.2 + 3 × 0.3 + 2 × 0 = **3.9 s** | `:472-497` |
  | 3.9 | the trigger is re-enabled; **12 s to take it**, only by the buyer | `:319-321`, `:389` |
  | grab or timeout | lid closes over 0.5 s. On a timeout the model sinks over 0.3 s | `:405-411`, `:507-513` |
  | +3 | the box can be used again | `:347` |

- **Give rules** (`treasure_chest_give_weapon` `:531-569`):
  - With 2 primaries, the current one is taken. `zombie_colt` counts as a primary.
  - Grenades and molotovs never replace a gun.
  - The new weapon comes with max ammo (`GiveMaxAmmo`).

## 3. Wall buys and ammo [V]

The price is from `mp/zombiemode.csv`, column 1, rounded up to 10 (`_zombiemode_weapons.gsc:11-27`). The csv has **no
ammo column**, so ammo is round_up_to_ten(int(cost × 0.5)) (`:52`).

| wall weapon | price | ammo refill |
|---|---|---|
| kar98k | 200 | 100 |
| m1carbine | 600 | 300 |
| doublebarrel | 1200 | 600 |
| doublebarrel_sawed_grip | 1200 | 600 |
| thompson | 1200 | 600 |
| shotgun | 1500 | 750 |
| bar | 1800 | 900 |
| stielhandgranate | 250 | **250** (grenades charge the full price) |
| cabinet `kar98k_scoped_zombie` | 1500 the first time | 750 |

The cabinet is in the rules doc. Behaviour (`weapon_spawn_think` `:722-823`, `ammo_give` `:898` onwards):
- **The first purchase** reveals the chalk model (`weapon_show`) and switches the hint to "cost / ammo".
- **Ammo is only sold if the reserve is below max.** Otherwise nothing is charged. A refill tops the weapon up to max.
- **Grenade refill quirk:** the affordability check uses the ammo cost (125), but the charge is the full 250 (`:798-810`).
  A player with 125-249 points can buy grenades and go below 250 [I: whether the score can go negative depends on
  `minus_to_player_score`].

## 4. Zombie damage to the player and feedback

### Zombie hit: 60 per swing [V]

This settles AI doc §2's open item.
- The player damage function in t4sp (`0x4f5d70`, at `0x4f5e6b-0x4f5ea8`) applies **one** multiplier by type:
  - **MOD 12:** none.
  - **Radius damage** (`dflags & 1`): `player_radiusDamageMultiplier`, default 1.0.
  - **MOD 7 (melee):** only `player_meleeDamageMultiplier`.
  - **Everything else:** `player_damageMultiplier`.
  - The result is at least 1.
- The dvar pointers are `0x18fb234` (radius), `0x18ecf5c` (melee) and `0x16d70fc` (damage), matched to their
  registrations at `0x4ff8e6-0x4ff980`.
- `_gameskill` sets the melee multiplier to 100/250 = 0.4 (`_gameskill.gsc:428`), at every difficulty.
- **So a zombie swing (kar98k meleeDamage 150) does 150 × 0.4 = 60.** The difficulty's `player_damageMultiplier` does not
  touch it.
- **Two hits is 120 > 100, so two quick hits down a full-health player.** Regen (AI doc §4) is the only way to survive
  a third.
- Melee is MOD 7 in the CoD4 numbering [I].
- **The patched `player_damage_override`** (`_zombiemode_prototype.gsc:1652-1688`) only steps in when the damage is
  ≥ current health. It doesn't change the amount.

### Red overlay [V] (`_gameskill.gsc`)

- **Trigger:** health ratio ≤ `healthOverlayCutoff` (0.2 on Normal, AI doc §4) sets `player_has_red_flashing_overlay`.
  It also starts a blur (`startfadingblur(3.6, 2)`) (`:1300-1312`).
- **The overlay** is the full-screen `overlay_low_health` (640×480), starting at alpha 0 (`healthOverlay` `:1631-1673`).
- **Pulses** (`fadeFunc` `:1872` onwards): each lasts 0.8 s.

  | phase | length |
  |---|---|
  | fade in | 0.08 s |
  | full | 0.8 × (0.1 + 0.2·sev) |
  | half fade | 0.8 × (0.1 + 0.1·sev), to alpha 0.8 + 0.1·sev |
  | out | 0.24 s, to alpha 0.5 + 0.3·sev |

- **The sequence** (`redFlashingOverlay` `:1967-2017`):
  - one pulse at severity 1
  - pulses at 0.9 until `longRegenTime` (5 s) has passed since the overlay started
  - one at 0.65 (×0.8 alpha)
  - one at 0 (×0.6)
  - fade out over 0.5 s, then clear the flag

  Any new damage restarts it. **So the overlay runs about 6.5-7 s after the last hit.**
- **"Get to cover" text:** only on gameskill ≤ 1, early in the map, with no co-op, and when `takeCoverWarnings` > 3
  (`:1933-1955`). [I] It is rarely seen in Zombies.
- **No hit markers.** The SP `_damagefeedback` is off by default (`scr_damagefeedback` 0, `_damagefeedback.gsc:3-12`).
  It is only hooked in dev builds (`_spawner.gsc:1328-1330`, inside `/# #/`).
- **Damage direction indicators** are engine HUD [I, not traced].

## 5. Grenades [V]

| | stielhandgranate | molotov |
|---|---|---|
| fuse | **3.5 s** (`fuseTime`) | 3.5 s |
| cook | **yes** (`cookOffHold` 1) | no (0) |
| explosion | radius **256**, **200** at the centre → **50** at the edge | radius 200, 250 → 40 (fire) |
| throw speed | 940 (`projectileSpeed`) | 940 |
| clip / max | 4 / 4 | 4 / 4 |

**Start count.** `round_start` gives the grenade with 0 in the clip (`_zombiemode_prototype.gsc:950-951`). Round 1's
award then sets it to **2**.

**Refill each round** (`award_grenades_for_survivors` `:1231-1259`), by the fraction of max (4):

| held at round start | becomes |
|---|---|
| 0 | 2 |
| 1 | 3 |
| 2, 3 or 4 | 4 |

In effect it's +2 per round, capped at 4. Players who are zombies are skipped.

**Self-damage** goes through `player_radiusDamageMultiplier`, 1.0 [V, §4]. So a grenade at your feet does up to 200
before falloff [I: the engine falloff shape].

## 6. Game over and last stand (solo) [V]

There is **no usable last stand in solo Nacht.** `player_damage_override` (`_zombiemode_prototype.gsc:1652-1688`):
1. Only runs on damage ≥ current health.
2. Counts players who are this player, a zombie, in last stand or spectating.
3. **Solo, that count is always the whole lobby.** So it:
   - threads `_laststand::PlayerLastStand` (visuals only)
   - runs `player_fake_death` (`:1769` onwards): take all weapons, no stand or crouch (forced prone), zombies ignore the
     player
   - calls `end_game` (`:1690` onwards)

There's no last-stand pistol, because the weapons have just been taken.

The game-over sequence (text, `mx_game_over`, intermission, mission failed) is in `zombies_t4_nacht_flow.md`.
