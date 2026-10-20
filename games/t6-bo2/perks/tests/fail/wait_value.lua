-- expect: wait() can only be used as a statement
perk = { name = "x" }
function on_give(player) local x = wait(1) end
