"""Add or refresh a Contents block in the long notes.

    python shared/tools/toc.py            # every .md with 200+ lines and 8+ headings
    python shared/tools/toc.py some.md    # just that file

The block sits between <!-- toc --> and <!-- /toc --> right after the title, so running it again replaces the old one.
Links use GitHub's heading anchors.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN_LINES, MIN_HEADINGS = 200, 8
START, END = "<!-- toc -->", "<!-- /toc -->"


def slug(text):
    text = re.sub(r"`([^`]*)`", r"\1", text).strip().lower()
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def toc_lines(lines):
    out, seen, fenced = [], {}, False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        if fenced or not re.match(r"^#{2,3} ", line):
            continue
        level = line.index(" ")
        title = line[level + 1:].strip()
        anchor = slug(title)
        n = seen.get(anchor, 0)
        seen[anchor] = n + 1
        if n:
            anchor = f"{anchor}-{n}"
        out.append(f"{'  ' * (level - 2)}- [{title}]({anchor})".replace("](", "](#", 1))
    return out


def process(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    body = lines
    if START in text and END in text:
        a, b = lines.index(START), lines.index(END)
        body = lines[:a] + lines[b + 1:]
        while a < len(body) and body[a].strip() == "" and a > 0 and body[a - 1].strip() == "":
            del body[a]
    if len(body) < MIN_LINES or sum(1 for l in body if l.startswith("#")) < MIN_HEADINGS:
        return False
    toc = toc_lines(body)
    if not toc:
        return False
    title = next((i for i, l in enumerate(body) if l.startswith("# ")), None)
    if title is None:
        return False
    block = ["", START, "## Contents", ""] + toc + [END]
    new = body[:title + 1] + block + body[title + 1:]
    path.write_text("\n".join(new) + "\n", encoding="utf-8")
    return True


def main(args):
    files = [Path(a) for a in args] or [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
    for f in files:
        if process(f):
            print("toc:", f.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
