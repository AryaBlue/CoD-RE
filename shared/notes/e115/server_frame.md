# Server frame: T5 / T6

Base for the E2 world layer (entities, traces, triggers, movers) and the E3 script service. Covers how the Treyarch
server runs a frame, what a trace takes and returns, how triggers fire, how script movers move and how the client
smooths entities between snapshots.

Tags:
- **[V]**: read in the exe, with the address. T6 is Plutonium `t6mp.exe` (sha256 `770318…6adf`). T5 is `BlackOps.exe`
  (the Steam exe). Static reads only: nothing was run or patched.
- **[I]**: inferred, usually from the Quake 3 / CoD4 lineage the code clearly follows. Treat as a guess until checked.

Function names are ours, from what the code does. The exes have no symbols. T6 is the main source. T5 was only
spot-checked (see "T5" at the end).

## T6 layouts used below [V]

`gentity_t` is 0x31C bytes and `g_entities` is at `0x21ef7c0`.

| offset | field |
|---|---|
| `+0x00` | entity number |
| `+0x0C` | `s.lerp.pos` trajectory (layout below) |
| `+0x30` | `s.lerp.apos` trajectory |
| `+0xD8` | `s.eType` (u16) |
| `+0xFB` | in use (u8) |
| `+0x100` / `+0x10C` | `r.mins` / `r.maxs` |
| `+0x118` | `r.contents` |
| `+0x134` / `+0x140` | `r.currentOrigin` / `r.currentAngles` |
| `+0x14C` | `r.ownerNum + 1` (0 = none) |
| `+0x154` | `gclient_t*` |
| `+0x172` | handler index (u8, into the handler table) |
| `+0x184` | spawnflags |
| `+0x188` | flags |
| `+0x18C` | event time |
| `+0x19C` | last frame this entity ran (de-dup) |
| `+0x1A4` | `nextthink` (ms, 0 = none) |
| `+0x22C` / `+0x25C` | mover state for position / angles |
| `+0x2A4` | link-to (tag) info |
| `+0x304` | use count (a respawn stamp used to validate stale refs) |

Trajectory (`+0x0C` / `+0x30`), 0x24 bytes:
- `u8 trType`
- `int trTime` (ms)
- `int trDuration` (ms)
- `vec3 trBase`
- `vec3 trDelta`

`trType` values seen:

| value | meaning |
|---|---|
| 0 | stationary |
| 1 | interpolate |
| 4 | linear stop |
| 8 | accelerate |
| 9 | decelerate |
| 0xA, 0xE | treated like stationary by the evaluator |

The evaluator is `0x44ce20(tr, time, out)`, with a jump table at `0x44d208` indexed by `trType − 3`.

Level globals:
- `level.framenum` `0x2367314`
- `level.time` `0x2367318` (ms)
- `level.previousTime` `0x236731c`
- `level.frameTime` `0x2367320` (ms)

The entity handler table is at `0xd4d330`. Each entry is 0x30 bytes, indexed by `+0x172`. The fields used here:
- `+0x00` think
- `+0x04` reached (mover finished a phase)
- `+0x0C` touch
- `+0x10` use

## 1. The frame

### Tick [V]

The server ticks at a fixed **50 ms**:
- `0x674014` and `0x893d58` do `svs.time (0x291c0b0) += 0x32`, then call `G_RunFrame(svs.time)` (`0x4a5520`).
- The time step is constant. The residual/accumulator loop around it isn't traced [I].

### `G_RunFrame` `0x4a5520`, in order

1. **Times** [V]
   - `framenum++`, `previousTime = time`, `time = levelTime`, `frameTime = levelTime − old time`.
2. **Per client in use** (loop to `maxclients`) [V]
   - `G_TouchTriggers` (`0x62f170`, section 3).
   - Then `0x831ba0`, `0x42c8c0`, a flag `0x10000` that clears 1000 ms after a stamp, `0x5f1540` and `0x8318c0`. These
     are client upkeep [I].
3. **Global calls** [V]
   - `0x49a690` (gated by a dvar) and `0x5f4a50(time, −1, 0)`. Their purpose wasn't identified [I].
4. **Per entity in use** [V]
   - `0x6eadc0(ent, frameTime × 0.001)`, a per-entity step in seconds. Likely physics or animation [I].
5. **Pending triggers, then scripts** (`0x4a56da`-`0x4a57f8`, details in section 3) [V]
   - Notify every queued `"trigger"`.
   - Run script threads: `0x566b70(0)` calls the VM runner `0x8f9780` and times it with `Sys_Milliseconds`.
   - Repeat until no trigger is left deferred.
