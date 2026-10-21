"""Reference writer for the minimal W2BSP001 render world (version 1) in EMITTER_SPEC.md.
Self-test: python emit_gfx_v1.py <known-good gfx.bin> <out.gfx.bin> re-emits it as v1 and reads it back."""
import struct
import sys
from pathlib import Path

# external dependency: B2W / BO1MapConverter (not included) — https://github.com/Ticass/B2W
sys.path.insert(0, r"PATH/TO/BO1MapConverter/b2w_bo1/src")  # set this to your own path


def pack_unit(n):
    scale = (255 + 192.0) / 32385.0
    return struct.unpack("<I", bytes([max(0, min(255, round(c / scale + 127))) for c in n] + [255]))[0]


def pack_colour(rgba):
    r, g, b, a = (max(0, min(255, round(c * 255))) for c in rgba)
    return (a << 24) | (r << 16) | (g << 8) | b


def string(s):
    data = s.encode("utf-8")
    return struct.pack("<I", len(data)) + data


def write_gfx_v1(path, name, base_name, skybox, vertices, indices, surfaces):
    """vertices: (xyz, rgba, uv, normal); indices: surface-local u16; surfaces: dicts with
    first_vertex, vertex_count, triangle_count, base_index, material, mins, maxs."""
    out = [b"W2BSP001", struct.pack("<IIIII", 1, len(vertices), len(indices), len(surfaces), 0),
           string(name), string(base_name), string(skybox)]
    for xyz, rgba, uv, normal in vertices:
        out.append(struct.pack("<3fI2f2fIIf", *xyz, pack_colour(rgba), *uv, 0.0, 0.0, pack_unit(normal), pack_unit(normal), 1.0))
    out.append(struct.pack(f"<{len(indices)}H", *indices))
    for s in surfaces:
        out += [struct.pack("<IHHI", s["first_vertex"], s["vertex_count"], s["triangle_count"], s["base_index"]),
                string(s["material"]), struct.pack("<4B6f", 0, 0, 0, 0, *s["mins"], *s["maxs"])]
    Path(path).write_bytes(b"".join(out))


if __name__ == "__main__":
    from waw2bo2.world import read_gfx_world
    w = read_gfx_world(Path(sys.argv[1]))
    write_gfx_v1(sys.argv[2], w.name, w.base_name, w.skybox_model,
                 [(v.xyz, v.color, v.uv, v.normal) for v in w.vertices], w.indices,
                 [{"first_vertex": s.first_vertex, "vertex_count": s.vertex_count, "triangle_count": s.triangle_count,
                   "base_index": s.base_index, "material": s.material, "mins": s.mins, "maxs": s.maxs} for s in w.surfaces])
    back = read_gfx_world(Path(sys.argv[2]))
    worst = max(max(abs(a - b) for a, b in zip(p.normal, q.normal)) for p, q in zip(w.vertices, back.vertices))
    same = (back.indices == w.indices and [v.xyz for v in back.vertices] == [v.xyz for v in w.vertices]
            and [(s.material, s.first_vertex, s.triangle_count) for s in back.surfaces]
            == [(s.material, s.first_vertex, s.triangle_count) for s in w.surfaces])
    print(f"v1 round-trip: geometry identical={same}, max normal error={worst:.4f}, {len(back.surfaces)} surfaces")
