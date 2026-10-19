"""Explain an EXE_CLIENT_FIELD_MISMATCH from the game's own log.

On a mismatch BO2 prints the client's and the server's clientfield tables to console_zm.log. This diffs the
latest pair (name, type, bits, version), prints the engine's own mismatch lines and, for every differing
field, where the last build registers it (clientfield_audit.json from the build's audit step).

usage: python313\\python.exe tools\\check_clientfields.py [console_zm.log] [--audit clientfield_audit.json]
"""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = Path(os.environ["LOCALAPPDATA"]) / "Plutonium/storage/t6/main/console_zm.log"
HEADER_RE = re.compile(r"\*+CLIENTFIELD SETS FOR \[(Client|Server)\]\*+")
SET_RE = re.compile(r"CLIENTFIELD SET \[(\w+)\] COUNT")
FIELD_RE = re.compile(r"FIELD : '([^']+)'")
INFO_RE = re.compile(r"TYPE : (\w+)\s+BITS : (\d+)\s+VERSION : (-?\d+)")


def tables(lines: list[str]) -> tuple[dict, dict, list[str]]:
    """The last client/server table pair in the log, plus the engine's mismatch lines after it."""
    starts = [i for i, line in enumerate(lines) if HEADER_RE.search(line)]
    client_at = max((i for i in starts if "[Client]" in lines[i]), default=None)
    if client_at is None:
        return {}, {}, []
    parsed = {"Client": {}, "Server": {}}
    side, cf_set, field, engine = None, None, None, []
    for line in lines[client_at:]:
        if header := HEADER_RE.search(line):
            side = header[1]
        elif m := SET_RE.search(line):
            cf_set = m[1]
        elif m := FIELD_RE.search(line):
            field = f"{cf_set}/{m[1]}"
        elif (m := INFO_RE.search(line)) and side and field:
            parsed[side][field] = (m[1], int(m[2]), int(m[3]))
        elif line.startswith("Clientfield ") or "EXE_CLIENT_FIELD_MISMATCH" in line:
            engine.append(line.strip())
            if "EXE_CLIENT_FIELD_MISMATCH" in line:
                break
        elif side == "Server" and "COM_ERROR" not in line and line.startswith("====="):
            break
    return parsed["Client"], parsed["Server"], engine


def newest_audit() -> Path | None:
    audits = sorted((ROOT / "b2w_work").glob("*/stage/clientfield_audit.json"), key=lambda p: p.stat().st_mtime)
    return audits[-1] if audits else None


def where(audit: dict, side: str, field: str) -> str:
    info = audit.get("fields", {}).get(side, {}).get(field.lower())
    if info:
        return "; ".join(info["where"][:3])
    retired = field.lower() in audit.get("retired_by_version", {}).get(side, [])
    return "registered but retired at the server's version" if retired else "not found in the build's scripts"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", type=Path, default=LOG)
    ap.add_argument("--audit", type=Path, default=None)
    a = ap.parse_args()
    client, server, engine = tables(a.log.read_text(encoding="utf-8", errors="replace").splitlines())
    if not client:
        print(f"no clientfield tables in {a.log}: the game only prints them on a mismatch")
        return 0
    audit_path = a.audit or newest_audit()
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path and audit_path.is_file() else {}
    print(f"{a.log}: client {len(client)} fields, server {len(server)} fields")
    print(f"build audit: {audit_path or 'none found'}\n")
    print("engine says:", *engine or ["(no mismatch lines)"], sep="\n  ")
    print()
    differences = 0
    for field in sorted(client.keys() | server.keys()):
        c, s = client.get(field), server.get(field)
        if c == s:
            continue
        differences += 1
        if c is None:
            print(f"ONLY SERVER  {field}  {s}\n  server: {where(audit, 'server', field)}\n  client: {where(audit, 'client', field)}")
        elif s is None:
            print(f"ONLY CLIENT  {field}  {c}\n  client: {where(audit, 'client', field)}\n  server: {where(audit, 'server', field)}")
        else:
            print(f"DIFFERS      {field}  client {c} vs server {s} (type, bits, version)\n"
                  f"  client: {where(audit, 'client', field)}\n  server: {where(audit, 'server', field)}")
        if field.lower().split("/")[1].rsplit("_", 1)[0] in ("overlay", "visionset"):
            vs_type = field.split("/")[1].rsplit("_", 1)[0]
            for side in ("server", "client"):
                infos = sorted(audit.get("vsmgr", {}).get(side, {}).get(vs_type, {}))
                print(f"  {side} visionset manager {vs_type} infos: {', '.join(infos) or 'none'}")
    print(f"\n{differences} differing fields")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
