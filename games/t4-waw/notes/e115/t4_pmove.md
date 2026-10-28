# T4 player movement (pmove) from t4sp

This doc closes the [I] gaps in the engine's T4 movement profile: accelerate and friction, sprint, the stick scale, fall damage
and stance changes. It is a companion to `zombies_t4_nacht_ai.md` §5, which has the dvar table.

Tags:
- **[V]**: read in the disassembly, with a `t4sp.exe` virtual address.
- **[I]**: inferred. Treat as a guess until checked.

How it was read:
- Static reading of Plutonium's `t4sp.exe` only. Nothing was run, patched or copied out of its folder.
- Dvar pointers were matched to names by their registration calls: the store after each call `0x5eef10`/`0x5eeea0`/
  `0x5eee20` belongs to that call.
- Field names follow the Quake 3 / CoD4 pmove layout where the code matches it. Those names are [I] unless stated.

Struct offsets used below:

| field | offset | notes |
|---|---|---|
| `ps.pm_type` | `+0x04` | |
| `ps.pm_flags` | `+0x0c` | |
| `ps.pm_time` | `+0x18` | |
| `ps.velocity` | `+0x2c..0x34` | |
| `ps.gravity` | `+0x70` | |
| `ps.speed` | `+0x78` | `g_speed` |
| `ps.viewHeightTarget` | `+0x130` | |
| `ps.viewHeightCurrent` | `+0x134` | |
| `ps.waterlevel` | `+0x944` | see §0 |
| `pml.frametime` | `+0x24` | |
| `pml.walking` | `+0x2c` | |
| `pml.groundTrace.surfaceFlags` | `+0x4c` | |
| `pml.mins` / `pml.maxs` | `+0xfc` / `+0x108` | |

`cmd.buttons` is at `+8`, `forwardmove` at `+0x1a` (also seen as `+0x16` from a different base) and `rightmove` at
`+0x1b`/`+0x17`.

## 0. A correction to the AI doc

`ps+0x944` is **waterlevel** (0-3), not a "stacking slowdown" [V by pattern, I by name]:
- **Friction** adds waterlevel × speed × frametime, and skips ground friction above waterlevel 1. That is Quake's water
  friction (`0x413716-0x413731`).
- **Waterlevel 3** skips fall damage (`0x4152a3`), and **waterlevel 2** halves it (`0x4153a5-0x4153be`).
- **Sprint** needs waterlevel < 2 (`0x412fb8`, `0x413122`).

So the CmdScale factor × (1 − n/3 × 0.75) is a **water slowdown**: 0.75 / 0.5 / 0.25 at waterlevel 1 / 2 / 3. For dry
land it is 1.

Also, in CmdScale the ×1.5 sprint factor needs `viewHeightTarget == 60` (standing, `0x413df7`). The AI doc called this a
weapon state.

## 1. Accelerate and friction

### Dvars [V]

There is **no `accelerate` or `airaccelerate` dvar** in t4sp (string search). The accelerations are constants.

| name | default | dvar pointer |
|---|---|---|
| `friction` | 5.5 | `0x8f4394` |
| `stopspeed` | 100 | `0x8f0c30` |
| `inertiaMax` | 50 | `0x8f439c` |
| `inertiaAngle` | −1000 | `0x8f43d4` |
| `inertiaDebug` | false | `0x8f4374` |

### PM_Accelerate (`0x413970`) [V]

The normal path, when `pm_flags & 8` is clear (our pseudocode of the disassembly):

```
addspeed = wishspeed − dot(vel, wishdir);         if addspeed ≤ 0: return
control  = max(wishspeed, stopspeed)              // 0x4139c3-0x4139d2
accelspeed = min(frametime × control × accel, addspeed)
accelspeed = inertia_clamp(accelspeed)            // 0x4138f0, see below
vel += accelspeed × wishdir
```

**Unlike Quake, the acceleration uses `max(wishspeed, stopspeed)`, not `wishspeed`.** This is what makes slow stances
work.

With `pm_flags & 8` set (ladder [I]), the vector form runs instead (`0x413a45-0x413ae4`):
- diff = wishdir × wishspeed − vel
- accelspeed = min(frametime × wishspeed × accel, |diff|)
- vel += accelspeed × normalise(diff)

**Inertia** (`0x4138f0`, `0x4137a0`) [V]:
- It can clamp the result to `inertiaMax` (50) when the new direction turns more than the cosine `inertiaAngle` away from
  the current velocity.
