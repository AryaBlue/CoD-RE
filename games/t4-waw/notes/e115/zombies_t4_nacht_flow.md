# Zombies: T4 Nacht match flow and HUD

How a solo Nacht match starts, what the HUD shows and does, how a round changes over, and the game-over sequence. This is
the companion to `zombies_t4_nacht.md`, which has the rules.

Tags:
- **[V]**: read in the source, with a file:line.
- **[I]**: inferred. Treat as a guess until checked.

Sources:
- **Scripts** are rawfiles dumped with OAT to a scratch folder outside the repo:
  - Nacht's own: `maps/_zombiemode*.gsc` from `nazi_zombie_prototype.ff`.
  - Shared: `maps/_loadout.gsc`, `maps/_introscreen.gsc` from `common.ff`.
- **Strings** come from the English localize assets (`nazi_zombie_prototype.str`, `common.str`).
- **Weapon numbers** come from the zone's weapon assets.
- No script text is copied here.

HUD coordinates are in the 640×480 virtual screen. The colour "blood red" below means (0.423, 0.004, 0).

## Map load to round 1 [V]

1. **Load.** `maps/_zombiemode.gsc:main` (`:9-96`) does its setup, then calls `_load::main`, then the zombie modules
   (weapons, blockers, spawner, power-ups, radio). Then:
   - Starting score is set to 500 on connect (`:451-453`). `score_total` starts at 500 too.
   - The game waits for `all_players_connected` (`:79`), then threads `round_start` and saves the game as
     `zombie_start` (`:90`).
2. **Intro screen.** Nacht's case in `_introscreen.gsc:234` passes no strings. `level.custom_introscreen` is
   `zombie_intro_screen` (`_zombiemode.gsc:391-402`), and it does only this:
   - wait 1 s
   - music state `SPLASH_SCREEN`
   - wait 0.2 s
   - music state `WAVE_1`

   There is **no title text and no black fade-in** from script. The custom intro returns before the black-screen code in
   `_introscreen.gsc:424-427`. Any fade on spawn comes from the engine's load [I].
3. **Player setup.** Client dvars are forced on connect and on spawn (`:461-478`, `:494-498`):

   | dvar | value |
   |---|---|
   | `compass` | 0 |
   | `hud_showStance` | 0 |
   | `cg_fov` | 65 |
   | `ammoCounterHide` | 0 |
   | `miniscoreboardhide` | 0 |
   | third person | off |

   It also sets depth of field (0, 0, 512, 4000, 4, 0). On first spawn the score HUD is initialised and player
   breadcrumbs start (`:503-512`).
4. **Starting weapon.**
   - The level's loadout is `zombie_colt` only. It is also the last-stand pistol, and the arms are
     `viewmodel_usa_marine_arms` (`_loadout.gsc:410-422`).
   - `zombie_colt` weapon file: clip 8, startAmmo 40, maxAmmo 80, damage 20, meleeDamage 150. So it is 8 in the clip and
     32 in reserve [I on how startAmmo splits].
   - meleeDamage 150 is exactly round 1's zombie health, so a knife hit one-shots in round 1.
5. **Starting grenades.**
   - `round_start` (`:939-963`) sets round 1 and health 150, and gives `stielhandgranate` with an empty clip.
   - Round 1's `award_grenades_for_survivors` then sets the clip to 2, because the player is below 25% of max ammo
     (`:1230-1258`).
   - So a solo player starts with **colt 8/32, 2 grenades, 500 points**. The grenade weapon file has clip 4, max 4.
6. **Chalk HUDs.** `round_start` creates two chalk HUDs, then threads `round_think`:
   - #1 at x 0, #2 at x 64
   - both aligned bottom-left, 64×64, blood red, alpha 0 (`:965-984`)
