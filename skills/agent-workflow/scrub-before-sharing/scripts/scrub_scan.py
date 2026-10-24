#!/usr/bin/env python3
"""Scan a share copy for identifier-shaped leftovers before it goes out.

Stdlib only. This is a net, not a verdict: it flags shapes that usually
mean private data (emails, phone numbers, postal codes, key-shaped
tokens, home paths) so a human can look. Context decides; a README that
documents the scanner will mention some shapes on purpose.

Usage:
    scrub_scan.py <directory> [--extra-regex '<pattern>'] ...

Exits 1 when anything is flagged, 0 when the tree is clean.
"""
import argparse
import os
import re
import sys

PATTERNS = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}\b"),
    "Canadian postal code": re.compile(r"\b[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d\b"),
    "US ZIP code": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
    "api key shape": re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "home path": re.compile(r"(?:/home/|/Users/|[A-Za-z]:[\\/]+Users[\\/]+)[A-Za-z0-9._-]+", re.IGNORECASE),
    "IP address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def main():
    parser = argparse.ArgumentParser(description="Scrub scan for share copies")
    parser.add_argument("directory")
    parser.add_argument("--extra-regex", action="append", default=[],
                        help="Additional pattern to flag (repeatable), e.g. "
                             "a name or handle specific to the owner")
    args = parser.parse_args()
    patterns = dict(PATTERNS)
    for i, extra in enumerate(args.extra_regex):
        patterns[f"extra pattern {i + 1}"] = re.compile(extra)

    self_path = os.path.realpath(__file__)
    hits = 0
    for root, dirs, files in os.walk(args.directory):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in sorted(files):
            path = os.path.join(root, name)
            if os.path.realpath(path) == self_path:
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(lines, 1):
                for label, pattern in patterns.items():
                    for match in pattern.finditer(line):
                        hits += 1
                        print(f"{path}:{lineno}: {label}: {match.group(0)[:60]}")
    print(f"scrub scan: {hits} flagged line(s)", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
