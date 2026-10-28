# MP rules across T4, T5 and T6 (TDM/FFA vs bots, M4)

One page per topic, with all three games side by side.

Tags:
- **[V]**: read in the source, with path:line.
- **[I]**: inferred, or from general knowledge.

T4 and T5 detail lives in [mp_t4_tdm_ffa.md](../../../games/t4-waw/notes/e115/mp_t4_tdm_ffa.md) (cited as "TDM doc §n"), and the BO1 bot brain in [bo1_bots.md](../../../games/t5-bo1/notes/e115/bo1_bots.md). This
page adds the cross-game view and the new reads below. No script text is copied.

Sources:
- **T4:** WaW `common_mp.ff` / `patch_mp.ff` scripts and raw weapon files.
- **T5:** BO1 `common_mp.ff` / `patch_mp.ff` scripts, weapon files and `mp/statstable.csv`.
- **T6:** BO2 `common_mp.ff` / `patch_mp.ff` / `common_patch_mp.ff`, unlinked with OAT: `mp/scoreinfo.csv`,
  `mp/statstable.csv`, `mp/gametypestable.csv` and the `weapons/*_mp` files. **BO2 MP scripts ship compiled**, so every
  T6 script-side rule is [I] until ACTS decompiles them.

## 1. TDM and FFA defaults

| | T4 | T5 | T6 |
|---|---|---|---|
| time limit | 10 min [V TDM doc §1] | 10 min [V TDM doc §8] | 10 min [I] |
| TDM score limit | 500 (50 kills) [V `tdm.gsc:63-66`] | 7500 (75 kills) [V `tdm.gsc:63-67`] | 7500 [I] |
| FFA score limit | 1000 (200 kills) [V `dm.gsc:54-57`] | 1000 (20 kills) [V `dm.gsc:54-55`] | 30 kills in playlists [I] |
| kill, TDM / FFA | 10 / 5 [V `_rank.gsc:24-33`, `dm.gsc:103-110`] | 100 / 50 [V `_rank.gsc:29`, `:50`, `dm.gsc:125`] | 100 / 100 [V `scoreinfo.csv` row `kill`, tdm/dm score columns] |
| headshot bonus | none (XP only) [V] | not checked | 0 in tdm and dm [V `scoreinfo.csv` row `headshot`] |
| assists 75/50/25 %, TDM | 8 / 6 / 4 | 80 / 60 / 40 | 50 / 25 / 25 [V `scoreinfo.csv` rows `assist_75/50/25`]; FFA 0 |
| tactical assists (flash, concussion, EMP, shock) | | | 50 each in TDM [V `scoreinfo.csv` rows 9-12] |
| UAV / counter-UAV assist | | | 10 [V `scoreinfo.csv` rows 16-17] |
| end conditions | score limit (team or player ≥ limit), else time; equal team scores = tie [V TDM doc §1] | same [V] | same shape [I] |
| overtime | none in TDM/FFA; only sab sets it [V TDM doc §1] | none in TDM/FFA [I: same `_globallogic` shape] | none in TDM/FFA [I] |
| rounds / lives | 1 round, unlimited lives [V] | 1, unlimited, plus a round-win limit dvar (0) [V] | 1, unlimited [I] |

- FFA ties: WaW returns no winner on a shared top score, with placement by score then fewer deaths [V TDM doc §8].
- Reforged pick, already made in the TDM doc §1: BO1's ×100 scale, TDM 7500, FFA 1000. BO2's TDM kill = 100 matches it.
  [I] For one Reforged ruleset: BO2's assist 50/25/25 and the 50-point tactical assists can be a per-profile score table
  over the same events.

## 2. Spawn selection

| | T4 | T5 | T6 |
|---|---|---|---|
| first spawns | `mp_tdm_spawn_<team>_start` (falling back to `mp_sab_spawn_<team>_start`) during the grace period; legacy `_spawnlogic` scoring until the first enemy hit [V TDM doc §2] | same start-spawn rule; `scr_spawn_force_unified` added [V TDM doc §7] | start spawns, then influencers [I] |
| later spawns | unified: engine `getsortedspawnpoints` over influencers, then the first point no enemy can see, sight-checking at most 35 [V TDM doc §2] | same structure, influencers re-tuned: enemy −150 r 2100, friend +10 r 700, no aim cylinder, "enemy spawned here" −200 r 1100 for 7 s [V TDM doc §7] | same architecture [I] |
| FFA | `getSpawnpoint_DM` (ideal 1600, bad 1200) before the first hit, then unified with one "free" pool [V] | same | [I] |
| spawn sight check | from point + 60 z to enemy + 60 z, within 1800 in 2D, with a facing cull at ±0.2; mask `0x806833` [V TDM doc §2, `t4mp 0x521010`] | mask not read | [I] |
| legacy LOS | origin + 50 to the point's trace point; skipped when both face away [V `_spawnlogic.gsc:1970`] | | |

