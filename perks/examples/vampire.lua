-- Vampire Brew: every kill heals you a little; every 25th kill pays a bonus.
perk = {
    name = "Vampire Brew",
    description = "Kills heal you. Every 25th kill pays 500 points.",
    cost = 3000,
    icon = "specialty_juggernaut_zombies",
    color = { 0.9, 0.1, 0.15 },
}

local HEAL = 15
local BONUS_EVERY = 25

function on_give(player)
    player.vampire_kills = 0
    player:print("^1Vampire Brew^7: kills heal you")
end

function on_kill(player, zombie, weapon, means)
    player:set_health(min(player:health() + HEAL, player:max_health()))
    player.vampire_kills = player.vampire_kills + 1
    if player.vampire_kills % BONUS_EVERY == 0 then
        player:give_points(500)
        player:print("Vampire bonus: " .. player.vampire_kills .. " kills")
    end
end
