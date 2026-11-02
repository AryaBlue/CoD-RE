# BO2 script built-in tables (360 CoDMP)

Where the GSC/CSC built-in tables sit in the BO2 Xbox 360 MP build, what an entry looks like, and how many each
holds. Read from the decrypted image ([t6_360_xex_route.md](../engine/xbox360_symbol_builds.md)) and named from `CoDMP.map`. Marks
are explained in the [notes index](../../../../NOTES.md).

## Entry layout

- [V] 24 bytes, big-endian: name pointer, canonical string id, minimum args, maximum args, handler pointer, type.
- [V] Maximum args `0x7fffffff` means variadic. Type 1 marks a developer-only built-in.
- [V] Functions and methods share the layout. The handler's signature tells them apart: methods take a
  `scr_entref_t`, functions take nothing.
- [V] Where tables sit back to back (the server `functions` array runs straight into its method table) a scan reads
  them as one run; split them by handler signature.

## Tables

| Table | Address | Entries | Notes |
| --- | --- | --- | --- |
| server functions + entity methods (`functions`, `g_scr_main_mp`) | `0x82d718c0` | 620 | [V] only this one has a public `.map` symbol |
| server core (print, assert, dvars, string and maths) | `0x820754d0` | 315 | [V] |
| player methods (`PlayerCmd_*`) | `0x82063f90` | 278 | [V] |
| hud element methods (`HECmd_*`) | `0x8206a210` | 29 | [V] |
| helicopter methods | `0x82074360` | 29 | [V] |
| script mover methods (`ScriptEntCmd_*`) | `0x82081010` | 22 | [V] |
| vehicle methods (`CMD_VEH_*`) | `0x820873d0` | 114 | [V] |
| actor methods (`ActorCmd_*`) | `0x82119c30` | 109 | [V] |
| client (CSC) functions `client_functions` | `0x82d69088` | 248 | [V] |
| client project functions `client_project_functions` | `0x82d6a870` | 90 | [V] |
| client methods (`CScr*`) | `0x8201f7d8`, `0x82024df0` | 166, 46 | [V] |

- [M] About 2,070 built-ins in all. Some names appear twice with different handlers (e.g. `setvehgoalpos` and
  `setneargoalnotifydist` exist for helicopters and for ground vehicles); the receiver's entity class picks one.
- [I] Addresses are for this Sep 2013 devkit build only. The PC `t6zm.exe` registers its table with a push/call
  sequence instead (see [t6_sound_playsound.md](../engine/sound_playsound.md)).

## Built-ins that matter for zombies visuals on the client

[V] From the client tables. A server-only VM never runs these, but the server clientfield and fx calls end up here:

- clientfields: `registerclientfield`, `codegetclientfield`, `codegetplayerstateclientfield`,
  `codegetworldclientfield`, `setupclientfieldcodecallbacks`, `setupclientfieldanimspeedcallbacks`,
  `processclientfieldsasifnew`
- fx: `playfx`, `playfxontag`, `playloopedfx`, `spawnfx`, `triggerfx`, `stopfx`, `deletefx`, `playviewmodelfx`,
  `playfxondynent`
- lights and exploders: `makelight`, the mixer-light family, `setlightcolor` / `intensity` / `radius`,
  `setmixerexploderid`
- vision and fog: `visionsetnaked`, `visionsetnakedlerp`, `setworldfogactivebank`, the volumetric fog switches
- footsteps, ambience, LUI (`luiload`, `luishow`, `luihide`, `luievent`), static model hide/unhide, `setdvar*`

## Not engine built-ins

[V] Names that a decompile pass of the zm scripts listed as built-in calls but that have no table entry, so they are
script functions or decompile artefacts: `entrance`, `player`, `get_closest_damage_refs`,
`check_point_in_active_zone`, `unmatched`, `value`, `buildable_think`, `index`, `module`.

## Credits

Ghidra (NSA) with zeroKilo's XEXLoaderWV; the symbol builds are the user's own.
