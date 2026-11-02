# BO2 actor, entity and zombie built-ins: what the handlers do

Behaviour notes for the actor (`ActorCmd_*`) and related built-ins that a zombies script VM needs, read in the BO2 360
`CoDMP` handlers and spot-checked in the PC dedicated server. Our own paraphrase; arguments are given in script order.
Marks are explained in the [notes index](../../../../NOTES.md).

## Anim state

- [V] `setanimstate(state, [substate])` does nothing in a zombies session. It first asks whether the anim-state-def
  (ASD) system is in use, and that check is just the session-mode zombies flag; in zombies the ASD calls
  (`setanimstatefromasd`) own actor anims. Elsewhere it maps the name to one of 47 fixed actor anim slots and stores
  slot and substate on the entity state.
- [V] `setaimanimweights(a, b)`: two floats stored on the actor's entity state (+0x98, +0x9c). No notify, no return.
- [V] `getanimstatefromasd()`: the current ASD state name, as a const string.
- [V] `hasanimstatefromasd(name)`: true when the actor's ASD has a state of that name (the index lookup's "not found"
  value is -2).
- [V] `animcustom(func, [endfunc])`: only acts if pushing actor AI state 10 succeeds. Then it kills the running
  animscript, stores `func` and the optional second function on the actor, and sets the animscript name. [I] The
  second function runs when the custom anim ends.

## Movement and goals

- [V] `allowedstances(name, ...)`: variadic. Each name sets a bit in a stance mask on the actor; there are three
  accepted names, [I] stand 1, crouch 2, prone 4 by the order of the checks. An unknown name is a script error. If the
  mask ends up empty it is a script error ("no allowed stances given") and the mask resets to all three.
- [V] `isingoal(point)`: bool, the point is inside the actor's goal.
- [V] `nearnode(node)`: bool, the actor's origin is near that pathnode.
- [V] `setpitchorient()`: sets two actor flag bytes (+0x229, +0x22a). [I] Pitch follows the ground.
- [V] `getdeltaturnyaw()`: dog actors only (asserts the species); returns a float.
- [V] `melee([point])`: runs the actor melee, toward the point when given; returns the entity hit, else nothing.
- [V] `settalktospecies(name, ...)`: variadic. Each species name sets a bit in a 5-bit mask (actor flags bits 21-25);
  one special name, [I] "all", sets all five; no arguments clears the mask. [I] The 360 decompile reads argument 0 on
  every pass of the loop, so only the first name may count.

## Path nodes

- [V] `spawnpathnode(classname, origin, angles, [key, value]...)`: builds a spawn-var block from the classname, origin,
  angles and any extra key/value pairs, parses it, spawns a runtime pathnode (static part, then dynamic part), drops it
  to the floor and connects paths for that one node. Returns the node as an entity of class 2 (pathnode), or nothing
  when the spawn fails.

## Teams and misc

- [V] `setteam(team)`: script error "SetTeam can not be used for players or actors" on those entity types (1 and 16).
  Otherwise it sets the low four team bits of the entity. Same on 360 and PC.
- [V] `setteamhasmeat(team, n)`: stores `n` in a per-team int array in the level locals. No script getter reads it.
- [V] `sendfaceevent(name)`: matches the name against a fixed list of face events and adds an entity event (a facial
  anim cue for the client). Nothing else on the server.
- [V] `itemweaponsetammo(clip, stock, [hand 0-1])`: script error unless the entity is an item (type 3). Negative counts
  are parameter errors. Reads the weapon's clip size ([I] to clamp the clip), then writes clip and stock to the item's
  weapon slot for that hand.
- [V] `dropitem(weapon, [tag])` (player): drops a held weapon as a pickup and returns it; script error if it isn't held.
  `dropscavengeritem(name)` drops a scavenger pickup and returns it.
- [V] `getcorpseanim()`: player corpses only, else a script error; returns the corpse's anim.
- [V] `turnedhuman()` (player): writes the client's "turned" state back to human.

## Zbarrier pieces

- [V] `setzbarrierpiecestate(piece, state, [rate])`: script error unless the entity type is 20 (zbarrier). The
  lowercased state name maps to an enum value 0-4; an unknown name is a parameter error. The optional third argument
  is an anim rate, default 1.0. [I] The five names are the ones zm scripts use (closed, opening, closing, open,
  targetted_by_zombie); [U] which value each one gets.

## Entity type enum

[V] The order of the `CoD.EntityType` names in the base LUI script lists the T6 entity types. [I] Numbered by that
order, matching three values read in handlers (player 1, item 3, actor 16) and the zbarrier check (20):

| Value | Type | Value | Type |
| --- | --- | --- | --- |
| 0 | general | 11 | turret |
| 1 | player | 12 | helicopter |
| 2 | player corpse | 13 | plane |
| 3 | item | 14 | vehicle |
| 4 | missile | 15 | vehicle corpse |
| 5 | invisible | 16 | actor |
| 6 | script mover | 17 | actor spawner |
| 7 | sound blend | 18 | actor corpse |
| 8 | fx | 19 | streamer hint |
| 9 | loop fx | 20 | zbarrier |
| 10 | primary light | | |

[V] `getentitytype()` returns this value as an int.

## Direct notifies

[V] Of the built-in handlers, only `ActorCmd_SetOverrideRunToPos`, `ActorCmd_finishActorDamage`, `ScrCmd_Delete` and
`ScrCmd_UseBy` call the script notify functions in their own bodies. [I] Other built-in notifies come from deeper
engine code.

## Credits

Ghidra (NSA), zeroKilo's XEXLoaderWV, capstone; the BO2 symbol builds and PC server pdb are our own.
