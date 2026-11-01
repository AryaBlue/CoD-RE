# Script VM gaps: builtins the T6 zm scripts call that the VM doesn't register

Made by `tools/script_pass/vm_gaps.py`. It reads gsc-tool's decompile of each map's exported scripts (local only, never
committed), takes every call that isn't one of that map's script functions, and checks it against the names the VM
registers (`.add("name", ...)` in src/script, src/game and games/reforged).

- [V] A name is listed here only when no `.add` registers it and some stock call site calls it.
- [I] Counts are static call sites in the decompiled text, not runtime calls. A function or method is told apart by the
  token before it, so a few calls through a parenthesised expression may be counted as functions.
- [I] The system is a name-pattern guess, except for the names in TRIAGE, which were placed by reading their call sites.
- harmless: in tools/script_pass/harmless_builtins.txt (no gameplay effect offline).
- [V] Calls inside dev blocks (`/# ... #/`) are left out: they only run in developer builds.
- [I] Stock usage is counted from the call sites, in our words: the argument counts seen, the commonest receivers
  of a method, and how often the result is assigned, tested in a condition or passed on. No script text is quoted.

Owners: the VM core has the VM, CoreBuiltins.cpp, WorldBuiltins.cpp and the entity, trigger, physics and
damage builtins; the player/hud side has player, hud, sound, fx, weapon, stats/online/debug and math/string/array
(t6_vm_builtin_gaps_player.md); the AI side has actor/AI (ActorBuiltins.cpp, NavActors).

