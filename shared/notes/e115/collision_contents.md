# Collision contents in the collision glb (proposal)

Status: proposal, not implemented. The writer is E115's zonedump (`tools/zonedump`, `--collision`); the reader
(`src/physics/LoadCollision.*`, `CollisionMesh.*`) is the engine's. This page is the contract between them.

Tags as in the other research pages: **[V]** read in the games' code or data, **[M]** measured on stock maps,
**[I]** inferred.

## Why

Today zonedump applies one contents mask at export (WaW's player mask `0x281C011` for every game) and writes one
flat, unlabelled triangle list. Two problems follow:

- The engine can't ask different questions of the same map. Players, AI, bullets, grenades and vehicles each trace
  against different contents in the games, and a single export answers only one of them.
- The mask differs per game, and a wrong guess can only be fixed by re-exporting.

Keep the contents in the glb and filter at run time.

## What the games use

| game | alive | dead/spectating | dead when | tweak | source |
|---|---|---|---|---|---|
| T4 MP | `0x2818011` | `0x810011` | `pm_type >= 8` | `pm_type == 4`: `&~0x2018000 \| 0x800` | [V, Plutonium t4mp.exe VA `0x4636f0`-`0x46371e`] |
| T4 SP / zombies | `0x281C011` | `0x810011` | `pm_type >= 8` | `pm_type == 4`: `&~0x201C000`, no sky bit | [V, Plutonium t4sp.exe VA `0x665cc4`-`0x665ce0`] |
| T5 MP | `0x2818011` | `0x810011` | `pm_type >= 9` | `pm_type == 4`: `&~0x2018000 \| 0x800` | [V, BlackOpsMP.exe `FUN_007e1ae0`, `0x7e1c39`-`0x7e1c65`] |
| T6 MP | `0x2818011` | `0x810011` | `pm_type >= 10` | `pm_type == 5`: `&~0x2018000 \| 0x800` | [V, Plutonium t6mp.exe VA `0x7baa8b`-`0x7baab9`] |

All four set `pm.tracemask` in the same code shape. The tweak drops player clip and the body bit and, except in WaW SP,
adds sky. b2w's `0x281C011` is WaW **SP**'s mask; WaW MP uses BO1's. T6 numbers its pm_types one higher from that
point. The T4/T6 values come from Plutonium's builds, not the stock exes (the stock T6 `.text` is DRM-encrypted). The site matches
the stock pattern, but Plutonium could in theory have patched it [I].

Contents bits, read from the clip materials (`dmaterial_t {char name[64]; int surfaceFlags; int contentFlags}`) of
WaW `mp_airfield` and BO1 `mp_nuked` [M]. The two games agree on every bit seen:

| bit | meaning (by the materials that carry it) |
|---|---|
| `0x1` | solid (caulk, world brushes) |
| `0x10` | glass / thin see-through (bus windows, curtains) |
| `0x20` | water (`puddle_muddy_green`) |
| `0x80` | missile clip (`clip_missile`) |
| `0x200` | vehicle clip (`clip_vehicle`) |
| `0x400` | physics clip (`clip_physics`) |
| `0x800` | sky (`sky_day`, `sky_pacific`, surf `0x34`) |
| `0x1000`, `0x40` | no-sight bits (`nosight_noclip 0x1040`, `clip_nosight 0x31640`) |
| `0x2000` + `0x80` | weapon-only geometry: `0x2080` on detail brushes and `clip_weapon 0x2040` |
| `0x10000` | player clip (`clip_player`, `ladder`) |
| `0x20000` | AI clip (`clip_ai`); `clip` = `0x30200` = player + AI + vehicle |
| `0x1000000` | mantle (`mantle_on`, `mount`) |
| `0x8000000` | structural/detail marker, on brushes alongside the real bits [I] |
| `0x10000000` | hint |

### Other T4 SP trace masks [V, Plutonium t4sp.exe]

| trace | mask | bits beyond solid `0x1` | where |
|---|---|---|---|
| player bullet | `0x280E833` | `0x2`, glass `0x10`, water `0x20`, sky `0x800`, weapon `0x2000`, `0x4000`, `0x8000`, `0x800000`, body `0x2000000` | pushed at `0x4e5bcd` in the bullet trace helper `0x4e5b80`, called from the penetration loop `0x4e61f0` |
| player move (alive / dead) | `0x281C011` / `0x810011` | (table above) | client `0x665cc4`; server `0x4e8945` uses the ent clipmask `+0x1b8`, set to `0x281C011` at `0x67c283` |
| actor move | `0x2820011` | AI clip `0x20000` instead of player clip | ent clipmask set at `0x4b49ba` |
| AI sight [I: that it's sight] | `0x280D803` | `0x2`, sky, no-sight `0x1000`, `0x4000`, `0x8000`, `0x800000`, body; no glass, water or weapon `0x2000` | pushed in actor function `0x4def20` at `0x4df012` and `0x4df0e7` |
| MP spawn sight (`isspawnpointvisible`) | `0x806833` | | t4mp, see [mp_t4_tdm_ffa.md](../../../games/t4-waw/notes/e115/mp_t4_tdm_ffa.md) |

- Others seen but not identified: `0x820011`, `0x280E091`.
- **What bullets pass and hit:** bullets pass player clip (`0x10000`), missile clip (`0x80`) and the no-sight bits
  (`0x40`/`0x1000`). They hit glass, water and `0x2000` weapon-only geometry, which players walk through.
- **AI sight is the opposite on two points:** it sees through glass and weapon-only geometry, and it's blocked by
  `0x1000` no-sight.
- [I] For one Reforged ruleset: use these T4 SP values as the default player-bullet and AI-sight masks.

Brush-entity brushes (`*N`) are stored in their entity's local space, and the clipmap includes trigger brushes
(material `trigger`, surf `0x40080`, contents `0x08000001`). On airfield, 62 of them sat at the map origin in the
current export [M]. Contents alone can't tell a trigger from a wall (both have `0x1`). The entity's classname has to
decide, so the writer must handle `*N` per entity anyway.

## Proposal

### File

One primitive per distinct **(effective contents, surface flags)** pair. Each primitive gets its own material whose
`extras` carry the bits:

```json
{"name": "contents 0x08010000", "doubleSided": true,
 "extras": {"e115_contents": 134283264, "e115_surface": 278688}}
```

- Effective contents: the AND along the aabb path for terrain (research 6.3), and the brush's contents for brushes.
- Brush entities stay out of the world primitives. Each solid `*N` becomes its own node, placed at the entity, with
  the entity's index in `extras.e115_entity`, so doors and the like can move later. Skip `trigger*` classnames, or
  write them under a separate `triggers` node with `extras.e115_trigger: true` for gameplay use. They're never
  solid.
- The glb root `extras.e115_collision` names the game's masks, so the engine never hard-codes per-game bits:

```json
"extras": {"e115_collision": {"game": "t5", "masks": {"player": 42041361, "player_dead": 8454161}}}
```

  Only masks read from code go in. Unknown ones are left out, and the engine falls back to its own default.
- Export everything with a non-zero contents. Drop nothing at export except contents 0 (decals, portals with 0).

Why primitives and not a per-vertex attribute (`_CONTENTS` u32):
- A map has a few dozen distinct values (airfield: about 40 brush (contents, material) groups [M]). Primitives cost
  nothing per triangle, and any glTF viewer still opens the file and colours each contents group differently, which
  makes debugging easy.
- Custom vertex attributes need the reader and writer to agree on an `_` name and component type, and they triple
  the storage (the soup is unwelded).
- The engine needs per-triangle contents in memory anyway, and it gets that from the primitive.

### Engine

- `CollisionMesh::addTriangle(a, b, c, contents = 1)`, storing `uint32_t contents` in `Tri`.
- `capsuleContacts(..., uint32_t mask = ~0u)` and `raycast(..., uint32_t mask = ~0u)` skip triangles with
  `(contents & mask) == 0`. The default keeps today's behaviour for callers and tests.
- `loadCollisionMesh` reads `e115_contents` per primitive (absent = `0x1`, so older exports load unchanged) and the
  root masks.
- `PlayerMove` passes the map's player mask. That's a one-line change in PlayerMove, so it's the lead's to apply.
- Tests in `tests/test_physics.cpp`: a mask that excludes a triangle lets the capsule pass, and the default mask
  matches the old behaviour. A glb round trip with two contents groups loads with both values.

### Migration

1. Writer: per-contents primitives, root masks, `*N` placed per entity, triggers split out.
2. Reader and CollisionMesh mask support (backwards compatible: no extras = everything solid).
3. PlayerMove uses the map mask.
4. Re-export the test maps. Check airfield: no boxes at the origin, the sky shell still solid.

## Open

- `0x4000` is in WaW SP's mask only (not WaW MP, BO1 or BO2). No material on airfield or mp_nuked uses it [M].
- Whether `0x8000000` changes behaviour or is only a compile-time marker [I].
- Static-model collision contents: T6 has `cStaticModel_s.contents`; T4/T5 don't [V, research 6.4].
