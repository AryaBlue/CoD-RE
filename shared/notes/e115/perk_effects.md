# T5 / T6 zombies perk effects: the data-only perks

What each perk that is `dataOnly` today actually does, split into script (GSC) and engine (exe), with the values, so
the profile can carry them per game and the zm code can run them with no per-map code. Researched 2026-10-27.

- **T5:** Stamin-Up, Deadshot, Mule Kick, PhD Flopper.
- **T6:** Stamin-Up, Deadshot, Mule Kick, PhD Flopper, Tombstone, Who's Who, Electric Cherry, Vulture Aid.

## Conventions

- **Tags.**
  - **[V]** read in a script or exe at the cited place.
  - **[M]** measured by running something.
  - **[I]** inferred.
  - **[U]** unknown.
  - Nothing here was run in game.
- **Sources.**
  - **T5 PATCH** = the scripts the game runs, in `zone\Common\common_zombie_patch.ff` (dumped with `e115_zonedump --rawfile`).
    - These supersede the mod-tools `raw\` copies. Those are older: Mule Kick is a stub there under a name the exe doesn't know, and Deadshot costs 1500.
  - **T5 EXE** = `BlackOps.exe` (32-bit, image base 0x400000), disassembled with capstone.
  - **T6 GSC** = gsc-tool decompile of the shipped zm scripts (`.../allzm/dump/decompiled/t6`). Short names:
    - `perks:` `_zm_perks.gsc`
    - `zm:` `_zm.gsc`
    - `utility:` `_zm_utility.gsc`
    - `dtn:` `_zm_perk_divetonuke.gsc`
    - `cherry:` `_zm_perk_electric_cherry.gsc`
    - `tomb:` `_zm_tombstone.gsc`
    - `chug:` `_zm_chugabud.gsc`
    - `vulture:` `_zm_perk_vulture.gsc`
  - **T6 EXE** = `t6zm.exe`.
  - The client scripts (csc) are not in the T6 dump, so T6 client-only effects are [I].
- **Units.** Cod units (inches), seconds, points.
- No script text is copied here, only values and `file:line` cites.

## How perks are held (both games)

- `setperk` sets an engine bit; `hasperk` and engine code test it [V].
- **T5:** 15 perks, 2 bits each, in `playerState+0x4fc`.
  - Name table at `0xb6dfe8`, index = position [V]:

    | index | specialty |
    |---|---|
    | 0 | longersprint |
    | 1 | unlimitedsprint |
    | 2 | scavenger |
    | 3 | fastreload |
    | 4 | bulletdamage |
    | 5 | bulletaccuracy |
    | 6 | flakjacket |
    | 7 | armorvest |
    | 8 | quickrevive |
    | 9 | altmelee |
    | 10 | rof |
    | 11 | extraammo |
    | 12 | endurance |
    | 13 | deadshot |
    | 14 | additionalprimaryweapon |

  - SetPerk ORs `3 << 2i` (`0x7d9082`); HasPerk tests the same mask (`0x7d9138`) [V].
  - Most zm perk code is also gated on dvar `zombiemode` [V].
- **T6:** see [T6 engine](#t6-engine). The specialty names the T6 GSC uses [V]:

  | perk | specialty |
  |---|---|
  | Stamin-Up | `specialty_longersprint` |
  | Deadshot | `specialty_deadshot` |
  | Mule Kick | `specialty_additionalprimaryweapon` |
  | PhD | `specialty_flakjacket` |
  | Tombstone | `specialty_scavenger` |
  | Who's Who | `specialty_finalstand` |
  | Electric Cherry | `specialty_grenadepulldeath` |
  | Vulture Aid | `specialty_nomotionsensor` |

- **Losing the perks.**
  - Every perk is unset on down, death, fake death (Who's Who) or a `<perk>_stop` notify (`perks:2152`) [V].
  - The deadshot clientfield and the Mule weapon take run from there.

## Costs

T6: `perks:1692-1730`; a perk with no case falls back to `zombie_perk_cost` 2000 (`perks:68`) [V].

| perk | T5 | T6 |
|---|---|---|
| Stamin-Up | 2000 [V] | 2000 [V] |
| Deadshot | **1000** (PATCH `_zombiemode_perks.gsc:1156`; raw says 1500) [V] | 1500 [V] |
| Mule Kick | 4000 [V] | 4000 [V] |
| PhD Flopper | 2000 [V] | 2000 [V] |
| Tombstone | n/a | 2000 (no case, so the default) [V] |
| Who's Who | n/a | 2000 (no case, so the default) [V] |
| Electric Cherry | n/a | 2000 (`cherry:14`) [V] |
| Vulture Aid | n/a | 3000 (`vulture:19`) [V] |

## Stamin-Up

**T5**
- **Script:** sets the perk and its HUD icon only [V].
- **Sprint time.** `BG_GetMaxSprintTime` `0x67fdc0` [V]:
  - `maxSprintMs = weapon.sprintDurationScale × 4000`. The 4000 is a constant; `player_sprintTime` is not read in SP.
  - With the perk, ×`perk_sprintMultiplier` = **2.0**.
  - The result is clamped to 16383 ms.
  - **So 4 s becomes 8 s.**
- **Sprint speed.** `0x75d680` [V]:
  - Applies only in `zombiemode`, while sprinting, with the perk.
  - The weapon's `moveSpeedScale` becomes `max(moveSpeedScale, 1.10)`.
  - It is a floor, not the MP ×1.07: guns already at 1.1 or more gain nothing.
- **Recovery:** unchanged. `perk_sprintRecoveryMultiplier` 0.6 and `perk_speedMultiplier` 1.07 are registered but unread in SP [V].

**T6**
- **Script:** setperk plus clientfield `perk_marathon`; no dvars [V].
- **Engine:** same as T5: sprint ×2 (4 s becomes 8 s) and the 1.1 sprint speed floor (see [T6 engine](#t6-engine)).

## Deadshot Daiquiri

**T5**
- **Script:**
  - Sets client flag 12 (PATCH `_zombiemode_perks.gsc:1485`) [V].
  - The client script turns alternate aim params on while it is set and off when it clears (PATCH `_zombiemode.csc:392-404`) [V].
- **Engine** [V unless marked]:
  - **Hip spread:** when not fully ADS, min and max spread ×`perk_weapSpreadMultiplier` **0.65** (`0x406e2b`).
  - **Scope sway:** with a scope overlay and fully ADS, one view-offset vector ×**0.25** (`0x56321d`). That vector is probably the sway [I].
  - **Hold breath:** off. The breath flag is never set with the perk (`0x7682c9`).
  - **Aim assist** (alternate params, while the client flag is on):

    | parameter | normal | Deadshot |
    |---|---|---|
    | lock-on strength | 0.6 | 1.0 |
    | lock-on pitch strength | 0.6 | 1.0 |
    | deflection | 0.05 | 0 |
    | target frustum min distance | 256 | 1024 |

    The lock-on region (90 × 90) is unchanged.
  - No head-snap found [U].

**T6**
- **Script:**
  - Clientfield toplayer `deadshot_perk` = 1 on give and 0 on loss (`perks:2004-2010`, registered `zm:1159`) [V].
  - The client side is not in the dump [U].
- **Engine:** hip spread ×0.65, no hold breath, ADS kick ×0.25; no aim-assist change in the exe (see [T6 engine](#t6-engine)).

## Mule Kick

**Both games: script only** (T5: no engine code tests its mask [V]).

- **Weapon limit:** 2, or **3** with the perk.
  - T5 checks it at box give, wall-buy give, the PaP return and the anti-cheat weapon monitor (PATCH `_zombiemode_weapons.gsc:2370`, `:2898`, `_zombiemode_perks.gsc:566`, `_zombiemode.gsc:1947`) [V].
  - T6: `level.additionalprimaryweapon_limit` 3 (`perks:22`); `get_player_weapon_limit` (`utility:5032-5042`) [V].
- **What counts:** only included or upgraded weapons count toward the limit [V].
- **Losing it.**
  - On a down (before last stand) and on `<perk>_stop`, if 3 or more counted primaries are held, the **last** one in the primaries list is taken (T5 `_zombiemode.gsc:2107-2147`, T6 `zm:1910-1935, 1971`) [V].
  - That is probably the newest [I].
  - If it was in hand, the player first switches to primaries[0] [V].
  - The weapon is gone for good: it is only remembered so last stand doesn't hand it back [V].
- **T5 machine:**
  - Script-spawned at per-map hard-coded origins (PATCH `_zombiemode.gsc:253-320`): a model plus a use trigger of radius 20, height 70, at +30 z [V].
  - The origins are per-map content, so they belong in the map data, not code.
  - It waits for `power_on` (prototype and sumpf: no wait), then 3 s [V].

## PhD Flopper

**Both games, script** (T5 PATCH `_zombiemode_perks.gsc:83-85, 963-985`; T6 `dtn:` init and `zm:4148-4172`) [V]:
- **Trigger:** `MOD_FALLING` damage while the player has the perk and is diving-to-prone sets off the explosion; the fall does 0 damage.
- **Explosion:**
  - Radius damage, radius **300**, from **5000** at the centre to **1000** at the edge, as `MOD_GRENADE_SPLASH`, with the player as attacker.
  - It also plays an fx and sound and a short vision set (T6: `zm_perk_divetonuke` for 1 s).
- **Network-optimised path (T6):** each round enemy in range takes `min + (max-min)·(1 - d/r)` instead of the radius damage [V].
- **Immunity with the perk:** `MOD_PROJECTILE`, `MOD_PROJECTILE_SPLASH`, `MOD_GRENADE` and `MOD_GRENADE_SPLASH` do 0.
- **Without the perk:** the same damage types are capped at 75 while health is above 75.

**T5 engine** [V]:
- **Dive fall damage** (`0x46a280`, dvar `dtp` on, while diving):
  - At or below `dtp_fall_damage_min_height` **65**, the damage is 0. **So a dive must drop more than 65 units to set PhD off** [I: below that no falling event reaches script].
  - At or above `dtp_fall_damage_max_height` 200, the damage is 100; linear between.
- **Normal falls:** 128..350 (`bg_fallDamageMin/MaxHeight`).
- **Fall damage with the perk:** in `zombiemode`, any fall damage above 0 becomes **1**, dive or not (`0x75e352`). So PhD makes falls harmless while still firing the event.
- **Low gravity:** with gravity below `bg_gravity` (Moon), fall damage is 0.

**T6 engine:** fall damage with the perk becomes 1, and the dive heights are 65 / 200, as in T5 (see [T6 engine](#t6-engine)). `self.divetoprone` is set by the engine [I].

## Tombstone Soda (T6)

`tomb:` and `zm:1957-1979` [V]:
- **On a down with the perk**, it saves:
  - the perks armorvest, deadshot, fastreload, flakjacket, longersprint, quickrevive and rof (`tomb:140-166`);
  - every weapon with clip and stock;
  - claymores, the emp, the lethal grenade count and monkeys.
- **The stone:**
  - A stone model spawns at the player's origin +40 z (`tomb:33-36`).
  - A revive removes it.
  - If the player bleeds out and respawns, it stays **60 s**: 48.5 s solid, then flashing for about 11.5 s (15 × 0.5, 10 × 0.25, 15 × 0.1) (`tomb:337-367`).
- **Grabbing it:**
  - Owner only, within **64** units (`tomb:197`), and only while a Tombstone machine is powered (`tomb:185-193`).
  - It gives back the weapons (co-op only, `tomb:224`), the perks (not Quick Revive in solo) and the equipment.
- **Engine:** `specialty_scavenger` only drives the MP Scavenger pickup rules; nothing zm-specific [V/I].

## Who's Who (T6)

`chug:` and `zm:` [V]:
- **Trigger:**
  - Damage that would kill, while `lives > 0` and the player has the perk: lives−1, the damage becomes 0, the Who's Who flow starts (`zm:4229-4236`).
  - Buying the perk sets lives = 1.
- **Flow** (`chug:35-109`):
  1. Health goes to max.
  2. The loadout is saved: weapons, equipment, claymores, grenades, monkeys and every perk. Then all perks are unset.
  3. A 1 s fake death: no weapons, invulnerable, frozen.
  4. After 3 s a clone body with a revive trigger is left at the spot, unless the player was insta-killed.
  5. The player is moved to a spawn point with the knife, the start pistol and **2** frag grenades. The score is kept. They are invulnerable 1 s more.
- **The body:**
  - It bleeds out after `player_lastStandBleedoutTime` (zm sets **45** s, `zm:963`).
  - Anyone can revive it, the owner included. A revive moves the player to the body and gives back the saved loadout and perks (not Who's Who, not solo Quick Revive).
  - If it bleeds out, the player keeps the new start loadout and has no perks.

## Electric Cherry (T6)

`cherry:` [V]:
- **On going down** (custom laststand func, `cherry:27`):
  - Fx and sound.
  - Every zombie within **500** (`cherry:128`) takes **1000** damage, 0.1 s apart (`cherry:150`).
  - Zombies with health ≤ 1000 die with a death fx and give **40** points (`cherry:141`); the rest are stunned.
- **On reload start** (`cherry:230-300`):
  - frac = clip / clipMax.
  - radius = lerp **32** (full clip) .. **128** (empty).
  - damage = lerp **1** (full) .. **1045** (empty) (`cherry:240-241`).
  - Kills give **40** points (`cherry:296`).
- **Consecutive reloads** cap the zombies hit (`cherry:250-262`):

  | reload in a row | zombies hit |
  |---|---|
  | 1st | unlimited |
  | 2nd | unlimited |
  | 3rd | 8 |
  | 4th | 4 |
  | 5th | 2 |
  | 6th+ | 0 |

  - The counter resets after the reload time (× `perk_weapReloadMultiplier` with Speed Cola) + **3** s (`cherry:327`).
  - Each weapon fires it once until its reload completes.
- **Stun:** only on zombies chasing a player; the stun anim plays twice (`cherry:207`).

## Vulture Aid (T6)

`vulture:` [V]:
- **Dvars** (`vulture:71-81`):

  | dvar | value |
  |---|---|
  | pickup time | 12 s |
  | stink pickup time | 16 s |
  | drop chance | 65 % |
  | ammo chance | 33 |
  | points chance | 33 |
  | stink chance | 33 |
  | drops max | 20 |
  | network drops max | 5 |
  | network time frame | 250 ms |
  | stink zombie spawn cooldown | 12 s |
  | max stink zombies | 4 |

- **Drop on a zombie's death:**
  - The drop roll must beat 100−65 (`vulture:493`); then ammo vs points by the 33/33 weights (`vulture:501-512`).
  - Stink zombies always drop stink.
  - Drops are visible to the Vulture player only.
- **Pickup:** within **32** units (`vulture:588`).
- **Points:** 5 × randomint 1..4 = **5, 10, 15 or 20** (`vulture:895-898`).
- **Ammo** (`vulture:832-870`):
  - The current weapon's stock gains `clamp(int(maxAmmo × rand 0..0.025), 1, max)`.
  - Heat weapons: −1..2 heat.
  - Fuel weapons: +1–3 % fuel.
- **Stink zombies:**
  - A 50 % roll, 12 s cooldown, at most 4 (`vulture:1031-1038`).
  - Standing in a stink cloud (radius **70**, `vulture:526`) shows an overlay and makes zombies ignore the player (`ignoreme`, `vulture:627`).
- **Glows:** perk machines, wall buys, the box, power-ups, PaP and zombie eyes glow through walls. These are client fx driven by clientfields (`vulture:41-53, 98-105`) [I: csc not dumped]. They are cosmetic: implement later or not at all.

## T6 engine

`t6zm.exe` (Steam). Addresses are image addresses in the Steam build. Plutonium's exe has the same perk table and dvar defaults. Disassembled with capstone.

**How perks are held.**
- 63 specialty names at `0xF69998`; the bit index is the table position [V].
- `setperk` ORs `1 << (i & 31)` into `ps.perks[i >> 5]` at `ps+0x548` / `+0x54C` [V].
- `BG_HasPerk` (`0x4AF3A0`) also checks the weapon and its attachments: weapons and attachments can grant perks [V].
- Our perks:

  | perk | specialty | index |
  |---|---|---|
  | Mule Kick | additionalprimaryweapon | 0 |
  | Deadshot | deadshot | 7 |
  | Who's Who | finalstand | 23 |
  | PhD | flakjacket | 25 |
  | Electric Cherry | grenadepulldeath | 28 |
  | Stamin-Up | longersprint | 37 |
  | Vulture Aid | nomotionsensor | 41 |
  | Tombstone | scavenger | 53 |
  | (not a cola) | unlimitedsprint | 62 |

**Stamin-Up (37)** [V]:
- **Sprint time** (`0x8BB920`):
  - `sprintDuration × the weapon's sprint scale`, ×`perk_sprintMultiplier` **2** with the perk, clamped to 16383 ms.
  - `sprintDuration` comes only from script `setsprintduration`; the zm scripts set 4 on spawn. **So 4 s becomes 8 s**, as in T5.
