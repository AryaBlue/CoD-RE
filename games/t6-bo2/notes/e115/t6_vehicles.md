# T6 vehicles: the TranZit bus

The engine side of the TranZit bus, for script slice 20:
- how the vehicle spawns;
- how it follows its node path;
- how players ride it;
- its collision and moving-platform behaviour.

Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in code, data or decompiled script.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - **Exe:** Steam `t6zm.exe`, read with capstone.
  - **Map:** the `zm_transit` map ents (OAT dump).
  - **Scripts:** the decompiled `maps/mp/zm_transit_bus.gsc`, `zm_transit_classic.gsc`, `zm_transit_cling.gsc` and `zm_transit_openings.gsc`.
  - Only addresses, names, values and behaviour are given here, no script text.
- **Builtin table:** script builtins sit in tables of 24-byte entries `{name, id, minArgs, maxArgs, fn, dev}` [V].

## Short answer

- **The bus is a real engine vehicle:**
  - a `script_vehicle` entity with `vehicletype "zombie_bus"`;
  - it drives along a separate graph of vehicle nodes with `attachpath` / `startpath`;
  - its speed is set by script in mph.
- **Players aren't seated or linked:**
  - they walk on it, because the bus and its linked clips are **moving platforms**;
  - the engine carries whoever stands on them [V];
  - script polls `getmoverent()` / `getgroundent()` to know who is "on the bus" [V].
- **The one exception is window clinging:** a player hangs off the outside with `playerlinktodelta`, then `unlink()` [V].
- **Vehicle seats (`usevehicle`, `getseatoccupant`) exist in the engine but transit never uses them** [V: no call in the transit scripts].

## 1. The entity and its spawn

**The map ent** (zm_transit, one only) [V]:

| key | value |
|---|---|
| classname | `script_vehicle` |
| vehicletype | `zombie_bus` |
| model | `veh_t6_civ_bus_zombie` |
| targetname | `the_bus` |
| script_team | `allies` |
| speed | `30` |
| script_vehicleride | `17771` |
| origin | (−7768, 6000, −64) |
| angles | yaw ≈ 0 |

- There are no spawnflags and no `target`, so the bus doesn't start on a path.
- Script finds it with `getent("the_bus", "targetname")` in `zm_transit_classic` init, then runs the bus setup on it.

