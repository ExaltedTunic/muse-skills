#!/usr/bin/env python3
"""Scan a share copy for identifier-shaped leftovers before it goes out.

Stdlib only. This is a net, not a verdict: it flags shapes that usually
mean private data (emails, phone numbers, postal codes, key-shaped
tokens, home paths) so a human can look. Context decides; a README that
documents the scanner will mention some shapes on purpose.

Usage:
    scrub_scan.py <directory-or-file> [--extra-regex '<pattern>'] ...

Exits 1 when anything is flagged, 0 when the target is clean, and 2
when the target does not exist.
"""
import argparse
import os
import re
import sys

PATTERNS = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}\b"),
    # The unspaced form must be uppercase: a lowercase letter-digit
    # alternation (a1b2c3, f4c2d5) is far more likely a hex fragment or
    # short ID than a postal code. The spaced form is unambiguous, so
    # it stays case-insensitive.
    "Canadian postal code": re.compile(
        r"\b(?:[A-Z]\d[A-Z]\d[A-Z]\d|[A-Za-z]\d[A-Za-z][ -]\d[A-Za-z]\d)\b"),
    # The lookbehind keeps keyword values (timeout=90000) and other
    # number runs that are part of a larger token from flagging.
    "US ZIP code": re.compile(r"(?<![=0-9A-Za-z_.-])\b\d{5}(?:-\d{4})?\b"),
    "api key shape": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{22,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    # The lookbehind requires the path to start a token, so prose like
    # "arrows/Home/End" (keyboard keys) does not flag as a home path.
    "home path": re.compile(r"(?<![A-Za-z0-9_/-])(?:/home/|/Users/|[A-Za-z]:[\\/]+Users[\\/]+)[A-Za-z0-9._-]+", re.IGNORECASE),
    # A dotted quad right after "v" or "version " is a version string
    # (v1.2.3.4), not an address; other quads still flag.
    "IP address": re.compile(r"(?<![\w.vV])(?<!version )(?<!Version )(?:\d{1,3}\.){3}\d{1,3}\b"),
}

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def iter_files(target):
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            yield os.path.join(root, name)


def main():
    parser = argparse.ArgumentParser(description="Scrub scan for share copies")
    parser.add_argument("directory",
                        help="Directory to scan, or a single file")
    parser.add_argument("--extra-regex", action="append", default=[],
                        help="Additional pattern to flag (repeatable), e.g. "
                             "a name or handle specific to the owner")
    args = parser.parse_args()
    if not os.path.exists(args.directory):
        print(f"scrub scan: no such file or directory: {args.directory}",
              file=sys.stderr)
        return 2
    patterns = dict(PATTERNS)
    for i, extra in enumerate(args.extra_regex):
        patterns[f"extra pattern {i + 1}"] = re.compile(extra)

    self_path = os.path.realpath(__file__)
    flagged_lines = 0
    files_scanned = 0
    for path in iter_files(args.directory):
        if os.path.realpath(path) == self_path:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        files_scanned += 1
        for lineno, line in enumerate(lines, 1):
            line_flagged = False
            for label, pattern in patterns.items():
                for match in pattern.finditer(line):
                    line_flagged = True
                    print(f"{path}:{lineno}: {label}: {match.group(0)[:60]}")
            if line_flagged:
                flagged_lines += 1
    print(f"scrub scan: {flagged_lines} flagged line(s), "
          f"{files_scanned} file(s) scanned", file=sys.stderr)
    return 1 if flagged_lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
