#!/usr/bin/env python3
"""Run every regression suite in this folder and report one verdict.

Each suite is stdlib-only, uses synthetic fixtures, and needs no network
or browser. Run from anywhere:

    python3 tests/run_all.py

Exit code 0 only when every suite passes.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "finance_checks.py",
    "scrub_memory_checks.py",
    "migration_models.py",
    "smite_checks.py",
    "amazon_checks.py",
]


def main() -> int:
    failed = []
    for name in SUITES:
        path = os.path.join(HERE, name)
        print(f"\n===== {name} =====", flush=True)
        result = subprocess.run([sys.executable, path])
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"----- {name}: {status} -----", flush=True)
        if result.returncode != 0:
            failed.append(name)
    print("\n===== summary =====")
    for name in SUITES:
        print(f"{name}: {'FAIL' if name in failed else 'PASS'}")
    if failed:
        print(f"{len(failed)} suite(s) failed: {', '.join(failed)}")
        return 1
    print("all suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
