import struct

DXGI = {
    "BC7_SRGB": 99, "BC7": 98,
    "BC1_SRGB": 72, "BC1": 71,
    "BC3_SRGB": 78, "BC3": 77,
    "BC4": 80, "BC5": 83, "BC6H": 95,
}

def build_dds(fmt, width, height, mip_count, pixel_data, linear_size):
    dxgi = DXGI.get(fmt)
    if dxgi is None:
        raise ValueError(f"unknown format {fmt}")
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000  # CAPS HEIGHT WIDTH PIXELFORMAT LINEARSIZE
    if mip_count > 1:
        flags |= 0x20000  # MIPMAPCOUNT
    hdr = b"DDS "
    hdr += struct.pack("<I", 124)            # dwSize
    hdr += struct.pack("<I", flags)
    hdr += struct.pack("<I", height)
    hdr += struct.pack("<I", width)
    hdr += struct.pack("<I", linear_size)    # pitch/linear size of top mip
    hdr += struct.pack("<I", 0)              # depth
    hdr += struct.pack("<I", max(mip_count, 1))
    hdr += b"\x00" * (11 * 4)                # reserved1
    # DDS_PIXELFORMAT
    hdr += struct.pack("<I", 32)             # size
    hdr += struct.pack("<I", 0x4)            # DDPF_FOURCC
    hdr += b"DX10"                           # fourCC
    hdr += struct.pack("<IIIII", 0, 0, 0, 0, 0)
    caps = 0x1000                            # TEXTURE
    if mip_count > 1:
        caps |= 0x400000 | 0x8               # MIPMAP | COMPLEX
    hdr += struct.pack("<I", caps)
    hdr += struct.pack("<IIII", 0, 0, 0, 0)
    # DDS_HEADER_DXT10
    hdr += struct.pack("<IIIII", dxgi, 3, 0, 1, 0)  # fmt, TEXTURE2D, misc, arraySize, misc2
    return hdr + pixel_data
