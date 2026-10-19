"""Prefix each line of stdin with seconds since start: python stamp.py < log (for profiling builds)."""
import sys
import time

start = time.monotonic()
for line in sys.stdin:
    sys.stdout.write(f"{time.monotonic() - start:8.1f} {line}")
    sys.stdout.flush()