- The influencer maths (curves, the sum, randomness 50) is engine-side; T4 is read in the TDM doc §2 "The engine
  scorer". BO1's "steep" curve formula is still open (TDM doc §7).
- Classnames: `mp_tdm_spawn`, `mp_dm_spawn`, `mp_tdm_spawn_allies_start`/`_axis_start`, `mp_uspawn_point`,
  `mp_global_intermission`; the same names in T5 [V `t5mp` strings]. T6 [I].

## 3. Killstreaks: the 3 defaults

| | earned by | the 3 defaults |
|---|---|---|
| T4 | kills, hard-coded; one held at a time; reset on death [V `_hardpoints.gsc:1328-1372`, TDM doc §4] | 3 Recon Plane (`radar_mp`), 5 Artillery, 7 Dogs (fixed ladder, not chosen) |
| T5 | kills; the player picks 3. Thresholds from `statstable.csv` col 5 [V `_hardpoints.gsc:63`] | rows tagged `all` in col 11 [V `statstable.csv` rows 193, 194, 203]: **Spy Plane 3, Care Package 5, Attack Helicopter 7** |
| T6 | score (scorestreaks). The cost is `statstable.csv` col 16 [V] | rows tagged `all` in col 11 [V rows 199, 205, 210]: **UAV 425, Lightning Strike (`planemortar`) 750, Dragonfire (`qrdrone`) 975** |

- T5 kill counts for the rest, now [V] from `statstable.csv` col 5:
  - Spy Plane 3, RC-XD 3, Counter-Spy 4, SAM 4, Care Package 5, Napalm 5
  - Sentry 6, Mortar 6, Attack Helicopter 7, Valkyrie 7, Blackbird 8, Rolling Thunder 8
  - Chopper Gunner 9, Gunship 11, Dogs 11
  - This replaces the TDM doc §7's [I] list, which matched.
- T6 costs for the rest [V col 16]: RC-XD 450, Hunter Killer 525, Care Package 550, Counter-UAV 600, Guardian 650,
  Hellstorm 700, Sentry 800, Death Machine 850, War Machine 900, AGR 1000, Stealth Chopper 1100, Orbital VSAT 1200,
  Escort Drone 1250, EMP 1300, Warthog 1400, Lodestar 1500, VTOL Warship 1600, Dogs 1700, Swarm 1900.
- `scoreinfo.csv` col 4, "Killstreaks Allowed Score", is TRUE on a few events (e.g. care-package crush, hacked package).
  [I] It marks which kills made *with* a streak still charge the next streak.

## 4. Damage model

**Per bullet** [V weapon fields; I for the engine order]: base damage by range × `loc*` multiplier for the hit
location, then the script callback adjusts it.

### Range falloff

- **T4 and T5:** `damage` up to `maxDamageRange`, then down to `minDamage` at `minDamageRange` [I: linear, as CoD4], and
  `minDamage` beyond.
  - T4 Thompson: 40 → 20 over 750-1000; Kar98k 50 → 40 over 4000-5000; Colt 40 → 20 over 250-500 [V `weapons/*_mp`].
  - T5 AK47: 40 → 30 over 1500-2000; L96A1 flat 70; M1911 40 → 20 over 350-900 [V].
- **T6 adds up to 5 range steps:** `damage`..`damage5` with `damageRange2`..`damageRange5`, plus `minDamage` past
  `minDamageRange` [V fields].
  - AN-94: 40 up to 1300, 33 for 1301-2250, 24 beyond 2251.
  - Five-seven: 55 up to 100, 45 for 101-800, 33 from 801, 24 from 1000, then 19 at 1500.
  - [I] Steps, not a lerp: the ranges are consecutive (1300/1301), which reads like bands.

### Hit-location multipliers

`locHead`, `locHelmet`, `locNeck`, `locTorsoUpper`, `locTorsoLower`, limbs, `locGun` [V weapon files]:

| weapon | head / helmet | neck | upper / lower torso | arms | legs |
|---|---|---|---|---|---|
| T4 SMG/pistol (Thompson, Colt) | 1.4 / 1.4 | 1 | 1 / 1 | 1 | 1 |
| T4 bolt rifle (Kar98k) | 2 / 2 | 2 | 1.5 / 1.5 | 1 | 1 |
| T5 rifle/pistol (AK47, M1911) | 1.4 / 1.4 | 1 | 1 / 1 | 1 | 1 |
| T5 sniper (L96A1) | 2 / 2 | 2 | 1.5 / 1.5 | 1.5 (upper) | 1 |
| T6 AN-94 | **1.2 / 0** | 1 | 1 / 1 | 1 | 1 |
| T6 MP7 | 1.1 / 1 | 1 | 1 | 1 | 1 |
| T6 DSR-50 | 2 / 2 | 1.5 | 1.5 / 1.5 | 1.5 | 1 |
| T6 Five-seven | 1.4 / 1.4 | 1 | 1 | 1 | 1 |

