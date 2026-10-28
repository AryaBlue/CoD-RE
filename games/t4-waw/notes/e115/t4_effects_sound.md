# T4 Nacht: weapon and zombie effects and sounds

The FX and sound side of Nacht's shoot-and-kill loop. This doc covers what isn't already elsewhere:
- **Zombie vocals, boards, windows, doors, round stingers, power-ups and box sounds** are in
  `zombies_t4_nacht_sounds.md`. Only cross-references here.
- **The alias format, falloff, picking rules and limits** are in `audio.md`.
- **Damage, hit locations and gib rules** are in `t4_hits_damage.md` and `zombies_t4_nacht_ai.md` §3.

Tags:
- **[V]**: read in the zone data, a raw file or `t4sp.exe`. All reads were static.
- **[M]**: measured in game. None yet.
- **[I]**: inferred.

Sources:
- raw weapon files (the zone's)
- `nazi_zombie_prototype.ff` and `common.ff`, inflated in scratch for XAnim notetracks
- the zones' asset lists
- the Nacht/common scripts and clientscripts
- OAT's T4 structs (`Common/Game/T4/T4_Assets.h`)
- Plutonium `t4sp.exe` strings and dvar registrations

## 1. Weapon effects

### Fields per weapon [V] (raw weapon files)

| weapon | `viewFlashEffect` / `worldFlashEffect` | `view`/`worldShellEjectEffect` | `impactType` |
|---|---|---|---|
| `zombie_colt` | `weapon/muzzleflashes/pistolflash_view` / `pistolflash` | `weapon/shellejects/pistol_view` / `pistol` | `bullet_small` |
| `kar98k` | `weapon/muzzleflashes/fx_kar98k_view` / `fx_kar98k` | `weapon/shellejects/rifle_view` / `rifle` | `bullet_large` |
| `thompson` | `weapon/muzzleflashes/standardflashview` / `standardflashworld` | `weapon/shellejects/pistol_view` / `pistol` | `bullet_small` |

- **Last shot:** `view`/`worldLastShotEjectEffect` is the same as the normal eject on all three.
- **Which variant plays:**
  - The **view** variants play on the first-person viewmodel.
  - The **world** variants play on the third-person weapon model, for other players and AI.
  - The flash spawns at `tag_flash` and the eject at `tag_brass` [I: the standard CoD tag names; check them on the
    viewmodels].
- **Every one of these is an `fx` asset** (`FxEffectDef`, §3). The names are their `fx/` paths without `.efx`.

### Tracers [V] (dvars in `t4sp.exe` `0x660540-0x660662`)

Tracers aren't per weapon in T4. The client draws them from global dvars:

| dvar | default |
|---|---|
| `cg_tracerchance` | 0.2 (a 1-in-5 chance per bullet) |
| `cg_tracerwidth` | 4 |
| `cg_tracerSpeed` | 7500 units/s |
| `cg_tracerlength` | 160 |
| `cg_tracerScale` | 1 |

The other dvars are `cg_tracerScaleMinDist`, `cg_tracerScaleDistRange`, `cg_tracerScrewDist` and
`cg_tracerScrewRadius`. Their defaults weren't read.

[I] A tracer is a camera-facing quad `length` long and `width` wide, moving from the muzzle to the hit at `speed`.

### Impacts: the `impactfx` table [V structure; I mapping]

- **One asset.** `common.ff` holds a single `impactfx` asset (`common.zone:3069`, unnamed `""`).
- **Layout** (OAT `FxImpactTable`): `name` plus `table` → **16 `FxImpactEntry` rows**, each
  `{FxEffectDef* nonflesh[31]; FxEffectDef* flesh[4];}` (`ZoneCode/T4/FxImpactTable.txt`: count 16).
  - **Row = the weapon's `impactType`.** The engine names are `bullet_small`, `bullet_large`, `bullet_ap`, `shotgun`,
    `grenade_bounce`, `grenade_explode`, `rifle_grenade`, `rocket_explode`, `projectile_dud`, `mortar_shell`,
    `tank_shell` (string table at `t4sp` file `0x4465a0`). The remaining rows are unused or "none" [I].
  - **Non-flesh column = the hit surface type.** There are 31 of them: the 28 in `bullet_penetration_sp`, plus default
    and a few others.
  - **Flesh column**, one of 4: `flesh_body_nonfatal`, `flesh_body_fatal`, `flesh_head_nonfatal`, `flesh_head_fatal`.
    The strings are at `t4sp` file `0x44d79c` [V names; I order].
- **OAT can't dump it.** OAT has no T4 FX or impactfx dumper (`ObjWriting/Game/T4` only has InfoString, Localize,
  Material, Phys*, RawFile, Sound, StringTable, Weapon). The table's entries are references to effects loaded earlier in
  the zone, so they can't be read without a full zone load [I: that needs a zonedump exporter pass].
