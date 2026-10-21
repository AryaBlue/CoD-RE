"""Havok 2017.2 binary tagfile (TAG0/SDKV 20170200) reader: section tree, type table, items, object decode.
Usage: havok_tag0.py <file> <offset-of-TAG0-tag> [--types|--items]"""
import struct
import sys


def section(buf, pos):
    """-> (tag, payload_start, end, is_leaf). Header: u32 BE (flags in top 2 bits, size incl. header), 4-char tag."""
    word = struct.unpack_from(">I", buf, pos)[0]
    size = word & 0x3FFFFFFF
    return buf[pos + 4:pos + 8].decode("ascii", "replace"), pos + 8, pos + size, bool(word & 0x40000000)


def children(buf, start, end):
    pos = start
    while pos < end:
        tag, a, b, leaf = section(buf, pos)
        yield tag, a, b, leaf
        pos = b


def varint(buf, pos):
    b0 = buf[pos]
    if b0 < 0x80:
        return b0, pos + 1
    if b0 < 0xC0:
        return ((b0 << 8) | buf[pos + 1]) & 0x3FFF, pos + 2
    if b0 < 0xE0:
        return ((b0 << 16) | (buf[pos + 1] << 8) | buf[pos + 2]) & 0x1FFFFF, pos + 3
    if b0 < 0xE8:
        return int.from_bytes(buf[pos:pos + 4], "big") & 0x7FFFFFF, pos + 4
    if b0 < 0xF0:
        return int.from_bytes(buf[pos:pos + 5], "big") & 0x7FFFFFFFF, pos + 5
    return int.from_bytes(buf[pos:pos + 8], "big") & 0x7FFFFFFFFFFFFFF, pos + 8


def strings(blob):
    return blob.split(b"\0")[:-1] and [s.decode("latin-1") for s in blob.split(b"\0")[:-1]]


def load(path, tag_pos):
    """Cut one tagfile out of a bigger file (e.g. the decompressed zone) given the offset of its 'TAG0'."""
    with open(path, "rb") as f:
        f.seek(tag_pos - 4)
        size = struct.unpack(">I", f.read(4))[0] & 0x3FFFFFFF
        f.seek(tag_pos - 4)
        return f.read(size)


class Type:
    def __init__(self, index):
        self.index, self.name, self.templates = index, None, []
        self.parent = self.format = self.subtype = self.version = self.size = self.align = self.flags = 0
        self.fields, self.interfaces = [], []

    def full_name(self, types):
        if not self.templates:
            return self.name
        args = [types[v].name if k.startswith("t") and v else str(v) for k, v in self.templates]
        return f"{self.name}<{','.join(args)}>"


class Tagfile:
    def __init__(self, buf, tag_pos):
        root, start, self.end, _ = section(buf, tag_pos - 4)
        assert root == "TAG0", root
        self.buf, self.sections = buf, {}
        for tag, a, b, leaf in children(buf, start, self.end):
            self.sections[tag] = (a, b)
            if not leaf:
                for sub, c, d, _ in children(buf, a, b):
                    self.sections[sub] = (c, d)
        self.sdk = bytes(buf[slice(*self.sections["SDKV"])]).decode()
        self.data = self.sections["DATA"][0]
        self._types()
        self._items()

    def blob(self, tag):
        return bytes(self.buf[slice(*self.sections[tag])])

    def _types(self):
        type_strings = strings(self.blob("TSTR" if "TSTR" in self.sections else "TST1"))
        field_strings = strings(self.blob("FSTR" if "FSTR" in self.sections else "FST1"))
        b, pos = self.blob("TNA1"), 0
        count, pos = varint(b, pos)
        self.types = [Type(i) for i in range(count)]
        for t in self.types[1:]:
            idx, pos = varint(b, pos)
            t.name = type_strings[idx]
            n, pos = varint(b, pos)
            for _ in range(n):
                k, pos = varint(b, pos)
                v, pos = varint(b, pos)
                t.templates.append((type_strings[k], v))
        b, pos = self.blob("TBDY"), 0
        while pos < len(b):
            idx, pos = varint(b, pos)
            if idx == 0:
                continue
            t = self.types[idx]
            t.parent, pos = varint(b, pos)
            opts, pos = varint(b, pos)
            if opts & 0x01:
                t.format, pos = varint(b, pos)
            if opts & 0x02:
                t.subtype, pos = varint(b, pos)
            if opts & 0x04:
                t.version, pos = varint(b, pos)
            if opts & 0x08:
                t.size, pos = varint(b, pos)
                t.align, pos = varint(b, pos)
            if opts & 0x10:
                t.flags, pos = varint(b, pos)
            if opts & 0x20:
                n, pos = varint(b, pos)
                for _ in range(n & 0xFFFF):  # high bits carry other flags
                    name, pos = varint(b, pos)
                    flags, pos = varint(b, pos)
                    offset, pos = varint(b, pos)
                    ftype, pos = varint(b, pos)
                    t.fields.append((field_strings[name], flags, offset, ftype))
            if opts & 0x40:
                n, pos = varint(b, pos)
                for _ in range(n):
                    a, pos = varint(b, pos)
                    c, pos = varint(b, pos)
                    t.interfaces.append((a, c))
            if opts & 0x80:
                _, pos = varint(b, pos)

    def _items(self):
        b = self.blob("ITEM")
        # item: u32 (type index in low 24 bits, flags high), u32 DATA offset, u32 count
        self.items = [(w & 0xFFFFFF, w >> 24, off, n) for w, off, n in struct.iter_unpack("<III", b)]

    def by_name(self, name):
        return [i for i, (t, _, _, _) in enumerate(self.items) if t and self.types[t].name == name]

    def all_fields(self, t):
        chain = []
        while t:
            chain.append(self.types[t])
            t = self.types[t].parent
        return [f for ty in reversed(chain) for f in ty.fields]

    def field(self, item, name):
        """-> (type, absolute offset) of a named field of item's object."""
        t, _, off, _ = self.items[item]
        for fname, _, foff, ftype in self.all_fields(t):
            if fname == name:
                return ftype, self.data + off + foff
        raise KeyError(f"{self.types[t].name} has no field {name}: {[f[0] for f in self.all_fields(t)]}")

    def array(self, item, name):
        """hkArray field -> (element item index, DATA offset, count); stored as u64 item index + sizes."""
        _, at = self.field(item, name)
        idx = struct.unpack_from("<Q", self.buf, at)[0]
        if not idx:
            return None, 0, 0
        t, _, off, n = self.items[idx]
        return t, self.data + off, n


if __name__ == "__main__":
    tf = Tagfile(load(sys.argv[1], int(sys.argv[2])), 4)
    print(tf.sdk, {k: v[1] - v[0] for k, v in tf.sections.items()}, len(tf.types), "types", len(tf.items), "items")
    if "--types" in sys.argv:
        for t in tf.types[1:]:
            print(t.index, t.full_name(tf.types), "size", t.size, "parent", t.parent and tf.types[t.parent].name,
                  [(f[0], f[2], tf.types[f[3]].full_name(tf.types) if f[3] else None) for f in t.fields])
    if "--items" in sys.argv:
        for i, (t, fl, off, n) in enumerate(tf.items):
            print(i, t and tf.types[t].full_name(tf.types), hex(fl), off, n)
