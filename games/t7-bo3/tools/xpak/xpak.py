"""BO3 (T7) XPAK (magic 'KAPI' v10) reader. Offline, read-only."""
import struct, re

class XPak:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        hdr = self.f.read(0x80)
        assert hdr[0:4] == b"KAPI", "not an xpak"
        self.version = struct.unpack_from("<H", hdr, 6)[0]
        q = lambda o: struct.unpack_from("<Q", hdr, o)[0]
        self.size        = q(0x10)
        self.file_count  = q(0x18)
        self.data_offset = q(0x20)
        self.data_size   = q(0x28)
        self.hash_count  = q(0x30)
        self.hash_offset = q(0x38)
        self.hash_size   = q(0x40)
        self.b_count     = q(0x48)
        self.b_offset    = q(0x50)
        self.b_size      = q(0x58)
        self.c_count     = q(0x60)
        self.c_offset    = q(0x68)
        self.c_size      = q(0x70)
        self._load_hash()
        self._load_meta()

    def _load_hash(self):
        self.f.seek(self.hash_offset)
        raw = self.f.read(self.hash_count * 24)
        self.hash = {}
        for i in range(self.hash_count):
            k, o, s = struct.unpack_from("<QQQ", raw, i*24)
            self.hash[k] = (o, s)

    def _load_meta(self):
        self.f.seek(self.c_offset)
        raw = self.f.read(self.c_size)
        self.entries = {}  # name -> dict
        self.by_key = {}
        pos = 0
        n = len(raw)
        while pos + 16 <= n:
            key = struct.unpack_from("<Q", raw, pos)[0]
            tlen = struct.unpack_from("<I", raw, pos+8)[0]
            # 4 bytes reserved
            if tlen == 0 or tlen > 4096 or pos+16+tlen > n:
                break
            text = raw[pos+16:pos+16+tlen].split(b"\x00",1)[0].decode("latin1","replace")
            d = {"key": key, "_text": text}
            for line in text.splitlines():
                if ":" in line:
                    kk, vv = line.split(":", 1)
                    d[kk.strip()] = vv.strip()
            name = d.get("name")
            if name:
                self.entries[name] = d
                self.by_key[key] = d
            pos += 16 + tlen
            # align to next entry: entries appear contiguous; advance to next key boundary
        self.meta_parsed = pos

    def read_blob(self, key):
        o, s = self.hash[key]
        self.f.seek(o)
        return self.f.read(s)