- **The impact effects that exist** (`common.zone:2721-3033`):
  - small: `asphalt`, `brick`, `concrete(_1)`, `dirt(_1)`, `foliage`, `glass`, `grass`, `gravel`, `metalhit(_1)`,
    `mud`, `plaster_1`, `rock(_1)`, `snowhit`, `waterhit` (all `impacts/small_*`)
  - large: `asphalt`, `brick`, `concrete_1`, `dirt(_1)`, `glass`, `gravel`, `metalhit_1`, `mud`, `plaster(_1)`,
    `rock(_1)`, `waterhit`, `woodhit` (all `impacts/large_*`). **There is no `small_wood*`**, so wood likely uses
    `large_woodhit` in both rows [I].
  - other: `default_hit`, `cloth_hit`, `fx_cushion_hit`
  - flesh: `impacts/flesh_hit`, `flesh_hit_splat`, `flesh_hit_body_nonfatal`, `flesh_hit_body_fatal_exit`,
    `flesh_hit_head_fatal_exit`, `flesh_hit_body_fatal_lg_exit`, `flesh_hit_head_fatal_lg_exit`, `flesh_hit_neck_fatal`,
    `flesh_hit_knife`, `flesh_body_impact01-03`, `flesh_head_impact01-03`
  - **For E115 until the table is dumped:** key `small_<surface>` for `bullet_small` and `large_<surface>` for
    `bullet_large`/`bullet_ap`. Use `flesh_hit_body_nonfatal` for a non-fatal flesh hit and `flesh_hit_*_fatal_exit`
    for a kill [I].
- **Impact sounds** are keyed the same way. The `t4sp` strings at file `0x44d7fc-0x44d894` are `bullet_small_normal`,
  `bullet_small_exit`, `bullet_small_underwater`, `bullet_large_normal/exit`, `shotgun_normal/exit` and
  `bullet_ap_normal/exit` [I: alias prefix + surface, the CoD4-line pattern].

### Blood and gibs on zombies [V] (scripts)

| moment | effect | where | source |
|---|---|---|---|
| any bullet hit | the impact table's flesh column (engine) | the hit point | §1 above [I] |
| head gib | `impacts/flesh_hit_head_fatal_lg_exit` (`headshot`) **and** `misc/fx_zombie_bloodsplat` (`headshot_nochunks`), at `j_neck`, along the tag's forward/up | then `misc/fx_zombie_bloodspurt` on `j_neck` | `_zombiemode.gsc:327-329`; `_zombiemode_spawner.gsc:727-756` |
| limb gib | `weapon/bullet/fx_flesh_gib_fatal_01` at the gib, and `trail/fx_trail_blood_streak` as the trail of the launched limb dyn-ent | the torn-off limb model is launched with `CreateDynEntAndLaunch` | `animscripts/death.gsc:2094-2095`, `:2238` |
| fire | `env/fire/fx_fire_player_sm_1sec` (pain), `fx_fire_player_md` (death), `fx_fire_player_torso` | | `_zombiemode.gsc:332-334` |
| eye glow | `misc/fx_zombie_eye_single` on a linked eye entity, until a head gib or death | | `:323`; spawner `:1476-1516` |
| board torn or broken | `impacts/large_woodhit` (`wood_chunk_destory`) ×3 at the chunk, +0-20 and +0-40 jitter | | `_zombiemode.gsc:318`; spawner `:545-547`; blockers `:651-653`, `:779-781` |
| power-up | `misc/fx_zombie_powerup_on` (on its `tag_origin`), `_grab`, `_wave` | | `_zombiemode_powerups.gsc:21-23` |

