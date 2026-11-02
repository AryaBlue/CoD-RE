# T6 pathnode links: one-way links are real directed edges

Every exported T6 graph has one-way links: prison 309, nuked 626, transit 657, tomb 1341, buried 1312, highrise
931, MP maps 19–187. This note checks whether `t6zm.exe` makes them two-way at load. Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in code or data at the address.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - Exe: the Steam `t6zm.exe`, disassembled with capstone.
  - Data: our exported `nav.json` graphs.
- Only addresses and counts are given here.

## Answer

**The engine never adds reverse links, so the one-way links are real directed edges [V].** Our export reads them
correctly. Neither zonedump nor NavGraph should make them two-way. NavGraph has to treat links as directed.

- **Load:**
  - Path init is `0x81e5f0`, called from the game-init sequence at `0x6002b5`.
  - `0x81e550` clears each node's dynamic and transient parts and rebuilds `forward` from `fAngle`.
  - Then `0x81e400`, for every node:
    - sets `wLinkCount = totalLinkCount`;
    - zeroes each link's `disconnectCount` (+6) and bad-place counts (+9..+0xd).
  - It never writes a link into another node [V].
  - The other two init calls right after it (`0x823970`, the base-node table; `0x8229e0`, restoring script-added links) add no links either [V].
- **The only link-adding code is script `linknodes(a, b)`:**
  - Builtin `0x823e00` → `0x822bf0`.
  - It reallocates **only `a`'s** link array with one new link to `b` (dist = |a−b|, flags |= 4), then bumps `a.totalLinkCount` and `a.wLinkCount`.
  - `b` is untouched, so even script links are one-way [V].
  - `0x822bf0` has no other caller [V].
- **The pathfinder:**
  - A* (expansion loop at `0x80d2ea`) walks only the current node's `Links[0 .. wLinkCount)` [V].
  - It reads the target index at link +4 and skips a link whose bad-place count for the team (+9+team) is set [V].
  - Searches run start→goal over out-links [I: the link layout, `linknodes(a, b)` meaning "a can go to b", and the node-removal scan below all fit that; the search setup itself wasn't traced].
- **Disconnects** (`connectpaths` / `disconnectpaths`, bad places):
  - `0x8205b7` and `0x81f710` bump a link's `disconnectCount`.
  - On 0→1 they decrement `wLinkCount` and swap the link to slot `wLinkCount`, so live links stay first [V].
  - The save/restore pair `0x612520` / `0x6131e0` writes and reads that order [V].
- **Dev dvars:**
  - `g_connectpaths` (default 0) and `g_removeRedundantLinks` (default 1) exist.
  - With the defaults, the shipped links are used as is [I: their readers weren't traced].

## The export matches the engine layout [V]

| field | engine offset | OAT `T6_Assets.h` |
|---|---|---|
| pathnode stride | 0x90 (`index × 9 × 16`) | `pathnode_t` |
| `vOrigin` | +0x18 | +0x18 |
| `totalLinkCount` | +0x3c | +0x3c |
| `Links` | +0x40 | +0x40 |
| `wLinkCount` | +0x68 | dynamic +0x24 |
| link stride | 0x10 | `pathlink_s` |
| link `fDist` / `nodeNum` / `disconnectCount` / `flags` | +0 / +4 / +6 / +8 | the same |

`ExportNav.cpp` writes `Links[0 .. totalLinkCount)`, which is what the engine starts with.

## What the one-way links look like (exported data) [V]

- **Prison** has 309 one-way links:
  - 168 plain pathnode → pathnode;
  - 94 negotiation_begin → negotiation_end, i.e. one-direction traversals;
  - the rest pathnode ↔ negotiation.
- **Shape:**
  - Distances: median 113, 95th percentile 244.
  - They are almost all **flat**. On every map, only a handful are steep drops or climbs (|dz| > 40, slope > 0.6). So they are not jump-down ledges.
- **Not a per-node cap:**
  - The target is never near the map's highest link count.
  - Only about a quarter of the missing reverse links would have been the target's longest.
  - So this is an asymmetry in the map compile (traces or radius from one side) [I]. It is not in the exe.
- **Prison node 128** at (1452, 10568, 1368) has `totalLinkCount = 0` in the zone. It has links in from 111, 113, 131, 132 and 154.
  - Prison has 5 such no-out nodes out of 1429.
  - In the real game a zombie that reaches 128 can't route onward from it [I]. How the engine picks a start node near a dead end (whether it tries other nearby nodes) is [U].

## How the engine picks the start and goal nodes [V]

- **Setup:** `0x809000` fills the path's goal node first, then its start node. Each is picked by `0x8259e0` → `0x824a40`, from the goal and start positions.
- **Candidates:**
  - Up to 64 (0x40) nodes within **192** units of the point, from the node tree, walked nearest first [I: the order comes from the query and wasn't traced].
  - A team/flag mask comes from the entity (+0x3d0 bits 0x20000 / 0x10000).
- **Pass 1, over the candidates in order:**
  - **No live links (`wLinkCount == 0`):** set aside on a deferred list (`0x8250bc`).
  - **Behind one of the query's planes** (dot test against the plane list): also deferred.
  - **Point inside the node's box** (xy ±15, z 0..+48 above the node; the node's z can first be dropped to the ground by a 700-unit trace): accepted at once.
  - **Otherwise:** accepted if the trace `0x6f4070` from the point to the node is clear.
- **Pass 2:** the deferred nodes, including dead ends, get the same trace. The first clear one is returned (`0x8250de`).
- **Last resort:** a dvar-gated step (`0x250445c`) [U].

So a dead end like prison 128 is only used when no node with live links is reachable within 192. A* from it then fails at once, since it has no out-links [I].

## For E115

1. **No fix in zonedump.** The export is faithful. Making links two-way there would invent edges the game doesn't have, including against the direction of traversals.
2. **NavGraph:**
   - Keep the links directed; search over out-links only.
   - Don't symmetrise on load.
   - Pick nodes the engine's way: candidates within 192, nearest first. Defer nodes with no live links (e.g. prison 128); accept a node whose ±15 / 0..48 box contains the point, else the first with a clear trace. Then try the deferred ones.
3. **Runtime state, later:**
   - Keep a per-node live count (`wLinkCount`) and a per-link `disconnectCount`.
   - `disconnectpaths` / bad places then hide a link by swapping it past the live count, as the engine does.
   - `linknodes(a, b)` adds a → b only; `unlinknodes(a, b)` removes a → b only.

## Open

1. Trace the A* setup to confirm start→goal direction (the [I] above).
2. What are the plane list and the trace `0x6f4070` in the node pick (hull size, mask), and what is the dvar-gated last resort?
3. Who reads `g_connectpaths` and `g_removeRedundantLinks`?
