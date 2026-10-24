"""BO4 (T8) asset-name hashes: FNV-1a 64 on the lower-cased name, optionally masked to 63 bits (ACTS hash_t8 style)."""
FNV_OFFSET, FNV_PRIME, MASK63 = 0xCBF29CE484222325, 0x100000001B3, 0x7FFFFFFFFFFFFFFF


def fnv1a64(s, offset=FNV_OFFSET):
    h = offset
    for c in s.lower().encode():
        h = ((h ^ c) * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def variants(name):
    h = fnv1a64(name)
    return {"fnv": h, "fnv63": h & MASK63}
