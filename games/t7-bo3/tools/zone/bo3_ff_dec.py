"""Decompress a BO3 (T7, version 0x251) fastfile to its raw zone stream: after the 0x248-byte
header the file is a chain of blocks {u32 compressed, u32 decompressed, u32 stored, u32 offset}
each holding one zlib stream."""
import struct
import sys
import zlib
from pathlib import Path


def decompress(ff, out):
    data = Path(ff).read_bytes()
    assert data[:8] == b"TAff0000" and struct.unpack_from("<I", data, 8)[0] == 0x251, "not a BO3 fastfile"
    total = struct.unpack_from("<Q", data, 0x90)[0]
    pos, written = 0x248, 0
    with open(out, "wb") as f:
        while pos + 16 <= len(data) and written < total:
            csz, dsz, stored, _ = struct.unpack_from("<4I", data, pos)
            if csz == 0:
                break
            if dsz == 0:  # filler: pads the stream to the next 8 MB chunk
                pos = (pos // 0x800000 + 1) * 0x800000
                continue
            assert struct.unpack_from("<I", data, pos + 12)[0] == pos, f"bad block header at {pos:#x}"
            block = zlib.decompress(data[pos + 16:pos + 16 + csz])
            assert len(block) == dsz, f"block at {pos:#x}: {len(block)} != {dsz}"
            f.write(block)
            written += dsz
            pos += 16 + stored
    return written, total


if __name__ == "__main__":
    written, total = decompress(sys.argv[1], sys.argv[2])
    print(f"{written:#x} of {total:#x} bytes")
