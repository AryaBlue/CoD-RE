-- real-Lua side of the live bytecode test: lovec <this folder> <perk.lua>
-- the mock world must match tests/livevm.cpp exactly
local out = io.stdout

local function ent(name, hp)
    local e = { _name = name, _hp = hp, _max = hp, _points = 500 }
    function e:name() return self._name end
    function e:points() return self._points end
    function e:give_points(n) self._points = self._points + n end
    function e:health() return self._hp end
    function e:origin() return { 0, 0, 0 } end
    function e:damage(n, by) self._hp = self._hp - n end
    function e:print(m) out:write("[" .. self._name .. "] " .. m .. "\n") end
    return e
end

function love.load(args)
    local path = args[1]
    local f = assert(io.open(path, "rb")); local src = f:read("*a"); f:close()
    local host, z1, z2 = ent("Host", 100), ent("z1", 150), ent("z2", 150)
    local env = {
        print = function(m) out:write("PRINT " .. m .. "\n") end,
        tostring = tostring, ipairs = ipairs, pairs = pairs, math = math, string = string, table = table,
        min = math.min, max = math.max, round_number = function() return 5 end,
        zombies_near = function() return { z1, z2 } end,
        thread = function(fn, ...) fn(...) end, wait = function() end,
    }
    local chunk = assert(loadstring(src, "perk"))
    setfenv(chunk, env)
    chunk()
    local p = env.perk
    out:write(("perk name=%s cost=%s color=%s,%s,%s spec=%s machines=%s\n"):format(p.name, p.cost, p.color[1], p.color[2], p.color[3],
        p.specialties[1], p.machines.zm_transit[1]))
    env.on_give(host)
    out:write("hit " .. env.on_hit(host, z1, 10, "MOD_MELEE") .. " " .. env.on_hit(host, z1, 10, "MOD_PISTOL_BULLET") .. "\n")
    love.event.quit()
end
