# T6 actor teams and the zombie round count: why Origins' giant robots don't hold the round

The script agent found that `zm_init` sets every zombie actor's `team` to `level.zombie_team`, and that no script
keeps the three giant robots out of the round's enemy count. In the real game the robots never hold a round open.
This note is the engine side. Researched 2026-10-27.

## Conventions

- **Tags:**
  - **[V]** read in code or data at the address.
  - **[I]** inferred.
  - **[U]** unknown.
- **Sources:**
  - Exe: the Steam `t6zm.exe`, disassembled with capstone.
  - Scripts:
    - gsc-tool decompiles of the patch scripts;
    - the Origins aitype scripts, unlinked from `zm_tomb.ff` with OAT and decompiled with gsc-tool (kept in a scratchpad).
- Only values and addresses are given here, no script text.

## Answer

**Two separate team values, and the round count reads only the engine one:**
1. **Script `self.team`** on an actor is not the AI's team. No server entity or actor field named `team` exists in this build, so the assignment `zm_init` makes is only a script variable [V/I, see below].
2. **The engine AI team** is the sentient's team (`sentient+4`).
   - The script names it **`aiteam`**: actor field entry at `0xba8344`, setter `0x828780`, getter `0x828690` [V].
   - The spawner's `setspawnerteam` (`0x61d000`) stores a team at spawner ent `+0x22c` [V]. **The engine doesn't copy that to the spawned actor** (see [Spawner team](#spawner-team-and-the-aitype-spawner-function)). A new sentient starts on team 9 = spectator, and script sets `aiteam` [V].
3. **`getaispeciesarray(team, species)`** (`0x61b900`), which `get_round_enemy_array` / `get_current_zombie_count` / `round_wait` use, walks the actor slots by **sentient team only** [V].
4. **Origins' giant robot aitypes** (`aitype/zm_tomb_giant_robot_0..2`):
   - `spawner()` calls `setspawnerteam("neutral")`, and `main()` sets script `team` "neutral".
   - The normal Origins zombie aitypes use "axis" [V, decompiled].
   - `zm_tomb_giant_robot.gsc` spawns them with `spawnactor` and never sets `aiteam`. Normal zombies get `guy.aiteam = level.zombie_team` in `_zm_utility::spawn_zombie` [V].
   - So a robot's AI team stays at the sentient default, **9 (spectator)** [I: nothing else on the spawn path writes it]. `zm_init`'s script `team = axis` never changes it.
   - `getaispeciesarray("axis", "all")` never returns them, since `"all"` is mask 0x1fe = teams 1..8. So the round never counts them [I, strong].

So it is engine-side only in the sense that the engine keeps the AI team separately. The data is in the robot's
aitype spawner team.

## Details

**`getaispeciesarray`** (`0x61b900`, builtin table entry `0xb50c28`) [V]:
- **Team argument:**
  - The string `"all"` (scr_const at `0x2405418`) gives mask 0x1fe.
  - Anything else gives `1 << Scr_GetTeam(arg)` (`0x7f3b50`):
    - axis 2, allies 1, then 3+ for team3..., neutral and the rest by their scr_const words.
- **Species argument:**
  - Parsed by `0x61b810`: human, dog, bigdog (table `0xcaede4`) or `all` = 4.
  - It defaults to all.
- **Actor walk:**
  - 32 actor slots of 0x2720 bytes at `[0x2286a2c]` (`0x7f7260` first, `0x7f72b0` next).
  - A slot is used when its in-use bit (`slot+0` bit 0) is set, and `1 << sentient->team` is in the mask (`slot+8` → sentient, `+4` team).
- **An actor is skipped if:**
  - `actor+0x1bc8 == 0`. This is a live/initialised flag: set to 1 at `0x801483` in actor init, cleared at `0x7f7925` [V; name I].
  - `actor+0x1db != 0`. This is the **`delayeddeath`** script field (entry `0xba43ac`) [V].
  - Its species (`actor+0xc`) doesn't match, unless the species is "all".
- **No other filters:** nothing reads `ignoreme`, `ignoreall`, `ghost`, `is_zombie` or health here [V].

**`Scr_GetTeam`** (`0x7f3b50`) [V]:

| string | team |
|---|---|
| allies | 1 |
| axis | 2 |
| team3 .. team8 | 3 .. 8 |
| spectator | 9 |
| neutral, none, free | 0 |
| anything else | error |

So `"all"` (0x1fe) covers teams 1..8 and leaves out both neutral (0) and spectator (9).

## Spawner team and the aitype `spawner()` function [V]

- **Who calls `spawner()`:**
  - At game init, `0x7faab0` (called from the init sequence at `0x600359` / `0x60039e`) does three passes.
  - Pass 1: for every `actor_*` classname, it runs the aitype's `precache(ai_index)` once and stores the index (aitype +0xc).
  - Pass 2: it runs the aitype's **`spawner()`** on every actor-spawner entity (eType 0x11, classname minus `actor_`), as an entity thread on the spawner.
  - Pass 3: for actors already in the map, it runs the species init animscript.
- **Where the handles come from:** `0x622c70` resolves the triplet `main` / `precache` / `spawner` from `aitype/<name>` (handles at +0 / +4 / +8).
- **The spawn path** `spawnactor` / `dospawn` (`0x62e760` → `0x81a110`):
  - It copies the spawner's key fields onto the new entity (`0x63f5d0`, table `0xb5a398`): classname, origin, model, spawnflags, target, targetname, script_noteworthy, count, health, dmg, angles, birthtime, index, lerp_to_*.
  - **`+0x22c` is not among them.**
  - It also copies script variables (`0x63e570`), then runs actor init (`0x801510`) without the spawner.
- **The sentient:**
  - It is allocated by `0x827690` with **team 9** (spectator).
  - Nothing on that path reads spawner `+0x22c`. Its only readers are `getspawnerteamarray` (`0x61bc9a`) and savegame (`0x612e81`) [V for the paths read; I that there is no other copy].
- **So** a spawner's team is used only by `getspawnerteamarray`. The actor's AI team comes from script `aiteam`.

**`getaiarray(team)`** (`0x61b880`) is the same walk with no species argument. It also skips actors for which `0x4cc3a0(species)` is true [V; which species it skips is U].

**The team fields** [V]:
- `aiteam` → `0x828780`:
  - `Scr_GetTeam` → `0x8280a0` writes `sentient+4`;
  - it also writes the client team (`+0x2d4`) and the entity's team nibble (`ent+0x7a`) when there is a client.
- The only other engine "team" field entries:
  - the client-script centity `team` (`0xb1dc50`, read-only, csc side);
  - the vehicle `vteam` (`0xb3fed0`).
  - Neither touches an actor's sentient.
- Other writers of `sentient+4`: `0x5d5480` (vteam, needs a vehicle), `0x65f490` and `0x66bf40` (vehicle and turret paths) [V].

**How the animscript set is picked** [V]:
- It is chosen per actor species from the table `0x2d49534`: index 0 human, 2 = the `zm_` set (`zm_init`…), 3 = `zm_dog_`.
- So the robots (aitype type "zombie") do run `zm_init` [I].
- That is consistent with the script agent's finding, but it only sets the script variable.

**Origins scripts** [V]:
- The robots are spawned by `spawnactor` from `ai_giant_robot_<n>` spawners (`zm_tomb_giant_robot.gsc:108-175`), and stay alive and ghosted between walks.
- The foot-stomp kill loop iterates `getaispeciesarray(level.zombie_team, "all")` and skips `is_giant_robot`. With the robots neutral, that check is defensive [I].
- `level.zombie_ai_limit` drops to 22 during three-robot rounds (`zm_tomb_giant_robot.gsc:199-225`). That is a spawn-cap tweak, not a count fix.

## For E115

- **Two team values:** keep an actor's engine AI team separate from the script `team` variable.
  - The AI team starts at spectator (9) and is set by `aiteam`. Don't copy the spawner team.
  - Run `precache` per aitype and `spawner()` per spawner at map start, so `getspawnerteamarray` works.
- **The enemy query:** the round count and `getaispeciesarray` / `getaiarray` must filter by the AI team, plus `delayeddeath` and live.
- **No per-map rule:** with that, the robots (aitype spawner team "neutral") drop out of the count with no per-map code.

## Open

1. ~~Spawner team copy~~: none found. See [above](#spawner-team-and-the-aitype-spawner-function).
2. Which species does `0x4cc3a0` exclude from `getaiarray`?
3. What exactly is `actor+0x1bc8` (live / think-enabled)?