- `locGun` is 0, so a hit on the gun does no damage [V T4].
- T6 tunes heads per weapon and drops AR head multipliers towards 1.

### The headshot rule

- **T4** [V `_globallogic.gsc:5135-5137`]: `MOD_HEAD_SHOT` when the hit location is `head` or `helmet` and the means isn't
  melee, bayonet or impact. MGs count.
- **T5** [V `_globallogic_utils.gsc:480-500`]: the same, but impact counts for the ballistic knife, and auto-turrets
  never headshot.
- **What it changes:**
  - It only renames the means of death (killfeed, medals, XP).
  - The extra damage comes from `locHead` in the engine, not script.
  - The "onlyheadshots" tweakable drops body bullets and sets a headshot to 150 [V T4 `:5763-5769`; T5
    `_globallogic_player.gsc:842-849`].
- **T6:** [I] the same rule. `scoreinfo` pays 0 bonus for `headshot` in tdm/dm [V].

### Perk scaling, after the engine

T4 `cac_modified_damage` [V `_class.gsc:1304-1420`, defaults `:1148-1153`]:
- **Stopping Power:** bullet damage × 1.4 (`perk_bulletDamage` 40). Cancelled when the victim has Juggernaut.
- **Juggernaut:** the victim takes bullet damage × 0.75 (`perk_armorVest` 75).
- **Sonic Boom:** explosive damage × 1.25 (`perk_explosiveDamage` 25), cancelled by Flak Jacket.
- **Flak Jacket:** explosive damage × 0.75, capped at 75 (`perk_flakJacket` / `perk_flakJacketMaxDamage`). It doesn't
  apply to projectile hits or stuck explosives.
- **Fireproof:** fire damage reduced by `perk_fireproof`.

T5 [V `_class.gsc:2024-2029`]:
- `perk_bulletDamage` 35, `perk_armorVest` 80, `perk_explosiveDamage` 25.
- Flak Jacket 35 %, or 9 % in hardcore.
- **BO1's statstable has no `specialty_bulletdamage` or `specialty_armorvest` perk rows**, so only Flak Jacket applies
  in practice [V by grep].

T6: [I] no damage perks besides Flak Jacket.

### Other modifiers

- Friendly fire, `scr_team_fftype` [V T4 `_globallogic.gsc:5233-5303`]:
  - 0: nobody is hurt
  - 1: the friend takes it
  - 2: reflect to the attacker
  - 3: both take half
  - [I] Use 0 for bots.
- Spawn protection: a grenade within 250 of the victim's spawn point in the first 3.5 s does nothing [V T4 `:5846`].

## 5. Bot hooks

- **T4:** none. Only dev testclients that stand still [V TDM doc §5].
- **T5:** Combat Training. Script picks the goals; the engine moves, aims and fires, tuned by `sv_bot*` dvars per
  difficulty (easy / normal / hard / fu) [V `_bot.gsc:402-528`].
  - The full dvar table is in the TDM doc §7, and the engine behaviour in [bo1_bots.md](../../../games/t5-bo1/notes/e115/bo1_bots.md).
  - What difficulty changes: reaction time, fire bursts, yaw/pitch speed, fov, crouch, lead bias, strafe chance,
    grenades on or off, sprint distance, melee distance and help distance.
- **T6:** Combat Training carries over [I]. The scripts are compiled, so the difficulty table isn't read.

## 6. Create-a-Class: attachments and perk slots

The slot groups per weapon (primary, secondary, lethal, tactical) are in ClassTables and the CaC reply. This section is
attachments and perks.

### Attachments

- **T4: one attachment per weapon.**
  - The pick must be in the weapon's statstable col 8 list. Otherwise it's reset to none [V `_class.gsc:573-585`].
  - Pistols have empty lists [V statstable].
  - **A `grip` or `gl` on either weapon takes the perk-1 slot.** Perk 1 is forced to 193 (`PERKS_ATTACHMENT`) unless
    it's already one of the placeholders 190-193 (none / grenade launcher / grip / attachment) [V `:563-568`,
    statstable rows 190-193].
  - Without Overkill, the secondary must be a pistol [V `:544-550`].
- **T5: one attachment by default** [I]. Warlord (`specialty_twoattach`, tier 2) allows two [V statstable].
  - The lists come from statstable col 8 [V]. Launchers, crossbow and ballistic knife have none.
  - BO1's Overkill check is commented out; launchers are plain secondaries [V `_class.gsc:811-826`].
- **T6: Pick 10** [I, script compiled]. Primary up to 2 attachments (3 with `bonuscard_primary_gunfighter`), secondary
  1 (2 with `bonuscard_secondary_gunfighter`). The lists come from statstable col 8 [V]; launchers have none.

