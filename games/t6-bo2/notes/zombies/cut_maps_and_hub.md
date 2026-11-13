# Cut zombies content left in retail BO2 - BO1 maps, the hub test map and unused gametypes

Found by reading strings in t6zm.exe / t6mp.exe and dumping the retail zones with OpenAssetTools (Unlinker).
No game files are stored here, only names and where they sit.

## Nacht, Der Riese and Moon are registered as BO2 maps

These are the leftovers of the unreleased fifth DLC, which is already well documented.

- `zm/gametypestable.csv` start location rows (type 5) list `zm_prototype`, `zm_factory`, `zm_moon`
- The same table has two dev maps first: `zm_bus_test` ("Bus Test") and `zm_meat`
- Type 6 rows wire all five to `zclassic`
- Loadscreen materials and images ship in `code_post_gfx_zm.ff` (image data in zm.ipak)
  - `loadscreen_zm_factory` - Der Riese blueprint
  - `loadscreen_zm_moon` - Moon comic
  - `loadscreen_zm_prototype` - the Kino comic used as a stand-in
  - `loadscreen_zm_meat` - neon "Tasty Meat - catch it!" street
- The map select icons the table names (`menu_zm_map_prototype_blit`, `..._factory_blit`, `..._moon_blit`) are not shipped
- English strings
  - `MPUI_PROTOTYPE` "Nacht Der Untoten", `MPUI_PROTOTYPE_CONTAINMENT` "Nacht Der Untoten (Containment)"
  - `MPUI_FACTORY` "Der Riese", `MPUI_MOON` "Moon"
  - `MPUI_PROTOTYPE_LOC` / `MPUI_FACTORY_LOC` "WORLD AT WAR", `MPUI_MOON_LOC` "BLACK OPS"
- Moon support code is still there
  - t6zm.exe has `equip_gasmask_zm` and `equip_hacker_zm` hardcoded next to each other
  - `setzombieshrink` builtin (Shangri-La shrink ray) is still registered
  - common zombies scripts: `_zm_equip_gasmask`, `_zm_equip_hacker`, seven `_zm_hackables_*`, `_zm_jump_pad`

## zm_meat is a hub map, not the Meat mode

- `MPUI_MEAT` = "Hub Test", `MPUI_DESC_MAP_MEAT` = "Pass the meat Dear!", `MPUI_MEAT_LOC` = "BLACK OPS 2"
- Variants: `MPUI_MEAT_RACE` "Meat on the Tarmac (Race)", `MPUI_MEAT_DEAD_POOL` "Meat on the Tarmac (Dead Pool)"
- `ZOMBIE_EXIT_MEAT` = "Hold [use] to end match and go back to the hub"
- `_zm_game_module::register_game_module` stores a `hub_start_func` per module, `zmeat.gsc` passes `meat_hub_start_func`
- So the versus modes were meant to be picked from inside a walk-around hub level

## Gametype list

`maps/mp/gametypes_zm/_gametypes.txt` has 13 entries, 4 shipped (zclassic, zstandard, zgrief, zcleansed).

| name | string | what is left |
| --- | --- | --- |
| zcontainment | Containment | preinit in zm_transit.gsc (survival_init) |
| zrace | Race | preinit, course names Farm/Town/Tunnel/Power, "Team CIA" / "Team CDC", "Get to the Finish Line!", "Zombies Left:" |
| zdeadpool | Deadpool / Dead Pool | preinit (encounter_init) |
| zmeat | Meat | zmeat.gsc, `_zm_game_module_meat*`, exe: `setteamhasmeat`, `hasmeat`, `sideHasMeat` |
| znml | No Man's Land | preinit (survival_init) |
| zturned | Turned | early name of zcleansed |
| zpitted | Pitted | preinit (encounter_init) |
| zmaxis, zrichtofen | none | `.txt` stubs + `zm/gamesettings_*.cfg`: 2 teams, scorelimit 7500, 10 min, roundlimit 3 |

- `zm/gamesettings_tdm.cfg` also exists in the zombies set

## War mode HUD from World at War

- Both exes still register the hudelem method `setwargamedata`
- Flag names `war_a` .. `war_e`, `war_sb`, strings `MENU_WAR_STATUS_TAKING` / `_CONTESTED`
- `mp_twar_spawn` is still in the spawn point classname list, `MPUI_TWAR` / `twar` in the presence gametype table

## Meat mode and the encounter courts in TranZit

The hub map `zm_meat` is not in retail. The Meat game itself is.

### How a mode starts from a hub

- `_zm_game_module::register_game_module( index, name, pre_init, post_init, pre_spawn, post_spawn, hub_start_func )`
- Only `zgrief` registers in retail (index 9)
- `zm_transit_ambush::ambushroundthink` still fetches `level.game_module_nml_index` and calls its `hub_start_func( "nml" )`, then notifies `game_mode_started`
- `ZOMBIE_EXIT_MEAT` ("go back to the hub") is not referenced by any shipped script

