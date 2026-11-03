# BO2 server built-ins the stock zombies maps call, by call site count

Which of the ~1,500 T6 server built-ins the six stock zm maps actually call, how often, and what our script VM does with
each. Generated from the built-in tables in [builtin_tables.md](builtin_tables.md) and a static scan of each map's
compiled scripts (common_zm, patch_zm, the map and its patch). Server side only, no CSC. The real/stub/missing columns
describe E115's VM, the names and site counts describe the game.

- real: registered and does what the game would (offline)
- stub: registered as a stand-in that does nothing (Builtins::stub); its first call logs `stub builtin called: name`
- missing: not registered; the VM returns undefined and the first call logs `missing builtin called: name`
- sites: static call sites outside /# #/ dev blocks (dev-only calls never run in a release game)

## Totals

| table | T6 names | real | stub | missing | needed by zm | needed real | needed stub | needed missing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| server functions + methods | 929 | 363 | 148 | 418 | 493 | 353 | 140 | 0 |
| player methods | 278 | 136 | 34 | 108 | 167 | 133 | 34 | 0 |
| actor methods | 109 | 36 | 13 | 60 | 47 | 34 | 13 | 0 |
| vehicle methods | 91 | 6 | 17 | 68 | 23 | 6 | 17 | 0 |
| helicopter methods | 29 | 4 | 9 | 16 | 13 | 4 | 9 | 0 |
| script mover methods | 22 | 15 | 3 | 4 | 17 | 14 | 3 | 0 |
| hud elem methods | 29 | 15 | 4 | 10 | 18 | 14 | 4 | 0 |

All names called by the six maps (release sites): **784**, real 558, stub 221, missing 5.
Call sites: real 56576, stub 5338, missing 18.
Registered by us but not in the T6 server tables (core/opcode-backed, shims, other games): 36.

## Per map

| map | names called | real | stub | missing | missing sites |
|---|---:|---:|---:|---:|---:|
| zm_transit | 711 | 517 | 189 | 5 | 5 |
| zm_nuked | 668 | 497 | 170 | 1 | 1 |
| zm_highrise | 665 | 495 | 169 | 1 | 1 |
| zm_prison | 710 | 526 | 179 | 5 | 5 |
| zm_buried | 703 | 516 | 182 | 5 | 5 |
| zm_tomb | 723 | 522 | 200 | 1 | 1 |

## Called but missing (5)

Highest first. The five left are gametype callbacks referenced as ::name with no definition in the loaded files, not engine builtins. `()` marks a function, otherwise a method. Many are MP-only dog/turret/vehicle paths the zm maps carry but rarely reach.

| builtin | table | sites | transit | nuked | highrise | prison | buried | tomb | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| wavespawntimer() | - | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| onpostinitgametype() | - | 3 | 1 |  |  | 1 | 1 |  |  |
| onpreinitgametype() | - | 3 | 1 |  |  | 1 | 1 |  |  |
| onspawnzombie() | - | 3 | 1 |  |  | 1 | 1 |  |  |
| onstartgametype() | - | 3 | 1 |  |  | 1 | 1 |  |  |

## Called stubs (221)

Mostly stats, logging, objectives, rumble and cosmetic physics: right to do nothing offline unless noted in the code.

