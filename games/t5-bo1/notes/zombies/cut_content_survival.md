# BO1 cut content - how much of each cut mode and feature still ships (survival %)

Survey of the retail PC zones, exe strings, English strings and map entities, compared with the scripts in the official mod tools `raw` folder. Names and locations only.

## How the % is scored

- Six parts: rules script, map or placement data, models and effects, UI text, sound, engine hooks
- 100% = everything needed to play is in the files and only needs switching on
- "retail" = in the game's zones, "mod tools" = only in the mod tools raw folder
- Sound was not checked for any item
- Tools: OpenAssetTools Unlinker (zone lists and dumps), own string scans of the exes

## Multiplayer

| Item | % | Ships | Missing |
|---|---|---|---|
| War (twar, the WaW mode) | 90 | retail `twar.gsc` (3359 lines), `ui_mp/hud_twar`, `hud_momentum*` and `hud_blitzkrieg*` art, `MP_WAR_*` / Momentum / Blitzkrieg strings, engine call `setWarGameData`, flags and spawns in mp_cairo (5 flags, 34 spawns), mp_cosmodrome (3, 66), mp_cracked (3, 24) | entry in `_gametypes.txt`, placements on the other 11 launch maps |
| Survival (sur) | 55 | retail `sur.gsc` (1074 lines), `MP_CARGO_*` / `MP_SAFEZONE_*` strings, name "Survival" / "Hardcore Survival" | `sur_cargo`, `sur_hardpoint`, `safezone_trigger` entities on any map, final cargo model (script comment says temporary) |
| Old School rule | 30 | mod tools `_oldschool.gsc` (547 lines), retail string `MPUI_RULES_OLDSCHOOL_CAPS` | not in retail zones, pickup placements |
| Name-only modes (cp Cash Pot, nvc Assassins vs Cowboys, rcrace RC Car Race, rps Rock Paper Scissors, wdom World Domination, wkh King of the Hill, vdm / vtdm vehicle deathmatch, mini) | 5 | retail `.txt` stubs and name strings, `MPUI_VMAY_*` vehicle control strings | everything else |

## Zombies

| Item | % | Ships | Missing |
|---|---|---|---|
| Death cards | 60 | retail `_zombiemode_deathcard.gsc` + `.csc` in common_zombie, strings (`ZM_PT_DEATH_CARD`, `MENU_DEATHCARDS_CAPS`) | its caller `_zombiemode_solo.gsc` is mod tools only |
| Chainsaw power-up and Sabertooth weapon | 50 | mod tools `_zombiemode_chainsaw_attack.gsc`, `_zombiemode_weap_sabertooth.gsc`, 24 sabertooth anims, melee sound folder, shock file, retail strings `ZOMBIE_CHAINSAW_PICKUP` and `ZOMBIE_WEAPON_SABERTOOTH` | weapon file and model not found, nothing in retail zones |
| Abilities (airstrike, artillery, napalm, helicopter, dogs, RC bomb, turret, cloak, portal, endurance, air support) | 45 | mod tools `_zombiemode_ability*.gsc` (12 files, HUD slots, wall buys, round unlocks), every buy / used / earned / unavailable string in retail, `zom_ability_airstrike_*` and `zom_ability_napalm_*` icons, also strings for Time Distortion and Radar | wall-buy placements, icons for 9 abilities, not in retail zones |
| Solo lives | 40 | mod tools `_zombiemode_solo.gsc`, retail strings `ZOMBIE_SOLO_LIFE_LOST` / `ZOMBIE_EXTRA_LIFE`, icon name `zom_icon_player_life` | not in retail zones |
| Power cell objective | 35 | mod tools `_zombiemode_powercell.gsc`, retail pickup / insert strings, sound alias names | pickup and drop-off entities, model |
| Boss zombie | 30 | mod tools `_zombiemode_ai_boss.gsc` (1245 lines, shockwave ground hit, proximity wake) | spawner entities, anims and model not confirmed |
| Ranks, challenges, titles | 30 | mod tools `_zombiemode_rank.gsc`, `_zombiemode_challenges.gsc`, retail strings (`ZOMBIE_XP_REWARD`, `ZOMBIE_AWARDS_AND_TITLES`, `ZOMBIE_CHALLENGES`) | stats tables, menus |
| Versus | 25 | mod tools `_zombiemode_versus.gsc` (317 lines, team volumes, per-team spawns), retail strings `ZOMBIE_VERSUS`, `MENU_VS_MODE_CAPS`, `ZOMBIE_PLAYERZOMBIE_DOWNED` | team volumes on any map, menu |
| zombie_mountain map | 3 | arena entry in `coopmaps.arena`, `vision/zombie_mountain.vision` | the map |
| Paris transporter | 2 | 2 strings (`ZOMBIE_PARIS_TRANSPORTER_*`) | everything else |

## Campaign and co-op

| Item | % | Ships | Missing |
|---|---|---|---|
| Campaign co-op and Arcade mode | 35 | retail `_cooplogic.gsc`, `_coop_weaponswap.gsc`, `skilltable_coop.csv`, `coop_arcademode.cfg`, arcade menus, `front_end_coop.bik`, `MENU_ARCADE_*` strings, mod tools `_arcademode.gsc` (1701 lines) and `_challenges_coop.gsc` | lobby flow, arcade script not in retail |
| Special Ops (so_bloodbath_mp_cairo, so_thunt_mp_cairo) | 15 | retail `_specialops.gsc`, `sop` gametype stub, arena entries, `MENU_SO_MODE_*` strings | both maps |
| Horse riding | 15 | mod tools `_horse.gsc` (522 lines) | model, anims, any level that uses it |

## Caveats

- Judged from file contents only, nothing was run in game
- A script being only in the mod tools means the retail game cannot run it without a mod
- DLC maps beyond the 14 launch MP maps were not checked for War placements

## Credits

- OpenAssetTools (Unlinker) for zone listing and dumping