**Spawn** [V]:
1. The classname table maps `script_vehicle` → spawn function `0x65f510`.
2. That reads the `vehicletype` key and calls `0x65f110(ent, type, 1)`, which:
   - looks the type up among the precached vehicle defs. A missing type errors with "vehicle '%s' not precached".
   - takes a free slot in a **16-slot vehicle array** of `0x2260`-byte records [I: the loop bound 0x10 and the stride].
   - checks the model's tags. A missing tag warns "vehicle '%s' is missing a required tag! switching to default vehicle model".
   - sets **contents** on the entity:
     - `0x812080` normally;
     - `0xa12080` when spawnflag 1 is set.
   - allocates a **sentient** for it (`0x827690`, the same call actors use), so AI can see and target the vehicle [I: that's why it carries a team].

**What the contents bits mean** (see [collision_contents.md](../../../../shared/notes/e115/collision_contents.md)):

| bit | meaning |
|---|---|
| `0x80` | missile clip |
| `0x2000` | weapon geometry |
| `0x10000` | player clip |
| `0x800000` | the vehicle/body bit that the player mask (`0x2818011`) and bullet mask both include |

- So players and bullets collide with the bus.
- Spawnflag 1 adds `0x200000` [U: meaning].

**Script setup** (`bussetup`) [V]:
- `setmovingplatformenabled(1)` on the bus itself.
- `setvehmaxspeed(25)`.
- `useanimtree(zombie_bus)`.
- `supportsanimscripted = 1`.
- Script-side tuning:
  - `accel` 10 and `decel` 30;
  - `radius` 88 and `height` 240;
  - `frontdist` 340 and `backdist` 55;
  - `floor` 36.

## 2. Vehicle nodes and path following

**The nodes are not entities** [V]:
- `info_vehicle_node` and `info_vehicle_node_rotate` are parsed at load by `0x663700` into a node array.
  - The array is at `0x23d4a80`: 0x50 bytes per node, with the count a short at `0x23be000`.
  - No gentity is allocated; the entity branch is taken only for other classnames.
- `_rotate` sets a rotate flag on the node [V: the classname compare feeds the builder's flag argument; what rotate changes wasn't traced, U].

**Engine fields** (table `0xc8eca8`, offsets into the node) [V]:

| key | offset | type |
|---|---|---|
| targetname | +0 | string |
| target | +2 | string |
| target2 | +4 | string |
| script_linkname | +6 | string |
| script_noteworthy | +8 | string |
| spawnflags | +0xc | int |
| speed | +0x10 | float |
| lookahead | +0x14 | float |
| origin | +0x18 | vec3 |
| angles | +0x24 | vec3 |
| radius | +0x30 | float |
| tension | +0x34 | float |

- `radius` and `tension` mean the path is a smoothed spline through the nodes, not straight segments [I].
- Other keys reach script through the node object: `script_float`, `script_string`, `script_notify` and `script_accel` are all read off `nextpoint` in the bus script [V: script use; I: stored as generic script fields].

**Transit's graph** (map ents) [V]:
- 266 `info_vehicle_node` + 24 `info_vehicle_node_rotate`, chained by `target` (one target each; no node is targeted twice).
- **`BUS_OPENING`** (−7640, 6000, −36) starts the one-off intro path. It has spawnflags 1, speed 15 and lookahead 0.6.
  - It is the only chain with an end (one node has no target).
  - Script waits for `opening_end_path`.
- **`BUS_START`** (rotate, the depot, yaw 180) starts the main loop. That path is a closed ring.
- **Stops:** `script_notify "reached_stop_point"` + `script_noteworthy` = stop name.
  - Stops: depot, diner, farm, power, town; plus `power2town`.
  - The stop nodes carry `script_float` 18–19 (the leaving speed) and `script_accel` 10.
- **Ambush points:** `script_notify "reached_ambush_point"` at forest, tunnel and cornfield.
- **Speed markers:** `slow_down` (12 nodes), `resume_speed` (13) and `emp_stop_point` (20), with `script_float` overriding script's default speeds.
  - Also: `start_lava` / `stop_lava`, `enter_transition`, `arriving`, `bus_scrape`, `turn_signal_left/right`.
  - `script_string "map_*"` triggers the location voice lines.

**Builtins** [V: the table entries; the behaviour as noted]:

| builtin | fn | args | behaviour |
|---|---|---|---|
| `getvehiclenode(value, key)` | `0x663bd0` | 2 | node lookup by key (`targetname`, `script_noteworthy`) |
| `getvehiclenodearray(value, key)` | `0x663ca0` | 2 | the same lookup, returning all matches |
| `attachpath(node)` | `0x666450` | 1 | puts the vehicle on the path at that node; clears a path flag (+0x2d0 bit 4) and the path-progress state [V] |
| `startpath()` | `0x666750` | 0 | starts driving. Errors "Can't start path on a vehicle that hasn't…" (no path attached) and "Can't start physics vehicles on path unt…" [V] |
| `setspeed(mph, accel, decel)` | `0x667160` → `0x667040` | 1–3 | see below |
| `setspeedimmediate(mph, accel, decel)` | `0x6671a0` | 1–3 | same as setspeed, and also sets the current speed at once [I: it calls the setspeed body, then writes the current-speed state] |
| `resumespeed(accel)` | `0x667720` | 1 | — |
| `getspeed()` | `0x667380` | 0 | the current speed, in inches/s [I] |
| `getspeedmph()` | `0x6673d0` | 0 | the current speed, in mph |
| `setvehmaxspeed(mph)` | `0x66a980` | 1 | — |
| `setbrake`, `setacceleration`, `setvehgoalpos` (`0x66bfc0`), `cancelaimove` | — | — | present; transit doesn't use them |

**setspeed** (`0x667040`) [V]:
- Sets the "script speed" flag (+0x4e4 = 1).
- `target = mph × 17.6` (inches/s; 1 mph = 17.6 in/s). A negative value errors "Cannot set negative speed on vehicle" and clamps to 0.
- `accel = arg2 × 17.6` if given; otherwise the previous value is kept.
- `decel = arg3 × 17.6` if given; otherwise **`accel × 0.5`** when an accel was given.
- An accel or decel ≤ 0 errors "Acceleration/deceleration must be > 0" and sets both to 17.6 (1 mph/s).
- So the units are mph and mph per second.

**Node events** (the per-frame path step, around `0x65a4a0`–`0x65a650`) [V]:
- The vehicle keeps its current node, next node and distance along the segment.
- When the distance passes the segment length, the remainder carries over, the node advances, and the engine sends **`reached_node`** to the vehicle with the node as its one argument.
- At the path's end it sends **`reached_end_node`**.
- The string table also registers `reached_wait_node` [V: string; when it fires, U].
- Script's `follow_path` relays these. For each `reached_node` it:
  - sets `currentnode`;
  - sends `trigger` to the node;
  - notifies the node's `script_noteworthy` and `noteworthy(name, node)`.
- `script_notify` keys are notified by engine or script [U: who sends `reached_stop_point`; it isn't in the bus scripts' explicit notifies, so probably the engine sends a node's `script_notify` on arrival].
- Node `speed` / `lookahead`: whether the engine applies a node's `speed` by itself when the script hasn't set a speed is [U]. The bus always drives with script `setspeed`.

## 3. How players ride it

**They aren't linked: they stand on a moving platform** [V]:
- `setmovingplatformenabled(b)` (`0x61d1e0`) sets/clears bit `0x80000000` of entity+8 (an entity-state flag word).
- **Per server frame:**
  - the frame function clears a list of moved platforms (`0x332afb0` = 0 at `0x6ecd7a`, right before `level.time += 50`);
  - every flagged entity that moves appends itself (max 64; `0x60fcc5`, `0x65eb10`).
- **Around each player's move:**
  - `0x5d1110`, a client entity function with a pmove-sized stack [I: ClientThink/Pmove] calls `AdjustMovers` (`0x965430`) before and `RestoreMovers` (`0x964ed0`) after;
  - these save, move and restore the listed platforms' origins and angles;
  - so the player's move collides against each platform where it is for that player [V: the save/restore of +0x134/+0x140; I: that it rewinds to the client's time].
  - The same pair also brackets three call sites in vehicle code (`0x66e21e`, `0x66e5cd`, `0x66e9f3`) and one at `0x8c7fbd` [V].
- **Riding:** the player's ground entity becomes the bus, and pmove carries the player with it [I: standard ground-entity mover behaviour; the carry code wasn't traced].
- **Mover vs ground:**
  - `getmoverent()` (`0x6380e0`, players only) returns `ps+0xa8`;
  - `getgroundent()` (`0x638080`) returns `ps+0xa4` for players, or the entity's ground entity (+0xda) for others;
  - both treat `0x3ff` as none [V].