6. **More per-entity passes** [V]
   - Per client: `0x831650`.
   - Per entity without flag `0x2000` (`+0x188`): `0x60f650(ent, 1, 0x831640)`.
   - Then `0x5d3f30(0)` and `0x573260`.
7. **Entity think pass** [V]
   - For each entity in use, set `level.currentEntityNum` (`0x2367dc8`) = i, call `G_RunFrameForEntity` (`0x831940`)
     and then `0x55c0a0`, the link-to/tag upkeep.
   - Afterwards `currentEntityNum = −1`.
8. **End of frame** [V]
   - `0x59cb20`, `0x6ed960`.
   - `ClientEndFrame` (`0x542320`) runs for clients whose session state (`client+0x5410`) isn't 2, then for the ones
     where it is 2 (spectators last).
   - Then misc tail calls and `0x909da0(time)`.

So in T6, **scripts run before entity think in a frame**, and trigger notifies are delivered just before script
threads run. Movers and think happen after scripts. So a `moveto` issued this frame starts evaluating in the same
frame's think pass.

### `G_RunFrameForEntity` `0x831940` [V]

1. It runs once per entity per frame, guarded by `+0x19C == framenum`. If the entity is linked to a parent, the parent
   runs first.
2. Event entities are freed or unlinked 300 ms (`0x12c`) after their event time (`+0x18C`, flags `+0x190`/`+0x194`).
3. A timed entity flag (`+0x04 & 0x4000`, with an expiry in `+0x80`) notifies `"death"` (`0x24e55cc`) and frees the
   entity. Used by e.g. grenades/temporary ents [I].
4. Then it dispatches on `eType`:

| eType | calls |
|---|---|
| 4 | `0x58df40` (missile [I]), then the link-to update |
| 0x14 | `0x5828f0` |
| 3 | link-to `0x603c00`, then `G_RunThink` |
| 2 | `0x4b58b0` |
| 0x12 | `G_RunThink` only |
| has a physics object (`+0x16E`) | `0x4a2b80` |
| 6, 0xD, 0xA (6 = script mover, see section 4) | `0x62d780` (damage over time, 4 slots) + `G_RunMover` `0x67d200` |
| client entities | `0x54f320` |
| otherwise (incl. 0 and 0x13) | link-to, `0x62d780`, then `G_RunThink` |

### `G_RunThink` `0x61ad00` [V]

- If `0 < nextthink <= level.time`: set `nextthink = 0`, then call `handlers[+0x172].think(ent)`.
- A null think is an error: `"NULL ent->think"`, `0xc3aa60`.
- Think is one-shot and in milliseconds. The entity re-arms it by setting `nextthink` again.

## 2. Traces

### Script-side calls [V]

| builtin | T6 function | args | mask |
|---|---|---|---|
| `bullettrace` | `0x85b9c0` | start, end, hitCharacters, ignoreEnt, [5], [6] | `0x280e033` with characters, else `0x806033`. Arg 5 clears `0x20` and arg 6 clears `0x10` |
| `physicstrace` | `0x84f480` | start, end, [mins, maxs], [ignoreEnt], [flags] | built from flags (below) |
| `playerphysicstrace` | `0x84f820` | | |

`physicstrace` mask from its flags (default 1):

| flag | mask |
|---|---|
| bit 1 | `0x280ec93` |
| bit 2 | `\| 0x211` |
| bit 4 | `\| 0x20` |
| bit 8 | `\| 0x376c0` |
| exactly `0x10` | `0x200` alone |

All of them return the same array fields: `fraction`, `position = start + (end − start) × fraction`, `entity`,
`normal` and `surfacetype`. The last two are only set when `fraction < 1`. These are scr_const slots `0x24e55f2`,
`0x24e5642`, `0x24e55e2`, `0x24e5638` and `0x24e566e`.

### Engine-side call [V]

```
G_TraceCapsule(trace_t *out, start, mins, maxs, end, int passEntityNum, int contentmask)   // 0x5809a0
G_LocationalTrace(trace_t *out, start, end, int passEntityNum, int contentmask, ...)       // 0x51bf10, ray, hit locations
```

- **Pass filter.** Both functions build a filter that skips `passEntityNum` and that entity's owner (`r.ownerNum`) with
  flags `0x1010001`. Then they call the server trace (`0x6ad9c0`).
- **World first.** The server trace calls `0x519460`, which clears `trace_t`, sets `fraction = 1` and `+0x26 = 0xFE`,
  then calls `CM_BoxTrace(out, start, end, mins, maxs, 0, mask)` (`0x66eee0`). Entities are traced afterwards (several
  callees after `0x6adb8f`) [I: per entity class].

