#!/usr/bin/env python3
"""Report on the shape of a memory file set before a hygiene pass.

Stdlib only, read-only. Reports sizes, section inventory, exact or
near-duplicate lines in the curated file, so the human or agent doing
the pass starts from the file's actual state instead of an impression
of it. It judges nothing; it measures.

Usage:
    memory_audit.py MEMORY.md [more-files...] [--dup-min-len 15]

Exits 1 if any input file cannot be read (the readable files are still
reported); 0 when every file was read.
"""
import argparse
import re
import sys
from collections import Counter

STALE_MARKER = re.compile(r"todo|pending|next week", re.IGNORECASE)
STALE_CAP = 10


def normalized(line):
    # Unicode-aware: casefold, keep Unicode letters and digits (so
    # "Møter" and "Måter" stay distinct), drop punctuation and the
    # underscore (a word character in regex, punctuation for prose),
    # collapse whitespace.
    kept = re.sub(r"[^\w\s]|_", "", line.casefold())
    return " ".join(kept.split())


def main():
    parser = argparse.ArgumentParser(description="Memory file shape report")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--dup-min-len", type=int, default=15,
                        help="Ignore lines shorter than this when hunting "
                             "duplicates (short lines repeat innocently)")
    args = parser.parse_args()

    failures = 0
    global_files = {}
    global_examples = {}
    for path in args.files:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"{path}: cannot read ({e})", file=sys.stderr)
            failures += 1
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
                global_files.setdefault(n, set()).add(path)
                global_examples.setdefault(n, l.strip()[:90])
        dups = [(n, c) for n, c in norms.items() if c > 1]
        if dups:
            print(f"   duplicate lines (normalized): {len(dups)}")
            for n, c in sorted(dups, key=lambda x: -x[1])[:10]:
                print(f"   x{c}: {examples[n]}")
        stale = [(i, l.strip()[:100])
                 for i, l in enumerate(lines, 1) if STALE_MARKER.search(l)]
        if stale:
            print(f"   stale markers: {len(stale)}")
            for lineno, snippet in stale[:STALE_CAP]:
                print(f"   L{lineno}: {snippet}")
            if len(stale) > STALE_CAP:
                print(f"   ... and {len(stale) - STALE_CAP} more")
    cross = [(n, fs) for n, fs in global_files.items() if len(fs) > 1]
    if cross:
        print("== cross-file duplicates (normalized)")
        print(f"   {len(cross)} line(s) appear in more than one file")
        for n, fs in sorted(cross, key=lambda x: -len(x[1]))[:10]:
            print(f"   in {len(fs)} files: {global_examples[n]}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
