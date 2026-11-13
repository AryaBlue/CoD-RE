# Cut zombies content left in retail BO2 - BO1 maps, the hub test map and unused gametypes

Found by reading strings in t6zm.exe / t6mp.exe and dumping the retail zones with OpenAssetTools (Unlinker).
No game files are stored here, only names and where they sit.

## Nacht, Der Riese and Moon are registered as BO2 maps

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
