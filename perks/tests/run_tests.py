"""lua2gsc tests: ok/*.lua must compile and pass gsc-tool; fail/*.lua must fail with the message after `-- expect:`.

usage: python run_tests.py <lua2gsc.exe> <gsc-tool.exe>
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
RUNTIME = HERE.parent / "runtime" / "zm_workshop_perks.gsc"


def main() -> int:
    compiler, gsctool = sys.argv[1], sys.argv[2]
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "zm_workshop_perks.gsc"
        oks = sorted((HERE / "ok").glob("*.lua")) + sorted((HERE.parent / "examples").glob("*.lua"))
        r = subprocess.run([compiler, str(RUNTIME), str(out), *map(str, oks)], capture_output=True, text=True)
        if r.returncode:
            print("FAIL compile ok/ + examples/:", r.stderr.strip())
            failures += 1
        else:
            g = subprocess.run([gsctool, "-m", "comp", "-g", "t6", "-s", "pc", out.name], cwd=tmp, capture_output=True, text=True)
            if "compiled t6/" not in g.stdout:
                print("FAIL gsc-tool:", g.stdout.strip(), g.stderr.strip())
                failures += 1
            else:
                print(f"ok   {len(oks)} perks compile and pass gsc-tool")
        for case in sorted((HERE / "fail").glob("*.lua")):
            expect = case.read_text(encoding="utf-8").splitlines()[0].split("-- expect:", 1)[1].strip()
            r = subprocess.run([compiler, str(RUNTIME), str(Path(tmp) / "x.gsc"), str(case)], capture_output=True, text=True)
            if r.returncode == 0 or expect not in r.stderr:
                print(f"FAIL {case.name}: wanted '{expect}', got: {r.stderr.strip() or 'no error'}")
                failures += 1
            else:
                print(f"ok   {case.name}: {r.stderr.strip().split(':', 1)[1]}")
    print("all passed" if not failures else f"{failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
