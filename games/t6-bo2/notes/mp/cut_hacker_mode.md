# Cut multiplayer gametypes left in retail BO2 - Hacker mode and the unused settings files

Found by listing and dumping `patch_mp.ff` / `common_mp.ff` and the English string zones with OpenAssetTools (Unlinker), plus strings in t6mp.exe.
No game files are stored here, only names and where they sit.

## Hacker (`hack`)

- Free-for-all where every player has an A.G.R. (internal name talon) and scores by hacking other players' drones
- `MENU_HACKER_DESC` "Hack enemy A.G.Rs for massive score!", `OBJECTIVES_HACKER_HINT` "HACK DRONES BEFORE TIME EXPIRES"
- `mp/gamesettings_hack.cfg` (patch_mp.ff) keeps its dev comments
  - teamCount 1, timelimit 5, class selection and scorestreaks off
  - `crateCaptureTime 0.5` = hack time
  - `flagRespawnTime 4` = seconds a drone stays stunned
  - `idleFlagResetTime 2` = starting EMPs, `destroyTime` = EMPs on respawn
  - `hotPotato` = if 1, unhacked talons are destroyed
  - `forceRadar 1`, `enemyCarrierVisible 2` (show mine and enemy drones)
- Medals with icons in the zone: `hud_medals_hack_hackathon`, `hud_medals_hack_denied`, `hud_medals_hack_heist`
  - Hackathon - hack 3 A.G.R.s in one life
  - Denied - kill an enemy hacking your A.G.R.
  - Heist - kill a hacker then hack the same A.G.R.
- `scavenger_item_hack_mp` - a Scavenger bag that refills EMP grenades
- `maps/mp/bots/_bot_hack.gsc` ships: bots path to a talon, throw `emp_grenade_mp`, crouch and hold use for `drone_hack_time`
  - yet `MENU_BOTS_NOT_SUPPORTED_HACK` says "Bots are not supported in Hacker."
- `_ai_tank.gsc` still checks for the mode and has the notifies `ai_tank_hack_spawned` / `ai_tank_hack_rebooting`
- Score events `SCORE_HACKER_DRONE_HACKED`, `SCORE_HACKER_DRONE_KILL`, custom rule `MPUI_RULES_DRONE_HACK_TIME_CAPS`
- t6mp.exe and t6zm.exe list `MPUI_HACK` / `hack` in the presence gametype table
- Missing: the main `maps/mp/gametypes/hack.gsc`

## Other unshipped gametypes with files or strings

| name | string | what is left |
| --- | --- | --- |
| pur | Purgatory | settings (queued respawn, 3 rounds), "Kills until release from purgatory:", "You are next to escape purgatory!" |
| hun | Hunted | settings (no perks, no class select, crateCaptureTime 2), "Retrieve Care Package to upgrade your loadout" |
| nvc | Assassins vs. Cowboys | .txt stub, attacker/defender objective text (fast side with radar vs slow side with heavy weapons) |
| tag | Freeze Tag | settings, objective text |
| res | Resistance | settings, "Teams alternate in attacking and defending flags" |
| wdom | World Domination | .txt stub |
| cp | Cash Pot | .txt stub |
| bwars | none | settings (captureTime 3, scorelimit 200) |
| tdef | Team Defender | settings, objective text |
| sab | Sabotage | settings, `mp_sab_spawn` classname |
| twar | War | see the zombies cut content note |
