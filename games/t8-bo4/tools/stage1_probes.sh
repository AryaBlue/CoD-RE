#!/usr/bin/env bash
# Stage 1 (decompressed zm_escape zone) — exact repro + the unblock probe.
# OFFLINE only. Never launches BO4. Run with BO4/Greyhound/cod2map CLOSED.
set -u
ACTS="PATH/TO/acts/bin"  # set this to your own path
P="PATH/TO/bo4_install"   # BO4 install (CASC, 142GB)
cd "$ACTS"

# --- FACT A: local CASC opens for LISTING only (casctest), forward slashes fine ---
# Lists zone\zm_escape.ff etc. Proof the local CASC is readable offline.
# ./acts.exe casctest "$P"

# --- FACT B: the fastfile DUMPER cannot open the LOCAL casc offline ---
# Any value WITHOUT ':' is treated as a local loose-ff dir (prints help, no casc).
# Any value WITH ':product' triggers CASCLib ONLINE open -> 0x2 offline (CDN).
# ./acts.exe fastfile -G "$P" -C "$P"            -r bo4 -d -w "*zm_escape*" -o out   # -> help, no dump
# ./acts.exe fastfile        -C "$P:tpr/b04"     -r bo4 -d -w "*zm_escape*" -o out   # -> Can't open casc 0x2

# --- FACT C: Oodle name ACTS probes is oo2core_8_win64; install ships only _6. ---
# OodleLZ_Decompress is export-stable across majors, so exposing _6 as _8 works:
cp -n deps/oo2core_6_win64.dll ./oo2core_8_win64.dll
cp -n deps/oo2core_6_win64.dll deps/oo2core_8_win64.dll

# --- FACT D: fftest DECRYPTS+DECOMPRESSES a loose BO4 .ff OFFLINE, NO module. ---
# Proof the TAff0000 AES+Oodle decompress works offline (keys bundled in ACTS).
# It persists scriptparsetree only (to ./scriptparsetree_t8ff), NOT the raw blob.
./acts.exe fftest "$P/LPC/core_playlists_tu23_639_cf92ecf4a75d3f79.ff"

# --- FACT E: the RAW decompressed blob (-d / --dumpCompiledZone) needs the MODULE. ---
# The bo4 handler ALWAYS loads deps\BlackOps4_dump.exe at init, every flag combo.
./acts.exe fastfile -r bo4 -d --noAssetDump -o out "$P/LPC/core_playlists_tu23_639_cf92ecf4a75d3f79.ff"

# --- FACT F: game_dump makes the module but STATICALLY = packed, UNUSABLE. ---
# Produces deps\BlackOps4_dump.exe == SizeOfImage expansion of the Arxan-packed exe
# (.text entropy 7.995, dual .text + .interpr VM section) -> ACTS "Can't load".
# ./acts.exe game_dump bo4 "$P"

# ========================================================================
# UNBLOCK PROBE (GAME WORKER, needs BO4 running+unpacked; NOT me/offline):
#  1. User loads BO4 to any zombies map (real input; see bo4-launch.md).
#  2. With BlackOps4.exe unpacked in memory, produce a RUNTIME dump of the
#     process image into:  <ACTS>/bin/deps/BlackOps4_dump.exe
#     (external dumper: PE-sieve / Scylla / x64dbg Scylla; rebuild imports;
#      must be the DECRYPTED .text, not the on-disk file.)
#  3. Close BO4. Expected-before: step E above throws "Can't load ...".
#     Expected-after: step E prints "Decompressed 0x.. from 0x.. blocks" and
#     writes files to out\ (the decompressed zone / assets).
#  4. Then the OFFLINE blob dump (no game) is:
#     ./acts.exe fastfile -C "$P" -r bo4 -d --dumpCompiledZone -w "*zm_escape*" -o ZONE
#     (if -C local casc still refuses, first copy zone\zm_escape.ff loose via
#      the running game's own cache / a casc extractor, then pass the .ff path.)
#  Failure signal: still "Can't load" (dump was static/packed, not runtime).
