p = r"F:\ClaudeWork\bo3\bod_port\t8_world\nav\bod_spawn_nodes.ents"
txt = open(p, encoding="utf-8", errors="replace").read()
if "initial_spawn_points" in txt:
    print("already has spawns - skipping"); raise SystemExit
pts = [(897,10595,1360),(913,10595,1360),(897,10611,1360),(913,10611,1360)]
blocks = ""
for i,(x,y,z) in enumerate(pts,1):
    blocks += (f'{{\r\n"classname" "script_struct"\r\n"targetname" "initial_spawn_points"\r\n'
               f'"origin" "{x} {y} {z}"\r\n"angles" "0 90 0"\r\n"script_int" "{i}"\r\n}}\r\n')
open(p,"w",encoding="utf-8",newline="").write(txt.rstrip()+"\r\n"+blocks)
print(f"appended {len(pts)} initial_spawn_points to {p}")
