# Zombies T6: perk machines, Pack-a-Punch and power from structs

On BO2, no perk machine is in the map as a `script_model`. The scripts spawn each one at runtime from a `script_struct`, so
`zonedump --world` has nothing to place. This doc lists those structs per map, how the script reads them, Nuketown's
exception, and how power switches work. It ends with a recommendation for getting the machines into the game.

Tags:
- **[V]**: read in the decompiled GSC already on disk from the BO1MapConverter work
  (gsc-tool output under `<scratch>/allzm/dump/decompiled/t6`, flat, not decompiled for this doc). `perks:` =
  `_zm_perks.gsc`; `nuked:` = `zm_nuked_perks.gsc`.
- **[M]**: counted in the map ents. These come from OAT Unlinker `mapents` / `addonmapents` dumps of `zone/all`, or from
  the `world.ents` written by `zonedump --world`.
- **[I]**: inferred.

## 1. The generic rule: `perk_machine_spawn_init` [V perks:2842-3080]

1. **Struct set.** The script reads `getstructarray("zm_perk_machine", "targetname")`, or
   `level.override_perk_targetname` when a map sets one (perks:2853-2856).
2. **Mode filter.** `match_string = <ui gametype> + "_perks_" + <start location>`, e.g. `zclassic_perks_transit` (perks:2850).
   - A struct with a `script_string` is kept only when one of its space-separated tokens equals that string.
   - A struct with no `script_string` is always kept (perks:2858-2875).
3. **Spawned ents, per kept struct with `script_noteworthy` (the specialty) and `model`:**
   - `trigger_radius_use` at origin + (0, 0, 30), radius 40, height 70: targetname `zombie_vending`, script_noteworthy =
     specialty (perks:2887-2890)
   - `script_model` at the struct's origin and angles, `setmodel(struct.model)` (perks:2891-2893)
   - `trigger_radius` bump trigger r35 h64, `audio_bump_trigger` (perks:2895-2906)
   - collision `script_model` `zm_collision_perks1`, script_noteworthy `clip`, `disconnectpaths` (perks:2908-2912)
   - optional struct keys copied over: `blocker_model`, `script_int`, `turn_on_notify` (perks:2914-2923)
4. **Machine targetname by specialty** (perks:2925-3080):

