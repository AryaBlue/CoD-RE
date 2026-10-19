-- Adrenaline: each kill gives a short burst of speed; a streak of 10 quick kills refills your ammo.
perk = {
    name = "Adrenaline",
    cost = 2500,
    icon = "specialty_marathon_zombies",
    color = { 1, 0.85, 0.1 },
    tick_every = 1,
}

local BOOST = 1.25
local STREAK = 10
local STREAK_WINDOW = 4  -- seconds between kills before the streak resets

function on_give(player)
    player.adrenaline_streak = 0
    player.adrenaline_last = 0
end

function on_take(player)
    player:set_speed(1)
end

function on_kill(player, zombie, weapon, means)
    local now = time()
    if now - player.adrenaline_last > STREAK_WINDOW then
        player.adrenaline_streak = 0
    end
    player.adrenaline_last = now
    player.adrenaline_streak = player.adrenaline_streak + 1
    player.adrenaline_until = now + 2
    player:set_speed(BOOST)
    if player.adrenaline_streak >= STREAK then
        player.adrenaline_streak = 0
        player:refill_ammo()
        player:print_bold("^3Adrenaline!^7 Ammo refilled")
    end
end

-- once a second: drop back to normal speed when the burst is over
function on_tick(player)
    if player.adrenaline_until ~= nil and time() > player.adrenaline_until then
        player.adrenaline_until = nil
        player:set_speed(1)
    end
end
