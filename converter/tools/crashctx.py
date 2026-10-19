"""Faulting thread context + stack scan of a 32-bit minidump (the exception stream's own context, not the
thread list's, which shows the dump writer). usage: crashctx.py <dmp> [module substring]"""
import struct, sys
from minidump.minidumpfile import MinidumpFile

mf = MinidumpFile.parse(sys.argv[1])
mods = mf.modules.modules
reader = mf.get_reader()


def where(addr):
    for m in mods:
        if m.baseaddress <= addr < m.baseaddress + m.size:
            return f"{m.name.split(chr(92))[-1]}+0x{addr - m.baseaddress:X}"
    return None


exc = mf.exception.exception_records[0]
loc = exc.ThreadContext
raw = open(sys.argv[1], "rb").read()[loc.Rva : loc.Rva + loc.DataSize]
# x86 CONTEXT: ContextFlags, Dr0-3,6,7, FloatSave(112), Gs Fs Es Ds, Edi Esi Ebx Edx Ecx Eax, Ebp Eip SegCs EFlags Esp SegSs
off = 4 + 6 * 4 + 112 + 4 * 4
edi, esi, ebx, edx, ecx, eax, ebp, eip, cs, eflags, esp = struct.unpack_from("<11I", raw, off)
print(f"fault 0x{exc.ExceptionRecord.ExceptionAddress:X} params {[hex(p) for p in exc.ExceptionRecord.ExceptionInformation[:2]]}")
print(f"eip {eip:08X} ({where(eip)}) esp {esp:08X} ebp {ebp:08X}")
print(f"eax {eax:08X} ebx {ebx:08X} ecx {ecx:08X} edx {edx:08X} esi {esi:08X} edi {edi:08X}")
try:
    data = b""
    for o in range(0, 0x800, 0x40):
        try:
            data += reader.read(esp + o, 0x40)
        except Exception:
            break
except Exception as e:
    data = b""
    print("stack read failed", e)
for i in range(0, len(data) - 3, 4):
    v = struct.unpack_from("<I", data, i)[0]
    w = where(v)
    if w and (len(sys.argv) < 3 or sys.argv[2] in w) and 0x401000 <= v < 0x1000000:
        print(f"  [esp+0x{i:03X}] 0x{v:08X} {w}")
