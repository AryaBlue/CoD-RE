# ZM Workshop Lua perks

Write a Black Ops II Zombies perk in Lua. ZM Workshop compiles it to GSC (`lua2gsc`) and Plutonium runs it.
A perk is one `.lua` file; its file name is its id (`vampire.lua` → `vampire`).

```lua
perk = {
    name = "Vampire Brew",
    cost = 3000,
    icon = "specialty_juggernaut_zombies",
    color = { 0.9, 0.1, 0.15 },
}

local HEAL = 15

function on_kill(player, zombie, weapon, means)
    player:set_health(min(player:health() + HEAL, player:max_health()))
end
```

The `examples/` folder has complete perks. To see how Treyarch wrote a stock perk, use **Export stock perk** in
ZM Workshop's Perks tab: it decompiles the script from your own game files.

## The perk table

| Field | Meaning |
| --- | --- |
| `name` | Shown in the machine prompt and the tool. |
| `description` | Shown in the tool. |
| `cost` | Machine price (default 2500). |
| `hint` | Machine prompt; `&&1` is the cost. The default is `Hold [Use] for <name> [Cost: &&1]`. |
| `icon` | HUD icon material: your own icon (see below), or a stock perk icon loaded on the map, e.g. `specialty_juggernaut_zombies`. |
| `color` | `{ r, g, b }` from 0 to 1, tints the icon. Use `{ 1, 1, 1 }` for an icon with its own colours. |
| `machine` | Model for its machines (default: the map's Juggernog machine). |
| `bottle` | Drinking animation weapon (default `zombie_perk_bottle_jugg`). |
| `machines` | Where machines stand, per map: `{ zm_transit = { "x y z yaw" } }`. The tool's **Place machine here** fills this in. |
| `specialties` | Engine perks switched on while the perk is owned, e.g. `{ "specialty_fastreload", "specialty_fastads" }`. One the player also has from a stock machine is left alone when this perk goes. |
| `tick_every` | Seconds between `on_tick` calls (default 0.5). |

## Your own icon

Put a PNG in `perks\icons\` (square, transparent background; it is scaled to 64x64). `static_shock.png` becomes the
material `zmw_icon_static_shock`, so the perk says `icon = "zmw_icon_static_shock"`. ZM Workshop builds the icons
into the ZM Workshop mod (`mod.ff` + `zm_workshop_icons.ipak`) after **Build + install**; click **Load mod** on Home
so the game loads them. Without the mod loaded the icon is missing.

(How: each PNG becomes an uncompressed IWI v27 image - 64-byte header `IWi` 27, format 1 = RGBA, flags 2 = no mips,
width/height/depth as uint16, `fileSizeForPicmip[0]` at byte 32 - and a copy of a stock perk icon's material. OAT
writes T6 images only as streamed images, so they need `>ipak,<name>` in the zone and the .ipak next to the .ff.)

## Events

Define any of these functions. Each receives the player who has the perk.

| Function | When |
| --- | --- |
| `on_give(player)` | The perk is drunk or given. |
| `on_take(player)` | The perk is lost (down, death, taken). |
| `on_kill(player, zombie, weapon, means)` | The player kills a zombie. |
| `on_hit(player, zombie, damage, means, weapon)` | The player damages a zombie. Return the new damage. |
| `on_damaged(player, attacker, damage, means, weapon)` | The player takes damage. Return the new damage, or `nil` to leave it. |
| `on_downed(player)` | The player goes down. |
| `on_revived(player)` | The player is revived. |
| `on_round(player, round)` | A new round starts. |
| `on_tick(player)` | Every `tick_every` seconds while the player has the perk. |

`means` is the engine's damage type: `"MOD_MELEE"`, `"MOD_PISTOL_BULLET"`, `"MOD_RIFLE_BULLET"`, `"MOD_GRENADE_SPLASH"`,
`"MOD_PROJECTILE_SPLASH"`, `"MOD_EXPLOSIVE"`, `"MOD_BURNED"`, ...

## Functions

| Function | Returns / does |
| --- | --- |
| `wait(seconds)` | Pauses this handler (statement only). |
| `thread(f, ...)` | Runs one of your functions alongside (statement only). |
| `print(text)` | Message to everyone. |
| `random(n)` / `random(a, b)` | Whole number 1..n or a..b. |
| `random_float(a, b)` | Number between a and b. |
| `time()` | Seconds since the map started. |
| `round_number()` | Current round. |
| `players()` | List of players. |
| `zombies()` | List of living zombies. |
| `zombies_near(position, radius)` | Zombies within `radius` of `position`. |
| `explode(position, radius, max_damage, min_damage, player)` | Damages zombies around `position` (credited to `player`) and shakes the screen. |
| `play_sound(alias, position)` | Plays a sound at a position. |
| `vector(x, y, z)` | A position. Positions can be added, subtracted and multiplied by numbers. |
| `distance(a, b)` | Distance between two positions. |
| `tostring(x)`, `tonumber(s)` | Conversions. |
| `abs`, `floor`, `ceil`, `sqrt`, `min(a, b)`, `max(a, b)` | Maths (also as `math.floor`, ...). |
| `string.lower(s)`, `string.sub(s, i, j)`, `string.find(s, part)` | `find` returns true or false. |
| `table.insert(t, v)`, `table.remove(t, i)`, `table.contains(t, v)` | Lists. |

## Player and zombie methods

Call methods with `:`, e.g. `player:give_points(500)`.

| Method | Works on |
| --- | --- |
| `name()`, `points()`, `give_points(n)`, `take_points(n)` | Players |
| `health()`, `set_health(n)`, `max_health()`, `set_max_health(n)`, `heal()` | Both |
| `origin()`, `forward()`, `distance_to(other or position)` | Both |
| `is_alive()` | Both |
| `is_downed()`, `revive()` | Players |
| `current_weapon()`, `give_weapon(name)`, `take_weapon(name)`, `refill_ammo()` | Players |
| `set_speed(scale)` | Players (1 is normal) |
| `print(text)`, `print_bold(text)`, `play_sound(alias)` | Players |
| `is_sprinting()`, `is_on_ground()`, `stance()` | Players |
| `set_ignored(on)` | Players: zombies ignore them while on |
| `damage(n, attacker)`, `kill(attacker)` | Both |
| `has_perk(id)`, `give_perk(id)`, `take_perk(id)` | Players; `id` is a custom perk id or a stock specialty such as `"specialty_armorvest"` |
| `shellshock(kind, seconds)` | Players |
| `set_engine_perk(specialty, on)` | Players: a raw engine perk on or off, without a stock perk's HUD or rules |

You can store your own values on players and zombies: `player.vampire_kills = 0`.
`perk` inside a function is this perk's table (`perk.name`, `perk.cost`).

## The Lua you can use

Locals, functions, `if/elseif/else`, `while`, `repeat/until`, numeric `for`, `for ... in ipairs(t)` and `pairs(t)`,
`break`, `return`, string joining with `..`, `and`/`or`/`not`, `#list`, and anonymous functions that don't use the
enclosing function's locals.

GSC can't do these, so they are compile errors with a line number:

- A function using a local of the function around it (a closure). Pass the value as an argument or make it a perk global.
- Returning more than one value, `...` arguments, `goto`, metatables, coroutines.
- Functions defined inside other functions. Define them at the top level of the file.
- Code at the top level other than definitions. Put it in `on_give` and the other handlers.

Differences from standard Lua:

- `0` counts as false, as in GSC.
- Top-level variables (`local` or not) are perk globals: every function sees them, and they are shared by all players.
  Keep per-player state on the player (`player.x`).
- Tables come in two kinds. `{ a = 1 }` is a record: read it with `t.a`. `{}`, `{ 1, 2 }` and `{ ["a"] = 1 }` are
  lists and maps: read them with `t[1]` or `t["a"]`. `pairs()` works on lists and maps.
- Lists start at 1, as in Lua.

## How it runs

`runtime/zm_workshop_perks.gsc` is the support library. ZM Workshop bundles it with every compiled perk into one
script in Plutonium's `scripts\zm` folder. Custom perks are tracked by the runtime itself rather than with engine
perk slots, so there is no limit on how many you have. They still count towards the map's perk limit, are lost
when you go down (Who's Who keeps them, as it does stock perks), and work with the tool's give/take. Use
`specialties` for engine effects. HUD icons are drawn by the runtime in rows above the stock icons; set the dvar
`zmw_perk_hud "x y size gap per_row"` to move them.

### Loading into a running match

New compiled GSC can't be added to a match that's already going, so **Build + install** does two things: it builds
the script for the next map start, and it sends every perk that changed since the last build straight into the
running match as bytecode (`lua2gsc --live`), which the runtime interprets. The log says when a perk is live. Players
who already have the perk get the old version's `on_take` and then the new version's `on_give`, so start-up state
is set again. At the next map start the compiled copy takes over.

Limits of a live load:

- A brand-new icon or machine model shows from the next map start (the engine only loads art while the map loads);
  until then the perk uses the Juggernog icon and machine.
- Fields you invent on players and zombies (`player.x`) are kept separately for a live perk, so they start empty.
- One push is limited to about 15 KB of bytecode (several typical perks). Bigger changes apply from the next map
  start.
- Live perks are interpreted, so they are slower than compiled ones, which is fine for trying changes.

Building `lua2gsc` itself: `cl /EHsc /std:c++17 lua2gsc.cpp`. Tests: `python tests/run_tests.py lua2gsc.exe gsc-tool.exe`.
`lua2gsc --live perk.lua` prints a perk's bytecode; `tests/livevm.cpp` runs it the way the runtime does and
`tests/live/lua` runs the same perk in real Lua (LÖVE), and the two outputs must match.
