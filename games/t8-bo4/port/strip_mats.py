"""Remove every TRI using the named materials from XMODEL_EXPORTs in place (MATERIAL lines kept, NUMFACES rewritten)."""
import re, sys

TRI = re.compile(r'^TRI \d+ (\d+) [^\n]*\n(?:(?!TRI |NUMOBJECTS|NUMMATERIALS)[^\n]*\n)*', re.M)

def strip(path, names):
    t = open(path, encoding="utf-8", errors="replace").read()
    mats = {i for i, m in enumerate(re.findall(r'^MATERIAL \d+ "([^"]+)"', t, re.M)) if m in names}
    if not mats: return 0
    head, sep, rest = t.partition("NUMFACES ")
    count, nl, body = rest.partition("\n")
    end = re.search(r'^(NUMOBJECTS|NUMMATERIALS)', body, re.M)
    faces, tail = (body[:end.start()], body[end.start():]) if end else (body, "")
    removed = 0
    def keep(m):
        nonlocal removed
        if int(m.group(1)) in mats: removed += 1; return ""
        return m.group(0)
    faces = TRI.sub(keep, faces)
    open(path, "w", encoding="utf-8").write(head + sep + str(int(count) - removed) + nl + faces + tail)
    return removed

if __name__ == "__main__":
    names = set(sys.argv[1].split(","))
    for p in sys.argv[2:]: print(p.rsplit("/", 1)[-1], strip(p, names))
