# T6 GSC bytecode and VM semantics (what E115's script VM does, and where it was checked)

Distilled from E115's scripting notes, as of 2026-11-01. It covers the T6 bytecode format facts, the VM rules we
rely on, and the places where the behaviour was read out of `t6zm.exe` (Plutonium's copy, addresses are VAs). No script
text is quoted: script behaviour is paraphrased with the file and function named, so you can check it against your own
install. The VM itself (`src/script`) is E115 source and is not published here.

Tags: **[V]** verified (read in the exe, the scripts or by an exact-match check), **[M]** measured by running it,
**[I]** inferred or assumed, **[U]** unknown.

Tools used (see CREDITS.md): xensik's gsc-tool for the decompile that our decoder is checked against, and ate47's ACTS
and the codresearch wiki as opcode references.

## T6 format facts the decoder relies on

All of these are **[V]**: `e115_t6check` reproduces gsc-tool 1.6.1's disassembly byte for byte on all 283 files,
384845 instructions and 23895 labels, and the decoder also insists that every string fixup, import, animation and
animtree site is consumed by exactly one decoded operand.

- **Alignment is to absolute file offsets**, not to the code segment start (the code segment starts at odd offsets).
- **Operands:**

  | Opcodes | Operand |
  | --- | --- |
  | GetByte, GetNegByte, EvalLocalVariableCached, EvalLocalVariableRefCached, SafeSetWaittillVariableFieldCached, the four `*CallPointer` (param count), WaitTillMatch (match count), VectorConstant | u8 |
  | GetUnsignedShort, GetNegUnsignedShort | align 2, u16 (Neg: negated) |
  | GetString, GetIString, EvalFieldVariable, EvalFieldVariableRef, ClearFieldVariable | align 2, u16 string |
  | jumps, DevblockBegin | align 2, i16 from the end of the operand |
  | GetInteger, GetFloat, GetHash | align 4, 32 bits |
  | GetAnimation | align 4, u32 (named by the animtree table) |
  | GetFunction | align 4, u32 |
  | ScriptFunctionCall, ScriptMethodCall, ScriptThreadCall, ScriptMethodThreadCall | u8, align 4, u32; the import entry at the opcode address supplies name, namespace, params and flags |
  | SafeCreateLocalVariables | u8 count, then count × (align 2, u16 name) |
  | Switch | align 4, i32 to the EndSwitch's case count |
  | EndSwitch | align 4, u32 count, then count × (u32 value, i32 offset from the end of the entry) |

- **Switch cases.** A string case has a string fixup at entry + 2. An int case sets bit 23 and keeps the value in the
  low 23 bits, sign-extended. The default is value 0 without a fixup, written last.
- **`#animtree` references** are `GetInteger -1` whose operand address is an animtree table site.
- **GetHash** carries djb2 of the lowercased dvar name (seed 5381, `h * 33 + c`).
- **VectorConstant** packs two bits per component, x highest: `10` = +1, `01` = -1, `00` = 0.
- **Function extent.** A function ends at the first End or Return that no jump goes past and that leaves at most 8
  bytes to the next export. After it come 0-4 junk bytes and a zero u32; the last function ends exactly at the code
  segment end. Dead code after an early `return` is part of the function.
- **String fixup `type`.** 1 on identifiers (locals, fields), 0 on string literals and switch cases. The decoder
  doesn't depend on it.
- **Names.** gsc-tool calls 0x64 `AngleClamp180`, and the bit operators `Bit_Or/Xor/And`.
- **Coverage.** 102 of the 125 opcodes occur in the corpus. CreateLocalVariable, RemoveLocalVariables,
  EvalLocalVariable(Ref), Object, ThreadObject, ProfileStart/Stop, CallBuiltin(Method), GetVector, JumpBack,
  SafeSetVariableFieldCached and EvalLocalArrayRefCached don't, so their operand layouts are **[I]**.

## VM model

### Verified

- **Stack order [V].** Read off gsc-tool's decompiler output next to the bytecode, for example `fake_physicslaunch`
  in `_zm_utility`:
  - binary operators: the left operand is pushed first;
  - call arguments are pushed last to first, after a `PreScriptCall` marker; the method object follows them; a
    function pointer comes last;
  - `Vector` pops x, then y, then z;
  - `EvalArray` pops the array, then the key; `EvalArrayRef` pops the key and indexes the current reference;
  - `NextArrayKey` pops the array, then the key; `VectorScale` pops the vector, then the scale.
- **Locals [V].** `SafeCreateLocalVariables` lists the parameters first. A cached index counts back from the most
  recently created local, so index 0 is the last name in the list.
- **waittill [V].** `WaitTill` pops the object, then the event. The notify arguments come back through
  `SafeSetWaittillVariableFieldCached`, and `ClearParams` drops the rest. `WaitTillMatch n` then pops n values to
  match. `Notify` pops the object, then the event, then its arguments down to a `VoidCodePos` marker.
- **Startup [V].** `common_scripts/utility::struct_class_init` iterates `level.struct`, which only
  `codescripts/struct::initstructs` creates. The runner therefore calls `initstructs` before the map's `main`.

### Assumed

Each item is **[I]**. It is implemented and unit-tested as written, but not yet compared against the game.

- **Scheduling.**
  - 50 ms frames on a fixed clock.
  - `wait t` resumes after `max(1, ceil(t * 20))` frames. Threads due in the same frame resume newest waiter first
    **[V]**.
  - `waittillframeend` runs after all timed wakes of the frame.
- **notify.**
  - `notify` first kills every thread that registered `endon` for the event, at once.
  - Its waiters don't run inside the notify **[V]**. They go in front of the frame's queue, newest first,
    and run when the notifier yields. A notify from native code runs them when the native call returns **[I]**.
  - A thread that notifies its own endon event ends at that notify.
- **Threads and endon.**
  - `thread f()` runs the new thread at once, until it first waits.
  - An `endon` lasts until the function that registered it returns. When it fires, it ends the whole thread.
- **Values.**
  - Arrays are copied on assignment and when passed to script functions, when another holder shares them.
  - Structs and entities are references.
  - Arrays iterate in insertion order.
  - Assigning `undefined` removes a field or element.
- **Arithmetic and conversions.**
  - `/` always gives a float.
  - Using `undefined` or a string as a bool is a runtime error.
  - `x == undefined` is false, not an error.
  - A string concatenated with `undefined` is an error.
- **Errors.** A runtime error prints (developer only) and the thread carries on, as t6zm.exe does. A thread
  that runs more than 5 million instructions without waiting counts as a runaway loop and ends.
- **Dev blocks.**
  - `DevblockBegin` is always taken, so `/# #/` code never runs.
  - `assert` and `assertmsg` check their condition only outside dev sites. Every corpus site is inside one.
- **Linking.** For every call site, the linker tries in order:
  1. the namespace;
  2. this file;
  3. its direct includes;
  4. the builtin table.

  Steps 2 and 3 only apply to unqualified calls. A qualified call (`maps\mp\x::f`) only ever links into that file.
  A name that is still unresolved binds to a stub that counts its calls and returns `undefined`. A qualified call
  whose file or function isn't loaded gets its own stub, named `file::func`. Early on, a qualified call fell back
  to the caller's includes, so `_globallogic::init` silently ran a different `init`; that is fixed and tested.
- **Builtins.** All pure functions, except the session group and the counting asset group.
  - **Core:** `println`, `assert`, `assertmsg`, `spawnstruct`, `isplayer`, `int`, `setdvar`, `getdvar`,
    `getdvarint`, `getdvarfloat`, `getdvarintdefault`, `getdvarfloatdefault`.
  - **Random:** `randomint`, `randomintrange`, `randomfloat`, `randomfloatrange`, all from one deterministic LCG.
  - **Maths:** `distance`, `distancesquared`, `distance2d`, `distance2dsquared`, `length`, `lengthsquared`,
    `vectordot`, `vectornormalize`, `floor`, `ceil`, `sqrt`, `min`, `max`, and trig in degrees (`sin`, `cos`, `acos`,
    `atan`).
  - **Strings:** `tolower`, `toupper`, `getsubstr`, `issubstr`, `strtok`.
  - **Arrays and types:** `isarray`, `isstring`, `isint`, `isfloat`, `isvec`, `getarraykeys`, `arraycombine`,
    `isinarray`, `arrayinsert`, `arrayremovevalue`, `arrayremoveindex`, `getminbitcountfornum`.
  - **World lookups:** `getent` and `getentarray` search `Vm::entities`. `getallnodes`, `getnode`, `getnodearray`,
    `getvehiclenode` and `getvehiclenodearray` search `Vm::nodes` and `Vm::vehicleNodes`, and only exist when the
    host registers them.
  - **Asset registration:** `loadfx` and `precache*` (model, item, rumble, shellshock, string, shader, menu,
    animstatedef, leaderboards, vehicle) do no work. Each returns an int handle per distinct name and counts its
    calls. The runner prints the counts.
  - **Offline session:** a solo offline zombies game with nobody connected yet. `ismp` = 1,
    `sessionmodeiszombiesgame` = 1, the other `sessionmode*` = 0, `issplitscreen` = 0, `isrankenabled` = 0,
    `getnumexpectedplayers` = 1, `getnumconnectedplayers` = 0, `getplayers` = `[]`. These values are chosen, not
    measured **[I]**.
- **Lookup rules [I].**
  - `getent` with more than one match is a runtime error; no match gives `undefined`.
  - Lookups compare the field's text form, so `"12"` finds a field stored as the number 12.
  - Arguments are `(value, key)`. With no arguments, a lookup returns the whole list.
  - `getarraykeys` returns keys in insertion order.
- **Not modelled yet.** Code fields backed by engine memory, the `death` and `entityshutdown` notifies on entity
  freeing, CSC, and animtree values. `GetInteger` animtree references push -1.

## A thread call's value, and runtime errors (read from t6zm.exe)

The VM loop was found from the `"%s script runtime error"` string (file 0x80ef94, VA 0xc10b94). Its one caller,
0x55cb10, prints only under the developer flags and returns. Four VM sites call it.

- **Errors carry on [M].** After the print at 0x8f79b2, the VM clears the error and switches on the failing opcode
  (byte table 0x8f80c0, jump table 0x8f8064, opcodes 0x1a to 0x7a). Each case fixes the stack and jumps back to the
  loop (0x8f43f0), so the thread goes on with the next opcode. The cases group exactly as our opcode list does (all
  binary ops together, all four conditional jumps together), which confirms the opcode numbering. Per case:
  - calls (builtin, function, method, thread, pointer): pop to the call's marker; the result is undefined;
  - `EvalArray`, `EvalFieldVariable`: undefined;
  - ref ops: a throwaway ref; `GetSelfObject`, `CastFieldObject`: a throwaway object;
  - conditional jumps: pop the condition and fall through, without jumping;
  - `Wait`, `RealWait`, `ClearArray`, `SetVariableField`, `Switch`: pop one; a failed wait doesn't wait;
  - `WaitTill`, `WaitTillMatch`, `EndOn`: pop two; `Notify`: pop to the marker;
  - binary ops: pop one and keep the left operand. Ours have popped both by then, so the result is undefined [I];
  - the rest (`CastBool`, `BoolNot`, `IsDefined`, the dvar and vector ops...): go on with the stack as it is.
- `Vm::recover` does the same from the stack size before the op. VM faults (stack underflow, bad locals, call depth,
  the op budget) are terminal and still end the thread [I]. `--errors-end-thread` (`Vm::errorsEndThread`) keeps the
  old behaviour for comparing.
- **A thread call's value [M].** A function call allocates a child of the caller's local id (0x618840), a thread call
  a new thread (0x482c40). At `End`/`Return` the VM asks for the parent (0x4f9470, 0 for a thread). With none, `End`
  writes undefined to the caller's slot (0x8f6538) and `Return` writes its value (0x8f6637). A `wait` writes
  undefined there (0x8f5cda) and resumes the caller. So a thread that returns before it waits gives its value to the
  caller. `get_closest_player_using_paths` now gets the validator's answer.


## Notify and the time lists [V]

Read from t6zm.exe (Plutonium addresses):
- **Notify doesn't run its waiters.** The `Notify` opcode (handler 0x8f6102) calls VM_Notify (0x8f3620). VM_Notify
  ends the endon threads at once (0x8f3300, 0x8f3380, 0x8f34b0). Each waiter gets the notify's arguments copied onto
  its saved stack. It's then put on the thread list of the current time (0x2dea814 at time 0x2dea810, through
  0x5cd170 and 0x4704e0). Nothing reachable from VM_Notify, five calls deep, gets to the VM loop (0x8f4380) or
  its entry points (0x8f8130, 0x8f82b0).
