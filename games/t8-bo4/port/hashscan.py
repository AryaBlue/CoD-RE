"""Scan zm_escape.ff.dec for 8-byte T8 name hashes at any alignment; returns {hash: [offsets]}."""
import numpy as np
DEC = r"F:\ClaudeWork\bo3\bod_port\t8_world\decomp\zm_escape.ff.dec"
def scan(hashes, path=DEC, cap=64):
    want = np.array(sorted(set(hashes)), dtype=np.uint64)
    raw = np.fromfile(path, dtype=np.uint8)
    out = {}
    for sh in range(8):
        n = (len(raw) - sh) // 8
        v = raw[sh:sh + n * 8].view(np.uint64)
        idx = np.nonzero(np.isin(v, want))[0]
        for i in idx:
            out.setdefault(int(v[i]), []).append(sh + int(i) * 8)
    for k in out: out[k] = sorted(out[k])[:cap] if cap else sorted(out[k])
    return out
