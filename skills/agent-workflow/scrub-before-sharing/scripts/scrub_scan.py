#!/usr/bin/env python3
"""Scan a share copy for identifier-shaped leftovers before it goes out.

Stdlib only. This is a net, not a verdict: it flags shapes that usually
mean private data (emails, phone numbers, postal codes, key-shaped
tokens, home paths) so a human can look. Context decides; a README that
documents the scanner will mention some shapes on purpose.

Findings are reported as path:line:label plus a short SHA-256
fingerprint of the matched text. The matched text itself is never
printed: a scan meant to prevent disclosure must not become another
copy of the secret in tool output or logs. Paths are held to the same
rule: every path the scanner prints (findings, exclusions, unreadable
listings, skipped directories) is first passed through the pattern
set, and any matched substring is replaced by its fingerprint, so an
identifier living in a filename is not disclosed by the report of it.

Coverage is part of the verdict. Every run prints a coverage line
(enumerated / scanned / archives and members / metadata inspected /
excluded / skipped / unreadable). Content the scanner could not read
(undecodable bytes, OS errors, inaccessible directories, corrupt
archives) is listed by path and makes the verdict incomplete rather
than clean. Archives (.zip, .tar, .tar.gz/.tgz and other tar variants)
are opened and their text members scanned with the same patterns.
Names are inspected as well as contents: each file's root-relative
path, archive member names, and tar link targets are run through the
same patterns, and non-regular archive members (links, directories,
devices) are counted as metadata inspected, never skipped silently.
Directories on the skip list (.git, .venv, venv, __pycache__,
node_modules) are not content-scanned, but they are never invisible:
the files inside each one are counted and the directory is listed by
name on the coverage report as skipped. The scanner's own source is
excluded explicitly (it legitimately contains the pattern shapes) and
reported as excluded; verify it separately. Deliberately non-text
artifacts can be excluded via a `.scrub-allowlist` file in the scanned
root, one glob per line (matched against file name and root-relative
path); allowlisted files are counted and named, never silently
skipped.

Usage:
    scrub_scan.py <directory-or-file> [--extra-regex '<pattern>'] ...

Exit codes:
    0  clean: everything enumerated was inspected, nothing flagged
    1  findings: at least one pattern matched in inspected content
    2  usage error: the target does not exist
    3  incomplete: some content could not be inspected (unreadable
       files, inaccessible directories, corrupt archives, unreadable
       archive members); the affected paths are listed
Exit 3 takes precedence over 1: a run with both findings and
uninspected content reports both but exits 3.
"""
import argparse
import fnmatch
import hashlib
import os
import re
import sys
import tarfile
import zipfile

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
ALLOWLIST_NAME = ".scrub-allowlist"
ZIP_EXTS = {".zip"}
TAR_EXTS = {".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"}


def archive_kind(path):
    lower = path.lower()
    for ext in TAR_EXTS:
        if lower.endswith(ext):
            return "tar"
    if os.path.splitext(lower)[1] in ZIP_EXTS:
        return "zip"
    return None


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


EMAIL_LABEL = "email address"
# The email pattern is quadratic on long non-matching runs (its greedy
# local part is retried at every start position). Bound the work:
# tokens without "@" cannot contain an address and are skipped, short
# tokens are scanned whole, and longer tokens are scanned in bounded
# overlapping chunks so an address straddling a chunk boundary is
# still seen whole in at least one chunk.
EMAIL_TOKEN_CAP = 1024
EMAIL_CHUNK_OVERLAP = 256


def iter_pattern_matches(label, pattern, text):
    """Yield (start, end, matched_text) for one pattern over text.

    Every pattern except the email pattern runs directly. The email
    pattern only ever runs over whitespace-delimited tokens that
    contain "@", in bounded pieces (see above), so a pathological
    line costs linear-ish time instead of quadratic.
    """
    if label != EMAIL_LABEL:
        for m in pattern.finditer(text):
            yield m.start(), m.end(), m.group(0)
        return
    seen = set()
    for tok in re.finditer(r"\S+", text):
        token = tok.group(0)
        if "@" not in token:
            continue
        base = tok.start()
        if len(token) <= EMAIL_TOKEN_CAP:
            spans = [(base + m.start(), base + m.end(), m.group(0))
                     for m in pattern.finditer(token)]
        else:
            spans = []
            step = EMAIL_TOKEN_CAP - EMAIL_CHUNK_OVERLAP
            for off in range(0, len(token), step):
                chunk = token[off:off + EMAIL_TOKEN_CAP]
                for m in pattern.finditer(chunk):
                    spans.append((base + off + m.start(),
                                  base + off + m.end(), m.group(0)))
        for start, end, matched in spans:
            if (start, end) not in seen:
                seen.add((start, end))
                yield start, end, matched


