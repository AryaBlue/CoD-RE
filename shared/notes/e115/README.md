# E115 research notes

These notes come from E115, a from-scratch engine (C++/Vulkan) that loads the user's own
installed copies of World at War (T4), Black Ops (T5) and Black Ops II (T6) and runs their
content natively. While building it we read how the stock games actually behave: zombies
rounds and AI, MP rules and killstreaks, audio, lighting, water, vehicles, camo, collision,
fx layouts, pathnodes and more. This folder holds the cross-game notes and the index; the
notes about one game live under that game's folder in `games/<game>/notes/e115/`.

No game files, script bodies, decompiled listings or string tables are included. Where a
note depends on game script it gives our own paraphrase or pseudocode plus a reference
(script file and function) so you can check it against your own install. Paths such as
`<game install>`, `<export root>` and `<scratch>` are placeholders for your own folders.
References to E115 source files (`src/...`, `games/reforged/...`) are context only; that
code is not published here.

## Evidence marks

| Mark | Meaning |
| --- | --- |
| **[V]** | verified: read in the game's own code or data (script, exe, zone), usually with the place cited |
| **[M]** | measured: observed by running something (a probe, a dump, the game) |
| **[I]** | inferred: reasoned from the above, not directly checked |
| **[U]** | unknown: not in the data we have, or not yet found |

## Index

### WaW / T4 — [`games/t4-waw/notes/e115/`](../../../games/t4-waw/notes/e115/)

| Note | Topic |
| --- | --- |
| [mp_t4_tdm_ffa.md](../../../games/t4-waw/notes/e115/mp_t4_tdm_ffa.md) | WaW MP Team Deathmatch and Free-for-all rules |
| [nacht_weapons_economy.md](../../../games/t4-waw/notes/e115/nacht_weapons_economy.md) | Nacht der Untoten weapons, wallbuys and points |
| [t4_effects_sound.md](../../../games/t4-waw/notes/e115/t4_effects_sound.md) | WaW effects and sound playback |
| [t4_hits_damage.md](../../../games/t4-waw/notes/e115/t4_hits_damage.md) | WaW hit detection and damage |
| [t4_pmove.md](../../../games/t4-waw/notes/e115/t4_pmove.md) | WaW player movement (pmove) |
| [t4_viewmodel.md](../../../games/t4-waw/notes/e115/t4_viewmodel.md) | WaW viewmodel |
| [zombies_t4_asylum_ents.md](../../../games/t4-waw/notes/e115/zombies_t4_asylum_ents.md) | Verrückt (asylum) map entities |
| [zombies_t4_later_maps.md](../../../games/t4-waw/notes/e115/zombies_t4_later_maps.md) | what Verrückt, Shi No Numa and Der Riese add to Nacht |
| [zombies_t4_nacht.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht.md) | Nacht der Untoten overview |
| [zombies_t4_nacht_ai.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht_ai.md) | Nacht zombie AI |
| [zombies_t4_nacht_flow.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht_flow.md) | Nacht round flow |
| [zombies_t4_nacht_sounds.md](../../../games/t4-waw/notes/e115/zombies_t4_nacht_sounds.md) | Nacht sounds |

### BO1 / T5 — [`games/t5-bo1/notes/e115/`](../../../games/t5-bo1/notes/e115/)

| Note | Topic |
| --- | --- |
| [bo1_bots.md](../../../games/t5-bo1/notes/e115/bo1_bots.md) | BO1 MP combat-training bots |
| [fx_t5_layout.md](../../../games/t5-bo1/notes/e115/fx_t5_layout.md) | BO1 FxEffectDef layout |
| [t5_weapon_colour_detail.md](../../../games/t5-bo1/notes/e115/t5_weapon_colour_detail.md) | BO1 weapon colour / detail maps |
| [zombies_t5_pentagon.md](../../../games/t5-bo1/notes/e115/zombies_t5_pentagon.md) | Five (pentagon) |
| [zombies_t5_theater_ents.md](../../../games/t5-bo1/notes/e115/zombies_t5_theater_ents.md) | Kino der Toten (theater) map entities |