| specialty | machine targetname | trigger `script_string` |
|---|---|---|
| `specialty_quickrevive` | `vending_revive` | `revive_perk` |
| `specialty_fastreload` | `vending_sleight` | `speedcola_perk` |
| `specialty_longersprint` | `vending_marathon` | `marathon_perk` |
| `specialty_armorvest` | `vending_jugg` | `jugg_perk` |
| `specialty_scavenger` | `vending_tombstone` | `tombstone_perk` |
| `specialty_rof` | `vending_doubletap` | `tap_perk` |
| `specialty_finalstand` | `vending_chugabud` | `tap_perk` |
| `specialty_additionalprimaryweapon` | `vending_additionalprimaryweapon` | `tap_perk` |
| `specialty_deadshot` | `vending_deadshot_model` | `deadshot_perk` |
| `specialty_weapupgrade` | `vending_packapunch` | - |

   - Pack-a-Punch's struct `target` names a flag struct, spawned as `pack_flag` with that struct's model.
   - Vulture Aid (`specialty_nomotionsensor`) and Electric Cherry (`specialty_grenadepulldeath`) go through
     `level._custom_perks` [I: their targetnames weren't read].
5. **On models.** `level.machine_assets[<perk>].off_model` / `.on_model`; the on model is the off model + `_on` (perks:129-200),
   e.g. `zombie_vending_doubletap2` → `_on`, `p6_anim_zm_buildable_pap` → `_on`. So `zonedump --world`'s swap rule (`<m>_on`) fits.

## 2. Structs per map [M]

The perk structs are in the **base** map ents on every map; none are in the `so_*` addon zones. The token is
`<gametype>_perks_<location>`.

| map | `zm_perk_machine` structs | classic token | classic set |
|---|---|---|---|
| zm_transit | 21 | `zclassic_perks_transit` | Speed Cola, Stamin-Up, Jugg, Double Tap (`zombie_vending_doubletap2`), Revive, PaP (`p6_anim_zm_buildable_pap`), Tombstone |
| zm_highrise | 7 | `zclassic_perks_rooftop` | Revive, Speed Cola, Stamin-Up, Jugg, Double Tap, PaP, Tombstone |
| zm_buried | 8 | `zclassic_perks_processing` | Jugg, Double Tap, Mule Kick (`zombie_vending_three_gun`), PaP, Revive, Stamin-Up, Vulture Aid (`p6_zm_vending_vultureaid`), Speed Cola |
| zm_prison | 9 | `zclassic_perks_prison`, with a leading space | Double Tap, Electric Cherry (`p6_zm_vending_electric_cherry_off`), PaP, Deadshot (`zombie_vending_ads_on`), Jugg, Speed Cola |
| zm_tomb | 6 | `zclassic_perks_tomb` | Jugg, Stamin-Up, Mule Kick (`p6_zm_tm_vending_three_gun`), Revive (`p6_zm_tm_vending_revive`), Speed Cola. The PaP struct (`p6_zm_tm_packapunch`) has no token, so every mode keeps it |
| zm_nuked | 0 | - | §3 |

- Transit's other tokens are for grief/standard per location (`zgrief_perks_town`, `zstandard_perks_farm`, …) and for
  No Man's Land (`znml_perks_town`, `znml_perks_cornfield`).
- Prison's Deadshot struct already names the on model (`zombie_vending_ads_on`), and Electric Cherry an `_off` one.

## 3. Nuketown: random spots, dropped from the sky (KI) [V nuked]

- `init_nuked_perks` (nuked:11-127):
  - deletes any `zm_perk_machine` structs and sets `level.override_perk_targetname = "zm_perk_machine_override"`
  - builds 5 entries: Revive `zombie_vending_revive`, Speed Cola `zombie_vending_sleight`, Double Tap
    `zombie_vending_doubletap2`, Jugg `zombie_vending_jugg`, PaP `p6_anim_zm_buildable_pap`, each with its `turn_on_notify`
  - deals them onto shuffled spots
- **Spots** [M]: 10 `script_struct`s with script_noteworthy `zm_random_machine` (z 2204.86, `script_int` 1-10 = the
  arrival path). Each one's `target` is the ground spot struct, whose `target` is a `p6_zm_cratepile` `script_model`
  (`zm_random_machine_blocker`).
  - 4 of them also have targetname `solo_revive`; in solo, Revive goes to one of those.
  - The crate piles are ordinary script_models, so they're already in `world.glb`.
- `perks_from_the_sky` (nuked:327-385):
  - raises every machine 8000 units and turns its trigger off
  - solo: Revive lands 9-19 s in
  - then one random machine lands per round window: 3-5, 6-9, 10-14, 15-19 and 20-25, each after an extra wait
- `bring_perk` (nuked:159-248):
  - flies the machine in on `perk_arrival_vehicle` along `perk_arrival_path_<script_int>`
  - nudges it 5-20 units back and deletes the crate pile (Revive hides it)
  - turns the trigger on and sends the perk's `turn_on_notify`; there's no power switch
- **So at round 1 Nuketown correctly shows no machines.** No export-time placement can be right: where they land is
  random and when is per round.

## 4. Power [M ents, V scripts]

| map | power |
|---|---|
| zm_highrise, zm_buried | T5 style: `trigger_use_touch` `use_elec_switch` + `script_model` `elec_switch` (`p6_zm_buildable_pswitch_lever_handed` / `p6_zm_pswitch_old_lever`) + `elec_switch_fx` struct. Read by `zm_highrise.gsc:1114`, `zm_buried_power.gsc:11`. The lever is already a `world.glb` script_model; `uses.powerSwitch` matches |
| zm_transit | a buildable: parts are `powerswitch_p6_zm_buildable_pswitch_{lever,hand,body}` structs; built at `powerswitch_buildable_trigger_power` (`zm_transit_buildables.gsc:41-46`, `zm_transit.gsc:2258`). Buildables are their own system, not covered here |
| zm_nuked | none: the machines arm as they land (§3) |
| zm_prison, zm_tomb | no `use_elec_switch` [M]. Tomb uses generators [I: not read] |

## 5. Found while checking: the `--mode` filter dropped the perk structs (fixed)

`zonedump --world --mode zclassic_transit` keeps an ent unless one of its `script_string` tokens is a mode token
(`<gametype>_...`) and none equals the mode.
- **Before:** `zclassic_perks_transit` counted as a mode token that didn't match, so all 7 classic perk structs were
  dropped. `znml` wasn't a known gametype, so the 5 No Man's Land structs were kept instead. That was the committed Transit
  `world.ents`.
- **Fix:** a token `<g>_perks_<loc>` now matches mode `<g>_<loc>`, and `znml` is a gametype. The change is in
  `tools/zonedump/ExportWorld.cpp` `filterEntityMode`, plus `kT6Gametypes` in GameProfile.cpp.
- **[M] Transit after the fix:** exactly the 7 classic structs; 7895 ents kept, 213 dropped.
- Converted T6 maps need `world.ents` re-exported.

## 6. Recommendation

**Recommended: zonedump emits the kept `zm_perk_machine` structs as script_model-style nodes, and a small profile rule
supplies the gameplay side.**

- **zonedump `--world`:** after the mode filter, each `zm_perk_machine` struct with a `model` becomes a node, exactly as a
  `script_model` is placed now:
  - extras: e115_classname `script_struct`, e115_targetname = the §1 machine name (`vending_jugg`, …),
    e115_noteworthy = the specialty, e115_entity = the struct's block
  - mesh shared and deduped; the `_on` models go to `script_models/` by the existing swap rule
  - It has to happen at export: the mode is already applied there (§5), and the meshes come from the same zones. A
    runtime spawn would have to load a glb per machine model instead.
- **Profile, T6 `PerkRules`:**
  - `spawnStructTargetname = "zm_perk_machine"`
  - `spawnTrigger = {radius 40, height 70, z +30}`
  - `spawnCollisionModel = "zm_collision_perks1"`
  - the specialty → targetname table in §1
  - Reforged then makes the `zombie_vending` trigger and the clip from the same struct, as the script does. The engine
    has to create these anyway, since no T6 trigger exists in the ents.
- **Not done this way:** a profile-only rule where the game spawns the models itself. It needs runtime xmodel glbs for
  every machine and would repeat the mode filter in the engine.
- **Nuketown stays script-driven** (§3): random spots and per-round arrivals. The export only has to make the 5 models
  available. Suggested per-map field: `perks.spawnedModels` = the 5 names, exported to `script_models/` by the same path.
  The game then picks spots from the `zm_random_machine` structs and lands a machine per round window. That is a contributor's runtime
  side.
- **Effort [I]:**
  - zonedump: about 40 lines in `ExportWorld.cpp`, reusing `scriptModelEnts` with a struct predicate and the targetname
    table from the profile
  - profile: about 6 fields
  - runtime: the trigger/clip spawn (a contributor's side)
