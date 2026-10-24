"""Hide placements whose partner model never ripped (e.g. apple heaps meant to sit on a missing crate). Edits .map.base_bodprops."""
import re

BASE = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\map_source\zm\zm_alcatraz_bodfull.map.base_bodprops"
DROP = {"p8_food_fruit_apple_cap_box_half", "p8_wz_ep_roman_candle", "p8_wz_ep_briefcase", "p8_wz_debris_metal_door_scrap_01", "p8_wz_debris_metal_door_scrap_04", "p7_fxanim_mp_apartments_hanging_tarps_gym_04_s3", "p7_fxanim_mp_apartments_hanging_tarps_gym_05_s3"}

b = open(BASE, encoding="utf-8", errors="surrogateescape", newline="").read()
pat = re.compile(r"// entity bodprop \d+\r?\n\{\r?\n(?:(?!\}\r?\n).)*?\"model\" \"(" + "|".join(map(re.escape, DROP)) + r")\".*?\r?\n\}\r?\n", re.S)
b, n = pat.subn("", b)
open(BASE, "w", encoding="utf-8", errors="surrogateescape", newline="").write(b)
print("dropped", n)
