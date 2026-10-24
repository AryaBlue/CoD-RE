"""Dev HUD: the player's X Y Z and yaw top-left, so screenshots carry a position. Run after add_zones (it rewrites the GSC). --off removes it."""
import re, sys

GSC = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\usermaps\zm_alcatraz_bodfull\scripts\zm\zm_alcatraz_bodfull.gsc"

FN = """
// BODHUD BEGIN
function bod_pos_hud()
{
	level flag::wait_till( "initial_blackscreen_passed" );
	p = GetPlayers()[0];
	hud = [];
	for ( i = 0; i < 4; i++ )
	{
		h = NewClientHudElem( p );
		h.alignX = "left"; h.alignY = "top"; h.horzAlign = "left"; h.vertAlign = "top";
		h.x = 8 + i * 70; h.y = 4; h.fontscale = 1.4; h.alpha = 0.9; h.hidewheninmenu = true;
		hud[i] = h;
	}
	hud[3].color = ( 1, 0.8, 0.3 );
	while ( isdefined( p ) )
	{
		hud[0] SetValue( Int( p.origin[0] ) );
		hud[1] SetValue( Int( p.origin[1] ) );
		hud[2] SetValue( Int( p.origin[2] ) );
		hud[3] SetValue( Int( p.angles[1] ) );
		wait 0.2;
	}
}
// BODHUD END
"""

def main():
    g = open(GSC, encoding="utf-8").read()
    g = re.sub(r"\n// BODHUD BEGIN.*?// BODHUD END\n", "\n", g, flags=re.S)
    g = g.replace("\tlevel thread bod_pos_hud();\n", "")
    if "--off" not in sys.argv:
        g = g.replace("\tlevel.pathdist_type = PATHDIST_ORIGINAL;\n", "\tlevel.pathdist_type = PATHDIST_ORIGINAL;\n\tlevel thread bod_pos_hud();\n", 1)
        g = g.rstrip("\n") + "\n" + FN
    open(GSC, "w", encoding="utf-8").write(g)
    print("pos hud", "off" if "--off" in sys.argv else "on")

if __name__ == "__main__":
    main()