## 2. Weapon sounds

### Fields [V] (raw weapon files; `_plr` = the first-person version, the plain alias = what others hear)

| field | `zombie_colt` | `kar98k` | `thompson` |
|---|---|---|---|
| fire (3p / plr) | `weap_colt_fire` / `_plr` | `weap_kar98k_fire` / `_plr` | `weap_thompson_fire` / `_plr` |
| last shot | same as fire | same as fire | — |
| empty fire | `dryfire_pistol` / `_plr` | `dryfire_rifle` / `_plr` | `dryfire_smg` / `_plr` |
| reload 3p | `gr_pistol_reload_notempty_3p`; empty: `gr_pistol_reload_empty_3p` | start `gr_rifle_open_3p`, each round `gr_rifle_round_in_3p`, end `gr_rifle_close_3p` | `gr_smg_reload_notempty_3p` / `_empty_3p` |
| reload plr | `gear_player` (the real 1p sounds are the notetracks below) | — (notetracks) | — (notetracks) |
| rechamber | — | `gr_rifle_rechamber_3p` | — |
| melee swipe / hit | `melee_swing_small` / `_plr`; `melee_hit` | `melee_swing` / `_plr`; `melee_hit` | same as kar98k |
| raise / first raise / putaway | `weap_raise` / `_plr`, `weap_putaway` / `_plr` | same | same |
| pickup / ammo pickup | `weap_pickup` / `_plr`, `ammo_pickup` / `_plr` | same | same |

### Viewmodel notetrack sounds [V] (XAnim notify lists from the inflated zones; times in seconds)

