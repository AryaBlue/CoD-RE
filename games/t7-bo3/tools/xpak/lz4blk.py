"""Pure-python LZ4 block decompressor (no deps). Greedy: decode one LZ4 block
sequence from src[pos:] producing output, stopping when max_out reached or a
token cannot complete. Returns (bytes out, consumed, reason)."""

def decode_block(src, pos=0, max_out=None, end=None):
    if end is None: end = len(src)
    out = bytearray()
    start = pos
    while pos < end:
        if max_out is not None and len(out) >= max_out:
            return bytes(out), pos-start, "hit_max_out"
        token = src[pos]; pos += 1
        lit = token >> 4
        if lit == 15:
            while True:
                if pos >= end: return bytes(out), pos-start, "eof_litlen"
                b = src[pos]; pos += 1; lit += b
                if b != 255: break
        if pos+lit > end:
            return bytes(out), pos-start, "eof_literals"
        out += src[pos:pos+lit]; pos += lit
        if max_out is not None and len(out) >= max_out:
            return bytes(out), pos-start, "done_after_literals"
        if pos+2 > end:
            return bytes(out), pos-start, "eof_no_match(final_literals)"
        off = src[pos] | (src[pos+1] << 8); pos += 2
        if off == 0:
            return bytes(out), pos-start, "zero_offset(block_end?)"
        ml = token & 0xF
        if ml == 15:
            while True:
                if pos >= end: return bytes(out), pos-start, "eof_matchlen"
                b = src[pos]; pos += 1; ml += b
                if b != 255: break
        ml += 4
        if off > len(out):
            return bytes(out), pos-start, f"bad_offset off={off}>out={len(out)}"
        s = len(out) - off
        for i in range(ml):
            out.append(out[s+i])
    return bytes(out), pos-start, "eof"
