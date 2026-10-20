-- expect: unknown function 'teleport'
perk = { name = "x" }
function on_give(player) teleport(player) end