`notetrackSoundMap` maps a notetrack name to an alias. On these weapons every entry maps to itself (e.g.
`gr_1911_mag_in_plr` → `gr_1911_mag_in_plr`). The client plays the alias when the viewmodel anim passes the notetrack
[I: the engine side wasn't read].

| anim (fps, length) | notetracks |
|---|---|
| `viewmodel_colt45_reload_notempty` (24, 2.54) | `gr_1911_mag_out_plr` 0.37, `gr_1911_futz_plr` 1.60, `gr_1911_mag_in_plr` 1.76 |
| `viewmodel_colt45_reload` (empty; 24, 2.88) | `mag_out` 0.37, `futz` 1.44, `mag_in` 1.73, `gr_1911_slide_forward_plr` 2.30 |
| `viewmodel_kar98_rechamber` (30, 1.00) | `gr_kar98_bolt_up_plr` 0.23, `bolt_back` 0.35, `bolt_front` 0.61 |
| `viewmodel_kar98_reload` (30, 2.60) | `bolt_up` 0.16, `bolt_back` 0.30, `clip_in` 1.45, `bolt_front` 2.11, `clip_eject` 2.14, `bolt_down` 2.34 |
| `viewmodel_kar98scoped_reload_start` (30, 1.80) | `bolt_up` 0.13, `bolt_back` 0.23, `gr_kar98_shell_in_plr` 1.34 |
| `viewmodel_kar98scoped_reload_loop` (30, 0.63) | `shell_in` 0.19 |
| `viewmodel_kar98scoped_reload_end` (30, 0.90) | `bolt_front` 0.32, `bolt_down` 0.48 |
| `viewmodel_kar98scoped_rechamber` (30, 1.00) | same as kar98 rechamber |
| `viewmodel_thompson_reload` (30, 1.90) | `gr_thompson_mag_out_plr` 0.43, `mag_in` 1.34 |
| `viewmodel_thompson_reload_empty` (30, 2.53) | `mag_out` 0.43, `mag_in` 0.99, `gr_thompson_charge_plr` 1.71 |
| `viewmodel_knife_stick` (melee charge; 30, 0.93) | `knife_stab_plr` 0.06, `knife_pull_plr` 0.51 |
| `viewmodel_knife_slash` (30, 0.60) | **none**. `knife_slash_plr` is in the map but not in the anim, so the swipe comes from `meleeSwipeSoundPlayer` |

- Fire, pullout, putaway and ADS anims have no sound notetracks. Those sounds come from the fields above.
- **Anim length vs weapon time:**
  - The colt reload anims are 2.54 / 2.88 s, but the weapon's reload times are 1.9 / 2.65 (economy doc).
  - The kar98 reload anim is 2.60 s with reload time 2.5.
  - [I] The engine rescales the anim to the weapon time, so **notetrack times scale with it**. Fire notetracks at
    `t × reloadTime / animLength`.
- The kar98 and colt viewmodel anims live in `common.ff` (colt) and the Nacht zone (kar98, thompson).

## 3. The FX asset format, for an FX player [V] (OAT `T4_Assets.h:3990-4160`)

**`FxEffectDef`:**
- `name`, `flags`, `totalSize`
- `msecLoopingLife`
- `elemDefCountLooping`, `elemDefCountOneShot`, `elemDefCountEmission`, then `elemDefs[]` in that order
- `efPriority`

**`FxElemDef`, one emitter:**
- **Spawn:**
  - `spawn`: looping `{intervalMsec, count}` or one-shot `{FxIntRange count}`
  - `spawnRange`, `spawnDelayMsec`, `spawnFrustumCullRadius`
- **Life:** `lifeSpanMsec` (int range), and `fadeInRange` / `fadeOutRange`.
- **Placement:**
  - `spawnOrigin[3]`, `spawnOffsetRadius`, `spawnOffsetHeight` (float ranges)
  - `spawnAngles[3]`, `angularVelocity[3]`, `initialRotation`
- **Physics:** `gravity`, `reflectionFactor`, `windInfluence`, and `collMins`/`collMaxs` for collision.
- **Velocity curve:** `velIntervalCount` + 1 samples of `FxElemVelStateSample`.
  - Each sample has local and world parts, each `{velocity, totalDelta}`.
  - Each is a `base` + `amplitude` vec3: the value is base + random × amplitude.
- **Visual curve:** `visStateIntervalCount` + 1 samples of `FxElemVisStateSample`.
  - Each holds base and amplitude of `{color RGBA8, rotationDelta, rotationTotal, size[2], scale}`.
  - **Interpolate between samples over the particle's life.** This is the colour, size and alpha curve.
- **Atlas:** `{behavior, index, fps, loopCount, colIndexBits, rowIndexBits, entryCount}` for flipbook sprites.
- **`elemType`:** billboard sprite, oriented sprite, tail, trail, cloud, spark cloud, model, omni light, spot light,
  sound, decal, runner. **Runners spawn other effects.**
- **`visuals`:** depends on the type.
  - one or `visualCount` materials, models, effect refs or sound names
  - decals use `markArray` (2 materials each)
- **Chained effects:** `effectOnImpact`, `effectOnDeath`, `effectEmitted` (with `emitDist` / `emitDistVariance`).
- **`trailDef`:** cross-section verts and inds, `scrollTimeMsec`, `repeatDist`, `splitDist`.
- `sortOrder`, `lightingFrac`, `useItemClip`.

### How the sprites are evaluated and drawn [V] (`t4sp.exe`)

- **Per-elem randoms.** Each elem gets a seed: (elem index + emitter + 0x128 × spawn index) mod 479. That indexes
  fixed random tables (`0x83dbe4..0x83dc0c`), with one table column per property (life, size0, size1, colour, rotation,
  atlas). So **one particle keeps the same random draw for its whole life** (`0x4a4990`).
- **Life** (`0x4a4990`): msecLife = `lifeSpanMsec.base + rand × (amplitude + 1)`.
  - age is clamped to life − 0.01. t = age / life.
  - The visual sample index is ⌊t × `visStateIntervalCount`⌋. frac is the remainder: sample i is weighted (1 − frac),
    sample i+1 frac.
  - Sample stride: 48 bytes = base 24 + amplitude 24.
- **Size** (`0x4a4b6f-0x4a4c0f`): size0 = lerp_frac(base.size0 + rand × amp.size0) over samples i and i+1.
  - size1 uses its own rand **only when elemDef flag `0x10000000` is set**. Otherwise size1 = size0.
- **Size is a half-extent** (`0x4a2110`, the shared quad builder). The corners are
  pos ± A × size0 ± B × size1, with A and B rotated in their plane by the rotation angle (`fsincos` at `0x4a2245`). **A
  sprite is 2 × size wide.** There's no ×0.5 anywhere.
  - **billboard** (type 0, `0x4a2e30`): A and B are the camera's left and up axes, negated as needed. It always faces
    the camera.
  - **oriented** (type 1, `0x4a2ef0`): A and B come from the elem's own orientation.
  - **tail** (type 2, `0x4a3140`): dir = normalised velocity, and the centre is moved size1 back along dir. **The head
    is at the particle and the tail is 2 × size1 long behind it.** A = normalise(dir × (camera − pos)), so it rolls to
    face the camera about its own axis. The width is 2 × size0.
- **Colour** (`0x4a1d30`): per channel, c = lerp_frac over samples of lerp_rand(base.color[k], amp.color[k]).
  - **The colour "amplitude" is a second colour picked between by rand, not added.**
  - Byte 3 is alpha. It's then × fadeAlpha / 256.
  - The 4 bytes are copied straight into the vertex colour dword (`0x4a25c6`). [I: that's D3D9 `D3DCOLOR`, so the
    stored order is **B, G, R, A** in memory.]
- **Distance fade** (`0x4a3500`), d = |pos − camera|:
  - range at elemDef `+0x14/+0x18` {base, amp}, when amp ≠ 0: 1 for d ≤ base, then falls linearly to 0 at base + amp.
  - range at `+0x1c/+0x20`, when amp ≠ 0: 0 for d ≤ base, then rises to 1 at base + amp.
  - fadeAlpha = 255 × min of the two.
  - So `+0x14` hides far particles and `+0x1c` hides near ones. Check the OAT names (`fadeInRange`/`fadeOutRange`)
    against this.
- **Rotation** (`0x4a1f14-0x4a1f96`), with t = frac:
  - rot = `initialRotation` (base + rand × amp) + life_ms × [rotTotal_i + rotDelta_i × (t − t²/2) + rotDelta_{i+1} × t²/2]
  - each term is base + rand × amp. That's trapezoid integration of the angular speed.
- **Atlas UV** (`0x4a1fb0`), for elemDef `+0xa8` `behavior`:
  - **Start frame** (bits 0-1): 0 = fixed `index` (+0xa9); 1 = random; 2 = from the per-effect random byte.
  - **Advance:** bit 2 plays over life: frame += t × entryCount. Otherwise, if `fps` (+0xaa) ≠ 0,
    frame += age_ms × fps / 1000.
  - **Loops:** bit 3 limits loops to `loopCount` (+0xab), then holds the last frame.
  - **UVs:** frame &= count − 1. u0 = (frame & (cols − 1)) / cols and v0 = (frame >> colBits) / rows, where
    cols = 2^`colIndexBits` (+0xac) and rows = 2^`rowIndexBits` (+0xad). The size is 1/cols × 1/rows.
  - `entryCount` (+0xae) = 1 means the full 0..1 UV.
- **Gravity** (`0x4b1170`, at `0x4b1245-0x4b1279`): vel.z −= (gravity.base + rand × gravity.amp) × dt × **800**.
  `gravity` is at elemDef `+0x98`, so 1.0 = the 800 in/s² world gravity.
- **Draw dispatch:** `elemType` byte at elemDef `+0xb4`, through the table at `0x83db7c` (`0x4a3b42`, `0x4a4485`).
  - types 0-3: `0x4a2e30`, `0x4a2ef0`, `0x4a3140`, `0x4a3380`
  - type 4: null
  - types 5-8: `0x4a3730`, `0x4a38c0`, `0x4a39f0`, `0x4a3a70`
- **Decals:** `0x4a36b0` places a mark only when the `fx_marks` dvar (`0x16a2070`) is on. Radius =
  max(size0, size1) + ctx `+0x90`, through `0x4b4120`. Elem flag `0x400` forces mark type 5.
  - The only mark dvars are `fx_marks`, `fx_marks_smodels`, `fx_marks_ents` and `cg_marks_ents_player_only`. There's
    **no mark lifetime or fade dvar**.
  - [I: as in CoD4, marks stay until the mark pool recycles the oldest. The pool size and any fade inside `0x4b4120`
    weren't read.]

**Smallest player that covers Nacht** [I]:
- billboard and oriented sprites, with the atlas
- models (shell ejects are model elems)
- runners
- omni lights (muzzle flash light)
- the sound elem
- decals (impact marks)

Trails and clouds can come later (the blood streak trail, smoke).

**Getting the data:** OAT has no T4 FX dumper, so E115 needs a zonedump pass that walks `FxEffectDef`. The
OAT zone loader already has the struct, and BO1/BO2's FX are close relatives [I].

## 4. Zombie, board, window and round sounds

See `zombies_t4_nacht_sounds.md`:
- **Zombie voice and body:** `amb_vocals` per walk loop; `attack_vocals`/`attack_whoosh`; death `generic_death_german`;
  headshot `bullet_impact_headshot*`; gibs `zombie_head_gib` / `generic_gib_german`; sprint and crawl vocals.
- **Barriers:** `remove_boards` (tear notetracks), `break_boards`, `repair_boards`, `boards_float`, `board_slam`.
- **Window climb:** engine footstep and bodyfall notetracks.
- **Doors and debris**, round `chalk`, `round_over`, game over `mx_game_over`, power-ups, the box, and the radio.

**"Behind" vocals:** there is no separate behind-the-player vocal in Nacht. The only ambient vocal is `amb_vocals`, once
per walk cycle (sounds doc). Later maps added `behind_vocals` [I: not in Nacht's ref table].

## 5. Music and ambience [V] (`clientscripts/nazi_zombie_prototype_amb.csc:1-45`, `clientscripts/_music.csc`)

This closes the sounds doc's open item: the music states mapped to aliases.

| state (set by `_zombiemode.gsc`) | music | rule |
|---|---|---|
| `SPLASH_SCREEN` (`:398`, at game start) | `mx_splash_screen`, one-shot, fade-out 12 | `musicwaittilldone`: the next state waits until it finishes |
| `WAVE_1` (`:401`, and `:1173` each round) | `mx_zombie_wave_1`, **looping**, fade-in 0, fade-out 4 | stays on for the whole game. Setting it again each round is a no-op [I: same-state guard in `musicCmdHandler`] |

Plus:
- **Game over:** `mx_game_over` (sounds doc). **The box:** `music_box` (`music_chest`, `_zombiemode.gsc:235`).
- **Ambience:** package `zombies` with one element, `amb_spooky_2d`, args 5, 8, 300, 2000. Room `zombies` with
  reverb `stoneroom` 1, 1.
  - [I] The args are random spacing in seconds (5-8) and distance (300-2000), as `_ambientpackage` defines them.

## Open

- [I] The impact table's row/column contents. Needs a zone-load dump of `impactfx` (and FX in general) by our zonedump
  exporter.
- [I] `tag_flash` / `tag_brass` on the viewmodels. Notetrack-to-alias playback and anim rescaling are engine-side.
- [I] The four tracer scale/screw dvars.
- [M] All of it in game.
