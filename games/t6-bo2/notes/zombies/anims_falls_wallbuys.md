# T6 zombies: zombie anim clips, fall damage, wall-buy models

Three small findings from 2026-11-01. Tags: **[V]** read in the exe, scripts or data, **[I]** inferred.

## Zombie anim clips [V]

- The T6 zombie scripts use about 490 distinct `ai_zombie_*` anim clips (walk, run, sprint variants, attacks, traversals,
  taunts, deaths, spawn-in clips and so on). Exporting only a short fixed list leaves zombies without a pose or
  stuck on one pose whenever a script asks for a clip you left out **[I]**.
- The export takes a name prefix (`ai_zombie_` plus a wildcard) and matches every `xanim` asset that starts with it, in
  every loaded zone. The same prefix idea works for other families.

## Fall damage [V]

- Zombies (zm): fall damage starts at a drop of 128 units and reaches the maximum at 300 units, and a full fall deals
  1.1 times the player's max health. Multiplayer uses 128 and 300 as well.
- BO1 zm is different: min 128, max 350 (read from the BO1 exe's `bg` dvar registration).
- `pm_crashland` turns the drop into a percentage, linear between min and max. The client event then scales that by
  the max health. In zm the scripts handle the hit as a falling-type damage from the world.
- Some ground surfaces take no fall damage: a ground-trace flag of 0x1 in every mode, 0x2 in zombies only **[V]** for
  T6; T4 and T5 are **[U]**.
- The T6 globallogic MP script also has an "oldschool" override of the fall rules. It applies to that mode only, not to
  zombies.

## Wall-buy models [V]

- A wall-buy shows the weapon's world model on the wall. The weapon definition has a list of `hideTags` (bones the
  model hides, for example a scope or magazine that would stick out). T5 and T6 wall-buy models must hide those bones
  the same way the viewmodel does, or attachments appear that the game hides (seen on Kino).
- T4 keeps the list in the weapon def with a fixed count of 8; T5 and T6 use their variant def's `hideTags`.
