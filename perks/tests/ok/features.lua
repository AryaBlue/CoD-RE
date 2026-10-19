-- Exercises most of the dialect; must compile and pass gsc-tool.
perk = {
    name = "Feature Test",
    description = "not a real perk",
    cost = 100,
    machines = { zm_transit = { "100 200 300 90", "0 0 0 0" }, zm_nuked = { "1 2 3 4" } },
}

counts = {}
local names = { "a", "b", "c" }
local settings = { radius = 200, bonus = 50 }       -- a record: settings.radius
local weights = { ["walk"] = 1, ["run"] = 2 }        -- a map: weights["walk"], works with pairs()

function helper(x, y)
    if x == nil then
        return y or 10
    elseif x > y then
        return x - y
    else
        return -x
    end
end

function on_give(player)
    local total = 0
    for i = 1, 10 do total = total + i end
    for i = 10, 1, -2 do total = total - i end
    for i, n in ipairs(names) do
        player:print(i .. ": " .. n)
    end
    for k, v in pairs(weights) do
        total = total + 1
    end
    local list = {}
    table.insert(list, 5)
    table.insert(list, 6)
    table.remove(list, 1)
    player:print("size " .. #list .. " first " .. list[1])
    local r = settings.radius * 2 / 3 // 1 + 2 ^ 3 % 5
    local s = string.lower("ABC") .. string.sub("hello", 2, 3)
    local maybe = player.not_set and player.not_set.value or "default"
    local n = 0
    repeat
        n = n + 1
        local inner = n * 2
    until inner > 6
    while n > 0 do
        n = n - 1
        if n == 2 then break end
    end
    local key = "dyn"
    counts[key] = (counts[key] or 0) + 1
    local f = function(a) return a * 2 end
    total = total + f(2) + helper(3, 1) + math.floor(2.5) + abs(-3)
    thread(helper, 1, 2)
    if not player:is_downed() and (total > 0 or r < 1) then
        player:give_points(total)
    end
    local a, b = 1, 2
    a, b = b, a
    local nearby = zombies_near(player:origin() + vector(0, 0, 10), settings.radius)
    for _, z in ipairs(nearby) do
        z:damage(10, player)
    end
    wait(0.5)
    print(tostring(a) .. s .. maybe .. perk.name)
end
