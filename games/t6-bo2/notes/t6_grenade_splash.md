# BO2 grenade splash, explosion and bounce; actor repath rules

Server-side missile and splash behaviour and the actor pathing rules, read in the PC dedicated server
(`CoDMPServer_PC.exe`, x86) and the 360 `CoDMP` build. Marks are explained in the
[E115 notes index](../../../shared/notes/e115/README.md).

## Splash damage (`G_RadiusDamage`)

- [V] Arguments, in order: origin, inflictor, attacker, maximum damage, minimum damage, radius, then cone and
  ignore options, means of death and weapon.
- [V] Collects entities in the radius box. For each one it takes the squared distance from the blast to the entity
  (a helper, [I] nearest point of its bounds rather than its origin) and skips it when that is at least radius².
- [V] Damage = min + (max − min) × (1 − distance ÷ radius), truncated to int: a straight-line falloff from max at the
  centre to min at the edge.
- [V] Vehicles go through their own radius-damage hook. Everything else needs a clear damage trace from the blast.
  Riot-shield protection then scales the damage; a blocked hit adds a shield splash event, otherwise the entity is
  damaged normally.
- [V] After the entity loop, destructibles, dynamic entities and glass in the radius are damaged too.
- [U] A sqrt(2) constant and a shrapnel cylinder-height dvar appear in the setup (a cylinder-span option); not read.

## Explosion (`G_ExplodeMissile`)

- [V] Evaluates the missile's final position and checks water depth (the `missileWaterMaxDepth` dvar).
- [V] Traces to find the surface hit and sends a script notify with the surface type's name and the position.
- [V] Spawns a temporary entity for the explosion event with the hit direction, and frees the missile after the event.

## Bounce (`BounceMissile`)

- [V] Reflects the velocity with a per-surface restitution, adds random bump and wobble from the `grenadeBump*` and
  `grenadeWobble*` dvars scaled by gravity, and uses grenade rolling when `grenadeRollingEnabled` is on.
- [U] No bounce sound is sent in the server code read (`BounceMissile`, `G_RunMissileInternal`).
- [I] WeaponDef's `bounceSound` field is a per-surface alias list (OAT shows it surface-indexed), so the client most
  likely plays the entry for the bounce surface.

## Actor repath rules

- [V] Goal update (`Actor_UpdateGoalPos`): the goal point is either the enemy's last known position (in "use enemy
  goal" mode), the live origin of a goal entity, or the script goal position or node (a node's live origin when the
  `enable_moving_paths` dvar is 1). Goal radius and height are applied after.
- [V] If the goal position changed at all (exact float compare), the actor's path-valid flag is cleared, which forces
  a new path on the next think. [I] There is no distance threshold here.
- [V] Repath (`Actor_RecalcPath`): keeps the current path's destination, clears the path, refreshes the actor's
  nearest node and finds a new path from where it stands to the same destination.
- [V] Failed path (`Actor_HandleInvalidPath`): no new attempt before level time + 500 ms. Unless a flag on the actor
  is set, it calls the team-move-blocked handler, prints that the AI couldn't find a path to its goal, and sends the
  actor a notify with the goal position. [I] That notify is `bad_path`, which stock zm scripts listen for.

## Credits

Ghidra (NSA) with zeroKilo's XEXLoaderWV, capstone for the x86 reads; the symbol builds and server pdb are the user's
own.
