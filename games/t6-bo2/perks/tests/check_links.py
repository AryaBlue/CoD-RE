"""Would Plutonium link this script? Every call must be this script's own function, one in the files it #includes,
a qualified path::function that exists there, or an engine builtin.

usage: python check_links.py <script.gsc> <decompiled stock dir> <decompiled includes dir> <CoDMPServer_PC.map>
  stock dir:    every stock Zombies script, decompiled (gsc-tool), file names flattened
  includes dir: common_scripts\\utility as utility.gsc, maps\\mp\\_utility as _utility.gsc (flattening clashes with
                animscripts\\utility, so these two come separately); _zm_utility.gsc is taken from the stock dir
Builtins: anything stock scripts call but no script defines (they link, so it's the engine's), plus names the
server .map has as GScr_/Scr_/PlayerCmd_/ScrCmd_/HECmd_<name> (for builtins stock never happens to call).
"""
import re
import sys
from pathlib import Path

KEYWORDS = {"if", "while", "for", "foreach", "switch", "return", "wait", "waittill", "notify", "endon", "isdefined", "thread"}
FN_DEF = re.compile(r"^([a-z_0-9]+)\s*\(", re.M)
CALL = re.compile(r"(?<![:\w.\]])([a-z_][a-z_0-9]*)\s*\(")


def strip(text):
    return re.sub(r'"(\\.|[^"\\])*"', '""', re.sub(r"//[^\n]*", "", text))


src = strip(Path(sys.argv[1]).read_text())
stock, includes = Path(sys.argv[2]), Path(sys.argv[3])
defs, stock_calls = {}, set()
for f in list(stock.glob("*.gsc")) + list(includes.glob("*.gsc")):
    text = strip(f.read_text(errors="ignore"))
    tag = ("inc:" if f.parent == includes else "") + f.name
    for m in FN_DEF.finditer(text):
        defs.setdefault(m.group(1), set()).add(tag)
    stock_calls |= set(CALL.findall(text))
builtins = {c for c in stock_calls if c not in defs}
syms = {m.lower() for m in re.findall(r"\b(?:GScr|Scr|PlayerCmd|ScrCmd|HECmd)_(\w+)", Path(sys.argv[4]).read_text(errors="ignore"))}
included = {"inc:utility.gsc", "inc:_utility.gsc", "_zm_utility.gsc"}

bad = 0
for path, fn in sorted(set(re.findall(r"([a-z_\\]+)::([a-z_0-9]+)", src))):
    if path.split("\\")[-1] + ".gsc" not in defs.get(fn, ()):
        print("MISSING", path + "::" + fn); bad += 1
own = set(FN_DEF.findall(src))
for c in sorted(set(CALL.findall(src)) - own - KEYWORDS):
    if defs.get(c, set()) & included or c in builtins or c in syms:
        continue
    where = sorted(defs.get(c, ()))
    print("UNRESOLVED", c, ("defined only in " + ", ".join(where[:3])) if where else "(no script defines it and it isn't a known builtin)")
    bad += 1
print("links ok" if not bad else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