**Script's "on the bus" test** [V]:
- Each update, a player counts as in the bus when `getmoverent()` is any of:
  - `the_bus`, `bus_path_blocker`, `hatch_clip` or `ladder_mantle`;
  - a riot shield or a zombie flagged `isonbus`.
- On ladders the mover counts.
- **Boarding:**
  - `setclientplayerpushamount(0)`, `allowsprint(0)` and `allowprone(0)`;
  - the interior audio loop starts.
- **Leaving:** the reverse, with `pushamount 1`, and sends `left bus`.
- `setclientplayerpushamount` (`0x5e89b0`) writes client field 10 [I: player-vs-player push strength, turned off inside].
- Objects (powerups, grenades, weapons) use `getgroundent()` up to two levels deep against the same names.

**Clinging:** `zm_transit_cling` links the player to a linked position ent with `playerlinktodelta(pos, "tag_origin", 1, …view clamps…, 120, 1)` (`0x61dba0`), then `unlink()` [V].

## 4. Collision and the linked parts

- **The bus body:** the vehicle entity's own collision, with contents `0x812080` [V] from its xmodel/vehicle collision [U: which shape; the vehicle def wasn't dumped].
- **Linked parts:** the bus walls, roof, doors and plow are separate map entities that script `linkto(bus, "", worldtolocalcoords(origin), angles…)`. Each linked solid gets `setmovingplatformenabled(1)` so players can stand on it [V]:
  - `bus_path_blocker` (several) and `cow_catcher_path_blocker`;
  - the door blockers;
  - `hatch_clip`;
  - the plow clip, linked once the cattle-catcher is built;
  - the roof trigger;
  - the ladders and their triggers;
  - the buyable weapon and its trigger;
  - the window "opening" triggers and targets.