The Reference column is filled as each builtin is implemented: the stock usage above, then public docs
(codresearch wiki, Plutonium's T6 function list, zeroy's script reference, OAT's T6 headers, docs/research) and, for
behaviour-critical ones, notes from the T6 executable (behaviour only, our own code), each tagged [V]/[I].

Maps: zm_nuked, zm_transit, zm_highrise, zm_prison, zm_buried, zm_tomb. 117 distinct unregistered names, 1115 call sites.

## actor/AI (42), AI side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| setanimstate | method | 222 | 37 | 37 | 37 | 37 | 37 | 37 |  | 1 arg; on self; result unused | |
| setaimanimweights | method | 132 | 22 | 22 | 22 | 22 | 22 | 22 | yes | 2 args; on self; result unused | |
| melee | method | 48 | 8 | 8 | 8 | 8 | 8 | 8 |  | 0-1 args; on self; result assigned 38% | |
| setteam | method | 34 | 5 | 6 | 5 | 6 | 6 | 6 |  | 1 arg; on self, other; result unused | |
| animcustom | method | 30 | 3 | 6 | 6 | 3 | 6 | 6 |  | 1 arg; on self, zombie, other; result passed on 3% | |
| setvehgoalpos | method | 26 |  |  |  |  | 1 | 25 |  | 2-4 args; on self; result assigned 23%, tested 12% | |
| sendfaceevent | method | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  | 1 arg; on other; result unused | |
| spawnpathnode | function | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  | 3-7 args; result unused | |
| setteamhasmeat | function | 18 |  | 6 |  | 6 | 6 |  |  | 2 args; result unused | |
| allowedstances | method | 15 | 2 | 2 | 2 | 2 | 3 | 4 |  | 1 arg; on self, other; result unused | |
| settalktospecies | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 1 arg; on self; result unused | |
| getdeltaturnyaw | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 0 args; on self; result assigned 100% | |
| getcorpseanim | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 0 args; on other; result assigned 100% | |
| animhasnotetrack | function | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 2 args; result tested 100% | |
| setpitchorient | method | 8 | 2 | 1 | 1 | 1 | 2 | 1 |  | 0 args; on self, other; result unused | |
| turnedhuman | method | 7 | 1 | 1 | 1 | 1 | 2 | 1 |  | 0 args; on self; result unused | |
| meleewithoffset | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result unused | |
| isingoal | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result tested 100% | |
| startscriptedanim | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 5 args; on self; result unused | |
| isstanceallowed | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result passed on 100% | |
| nearnode | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result tested 100% | |
| releaseclaimedtrigger | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result passed on 100% | |
| finishmeleehit | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 7 args; on self; result unused | |
| isragdoll | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result tested 100% | |
| setteamscore | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 2 args; result unused | |
| missionfailed | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; result unused | |
| docowardswayanims | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on self; result assigned 100% | |
| findpath | function | 6 |  |  | 1 | 2 | 1 | 2 |  | 2-5 args; result tested 100% | |
| setneargoalnotifydist | method | 6 |  |  |  |  | 1 | 5 |  | 1 arg; on self, other; result passed on 17% | |
| cancelaimove | method | 5 |  |  |  |  | 3 | 2 |  | 0 args; on self, other; result passed on 20% | |
| clearvehgoalpos | method | 5 |  |  |  |  | 3 | 2 |  | 0 args; on self, other; result passed on 20% | |
| nodesvisible | function | 3 |  | 1 |  | 1 | 1 |  |  | 2 args; result tested 100% | |
| nodescanpath | function | 3 |  | 1 |  | 1 | 1 |  |  | 2 args; result tested 100% | |
| setriotshieldfailhint | method | 3 |  | 1 |  | 1 |  | 1 |  | 0 args; on self; result unused | |
| pathvariableoffset | method | 3 |  |  |  |  | 1 | 2 |  | 2 args; on self; result unused | |
| clearpitchorient | method | 2 | 2 |  |  |  |  |  |  | 0 args; on self; result unused | |
| vehicle_path | function | 2 |  | 1 |  |  |  | 1 |  | 0 args; result passed on 100% | |
| getspawnerarray | function | 1 |  |  |  |  | 1 |  |  | 2 args; result assigned 100% | |
| getpathlength | method | 1 |  |  |  |  | 1 |  |  | 0 args; on self; result assigned 100% | |
| pathvariableoffsetclear | method | 1 |  |  |  |  |  | 1 |  | 0 args; on self; result unused | |
| pathfixedoffsetclear | method | 1 |  |  |  |  |  | 1 |  | 0 args; on self; result unused | |
| drivepath | method | 1 |  |  |  |  |  | 1 |  | 1 arg; on self; result unused | |

## player (12), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| itemweaponsetammo | method | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  | 2-3 args; on other, self; result unused | |
| cloneplayer | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result assigned 100% | |
| canplayerplaceturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result assigned 100% | |
| player | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result passed on 100% | |
| stoppoisoning | method | 4 |  | 4 |  |  |  |  |  | 0 args; on self, player; result unused | |
| attachshieldmodel | method | 3 |  | 1 |  | 1 |  | 1 |  | 2 args; on self; result unused | |
| startpoisoning | method | 2 |  | 2 |  |  |  |  |  | 0 args; on self, player; result unused | |
| setcurrentweaponspinlerp | method | 2 |  | 2 |  |  |  |  |  | 1 arg; on self; result unused | |
| fireweapon | method | 2 |  |  |  |  |  | 2 |  | 0-3 args; on self; result unused | |
| isgodmode | function | 1 |  | 1 |  |  |  |  |  | 1 arg; result assigned 100% | |
| getcurrentweaponspinlerp | method | 1 |  | 1 |  |  |  |  |  | 0 args; on self; result passed on 100% | |
| seatgetweapon | method | 1 |  |  |  |  |  | 1 |  | 1 arg; on self; result assigned 100% | |

## weapon (4), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dropitem | method | 18 | 3 | 3 | 3 | 3 | 3 | 3 |  | 1 arg; on self; result assigned 67% | |
| dropscavengeritem | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 1 arg; on self; result assigned 100% | |
| canplaceriotshield | method | 6 |  | 2 |  | 2 |  | 2 |  | 1 arg; on self; result assigned 100% | |
| deployriotshield | function | 3 |  | 1 |  | 1 |  | 1 |  | 2 args; result assigned 100% | |

## sound (1), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stoplocalsound | method | 2 |  |  |  | 1 |  | 1 |  | 1 arg; on self; result unused | |

## fx (1), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| setvolfog | function | 2 | 1 | 1 |  |  |  |  | yes | 18 args; result unused | |

## physics (3), VM core

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| setvehvelocity | method | 8 |  |  |  |  | 1 | 7 |  | 1 arg; on self; result unused | |
| createdynentandlaunch | function | 2 |  |  |  | 1 |  | 1 |  | 5 args; result unused | |
| physicsjetthrust | function | 1 |  | 1 |  |  |  |  |  | 5 args; result unused | |

## entity (11), VM core

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| getentitytype | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 0 args; on other; result assigned 100% | |
| useby | method | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  | 1 arg; on other; result passed on 14% | |
| spawnturret | function | 7 | 1 | 2 | 1 | 1 | 1 | 1 |  | 3 args; result assigned 100% | |
| entrance | method | 7 | 1 | 1 | 1 | 1 | 1 | 2 |  | 1 arg; on other; result passed on 100% | |
| getsortedspawnpoints | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 5 args; result assigned 100% | |
| relinktoturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result unused | |
| get_closest_damage_refs | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; result passed on 100% | |
| setscriptmoverflag | method | 6 |  | 2 |  | 2 |  | 2 |  | 1 arg; on other; result unused | |
| isinmovemode | method | 1 |  | 1 |  |  |  |  |  | 2 args; on self; result assigned 100% | |
| makeunusable | method | 1 |  | 1 |  |  |  |  |  | 0 args; on other; result unused | |
| getpartname | function | 1 |  |  |  |  |  | 1 |  | 2 args; result assigned 100% | |

## vehicle/turret (28), VM core

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| getoccupantseat | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 1 arg; on self, other; result assigned 100% | |
| getvehicleoccupied | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 0 args; on other, self; result assigned 100% | |
| setturretcarried | method | 12 | 2 | 2 | 2 | 2 | 2 | 2 |  | 1 arg; on other; result unused | |
| setturrettype | method | 7 | 1 | 2 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result unused | |
| setturretowner | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result unused | |
| carryturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 3 args; on self; result unused | |
| stopcarryturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on self; result unused | |
| startfiring | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result unused | |
| stopshootturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result unused | |
| stopfiring | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result unused | |
| isfiringturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on self; result tested 100% | |
| shootturret | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on self; result unused | |
| makevehicleunusable | method | 3 |  |  |  |  | 2 | 1 |  | 0 args; on other, self; result passed on 33% | |
| setvehicleavoidance | method | 3 |  |  |  |  |  | 3 |  | 1 arg; on self; result unused | |
| vehcansee | method | 3 |  |  |  |  |  | 3 |  | 1 arg; on self; result tested 100% | |
| getheliheightlockheight | method | 3 |  |  |  |  |  | 3 |  | 1 arg; on self; result assigned 100% | |
| clearlookatent | method | 3 |  |  |  |  |  | 3 |  | 0 args; on self; result unused | |
| forceslick | method | 2 |  |  | 2 |  |  |  |  | 1 arg; on player; result unused | |
| setturrettargetent | method | 2 |  |  |  |  |  | 2 |  | 1 arg; on self; result unused | |
| setlookatent | method | 2 |  |  |  |  |  | 2 |  | 1 arg; on self; result unused | |
| getseatoccupant | method | 2 |  |  |  |  |  | 2 |  | 1 arg; on self; result assigned 100% | |
| maketurretunusable | method | 1 |  | 1 |  |  |  |  |  | 0 args; on other; result unused | |
| setmode | method | 1 |  | 1 |  |  |  |  |  | 1 arg; on other; result unused | |
| setdefaultdroppitch | method | 1 |  | 1 |  |  |  |  |  | 1 arg; on other; result unused | |
| setconvergencetime | method | 1 |  | 1 |  |  |  |  |  | 1 arg; on other; result unused | |
| setturretteam | method | 1 |  | 1 |  |  |  |  |  | 1 arg; on other; result unused | |
| sethoverparams | method | 1 |  |  |  |  |  | 1 |  | 3 args; on self; result unused | |
| setheliheightlock | method | 1 |  |  |  |  |  | 1 |  | 1 arg; on self; result unused | |

## math/string (4), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| setplacementhint | method | 9 |  | 3 |  | 3 |  | 3 |  | 1 arg; on self; result unused | |
| check_point_in_active_zone | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; result assigned 100% | |
| string | method | 2 |  |  |  | 1 |  | 1 |  | 1 arg; on other; result passed on 100% | |
| getvehiclearray | function | 1 |  |  |  | 1 |  |  |  | 1 arg; result passed on 100% | |

## stats/online (4), player side

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hasanimstatefromasd | method | 19 | 2 | 2 | 2 | 2 | 3 | 8 |  | 1 arg; on self; result tested 100% | |
| getanimstatefromasd | method | 17 | 1 | 1 | 1 | 1 | 12 | 1 |  | 0 args; on self; result assigned 41%, tested 59% | |
| addtestclient | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; result assigned 100% | |
| showindemo | method | 1 |  |  |  |  |  | 1 |  | 0 args; on other; result passed on 100% | |

## not a builtin (7), no owner (a decompile artefact or a script function from another file)

| Builtin | Kind | Calls | nuked | transit | highrise | prison | buried | tomb | Harmless | Stock usage | Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| unmatched | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result passed on 100% | |
| value | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result passed on 100% | |
| buildable_think | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 0 args; on other; result passed on 100% | |
| index | function | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; result passed on 100% | |
| module | method | 6 | 1 | 1 | 1 | 1 | 1 | 1 |  | 1 arg; on other; result passed on 100% | |
| item | method | 2 |  |  |  | 1 |  | 1 |  | 1 arg; on other; result passed on 100% | |
| craftable_think | method | 2 |  |  |  | 1 |  | 1 |  | 0 args; on other; result passed on 100% | |

## Sources and credits

- gsc-tool by xensik: the decompiler the inventory reads (run locally on the user's own game files).
- JezuzLizard's Recompilable GSCs for BO2 zombies and multiplayer (now plutoniummod/t6-scripts): hand-fixed T6
  scripts, read only as a behaviour reference where our decompile looks odd. Nothing from it is in the repo.
- Per-builtin references (codresearch wiki, Plutonium's T6 function list, zeroy's script reference, OAT's T6
  headers) are credited in the Reference column as entries are filled.

