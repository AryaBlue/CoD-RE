-- live bytecode test: run by tests/livevm.exe and by real Lua (tests/live/lua/main.lua); the printed lines must match.
-- avoids what the dialect does differently on purpose (0 is false, tables are copied on assignment)
perk = {
    name = "Semantics",
    cost = 1234,
    color = { 1, 0.5, 0.25 },
    specialties = { "specialty_fastreload" },
    machines = { zm_transit = { "1 2 3 90" } },
}

counts = {}
local LIMIT = 3
local cfg = { radius = 200, inner = { level = 1, tags = { "x", "y" } } }

function fact(n)
    if n <= 1 then return 1 end
    return n * fact(n - 1)
end

function classify(x)
    if x < 0 then
        return "neg"
    elseif x < 10 then
        return "small"
    else
        return "big"
    end
end

function bump(key)
    counts[key] = (counts[key] or 0) + 1
    return counts[key]
end

function on_give(player)
    print("give " .. player:name() .. " " .. perk.name .. " " .. perk.cost)
    local total = 0
    for i = 1, 10 do total = total + i end
    for i = 10, 1, -3 do total = total - i end
    print("total " .. total)
    print("fact " .. fact(6) .. " " .. classify(-4) .. " " .. classify(4) .. " " .. classify(40))
    local list = {}
    table.insert(list, "a")
    table.insert(list, "b")
    table.insert(list, "c")
    table.remove(list, 2)
    print("list " .. #list .. " " .. list[1] .. list[2])
    for i, v in ipairs(list) do print("ipairs " .. i .. "=" .. v) end
    local sum = 0
    local map = { ["p"] = 3, ["q"] = 4 }
    for k, v in pairs(map) do sum = sum + v end
    print("pairs " .. sum)
    cfg.inner.level = cfg.inner.level + 5
    cfg.inner.tags[2] = "z"
    table.insert(cfg.inner.tags, "w")
    print("nested " .. cfg.inner.level .. " " .. cfg.inner.tags[1] .. cfg.inner.tags[2] .. cfg.inner.tags[3] .. " " .. #cfg.inner.tags)
    print("bump " .. bump("k") .. bump("k") .. bump("j"))
    player.hits = {}
    table.insert(player.hits, 7)
    table.insert(player.hits, 8)
    player.hits[1] = player.hits[1] + 100
    print("entity " .. #player.hits .. " " .. player.hits[1] .. " " .. player.hits[2])
    local n = 0
    while true do
        n = n + 1
        if n >= LIMIT then break end
    end
    local m = 0
    repeat
        m = m + 2
        local done = m > 5
    until done
    print("loops " .. n .. " " .. m)
    local a, b = 1, 2
    a, b = b, a
    local orv = nil or "fallback"
    local andv = "first" and "second"
    print("swap " .. a .. b .. " " .. orv .. " " .. andv .. " " .. ((not nil) and "T" or "F") .. ((5 == 6) and "T" or "F"))
    local double = function(x) return x * 2 end
    print("fn " .. double(21) .. " " .. 2 ^ 5 .. " " .. 17 % 5 .. " " .. 7 / 2)
    local s = string.lower("HeLLo") .. string.sub("abcdef", 2, 4)
    print("str " .. s .. " " .. (string.find("needle", "eed") and "found" or "missing") .. " " .. math.floor(2.7) .. min(3, 9) .. max(3, 9))
    player:give_points(250)
    print("points " .. player:points())
    for _, z in ipairs(zombies_near(player:origin(), cfg.radius)) do
        z:damage(30, player)
        print("zombie " .. z:health())
    end
    thread(report, player, "threaded")
    if player.never ~= nil then print("wrong") else print("nil field ok") end
end

function report(player, msg)
    player:print(msg .. " " .. round_number())
end

function on_hit(player, zombie, damage, means, weapon)
    if means == "MOD_MELEE" then return damage * 3 end
    return damage + 1
end