`trace_t` is 0x40 bytes:

| offset | field |
|---|---|
| `+0x00` | `normal` (vec3) |
| `+0x10` | `fraction` |
| `+0x14` | `surfaceFlags`. The surface type is bits 20-25 (`>> 20 & 0x3F`, `0x84f71c`) |
| `+0x18` | probably `contents` [I] |
| `+0x1C` | hit type: 1 = entity, 2/3/4 = world-like (reported as `ENTITYNUM_WORLD` 0x3FE), anything else = none (0x3FF). See `Trace_GetEntityHitId`, `0x6a32f0` |
| `+0x20` | hit entity id (u16) |

### Boxes are swept as capsules [V]

`CM_BoxTrace` (`0x66ef7b`-`0x66f196`) works like this:
- Half-extents = (maxs − mins) / 2, and the box centre is added to start and end.
- `radius = min(halfX, halfZ)` and `offsetZ = halfZ − radius`. The comparison is at `0x66f116`.

So every box trace is a vertical capsule of that radius, with sphere centres at ±offsetZ. Any player or entity box
sweep therefore behaves as a capsule. Player movement uses the same CM trace [I: pmove not traced]. Players' collision
in T6 is a capsule of radius = half the box width.

## 3. Triggers

### Per-frame touch test: `G_TouchTriggers` `0x62f170` [V]

It runs for every client at the start of `G_RunFrame`. It is also called from `0x5604f8`, `0x691d7b`, `0x69211f` and
`0x6fb097` (actors, vehicles, etc. [I]).

1. **Area query.** The candidate box is the entity's absolute box ± **20** units (`0xc717b0`), passed to
   `CM_AreaEntities` (`0x6ef9a0`, max 1024).
   - The content mask depends on the toucher: 8, `0x400000`, `0x1c0000` or `0x40000000`, chosen by actor/client
     fields [I].
2. **Exact box.** Each hit is tested with the unexpanded box:
   - for clients, `r.mins/maxs + ps.origin`
   - for others, `currentOrigin + mins/maxs`
3. **Skips.**
   - Skip if neither side has a touch handler.
   - Skip if the toucher's client index bit is set in the trigger's per-client mask (`+0xBC`, a "hide/ignore for this
     player" bitset [I]).
   - For `trigger_use`, `trigger_use_touch`, `trigger_radius`, `trigger_box` and `trigger_radius_use`, apply the team
     checks (`+0x23F`, `+0x173`).
4. **Contact test.**
   - Items (eType 3) use `0x534d30`.
   - Everything else uses `0x4d69e0`:
     - **Radius triggers** (`+0xFA & 0x20`) are a vertical cylinder, with origin.z ≤ z < origin.z + height
       (`maxs.z`). They hit when the 2D distance from the trigger origin to the box centre is less than radius +
       the box's half width.
     - Bit `0x40` is another shape [I: disc].
     - **Brush triggers** test against the brush model.
5. **On contact.**
   - Notify `"touch"` on both entities, each with the other as the argument (`0x24e56be`).
   - Call `trigger.touch(trigger, toucher, 1)` and, if the toucher has one, `toucher.touch(toucher, trigger, 1)`.

### `trigger_multiple` / `trigger_radius` [V]

**Setup.**
- Both use handler 4. Its touch is `0x605340`.
- `trigger_multiple` (`0x4bb8e0`) reads `wait`. If wait ≤ 0 it sets spawnflag-word bit `0x40`.
- `trigger_radius` (`0x5aef10`) reads `radius` and `height`, or takes them from `spawn("trigger_radius", origin,
  spawnflags, radius, height)`.
  - It sets mins = (−r, −r, 0), maxs = (r, r, h) and the shape bit `0x20` (`0x85e420`), then links the entity.

**Touch.**
1. The touch handler calls `G_Trigger(self, activator)` (`0x4d5360`).
2. If bit `0x40` is set, it then calls `0x4277f0` [I: deletes the trigger, i.e. fire once].

**Queueing (`G_Trigger`).**
- It doesn't notify straight away. It queues `{self, activator, both use counts}` in a 256-entry list (`0x2367e50`,
  count `0x2369650`).
- Only when the list is full does it notify immediately.

**Delivery (in `G_RunFrame`).**
1. The list is copied, then each entry is checked: both use counts must still match, so freed or reused entities are
   dropped.
2. A valid entry sends `self notify("trigger", activator)` (`0x24e56c0`).
3. **An entity is notified at most once per pass.** A second entry for the same trigger waits for the next pass.
4. Script threads run between passes.

So a trigger touched by two players in one frame delivers `"trigger"` twice, with the scripts running in between.

