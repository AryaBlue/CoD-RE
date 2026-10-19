-- expect: goto and labels are not supported
perk = { name = "x" }
function on_give(player) goto done end
