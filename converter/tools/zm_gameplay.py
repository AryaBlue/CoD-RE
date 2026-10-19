"""BO1 zombies gameplay data -> BO2 conventions.

- convert_ents: rewrites a BO1 map's entity string so BO2's _zm framework finds its zones and spawns.
  BO1 and BO2 share info_volume "player_volume" zones and "initial_spawn_points"; BO1 uses actor spawners placed
  in the map plus "<group>_rise" / "<group>_dog" structs, BO2 uses structs named after the zone's target group
  (script_noteworthy spawn_location / riser_location / dog_location) and a few global actor spawners.
- bo1_zone_setup: pulls the zone list and adjacency function out of the BO1 level script (same API in BO2).
- patch_donor_scripts: rewrites the decompiled donor (stock BO2) level scripts for the converted map.
"""
import re

ENT_RE = re.compile(r'\{([^{}]*)\}')
KV_RE = re.compile(r'"([^"]*)"\s+"([^"]*)"')


def parse_ents(text):
    return [KV_RE.findall(block) for block in ENT_RE.findall(text)]


def write_ents(ents):
    out = []
    for kvs in ents:
        out.append("{")
        out += [f'"{k}" "{v}"' for k, v in kvs]
        out.append("}")
    return "\n".join(out) + "\n"


def get(kvs, key, default=None):
    for k, v in kvs:
        if k == key:
            return v
    return default


def setkv(kvs, key, value):
    kvs = [(k, v) for k, v in kvs if k != key]
    kvs.append((key, value))
    return kvs


def struct(targetname, origin, angles, **extra):
    kvs = [("classname", "script_struct"), ("targetname", targetname), ("origin", origin), ("angles", angles or "0 0 0")]
    return kvs + list(extra.items())


def convert_ents(bo1_text, donor_text):
    """Returns (bo2 entity text, report lines)."""
    ents = parse_ents(bo1_text)
    donor = parse_ents(donor_text)
    out, report = [], []
    spawn_groups = {}
    report_counts = {}

    for kvs in ents:
        cls = get(kvs, "classname", "")
        name = get(kvs, "targetname", "")
        note = get(kvs, "script_noteworthy", "")

        if cls.startswith("actor_"):
            # BO1 zombie spawners stand where zombies enter; BO2 spawns from structs in the zone's target group
            if note == "zombie_spawner" and name:
                out.append(struct(name, get(kvs, "origin"), get(kvs, "angles"), script_noteworthy="spawn_location"))
                spawn_groups[name] = spawn_groups.get(name, 0) + 1
            continue
        if cls.startswith("node_"):
            continue  # path data is not converted yet

        if cls == "script_struct" and name == "exterior_goal":
            # BO2 windows are zbarrier entities; BO2's blocker code spins on a BO1 board window (no zbarrier),
            # so windows stay out until boards are converted to zbarriers
            windows = report_counts.setdefault("windows", 0)
            report_counts["windows"] = windows + 1
            continue
        if name == "zombie_trap":
            # BO2's trap code registers screen-overlay client fields the donor's client scripts don't have
            # (EXE_CLIENT_FIELD_MISMATCH); traps come back with converted client scripts
            report_counts["traps"] = report_counts.get("traps", 0) + 1
            continue
        if cls == "script_struct" and name.endswith("_rise"):
            group = name[: -len("_rise")]
            out.append(struct(group, get(kvs, "origin"), get(kvs, "angles"), script_noteworthy="riser_location"))
            spawn_groups[group] = spawn_groups.get(group, 0) + 1
            continue
        if cls == "script_struct" and name.endswith("_dog"):
            group = name[: -len("_dog")]
            out.append(struct(group, get(kvs, "origin"), get(kvs, "angles"), script_noteworthy="dog_location"))
            continue
        if cls == "script_struct" and name == "initial_spawn_points" and not note:
            kvs = setkv(kvs, "script_noteworthy", "initial_spawn")

        out.append(kvs)

    zones = {}
    for kvs in out:
        if get(kvs, "classname") == "info_volume" and get(kvs, "script_noteworthy") == "player_volume":
            zones.setdefault(get(kvs, "targetname"), get(kvs, "target"))

    # respawn points: BO2 asserts each zone can respawn players; use the start spawns until better ones exist
    for zone in zones:
        out.append([("classname", "script_struct"), ("targetname", "player_respawn_point"), ("script_noteworthy", zone),
                    ("target", "initial_spawn_points"), ("origin", "0 0 0")])

    # the donor's global actor spawners (zombie / dog aitypes that exist in the donor zones)
    actors = [kvs for kvs in donor if get(kvs, "classname", "").startswith("actor_")]
    out += actors

    for zone, target in sorted(zones.items()):
        count = spawn_groups.get(target, 0)
        report.append(f"zone {zone}: {count} spawn locations ({target})" + ("" if count else "  <-- none"))
    report.append(f"{len(actors)} donor actor spawners, {len(zones)} zones, {report_counts.get('windows', 0)} windows and {report_counts.get('traps', 0)} traps left out")
    return write_ents(out), report