### BO2 / T6 — [`games/t6-bo2/notes/e115/`](../../../games/t6-bo2/notes/e115/)

| Note | Topic |
| --- | --- |
| [box_model_misses.md](../../../games/t6-bo2/notes/e115/box_model_misses.md) | mystery box models missing after conversion, and fixes |
| [fx_t6_layout.md](../../../games/t6-bo2/notes/e115/fx_t6_layout.md) | BO2 FxEffectDef layout |
| [sky_t6.md](../../../games/t6-bo2/notes/e115/sky_t6.md) | BO2 skies |
| [t6_actor_team_round_count.md](../../../games/t6-bo2/notes/e115/t6_actor_team_round_count.md) | BO2 actor teams and the zombie round count (Origins robots) |
| [t6_hero_lighting.md](../../../games/t6-bo2/notes/e115/t6_hero_lighting.md) | BO2 hero (viewmodel/character) lighting |
| [t6_pathnode_links.md](../../../games/t6-bo2/notes/e115/t6_pathnode_links.md) | BO2 pathnode links |
| [t6_reticle_lens.md](../../../games/t6-bo2/notes/e115/t6_reticle_lens.md) | BO2 sight reticles and lenses |
| [t6_vehicles.md](../../../games/t6-bo2/notes/e115/t6_vehicles.md) | BO2 vehicles |
| [t6_weapon_camo.md](../../../games/t6-bo2/notes/e115/t6_weapon_camo.md) | BO2 weapon camo |
| [zbarrier_t6.md](../../../games/t6-bo2/notes/e115/zbarrier_t6.md) | BO2 zbarrier (boards / box / perk machine pieces) |
| [zombies_t6_struct_spawns.md](../../../games/t6-bo2/notes/e115/zombies_t6_struct_spawns.md) | BO2 zombies struct-based spawns |

### Cross-game — this folder

| Note | Topic |
| --- | --- |
| [animation_t4_t5_t6.md](animation_t4_t5_t6.md) | XAnim across the three games |
| [assets_t4_t5_t6.md](assets_t4_t5_t6.md) | asset formats across the three games |
| [audio.md](audio.md) | sound aliases, banks and playback |
| [collision_contents.md](collision_contents.md) | collision contents flags (proposal for our exporter) |
| [killstreaks.md](killstreaks.md) | WaW / BO1 / BO2 MP killstreaks |
| [lighting_inputs.md](lighting_inputs.md) | light grid, primary lights, probes, static-model lighting |
| [mp_frontend_t4_t5.md](mp_frontend_t4_t5.md) | WaW / BO1 MP front end: create-a-class, default classes, emblems |
| [mp_rules_t4_t5_t6.md](mp_rules_t4_t5_t6.md) | MP game rules across the three games |
| [notes_texture_gaps.md](notes_texture_gaps.md) | BO1 "no colour map" / BO2 "no pixel data" texture gaps |
| [other_games.md](other_games.md) | other CoD titles: what E115 could add next |
| [perk_effects.md](perk_effects.md) | T5 / T6 zombies perk effects |
| [scripting_t4_t5_t6.md](scripting_t4_t5_t6.md) | GSC/CSC scripting across the three games |
| [server_frame.md](server_frame.md) | the T5 / T6 server frame |
| [t4_t5_water.md](t4_t5_water.md) | WaW / BO1 water |
| [world_t4_t5_t6.md](world_t4_t5_t6.md) | GfxWorld / clipMap world data |
| [zombie_movement_t4_t5.md](zombie_movement_t4_t5.md) | zombie movement in WaW / BO1 |
| [zombies_dogs_laststand_rebuild.md](zombies_dogs_laststand_rebuild.md) | dog rounds, last stand, barrier rebuild |
| [zombies_t5_vs_t4.md](zombies_t5_vs_t4.md) | BO1 zombies compared with WaW |
| [zonedump_formats.md](zonedump_formats.md) | the export formats our zone dumper writes |

See [CREDITS.md](../../../CREDITS.md) for the tools and research these notes rely on.
