# BO2 player movement: fall damage, slick-surface sliding, melee and lunge

Read in the BO2 360 `CoDMP` player-move code (`PM_*`) and cross-checked against the PC dedicated server. WeaponDef
field names come from matching offsets to OpenAssetTools' T6 header. Marks are explained in the
[notes index](../../../../NOTES.md).

## Fall damage (`PM_CrashLand`)

- [V] One movement mode returns early (playerstate +0x5b8 == 4).
- [V] Fall height comes from the impact: the downward speed at landing and the drop since the fall began, solved for
  the height using the playerstate gravity (v² / 2g).
- [V] Damage percent = (height − min) / (max − min) × 100, clamped to 0..100. Min and max are the
  `bg_fallDamageMinHeight` and `bg_fallDamageMaxHeight` dvars; both are asserted positive with max above min.
- [V] Zombies only: if the playerstate gravity is below `(int)bg_gravity`, damage is 0. At normal gravity it is kept.
- [V] Perk index 14 cancels the damage. [I] In session mode 4, perk index 25 cuts any damage to 1.
- [V] Damage is 0 when the ground trace's surface flags have bit 1 set ([I] a no-damage surface) or `pm_type` is above
  9. A stance-like field above 1 halves it.
- [V] Landing with damage between 1 and 99: if a player flag (0x40000000) and surface flag bit 2 are both clear, it
  sets the move timer to 500 + 35 × damage ms (at most 2000), sets a move flag (0x80), and scales horizontal velocity
  down to about 15–30%. Otherwise velocity is scaled by about 0.67. Then it sends a fall-damage event with the ground
  surface type and the damage value.
- [V] Landing with no damage: below 4 units nothing happens; below 8 a light land event; below 12 a medium one; above
  that the velocity is scaled by about 0.67 and the land event carries the ground surface type. Above 12 units it also
  fires a landing anim event.

## Sliding on slick ground (`PM_DoSlideAdjustments`)

- [V] When the ground trace's surface flags have bit 2 set ([I] slick), the player is accelerated downhill along the
  horizontal part of the ground normal. Wish speed is the `player_sliding_wishspeed` dvar, the acceleration a fixed
  constant, and speed is capped by `player_sliding_velocity_cap`.
- [V] The cap test compares the cap squared against the unsquared speed, so it only trims at very high speeds. A
  faithful reimplementation should keep that.
- [V] Separately, while a player flag (0x40000000) is set and the player is walking, it accelerates with the
  `player_slick_invspeed`, `player_slick_accel` and `player_slick_wishspeed` dvars.
- [I] So a slope whose material carries the slick surface flag pushes the player down with no input.

## Melee and lunge

- [V] The melee weapon is the held weapon when it counts as a melee weapon, else the player's melee slot weapon.
- [V] A melee is a lunge when the charge flag is set (playerstate flag 0x20000) and the charge distance is beyond
  `player_meleeRange` (`player_bayonetRange` for bayonets).
- [V] Lunge timing (`PM_Weapon_MeleeInit`): weapon time = `meleeChargeTime`, weapon delay = `meleeChargeDelay`,
  written to the right or left hand slot. [I] A plain melee uses `iMeleeTime` / `iMeleeDelay` (that branch wasn't
  read).
- [I] The hit lands after the delay, and nothing else can start until the weapon time runs out. That is the whole
  repeat cooldown; there is no separate timer.
- [V] `PM_Weapon_MeleeFire` sets weapon state 0x14 and adds the melee swing event (0x28). `PM_Weapon_MeleeEnd`
  returns to idle, or when the weapon changed meanwhile, sets state 0x15 with weapon time from a later WeaponDef
  field (+0x4c8, [U] probably a raise time).
- [V] Lunge start (`PM_MeleeChargeIsValid`) needs: no charge already active, standing on something, `pm_type` 0, two
  weapon-state flag bits clear, no ladder or mantle flags, and not in the air.
- [V] Lunge move (`PM_MeleeChargeCheck`), skipped when the `player_meleeCOD4ChargeMovement` dvar is set: on the first
  frame, delay = `iMeleeDelay`, or `meleeChargeDelay` when the target is beyond melee range; horizontal velocity =
  the charge yaw direction × (2 × distance ÷ delay in seconds); the charge timer is set to the delay in ms.
  [I] The 2 × distance ÷ time means the lunge starts at twice its average speed and slows down.

## WeaponDef offsets used (360 build)

[I] From OAT's T6 `WeaponDef` field order with 4-byte pointers: `iMeleeDelay` +0x434, `meleeChargeDelay` +0x438,
`iMeleeTime` +0x480, `meleeChargeTime` +0x488. These match how the handlers use them.

## Credits

Ghidra (NSA) with zeroKilo's XEXLoaderWV; OpenAssetTools' T6 asset header for field names; the symbol builds are
the user's own.