| builtin | table | sites | transit | nuked | highrise | prison | buried | tomb | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| addplayerstat | S | 726 | 121 | 121 | 121 | 121 | 121 | 121 |  |
| incrementcounter() | S | 690 | 116 | 114 | 116 | 114 | 116 | 114 |  |
| addweaponstat | S | 330 | 55 | 55 | 55 | 55 | 55 | 55 |  |
| addgametypestat | S | 216 | 36 | 36 | 36 | 36 | 36 | 36 |  |
| blank() | - | 180 | 30 | 30 | 30 | 30 | 30 | 30 |  |
| pixendevent() | S | 180 | 30 | 30 | 30 | 30 | 30 | 30 |  |
| bbprint() | S | 169 | 32 | 28 | 27 | 27 | 28 | 27 |  |
| pixbeginevent() | S | 162 | 27 | 27 | 27 | 27 | 27 | 27 |  |
| openmenu | Splayer | 126 | 21 | 21 | 21 | 21 | 21 | 21 |  |
| startragdoll | S | 86 | 14 | 12 | 14 | 13 | 15 | 18 |  |
| setmatchtalkflag() | S | 77 | 17 | 7 | 7 | 17 | 22 | 7 |  |
| getteamscore() | S | 60 | 10 | 10 | 10 | 10 | 10 | 10 |  |
| logstring() | S | 54 | 9 | 9 | 9 | 9 | 9 | 9 |  |
| incrementplayerstat | Splayer | 48 | 8 | 8 | 8 | 8 | 8 | 8 |  |
| isbonuscardactive | S | 48 | 8 | 8 | 8 | 8 | 8 | 8 |  |
| melee | Sactor | 48 | 8 | 8 | 8 | 8 | 8 | 8 | NavActors lands the zombie and dog hits itself; a script hit too would double them |
| setplayernamestring | Shud | 48 | 8 | 8 | 8 | 8 | 8 | 8 |  |
| getloadoutitem | S | 42 | 7 | 7 | 7 | 7 | 7 | 7 |  |
| objective_state() | S | 40 | 6 | 6 | 6 | 6 | 6 | 10 |  |
| launchragdoll | S | 38 | 7 | 5 | 7 | 6 | 6 | 7 |  |
| addplayerstatwithgametype | S | 36 | 6 | 6 | 6 | 6 | 6 | 6 |  |
| logprint() | S | 36 | 6 | 6 | 6 | 6 | 6 | 6 |  |
| removeinfluencer() | S | 36 | 6 | 6 | 6 | 6 | 6 | 6 |  |
| updatestatratio | S | 36 | 6 | 6 | 6 | 6 | 6 | 6 |  |
| playrumbleonentity | S | 32 | 5 | 4 | 4 | 6 | 7 | 6 |  |
| setphysparams | S | 32 | 4 | 3 | 4 | 4 | 11 | 6 |  |
| objective_position() | S | 31 | 5 | 5 | 5 | 5 | 5 | 6 |  |
| addbonuscardstat | S | 30 | 5 | 5 | 5 | 5 | 5 | 5 |  |
| finishvehicledamage | Sveh | 30 | 5 | 5 | 5 | 5 | 5 | 5 |  |
| finishvehicleradiusdamage | Sveh | 30 | 5 | 5 | 5 | 5 | 5 | 5 |  |
| isweaponviewonlylinked | Splayer | 30 | 5 | 5 | 5 | 5 | 5 | 5 |  |
| profilelog_endtiming() | S | 30 | 5 | 5 | 5 | 5 | 5 | 5 |  |
| objective_add() | S | 28 | 4 | 4 | 4 | 4 | 4 | 8 |  |
| gib | S | 27 | 4 | 4 | 4 | 4 | 4 | 7 |  |
| isplayeronsamemachine | Splayer | 25 | 4 | 4 | 4 | 4 | 4 | 5 |  |
| physicsexplosionsphere() | S | 25 | 4 | 4 | 4 | 5 | 4 | 4 |  |
| playrumbleonposition() | S | 25 | 4 | 4 | 4 | 4 | 4 | 5 |  |
| enableinfluencer() | S | 24 | 4 | 4 | 4 | 4 | 4 | 4 |  |
| objective_visibleteams() | S | 24 | 4 | 4 | 4 | 4 | 4 | 4 |  |
| profilelog_begintiming() | S | 24 | 4 | 4 | 4 | 4 | 4 | 4 |  |
| recordplayerstats() | S | 24 | 4 | 4 | 4 | 4 | 4 | 4 |  |
| setinfluencerteammask() | S | 24 | 4 | 4 | 4 | 4 | 4 | 4 |  |
| objective_clearplayerusing() | S | 20 | 3 | 3 | 3 | 3 | 3 | 5 |  |
| objective_setplayerusing() | S | 19 | 3 | 3 | 3 | 3 | 3 | 4 |  |
| adddemobookmark() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| getbaseweaponitemindex() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| isweaponoverheating | Splayer | 18 | 4 | 2 | 2 | 2 | 6 | 2 |  |
| kick() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| logstring | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| luinotifyevent | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| makegrenadedud | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| recordplayerdeathzombies | Splayer | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| recordplayerrevivezombies | Splayer | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| resettimeout() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| setteamhasmeat() | S | 18 | 6 |  |  | 6 | 6 |  |  |
| spawnpathnode() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| uploadstats() | S | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  |
| clientclaimtrigger | S | 14 | 2 | 2 | 4 | 2 | 2 | 2 |  |
| objective_onentity() | S | 13 | 2 | 2 | 2 | 2 | 2 | 3 |  |
| setgameendtime() | S | 13 | 2 | 2 | 2 | 2 | 3 | 2 |  |
| setroundsplayed() | S | 13 | 2 | 2 | 2 | 2 | 3 | 2 |  |
| announcement() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| clientreleasetrigger | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| detachshieldmodel | S | 12 | 3 | 1 | 1 | 3 | 1 | 3 |  |
| devaddpitch | Sent | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| devaddroll | Sent | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| devaddyaw | Sent | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| dropscavengeritem | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| getcorpseanim | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| getdeltaturnyaw | Sactor | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| getmotionangle | Sactor | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| getoccupantseat | Sveh | 12 | 2 | 2 | 2 | 2 | 2 | 2 | nobody rides a vehicle seat offline (the bus is stood on), so undefined is right |
| getsnapshotackindex | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| getvehicleoccupied | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 | as getoccupantseat |
| ghostindemo | S | 12 | 1 | 1 | 1 | 6 | 1 | 2 |  |
| giveachievement | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| isremotecontrolling | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| isvehicleimmunetodamage | Sveh | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| matchrecorderincrementheaderstat() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| obituary() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| objective_team() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| pixmarker() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| placespawnpoint | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| recordkillmodifier | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| recordzombiezone | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| resetmissiledetonationtime | S | 12 | 1 | 1 | 1 | 3 | 1 | 5 |  |
| sendfaceevent | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| setflashbanged | Sactor | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| setforcenocull | S | 12 | 1 | 1 | 1 | 3 | 1 | 5 |  |
| sethostmigrationstatus() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| setinitialplayersconnected() | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| settalktospecies | Sactor | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| setturretcarried | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 | carrying is the link carryturret makes |
| startfadingblur | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| stoprumble | S | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| undolaststand | Splayer | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  |
| isinscriptedstate | Sactor | 11 | 1 | 1 | 3 | 1 | 4 | 1 |  |
| setplacementhint | Splayer | 9 | 3 |  |  | 3 |  | 3 | hud-only hint while placing the riot shield |
| setelectrified | S | 8 | 3 | 1 | 1 | 1 | 1 | 1 |  |
| setpitchorient | Sactor | 8 | 1 | 2 | 1 | 1 | 2 | 1 |  |
| setvehvelocity | Sveh | 8 |  |  |  |  | 1 | 7 |  |
| objective_clearentity() | S | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  |
| objective_setgamemodeflags() | S | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  |
| objective_setprogress() | S | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  |
| setangularvelocity | Sveh | 7 |  |  |  |  | 1 | 6 |  |
| setturrettype | S | 7 | 2 | 1 | 1 | 1 | 1 | 1 | engine-side turret type, nothing reads it offline |
| setvisibletoteam | S | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  |
| startrevive | Splayer | 7 | 1 | 1 | 1 | 2 | 1 | 1 |  |
| stoprevive | Splayer | 7 | 1 | 1 | 1 | 2 | 1 | 1 |  |
| turnedhuman | Splayer | 7 | 1 | 1 | 1 | 1 | 2 | 1 |  |
| addtestclient() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| ban() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| bbpostdemostreamstatsforround() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| clearalltextafterhudelem | Shud | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| clientannouncement() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| cloneplayer | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| deactivateclientexploder() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| directionalhitindicator | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| disablezombies() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| docowardswayanims | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| enablezombies() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| fakedamagefrom | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| finishmeleehit | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| gamehistoryfinishmatch | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| gamehistorystartmatch | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| getflashbangedstrength | Sactor | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| getgametypeenumfromname() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| isempjammed | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| isitemlocked | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| islookingat | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| isragdoll | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| isusingoffhand | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| isweaponspecificuse() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| map_restart() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| meleewithoffset | Sactor | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| missionfailed() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| nearnode | Sactor | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| needsrevive | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| objective_getgamemodeflags() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| objective_icon() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| physicsexplosioncylinder() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| playerlinkedoffsetenable | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| predictspawnpoint | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| recordmatchsummaryzombieendgamedata() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| recordplayerdownzombies | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| recordplayermatchend() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| recordzombieroundend() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| recordzombieroundstart() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| releaseclaimedtrigger | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| relinktoturret | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| reportmtu() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setclientnamemode() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setcontents | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setcurrentspectatorclient | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setdemointermissionpoint() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setignoreentfortrigger | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setmapcenter() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setneargoalnotifydist | Sheli | 6 |  |  |  |  | 1 | 5 |  |
| setperkfortrigger | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setperks | Shud | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setscriptmoverflag | S | 6 | 2 |  |  | 2 |  | 2 |  |
| setslowmotion() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setspawnpointrandomvariation() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setteamscore() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| settenthstimerup | Shud | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| setturretowner | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 | scripts keep .owner themselves |
| skillupdate() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| sprintuprequired | Splayer | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| startfiring | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| startscriptedanim | Sactor | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| stopallrumbles() | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| stopfiring | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| stopshootturret | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| uploadleaderboards | S | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  |
| cancelaimove | Sveh | 5 |  |  |  |  | 3 | 2 |  |
| applyknockback | Splayer | 4 | 2 |  |  | 1 | 1 |  |  |
| stoppoisoning | S | 4 | 4 |  |  |  |  |  |  |
| attachshieldmodel | S | 3 | 1 |  |  | 1 |  | 1 |  |
| clearlookatent | Sheli | 3 |  |  |  |  |  | 3 |  |
| dontinterpolate | S | 3 |  |  |  |  | 3 |  |  |
| getheliheightlockheight | Sheli | 3 |  |  |  |  |  | 3 |  |
| makevehicleunusable | Sveh | 3 |  |  |  |  | 2 | 1 |  |
| nodescanpath() | S | 3 | 1 |  |  | 1 | 1 |  |  |
| nodesvisible() | S | 3 | 1 |  |  | 1 | 1 |  |  |
| pathvariableoffset | Sveh | 3 |  |  |  |  | 1 | 2 |  |
| setculldist() | S | 3 | 1 |  |  | 1 |  | 1 |  |
| setriotshieldfailhint | Splayer | 3 | 1 |  |  | 1 |  | 1 |  |
| setvehicleavoidance | Sveh | 3 |  |  |  |  |  | 3 |  |
| vehcansee | Sveh | 3 |  |  |  |  |  | 3 |  |
| clearpitchorient | Sactor | 2 |  | 2 |  |  |  |  |  |
| createdynentandlaunch() | S | 2 |  |  |  | 1 |  | 1 |  |
| fireweapon | Sheli | 2 |  |  |  |  |  | 2 |  |
| forceslick | Splayer | 2 |  |  | 2 |  |  |  |  |
| getseatoccupant | Sveh | 2 |  |  |  |  |  | 2 | as getoccupantseat |
| setcurrentweaponspinlerp | Splayer | 2 | 2 |  |  |  |  |  |  |
| setlightintensity | S | 2 |  |  |  |  |  | 2 |  |
| setlookatent | Sheli | 2 |  |  |  |  |  | 2 |  |
| setphysacceleration | Sveh | 2 |  |  |  |  | 1 | 1 |  |
| setturrettargetent | Sheli | 2 |  |  |  |  |  | 2 |  |
| setvolfog() | S | 2 | 1 | 1 |  |  |  |  |  |
| startpoisoning | S | 2 | 2 |  |  |  |  |  |  |
| stoplocalsound | Splayer | 2 |  |  |  | 1 |  | 1 |  |
| bloodimpact | S | 1 |  |  |  |  | 1 |  |  |
| drivepath | Sveh | 1 |  |  |  |  |  | 1 |  |
| getcurrentweaponspinlerp | Splayer | 1 | 1 |  |  |  |  |  |  |
| getpartname() | S | 1 |  |  |  |  |  | 1 |  |
| getpathlength | Sactor | 1 |  |  |  |  | 1 |  |  |
| isinmovemode | Splayer | 1 | 1 |  |  |  |  |  |  |
| maketurretunusable | S | 1 | 1 |  |  |  |  |  |  |
| makeunusable | S | 1 | 1 |  |  |  |  |  |  |
| pathfixedoffsetclear | Sveh | 1 |  |  |  |  |  | 1 |  |
| pathvariableoffsetclear | Sveh | 1 |  |  |  |  |  | 1 |  |
| physicsjetthrust() | S | 1 | 1 |  |  |  |  |  |  |
| precacheturret() | S | 1 | 1 |  |  |  |  |  |  |
| seatgetweapon | Sveh | 1 |  |  |  |  |  | 1 |  |
| setconvergencetime | S | 1 | 1 |  |  |  |  |  |  |
| setdefaultdroppitch | S | 1 | 1 |  |  |  |  |  |  |
| setheliheightlock | Sheli | 1 |  |  |  |  |  | 1 |  |
| sethoverparams | Sheli | 1 |  |  |  |  |  | 1 |  |
| setturrettargetvec | Sheli | 1 |  |  |  |  |  | 1 |  |
| showindemo | S | 1 |  |  |  |  |  | 1 |  |

## Dev-only calls to missing builtins (19)

Only inside /# #/ blocks; never run in a release game.

print3d() 291, line() 286, adddebugcommand() 219, fgetarg() 108, circle() 75, openfile() 42, closefile() 42, debugstar() 39, getentnum 36, fprintln() 30, print() 30, fprintfields() 24, freadln() 24, box() 13, getfogsettings() 6, setexpfog() 6, getreflectionlocs() 6, getreflectionorigin() 6, execdevgui() 5
