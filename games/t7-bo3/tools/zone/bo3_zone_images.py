"""Extract the images a BO3 zone carries inline (UI art is resident, not streamed) from a stream
decompressed by bo3_ff_dec.py. A GfxImage record ends with its inline name; relative to the name:
-72 u16 width,height  -32 u64 data size  -24 u64 DXGI format  -16 / -48 = -1 (inline pointers),
and the pixels follow the name's terminating NUL. Writes <out>/<name>.png (top mip) + index.json."""
import io
import json
import re
import struct
import sys
from pathlib import Path

from PIL import Image

BLOCK_BYTES = {71: 8, 72: 8, 80: 8, 81: 8, 74: 16, 75: 16, 77: 16, 78: 16, 83: 16, 84: 16, 95: 16, 96: 16,
               98: 16, 99: 16}
SRGB_TWIN = {72: 71, 75: 74, 78: 77, 99: 98}  # same bits; Pillow decodes only the UNORM ids
RAW_BYTES = {28: 4, 29: 4, 87: 4, 91: 4, 61: 1, 65: 1}
NAME = re.compile(rb"\xff{8}[\x00-\xff]{4}\x00{4}([a-z0-9_$~\-./]{3,96})\x00")


def dds(w, h, fmt, data):
    header = struct.pack("<4sI6I44x8I5I", b"DDS ", 124, 0x1007 | 0x80000, h, w, len(data), 0, 1,
                         32, 0x4, 0x30315844, 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
    return header + struct.pack("<5I", SRGB_TWIN.get(fmt, fmt), 3, 0, 1, 0) + data


def top_mip_size(w, h, fmt):
    if fmt in BLOCK_BYTES:
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * BLOCK_BYTES[fmt]
    return w * h * RAW_BYTES[fmt]


def records(zone):
    for m in NAME.finditer(zone):
        i = m.start(1)
        if zone[i - 48:i - 40] != b"\xff" * 8:
            continue
        w, h = struct.unpack_from("<HH", zone, i - 72)
        size, fmt = struct.unpack_from("<QQ", zone, i - 32)
        if not (0 < w <= 8192 and 0 < h <= 8192 and 0 < size < 1 << 28 and fmt < 200):
            continue
        yield m.group(1).decode(), w, h, fmt, size, m.end()


def extract(zone_path, out, pattern):
    zone = Path(zone_path).read_bytes()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    keep = re.compile(pattern)
    index, skipped = {}, {}
    for name, w, h, fmt, size, start in records(zone):
        if not keep.search(name) or name in index:
            continue
        if fmt not in BLOCK_BYTES and fmt not in RAW_BYTES:
            skipped[name] = fmt
            continue
        top = top_mip_size(w, h, fmt)
        data = zone[start:start + top]
        if fmt in BLOCK_BYTES:
            image = Image.open(io.BytesIO(dds(w, h, fmt, data)))
        else:
            mode = {4: "RGBA", 1: "L"}[RAW_BYTES[fmt]]
            image = Image.frombytes(mode, (w, h), data)
            if fmt in (87, 91):
                b, g, r, a = image.split()
                image = Image.merge("RGBA", (r, g, b, a))
        image.convert("RGBA").save(out / f"{name.replace('/', '_')}.png")
        index[name] = {"width": w, "height": h, "dxgi": fmt, "bytes": size, "offset": start}
    (out / "index.json").write_text(json.dumps({"images": index, "unsupported_format": skipped}, indent=1))
    return index, skipped


if __name__ == "__main__":
    index, skipped = extract(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
    print(f"{len(index)} images extracted, {len(skipped)} in unsupported formats {sorted(set(skipped.values()))}")
