"""BO4 .xpak (KAPI v0xB) reader: header, 24-byte hash table, 0x80-aligned block headers, Oodle Kraken payloads.
Usage: xpak_kapi.py <file.xpak> [--extract outdir]  (64-bit Python; uses the game's oo2core_6_win64.dll)."""
import ctypes
import struct
import sys
from pathlib import Path

OODLE = r"PATH/TO/bo4_install/oo2core_6_win64.dll"  # set this to your own path
HEADER = "<4sHHQ" + "Q" * 13
FIELDS = "magic unk version one size file_count data_offset data_size hash_count hash_offset hash_size " \
         "unk_count unk_offset unk_size index_count index_offset index_size".split()


def oodle():
    dec = ctypes.WinDLL(OODLE).OodleLZ_Decompress
    dec.restype = ctypes.c_int64
    c = ctypes
    dec.argtypes = [c.c_char_p, c.c_int64, c.c_char_p, c.c_int64, c.c_int, c.c_int, c.c_int,
                    c.c_void_p, c.c_int64, c.c_void_p, c.c_void_p, c.c_void_p, c.c_int64, c.c_int]

    def run(src, n):
        out = ctypes.create_string_buffer(n)
        got = dec(src, len(src), out, n, 1, 0, 0, None, 0, None, None, None, 0, 3)
        if got != n:
            raise ValueError(f"oodle returned {got}, expected {n}")
        return out.raw
    return run


class Xpak:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.h = dict(zip(FIELDS, struct.unpack(HEADER, self.f.read(struct.calcsize(HEADER)))))
        assert self.h["magic"] == b"KAPI" and self.h["version"] == 0xB, self.h
        self.f.seek(self.h["hash_offset"])
        # entry: u64 key, u64 offset (relative to data_offset), u64 size (0x80-aligned, includes block headers)
        self.entries = {k: (o, s) for k, o, s in struct.iter_unpack("<QQQ", self.f.read(self.h["hash_count"] * 24))}
        self._dec = None

    def blocks(self, key):
        """Yield (flag, payload) per block. Block header: u32 count, u32 raw output offset, u32 cmd[count] (size & 0xFFFFFF | flag << 24)."""
        offset, size = self.entries[key]
        pos, end = self.h["data_offset"] + offset, self.h["data_offset"] + offset + size
        while pos < end:
            self.f.seek(pos)
            head = self.f.read(0x80)
            count = struct.unpack_from("<I", head)[0]
            if not 0 < count <= 30:
                break  # 0xCDCDCDCD padding at the tail of some entries
            pos += 0x80
            for cmd in struct.unpack_from(f"<{count}I", head, 8):  # payloads are packed; only the group is 0x80-aligned
                self.f.seek(pos)
                yield cmd >> 24, self.f.read(cmd & 0xFFFFFF) if cmd >> 24 != 0xCF else b""
                pos += cmd & 0xFFFFFF
            pos = (pos + 0x7F) & ~0x7F

    def read(self, key):
        self._dec = self._dec or oodle()
        out = []
        for flag, data in self.blocks(key):
            if flag == 8:  # u32 raw size + Oodle Kraken stream
                out.append(self._dec(data[4:], struct.unpack_from("<I", data)[0]))
            elif flag == 0xCF:  # padding: skip, no output
                continue
            elif flag == 0:
                out.append(data)
            else:
                raise ValueError(f"unknown block flag {flag}")
        return b"".join(out)


if __name__ == "__main__":
    x = Xpak(sys.argv[1])
    print({k: hex(v) if isinstance(v, int) else v for k, v in x.h.items()})
    dest = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--extract" else None
    ok = fail = total = 0
    for key in x.entries:
        try:
            data = x.read(key)
            ok, total = ok + 1, total + len(data)
            if dest:
                dest.mkdir(parents=True, exist_ok=True)
                (dest / f"{key:016x}.bin").write_bytes(data)
        except ValueError as e:
            fail += 1
            print(f"{key:016x}: {e}")
    print(f"{ok} entries decoded, {fail} failed, {total / 1e6:.1f} MB raw")