- The test is dot(new, old) ≥ inertiaAngle × |new| |old|. With the default −1000 it can never fire, so **inertia is off
  by default.**

### Acceleration per move mode [V]

| function | mode [I] | accel | source |
|---|---|---|---|
| `0x4148d0` | WalkMove, standing | **9** | `0x414ac9` (`0x83fcd8`) |
| `0x4148d0` | WalkMove, crouched | **12** | `0x414abf` (`0x83fcd4`) |
| `0x4148d0` | WalkMove, prone | **19** | `0x414ab0` (`0x83fcd0`) |
| `0x4148d0` | on a slick surface (`surfaceFlags & 2`) or knockback (`pm_flags & 0x100`) | 1 | `0x414ad3` |
| `0x4148d0` | `pm_flags & 0x80` (hard landing [I]) | × 0.25 | `0x414adb-0x414aef` |
| `0x4143b0` | AirMove | 1 | `0x4144ab` |
| `0x4141b0` | FlyMove | 8 | `0x414344` |
| `0x4145b0` | ladder or swim [I] | 2, and 200 on one path | `0x4147f9`, `0x41485c` |
| `0x414c30`, `0x414ef0` | noclip / ufo [I] | 9, with their own friction × 1.5 | `0x414cc0`, `0x415152` |

**How the stance is picked** (`0x412e60`), from `viewHeightTarget`:
- 11 is prone (1)
- 40 is crouch (2)
- 22 (last stand, §5) is prone if waterlevel is 0, crouch if 1, stand if ≥ 2
- anything else is stand (0)

### PM_Friction (`0x413620`) [V] (our pseudocode of the disassembly)

```
speed = |vel|  (z ignored when walking);  if speed < 1: vel = 0; return
drop = 0
if waterlevel ≤ 1:
    if pm_flags & 0x20000:            drop = dvar@0x8f4408 × frametime      // [I] what this is
    elif walking && !(surfaceFlags & 2) && !(pm_flags & 0x100):
        control = max(speed, stopspeed)
        if pm_flags & 0x80:           control ×= 0.3                         // 0x4136e3, hard landing [I]
        elif pm_flags & 0x4000:       control ×= jumpLandScale()             // 0x40be20
        drop = friction × frametime × control
drop += waterlevel × frametime × speed                                       // water friction 1
if pm_type == 4:  drop += 5 × frametime × speed                              // spectator [I]
vel ×= max(speed − drop, 0) / speed
```

`jumpLandScale` (`0x40be20`) is **1 unless `jump_slowdownEnable` is on**, and that defaults to false. When it is on:
- the scale is 1 + pm_time × 0.000882, reaching 2.5 at pm_time ≥ 1700 ms
- after 1800 ms it clears flag `0x4000`

### Why prone works [V for the inputs, I for the arithmetic]

Prone wishspeed is about 28.5 (190 × 0.15). In steady movement at that speed:
- **Friction:** control = max(28.5, 100) = 100, so 5.5 × 100 = **550 u/s²** of drag.
- **Accel:** 19 × max(28.5, 100) = **1900 u/s²**, capped each frame at the gap to 28.5.

So prone reaches its 28.5 within a frame or two and holds it. The same rule gives:
- **Crouch** (≈124): 12 × 124 = 1488 u/s² against 682.
- **Stand** (190): 9 × 190 = 1710 u/s² against 1045.

**For the engine:** replace Quake's `accel × wishspeed` with `accel × max(wishspeed, stopspeed)`, and use accel 9 / 12 / 19 by
stance.

## 2. Sprint (`PM_UpdateSprint` `0x413460`) [V]

Dvars [V], with pointers:

| dvar | default | pointer |
|---|---|---|
| `player_sprintForwardMinimum` | 105 | `0x8f0c20` |
| `player_sprintSpeedScale` | 1.5 | `0x8f440c` |
| `player_sprintUnlimited` | false | `0x8f4410` |
| `player_sprintTime` | 4 | `0x8f4444` |
| `player_sprintMinTime` | 1 | `0x8f4358` |
| `player_sprintRechargePause` | 0 | `0x8f441c` |
| `player_sprintStrafeSpeedScale` | 0.667 | `0x8f443c` |

### Starting a sprint (`0x413591-0x41360c`)

All of these must hold:
- The sprint button is pressed: `cmd.buttons & 2`.
- The latch `ps+0x880` is 0. It is set to 1 when a sprint ends while the button is still held, and cleared only when the
  button is released (`0x41346b-0x41347a`, `0x412f80`). **So you must release and press again after a sprint ends.**
