# Script VM gaps: player, hud, sound, fx, weapon, stats and misc builtins

This is the player-side half of the builtin gap work. The full inventory is [t6_vm_builtin_gaps.md](t6_vm_builtin_gaps.md).

The code lives in three files:
- `src/script/PlayerBuiltins.cpp`: player state.
- `src/script/MiscBuiltins.cpp`: level calls, math and the offline no-ops.
- The tail of `src/script/WeaponBuiltins.cpp`: the weapon extras.

`registerWeaponBuiltins` registers all three, so there is no new entry in the session table. Player and misc names go in through `addIfNew` (`PlayerState.h`), which skips any name an earlier table already registered (core, bridge). Tables registered later, such as world, still override ours. If another table adds a better version, theirs wins in both orders.

Player state is kept in each player's code map under `ctl_<name>`. The game reads it back with `playerControls(vm, player)` (`PlayerState.h`). `ScriptLevel` hands it to the game each frame as `Output::controls`, and `main.cpp` applies it (see "Wiring" below). Invulnerability is applied in `ScriptWorld::damage`.

Tags:
- [V script]: the arguments and the use of the result were checked against the stock call sites.
- [I]: inferred. The engine side was not read.
- No binary RE was done for this batch.

References, used read-only for usage and intent (none of their code is in the repo):
- The stock T6 zm scripts of nuked and buried, decompiled privately with xensik's gsc-tool.
- plutoniummod/t6-scripts (JezuzLizard's recompilable, hand-fixed BO2 GSC; formerly JezuzLizard/Recompilable-gscs-for-BO2-zombies-and-multiplayer), for prison and the other maps.

## Player (PlayerBuiltins.cpp)

| Builtin | Status | Behaviour | Ref |
|---|---|---|---|
| allowstand / allowcrouch / allowprone / allowjump / allowsprint / allowads / allowmelee / allowlean (bool) | done, recorded | `PlayerControls` flags. Undefined errors, as any bool does | [V script] afterlife_leave, zm laststand; [I] engine |
| enable/disable + weapons, offhandweapons, weaponcycling, usability, invulnerability, afterlife, deathstreak, grenadesuicide | done | Flags. Not counted: two disables are undone by one enable | [V script]; [I] not ref-counted |
| enableinvulnerability | done, **wired** | `ScriptWorld::damage` drops a hit on an invulnerable player before any callback (like `god`) | [V script] zm spawn protection; [I] drop point |
| setmovespeedscale / getmovespeedscale | done, recorded | Scale, default 1 | [V script] `setmovespeedscale(0.3)`, `( target.movementspeedmodifier )` |
| setsprintduration / setsprintcooldown | done, recorded | Seconds (4 / 0 in stock) | [V script] |
| playerknockback / setplayercollision (bool) | done, recorded | | [V script] |
| setviewmodel / getviewmodel | done | Kept per player. get answers "" until a set | [V script] `_zm_afterlife` saves the living hands with getviewmodel before the ghost hands |
| setcharacterindex (int) | done, recorded | | [V script] |
| shellshock(name, s) / stopshellshock | done, recorded | Name plus end time (vm ms) for the host's `ShellShock` | [V script] |
| setburn(s) / stopburning | done, recorded | Burn end time | [V script] |
| setblur(amount, s), resetfov, cameraactivate(bool), setclientthirdperson(bool) | done, recorded | | [V script] |
| setdepthoffield, camerasetposition, camerasetlookat, setclientthirdpersonangle, setfreecameralockonallowed, setclientcgobjectivetext, setclientammocounterhide, setclientminiscoreboardhide, setclientcompass, setclienthudhardcore, setclientplayerpushamount, setclientaimlockonpitchstrength, setclientplayersprinttime, setclientnumlives, setclientscriptmainmenu, setclientdrawtalk, setclientnamemode, setspectatepermissions, setentertime, vibrate, setempjammed, closemenu, closeingamemenu, setplayercurrentstreak | done, record only | Their arguments are kept as an array on the entity. They take any entity: stock calls setfreecameralockonallowed on ai and vibrate on script models | [V script] |
| allowspectateteam(team, bool), setclientuivisibilityflag(flag, v) | done, record only | Keyed by the first argument | [V script] |
| setactionslot(slot, kind, weapon) | done, record only | | [V script] |
| setvelocity / getvelocity | done | get answers what set left, else (0,0,0) | [I] no player velocity on the script side |
| getnormalizedmovement / getnormalizedcameramovement | done | (0,0,0) | [I] scripts see no stick input |
| getplayerviewheight | done | 60 standing, 40 crouched, 11 prone, from the stance | [I] stock heights |
| playerlinkto / playerlinktoabsolute / playerlinktodelta / playerlinkweaponviewtoentity | done | `ScriptWorld::linkTo` with no offset: keeps the current offset, view clamps ignored. `unlink` undoes it | [I] |
| iprintln / iprintlnbold (function and method) | done | To `vm.print` (the log) until a hud feed shows them | [V script] |

## Weapons (WeaponBuiltins.cpp)

| Builtin | Status | Behaviour | Ref |
|---|---|---|---|
| useweaponmodel(weapon, model, options) | done | The entity's model becomes the model given, else the def's world model | [V script] wallbuy and box models |
| useweaponhidetags | done, no-op | Our weapon models carry no attachment tags | [I] |
| getweaponstowedmodel → 0, setstowedweapon / clearstowedweapon | done | 0 is the model index for getweaponmodel. The stowed gun is kept per player | [V script] `_weapons::stow_on_back` |
| calcweaponoptions(camo, lens, reticle, colour) | done | Packs the 4 into an int, one byte each. giveweapon ignores it | [V script]; [I] packing |
| getweapondisplayname | done | istring of the def's display name, else the weapon name | [V script] hint parm |
| weaponhasattachment / getweaponsupportedattachments | done | Attachments after `+` in the name; zombies guns have none | [I] |
| getweaponoptic | done | "" | [I] |
| weaponfiretime / weaponreloadtime | done | Seconds, from the def | [V script] `n_reload_time = weaponreloadtime(...)` |
| getweaponammofuel / setweaponammofuel, setweaponoverheating, setheldweaponmodel, weaponplayejectbrass | done | Fuel is kept per weapon (0 by default); the rest are no-ops | [I] |
| getweaponforwarddir | done | The forward vector from the player's angles | [V script] jetgun, staffs; [I] uses the entity angles |
| addweaponstat | no-op, harmless | | stats |
| magicbullet(weapon, start, end, owner) | done | Returns a projectile entity, flown by `ScriptWorld::stepProjectiles` (`ScriptProjectiles.cpp`). Bullet weapons hit at once (8192 u); others fly at 2000 u/s. The first actor hit takes `shotDamage` (MOD_RIFLE_BULLET / MOD_PROJECTILE). Then `explode`(pos) goes to the projectile, a projectile weapon also sends `projectile_impact`(weapon, pos, 0, ent, normal) to the owner, and the entity is deleted | [V script] staffs, blundersplat use the entity, `explode`; [I] speeds, the notify's arguments |
| forcegrenadethrow | done | The player's first offhand grenade with ammo: one is spent, launched from the eye along the view at 800 u/s (1200 u max). `grenade_fire`(ent, weapon) goes to the player. It rests where it lands and goes off after 2.5 s: `explode`, plus splash on actors within 200 u (damageMax, falling off) | [V script] screecher, plane; [I] speed, fuse and radius (not in the export) |
| reviveplayer | done | Health back to maxhealth; the scripts clear `laststand` themselves | [V script] `_zm_laststand` revive; [I] |
| setrevivehintstring(hint, team) | done | The trigger's hint, as sethintstring stores it | [V script] |
| seteverhadweaponall | done, record only | | |

## Level, hud, sound, fx and math (MiscBuiltins.cpp)

| Builtin | Status | Behaviour | Ref |
|---|---|---|---|
| makedvarserverinfo(dvar, value) | done | Sets the dvar only when it is unset | [I] |
| setmatchflag / getmatchflag | done | Kept as the pseudo dvar `matchflag:<name>` | [V script] `hud_zombie`, `disableIngameMenu` |
| setscoreboardcolumns, setminimap | done, record only | `ui:scoreboardcolumns`, `ui:minimap` | [V script] |
| visionsetnaked / visionsetnight / visionsetlaststand / visionsetdamage / visionsetflash | done, record only | `vision:<kind>` = the name | [V script] |
| activateclientexploder / deactivateclientexploder | done, record only | We don't run the client scripts, so the id is only kept (`fx:clientexploder`) | [V script] |
| objective_* (add, delete, state, position, icon, onentity, clearentity, team, visibleteams, setprogress, set/clearplayerusing, setgamemodeflags, set*toall); objective_getgamemodeflags → 0 | done, no-op | Zombies shows no objectives | [I] |
| addsphereinfluencer / addcylinderinfluencer / addboxinfluencer → id; removeinfluencer, enableinfluencer, setspawnpointrandomvariation, setspawnpointsbaseweight, clearspawnpoints, spawnpointsupdate | done, no-op | MP spawn scoring; zombies places players itself | [V script] `_spawning` |
| getplayerspawnid(player) | done | The entity number | [I] blackbox only |
| playsoundtoteam(alias, team) | done | Plays on the ent when a player is on that team (solo) | [V script] powerups |
| playsoundasmaster(alias) | done | A local sound on the ent | [I] |
| soundgetplaybacktime | done | -1 (unknown); the stock scripts then wait a default 1-3 s | [V script] `_zm_audio`, brutus: `if (t >= 0) t *= 0.001; else t = 1` |
| disablegrenadesuicide / enablegrenadesuicide (level) | done, record only | `matchflag:grenadesuicide`. The player method forms are in PlayerBuiltins | [V script] `_zm` init |
| pow, log, exp | done | | |
| blank(...) | done, no-op | `_globallogic`'s do-nothing callback, for zone sets without `_globallogic` | [V script] |
| pix*, bbprint, bbpostdemostreamstatsforround, incrementcounter, profilelog_*, adddemobookmark, setdemointermissionpoint, ghostindemo, record* (zombie round/zone/revive/down, match begin/summary/end, kill modifier, league), add/increment player stats, logprint, logstring, reportmtu, resettimeout, setmatchtalkflag, setinitialplayersconnected, setroundsplayed, uploadstats, uploadleaderboards, bbaddtostat | no-op, harmless | Stats, blackbox, demo, profiling and session: nothing to do offline. New names are appended to `tools/script_pass/harmless_builtins.txt` | |

## Wiring (main.cpp, scripted maps)

These are built and pass-tested with no regressions on transit, highrise, prison and tomb. They are not checked in game.
- **Movement:**
  - freezecontrols (`Output::frozen`, which nothing read before) stops all movement;
  - the allow* flags gate jump, sprint and dive, and a stance that isn't allowed steps to an allowed one;
  - setmovespeedscale multiplies `weaponScale`;
  - setsprintduration scales `sprintDurationScale` against the stock 4 s.
- **Weapons:**
  - disableweapons counts as drinking: no fire, ads or knife;
  - allowads gates ads, and allowmelee gates the knife and the scripts' melee;
  - disableoffhandweapons gates frag and tactical;
  - disableweaponcycling gates switch and the wheel.
- **Use:** disableusability blocks use and use presses, the dev ones included.
- **View:**
  - shellshock / stopshellshock start and stop `lvl.shellShock` from the game's shock file (`<game>/shock/<name>.shock`; a missing file only warns);
  - setblur sets the screen blur, as the higher of it and the shock's [I: 10 = the full 1%].

Viewmodel hands (setviewmodel):
- the guns are exported with their hands baked in, on the map's first `armsByMap` hands (`weapons/<map>/<def>.glb`);
- when the scripts set another listed character's hands, main.cpp reads the map's guns on those hands from the zones in the background (`MpGuns::zmArms`, nothing written) and puts them first in the viewmodel lookup; the held gun swaps when the read is done;
- the glb path only uses a `weapons/<map>/<arms>/` that a convert already made; the converter plans it only when `zmArms` is set, so normal converts don't change;
- hands `armsByMap` doesn't list for the map (the afterlife ghost hands, say) keep the current viewmodel;
- `--script-seed N` sets the script lcg's start, which picks Buried's character in solo; seed 2 gives the old man's hands, seed 1 the engineer's.

Not wired:
- the afterlife ghost hands: they're not in `armsByMap`, so prison keeps the living hands;
- third person and cameraactivate: the game has no third-person or script camera here;
- sprint cooldown: the player movement has no cooldown input.
