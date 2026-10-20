"""BO3 (T7) XPAK extractor. Our own port of the decompression scheme; the
block-group layout (BO3XPakDataHeader) and DecompressPackageObject logic were
reverse-engineered with reference to Scobalula's Greyhound (XPAKCache.cpp,
DBGameFiles.h) — see ../../notes/t7_xpak_format.md for the format write-up.
Offline, read-only."""
import sys, struct
sys.path.insert(0, ".")
from xpak import XPak
from lz4blk import decode_block

def decompress(payload, decompressed_size):
    """Port of DecompressPackageObject. payload = CompressedSize bytes at
    file offset DataOffset+Entry.Offset. Returns decompressed bytes."""
    out = bytearray()
    remaining = decompressed_size
    pos = 0
    n = len(payload)
    while pos < n and remaining > 0:
        if pos + 128 > n:
            break
        count = struct.unpack_from("<I", payload, pos)[0]
        # Offset field at pos+4 (unused for linear read)
        cmds = struct.unpack_from("<30I", payload, pos + 8)
        pos += 128  # sizeof(BO3XPakDataHeader) = 8 + 30*4
        if count > 30:
            raise ValueError(f"insane command count {count} at pos {pos-128}")
        for i in range(count):
            cmd = cmds[i]
            block_size = cmd & 0xFFFFFF
            flag = cmd >> 24
            data = payload[pos:pos + block_size]
            if len(data) < block_size:
                raise ValueError("EOF in data block")
            if flag == 0x0:            # raw
                out += data
                remaining -= block_size
            elif flag == 0x3:          # LZ4 block
                dec, _, reason = decode_block(data, 0, max_out=remaining)
                out += dec
                remaining -= len(dec)
            elif flag in (0x6, 0x8):
                raise ValueError(f"Oodle/Siren block (flag {flag}) not supported offline")
            else:
                pass  # skip unknown
            pos += block_size
        # align up to next 0x80 boundary
        pos = (pos + 0x7F) & ~0x7F
    return bytes(out)

def extract(xpak_path, name, out_path):
    x = XPak(xpak_path)
    d = x.entries[name]
    key = d["key"]
    raw_off, comp_size = x.hash[key]
    file_off = x.data_offset + raw_off
    x.f.seek(file_off)
    payload = x.f.read(comp_size)
    dec_size = int(d["size0"]) if "size0" in d else int(d.get("width"))*int(d.get("height"))
    # total decompressed = sum of all mip sizes
    total = 0
    i = 0
    while f"size{i}" in d:
        total += int(d[f"size{i}"]); i += 1
    if total == 0: total = dec_size
    data = decompress(payload, total)
    with open(out_path, "wb") as fo:
        fo.write(data)
    return d, file_off, comp_size, total, len(data)

if __name__ == "__main__":
    xp, name, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    d, fo, cs, total, got = extract(xp, name, outp)
    print(f"{name}: fmt={d.get('format')} {d.get('width')}x{d.get('height')} levels={d.get('levels')}")
    print(f"  file_off=0x{fo:x} comp_size={cs} expected_decomp={total} got={got} -> {outp}")
