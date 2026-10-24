"""Reverse triangle winding in XMODEL_EXPORTs (swap each TRI's 2nd and 3rd corner): BO3 front faces wind opposite to glTF."""
import re
import sys
from pathlib import Path

CORNER = r"VERT \d+\n(?:[A-Z]+[^\n]*\n)*?UV[^\n]*\n"
TRI = re.compile(rf"^(TRI [^\n]*\n)({CORNER})({CORNER})({CORNER})", re.M)

for path in map(Path, sys.argv[1:]):
    text = path.read_text(errors="replace")
    out, n = TRI.subn(lambda m: m.group(1) + m.group(2) + m.group(4) + m.group(3), text)
    path.write_text(out, newline=chr(10))
    print(path.name, n)