def redact_path(path, patterns):
    """Replace any pattern-matched substring of a path with its
    fingerprint token, so printed paths cannot disclose identifiers
    that live in filenames. Paths with no match pass through
    unchanged."""
    result = str(path)
    for label, pattern in patterns.items():
        matches = sorted(iter_pattern_matches(label, pattern, result),
                         reverse=True)
        for start, end, matched in matches:
            result = (result[:start] + f"sha256:{fingerprint(matched)}"
                      + result[end:])
    return result


class Scan:
    def __init__(self, patterns, root, allowlist):
        self.patterns = patterns
        self.root = root
        self.allowlist = allowlist  # list of (glob, pattern)
        self.flagged_lines = 0
        self.files_scanned = 0
        self.enumerated = 0
        self.excluded = 0
        self.archives = 0
        self.members_inspected = 0
        self.metadata_inspected = 0
        self.skipped_files = 0
        self.skipped_dirs = []      # (dir path, file count) pruned by name
        self.unreadable = []        # paths (or archive::member) not inspected
        self.walk_errors = []       # directories os.walk could not enter

    def display(self, path):
        return redact_path(path, self.patterns)

    def allowlist_glob(self, name, rel):
        for glob, pat in self.allowlist:
            if pat.match(name) or pat.match(rel):
                return glob
        return None

    def scan_lines(self, display_path, lines):
        display_path = self.display(display_path)
        for lineno, line in enumerate(lines, 1):
            line_flagged = False
            for label, pattern in self.patterns.items():
                for _start, _end, matched in iter_pattern_matches(
                        label, pattern, line):
                    line_flagged = True
                    print(f"{display_path}:{lineno}: {label}: "
                          f"sha256:{fingerprint(matched)}")
            if line_flagged:
                self.flagged_lines += 1

    def scan_metadata_text(self, display_path, text, context):
        """Run the patterns over a name or target string (a file path,
        an archive member name, a tar link target). Matches are
        reported with the matched text fingerprinted, never printed."""
        display_path = self.display(display_path)
        found = False
        for label, pattern in self.patterns.items():
            for _start, _end, matched in iter_pattern_matches(
                    label, pattern, text):
                found = True
                print(f"{display_path}:0: {label} in {context}: "
                      f"sha256:{fingerprint(matched)}")
        if found:
            self.flagged_lines += 1

    def inspect_member_name(self, archive_path, member_name):
        self.metadata_inspected += 1
        self.scan_metadata_text(f"{archive_path}::{member_name}",
                                member_name, "archive member name")

    def record_skipped_dir(self, dirpath):
        """Count (never read) the files inside a pruned directory and
        record the directory for the coverage report, so a skipped
        subtree is accounted for instead of invisible."""
        def onerror(err):
            self.walk_errors.append(err.filename or str(err))

        count = 0
        for _root, _dirs, files in os.walk(dirpath, onerror=onerror):
            count += len(files)
        self.skipped_dirs.append((dirpath, count))
        self.skipped_files += count
        self.enumerated += count

    def scan_member(self, archive_path, kind, member_name, read):
        display = f"{archive_path}::{member_name}"
        glob = self.allowlist_glob(os.path.basename(member_name), member_name)
        try:
            raw = read()
        except Exception:
            raw = None
        if raw is None:
            if glob is not None:
                self.excluded += 1
                print(f"scrub scan: excluded {self.display(display)} "
                      f"(allowlist: {glob})", file=sys.stderr)
            else:
                self.unreadable.append(display)
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            if glob is not None:
                self.excluded += 1
                print(f"scrub scan: excluded {self.display(display)} "
                      f"(allowlist: {glob})", file=sys.stderr)
            else:
                self.unreadable.append(display)
            return
        self.members_inspected += 1
        self.scan_lines(display, text.splitlines())

    def scan_archive(self, path, kind):
        try:
            if kind == "zip":
                with zipfile.ZipFile(path) as zf:
                    for info in zf.infolist():
                        self.inspect_member_name(path, info.filename)
                        if info.is_dir():
                            continue
                        self.scan_member(path, kind, info.filename,
                                         lambda info=info: zf.read(info))
            else:
                with tarfile.open(path, "r:*") as tf:
                    for member in tf:
                        self.inspect_member_name(path, member.name)
                        if not member.isfile():
                            if member.issym() or member.islnk():
                                self.scan_metadata_text(
                                    f"{path}::{member.name}",
                                    member.linkname or "",
                                    "tar link target")
                            continue
                        self.scan_member(
                            path, kind, member.name,
                            lambda member=member: tf.extractfile(member).read())
        except (zipfile.BadZipFile, tarfile.TarError, OSError, EOFError,
                RuntimeError):
            self.unreadable.append(path)

    def scan_file(self, path, self_path):
        if os.path.realpath(path) == self_path:
            self.excluded += 1
            print(f"scrub scan: excluded {self.display(path)} "
                  f"(scanner source, verify separately)", file=sys.stderr)
            return
        rel = os.path.relpath(path, self.root)
        self.metadata_inspected += 1
        self.scan_metadata_text(path, rel, "file path")
        glob = self.allowlist_glob(os.path.basename(path), rel)
        if glob is not None:
            self.excluded += 1
            print(f"scrub scan: excluded {self.display(path)} "
                  f"(allowlist: {glob})", file=sys.stderr)
            return
        kind = archive_kind(path)
        if kind is not None:
            self.archives += 1
            self.scan_archive(path, kind)
            return
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (UnicodeDecodeError, OSError):
            self.unreadable.append(path)
            return
        self.files_scanned += 1
        self.scan_lines(path, lines)