- **Triggers:** they need `enablelinkto()` before `linkto` (`0x61d670`) [V: script always pairs them].
- **Moving links:** linked children follow the parent each frame. If a child is a flagged mover, it joins the moved-platform list like the parent [I].
- **Zombies:**
  - stand on the same platforms (`getgroundent`) and are flagged `isonbus` by script;
  - the bus kills or pushes them via script (`busplowkillzombie`, `zombie_surf` when a player stands on a zombie) [V: script].
  - Pathing on or off the bus uses linked nodes: `link_nodes` / `unlink_nodes`, `buslinkdoornodes` [V: script calls].

## For E115 (slice 20)

1. **Spawn:**
   - spawn `script_vehicle` as an entity with the vehicle model and solid, player-blocking contents;
   - give it a team;
   - its path state is separate from the entity.
2. **Load the vehicle nodes** into their own graph (not entities):
   - fields as in the table, with the `script_*` extras kept as script fields;
   - add `getvehiclenode(value, key)` and `getvehiclenodearray`.
3. **Driving:**
   - `attachpath` / `startpath` drive along the chain at the current speed, approaching the target speed at accel/decel (inches/s²);
   - send `reached_node(node)` on passing each node and `reached_end_node` at the end;
   - a straight segment walk is enough at first; spline smoothing (radius/tension) can come later [I].
4. **Speed builtins:**
   - `setspeed` / `setspeedimmediate` / `getspeed` / `getspeedmph` with the ×17.6 maths and defaults above;
   - `setvehmaxspeed` as a clamp.
5. **Platforms:**
   - `setmovingplatformenabled`, plus carrying ground entities in player movement:
     - move the player by the platform's delta each frame;
     - rotate them by its yaw delta [I].
   - `getmoverent` and `getgroundent` are what script reads.
6. **Linking:** `linkto(parent, tag, localOffset, localAngles)` for solids and triggers (`enablelinkto` gate), and `playerlinktodelta` + `unlink` for clinging.
7. **No seats needed** for transit.

## Follow-up: the open items closed (2026-10-27)

### 1. A node's `script_notify`: nobody sends it [V]

- **The exe has no `script_notify` string at all.** Its only engine-known `script_*` keys are noteworthy, linkname, string, label, owner, disable, camera and the class names.
- **No script reads it either.** No script in the zombies dump (common, transit and every other map) contains `script_notify`.
- **The only listener:** `reached_stop_point` is waited on only in `zm_transit_ambush::ambushpointfailsafe`, and that function has no caller.
- So the `script_notify` keys on transit's nodes are dead data, probably left over from Radiant's vehicle-node prefab or the SP vehicle scripts.
- **For us:** don't send them. The bus's stop logic runs entirely off `reached_node` + `script_noteworthy` in `follow_path`.

### 2. Node speed and lookahead [V]

- **Load:** the builder (`0x663700`) defaults `speed`, `lookahead` and `radius` to −1 (unset). It then sets a node flag per key present:

  | key present | flag | stored as |
  |---|---|---|
  | speed | `0x20000` | **mph × 17.6** (in/s) |
  | lookahead | `0x40000` | as is |
  | radius | `0x80000` | as is |
  | (rotate node) | `0x10000` | — |

  The node array caps at 2000 (`0x7d0`). Records are at `0x23d4ad0 + i×0x50`.
