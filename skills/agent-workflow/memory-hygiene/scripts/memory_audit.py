#!/usr/bin/env python3
"""Report on the shape of a memory file set before a hygiene pass.

Stdlib only, read-only. Reports sizes, section inventory, and exact or
near-duplicate lines in the curated file, so the human or agent doing
the pass starts from the file's actual state instead of an impression
of it. It judges nothing; it measures.

Usage:
    memory_audit.py MEMORY.md [more-files...] [--dup-min-len 40]
"""
import argparse
import re
import sys
from collections import Counter


def normalized(line):
    return re.sub(r"[^a-z0-9 ]", "", line.lower()).strip()


def main():
    parser = argparse.ArgumentParser(description="Memory file shape report")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--dup-min-len", type=int, default=15,
                        help="Ignore lines shorter than this when hunting "
                             "duplicates (short lines repeat innocently)")
    args = parser.parse_args()

    for path in args.files:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"{path}: cannot read ({e})", file=sys.stderr)
            continue
        lines = text.splitlines()
        sections = []
        in_fence = False
        for l in lines:
            if l.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = re.match(r"^#{1,6}\s+(.+)$", l)
            if m:
                sections.append(m.group(1).strip())
        print(f"== {path}")
        print(f"   {len(lines)} lines, {len(text.split())} words, "
              f"{len(sections)} sections")
        for s in sections:
            print(f"   - {s}")
        norms = Counter()
        examples = {}
        for l in lines:
            n = normalized(l)
            if len(n) >= args.dup_min_len:
                norms[n] += 1
                examples.setdefault(n, l.strip()[:90])
        dups = [(n, c) for n, c in norms.items() if c > 1]
        if dups:
            print(f"   duplicate lines (normalized): {len(dups)}")
            for n, c in sorted(dups, key=lambda x: -x[1])[:10]:
                print(f"   x{c}: {examples[n]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
