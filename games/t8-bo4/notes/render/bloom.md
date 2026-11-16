# BO4 (T8) bloom chain, read from shader bytecode

<!-- toc -->
## Contents

- [0. Headline](#0-headline)
- [1. Pass list (compute path)](#1-pass-list-compute-path)
- [2. Pass 1: prefilter and downsample (boot 0xcf9bc) **[P]**](#2-pass-1-prefilter-and-downsample-boot-0xcf9bc-p)
- [3. Passes 2-11: separable Gaussian, accumulate coarse to fine **[P]**](#3-passes-2-11-separable-gaussian-accumulate-coarse-to-fine-p)
- [4. Pass 11 tail and the combine](#4-pass-11-tail-and-the-combine)
  - [The two shader-level combines (other output paths)](#the-two-shader-level-combines-other-output-paths)
- [5. Pixel-shader twin of the blur chain **[P]**](#5-pixel-shader-twin-of-the-blur-chain-p)
- [6. Constants: source](#6-constants-source)
- [7. To copy this](#7-to-copy-this)
- [8. Open](#8-open)
<!-- /toc -->

Offline read of the DXBC in `cache\ffx\core_bootstrap.ff.dec` (base zone). Maths only.
Tags: **[P]** proven from bytecode, **[I]** inferred, **[?]** unknown / not found.
Shader ids are `boot 0x<file offset of the DXBC blob>`; listings are in `asm\boot_<offset>.asm`
(made with `..\shaders\d3d.py`). D3D asm: `exp` = 2^x, `log` = log2.

## 0. Headline

- The bloom chain is **compute shaders with no constant buffers at all**. Every number (threshold, clamp,
  kernel weights, level weights) is a literal. There is nothing for a map to tune, so there are **no zm_escape
  bloom values**: zm_escape's bloom is the engine's fixed bloom **[P for "no cbuffer", I for "therefore no per-map data"]**.
  This agrees with `gi\README.txt` (no bloom fields found in the lighting state record).
- Input is the pre-exposed scene HDR buffer (exposure is already multiplied in by every lighting shader, spec
  section 1 item 5), Rec.2020 linear, 1.0 = 100 nits. So the threshold is **after exposure, before tone map** **[P/I]**.
- 5 levels (1/2 .. 1/32), separable Gaussian per level, level weights 1/15, 2/15, 3/15, 4/15, 5/15 (widest level
  heaviest, sum = 1) **[P]**.
- The last pass converts the summed bloom **on its own** through PQ and the same 32^3 display LUT as the scene and
  writes a display-encoded bloom texture **[P]**. The scene output shaders of that path take no bloom texture, so
  the final combine is done by output-merger blend state, which is not visible in bytecode **[?]**.

## 1. Pass list (compute path)

| # | pass | shader | reads | writes |
|---|---|---|---|---|
| 1 | prefilter + 5-level downsample | boot 0xcf9bc (cs, 16x16 groups) | t0 scene HDR | u0..u4 = mips 1..5 |
| 2 | level 5 blur H, radius 11 | boot 0x275844 | mip 5 | temp |
| 3 | level 5 blur V, radius 11, x 5/15 | boot 0xbb59a0 | temp | acc5 |
| 4 | level 4 blur H, radius 9 | boot 0xb72e34 | mip 4 | temp |
| 5 | level 4 blur V, radius 9, x 4/15, + upsampled acc5 | boot 0x26fca4 | temp, acc5 | acc4 |
| 6 | level 3 blur H, radius 7 | boot 0xd3118 | mip 3 | temp |
| 7 | level 3 blur V, radius 7, x 3/15, + acc4 | boot 0x717fbc | temp, acc4 | acc3 |
| 8 | level 2 blur H, radius 5 | boot 0x6d329c | mip 2 | temp |
| 9 | level 2 blur V, radius 5, x 2/15, + acc3 | boot 0xd0fbc | temp, acc3 | acc2 |
| 10 | level 1 blur H, radius 3 | boot 0x6b565c | mip 1 | temp |
| 11 | level 1 blur V, radius 3, x 1/15, + acc2, then unscale, PQ, display LUT | boot 0xd91684 | temp, acc2, t2 = 32^3 LUT | display-encoded bloom |
| 12 | combine with the display-encoded scene | fixed-function blend **[?]** | | |

Order **[P]** for what each shader does; **[I]** for the binding order (which mip each radius is run on). The ends are
proven: 0xbb59a0 is the only V pass with no second texture (chain start), 0xd91684 is the only one with the LUT
(chain end), and the level weights rise 1..5 with the radius.

A pixel-shader twin of the blur chain exists with the same kernels folded into bilinear taps (section 5).

## 2. Pass 1: prefilter and downsample (boot 0xcf9bc) **[P]**

No cbuffer. One 16x16 thread group produces all five mips through group-shared memory.

    uv   = (pixel + 0.5) / size(u0)                 u0 = mip 1; half the source size [I]
    c0   = scene(uv)                                 bilinear
    c1-4 = scene(uv, texel offset (+-1, +-1))        source texels, bilinear
    w_i  = 1 / (1 + Y(c_i))                          Y = dot(c, (0.2627, 0.678, 0.0593))  Rec.2020 luma
    avg  = sum(w_i c_i) / sum(w_i)                   5 taps, luma-weighted (firefly suppression)

    threshold (hue preserving, hard knee):
    L    = Y(avg)
    c    = avg * max(L - 1.5, 1.52588e-5) / (L + 1.52588e-5)

    clamp (soft, on luma, hue preserving):
    m    = Y(c) / 100                                literal weights (0.002627, 0.00678, 0.000593)
    if m > 0.5:  m' = 0.5 + 0.5 * (1 - 1/(1 + 2 (m - 0.5)))   = 1 - 1/(4 m)
                 c  = c * m'/m
    (luma is untouched up to 50 = 5,000 nits, then rolls off to an asymptote of 100 = 10,000 nits)

    store scale (not a tint, undone in pass 11):
    mip1 = c * (85.53421, 220.55641, 19.253632)

    mip2 = 2x2 box average of mip1   (x 0.25)
    mip3 = 2x2 box of mip2,  mip4 = 2x2 box of mip3,  mip5 = 2x2 box of mip4

- Threshold 1.5 = 150 nits in exposed scene units. There is **no knee width**: the subtraction `L - 1.5` gives a
  linear ramp from zero, which is itself soft. Evidence: `add r1.xy, r0.wwww, l(-1.5, 0.000015)`, `max`, `rcp`, `mul`.
- Space: exposed, linear, Rec.2020 primaries, before any tone map / LUT.
- The per-channel scale is about 325 x the luma weights (325.6, 325.3, 324.7); with the luma clamp it keeps every
  channel below about 32,500 **[I: range normalisation for an R11G11B10 float target]**. It cancels exactly with pass 11,
  so a port can skip both.

## 3. Passes 2-11: separable Gaussian, accumulate coarse to fine **[P]**

Each level k (1 = finest, 5 = coarsest) has radius r = 2k + 1 texels of its own mip.

    H pass:  T(x)   = norm_h * sum_{n=-r..r} exp(-n^2 / (2 sh^2)) * mip_k(x + n)       sh = r / 3
    V pass:  acc_k  = up(acc_{k+1}) + (k/15) * norm_v * sum_{n=-r..r} exp(-n^2 / (2 sv^2)) * T(y + n)   sv = r / 4

`up()` is one bilinear sample of the coarser accumulator at the same uv (no extra filter). acc_6 = 0.
Taps are point samples at texel centres (the shader fetches a 64-wide row plus 2r into group-shared memory).
The H and V sigmas really differ (edge weight e^-4.5 for H, e^-8 for V).

| level | mip | r | H sigma | H norm (literal) | V sigma | V norm | V literal = (k/15) x norm | level weight |
|---|---|---|---|---|---|---|---|---|
| 1 | 1/2 | 3 | 1.0 | 0.399050 | 0.75 | 0.531908 | 0.035460 | 1/15 |
| 2 | 1/4 | 5 | 1.6667 | 0.239559 | 1.25 | 0.319156 | 0.042554 | 2/15 |
| 3 | 1/8 | 7 | 2.3333 | 0.171181 | 1.75 | 0.227970 | 0.045594 | 3/15 |
| 4 | 1/16 | 9 | 3.0 | 0.133176 | 2.25 | 0.177312 | 0.047283 | 4/15 |
| 5 | 1/32 | 11 | 3.6667 | 0.108983 | 2.75 | 0.145074 | 0.048358 | 5/15 |

The sigmas were recovered from the literal weights (e.g. level 1 H: 1, 0.606531, 0.135335, 0.011109; level 1 V:
1, 0.411112, 0.028565, 0.000335) and the level weights by dividing the V literal by the kernel norm: they come out
1.0000, 2.0000, 3.0000, 4.0000, 5.0000 fifteenths.

Result:

    bloom = sum_{k=1..5} (k/15) * G_k(mip_k)         weights sum to 1: energy preserving, no gain, no tint

No per-level tint, no lens dirt texture, no streak or flare pass: the chain's only inputs are the mips, the
accumulators and the LUT **[P]**. Lens flares are not part of the post chain (not looked for elsewhere **[?]**).

## 4. Pass 11 tail and the combine

End of boot 0xd91684 (and of its pixel-shader twin boot 0x141feb4) **[P]**:

    b   = acc_1 * (1.1691228e-4, 4.533988e-5, 5.193825e-4)      = 0.01 / store scale: true bloom / 100
    p   = PQ(b)                                                  ST 2084, 1.0 = 10,000 nits (no saturate: b <= 1 by the clamp)
    out = LUT32(p * 31/32 + 1/64)                                the same PQ-indexed 32^3 display LUT as the scene

So bloom is display-mapped separately from the scene, through the same LUT (which holds the tone map / 2020->709 /
OETF / grade, spec 8b), and stored display-encoded. The scene output shaders of this path (boot 0x1442628,
0x1358068, 0x14762dc, 0x130a578, 0x1404220) sample scene + LUT (+ dither noise) and **no bloom texture** **[P]**.
The bloom texture is therefore composited by drawing it with a blend state **[I]**; whether that state is additive
(ONE, ONE) or screen (INV_DEST_COLOR, ONE) is not in the bytecode **[?]**. Screen is the likelier: both shader-level
combines found in the zone are screen blends (below).

Order in this path: exposure -> [scene: PQ -> LUT] and [bloom: threshold -> blur -> PQ -> LUT] -> combine -> dither.
Bloom sits **after** the tone map, the 2020->709 conversion, the OETF and the LUT, because all of those are inside the LUT.

### The two shader-level combines (other output paths)

A scan of all 719 engine shaders for the pattern `add r, a, b` / `mad r, -a, b, r` finds exactly these:

| shader | formula | position |
|---|---|---|
| boot 0x11f43f0, 0x130d950, 0x141a41c, 0x1441078 (film-curve path, spec 8a) | `e + b - e*b`, b = sat(tex / 256) | after film curve, 2020->709 and BT.709 OETF; **before** the overlay add and the 32^3 LUT |
| boot 0x1440530 | `s + b - s*b`, s = softclip(sceneA + sceneB) / 100, b = sat(tex / 100) | in linear 10,000-nit-normalised space, **before** PQ and the LUT |

0x1440530 soft clip: per channel, if x > 87.5 then x/100 becomes `0.875 + 0.125 * (1 - e^(-0.08 (x - 87.5)))`
(literals -0.115416 and 10.098866 are 0.08 and 7.0 times 1.442695), applied when max channel > 87.5 **[P]**.

So the existing spec line "bloom is a screen blend of bloom/256 after the BT.709 OETF" is a correct read of the
film-curve shader **[P]**, and it does sit after tone map, 2020->709 and OETF and before the LUT. But the texture
those shaders divide by 256 (and the one 0x1440530 divides by 100) must be in plain linear units, and the chain
above never outputs that: its only end is LUT-encoded. The producer of those textures was not found, so calling
that input "bloom" is **[I]** and whether these paths ship with the chain above is **[?]**.

## 5. Pixel-shader twin of the blur chain **[P]**

Same Gaussians, folded into bilinear taps (offsets in texels along the blur axis, v1.x = texel size).
Fitted per-texel sigmas match section 3 to 3 decimals.

| level | H shader | V shader | V extra |
|---|---|---|---|
| 1 | boot 0x11f505c (2 taps, see note) | boot 0x141feb4 (4 taps) | + acc, x 0.066667, unscale, PQ, LUT |
| 2 | boot 0x11e3a10 (6 taps) | boot 0x11df914 (6 taps) | + acc, x 0.133333 |
| 3 | boot 0xfb4500 (8) | boot 0x11f9510 (8) | + acc, x 0.2 |
| 4 | boot 0x11e1f04 (10) | boot 0x11f2da8 (10) | + acc, x 0.266667 |
| 5 | boot 0xf5f214 (12) | boot 0x11fba04 (12) | x 0.333333, no acc |

Taps (offset: weight, mirrored about 0, weights sum to 1):

    L1 V: 0.451220: 0.484627   2.011607: 0.015373
    L2 H: 0.625544: 0.319877   2.289051: 0.164015   4.165205: 0.016109
    L2 V: 0.592219: 0.391333   2.167982: 0.106653   4.053151: 0.002014
    L3 H: 0.645956: 0.241751   2.387179: 0.193457   4.304379: 0.056615   6.232566: 0.008177
    L3 V: 0.629456: 0.307615   2.306544: 0.171095   4.187036: 0.020574   6.106934: 0.000715
    L4 H: 0.654209: 0.192567   2.430999: 0.187414   4.377541: 0.087958   6.326904: 0.026777   8.280004: 0.005284
    L4 V: 0.644370: 0.249292   2.378992: 0.192339   4.291339: 0.051524   6.216878: 0.006468   8.157227: 0.000378
    L5 H: 0.658352: 0.159496   2.453646: 0.171901   4.417095: 0.103119   6.381433: 0.046187   8.347005: 0.015444   10.314106: 0.003854
    L5 V: 0.651816: 0.208329   2.418100: 0.191375   4.355479: 0.078151   6.297443: 0.019108   8.245276: 0.002793   10.199658: 0.000244

Note: L1 H (0x11f505c) samples only the negative side (offsets -0.548137: 0.883123, -2.075858: 0.116877). Unfolded
that is the sigma 1.0 radius-3 kernel with both halves stacked on one side **[P]**; why is **[?]**. Use the
symmetric kernel from section 3.

A pixel-shader prefilter with the store-scale constants was not found; 0xcf9bc is the only shader carrying them **[P]**.

## 6. Constants: source

| constant | value | source |
|---|---|---|
| luma weights | 0.2627, 0.678, 0.0593 | literal |
| threshold | 1.5 (exposed units, = 150 nits) | literal |
| epsilon | 1.52588e-5 (2^-16) | literal |
| clamp start / asymptote | luma 50 / 100 | literal |
| store scale / unscale | 85.53421, 220.55641, 19.253632 / 1.1691228e-4, 4.533988e-5, 5.193825e-4 | literal |
| kernel weights, norms | section 3 | literal |
| level weights | k/15 | literal (folded into the V norm) |
| exposure | cb2[110].y, applied by the lighting shaders upstream, not by the bloom chain | cbuffer (spec section 7) |
| display LUT | 32^3 texture, t2 of 0xd91684 | texture |

No cb slot is declared by any chain shader, so there is no bloom strength / threshold / tint to read from the
zm_escape lighting state.

## 7. To copy this

Inputs: the exposed linear HDR scene (Rec.2020, 1.0 = 100 nits), and the display transform used for the scene.

1. Half-res prefilter: 5 bilinear taps (centre and the four diagonals at one source texel), weights 1/(1 + luma),
   normalised. Then `c *= max(L - 1.5, eps) / (L + eps)`. Then if luma > 50: scale so luma = 100 - 2500/luma.
2. Four more mips by 2x2 box: 1/4, 1/8, 1/16, 1/32.
3. Per level k = 1..5 (finest to coarsest): Gaussian of radius r = 2k + 1 texels, horizontal sigma r/3, vertical sigma r/4.
4. Accumulate from coarsest to finest: `acc_k = bilinear_up(acc_{k+1}) + (k/15) * blur_k`. Weights 1/15, 2/15, 3/15,
   4/15, 5/15. No tint, no dirt, no strength control.
5. Run the result through the same display transform as the scene, on its own (bloom/100 -> PQ -> display LUT in
   the game; in a film-curve engine: curve -> 2020->709 -> OETF -> LUT).
6. Combine in display-encoded space: `out = scene + bloom - scene * bloom` **[I]** (plain add is the alternative; they
   differ only where both are bright). Then dither.

If the engine uses the film-curve path of spec 8a as written, the shader-proven position is: screen blend after the
OETF and before the grade LUT; feed it this chain's linear bloom mapped through the same curve + matrix + OETF.

## 8. Open

- Blend state of the final combine (add vs screen) **[?]**.
- Which path (this chain, or the /256 and /100 shader-level combines) a given PC setting uses; producer of the
  linear-unit texture those two read **[?]**.
- Mip sizes are inferred from the shader structure (u0 half of t0), not from render-target descriptions **[I]**.
- Only the base core_bootstrap zone was read; a patched core_bootstrap was not dumped.
- `asm\` also holds candidates that were ruled out (depth-of-field, fog composite, sharpen, exposure histogram:
  0x1269198, 0x132a948, 0x1317fe0, 0x1317504, 0x11e43a0, 0x14103ec, 0x26dc8c, 0x26b388 and other small blurs).
