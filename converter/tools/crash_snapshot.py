"""Read the renderer's surface table out of the game at its crash, without a debugger.

Plutonium refuses debuggers, and kills the process before a full
MiniDumpWriteDump can finish, but its crash handler keeps the process alive for
a few seconds while it writes crashdumps/*.dmp. This watcher sees that file
appear and immediately reads (ReadProcessMemory, no debugger attach) the
surface pointer table behind crash 0x72671B, every GfxSurface it points to and
each surface's material name, into tmp/crash_full/<crash>.surfaces.json.

    python313\\python.exe tools\\crash_snapshot.py      (start before loading the map; Ctrl+C to stop)
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import sys
import time
from pathlib import Path

PLUTONIUM = Path(os.environ["LOCALAPPDATA"]) / "Plutonium"
CRASHDUMPS = PLUTONIUM / "crashdumps"
OUT = Path(__file__).resolve().parent.parent / "tmp" / "crash_full"
PROCESS_NAME = "plutonium-bootstrapper-win32.exe"

# function 0x7266E0: surf = (*(GfxSurface ***)0x033ED200)[index + 1]; surf->material (+0x30)->cameraRegion (+0x58)
TABLE_POINTER = 0x033ED200
TABLE_ENTRIES = 0x4000
SURFACE_SIZE = 0x50
MATERIAL_OFFSET = 0x30

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x2

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


def game_pids() -> list[int]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    pids = []
    ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
    while ok:
        if entry.szExeFile.lower() == PROCESS_NAME:
            pids.append(entry.th32ProcessID)
        ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    kernel32.CloseHandle(snap)
    return pids


class Reader:
    def __init__(self, handle):
        self.handle = handle

    def read(self, address: int, size: int) -> bytes | None:
        if address < 0x10000 or address >= 0xFFFF0000:
            return None
        buf = ctypes.create_string_buffer(size)
        done = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.handle, address, buf, size, ctypes.byref(done)) or done.value != size:
            return None
        return buf.raw

    def u32(self, address: int) -> int | None:
        data = self.read(address, 4)
        return struct.unpack("<I", data)[0] if data else None

    def cstring(self, address: int) -> str | None:
        data = self.read(address, 128)
        return data.split(b"\0")[0].decode("latin-1") if data else None


def capture(pid: int) -> dict:
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return {"error": f"OpenProcess failed: {ctypes.get_last_error()}"}
    r = Reader(handle)
    result = {"pid": pid, "table_pointer": TABLE_POINTER}
    table = r.u32(TABLE_POINTER)
    result["table"] = table
    raw = r.read(table, TABLE_ENTRIES * 4) if table else None
    if raw is None:
        kernel32.CloseHandle(handle)
        result["error"] = "table unreadable"
        return result
    pointers = struct.unpack(f"<{TABLE_ENTRIES}I", raw)
    materials: dict[int, str | None] = {}
    entries = []
    for slot, surf in enumerate(pointers):
        if not surf:
            continue
        data = r.read(surf, SURFACE_SIZE)
        if data is None:
            entries.append({"slot": slot, "surface": surf, "unreadable": True})
            continue
        material = struct.unpack_from("<I", data, MATERIAL_OFFSET)[0]
        if material not in materials:
            name_ptr = r.u32(material)
            materials[material] = r.cstring(name_ptr) if name_ptr else None
        entries.append({"slot": slot, "surface": surf, "material": material, "material_name": materials[material],
                        "bytes": data.hex()})
    kernel32.CloseHandle(handle)
    result["entries"] = entries
    result["bad"] = [e for e in entries if e.get("unreadable") or e.get("material_name") is None]
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    seen = {p.name for p in CRASHDUMPS.glob("*")}
    print(f"watching {CRASHDUMPS} (Ctrl+C to stop); captures go to {OUT}")
    while True:
        new = [p for p in CRASHDUMPS.glob("*") if p.name not in seen]
        if new:
            seen.update(p.name for p in new)
            pids = game_pids()
            if not pids:
                print("game already gone when the crash dump appeared; capture missed")
            for pid in pids:
                started = time.time()
                result = capture(pid)
                stem = new[0].name.split(".")[0].replace("-minimal", "")
                path = OUT / f"{stem}.surfaces.json"
                path.write_text(json.dumps(result, indent=1), encoding="utf-8")
                print(f"captured {len(result.get('entries', []))} surfaces, {len(result.get('bad', []))} bad, "
                      f"in {time.time() - started:.2f}s -> {path} {result.get('error', '')}")
        time.sleep(0.02)


if __name__ == "__main__":
    sys.exit(main())
