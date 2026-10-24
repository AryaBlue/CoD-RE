"""Place BO3 stock gameplay (mystery box, PaP, wallbuys, perks, power switch) at BoD's own positions in zm_alcatraz_bodfull.map.
Idempotent: strips earlier "// entity bodplay" entries before appending."""
import json, math, re, sys, uuid

TOOLS = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
MAP = TOOLS + r"\map_source\zm\zm_alcatraz_bodfull.map"
GIANT_BOX = TOOLS + r"\map_source\_prefabs\zm\zm_giant\script\zm_giant_magicboxes.map"
ENTS = r"F:\ClaudeWork\bo4_recon\entities.json"
TOUR = r"F:\ClaudeWork\bo3\bod_port\geo\tools\tour_stops.json"
PF = "_prefabs/zm/zm_core/"
START_BOX = (7481, 10709)
PAP = ((8272, 8617, 392), 230)  # powerhouse; the street spot sits behind cell bars
POWER = ((-914, 6372, 113), 0)
WEAPONS = {"ar_accurate_t8": "ar_marksman", "smg_handling_t8": "smg_versatile", "shotgun_pump_t8": "shotgun_pump", "ar_stealth_t8": "ar_cqb",
           "shotgun_trenchgun_t8": "shotgun_pump", "ar_fastfire_t8": "ar_standard", "pistol_revolver_t8": "pistol_fullauto", "ar_modular_t8": "ar_standard",
           "smg_thompson_t8": "smg_standard", "smg_fastfire_t8": "smg_fastfire", "tr_powersemi_t8": "ar_marksman", "pistol_burst_t8": "pistol_burst",
           "tr_leveraction_t8": "ar_marksman", "smg_accurate_t8": "smg_versatile", "smg_standard_t8": "smg_standard", "tr_longburst_t8": "ar_longburst",
           "lmg_standard_t8": "ar_longburst"}
# perk -> the BoD wallbuy it sits beside (spread round the start area)
PERKS = [("vending_revive_struct", (3391, 9910)), ("vending_juggernaut_struct", (2109, 10491)), ("vending_doubletap_struct", (1919, 9017)),
         ("vending_sleight_struct", (328, 10569)), ("vending_marathon_struct", (-1071, 9365)), ("vending_deadshot_struct", (813, 9470)),
         ("vending_additionalprimaryweapon_struct", (3377, 9691))]
BGB = ((2800, 10032, 1336), 180)

def guid(): return "{" + str(uuid.uuid4()).upper() + "}"
def fmt(v): return " ".join(f"{a:g}" for a in v)

def ent(kv):
    return "{\nguid \"" + guid() + "\"\n" + "".join(f"\"{k}\" \"{v}\"\n" for k, v in kv.items()) + "}\n"

def prefab(name, origin, yaw):
    return ent({"classname": "misc_prefab", "angles": f"0 {yaw:g} 0", "model": PF + name + ".map", "origin": fmt(origin)})

def rot(v, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])

def box_template():
    t = open(GIANT_BOX, encoding="utf-8", errors="replace").read()
    for e in re.split(r"^// entity \d+\n", t, flags=re.M)[1:]:
        if '"zbarrier_zmcore_MagicBox"' in e: return dict(re.findall(r'^"([^"]+)" "([^"]*)"', e, re.M))

def main():
    E = json.load(open(ENTS))
    out, stops = [], []
    tpl = box_template()
    boxes = [e for e in E if e.get("classname") == "zbarrier_zm_esc_magicbox"]
    for i, b in enumerate(boxes):
        o, yaw = b["origin"], b["angles"][1]
        name = "start_chest" if math.dist(o[:2], START_BOX) < 50 else f"chest_{i}"
        out.append(ent({**tpl, "angles": f"0 {yaw:g} 0", "origin": fmt(o), "script_noteworthy": name + "_zbarrier"}))
        stops.append((name, o, yaw))
        out.append(ent({"classname": "script_struct", "angles": f"0 {yaw:g} 0", "origin": fmt(o), "script_noteworthy": name,
                        "targetname": "treasure_chest_use", "zombie_cost": "950"}))
    # PaP prefab's zbarrier sits at yaw 270, offset (2.5 5 -7.5)
    (p, pyaw) = PAP; y = pyaw - 270; d = rot((2.5, 5, -7.5), y)
    stops.append(("pap", p, pyaw))
    out.append(prefab("vending_weapon_upgrade_spawnable", (p[0] - d[0], p[1] - d[1], p[2] - d[2]), y % 360))
    walls = [e for e in E if e.get("targetname") == "weapon_upgrade"]
    for w in walls:
        bo3 = WEAPONS.get(w.get("zombie_weapon_upgrade"), "ar_longburst")
        o = w["origin"]
        stops.append(("wall_" + bo3, o, w["angles"][1]))
        out.append(prefab("spawnable_weapon_" + bo3, (o[0], o[1], o[2] - 56), w["angles"][1]))
    for name, near in PERKS:
        w = min(walls, key=lambda e: math.dist(e["origin"][:2], near))
        o, yaw = w["origin"], w["angles"][1]
        f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw))); t = (-f[1], f[0])
        po = (o[0] + t[0] * 90 + f[0] * 24, o[1] + t[1] * 90 + f[1] * 24, o[2] - 58)
        stops.append((name.replace("vending_", "").replace("_struct", ""), po, yaw))
        out.append(prefab(name, po, yaw))
    (g, gyaw) = BGB; f = (math.cos(math.radians(gyaw)), math.sin(math.radians(gyaw))); t = (-f[1], f[0])
    out.append(prefab("vending_bgb_struct", (g[0] + t[0] * 80, g[1] + t[1] * 80, g[2]), gyaw))
    stops.append(("power", *POWER))
    out.append(prefab("power_switch", *POWER))
    json.dump(stops, open(TOUR, "w"), indent=0)
    txt = open(MAP, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in txt[:2000] else "\n"
    txt = txt.replace("\r\n", "\n")
    parts = re.split(r"(?=^// entity )", txt, flags=re.M)
    txt = "".join(p for p in parts if not p.startswith("// entity bodplay")).rstrip("\n") + "\n"
    txt += "".join(f"// entity bodplay {i}\n{e}" for i, e in enumerate(out))
    open(MAP, "w", encoding="utf-8", errors="surrogateescape", newline="").write(txt.replace("\n", nl))
    print(f"boxes {len(boxes)}, wallbuys {len(walls)}, perks {len(PERKS)} + gobblegum, PaP 1, power switch 1")

if __name__ == "__main__":
    sys.exit(main())