### Perk slots

**T4** [V]: statstable col 8 tags, then `validatePerk` against `level.allowedPerks` (`_class.gsc:377-421`). A perk not
in the slot's list becomes 190 (none).

| slot | perks |
|---|---|
| perk 1 | extra special grenades, Bouncing Betty ×2, frag ×3, Bandolier, Bomb Squad, M2 flamethrower, Bazooka ×2, Satchel ×2 (`specialty_specialgrenade`, `_weapon_bouncing_betty`, `fraggrenade`, `extraammo`, `detectexplosive`, `_weapon_flamethrower`, `_weapon_bazooka`, `_weapon_satchel_charge`); plus the placeholders 190-193 |
| perk 2 | Stopping Power, Juggernaut, Sleight of Hand, Double Tap, Overkill, Camouflage, Sonic Boom, Flak Jacket, Shades, Gas Mask (`bulletdamage`, `armorvest`, `fastreload`, `rof`, `twoprimaries`, `gpsjammer`, `explosivedamage`, `flakjacket`, `shades`, `gas_mask`) |
| perk 3 | Martyrdom, Steady Aim, Second Chance, Deep Impact, Iron Lungs, Dead Silence, Fireproof, Reconnaissance, Toss Back, Extreme Conditioning (`grenadepulldeath`, `bulletaccuracy`, `pistoldeath`, `bulletpenetration`, `holdbreath`, `quieter`, `fireproof`, `reconnaissance`, `pin_back`, `longersprint`) |
| perk 4, vehicle (stat +105) | Coaxial Machine Gun, Greased Bearings, Ordinance Training, Leadfoot, Boost (`water_cooled`, `greased_barrings`, `ordinance`, `leadfoot`, `boost`) [V `:416-421`] |

**T5** [V statstable, specialty1-3 tag, base → pro specialties]:

| tier | perks |
|---|---|
| 1 | Lightweight (`movefaster` → +`fallheight`), Scavenger (`scavenger` → +`extraammo`), Ghost (`gpsjammer` → +`nottargetedbyai`, `noname`), Flak Jacket (`flakjacket` → +`fireproof`, `pin_back`), Hardline (`killstreak` → +`gambler`) |
| 2 | Steady Aim (`bulletaccuracy` → +`sprintrecovery`, `fastmeleerecovery`), Scout (`holdbreath` → +`fastweaponswitch`), Hardened (`bulletpenetration` → +`armorpiercing`, `bulletflinch`), Sleight of Hand (`fastreload` → +`fastads`), Warlord (`twoattach` → +`twogrenades`) |
| 3 | Marathon (`longersprint` → +`unlimitedsprint`), Ninja (`quieter` → +`loudenemies`), Second Chance (`pistoldeath` → +`finalstand`), Hacker (`showenemyequipment`, `detectexplosive` → +`disarmexplosive`, `nomotionsensor`), Tactical Mask (`gas_mask` → +`shades`, `stunprotection`) |

**T6** [V statstable col 13]:

| tier | perks |
|---|---|
| 1 | Lightweight (`movefaster`, `fallheight`), Flak Jacket, Blind Eye (`nottargetedbyairsupport`), Hardline (`earnmoremomentum`), Ghost (`gpsjammer`) |
| 2 | Hard Wired (`immunecounteruav`, `immuneemp`), Scavenger, Cold Blooded (`immunenvthermal`, `noname`, `immunerangefinder`, `nokillstreakreticle`, `immunemms`, `nomotionsensor`), Fast Hands (`fastweaponswitch`, `pin_back`, `fasttoss`, `fastequipmentuse`), Toughness (`bulletflinch`) |
| 3 | Dexterity (`fastmantle`, `fastladderclimb`, `sprintrecovery`, `fastmeleerecovery`), Engineer (`showenemyequipment`, `delayexplosive`), Dead Silence (`quieter`), Extreme Conditioning (`longersprint`), Tactical Mask (`stunprotection`, `flashprotection`, `proximityprotection`), Awareness (`loudenemies`) |

- The display names are [I], from general knowledge; the specialty strings are [V].
- T6 perk greed wildcards (`bonuscard_perk_1/2/3_greed`) allow a second perk in a tier [V table; ClassTables
  `extraPerks`].
- [I] For one Reforged ruleset: keep the slot lists per source game, and apply T4's grip/gl → perk-1 rule only to T4
  weapons.

## Open

- T6 limits, spawn influencer values, bot tuning and the scorestreak rules: decompile the T6 `.gsc` (ACTS) from
  `patch_mp.ff`.
- The T4/T5 falloff shape (linear vs stepped) and the order of the multipliers: confirm in the `t4mp` damage code.
- The BO1 headshot score entry: whether it's paid on top of the kill.