- `0x412fb0` passes:
  - not on a ladder (`pm_flags & 8`)
  - waterlevel < 2
  - **forwardmove > 105**, strictly; cmd forwardmove is −127..127 (`0x412fc6`)
  - none of the buttons in mask `0xc435` (fire, ADS and so on [I])
  - `ps+0x74` == 0
  - none of the flags in `0x1001c`
  - not in the jump state (`pm_flags & 0x4000` with pm_time 0)
  - not in weapon states 13-15 or 16-21
- `0x413190` and `0x413260` pass. [I] These are the room-to-stand checks: `0x413190` traces with a stand-height box.
- **The sprint meter > `player_sprintMinTime` × 1000 ms** (`0x4135dc-0x4135fb`). So yes: it needs more than 1 s of meter.
- After a stop, now − stop time ≥ `player_sprintRechargePause` × 1000 (0 by default; `0x413561-0x41358b`).

On start, the code sets `pm_flags |= 0x8000` and stores the start time and the meter (`0x4135fd-0x41360c`).

### While sprinting (`0x4134f1-0x413560`)

**The button doesn't need to be held.** Nothing reads it while sprinting, so a tap starts sprint and it continues until
a stop condition. Sprint stops when:
- **The meter runs out:** time since start ≥ the meter at start (skipped if unlimited).
- **`0x413120` is true:** waterlevel ≥ 2, flags `0x10018`, forwardmove ≤ 105, buttons `0xc735`, `ps+0x74` ≠ 0, or a
  blocked weapon state.

A stop runs `0x412f80`: it clears `0x8000`, stores the stop time, and sets the latch if the button is still held.
- [I] With button bit `0x400` held (a weapon or melee button?), it also adds 800 ms to the stop time (`0x413545-0x413552`).

### Other sprint rules

- **Sprint forces standing.** `PM_CheckDuck` clears prone and crouch when `0x8000` is set (`0x41653d-0x41655b`).
- **Strafe scale.** While sprinting, WalkMove scales `rightmove` by `player_sprintStrafeSpeedScale` (`0x4148f1-0x414911`).
- **The meter** is in the AI doc §5. It refills at 1 ms per ms.

## 3. Stick / command scale (`PM_CmdScale` `0x413cd0`) [V]

The input part (`0x413cfe-0x413dca`), as our pseudocode:

```
f = cmd.forwardmove, r = cmd.rightmove         (signed char)
total = sqrt(f² + r²)                          // raw values
fs = |f × (f < 0 ? player_backSpeedScale : 1)| // 0.7
rs = |r × player_strafeSpeedScale|             // 0.8
mx = max(fs, rs);  if mx == 0: return 0
scale = ps.speed × mx / (127 × total)
```

Notes:
- `max` uses the scaled values, but `total` uses the raw ones.
  - **Full diagonal** (127, 127): 190 × 127 / (127 × 179.6) ≈ 1.06 per unit. The wish vector is (127, 127) × that,
    giving ≈ 190 u/s.
  - **Pure backwards:** 190 × 0.7 = 133.
  - **Pure strafe:** 152.
- `backSpeedScale` is at `0x8f43b8` and `strafeSpeedScale` at `0x8f4458` [V].

The other factors are as in the AI doc, with the corrections from §0:
1. × 0.4 when walking (`pm_flags & 0x40`), when `ps+0x74` ≠ 0, or when prone with `ps+0x110` > 0 (`0x413ce3`).
2. × 1.5 when sprinting **and** `viewHeightTarget == 60`.
3. × 3 / × 6 for pm_type 2 / 3.
4. × the stance scale (`0x413030`): 1 / 0.65 / 0.15. It blends over the stance transition.
5. × the water factor.
6. × the weapon move scale (ADS or normal).
7. × the script speed scale `ps+0x8a4`.

## 4. Fall damage (`PM_CrashLand` `0x4152a0`) [V]

**The height used is the impact speed turned into a height, not the measured drop.**

1. Solve for the moment of impact, as in Quake (`0x4152b0-0x415336`):
   - a = −gravity / 2
   - b = the previous velocity z
   - c = the z change this frame
   - t = (−b − sqrt(b² − 4ac)) / 2a
2. The impact speed is v = b + t × (−gravity).
3. **Fall height h = v² / (2 × gravity)** (`0x415349-0x415382`). [I on the exact operand order; the shape is clear.]

Damage then follows:
- **None** if waterlevel is 3 (`0x4152a3`), if h ≤ `bg_fallDamageMinHeight` (200), if the surface has `surfaceFlags & 1`
  (no-damage [I]), or if pm_type ≥ 8 (dead).
