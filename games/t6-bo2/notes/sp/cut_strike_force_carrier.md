# Cut campaign content left in retail BO2 - Strike Force Carrier, a sixth Strike Force mission

Found in t6sp.exe strings and the English frontend / common string zones (dumped with OpenAssetTools Unlinker).
No game files are stored here, only names and where they sit.

## Evidence

- t6sp.exe presence table lists six Strike Force maps
  - `so_rts_mp_socotra`, `so_rts_mp_overflow`, `so_rts_mp_drone`, `so_rts_mp_dockside`, `so_rts_mp_carrier`, `so_rts_afghanistan`
  - `PRESENCE_SO_CARRIER` = "Carrier"
- No `so_rts_mp_carrier.ff` in zone/all (the MP map `mp_carrier.ff` is unrelated)
- t6sp.exe keeps the string `SP_RTS_CARRIER` next to the per-level challenge / intel stat code
- Strings
  - `MENU_LEVEL_CARRIER_RTS_CAPS` "STRIKE FORCE: CARRIER"
  - `FRONTEND_SF_CARRIER` "Carrier"
  - `CH_SP_WAR_CARRIER_TACTICAL` "Complete the mission in tactical view only"

## Briefing

Subtitles `FRONTEND_VOX_VOX_SFF_1_02_009` to `_015` describe the mission. They sit in the same briefing block as the FOB Spectre lines (`_011`, `_019`, `_020`).

- Enemy destroyers carrying anti-satellite weapons are in the Arabian Sea
- The team HALO jumps onto the carrier
- Primary objective is to disable the carrier: take over its ASDs from the defence control area, then destroy the engines and power systems
- Then fly the enemy VTOLs off the flight deck and destroy the fleet

Not checked: whether the voice audio for these lines is in the sound banks.
