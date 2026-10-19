-- expect: unknown method ':fly'
perk = { name = "x" }
function on_give(player) player:fly() end
