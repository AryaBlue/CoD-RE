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
| `icon` | HUD icon material. It must be loaded on the map; every stock perk icon on that map works, e.g. `specialty_juggernaut_zombies`. |
| `color` | `{ r, g, b }` from 0 to 1, tints the icon. |
| `machine` | Model for its machines (default: the map's Juggernog machine). |
| `bottle` | Drinking animation weapon (default `zombie_perk_bottle_jugg`). |
| `machines` | Where machines stand, per map: `{ zm_transit = { "x y z yaw" } }`. The tool's **Place machine here** fills this in. |
| `tick_every` | Seconds between `on_tick` calls (default 0.5). |

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
script in Plutonium's `scripts\zm` folder. Each custom perk becomes a real BO2 perk: it borrows an engine perk slot
Zombies never uses and registers with `_zm_perks`. So the perk limit, losing perks when you go down, and the tool's
give/take all work. HUD icons are drawn by the runtime in a row above the stock icons; set the dvar
`zmw_perk_hud "x y size gap"` to move them.

Up to 7 custom perks can be loaded at once: each needs an engine perk slot that Zombies never touches, and BO2
has 7 of those. Extra perks are skipped with a message.

Building `lua2gsc` itself: `cl /EHsc /std:c++17 lua2gsc.cpp`. Tests: `python tests/run_tests.py lua2gsc.exe gsc-tool.exe`.