- **The time lists are LIFO.** 0x4704e0 links a new entry at the list's head (0x8f1b70 writes the parent's +0). The
  run loop (0x8f8130, Scr_RunCurrentThreads) takes the head again each time round. So:
  - threads due in the same frame resume newest waiter first;
  - a notify's waiters go in front of what's still due, and run as soon as the notifier yields.
- **The waiter walk.** VM_Notify walks the event's waiters from the list's tail (+4, the oldest) and pushes each at
  the head, so the newest waiter runs first. This confirms the newest-first order.
- **Native notifies** are run by the game's Scr_RunCurrentThreads calls (0x4eb110, seven callers). The frame's
  Scr_IncTime (0x653f10) runs them, does the frame end, then time++. We run the queue when the native call returns
  **[I]**.

`Vm::notify` now queues its waiters (`Thread::State::Queued`) in front of `queued_`. `runFrame` adds the due waits,
newest first, behind them. `execute` drains the queue when the outermost run hands back to native code.
`--notify-runs-waiters` and `--waits-oldest-first` keep the old ways for comparison.

**What it fixes [M].** Tomb's `_zm_challenges::player_stats_init` (51 errors) runs from the `connected` notify.
Before, it ran inside the notify, before `callback_playerconnect` reached `spawnclient` (`self thread`, which runs at
once) and `give_personality_characters` set `characterindex`. Now it runs after that thread yields, and
`characterindex` is set. **0 errors.**

