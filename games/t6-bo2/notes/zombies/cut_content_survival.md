# BO2 cut content - how much of each cut mode, map and feature still ships (survival %)

Survey of the retail PC files (exes, zones, English strings, map entities). Names and locations only.

## How the % is scored

- Six parts: rules script, map or placement data, models and effects, UI text, sound, engine hooks
- 100% = everything needed to play is in the shipped files and only needs switching on
- Sound was only checked for Meat, so most scores assume nothing for sound
- Tools: OpenAssetTools Unlinker (zone lists and dumps), own string scans of the exes

## Zombies

| Item | % | Ships | Missing |
|---|---|---|---|
| Bus ambush round (Tranzit) | 80 | `zm_transit_ambush.gsc` in zm_transit_patch, called from the bus script, 5 ambush stops in the bus schedule (tunnel, forest, cornfields, power2town, bridge), dog spawns, lightning and bus fire effects | random trigger tests are empty in the dump, only the bus-out-of-fuel test is left, and fuel is not used |
| Meat (zmeat) on Town, Farm, Tunnel | 70 | `zmeat.gsc`, `_zm_game_module_meat*.gsc`, `zmeat.csc`, `item_meat_zm`, anims, fx, scoreboard, team spawns, 1217 encounter entities, exe hooks `setteamhasmeat` / `hasmeat` / `sideHasMeat` | sign models `p6_zm_sign_meat_01..06_on`, announcer VO, minigun and splitter trigger entities, the `add_map_gamemode` registration |
| Turned on Town and Farm | 60 | Turned rules ship for Diner, 22 and 24 respawn points tagged `zcleansed_town` / `zcleansed_farm` | location registration, location UI |
| Dive to Nuke on Buried and Mob of the Dead | 60 | `_zm_perk_divetonuke.gsc` + `.csc` in both patches, `specialty_divetonuke_zombies` icon, `p6_zm_al_vending_nuke` machine textures in zm_prison | machine placement, bottle weapon not confirmed |
| Cornfield location | 55 | 4 player spawns, 35 Turned respawns, perk set `znml_perks_cornfield`, 8 vehicles, tags for NML / Turned / Grief | location registration, menu entry |
| Moon kit (P.E.S., Hacker, hackables, jump pads) | 45 | `_zm_equip_gasmask`, `_zm_equip_hacker`, 7 `_zm_hackables_*`, `_zm_jump_pad` in patch_zm, exe names `equip_gasmask_zm` / `equip_hacker_zm`, PDA viewmodel anims | weapon files, models, a map that uses them |
| Race (zrace) on Farm, Power, Town, Tunnel | 40 | courses in the encounter entities (114 / 69 / 41 / 15 objects), team spawns, target sign, `_zm_game_mode_objects.csc`, strings, announcer keys | the rules script itself, `p6_anim_zm_finish_line` |
| No Man's Land (znml) | 20 | gametype name, `znml_preinit` stub, spawn and perk tags on Town and Cornfield | rules script |
| Nacht, Der Riese, Moon rows (DLC5) | 15 | gametypestable rows, load screens, names and descriptions | the maps |
| zmaxis / zrichtofen | 10 | `.txt` stubs, gamesettings (score 7500, 10 min, 3 rounds, 2 teams) | everything else |
| zcontainment / zdeadpool / zpitted | 5 | gametype names, preinit stubs, one Dead Pool string | everything else |
| zm_meat "Hub Test" map | 5 | 2 table rows, 5 strings, `loadscreen_zm_meat` | the map, any exe reference |
| zm_bus_test "Bus Test" map | 3 | table row, name string | the map |

## Multiplayer

| Item | % | Ships | Missing |
|---|---|---|---|
| One Flag (oneflag) | 70 | `oneflag.gsc` ships compiled, reuses CTF placements | mode list entry, own settings file not confirmed |
| Hacker (hack) | 55 | `gamesettings_hack.cfg`, `_bot_hack.gsc`, medals, `scavenger_item_hack_mp`, AI tank hooks | `hack.gsc` |
| WaW War HUD | 15 | `setwargamedata`, `war_a..e`, `mp_twar_spawn` class | script, placements |
| Settings-only modes (pur, hun, nvc, tag, res, wdom, cp, bwars, tdef, sab, twar) | 10 | `.txt` name stubs and gamesettings cfgs | scripts, placements |
| BO1 contracts and deathstreaks | 10 | builtins, strings, `perk_deathStreakCountRequired` | data tables, UI |
| Unbuilt map descriptions (War Museum, Cruise, Firebase, Area 51, tech demo) | 2 | name and description strings | everything |

## Campaign

| Item | % | Ships | Missing |
|---|---|---|---|
| Strike Force: Carrier | 10 | `so_rts_mp_carrier` name, presence and menu strings, challenge name, 7 briefing subtitles | the zone, audio not checked |

## Caveats

- Scores are judged from file contents only, nothing was run in game
- The One Flag and Dive to Nuke rows rest on asset lists, the scripts were not read line by line
- Empty `if` bodies in dumped scripts can also come from stripped developer blocks

## Credits

- OpenAssetTools (Unlinker) for zone listing and dumping