7. **Round 1 intro.** `round_think` (`:1169`) sets music `WAVE_1` and calls `chalk_one_up` *synchronously*, so nothing
   spawns until the intro ends (`:986-1100`). The intro runs like this:

   | t (s) | what happens |
   |---|---|
   | 0 | The text "Round" fades in over 1 s: white, fontscale 16, centred, bottom-aligned at y −265. Chalk #1 is moved to the centre, x −5, y −200. |
   | 1 | "Round" starts a 3 s colour fade from white to blood red. Chalk #1 fades to alpha 0 over 0.5 s (it is already 0). |
   | 1.5 | The `chalk` sound plays and chalk #1 fades in over 0.5 s, showing one tally mark (`hud_chalk_1`). |
   | 4.5 | "Round" fades out over 1 s. |
   | 4.75 | `intro_hud_done`. Chalk #1 slides to the bottom-left corner over 1.75 s. |
   | 6.75 | "Round" is destroyed and `chalk_one_up` returns. |

   Then:
   - power-up counters reset
   - barrier rewards reset
   - grenades are awarded
   - `round_spawning` starts
   - the first zombie spawns at once; the spawn delay comes after each spawn (`:862-883`)

   So **round 1's first zombie appears about 6.75 s after `all_players_connected`**, plus one frame.

## HUD [V]

| element | look and position | behaviour | source |
|---|---|---|---|
| Round tally (rounds 1-5) | chalk #1 shows `hud_chalk_N`, 64×64, bottom-left, blood red | N tally marks, swapped at each round start | `_zombiemode.gsc:1091-1098` |
| Round tally (rounds 6-10) | chalk #1 stays on `hud_chalk_5`; chalk #2 at x 64 shows `hud_chalk_(N−5)` | second group of marks | `:1022-1030`, `:1092-1093` |
| Round number (11+) | chalk #1 becomes a number via `SetValue(round)`, fontscale 32 | at round 11, chalk #2 fades out over 0.5 s and is destroyed | `:1022-1026`, `:1048-1060` |
| Score | drawn by the engine's HUD menu from `player.score`; not a script hudelem [I] | updates on every change | `_zombiemode_score.gsc:177-191` |
| Score popup | yellow (0.9, 0.9, 0) with label "+" for gains; blood red with no label for losses; fontscale 8; right/bottom aligned at x −103, y −71 (each further player −18 y) | on every score change, including purchases (shown as negative). Moves over 0.5 s by x −(20..59), y +(−14..15), fades out over the last 0.25 s, then is destroyed | `_zombiemode_score.gsc:305-407` |
| Ammo counter | the engine's (`ammoCounterHide 0`) | | `_zombiemode.gsc:473` |
| Compass, stance | hidden | | `:468-469` |
| Double Points timer | text "Double Points: " + seconds; font `objective` 2; top-centre, y 350; fades in over 0.5 s | counts down once a second, then is destroyed | `_zombiemode_powerups.gsc:533-594` |
| Insta-Kill timer | "Insta-Kill: " + seconds, same style, y 380 | as above | `:461-531` |
| Max Ammo | "Max Ammo!", same style, y 290 | after 0.5 s, moves to y 270 and fades out over 1.5 s | `:596-630` |
| Nuke | no text. Full-screen white: 0.2 s fade to alpha 0.8, hold until 0.5 s, 1 s fade out | | `:377-399` |

**There are no power-up icons in Nacht, only text lines.** All the texts are [V] from `nazi_zombie_prototype.str`.

Timer quirks [V]:
- **Countdown runs to −1.** The countdown loops while the time is ≥ 0, so it shows 30 down to −1, about 31 s. The effect
  itself is a separate 30 s wait (`:416`, `:448`).
- **Re-grab resets the timer.** Grabbing the same power-up while it is active resets the timer to 30 and creates no new
  HUD element (`:466-471`, `:538-543`).
- **Double Points stacks to ×4.** Re-grabbing it ends the old thread before it can reset the scalar, then doubles the
  scalar again. Points become **×4** until the newer 30 s ends (`:405-419`). This is a real game quirk.

Power-up sounds [V]:

| moment | alias | source |
|---|---|---|
| spawn | `spawn_powerup`, then loop `spawn_powerup_loop` | `:214`, `:224` |
| grab | `powerup_grabbed` | `:271` |
| Insta-Kill active | loop `insta_kill_loop`; `insta_kill` at the end | `:496`, `:519` |
| Double Points active | loop `double_point_loop`; `points_loop_off` at the end | `:568`, `:584` |
| Max Ammo | `full_ammo` | `:623` |
| Nuke | `nuke_flash`; `nuked` on each zombie | `:379`, `:373` |