def bo1_zone_setup(bo1_gsc):
    """(init zone list, name of the zone init function, its body) from a BO1 level script."""
    init_zones = re.findall(r'init_zones\s*\[\s*\d+\s*\]\s*=\s*"([^"]+)"', bo1_gsc)
    func = re.search(r'level\.zone_manager_init_func\s*=\s*::\s*(\w+)', bo1_gsc)
    body = ""
    if func:
        m = re.search(r'^' + func.group(1) + r'\s*\(\s*\)\s*\{', bo1_gsc, re.M)
        if m:
            depth, i = 0, m.end() - 1
            for j in range(i, len(bo1_gsc)):
                depth += {"{": 1, "}": -1}.get(bo1_gsc[j], 0)
                if depth == 0:
                    body = bo1_gsc[i + 1 : j]
                    break
    return init_zones, body


# donor (zm_nuked) set pieces that need Nuketown's own entities
NUKED_REMOVE = [
    r"level thread zombie_eye_glow_change\(\);", r"level thread switch_announcer_to_richtofen\(\);",
    r"level thread moon_transmission_vo\(\);", r"level thread marlton_vo_inside_bunker\(\);",
    r"level thread bus_random_horn\(\);", r"level thread inermission_rocket_init\(\);",
    r"level thread nuked_mannequin_init\(\);", r"level thread fake_lighting_cleanup\(\);",
    r"level thread bus_taser_blocker\(\);", r"level thread nuked_doomsday_clock_think\(\);",
    r"level thread nuked_population_sign_think\(\);", r"level thread maps\\mp\\zm_nuked_perks::perks_from_the_sky\(\);",
    r"level thread perks_behind_door\(\);", r"level thread sndmusiceastereggs\(\);",
    r"level thread nuked_update_traversals\(\);", r"level thread nuked_collision_patch\(\);",
    r"maps\\mp\\zm_nuked_perks::init_nuked_perks\(\);", r"level\.custom_intermission = ::nuked_standard_intermission;",
    r"nuked_treasure_chest_init\(\);",
]
NOOP = "level.bo1port_noop = 1;"  # keeps single-statement if bodies valid


def patch_donor_scripts(level_src, standard_src, init_zones, zone_body, zombies=False):
    """Patched (level script, standard gamemode script) sources for the zm_nuked donor.
    zombies=False holds round 1 with no spawning (AI path nodes are not converted yet; pathing on a map
    without nodes crashes the engine)."""
    removed = 0
    if not zombies:
        hook = "    level.zombiemode = 1;\n"
        if hook not in level_src:
            raise RuntimeError("level.zombiemode not found in donor level script")
        level_src = level_src.replace(hook, hook + "    level.round_spawn_func = ::bo1port_no_spawning;\n"
                                      "    level.round_wait_func = ::bo1port_hold_round;\n", 1)
        level_src += ("\nbo1port_no_spawning()\n{\n}\n\n"
                      "bo1port_hold_round()\n{\n    level waittill( \"forever\" );\n}\n")
    for pattern in NUKED_REMOVE:
        level_src, n1 = re.subn(pattern, NOOP, level_src)
        standard_src, n2 = re.subn(pattern, NOOP, standard_src)
        removed += n1 + n2

    zones = "\n".join(f'    init_zones[{i}] = "{z}";' for i, z in enumerate(init_zones))
    level_src, n = re.subn(r'    level\.zone_manager_init_func = ::nuked_zone_init;\n(    init_zones\[\d+\] = "[^"]+";\n)+',
                           "    level.zone_manager_init_func = ::bo1port_zone_init;\n" + zones + "\n", level_src)
    if n != 1:
        raise RuntimeError("zone setup not found in donor level script")
    level_src += "\nbo1port_zone_init()\n{" + zone_body + "}\n"
    return level_src, standard_src, removed


def add_trace(src, func, tag):
    """Prints a console line after every top-level statement of func (finds where a level script stalls)."""
    m = re.search(r"^" + func + r"\(\s*\)\n\{\n", src, re.M)
    if not m:
        return src
    end = src.index("\n}\n", m.end())
    lines = src[m.end():end].split("\n")
    out, n = [], 0
    for i, line in enumerate(lines):
        out.append(line)
        top_level = line.startswith("    ") and not line.startswith("     ") and line.rstrip().endswith(";")
        prev = lines[i - 1].strip() if i else ""
        is_if_body = prev.startswith(("if", "else", "for", "while", "foreach")) and not prev.endswith((";", "}"))
        next_is_else = i + 1 < len(lines) and lines[i + 1].strip().startswith("else")
        if top_level and not is_if_body and not next_is_else:
            n += 1
            text = line.strip()[:60].replace('"', "'").replace("\\", "/")
            out.append(f'    print( "bo1port {tag} {n}: {text}" );')
    return src[: m.end()] + "\n".join(out) + src[end:]