## The script RNG [V]

`randomint`, `randomintrange`, `randomfloat` and `randomfloatrange` share one game-wide LCG at 0xd46804:
- the step is `seed * 0x343fd + 0x269ec3`;
- irand (0x405990) is `min + (((seed >> 17) * (max - min)) >> 15)`;
- flrand (0x41c8d0) is `min + (seed >> 17) * (max - min) / 32768`;
- `randomint` of 0 or less is "RandomInt parm must be positive integer." (0x83d180);
- `randomintrange` with max not above min is an error too (0x83d200).

Ours matches. The game seeds the LCG from Sys_Milliseconds (0x4203fb, and G_InitGame's seed at 0x67e9f0), so a real
game never repeats. `--seed n` sets ours; without it the VM's fixed seed holds.


## The error groups

| group | where | count before | now | verdict |
| --- | --- | --- | --- | --- |
| `stow_on_back` "undefined is not a bool" | `_weapons.gsc` stow_on_back: an or-condition whose right side reads the player's `hasriotshield` field | nuked 11, buried 3, highrise 3 | the same kind | **[V] faithful.** No script sets `hasriotshield` on players (only `_globallogic_player` clears it, and tombstone sets it on its struct). t6zm.exe has no `hasriotshield` field. The jump ops error on undefined ("cannot cast %s to bool", 0x8f674f, 0x8f6815). They then fall through, so it returns as the game does. |
| `player_stats_init` and `onplayerconnect` | tomb `_zm_challenges` | tomb 51 | 0 | **fixed [V]**: notify queues its waiters (above) |
| detach "isn't attached" | `_zm_spawner::zombie_head_gib` hats | buried 5 | 0 | **fixed [V]**: detach (0x844150) ignores G_EntDetach's result (0x6a1ff0). It matches the tag exactly, and no tag is the empty tag. attach (0x844060) detaches a same-model, same-tag one first, then errors "already attached" |
| `ceiling_ring_update_position` | tomb `quest_air`: `self.angles[0]` | tomb 16 | 0 | **fixed [V]**: angles (+0x140) and origin (+0x134) are vectors in the gentity (field table 0xc6ccb0). A map ent with no `angles` key reads (0, 0, 0) |
| `staff_ice_dig_pieces` | tomb `main_quest`: `level.ice_staff_pieces = arraycopy(...)` | tomb 9 | 0 | **fixed [V]**: `arraycopy` (0x840a90) is a native builtin; it was missing |
| `nuke_powerup` size of undefined | `arraysort( zombies, location )` | transit 2, nuked co-op 2 (new: more nukes drop now) | 0 | **fixed [V]**: `arraysort` (0x840bd0) added: (array, origin, nearest first = 1, most, max dist). It takes entities only, up to 1024, by squared distance |
| `turned_player_buttons` | transit_dr `_zm_turned`: `self issprinting()` | 7991 | 0 | **fixed [I]**: `issprinting` added, 0 unless the host holds sprint |
| `dig_spots_respawn` | tomb `zm_tomb_dig` | tomb 4 to 8 | left | **[I] content.** `level.weather_snow` and `level.a_dig_spots` are set by `init_weather_manager` and `dig_spots_init`, which haven't run when `end_of_round` first comes. Not generic. |
| `zombie_goto_entrance` | tomb | 0 | 9 (3 + 3 + 3) | **[I] left**: a zombie removed while it runs its entrance animscripted, then a missing entrance name. It shows in some runs only |
| `treasure_chest_canplayerreceiveweapon` | transit dogs, 1 | 0 | 1 | **[I] left**: one undefined flag on the box roll; it needs a look |

The fixed rows are measured in the final runs below **[M]**: tomb has no `ceiling_ring` or `staff_ice` errors, and
transit_dr no `turned_player_buttons` ones.

## getaiarray [V]

`getaiarray` (0x840f90) takes any number of team arguments. 0x4bc8b0 ORs them into a mask, and none gives 0x1fe. It
skips:
- an actor not in use (+0x1bc8);
- an actor in `delayeddeath` (+0x1db);
- an actor for which 0x51c280 is true: species 0 or 3 of the table at 0xd64f88. Those are **dog** and **zombie_dog**.

So `getaiarray` never returns dogs; `getaispeciesarray(team, "all")` does. Ours matches.


## Earthquakes [V: GScr_Earthquake, CG_StartShakeCamera, CG_UpdateCameraShake, CG_ShakeCamera]
- `earthquake(scale, seconds, origin, radius)`: scale, duration and radius must each be > 0.
- The client keeps 4 shake slots. A new quake takes a free slot, else the one shaking least.
- Per slot: falloff = 1 - distance / radius, strength = scale x (1 - elapsed / length). The strongest slot shakes,
  with its size capped at 1.
- The view turns by sin(t x {25.13, 47.12, 37.70} + phase) x strength x {18, 16, 10} degrees x size, for pitch, yaw
  and roll, with t = ms / 600. The phase is randomised while nothing shakes.
- [I] Roll isn't applied.

## Bool casts [V: VM_Execute, Scr_CastBool_NonInteger]
- Int casts directly; float casts as nonzero.
- Everything else is the error `cannot cast %s to bool`, undefined included. Our error is the real one, so
  `stow_on_back`'s `hasriotshield` error happens in T6 too.

## Script model anims [V: GScr_UseAnimTree, GScr_SetAnimInternal, GScr_ClearAnim]
- `setanim(anim, weight = 1, goal time = 0.2, rate = 1)`: undefined takes the default.
  - The checks run in this order: rate >= 0, then goal time >= 0, then weight in 0..1.
  - An ent without a tree is an error. `useanimtree` gives one ent a tree; `scriptmodelsuseanimtree` gives every
    script_model one.
- `clearanim(anim, goal time)`: both arguments are needed.
- The host (ScriptLevel::animateModels) looks for the ent's model glb in `script_models/` and plays the clip of that
  name in it. The glb takes over from the world nodes or spawned model that drew the ent; those nodes stay hidden
  and still carry the placement.
- [I] Only script_models are checked for a tree. The xanim's own rate / goaltime / goalweight params aren't read.
  clearanim holds the pose where it is.
- [U] Only the fxanim models have exported clips. Die Rise's elevator doors (`v_zombie_elevator_doors_*` on
  `p6_anim_zm_hr_elevator_common`) need a converter export before they move. The end-of-run log line
  `script anims:` lists the missing `model anim` pairs.

