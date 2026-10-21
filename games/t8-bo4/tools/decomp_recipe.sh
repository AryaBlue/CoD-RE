#!/usr/bin/env bash
# b2: decompress an extracted BO4 TAff0000 fastfile -> raw asset stream, OFFLINE, module-free.
# Prereq: oo2core exposed as oo2core_8_win64.dll in the ACTS bin (see ../stage1_zone/stage1_probes.sh).
# KEY: omit `-r bo4` so ACTS uses its flexible/generic reader (T78FFDecompressor) and does NOT
# load deps\BlackOps4_dump.exe. With `-r bo4` it loads the (unusable, packed) module and aborts.
ACTS="PATH/TO/acts/bin"  # set this to your own path
cd "$ACTS"
IN="PATH/TO/zm_escape.ff"  # set this to your own path
OUT="PATH/TO/decomp_out"  # set this to your own path
./acts.exe fastfile -d "$IN" -o "$OUT"   # -> $OUT/zm_escape.ff.dec  (~487 MB, T8 linked asset stream)
# Handles AES-decrypt (key derived by ACTS; zm_escape has NO named key in keys_aes.csv) + Oodle.
# Verified: fftest reports Decompressed 0x1e715cb4 from 0x7b1 blocks; .dec = 510,745,780 bytes.
