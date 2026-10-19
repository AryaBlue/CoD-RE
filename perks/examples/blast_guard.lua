-- Blast Guard: your own explosives can't hurt you, and going down sets off a blast around you.
perk = {
    name = "Blast Guard",
    cost = 2000,
    icon = "specialty_divetonuke_zombies",
    color = { 0.6, 0.2, 0.9 },
}

local SPLASH = { "MOD_GRENADE", "MOD_GRENADE_SPLASH", "MOD_PROJECTILE", "MOD_PROJECTILE_SPLASH", "MOD_EXPLOSIVE" }

function is_splash(means)
    for _, m in ipairs(SPLASH) do
        if m == means then
            return true
        end
    end
    return false
end

function on_damaged(player, attacker, damage, means, weapon)
    if attacker == player and is_splash(means) then
        return 0
    end
    return nil  -- nil keeps the damage as it is
end

function on_downed(player)
    explode(player:origin(), 250, 1500, 300, player)
end