Prompts (hint strings) come from `add_zombie_hint`, keyed by cost: "buy door 1000", "random weapon 950", "reward
barrier" and so on (`_zombiemode.gsc:136-199`). The text is in the zone's `.str`.

## Round change [V]

When `round_wait` returns (no zombies left and none still to spawn), `round_think` (`:1201-1227`) does this:
- **t 0:** threads `chalk_round_hint`, then waits `between_round_time`, 10 s.
- **`chalk_round_hint`** (`:1103-1166`) runs over those 10 s:

  | t (s) | what happens |
  |---|---|
  | 0 → 2.5 | the active chalk HUD(s) fade from blood red to white |
  | 2.5 | sound `round_over` |
  | 2.5 → 7.5 | the chalk pulses: 5 cycles of 0.5 s fade out, 0.5 s fade in |
  | 7.5 → 10 | the chalk fades back to blood red |

- **Spectators** respawn at the start of the break (co-op only).
- **t 10:** `spawn_delay ×= 0.95`, move speed = round × 8, round++.
- The next `round_think` pass then runs `chalk_one_up` without the intro:
  - the chalk fades out over 0.5 s
  - wait 0.5 s
  - `chalk` sound
  - new marks or number set, fade in over 0.5 s

  It returns after 0.5 s, so **the next round's first zombie comes about 10.5 s after the last kill**.
- **Music:** no music change per round. `WAVE_1` is set once (`:1173`).

## Game over (solo) [V]

1. **Trigger.** When damage would kill the last player standing (solo: always), `player_damage_override` (`:1651-1687`)
   threads the last-stand visuals and calls `player_fake_death`:
   - takes all weapons
   - can't stand or crouch, so the player goes prone
   - zombies ignore the player, and the player is invulnerable
   - controls freeze after 1 s

   Then `end_game` runs.
2. **`end_game`** (`:1689-1756`):
   - Uploads the leaderboard, except in system link or split-screen.
   - **t 0:** "GAME OVER" fades in over 1 s: white, fontscale 3, centred, y −10.
   - **t 0:** below it, "You Survived N Rounds" fades in over 1 s: white, fontscale 2, y +20. In round 1 it reads "You
     Survived 1 Round". **N is the round you died in, not the rounds you finished.**
   - **t 1:** sound `mx_game_over`.
   - **t 3:** `intermission()`.
   - **t 18:** `stop_intermission`, after `intermission_time` of 15 s. Each player's black overlay fades in over 1 s.
   - **t 19.5:** solo calls `MissionFailed()`; co-op calls `ExitLevel(false)`.

   The two text elements are never destroyed. They stay on screen over the intermission [V, nothing frees them].
3. **`intermission()`** (`:2087-2121`):
   - Player health is set to 100.
   - The client gets the `zi` level notify, then the last-stand monitor 0.25 s later.
   - The vision set changes to `zombie` over 2 s.
   - `zombie_game_over_death` (`:2123-2149`): each live zombie freezes in place, then one by one, every 0.5-2.5 s, gets
     its head gibbed and is killed.
4. **`player_intermission`** (`:2151-2253`):
   - `score` is set to `score_total`, so the end scoreboard shows lifetime points.
   - The session state becomes `intermission`, and a full-screen black overlay starts at alpha 1.
   - Camera shots are chosen in random order from the 8 `intermission` structs. Each one:
     - fades the black out over q = min(1, time / 4)
     - flies the camera from the struct to its target at the struct's `speed` (default 20 units/s)
     - fades back to black at the end
   - If the map had only `info_intermission` points, each shot would instead be a 5 s hold with 1 s fades.
   - Nacht's 8 shots run at speeds 20-50, and their paths are 160-870 units long (ents).

   At 20 units/s most shots outlast the 15 s, so a solo game over usually shows **one slow pan** [I from the numbers].
