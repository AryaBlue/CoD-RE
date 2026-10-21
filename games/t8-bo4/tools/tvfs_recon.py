import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # co-located modules
import casc_bo4 as c

cfg = c.parse_build_config()
idx = c.load_idx_map()
vekey = bytes.fromhex(cfg["vfs-root"][1]); vdsize = int(cfg["vfs-root-size"][0])
blte, stored, bsz = c.read_blob(idx, vekey)
tvfs = c.blte_decode(blte)
print("vfs-root decoded:", len(tvfs), "expected", vdsize, "match", len(tvfs) == vdsize)
print("magic:", tvfs[:4])
ver, hdrSize, ekeySize, patchKeySize = struct.unpack_from(">BBBB", tvfs, 4)
flags = struct.unpack_from(">I", tvfs, 8)[0]
pto, pts, vto, vts, cto, cts = struct.unpack_from(">IIIIII", tvfs, 12)
maxDepth = struct.unpack_from(">H", tvfs, 36)[0]
print(f"ver={ver} hdrSize={hdrSize} ekeySize={ekeySize} patchKeySize={patchKeySize} flags=0x{flags:x}")
print(f"pathTable off={pto} size={pts} | vfsTable off={vto} size={vts} | cftTable off={cto} size={cts} maxDepth={maxDepth}")
print("hdr hex[0:40]:", tvfs[:40].hex())
print("pathTable[0:64]:", tvfs[pto:pto + 64].hex())
print("vfsTable[0:32]:", tvfs[vto:vto + 32].hex())
print("cftTable[0:32]:", tvfs[cto:cto + 32].hex())