def load_allowlist(root):
    path = os.path.join(root, ALLOWLIST_NAME)
    entries = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                glob = line.strip()
                if glob and not glob.startswith("#"):
                    entries.append((glob, re.compile(fnmatch.translate(glob))))
    except OSError:
        pass
    return entries


def iter_files(target, scan):
    if os.path.isfile(target):
        yield target
        return

    def onerror(err):
        scan.walk_errors.append(err.filename or str(err))

    for root, dirs, files in os.walk(target, onerror=onerror):
        kept = []
        for d in dirs:
            if d in SKIP_DIRS:
                scan.record_skipped_dir(os.path.join(root, d))
            else:
                kept.append(d)
        dirs[:] = kept
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
    patterns = dict(PATTERNS)
    for i, extra in enumerate(args.extra_regex):
        patterns[f"extra pattern {i + 1}"] = re.compile(extra)
    if not os.path.exists(args.directory):
        print(f"scrub scan: no such file or directory: "
              f"{redact_path(args.directory, patterns)}",
              file=sys.stderr)
        return 2

    target = args.directory
    root = target if os.path.isdir(target) else os.path.dirname(target)
    scan = Scan(patterns, root, load_allowlist(root))
    self_path = os.path.realpath(__file__)
    for path in iter_files(target, scan):
        scan.enumerated += 1
        scan.scan_file(path, self_path)
    scan.unreadable.extend(scan.walk_errors)

    for dirpath, count in scan.skipped_dirs:
        print(f"scrub scan: skipped {scan.display(dirpath)}: "
              f"{count} file(s) not content-scanned "
              f"(skip-list directory)", file=sys.stderr)
    for path in scan.unreadable:
        print(f"scrub scan: not inspected (unreadable): "
              f"{scan.display(path)}", file=sys.stderr)
    print(f"scrub scan: {scan.flagged_lines} flagged line(s), "
          f"{scan.files_scanned} file(s) scanned", file=sys.stderr)
    print(f"scrub scan coverage: enumerated {scan.enumerated}, "
          f"scanned {scan.files_scanned}, "
          f"archives {scan.archives} ({scan.members_inspected} member(s) "
          f"inspected), metadata {scan.metadata_inspected} inspected, "
          f"excluded {scan.excluded}, "
          f"skipped {scan.skipped_files} file(s) in "
          f"{len(scan.skipped_dirs)} dir(s), "
          f"unreadable {len(scan.unreadable)}", file=sys.stderr)
    if scan.unreadable:
        print("scrub scan: verdict incomplete: uninspected content present",
              file=sys.stderr)
        return 3
    return 1 if scan.flagged_lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
