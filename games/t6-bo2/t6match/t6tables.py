"""Print the T6 technique, draw-list and vertex-format tables from the server exe (see ../notes/t6_techniques.md).
usage: t6tables.py CoDMPServer_PC.exe"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import PE

TECH_NAMES = 0x00D1BE90      # {const char *name; uint value}[48]
SET_DEFAULT_LIT = 0x00A7C560  # R_SetDefaultLitTechTypes
DRAW_METHOD = 0x084F6F08      # gfxDrawMethod
LIST_SETUP = 0x00D06298       # s_drawSurfListInfoSetup[23]
LIST_NAMES = 0x010C0818       # g_drawlistNames
STREAM_INFO = 0x00D0F0C8      # stream_source_info_t[20][11]
STREAM_DEST = 0x00D0F360      # {const char *semantic; u8 index}[20]

SURF = ['TRIANGLES', 'TRIANGLES_NO_SUN_SHADOW', 'STATICMODEL_RIGID_NO_SUN_SHADOW', 'STATICMODEL_RIGID',
        'STATICMODEL_SKINNED', 'BMODEL', 'XMODEL_RIGID', 'XMODEL_RIGID_NO_SUN_SHADOW', 'XMODEL_RIGID_SKINNED',
        'XMODEL_SKINNED', 'XMODEL_SKINNED_NO_SUN_SHADOW', 'CODE_MESH', 'MARK_MESH', 'PARTICLE_CLOUD', 'ROPE_MESH',
        'GLASS_MESH']
LIGHT = ['NONE', 'DIR', 'SPOT', 'SPOT_SQ', 'SPOT_RND', 'OMNI', 'DIR_SM', 'SPOT_SM', 'SPOT_SQ_SM', 'SPOT_RND_SM', 'OMNI_SM']
DECL = ['GENERIC', 'PACKED', 'PACKED_LMAP_VC', 'WORLD', 'PACKED_WORLD'] + \
       [f'PACKED_WORLD_T{t}N{n}' for t, n in ((1, 0), (1, 1), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2),
                                               (4, 0), (4, 1), (4, 2))] + \
       ['POS_TEX', 'PARTICLECLOUD', 'POS_COLOR', 'POS_FP16TEX']
SOURCE = ['position', 'color', 'texcoord0', 'normal', 'tangent', 'texcoord1', 'texcoord2', 'texcoord3',
          'normalTransform0', 'normalTransform1', 'blendWeight']
DXGI = {2: 'R32G32B32A32_FLOAT', 6: 'R32G32B32_FLOAT', 10: 'R16G16B16A16_FLOAT', 13: 'R16G16B16A16_SNORM',
        16: 'R32G32_FLOAT', 24: 'R10G10B10A2_UNORM', 28: 'R8G8B8A8_UNORM', 34: 'R16G16_FLOAT', 35: 'R16G16_UNORM'}


def techniques(p):
    out = []
    for i in range(48):
        name = p.cstr(p.u32(TECH_NAMES + 8 * i)).strip('"')
        out.append((i, name, p.u32(TECH_NAMES + 8 * i + 4)))
    return out


def default_lit_table(p):
    """Emulate R_SetDefaultLitTechTypes: memset 0xFF, then immediate stores into litTechType."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    base = DRAW_METHOD + 6
    mem, regs = bytearray([0xFF] * 0xB0), {}
    code = p.d[p.off(SET_DEFAULT_LIT):p.off(SET_DEFAULT_LIT) + 0x210]
    for ins in Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, SET_DEFAULT_LIT):
        if ins.mnemonic == 'ret':
            break
        m = re.fullmatch(r'(\w+), (0x[0-9a-f]+|\d+)', ins.op_str)
        if ins.mnemonic == 'mov' and m and m[1] in ('dl', 'cl', 'bl', 'al'):
            regs[m[1]] = int(m[2], 0)
        m = re.fullmatch(r'(dword|word|byte) ptr \[(0x[0-9a-f]+)\], (\w+)', ins.op_str)
        if ins.mnemonic == 'mov' and m:
            size = {'dword': 4, 'word': 2, 'byte': 1}[m[1]]
            value = regs[m[3]] if m[3] in regs else int(m[3], 0)
            at = int(m[2], 16) - base
            if 0 <= at < 0xB0:
                mem[at:at + size] = value.to_bytes(size, 'little')
    return [list(mem[11 * s:11 * s + 11]) for s in range(16)]


def list_setup(p):
    names = [p.cstr(p.u32(LIST_NAMES + 4 * i)) for i in range(29)]
    rows = []
    for i in range(23):
        drawlist, base, camera, depth_hack, occlusion = struct.unpack_from('<5i', p.d, p.off(LIST_SETUP + 20 * i))
        rows.append((i, names[drawlist], base, camera, depth_hack, occlusion))
    return names, rows


def stream_info(p):
    table = {}
    for d in range(20):
        row = []
        for s in range(11):
            stream, offset, fmt = p.d[p.off(STREAM_INFO + 33 * d + 3 * s):][:3]
            if stream not in (0xFF, 0xFE):
                row.append((SOURCE[s], stream, offset, DXGI.get(fmt, fmt)))
        table[DECL[d]] = row
    dests = [(p.cstr(p.u32(STREAM_DEST + 8 * i)), p.d[p.off(STREAM_DEST + 8 * i) + 4]) for i in range(20)]
    return table, dests


if __name__ == '__main__':
    p = PE(sys.argv[1])
    print('== technique types (name table 0x%08X)' % TECH_NAMES)
    for i, name, value in techniques(p):
        print('%2d  %-38s 0x%03X' % (i, name, value))
    print('\n== default litTechType[surfType][lightType] (R_SetDefaultLitTechTypes)')
    print('%-32s' % '' + ''.join('%-11s' % l for l in LIGHT))
    for s, row in enumerate(default_lit_table(p)):
        print('%-32s' % SURF[s] + ''.join('%-11s' % ('-' if v == 0xFF else v) for v in row))
    print('\n== draw list setup (s_drawSurfListInfoSetup 0x%08X)' % LIST_SETUP)
    names, rows = list_setup(p)
    for i, name, base, camera, depth_hack, occlusion in rows:
        b = {-1: 'drawMethod.base', -2: 'drawMethod.emissive', 0xFF: '0xFF (own)'}.get(base, base)
        print('%2d  %-36s base %-20s cameraView %d depthHack %d occlusion %d' % (i, name, b, camera, depth_hack, occlusion))
    print('\n== vertex stream formats (stream_source_info_t 0x%08X)' % STREAM_INFO)
    table, dests = stream_info(p)
    for decl, row in table.items():
        print('%-20s ' % decl + '; '.join(f'{n} s{s}+{o} {f}' for n, s, o, f in row))
    print('\n== stream destinations: ' + ', '.join(f'{i}={n}{x}' for i, (n, x) in enumerate(dests)))