### Meat rules (maps/mp/gametypes_zm/zmeat.gsc)

- Two teams, court split by `_meat_team_1_volume` / `_meat_team_2_volume`; zombies path to the side holding the meat (`meat_poi_override_func`)
- Round limit 5, score limit 5, sides switch each round; a team with nobody alive loses the round
- Carrier: move speed 0.6, `holding_meat` clientfield, glow fx
- Throw, kick (sprint within 48 units without holding use) and spike
- Holding the meat for 15 s respawns a spectating teammate (`bring_back_teammate_progress`)
- Meat out of both volumes for 5 s is reset to the start point
- Rings (`_zm_game_module_meat_utility`): minigun, ammo and splitter; rings slide between `ring_sliders` and rotate; splitter spawns 3 meats, 1 real
- Intro: firework launches from `<loc>_meat_launch_spot`, then the meat drops from 600 units up
- Announcer keys: `meat_drop`, `meat_grab`, `meat_land`, `meat_hold`, `meat_revive_1..3`, `meat_ring_splitter` (alias ring_tripple), `meat_ring_minigun` (ring_death), `meat_ring_ammo`
- Engine side: `setteamhasmeat`, `hasmeat`, `sideHasMeat`, `alliesHasMeat` / `axisHasMeat`

### Placement data (so_zencounter_zm_transit.ff, addon map ents, 1217 entities)

- `game_mode_object` structs by location and `script_string`
  - town: 30 meat, 114 race
  - farm: 26 meat, 69 race, 3 both
  - tunnel: 27 meat, 41 race, 2 both
  - power: 15 race
- Meat: `meat_object` rings (`town_meat_minigun`, `town_meat_splitter`, `town_meat_ammo`, `farm_meat_ammo`) using `zombie_teleporter_mainframe_ring1/3`, per-team zombie spawn structs for town (`meat_2_*`), farm and tunnel
- Race: `race_town_area_1..5`, `race_farm_area_1..6`, `race_tunnel_area_1`, `race_power_area`, `power_race_lavapit_respawn`, `race_*_grief_*` target signs, bridge raise/lower targets, a Stamin-Up machine tagged `zrace_perks_farm`
- Props in the zone: `t6_wpn_zmb_meat_view/world`, `item_meat_zm`, 20 `viewmodel_zomb_meat_*` anims, `p6_zm_scoreboard_on`, `p6_zm_sign_neon_arrow_*`, `p6_zm_sign_race_target(_on)`, `p6_zm_barrier_pedestrian*`, meat and race fx
- Referenced by the entities but not in any zone listed: `p6_zm_sign_meat_01..06_on`, `p6_zm_sign_encounters_01..06`, `p6_anim_zm_finish_line`
- Not found in the zone's sound bank: the Meat and Race announcer aliases

## Unused TranZit locations in the main map entities (zm_transit.d3dbsp.ents)

Location scripts ship only for transit (station), farm and town. The entities are tagged for more.

### Cornfield

- Player spawns: `cornfield_nml_player_spawns` x4, `script_string` "zgrief_cornfield znml_cornfield"
- Turned respawns: `cornfield_standard_player_respawns` x35, "zcleansed_cornfield zturned_cornfield"
- `player_respawn_point` entries in `zone_amb_cornfield` for zgrief_cornfield and zcleansed/zturned_cornfield
- Perks tagged `znml_perks_cornfield`: `specialty_fastreload`, `specialty_armorvest`, `specialty_weapupgrade` (with `zombie_sign_please_wait` and a `perksacola` jingle struct)
- 8 `game_mode_object` structs, `script_noteworthy` cornfield, `script_string` "znml zcleansed zturned", all dead vehicle models
- Strings: `ZMUI_CORNFIELD`, `ZMUI_CORNFIELD_DESC`, `ZMUI_CLEANSED_CORNFIELD_1..4_PLAYER(S)_CAPS`
- Only `LB_ZM_GM_ZCLEANSED_DINER` and `_STREET` leaderboard assets exist

### Others

- Turned: `town_standard_player_respawns` x22 (zcleansed_town), `farm_standard_player_respawns` x24 (zcleansed_farm)
- No Man's Land on Town: `znml_town` on the town spawns, `znml_perks_town` on the town perk set
- Tunnel: `meat_tunnel_team_1/2_player_spawns` (zmeat_tunnel), `race_transit_tunnel_team1/2_spawn` (zrace_tunnel), `intermission` struct for tunnel
- Power: `race_transit_power_team1/2_spawn` (zrace_power), `intermission` struct for power, `menu_zm_map_transit_blit_power` image ships
- The other five zombies maps have no unused location tags of this kind
