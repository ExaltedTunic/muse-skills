#!/usr/bin/env python3
"""Regression checks for fix wave W2 (scrub scanner, memory audit, metadata).

Stdlib only. Builds synthetic fixtures in a temp dir and runs the LIVE
scripts against them. Exit 0 iff every check passes.
"""
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
STAGING = os.path.join(ROOT, "skills")
SCRUB = os.path.join(STAGING, "agent-workflow", "scrub-before-sharing", "scripts", "scrub_scan.py")
AUDIT = os.path.join(STAGING, "agent-workflow", "memory-hygiene", "scripts", "memory_audit.py")

KEY = "sk-" + "proj-" + "FAKE" * 8 + "1234"
EMAIL = "jane.doe" + "@" + "example.com"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" :: {detail}" if detail else ""))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run_scrub(target, script=SCRUB, as_nobody=False):
    cmd = [sys.executable, script, target]
    if as_nobody and os.geteuid() == 0:
        cmd = ["runuser", "-u", "nobody", "--"] + cmd
    return run(cmd)


def fp(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def main():
    tmp = tempfile.mkdtemp(prefix="w2fix_")
    os.chmod(tmp, 0o755)

    def tree(name):
        d = os.path.join(tmp, name)
        os.makedirs(d)
        os.chmod(d, 0o755)
        return d

    def wfile(d, name, data, mode="w"):
        p = os.path.join(d, name)
        with open(p, mode) as fh:
            fh.write(data)
        os.chmod(p, 0o644)
        return p

    # ---------- backward compatibility (must pass before AND after) ----------
    d = tree("compat")
    clean = wfile(d, "clean.txt", "Nothing sensitive here.\n")
    r = run_scrub(clean)
    check("compat.clean_file_exit_0", r.returncode == 0, f"exit={r.returncode}")

    d = tree("compatkey")
    kf = wfile(d, "key.txt", f"token: {KEY}\n")
    r = run_scrub(kf)
    check("compat.planted_key_exit_1", r.returncode == 1, f"exit={r.returncode}")

    r = run_scrub(os.path.join(tmp, "does-not-exist"))
    check("compat.missing_target_exit_2", r.returncode == 2, f"exit={r.returncode}")

    # ---------- S02: output redaction ----------
    d = tree("redact")
    f = wfile(d, "leak.txt", f"token: {KEY}\ncontact: {EMAIL}\n")
    r = run_scrub(f)
    out = r.stdout
    check("s02.key_not_in_output", KEY not in out)
    check("s02.email_not_in_output", EMAIL not in out)
    check("s02.key_fingerprint_printed", f"sha256:{fp(KEY)}" in out,
          "expected sha256 fingerprint of the key match")
    check("s02.email_fingerprint_printed", f"sha256:{fp(EMAIL)}" in out,
          "expected sha256 fingerprint of the email match")

    # ---------- S01: coverage honesty ----------
    # (b) undecodable file -> exit 3, path listed, no clean verdict
    d = tree("undecodable")
    bad = wfile(d, "bad.bin", b"\xff\xfe\x80\x81 not utf-8", mode="wb")
    wfile(d, "ok.txt", "plain clean text\n")
    r = run_scrub(d)
    check("s01.undecodable_exit_3", r.returncode == 3, f"exit={r.returncode}")
    check("s01.undecodable_path_listed", bad in (r.stdout + r.stderr))

    # (a) coverage summary line on every run
    check("s01.coverage_line_printed",
          "coverage:" in r.stderr and "enumerated" in r.stderr
          and "scanned" in r.stderr and "unreadable" in r.stderr,
          r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "no stderr")

    # (c) zip archive members are inspected: planted email inside -> exit 1
    d = tree("zipflag")
    zp = os.path.join(d, "bundle.zip")
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("notes.txt", f"reach me at {EMAIL}\n")
    r = run_scrub(d)
    check("s01.zip_member_flagged_exit_1", r.returncode == 1, f"exit={r.returncode}")
    check("s01.zip_member_named", "bundle.zip" in r.stdout and "notes.txt" in r.stdout)
    check("s01.zip_member_redacted", EMAIL not in r.stdout
          and f"sha256:{fp(EMAIL)}" in r.stdout)
    check("s01.zip_members_counted", "member" in r.stderr and "inspected" in r.stderr)

    # (c2) tar.gz members are inspected: planted key inside -> exit 1
    d = tree("tarflag")
    tp = os.path.join(d, "pack.tar.gz")
    with tarfile.open(tp, "w:gz") as t:
        data = f"token: {KEY}\n".encode()
        info = tarfile.TarInfo("inner.txt")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    r = run_scrub(d)
    check("s01.tar_member_flagged_exit_1", r.returncode == 1, f"exit={r.returncode}")
    check("s01.tar_member_redacted", KEY not in r.stdout
          and f"sha256:{fp(KEY)}" in r.stdout)

    # (c3) corrupt archive -> unreadable -> exit 3
    d = tree("zipcorrupt")
    wfile(d, "bad.zip", b"this is not a zip archive at all", mode="wb")
    r = run_scrub(d)
    check("s01.corrupt_zip_exit_3", r.returncode == 3, f"exit={r.returncode}")

    # (b/d) permission-denied file and directory, run as nobody
    if os.geteuid() == 0:
        d = tree("locked")
        copy = os.path.join(d, "scrub_copy.py")
        shutil.copy(SCRUB, copy)
        os.chmod(copy, 0o644)
        secret = wfile(d, "secret.txt", f"boss: {EMAIL}\n")
        os.chmod(secret, 0o000)
        r = run_scrub(d, script=copy, as_nobody=True)
        check("s01.locked_file_exit_3", r.returncode == 3,
              f"exit={r.returncode} out={r.stdout.strip()[:80]} err={r.stderr.strip()[:80]}")
        check("s01.locked_file_path_listed", secret in (r.stdout + r.stderr))
        os.chmod(secret, 0o644)

        d = tree("lockeddir")
        copy = os.path.join(d, "scrub_copy.py")
        shutil.copy(SCRUB, copy)
        os.chmod(copy, 0o644)
        sub = os.path.join(d, "vault")
        os.makedirs(sub)
        wfile(sub, "inner.txt", f"hidden: {EMAIL}\n")
        os.chmod(sub, 0o000)
        r = run_scrub(d, script=copy, as_nobody=True)
        check("s01.locked_dir_exit_3", r.returncode == 3,
              f"exit={r.returncode} out={r.stdout.strip()[:80]} err={r.stderr.strip()[:80]}")
        os.chmod(sub, 0o755)
    else:
        check("s01.locked_file_exit_3", False, "must run as root to drop to nobody")
        check("s01.locked_dir_exit_3", False, "must run as root to drop to nobody")

    # (e) scanner's own source: excluded explicitly, with the reason
    d = tree("selfscan")
    copy = os.path.join(d, "scrub_scan.py")
    shutil.copy(SCRUB, copy)
    os.chmod(copy, 0o644)
    wfile(d, "clean.txt", "perfectly clean\n")
    r = run_scrub(d, script=copy)
    blob = r.stdout + r.stderr
    check("s01.self_excluded_with_reason",
          "scanner source, verify separately" in blob,
          "coverage/exclusion output must name the reason")
    check("s01.self_scan_exit_0", r.returncode == 0, f"exit={r.returncode}")
    check("s01.self_coverage_counts",
          "enumerated 2" in blob and "excluded 1" in blob and "scanned 1" in blob,
          blob.strip().splitlines()[-1] if blob.strip() else "")

    # (f) allowlist: deliberately non-text artifact excluded, no exit 3
    d = tree("allowlist")
    binf = wfile(d, "logo.bin", b"\x89PNG\x00\xff\xfe binary", mode="wb")
    wfile(d, ".scrub-allowlist", "*.bin\n")
    wfile(d, "clean.txt", "clean\n")
    r = run_scrub(d)
    blob = r.stdout + r.stderr
    check("s01.allowlist_exit_0", r.returncode == 0, f"exit={r.returncode}")
    check("s01.allowlist_named_in_output",
          "logo.bin" in blob and "allowlist" in blob,
          "allowlisted file must be counted and named")

    # ---------- I03: Unicode-aware normalization ----------
    spec = importlib.util.spec_from_file_location("memory_audit", AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    n_no = mod.normalized("Møter starter neste mandag")
    n_ma = mod.normalized("Måter starter neste mandag")
    check("i03.norwegian_letters_preserved", n_no != n_ma,
          f"{n_no!r} vs {n_ma!r}")
    check("i03.case_punct_still_folded",
          mod.normalized("Hello, World! Test.") == mod.normalized("hello world test"))
    check("i03.underscore_not_kept", "_" not in mod.normalized("a_b c_d"))

    d = tree("audit")
    no = wfile(d, "no.md", "Møter starter neste mandag\nMåter starter neste mandag\n")
    r = run([sys.executable, AUDIT, no])
    check("i03.audit_no_false_duplicate",
          "duplicate lines (normalized)" not in r.stdout, r.stdout.strip()[:120])
    dup = wfile(d, "dup.md", "Review the Plan Weekly.\nreview the plan weekly\n")
    r = run([sys.executable, AUDIT, dup])
    check("i03.audit_real_duplicate_still_found",
          "duplicate lines (normalized): 1" in r.stdout, r.stdout.strip()[:120])

    # ---------- R02: metadata alignment ----------
    def parse_description(text):
        m = re.search(r"^description:\s*(.*)$", text, re.MULTILINE)
        if not m:
            return None
        raw = m.group(1).strip()
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            try:
                return json.loads(raw)
            except ValueError:
                return raw[1:-1]
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            return raw[1:-1].replace("''", "'")
        return raw

    def frontmatter_description(skill_md):
        text = open(skill_md, encoding="utf-8").read()
        parts = text.split("---", 2)
        return parse_description(parts[1] if len(parts) > 2 else text)

    def sidecar_description(yaml_path):
        return parse_description(open(yaml_path, encoding="utf-8").read())

    def norm(s):
        return " ".join((s or "").split())

    mismatches = []
    count = 0
    for cat in sorted(os.listdir(STAGING)):
        catdir = os.path.join(STAGING, cat)
        if not os.path.isdir(catdir):
            continue
        for skill in sorted(os.listdir(catdir)):
            sdir = os.path.join(catdir, skill)
            sm, sy = os.path.join(sdir, "SKILL.md"), os.path.join(sdir, "skill.yaml")
            if os.path.isfile(sm) and os.path.isfile(sy):
                count += 1
                if norm(frontmatter_description(sm)) != norm(sidecar_description(sy)):
                    mismatches.append(f"{cat}/{skill}")
    check("r02.all_18_staging_descriptions_match",
          count == 18 and not mismatches,
          f"{count} skills compared; mismatches: {mismatches or 'none'}")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f"; FAILED: {failed}" if failed else ""))
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
