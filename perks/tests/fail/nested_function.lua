-- expect: functions must be defined at the top level
perk = { name = "x" }
function on_give(player)
    function inner() end
end