- **h ≥ `bg_fallDamageMaxHeight` (350):** damage = 100 (`0x4153ec`).
- **Otherwise: linear.** damage = int((h − 200) / (350 − 200) × 100), clamped to 1..99 (`0x4153f3-0x41542b`).
- **Waterlevel 2:** damage × 0.5 (`0x4153a5-0x4153be`).
- If min ≥ max, the code prints a warning (`0x41538e`).
- The pointers are `0x8f4448` (min) and `0x8f4378` (max).

The damage is a percent of max health. [I] The game side applies it. SP max health is 100, so it is the same number.

**Landing view dip** (`0x415430-0x415458`): for h ≥ 12 it is min(24, int(((h − 12) / 26 + 1) × 4)), and 0 below 12.

## 5. Stances (`PM_CheckDuck` `0x416360`, view height blend `0x415f40`) [V]

### Capsule

The box is mins (−15, −15, 0) and maxs (15, 15, z). The z value switches **at once** with the stance, while the view
height blends.

| stance | maxs z | view height target | source |
|---|---|---|---|
| stand | 70 | 60 | `0x4163c5`, `0x416dd5` |
| crouch | 50 | 40 | `0x416da6` |
| prone | 30 | 11 | `0x416d71` |
| dead (pm_type 8) | | 8 | `0x4163d9-0x4163eb` |
| pm_type 6 / 7 | | **22** | `0x4169c0-0x4169cc` → `0x416d4e`. [I] Last stand; stance is chosen by waterlevel, as in §1 |

**Water forces stance** (`0x416401-0x416480`):
- waterlevel ≥ 1 with prone pressed gives crouch (40).
- waterlevel ≥ 3 gives stand.

**Going prone from standing** goes through crouch first. The target becomes 40, then 11 on a later frame
(`0x4169dd-0x4169ec`).

On entering prone, if pm_time is 0, the code sets `pm_flags |= 0x4000` and pm_time = **1800 ms** (`0x416cd9-0x416ce6`).
[I] This is the prone settle or dive lock, and it is the same flag the friction's landing scale reads.

### Transition timing (`0x415ffe-0x4160ca`)

progress = (now − start) × 100 / duration, clamped to 0..100. The view height comes from a keyframe curve.

| to | from | duration | view height curve (percent → height) | table |
|---|---|---|---|---|
| prone (11) | crouch | **400 ms** | 0 → 40, 11 → 38, 22 → 33, 34 → 25, 45 → 16, 50 → 15, 55 → 16, 70 → 18, 90 → 17, 100 → 11 | `0x8e0078` |
| crouch (40) | stand (`ps+0x140` set [I]) | **200 ms** | 0 → 60, 1 → 59.5, 4 → 58.5, 30 → 56, 80 → 44, 90 → 41.5, 95 → 40.5, 100 → 40 | `0x8dff90` |
| crouch (40) | prone | **400 ms** | 0 → 11, 5 → 10, 30 → 21, 50 → 25, 67 → 31, 83 → 34, 100 → 40 | `0x8e0128` |
| stand (60) | crouch | **200 ms** | 0 → 40, 5 → 40.5, 10 → 41.5, 20 → 44, 70 → 56, 96 → 58.5, 99 → 59.5, 100 → 60 | `0x8e0008` |

The prone curve has a **dip and bounce**: it reaches 15 at the halfway point, rises to 18, then settles at 11.

So stand → prone takes 200 + 400 = 600 ms. The table entries are 12 bytes `{int pct, float height, int}`. The third
field is 0 in all four tables. It is read into a second output that the blend function `0x415ea0` returns (an angle
[I]).

**Other heights** (8, 22) don't use a curve. They move linearly at **180 u/s** (`0x415f9a-0x415fcf`, constant
`0x8af4c0`).

**The speed scale** blends across the transition by the same time fraction (`0x413040-0x413112`):
- 1 ↔ 0.65 for crouch (constant `0x8af834`)
- 0.65 ↔ 0.15 for prone (constant `0x83c778`)

## Open items

- `pm_flags` bit names: `0x80`, `0x4000`, `0x20000` and the button masks `0xc435` / `0xc735` are [I]. They were
  matched by behaviour, not symbols.
- What `0x4145b0` is (accel 2 / 200), and which ladder or swim path uses the vector accel.
- What `ps+0x140` is: it picks the 200 ms or 400 ms crouch curve.
