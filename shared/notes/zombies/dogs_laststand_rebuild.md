# Dog rounds, last stand and barrier rebuild (t4 / t5 / t6)

Data for native zombies. Profile fields are `GameProfile::dogs`, `lastStand` and `rebuild` (src/content/GameProfile.h); the last-stand pistol stays in `PerkRules` (a contributor's).

Tags: [V] read in script/exe, [M] measured, [I] inferred, [U] unknown. Paths: t4 = WaW Der Riese dump (`zm_factory/maps/`), t5 = BO1 `raw/maps/`, t6 = decompiled `t6/`. No script text here, only values and line refs.

## 1. Dog rounds

| | t4 (factory) | t5 | t6 |
|---|---|---|---|
| maps | sumpf, factory | theater, cod5 sumpf/factory [I]; pentagon loads the module but never enables dog rounds [V] | zm_transit survival only [V/I] |
| first dog round | random 5..7 [V] | random 5..7 [V] | start round + 4..6, so 5..7 from round 1 [V] |
| next round gap | +4..5 [V] | +4..5 [V] | +4..5 [V] |
| dogs per player | 6 for the first rounds, then 8 (earlyRounds 2) [V] | same [V] | same [V] |
| alive at once | 2 per player, polled every 2 s [V] | same [V] | same [V] |
| intro wait | 7 s [V] | 7 s [V] | 1 s + 6 s [V] |
| health by dog round 1/2/3/4+ | factory 400/900/1300/1600, sumpf 350/700/1000/1250 [V] | 400/900/1300/1600 [V] | 400/900/1300/1600, capped 1600 [V] |
| walk multiplier | factory x4 until it runs, sumpf x1 [V] | x4 until running [V] | x4 until running, then cut to dog health [V] |
| spawn gap by dog round | 3 / 2.5 / 2 / 1.5 s, minus a count term [V] | same [V] | same [V] |
| spawn points | factory: structs 400..1000 units from the player; sumpf: old spawner path 400..800 [V] | zone structs 400..1000 [V] | zone structs whose script_noteworthy has the token `dog_location`, 400..1000 [V] |
| spawners | script_noteworthy `zombie_dog_spawner` [V] | same [V] | same [V] |
| end drop | `full_ammo` at the last dog's origin [V] | same [V] | same [V] |

Refs:
- t4: factory `_zombiemode_dogs.gsc` round pick :471, struct spawn :377-395, sumpf spawner path :350; rest as t5.
- t5: `_zombiemode_ai_dogs.gsc` :330 first, :346 next, :100 intro, :119-121 cap, :160-177 gaps, :188 max ammo, :205-211 spawn fx/sounds, :301-321 health, :728 run cut, :253-270 range, :494-504 trails; opt-in `enable_dog_rounds` :45-50.
- t6: `_zm_ai_dogs.gsc` :314 first, :333 next, :107-115 intro/counts, :124-128 cap, :165-182 gaps, :183-195 max ammo, :197-207 spawn, :296-308 health, :418-426 x4, :692-697 run cut, :461-473 trails; `_zm_zonemgr.gsc` :199-229, :945-976 locations, :249-267 distance; `zstandard.gsc` :27, :37-42 allowdogs gate.

Spawn fx and sounds:

| | t4 | t5 / t6 |
|---|---|---|
| lightning fx | `maps/zombie/fx_zombie_dog_lightning_buildup` [V] | same [V] |
| prespawn / bolt (1.5 s later) / spawn sound | `pre_spawn` / `bolt` / `spawn` [V] | `zmb_hellhound_prespawn` / `zmb_hellhound_bolt` / `zmb_hellhound_spawn` [V] |
| trails (50/50 fire or ash) | `fx_zombie_dog_fire_trail` / `fx_zombie_dog_ash_trail`; `dog_trail_fire` / `dog_trail_fire_breath` [V] | same fx; `zmb_hellhound_loop_fire` / `zmb_hellhound_loop_breath` [V] |

## 2. Last stand

| | t4 | t5 | t6 |
|---|---|---|---|
| bleed-out | 30 s, the dvar `player_lastStandBleedoutTime` default [M: t4sp.exe registers it at 0x40e97d, float 30.0 at 0x7f0428] | 45 s [V `_zombiemode.gsc`:543] | 45 s [V `_zm.gsc`:963] |
| revive | 3 s; QR halves it [V] | 3 s, QR halves [V] | 3 s, QR halves (`_zm_laststand.gsc`:834-840) [V]; a pers upgrade halves it again [V] |
| points lost on down | 5% [V factory `_zombiemode.gsc`:552-554] | 5% (csv MEDIUM column) [V mp/zombiemode.csv:20-22] | 5% [V `_zm.gsc`:875-877] |
| bled out (no revive) | 10% [V] | 10% [V] | 10% [V] |
| died | 0 [V] | 0 [V] | 0 [V] |
| reviver gets | none found [U] | points lost when downed [V :1361-1363] | points lost when downed [V `_zm.gsc`:1853-1858] |
| pistol | best owned pistol, else colt; ray gun keeps clip only (PerkRules) [V factory `_laststand.gsc`:181-219, :301-322] | PerkRules | PerkRules; zm_tomb overrides c96_zm / c96_upgraded_zm [V zm_tomb.gsc:997-999] |
| solo | t5/t6 solo QR = self revive, see PerkRules | | |

Note for PerkRules: the t6 pistol-class check uses `pistol spread` with a space (`_zm.gsc`:2265), not `pistol_spread`.

## 3. Barrier rebuild and Speed Cola

| | t4 | t5 | t6 |
|---|---|---|---|
| points per board | 10 [V `_zombiemode_blockers_new.gsc`:626] | 10 [V :1027] | 10 [V `_zm_blockers.gsc`:1400] |
| cap per round | min(50 x round, 500), reset each round [V `_zombiemode.gsc`:2050-2053, blockers :821] | same [V `_zombiemode.gsc`:2688-2696] | same [V `_zm.gsc`:3426-3431] |
| pace | 1 s per board while held [V :751-753] | 1 s [V :1187-1190] | 1 s [V :1350-1354] |
| speed cola effect | board anim only; 1 s pace unchanged [V] | board anim: fastreload rotate 0.15 + 0.1 s, upgraded 0.08 + 0.1, else 0.1 + 0.1 + 0.3 + 0.2 [V :1718-1743] | none: the perk check returns `specialty_fastreload` (:1340-1347) but the anim code compares against `speciality_fastreload` (:1906-1909), so its 0.31 / 0.2112 scale never applies [V] |

Profile `boardAnim` / `fastBoardAnim` are the totals from the rows above (t4 0.65 / 0.25 [V], t5 0.7 / 0.25 [V]). For t6 they're 0 because the anim comes from the zbarrier asset's length [U]. `fastWorks=false` reproduces the typo; set it true if we want the intended behaviour.