- **Sampling:** each step, the path sampler (`0x660930` / `0x660dd0`) lerps **speed, lookahead and radius** between the current node and the next by the segment fraction. It also computes the rotate weight (item 4) into the vehicle's path sample.
- **Which target speed wins** (`0x652f3e`) is set by the speed mode at vehicle +0x4e4:

  | mode | set by | target | accel / decel |
  |---|---|---|---|
  | 1 | `setspeed` | the script speed | script accel/decel |
  | 2 | `resumespeed(accel)` | the **sampled path speed** | script accel/decel; returns to mode 0 once the current speed reaches the target |
  | 0 | — | **sampled path speed** if path flag 4 is set, else the vehicle def's default speed | def accel; decel = 0.5 × accel |

  - In every mode the current speed (+0x4f4) moves toward the target by accel×dt (decel×dt when slowing) without overshooting.
- **Path flag 4:**
  - set only by `drivepath` (`0x666860`, which ORs 6 into the path flags);
  - `startpath` ORs only 2;
  - `attachpath` clears 4.
- **So for the bus** (`attachpath` + `startpath` + `setspeed` every time): **node `speed` is not applied** [V].
  - It would be applied only under `drivepath`, or after `resumespeed`.
- **Lookahead:** sampled with the rest. It feeds the steering look-ahead point [I: its consumer wasn't traced].
- **For us:** follow the script speed only. Keep node `speed` for a later `drivepath` / `resumespeed`.

### 3. Moving-platform carry and view rotation [V]

**Per-frame mover list:**
- A flagged entity (`setmovingplatformenabled`, ent+8 bit `0x80000000`) appends itself to a 64-entry list when it moves (`0x60fcc5`, `0x65eb10`).
- The list is cleared at the top of each server frame (`0x6ecd7a`).

**Pose history:** each listed mover has a history object, found in a pointer-keyed tree at `0x332b2dc` (finder `0x965070`). `0x964bd0(history, time, &origin, &angles)` evaluates the mover's pose at any given time [I: a history of past poses].

**AdjustMovers** (`0x965430(isServer, …, time, relink)`):
1. For every listed mover, saves its current origin (+0x134) and angles (+0x140) into side arrays (`0x332a8b0` / `0x332acb0`).
2. Evaluates its pose at `time` from the history.
3. Writes that pose into the entity.
4. Relinks the entity for collision (`0x6f4420`) if asked.
- The client branch does the same on centities (stride 0x380) for prediction.

**RestoreMovers** (`0x964ed0`) writes the saved origin and angles back and relinks.

So *what is rewound* is every moving platform that moved this frame, set to its origin and angles at the given command time, for the duration of one player move.

**The player step** (`0x8c7e60`, part of pmove; pm in esi, ps = pm→ps):
- **Mover tracking:**
  - When ps.groundEntityNum (ps+0xa4) is a real non-player entity (≥ 18, not 0x3fe or 0x3ff), it sets `ps.moverEntityNum = ground` (ps+0xa8) and `moverTimestamp = cmd.serverTime` (ps+0xac).
  - Re-landing on the same mover just refreshes the timestamp.
- **Grace period:** the mover is dropped (set to 0x3ff) when:
  - ground is 0x3fe;
  - `cmd.serverTime > moverTimestamp + 2000` (constant at `0xf69cd8`);
  - pm_type is 1 or 0xb.
  - Otherwise **it stays the player's mover for 2 s after leaving its surface**, so a jump on the moving bus still travels with it.
  - Pm_flags & 0xc skips the update.
- **Carry:** `0x965780(isServer, …, mover, ps.commandTime, cmd.serverTime, &ps.origin, &angleDelta)`:
  1. Evaluates the mover's pose at the **old** command time and at the **new** server time, from the history.
  2. Turns both into axes (`0x74ea90`).
  3. Moves the player's origin through the inverse of the old pose and then the new pose. So the player keeps their position in the mover's local frame: translation **and** rotation about the mover.
  4. Returns the change in the mover's angles (`0x74bf70`).
- **View:**
  - `ps.delta_angles[YAW] (+0x9c) += AngleDelta(yaw change)`, in full;
  - `ps.delta_angles[PITCH] (+0x98) += pitch change × bg_movingPlatformPitchScale`;
  - the dvar defaults to **0** (range 0–1; "the scale to apply to pitch from the moving platform"), so by default the view follows the platform's yaw but not its pitch.
  - The roll change isn't applied.
- **Then, collision against the moved platforms:**
  1. AdjustMovers to `cmd.serverTime`.
  2. A trace/stick step (`0x8cc6b0` with mask `0x3818813`, then `0x8c7de0` and `0x8cc030`) [I: un-stick / ground check].
  3. RestoreMovers.
  - The full player move itself is bracketed the same way in `0x5d1110` (`0x5d1157` / `0x5d1452`).

**For us:**
- Track `moverEnt` with the 2 s grace.
- Each move, apply the platform's old→new transform to the player's origin, and add its yaw delta to the view yaw (pitch × 0, roll none).
- Collide the player against platforms at their current pose.
- A pose history is only needed for lag compensation. Offline we can use last frame → this frame.

### 4. `info_vehicle_node_rotate` [V: flag and weights; I: meaning]

- `_rotate` sets node flag `0x10000`.
- The sampler's helper (`0x6602f0`) turns the current and next nodes' flags into a **rotation weight** for position t on the segment:

  | current rotate | next rotate | weight |
  |---|---|---|
  | yes | yes (or no next node) | 1 |
  | yes | no | 1 − t |
  | no | yes | t |
  | no | no | 0 |

- The weight goes into the path sample next to the speed and lookahead.
- A second consumer (`0x65c654`) passes "current node is not rotate" as a bool into the vehicle orient step (`0x6539c0`).
- **What it means:** near rotate nodes the vehicle's facing blends toward the **node's own `angles`**, instead of facing along the path tangent [I].
- Transit uses rotate nodes at the stops (depot `BUS_START` at yaw 180, diner, power, town, and the depot transition node). So the bus turns to set headings when it parks.
- **For us:** facing = slerp(path tangent, node angles lerped between the two nodes, weight).

### 5. The `zombie_bus` vehicle def [V: OAT dump of `zm_transit.ff`, vehicles only]

| field | value |
|---|---|
| type | `4 wheel` |
| isDrivable | 1 |
| numberOfSeats | 1 |
| enterRadiusDriver | 80 |
| maxSpeed | **30 mph** (script then caps it at 25 with `setvehmaxspeed`) |
| accel | **12.55** (the def accel used in mode 0; ×17.6 in engine units [I]) |
| maxSpeedVertical / accelVertical | 65 / 60 (helicopter-style fields, unused for a 4-wheel path vehicle [I]) |
| rotRate / rotAccel | 60 / 100 |
| collisionSpeed | 15 |
| suspensionTravel | 7 |
| maxBodyPitch / maxBodyRoll | 5° / 5° |
| tiltFromAcceleration pitch / roll | 2 / 2 |
| tiltSpeed pitch / roll | 1.2 / 1.2 |
| mantleAngle front / back / left / right | 1 / 0.707 / 0.707 / 0.707 |
| worldModel / deathModel | `veh_t6_civ_bus_zombie` |

- **Physics block** (`nitrous_*`, the physics-vehicle tuning):
  - body mass 700, wheel radius 21.8, all-wheel drive, steer angle max 0.82;
  - bbox min (−200, −60, 80), max (200, 60, 15) as dumped [U: z min > max, so the OAT field order may be swapped].
- **Path vs physics:** `startpath` refuses physics vehicles that haven't been set up (the "Can't start physics vehicles on path…" check on the vehicle def). The bus drives as a path vehicle [I: the bus never hits that error].
- **Collision shape:**
  - the entity collides with its **xmodel's collision**; the model dump gives `collLod 1`, so traces use LOD 1's mesh;
  - the walls, roof and floor players actually stand on are the separate linked clip entities (section 4) [I].
  - The bbox above is for the physics sim only [I].

## Open

1. What does spawnflag 1's extra contents bit `0x200000` mean?
2. Who consumes the sampled lookahead (steering)?
3. The exact orient step for rotate nodes (`0x6539c0`).
4. The trace/stick helpers after AdjustMovers (`0x8cc6b0` / `0x8c7de0` / `0x8cc030`).