### `trigger_use` and the use key [V]

- `trigger_use` (`0x838a60`) sets contents `0x200000` and reads `cursorhint` and the hint keys.
- When a player uses an entity (`0x86d410`, from `0x86d8fa`):
  - **Items:** `notify("touch", player)`, then the touch handler (pickup).
  - **Everything else:** `notify("trigger", player)` **immediately** (not queued), then `handler.use(ent, player,
    player)`.
- Script `ent useby(player)` (`0x84a410`) does the same thing: notify `"trigger"`, then `use`.
- How the use target is picked isn't traced (cursor hint / look-at) [I].

`trigger_hurt`'s use handler (`0x69dc50`) toggles the handler between 5 and 6, i.e. on and off. Its touch (`0x461150`)
deals damage with a rate limit: the next hurt is +1000 ms with spawnflag `0x10`, otherwise +50 ms. Its means of death
is `0xE`.

## 4. Script movers

### Which entities can move [V]

`moveto`/`movex`/`movey`/`movez`/`rotateto`/… are entity methods (method table `0xc76f18`). They accept only
`script_brushmodel`, `script_model`, `script_origin` or `light` (`0x5a6940`, error `0xc33208`).

`script_brushmodel` (`0x5fa7b0`) and the other mover inits (`0x5071c0`) set:
- eType 6
- handler 8, whose `reached` is `0x66bf90`
- `trBase` = current origin / angles
- flag `0x1000`

### Arguments: `moveto(point, time, [accel], [decel])` [V, `0x502d30`]

The values are in seconds:
- `time` must be > 0. It is clamped to at least 0.001.
- `accel` and `decel` must be ≥ 0. They default to 0.
- If `accel + decel > time × 1.0000005`, that's an error ("accel time plus decel time is greater than total time").
  If they are just over `time`, `time` is raised to match.

### Move setup: `0x85c320` [V]

Inputs: `d = |end − start|`, `T` = time, `a` = accel, `e` = decel. Durations are stored as `int(seconds × 1000)` ms.

**No ramp.** If both `a` and `e` are < 0.002 (`0xc547e8`):
- A single **linear stop** move (`trType 4`), with `trDuration = T × 1000` and `trDelta = (end − start) / (dur / 1000)`.

**With ramps.**
- Peak speed `v = 2d / (2T − a − e)`, the cruise time is `T − a − e`, and the direction is normalised.
- The phases run in order:
  1. **accelerate** (`trType 8`) for `a`, with `trDelta = dir × v`
  2. **linear stop** (`trType 4`) for the cruise time, at speed `v`
  3. **decelerate** (`trType 9`) for `e`
- A phase with zero length is skipped.
- The mover state (`+0x22C`) keeps the decel time, the speed, the cruise time, the phase start points and the final
  point.

**Time-0 quirk.** If `trTime` would be 0, it's set to 1 and `trDuration` is reduced by 1 ms, because 0 means "not
moving".

`rotateto` uses the same code for angles: the `apos` trajectory and the state at `+0x25C`.

### Evaluation: `0x44ce20` [V]

`t = clamp(time − trTime, 0, trDuration) / 1000` (seconds):
- **linear stop:** `base + delta × t`
- **accelerate:** with `accel = |delta| / dur`, `base + dir × ½ × accel × t²`
- **decelerate:** `base + delta × t − dir × ½ × accel × t²` [V shape; the sign constant at `0xbf8810` is presumed −0.5]

### Per frame [V]

1. **Evaluate.** `G_RunMover` (`0x46b6e0`, called from `0x67d200`) evaluates both trajectories at `level.time`.
2. **Push.** The new position and angles go to the push routine (`0x608270`). On a block, the blocked path (`0x838c60`)
   runs [I: crush/stop rules not traced].
3. **Reached.** `0x422c30` then calls `handlers[+0x172].reached` once `trTime + trDuration <= level.time`.
4. **`reached`** (`0x66bf90`):
   - It advances to the next phase (`0x85c140`), re-evaluates and calls `SV_LinkEntity` (`0x595ee0`).
   - When the last phase ends it notifies **`"movedone"`** (`0x24e5626`).
   - For angles, when the last phase ends it wraps pitch/yaw/roll to [0, 360) and notifies **`"rotatedone"`**
     (`0x24e5656`).

**Collision follows the brush model.** The entity is relinked with its new origin and angles every time the mover
updates. A `script_brushmodel`'s collision is its brush model placed at `currentOrigin`/`currentAngles` [I: the link
inside the push path wasn't read line by line].

