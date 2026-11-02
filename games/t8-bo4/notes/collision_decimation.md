# Collision decimation: passes, measured results, caveats

Offline engine that lowers the unique collision-plane count of a ported BO4 clip.json so BO3 `cod2map64.exe`
stays under `MAX_MAP_PLANES` (131,072). Operates only on world **brushes**; tris pass through untouched (they
become terrain patches, which do not count toward the plane cap). Output is a clip.json consumed unchanged by
`clip_brushes.py`. Everything below is **built and stub-tested offline, not installed in game.**

## The budget gauge (`plane_count.py`)

cod2map keeps one global table of every unique plane a brush side references, and (idTech lineage, matching this
project's own `bo4_recon\count_map_planes.py` note "x2 with flips") stores each geometric plane together with its
flip, so the table grows by **two** per new undirected plane. The gauge therefore:

- canonicalises each plane to a unit normal with a **consistent sign** (a plane and its opposite collapse to one
  key), quantised to ~0.001 on the normal and ~0.01 on the distance (both `--neps`/`--deps` tunable);
- reports `unique` (distinct undirected planes), `table = unique*2` (compare THIS to 131,072), and directed-unique
  for reference;
- counts exactly what cod2map receives: brushes `clip_brushes.py` would emit (same skip rules) plus the 5-plane
  prisms it makes from tris.

**Inference, not verified:** that the real BO3 cod2map table is `unique*2`. If it is `unique*1` (opposite signs
stored once) or `directed` (no sign merge), the budget is even looser. The **measurement that settles it** is a
live probe (below). Either way the engine lowers `unique`, so the reduction stands under any interpretation.

### Measured baselines (unique undirected / table x2 vs cap 131,072)

| file | brushes | prisms | unique | table | vs cap |
|---|---|---|---|---|---|
| `bod_clip.json` (the main test input) | 12,817 | 0 | 49,823 | 99,646 | 76% — already under |
| `shell_plus_bod_clip.json` (combined island) | 27,725 | 18,796 | 123,187 | 246,374 | 187% — **over** |
| &nbsp;&nbsp;↳ its brush-only half | 27,725 | — | 64,129 | 128,258 | 98% — at the edge |

So `bod_clip.json` alone does **not** blow the cap on any metric (measured). The island blows it when regions are
combined; even brush-only the combined map sits at ~98% of the cap, and the inline prisms push the whole file to
187%. In the real pipeline those prisms are terrain and route to `--terrain` as patches (uncounted); the brush half
is this engine's job.

## Where the planes come from (profiled on `bod_clip.json`)

- 49,823 unique planes; **35,755 (72%) are private** — referenced by exactly one brush, so removable by merge/drop.
- 27,635 axial / 22,188 oblique; 16,736 of the private planes are oblique.
- 10,579 of 12,817 brushes are thin slivers (smallest axis ≤32u); only 3,213 are pure axis-aligned boxes.

This is imported per-surface collision: thousands of tiny oblique slivers, each carrying private bevel planes. A
pure box-run merge (the "split wall → one brush" idea) barely helps here (3,213 boxes merge to 3,131). The lever is
turning near-box slivers into clean AABBs, then merging those.

## Passes (`decimate_clip.py`)

0. **redundant + cap** — rebuild each brush as its 6 axial AABB planes plus only the oblique planes a vertex
   supports; drop import-noise bevels. Any brush still over 45 sides (Radiant assert) is replaced by its AABB.
   *Lossless for the solid (dropping an unsupported plane only enlarges the polytope); re-tightens the AABB.*
1. **contain** — drop a brush whose AABB lies wholly inside another same-class brush's solid (overlapping import).
   *Lossless: the volume is still covered by the container.*
2. **boxify** — replace a brush with its AABB when the box pokes ≤ `--tol` past the brush, **and** it is not a
   walkable slope rising more than `--floor-tol`. *Adds a little solid in shaved corners; floor-safe (see caveats).*
3. **merge** — fuse axis-aligned boxes of equal cross-section, contents and face adjacency into one box.
   *Exact: identical occupied volume.*
4. **cluster** *(`--cluster`, off by default)* — collapse each dense grid cell of leftover oblique brushes to one
   AABB. *Loses concavity; only runs when a cell's brushes are tight and target is still missed.*

Passes 2–3 iterate with `--tol` doubling from `--tol` up to `--max-tol` until `table ≤ --target-planes` or the
ceiling is hit. `--target-planes` is the **table** value (default 120,000, headroom under 131,072).

### Measured results on `bod_clip.json` (unique 49,823 → …)

| run | unique | table | reduction | notes |
|---|---|---|---|---|
| default (`--target 120000 --tol 8 --max-tol 64`) | 42,768 | 85,536 | **14.2%** | target met at tol 8; stops early |
| forced `--target 40000` (default `--max-tol 64`) | 35,092 | 70,184 | **29.6%** | escalates to tol 64 |
| forced `--target 40000 --max-tol 1024` | 33,458 | 66,916 | 32.8% | diminishing returns past tol 64 |
| `--cluster --target 40000` | 30,260 | 60,520 | 39.3% | aggressive; concavity lost in dense cells |

Per-pass (default): redundant+contain drops 701 contained brushes and caps 2 over-45 brushes (12,817→12,116);
boxify(tol 8) boxifies 2,831 and merge fuses 274 (→11,842), unique 49,823→42,768.

On `shell_plus_bod_clip.json` the **brush-only** half goes 64,129 → 42,489 unique (−34%), brush-only table
128,258 → 84,978 (from ~98% of cap to ~65%). The file as a whole stays over cap only because of its inline prisms,
which are terrain and belong in `--terrain` patches, not in the brush budget.

## Correctness checks (`check_decimate.py`, 14/14 pass)

- Emitter contract on every emitted brush: first six planes axial in order −X +X −Y +Y −Z +Z, ≤45 sides, integer
  contents, verts inside planes.
- Consumer stub: `clip_brushes.brushes()` loads the output and emits well-formed `{ }` blocks.
- Plane-table stub: output table ≤ input table and ≤ cap.
- **Containment: 0 of 6,000 sampled interior points of the original lost** — no collision was removed, the
  decimated solid is a superset.
- Failure paths: empty input, a degenerate-plane brush (emitter-skipped), an over-45-side brush (capped), and
  tris/tri_contents/tri_materials pass-through with contents preserved.

## Caveats — what fidelity is lost

- **Boxify adds solid.** ~3.0% of sampled decimated-interior points were empty before (shaved concave corners and
  sliver thickening now filled). It never opens a hole: collision is a strict superset of the original.
- **Floors/ramps.** Boxify skips any brush with a non-axial walkable top rising more than `--floor-tol` (default
  8u), so real ramps are preserved (2,621 ramp brushes in → 2,542 kept; the ~3% boxed are near-flat slivers whose
  stand height moves ≤8u, under the engine step height). **Not verified in game** that 8u is the right floor
  tolerance — a live walk probe settles it.
- **`--cluster` loses concavity** inside collapsed cells: a doorway or recess within one 128u cell of oblique
  detail can fill. Off by default; use only when a target cannot be met otherwise, and walk-test the result.
- **Thin gaps.** Boxing a sliver thickens it by up to `--tol`; two slivers `--tol` apart could close a gap narrower
  than that. Default `--tol` 8u keeps this below player width.
- **Plane-table model is an inference** (see gauge section); the live probe below confirms it.

## Performance (measured, offline)

`bod_clip.json` default ~18s; `shell_plus_bod_clip.json` (28k brushes, escalating) ~48s. Cost is dominated by
re-counting the plane table each pass (writes a temp json and reparses). Acceptable for an offline rebuild step.

## Live probes for the game worker (nothing below is verified yet)

1. **Does it compile under the cap?** Run `plane_count.py` on the decimated clip to get the predicted table, then
   `make_shell_map.py --clip <decimated>.json` + `build_usermap.ps1`. Expect cod2map to finish without the
   `MAX_MAP_PLANES` assert. If it still asserts, read the plane count cod2map prints and compare to our gauge —
   that number settles the x1/x2 table question.
2. **Walkability unchanged.** Spawn at the BoD start and walk the decimated interior. Expect the same reachable
   floor as the undecimated build; watch for new 8u steps on former ramps and for any thin doorway that closed.
3. **Nothing fell through.** Expect no new spots where the player drops through former collision (containment test
   says this cannot happen, but confirm in game).
