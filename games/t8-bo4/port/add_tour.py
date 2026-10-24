"""Test-only GSC tour: god mode + teleport to each placed gameplay item (two views each) with an on-screen label. --off removes it."""
import json, math, re, sys

GSC = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\usermaps\zm_alcatraz_bodfull\scripts\zm\zm_alcatraz_bodfull.gsc"
TOUR = r"F:\ClaudeWork\bo3\bod_port\geo\tools\tour_stops.json"
HOLD = 4

def main():
    g = open(GSC, encoding="utf-8").read()
    g = re.sub(r"\n// BODTOUR BEGIN.*?// BODTOUR END\n", "\n", g, flags=re.S)
    g = g.replace("\tlevel thread bod_tour();\n", "")
    if "--off" in sys.argv:
        open(GSC, "w", encoding="utf-8").write(g); print("tour removed"); return
    lines = []
    for i, (name, o, yaw) in enumerate(json.load(open(TOUR))):
        f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        for s, tag in ((1, "front"), (-1, "back")):
            pos = (o[0] + f[0] * 110 * s, o[1] + f[1] * 110 * s, o[2] - 20)
            lines.append(f'\tbod_tour_stop( p, "{i:02d} {name} {tag}", ({pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f}), ({o[0]:.0f}, {o[1]:.0f}, {o[2] + 40:.0f}) );\n')
    fn = ("\n// BODTOUR BEGIN\nfunction bod_tour()\n{\n\tlevel flag::wait_till( \"initial_blackscreen_passed\" );\n\tp = GetPlayers()[0];\n"
          "\tp EnableInvulnerability();\n\tp.ignoreme = true;\n\tp notify( \"stop_player_out_of_playable_area_monitor\" );\n\twait 3;\n" + "".join(lines) + "\tIPrintLnBold( \"TOUR DONE\" );\n}\n\n"
          "function bod_tour_stop( p, label, pos, look )\n{\n\tp SetOrigin( pos );\n\tp SetPlayerAngles( VectorToAngles( look - ( pos + ( 0, 0, 60 ) ) ) );\n"
          "\twait 0.5;\n\tz = zm_zonemgr::get_zone_from_position( p.origin + ( 0, 0, 30 ), true );\n\tif ( !isdefined( z ) ) z = \"NONE\";\n"
          f"\tIPrintLnBold( label + \" | \" + z + \" ok=\" + p zm::in_enabled_playable_area() );\n\twait {HOLD};\n}}\n// BODTOUR END\n")
    g = g.replace("\tlevel.pathdist_type = PATHDIST_ORIGINAL;\n", "\tlevel.pathdist_type = PATHDIST_ORIGINAL;\n\tlevel thread bod_tour();\n", 1)
    open(GSC, "w", encoding="utf-8").write(g.rstrip("\n") + "\n" + fn)
    print(f"tour on: {len(lines)} views, {len(lines) * HOLD}s")

if __name__ == "__main__":
    main()
