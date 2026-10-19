-- expect: can't capture locals
perk = { name = "x" }
function on_give(player)
    local n = 5
    local f = function() return n end
end