- **Sprint speed** (`0x8BE0F0`): in zombies, while sprinting, the weapon's moveSpeedScale = max(it, **1.1**), as in T5.
- **Odd flag:** a playerState flag (`ps+0xFC & 0x4000`) forces max sprint to 740 ms [I: meaning unknown].

**unlimitedsprint (62):**
- The meter never empties (`0x8BE3E0`, `0x8C4140`) [V].
- In zm script only Turned gives it [V].
- `player_sprintUnlimited` is never read [V].

**Deadshot (7), zombies only** [V]:
- **Hip spread:** ×`perk_weapSpreadMultiplier` **0.65** when not fully ADS (`0x8E1230`).
- **Hold breath:** off (`0x8E18F0`).
- **Fully ADS:** a client view-kick vector ×**0.25** (`0x4B1EC0`). It is probably scoped recoil or sway [I].
- **Aim assist:** **no code** reads Deadshot. Unlike T5's csc, the engine has no Deadshot aim-assist path.
  - Whether T6's csc calls the alternate aim params is unknown (csc not dumped) [U].
  - The zm scripts set lock-on pitch strength 0 on spawn [V].

**PhD (25), zombies only** [V]:
- **Fall damage with the perk:** any fall damage becomes **1** (`0x8BF60E`), as in T5.
- **Grenade in hand:** the 100000-damage self-kill when a grenade goes off in hand is skipped (`0x5D31E3`).
- **Dive heights:** `dtp_fall_damage_min_height` **65** and `_max_height` **200** (registered `0x8AD2C4` / `0x8AD30C`, bounds 0..1000) [V: defaults]. That is the same 65-unit dive minimum as T5 [I: the reader wasn't traced in T6].
- **perk_flakJacket:** `perk_flakJacket` 35 is read by nothing [V].

**Mule Kick (0), Who's Who (23), Electric Cherry (28), Vulture Aid (41):** no engine checks at all, so they are script only [V: an immediate-mask scan found none].

**Tombstone (53):**
- `specialty_scavenger` only drives the MP Scavenger pickup rules [V].
- Nothing zm-specific [I].
- `perk_scavenger_*` dvars have no readers [V].

**Dvar defaults** (all flag 0x80, none set by any zm zone or script) [V]:

| dvar | default | min..max |
|---|---|---|
| perk_sprintMultiplier | 2 | 0..3 |
| perk_sprintRecoveryMultiplier | 0.3 | 0..1 |
| perk_weapSpreadMultiplier | 0.65 | 0..1 |
| perk_weapReloadMultiplier | 0.5 | 0..1 |
| perk_weapRateMultiplier | 0.75 | 0..1 |
| perk_weapAdsMultiplier | 0.5 | 0.01..1 |
| perk_weapSwitchMultiplier | 0.5 | 0.01..1 |
| perk_extraBreath | 5 | 0.. |
| player_sprintTime | 4 | 0..12.8 |
| player_sprintSpeedScale | 1.5 | 0..5 |
| player_lastStandBleedoutTime | 30 (zm script: 45) | 0.. |

- Electric Cherry's script reads `perk_weapReloadMultiplier` for its reset timer [V].
- **Unread or unknown:** nothing in plain code reads `player_sprintSpeedScale`, `_RechargePause` or `_StrafeSpeedScale` [U: maybe through a table].

## Dive to prone (both games)

The move PhD needs. T5 (`BlackOps.exe`) and T6 (`t6zm.exe`, Steam build) have the **same dvars, defaults and
logic** [V]. The only differences:
- `dtp` is registered with flags 0x5000 in T5 and 0x4080 in T6.
- T6 adds one extra start check (a playerState flag bit 25 must be clear) [V, meaning I].

**Dvars** (registration: T5 `0x562eb0-0x56311e`, T6 `0x8ad170-0x8ad441`) [V]:

| dvar | default | min..max | use |
|---|---|---|---|
| dtp | 1 (bool) | | the move on/off |
| dtp_startup_delay | 250 ms | 100..10000 | how long the player must have sprinted |
| dtp_exhaustion_window | 1500 ms | 100..10000 | the gap needed since the last dive ended |
| dtp_min_speed | 3.16 | 0..1000 | horizontal speed needed to start, and to keep sliding |
| dtp_new_trajectory | 1 (bool) | | use the capped-apex launch below |
| dtp_new_trajectory_multiplier | 2 | 0..10 | × the launch's vertical speed |
| dtp_max_apex_duration | 400 ms (int) | 0..10000 | the most time the dive may hover at its apex |
| dtp_max_slide_duration | 300 ms | 0..10000 | the slide after landing |
| dtp_max_slide_addition | 0 ms | 0..10000 | extra slide when landing on a mantle-able surface |
| dtp_post_move_pause | 100 ms | 0..10000 | the pause after the slide |
| dtp_fall_damage_min_height | 65 | 0..1000 | a dive drop at or below this does no fall damage |
| dtp_fall_damage_max_height | 200 | 0..1000 | a dive drop at or above this does 100 |

**1. Starting a dive.** Start check T5 `0x75ba60`, T6 `0x8ada20`; dive start T5 `0x56f2f9`, T6 `0x8adb3b`. All of these must hold:
- `dtp` is on [V].
- The weapon doesn't forbid it: a WeaponDef byte, T6 `+0x694` [V, meaning I].
- The player is sprinting this frame: a playerState sprint time equals the command time [V, meaning I].
- The command's button bit 19 (0x80000) is set. That is the prone/stance press [I].
- Horizontal speed² > `dtp_min_speed`² [V]. 3.16 u/s means "moving at all" [I].
- T6 only: playerState flag bit 25 (0x2000000) is clear [V].
- At least `dtp_exhaustion_window` (1500 ms) has passed since the last dive ended [V]. A negative gap also passes.
- The player has been sprinting for more than `dtp_startup_delay` (250 ms), measured from the sprint's start time [V].

So: sprint for more than 0.25 s, then press prone while moving, at least 1.5 s after the last dive.

**2. The launch** (T5 `0x75b980`, T6 `0x8ad570`) [V]:
- **Vertical speed** = `sqrt(2 × 39 × gravity)`.
  - 39 is a hard-coded jump height constant (T5 `0xa3fdd8`, T6 `0xbc6188`).
  - Then × `dtp_new_trajectory_multiplier` 2 when `dtp_new_trajectory` is on.
  - With gravity 800 that is 249.8 × 2 = **499.6 u/s up** [V math].
- **Horizontal speed:** not set at launch, so the sprint's horizontal velocity carries on [V: only vz is written; air control I].
- **State:** a diving flag is set (T5 `ps+0xc |= 0x20000000`, T6 `|= 0x200000`); the dive start time and start z are saved [V].
- **Events:** a dive-start event (`0xb8` T5 / `0xd7` T6) and anim 0x17 / 0x1a [V].

**3. In the air.**
- **The apex cap** (T5 `0x4975d0`, T6 `0x8ad770`, only with `dtp_new_trajectory`) [V]:
  - Once the player is **39** units above the dive's start z, vz is set to 0 (hover) until `dtp_max_apex_duration` (400 ms) after the dive started.
  - After that, vz is clamped to ≤ 0.
  - So the arc is capped at +39 u and then falls under normal gravity [V].
- **Gravity:** the normal player gravity [I: no dive-specific gravity dvar].
- **Landing** (T5 `0x56f2a7`, T6 `0x8adae0`): a land event (`0xb9` / `0xd8`, with the surface type), anim 0x18 / 0x1b, then the slide phase starts [V].
- **Slide** (T6 `0x8ad8b0`, `0x8ad690`) [V]:
  - It lasts `dtp_max_slide_duration` 300 ms, plus `dtp_max_slide_addition` (0) on a mantle-able surface.
  - It ends early if horizontal speed drops to `dtp_min_speed` or below.
  - The end clears the diving flag, sets velocity to 0 and stores the end time (which the exhaustion window counts from).
- **Post pause:** for `dtp_post_move_pause` 100 ms after the end, a check (T6 `0x8ad7f0`) returns 0, which blocks the next stance or move [V: the value; I: what it blocks].
- **Stance after the dive:** prone [I, from the move's name and anims; the stance write isn't traced].

**4. The PhD height** (crash land, T6 `0x8bf480-0x8bf5ac`) [V]:
- The "height" passed to the dtp fall-damage function (T5 `0x46a280`, T6 `0x8ad4a0`) is `vz_impact² / (2 × gravity)`, worked out from the vertical speed at impact.
- **So it is the drop from the apex, not from the dive's start height.**
- With gravity 800, the 65 minimum means an impact faster than about 322 u/s down [V math].
- A flat-ground dive: the apex is +39, so the drop is about 39, under 65. **A flat dive does no fall damage, and so no PhD blast** [I: the T6 csc/gsc only blasts on a MOD_FALLING hit]. The player has to dive off something about 26 u or higher.
- **Damage:** 0 at or below 65, 100 at or above 200, linear between [V]. The value is probably a percent of max health [I].
- **Afterwards:** fall damage is zeroed for a weapon/perk with specialty 14 (T6) and in low gravity [V], then set to 1 in zombies with flakjacket [V] (see PhD).

## Spec for the profile

What the zombies profile needs per game. Everything is profile data plus one generic implementation per effect; nothing keys on a map.

**New `PerkDef` fields.** A perk carries any of these, 1 / 0 = untouched, like the existing scales:

| field | meaning | T5 | T6 |
|---|---|---|---|
| `sprintTimeScale` | × max sprint time | longersprint 2.0 | longersprint 2.0 |
| `sprintSpeedFloor` | while sprinting, weapon moveSpeedScale = max(it, this) | longersprint 1.1 | longersprint 1.1 |
| `hipSpreadScale` | × min/max spread when not fully ADS | deadshot 0.65 | deadshot 0.65 |
| `scopeSwayScale` | × scoped ADS sway/kick | deadshot 0.25 [I] | deadshot 0.25 [I] |
| `noHoldBreath` | hold breath off | deadshot | deadshot |
| `aimAssistAlt` | lock-on strength and pitch 1.0, deflection 0, frustum min 1024 | deadshot | none in the exe; csc [U] |
| `weaponLimit` | primaries cap while held (0 = default 2) | mule 3 | mule 3 |
| `explosiveImmune` | projectile/grenade damage to self = 0 | phd | phd |
| `fallDamageTo1` | any fall damage > 0 becomes 1 | phd | phd |

**New `PerkRules` fields.**
- `explosiveSelfCap` 75: the cap on explosive self damage without PhD, both games.
- `weaponLimit` 2.

**Behaviours** (one implementation each, values in the profile):

1. **Dive nuke** (`flakjacket`).
   - On dive landing with fall height > `diveMinHeight`, explode: radius 300, damage 5000→1000 linear by distance, attacker the player, fall damage 0.
   - `diveMinHeight`: 65 in both games (T6: the default [V], its reader [I]).
   - Vision flash 1 s (T6) [V].
2. **Mule take on down.** If held counted primaries ≥ 3, remove the last acquired one, switching away first if it's in hand. It is not restored. Same in T5 and T6.
3. **Tombstone** (T6, `scavenger`).
   - Save list: armorvest, deadshot, fastreload, flakjacket, longersprint, quickrevive, rof, plus the loadout.
   - Stone offset +40 z, life 60 s (blink from 48.5 s), grab radius 64, owner only, needs a powered Tombstone machine.
   - Weapons back only in co-op; Quick Revive not back in solo.
4. **Who's Who** (T6, `finalstand`).
   - 1 life.
   - Fake death 1 s, body after 3 s, bleedout 45 s.
   - Respawn loadout: knife, start pistol, 2 frags; invulnerable 1 s.
   - Revive restores loadout and perks (not finalstand, not solo quickrevive).
   - Needs a spawn-point query (the map's player spawns), no per-map code.
5. **Electric Cherry** (T6, `grenadepulldeath`).
   - Down blast: 500 radius, 1000 damage, 0.1 s stagger, 40 points a kill.
   - Reload blast: frac = clip/clipMax, radius lerp 32..128, damage lerp 1..1045.
   - Consecutive caps: ∞, ∞, 8, 4, 2, 0; reset after reload time + 3 s.
   - 40 points a kill; the rest stunned.
6. **Vulture Aid** (T6, `nomotionsensor`).
   - Drop table and stink zombies with the values above; pickup radius 32; stink radius 70 makes the player ignored.
   - The glows can wait.
7. **Deadshot / Stamin-Up:** need only the `PerkDef` scales above and the movement and aim code reading them.

**T6 power.** The T6 machines wait for the power like the others; Tombstone's grab also checks it at grab time [V].

## Open

1. **T5 Deadshot.**
   - Head targeting: is there any head snap?
   - Is the 0.25 vector really the sway?
2. **T5 fall damage:** is it a percent of max health? (affects `fallDamageTo1`)
3. **Mule Kick:** is "last in the primaries list" the newest weapon? It depends on how the engine orders the list.
4. **T6 csc:** not dumped, so whether T6 Deadshot changes aim assist (none in the exe), and the Vulture glows, are [U].
5. **T6 sprint dvars:** what reads `player_sprintSpeedScale`, `_RechargePause` and `_StrafeSpeedScale`? Nothing in plain code does.
