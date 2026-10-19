-- Scavenger's Luck: melee hits do double damage, and each new round has a chance to pay out.
perk = {
    name = "Scavenger's Luck",
    cost = 1500,
    icon = "specialty_tombstone_zombies",
    color = { 0.2, 0.8, 0.3 },
}

local payouts = { 100, 250, 500, 1000 }

function on_hit(player, zombie, damage, means, weapon)
    if means == "MOD_MELEE" then
        return damage * 2
    end
    return damage
end

function on_round(player, round)
    if random(1, 100) <= 30 then
        local amount = payouts[random(#payouts)]
        if round >= 20 then
            amount = amount * 2
        end
        player:give_points(amount)
        player:print("Scavenger's Luck: +" .. amount .. " points")
    end
end
