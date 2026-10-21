"""Offline BO4 (viper) local CASC reader: idx -> data.NNN blob -> BLTE -> bytes.
Pure stdlib + optional Oodle via ACTS oo2core for 'Z'? (BLTE uses zlib, not Oodle).
From-first-principles for task #37 b1. No game, no exe. British spelling in comments."""
from __future__ import annotations
import os, struct, glob, zlib, hashlib
from pathlib import Path

INSTALL = Path(r"PATH/TO/bo4_install")  # set this to your own path
DATADIR = INSTALL / "Data" / "data"


def parse_build_config():
    """Read .build.info -> build-config hash -> parse Data/config build config text."""
    bi = (INSTALL / ".build.info").read_text().splitlines()
    cols = bi[0].split("|")
    names = [c.split("!")[0] for c in cols]
    row = bi[1].split("|")
    rec = dict(zip(names, row))
    bkey = rec["Build Key"]
    cfg = (INSTALL / "Data" / "config" / bkey[:2] / bkey[2:4] / bkey).read_text()
    out = {}
    for line in cfg.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().split()
    return out


def load_idx_map():
    """Merge all latest-version .idx -> {ekey9: (archive, offset, size)}."""
    latest = {}  # bucket(2 hex) -> (version, path)
    for p in glob.glob(str(DATADIR / "*.idx")):
        name = os.path.basename(p)[:-4]
        bucket, ver = name[:2], name[-2:]
        if bucket not in latest or ver > latest[bucket][0]:
            latest[bucket] = (ver, p)
    m = {}
    for _, (_, p) in sorted(latest.items()):
        d = open(p, "rb").read()
        hhs = struct.unpack_from("<I", d, 0)[0]
        _ver, _bk, _ex, esz, eob, ekb, eobits = struct.unpack_from("<HBBBBBB", d, 8)
        base = (8 + hhs + 0x0F) & ~0x0F
        esize = struct.unpack_from("<I", d, base)[0]
        estart = base + 8
        entry_len = ekb + eob + esz
        offmask = (1 << eobits) - 1
        for i in range(esize // entry_len):
            o = estart + i * entry_len
            key = d[o:o + ekb]
            packed = int.from_bytes(d[o + ekb:o + ekb + eob], "big")
            arch = packed >> eobits
            off = packed & offmask
            size = struct.unpack_from("<I", d, o + ekb + eob)[0]
            if size:  # drop 30-byte stub entries
                m[key] = (arch, off, size)
    return m


def read_blob(idxmap, ekey: bytes):
    """ekey: full 16 bytes (or >=9). Returns the BLTE-framed blob WITHOUT the 30-byte CASC header."""
    k9 = ekey[:9]
    if k9 not in idxmap:
        raise KeyError(f"ekey {ekey.hex()} not in idx")
    arch, off, size = idxmap[k9]
    with open(DATADIR / f"data.{arch:03d}", "rb") as f:
        f.seek(off)
        raw = f.read(size)
    # CASC blob header: 16 bytes ekey (reversed) + u32 size(LE) + u16 flags + u32 + u32 = 30 bytes
    stored = raw[:16][::-1]
    blobsize = struct.unpack_from("<I", raw, 16)[0]
    return raw[30:], stored, blobsize


def blte_decode(data: bytes, verify: bool = False) -> bytes:
    """Decode a BLTE stream. Handles chunk modes N (none) and Z (zlib). E/F flagged.
    verify=True checks each chunk's stored md5 (byte-exactness self-check)."""
    assert data[:4] == b"BLTE", f"not BLTE: {data[:4]!r}"
    header_size = struct.unpack_from(">I", data, 4)[0]
    out = bytearray()
    if header_size == 0:
        _decode_chunks(data, 8, [(len(data) - 8, None)], out)
        return bytes(out)
    chunk_count = int.from_bytes(data[9:12], "big")  # [8]=flags(1) [9:12]=count(3 BE)
    tbl = 12
    chunks = []
    for _ in range(chunk_count):
        csize, usize = struct.unpack_from(">II", data, tbl)
        chk = data[tbl + 8:tbl + 24]  # md5 of the compressed chunk
        tbl += 24
        chunks.append((csize, chk))
    pos = header_size
    for csize, chk in chunks:
        chunk = data[pos:pos + csize]
        pos += csize
        if verify and hashlib.md5(chunk).digest() != chk:
            raise ValueError("BLTE chunk md5 mismatch")
        mode = chunk[0:1]
        body = chunk[1:]
        if mode == b"N":
            out += body
        elif mode == b"Z":
            out += zlib.decompress(body)
        elif mode == b"E":
            raise NotImplementedError("BLTE 'E' encrypted chunk (needs keyring)")
        elif mode == b"F":
            raise NotImplementedError("BLTE 'F' recursive frame")
        else:
            raise ValueError(f"unknown BLTE mode {mode!r}")
    return bytes(out)


def _decode_chunks(data, pos, chunks, out):
    for csize, _ in chunks:
        chunk = data[pos:pos + csize] if csize else data[pos:]
        pos += csize
        mode = chunk[0:1]
        body = chunk[1:]
        if mode == b"N":
            out += body
        elif mode == b"Z":
            out += zlib.decompress(body)
        else:
            raise ValueError(f"single-chunk mode {mode!r}")


if __name__ == "__main__":
    import sys
    cfg = parse_build_config()
    print("build-product:", cfg.get("build-product"))
    enc_ckey = bytes.fromhex(cfg["encoding"][0])
    enc_ekey = bytes.fromhex(cfg["encoding"][1])
    enc_dsize = int(cfg["encoding-size"][0])
    print("encoding ckey/ekey:", enc_ckey.hex(), enc_ekey.hex(), "dsize", enc_dsize)
    idxmap = load_idx_map()
    print("idx entries:", len(idxmap))
    blte, stored, blobsize = read_blob(idxmap, enc_ekey)
    print("blob ekey(stored):", stored.hex(), "blobsize", blobsize, "blte0:", blte[:4])
    dec = blte_decode(blte)
    md5 = hashlib.md5(dec).hexdigest()
    print(f"decoded {len(dec)} bytes, md5={md5}")
    print("ORACLE ckey match:", md5 == enc_ckey.hex(), "| size match:", len(dec) == enc_dsize)