There's also a special path for movers with both trajectories set to type 1 that are linked to something with a
32-slot history (`+0x380`): it moves them by the parent's frame delta (`0x46b744`-`0x46b989`), e.g. riders on
vehicles [I].

## 5. Client: snapshots and interpolation

### `CG_ProcessSnapshots` `0x47e390` [V]

The cgame globals pointer is `0x113f18c`. The fields used:
- `+0x24` = `snap`
- `+0x28` = `nextSnap`
- `+0x4808C` = `cg.time`
- `+0x48084` = `frameInterpolation`

The steps:
1. It reads snapshots until `snap` and `nextSnap` are set. Each read goes through `CG_TransitionSnapshot`
   (`0x5f0790`) and the entity state copies `0x57bed0`/`0x706500`.
2. It sets the frame interpolation (`0x4577b0`).
3. While `cg.time >= nextSnap.serverTime` (with a −1000 ms resync guard at `0x47e4ff`), it transitions to the next
   snapshot.
4. "Server time went backwards" is an error (`0x47e4ac`).
5. If `cg.time < snap.serverTime`, it clamps `cg.time` to `snap.serverTime` (`0x47e55e`).

### `frameInterpolation` `0x4577b0` [V]

```
f = (cg.time − snap.serverTime) / (nextSnap.serverTime − snap.serverTime)
```

`f` is 0 if the two times are equal. Negative values are clamped to 0, and there's no clamp at 1.

### Entity positions [V, `0x5d5670`]

For an interpolated entity, the client evaluates `currentState.pos` at `snap.serverTime` and `nextState.pos` at
`nextSnap.serverTime`, then lerps the two by `f`. Angles get the same treatment. A trajectory type in {0, 1, 0xA, 0xE}
uses `trBase` as is.

So movers glide on the client from their trajectories rather than from per-snapshot positions. The player state
(view angles etc.) is also lerped by `f`, with angle wrap (`0x4380ad`-`0x438b1a`).

Extrapolating entities that have no next state isn't traced [I: the other branch at `0x5d5b11`]. Neither is the
client's time-nudge or delay policy [I].

## T5 (spot checks)

**Tick** [V]:
- `sv_fps` is registered as an int, default 20, range 10..1000 (`0x69898d`, dvar pointer `0x2899d88`).
- The server frame computes `frameMsec = 1000 / sv_fps` (`0x87e34d`) and compares it with the residual (`0x27f768c`).

So T5 is 50 ms by default but configurable, while T6 is a fixed 50.

**Movers** [V]:
- The same argument errors exist ("total time must be positive", "accel/decel time must be nonnegative", `0x60c3fe` and
  `0x40ad3e`).
- The constants are the same (0.001 at `0x9abd88`, 1.0000005 at `0x9e97e8`).
- `movedone` and `rotatedone` are registered.

**Traces** [V]:
- `bullettrace` (`0x7f8190`) uses masks `0x280e833` with characters and `0x802833` without, plus the same `0x20`/`0x10`
  clears.
- `physicstrace` (`0x7f8560`) uses the fixed mask `0x820011` and the same
  `(trace, start, mins, maxs, end, passEnt, mask, filter)` call (`0x4ee360`).

`G_RunFrame` order, triggers and client interpolation aren't traced in T5. Assume they match T6 [I], since the code
lineage is the same.

## Engine notes (E2 / E3)

- **Tick.** Use a fixed 50 ms tick. `level.time` is in ms, and think, `nextthink` and trajectories are all in ms.
- **Frame order.**
  1. client touch tests
  2. queued trigger notifies, alternating with script runs
  3. entity think / movers / missiles, parent-first for linked entities
  4. end-of-frame client work
- **Triggers notify through a queue** delivered before scripts run. Each trigger gets at most one `"trigger"` per pass,
  and use-key triggers notify immediately. The 20-unit expansion is only for the area query.
- **Traces.** Treat a box sweep as a capsule: radius = min(half x, half z). Return
  `{fraction, endpos, normal, surfaceFlags, hitType/id}`. Contents masks are as listed in the tables, see
  [collision_contents.md](collision_contents.md).
- **Movers** are piecewise trajectories (accelerate → linear → decelerate) evaluated at time t. `"movedone"` and
  `"rotatedone"` fire when the last phase ends. Clients reproduce the motion from the trajectory, so E2 should network
  or share trajectories, not positions.

## Open

- What the per-entity step `0x6eadc0` and the passes `0x60f650`/`0x831650` are.
- Push/crush rules in `0x608270`/`0x838c60`.
- `contents` offset in `trace_t`.
- The content-mask choice in `G_TouchTriggers`.
- How the use target is selected.
- T5 `G_RunFrame` order.
- Client extrapolation.
