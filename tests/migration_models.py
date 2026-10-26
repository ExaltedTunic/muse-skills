#!/usr/bin/env python3
"""Executable sqlite models for schema-migration-safety fix wave W3.

Each scenario implements the OLD pseudocode (control: must still fail in the
way the review demonstrated) and the NEW pseudocode (must pass), following the
text of references/runner-and-proof-templates.md before and after the fix.
Findings covered: M01 (adoption over-seeding), M02 (fresh-only baseline
eligibility), M03 (concurrent runners + stale applied set), M04 (CHECK guard
scoping, modelled as the pattern's decision logic over a mock catalog), CTX04
(nontransactional-DDL boundary and protocol).

sqlite stands in for the target engine; PostgreSQL-only surface syntax
(pg_advisory_lock, pg_constraint, CREATE INDEX CONCURRENTLY) is modelled by
its documented semantics, noted per scenario. Stdlib only.
"""

import os
import sqlite3
import sys
import tempfile

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))


def mem():
    return sqlite3.connect(":memory:", isolation_level=None)


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def index_valid(conn, name):
    # sqlite has no indisvalid; an index present in sqlite_master is the probe.
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone() is not None


def columns(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def bootstrap(conn):
    conn.execute(
        'CREATE TABLE IF NOT EXISTS "schema_migration_ledger" '
        '("name" text PRIMARY KEY, "applied_at" text NOT NULL DEFAULT \'now\')'
    )


def record(conn, name):
    conn.execute(
        'INSERT INTO "schema_migration_ledger" ("name") VALUES (?) '
        'ON CONFLICT ("name") DO NOTHING', (name,))


def ledger_names(conn):
    return [r[0] for r in conn.execute(
        'SELECT name FROM "schema_migration_ledger" ORDER BY name')]


class Mig:
    def __init__(self, name, body=None, footprint=None, fresh_only=False,
                 postconditions=None, declared_nontransactional=False,
                 body_text="", apply_outside=None, postcondition=None):
        self.name = name
        self.body = body
        self.footprint = footprint
        self.fresh_only = fresh_only
        self.postconditions = postconditions or []
        self.declared_nontransactional = declared_nontransactional
        self.body_text = body_text
        self.apply_outside = apply_outside
        self.postcondition = postcondition


# ---------------------------------------------------------------- old runner
def old_runner(conn, migrations, base_exists, newest_preledger_idx=-1):
    """The pre-fix pseudocode: seed every listed name on adoption; fresh-only
    recorded on base existence alone; applied set read once at bootstrap."""
    bootstrap(conn)
    applied = set(ledger_names(conn))
    if not applied and base_exists(conn):
        newest_fp = migrations[newest_preledger_idx].footprint
        if newest_fp and newest_fp(conn):
            conn.execute("BEGIN")
            for m in migrations:
                record(conn, m.name)
            conn.execute("COMMIT")
            applied = {m.name for m in migrations}
    report = {"appliedNow": [], "skippedRecorded": [], "adopted": False}
    for m in migrations:
        if m.name in applied:
            report["skippedRecorded"].append(m.name)
            continue
        if m.fresh_only and base_exists(conn):
            record(conn, m.name)          # "by definition present"
            report["skippedRecorded"].append(m.name)
            continue
        conn.execute("BEGIN")
        m.body(conn)
        record(conn, m.name)
        conn.execute("COMMIT")
        report["appliedNow"].append(m.name)
    return report


# ---------------------------------------------------------------- new runner
class Lock:
    """Single-runner lock: a row in runner_lock. PostgreSQL form is
    pg_advisory_lock(<fixed key>); this is the named-lock equivalent."""

    def __init__(self, conn):
        self.conn = conn
        conn.execute(
            'CREATE TABLE IF NOT EXISTS "runner_lock" '
            '("id" integer PRIMARY KEY CHECK (id = 1))')

    def acquire(self):
        try:
            self.conn.execute('INSERT INTO "runner_lock" ("id") VALUES (1)')
            return True
        except sqlite3.IntegrityError:
            return False

    def release(self):
        self.conn.execute('DELETE FROM "runner_lock" WHERE id = 1')


class NamedAbort(Exception):
    pass


def new_apply_one(conn, m, base_exists):
    """One loop iteration of the new pseudocode: re-read inside the txn."""
    conn.execute("BEGIN")
    recorded = conn.execute(
        'SELECT name FROM "schema_migration_ledger" WHERE name = ?',
        (m.name,)).fetchone()
    if recorded:
        conn.execute("COMMIT")
        return "skipped"
    if m.fresh_only and base_exists(conn):
        missing = [label for label, probe in m.postconditions if not probe(conn)]
        if missing:
            conn.execute("ROLLBACK")
            raise NamedAbort(
                f"fresh-only baseline {m.name} not eligible: "
                f"missing postcondition {missing[0]}")
        record(conn, m.name)
        conn.execute("COMMIT")
        return "recorded-verified"
    m.body(conn)
    record(conn, m.name)
    conn.execute("COMMIT")
    return "applied"


NONTRANSACTIONAL_MARKERS = ("CREATE INDEX CONCURRENTLY", "ALTER TYPE")


def contains_nontransactional(body_text):
    return any(mk in body_text.upper() for mk in
               (m.upper() for m in NONTRANSACTIONAL_MARKERS))


def nontransactional_protocol(conn, m, crash_after_apply=False):
    """CTX04 protocol: precheck -> apply outside a transaction -> verify ->
    only then write the ledger row."""
    if m.postcondition(conn):                    # precheck
        record(conn, m.name)
        return "recorded-from-precheck"
    m.apply_outside(conn)                        # no BEGIN: outside a transaction
    if crash_after_apply:
        return "crashed-after-apply-before-record"
    if not m.postcondition(conn):               # verify
        raise NamedAbort(f"postcondition for {m.name} does not hold after apply")
    conn.execute("BEGIN")
    record(conn, m.name)
    conn.execute("COMMIT")
    return "applied-and-recorded"


def new_runner(conn, migrations, base_exists, newest_preledger_idx,
               bypass_lock=False):
    # preflight: reject undeclared nontransactional files before anything runs
    for m in migrations:
        if contains_nontransactional(m.body_text) and not m.declared_nontransactional:
            raise NamedAbort(
                f"preflight: {m.name} contains a nontransactional statement "
                f"but its header lacks 'transactional: no'")
    lock = Lock(conn)
    if not bypass_lock and not lock.acquire():
        return {"outcome": "another runner holds the lock"}
    try:
        bootstrap(conn)
        applied = set(ledger_names(conn))
        adopted = []
        if not applied and base_exists(conn):
            if migrations[newest_preledger_idx].footprint(conn):
                # evidenced prefix: up to and including the NEWEST migration
                # whose footprint is present
                newest_ev = max(i for i, m in enumerate(migrations)
                                if m.footprint and m.footprint(conn))
                prefix = [m.name for m in migrations[:newest_ev + 1]]
                conn.execute("BEGIN")
                for n in prefix:
                    record(conn, n)
                conn.execute("COMMIT")
                applied = set(prefix)
                adopted = prefix
        report = {"appliedNow": [], "skippedRecorded": [], "adopted": adopted}
        for m in migrations:
            if m.declared_nontransactional:
                r = nontransactional_protocol(conn, m)
                report["appliedNow"].append((m.name, r))
                continue
            r = new_apply_one(conn, m, base_exists)
            (report["appliedNow"] if r == "applied"
             else report["skippedRecorded"]).append(m.name)
        return report
    finally:
        if not bypass_lock:
            lock.release()


# =====================================================================
print("== M01: adoption must seed only the evidenced prefix ==")
# Pre-ledger database: base + orders (002's footprint) + sentinel row.
# Runner list has grown since: 003_audit is post-ledger, never ran anywhere.
def build_preledger(conn):
    conn.execute("CREATE TABLE base (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO base VALUES (1)")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO orders VALUES (99)")  # sentinel-adjacent data

def migs_m01():
    return [
        Mig("001_base",
            body=lambda c: c.execute("CREATE TABLE base (id INTEGER PRIMARY KEY)"),
            footprint=lambda c: table_exists(c, "base")),
        Mig("002_orders",
            body=lambda c: c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY)"),
            footprint=lambda c: table_exists(c, "orders")),
        Mig("003_audit",
            body=lambda c: c.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY)"),
            footprint=lambda c: table_exists(c, "audit_log")),
    ]

base_exists = lambda c: table_exists(c, "base")  # noqa: E731

conn = mem(); build_preledger(conn)
rep = old_runner(conn, migs_m01(), base_exists, newest_preledger_idx=1)
print(f"  old run: ledger={ledger_names(conn)} audit_log={table_exists(conn, 'audit_log')}")
old_runner(conn, migs_m01(), base_exists, newest_preledger_idx=1)
print(f"  old rerun: audit_log still exists={table_exists(conn, 'audit_log')}")
check("M01 old control reproduces the defect",
      "003_audit" in ledger_names(conn) and not table_exists(conn, "audit_log"),
      "003 recorded as applied, its table never created, rerun skips it")

conn = mem(); build_preledger(conn)
rep = new_runner(conn, migs_m01(), base_exists, newest_preledger_idx=1)
print(f"  new run: adopted={rep['adopted']} appliedNow={rep['appliedNow']} "
      f"ledger={ledger_names(conn)} audit_log={table_exists(conn, 'audit_log')}")
check("M01 new: prefix adopted, post-ledger migration NOT seeded",
      rep["adopted"] == ["001_base", "002_orders"])
check("M01 new: 003 body ran in the same run, audit_log exists",
      table_exists(conn, "audit_log") and "003_audit" in ledger_names(conn))
check("M01 new: sentinel data untouched",
      conn.execute("SELECT COUNT(*) FROM orders WHERE id=99").fetchone()[0] == 1)

# =====================================================================
print("== M02: fresh-only baseline needs verified postconditions ==")
POST = [("table base", lambda c: table_exists(c, "base")),
        ("column base.id", lambda c: "id" in columns(c, "base")),
        ("column base.new_col", lambda c: "new_col" in columns(c, "base"))]
baseline = Mig("001_baseline", fresh_only=True, postconditions=POST,
               body=lambda c: c.execute(
                   "CREATE TABLE base (id INTEGER PRIMARY KEY, new_col text)"))

def partial_base():
    conn = mem()
    conn.execute("CREATE TABLE base (id INTEGER PRIMARY KEY)")  # no new_col
    bootstrap(conn); record(conn, "000_legacy")
    return conn

conn = partial_base()
rep = old_runner(conn, [baseline], base_exists)
print(f"  old: ledger={ledger_names(conn)} new_col present={'new_col' in columns(conn, 'base')}")
check("M02 old control reproduces the defect",
      "001_baseline" in ledger_names(conn) and "new_col" not in columns(conn, "base"),
      "baseline recorded against a partial base; new_col absent")

conn = partial_base()
try:
    new_runner(conn, [baseline], base_exists, newest_preledger_idx=0)
    outcome = "no error"
except NamedAbort as e:
    outcome = str(e)
print(f"  new on partial base: {outcome}; ledger={ledger_names(conn)}")
check("M02 new: partial base rejected with the missing postcondition named",
      "base.new_col" in outcome)
check("M02 new: nothing recorded for the ineligible baseline",
      "001_baseline" not in ledger_names(conn))

conn = mem()  # full base: every postcondition present
conn.execute("CREATE TABLE base (id INTEGER PRIMARY KEY, new_col text)")
bootstrap(conn); record(conn, "000_legacy")
rep = new_runner(conn, [baseline], base_exists, newest_preledger_idx=0)
print(f"  new on full base: report={rep} ledger={ledger_names(conn)}")
check("M02 new: verified full base is recorded without running the body",
      "001_baseline" in ledger_names(conn),
      "body would have raised (table exists) if it had run")

# =====================================================================
print("== M03: concurrent runners must not double-apply ==")
def filedb():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    a = sqlite3.connect(path, isolation_level=None)
    b = sqlite3.connect(path, isolation_level=None)
    return path, a, b

def seed_mig():
    return Mig("001_seed",
               body=lambda c: c.execute("INSERT INTO app_data VALUES ('seed-admin')"))

path, A, B = filedb()
for c in (A,):
    bootstrap(c); c.execute("CREATE TABLE app_data (v text)")
# OLD: both runners bootstrap-read the applied set before either writes.
appliedA = set(ledger_names(A)); appliedB = set(ledger_names(B))
for conn, applied in ((A, appliedA), (B, appliedB)):
    if "001_seed" not in applied:
        conn.execute("BEGIN"); seed_mig().body(conn); record(conn, "001_seed")
        conn.execute("COMMIT")
rows = A.execute("SELECT COUNT(*) FROM app_data").fetchone()[0]
print(f"  old interleaved: app_data rows={rows} ledger={ledger_names(A)}")
check("M03 old control reproduces the defect", rows == 2 and ledger_names(A) == ["001_seed"],
      "two committed data effects, one ledger row, no error")
A.close(); B.close(); os.unlink(path)

path, A, B = filedb()
bootstrap(A); A.execute("CREATE TABLE app_data (v text)")
lockA = Lock(A)
assert lockA.acquire()
repB = new_runner(B, [seed_mig()], base_exists, newest_preledger_idx=0)
print(f"  new while A holds the lock: B outcome={repB}")
check("M03 new: second runner gets the named lock outcome, runs nothing",
      repB.get("outcome") == "another runner holds the lock"
      and A.execute("SELECT COUNT(*) FROM app_data").fetchone()[0] == 0)
repA = {"appliedNow": [new_apply_one(A, seed_mig(), base_exists)]}
lockA.release()
repB2 = new_runner(B, [seed_mig()], base_exists, newest_preledger_idx=0)
rows = A.execute("SELECT COUNT(*) FROM app_data").fetchone()[0]
print(f"  new: A applied={repA['appliedNow']} B after release={repB2} rows={rows}")
check("M03 new: body ran exactly once across both runners", rows == 1)
A.close(); B.close(); os.unlink(path)

# Defense in depth: lock bypassed, in-transaction re-read still prevents it.
path, A, B = filedb()
bootstrap(A); A.execute("CREATE TABLE app_data (v text)")
appliedA = set(ledger_names(A)); appliedB = set(ledger_names(B))  # both stale-empty
rA = new_apply_one(A, seed_mig(), base_exists)
rB = new_apply_one(B, seed_mig(), base_exists)
rows = A.execute("SELECT COUNT(*) FROM app_data").fetchone()[0]
print(f"  new, lock bypassed: A={rA} B={rB} rows={rows}")
check("M03 new: re-read inside the transaction catches the stale snapshot",
      rA == "applied" and rB == "skipped" and rows == 1)
A.close(); B.close(); os.unlink(path)

# =====================================================================
print("== M04: CHECK guard scoped by relation + definition, three states ==")
# Decision-logic model of the pattern over a mock pg_constraint catalog.
NAME = "orders_status_closed_set"
INTENDED = "check ((status = any (array['placed','paid','shipped','refunded','cancelled'])))"
def norm(s): return " ".join(s.lower().split())

def old_guard(catalog):
    return "skipped" if any(r["conname"] == NAME for r in catalog) else "added"

def new_guard(catalog, action_log):
    rows = [r for r in catalog if r["conname"] == NAME and r["conrelid"] == "orders"]
    if not rows:
        catalog.append({"conname": NAME, "conrelid": "orders",
                        "def": INTENDED, "convalidated": True})
        return "added"
    r = rows[0]
    if norm(r["def"]) != norm(INTENDED):
        raise NamedAbort(f"constraint {NAME} on orders exists with a different definition: {r['def']}")
    if not r["convalidated"]:
        r["convalidated"] = True
        return "validated"
    return "no-op"

cat = [{"conname": NAME, "conrelid": "shipments", "def": INTENDED, "convalidated": True}]
o = old_guard(cat); n = new_guard(cat, [])
print(f"  same name on shipments only: old={o} new={n}")
check("M04 old control: name-only guard skips on another table's constraint", o == "skipped")
check("M04 new: scoped guard adds the constraint to orders", n == "added")

cat = [{"conname": NAME, "conrelid": "orders", "def": "check ((status <> 'x'))", "convalidated": True}]
o = old_guard(cat)
try: n = new_guard(cat, [])
except NamedAbort as e: n = f"raised: {e}"
print(f"  different definition on orders: old={o} new={n}")
check("M04 old control: wrong definition silently accepted", o == "skipped")
check("M04 new: different definition fails loudly, naming what was found",
      n.startswith("raised:") and "different definition" in n)

cat = [{"conname": NAME, "conrelid": "orders", "def": INTENDED, "convalidated": False}]
o = old_guard(cat); n = new_guard(cat, [])
print(f"  identical but NOT VALID: old={o} new={n} convalidated now={cat[0]['convalidated']}")
check("M04 old control: unvalidated constraint left unvalidated by a skip", o == "skipped")
check("M04 new: NOT VALID state runs VALIDATE as the separate step",
      n == "validated" and cat[0]["convalidated"] is True)

cat = [{"conname": NAME, "conrelid": "orders", "def": INTENDED, "convalidated": True}]
check("M04 new: present, identical, validated is a true no-op",
      new_guard(cat, []) == "no-op")

# =====================================================================
print("== CTX04: nontransactional DDL boundary and protocol ==")
CIC_TEXT = "CREATE INDEX CONCURRENTLY idx_orders_status ON orders (status);"
apply_count = {"n": 0}
def cic_apply(conn):
    apply_count["n"] += 1
    conn.execute("CREATE INDEX idx_orders_status ON orders (status)")
cic = Mig("001_idx", declared_nontransactional=True, body_text=CIC_TEXT,
          apply_outside=cic_apply,
          postcondition=lambda c: index_valid(c, "idx_orders_status"))
plain = Mig("002_t2", body=lambda c: c.execute("CREATE TABLE t2 (id INTEGER)"),
            footprint=lambda c: table_exists(c, "t2"))

# OLD: the atomic runner has no path for it; the statement cannot run in the
# migration transaction, so the run aborts and nothing is recorded or built.
conn = mem(); bootstrap(conn); conn.execute("CREATE TABLE orders (status text)")
try:
    conn.execute("BEGIN")
    raise RuntimeError("CREATE INDEX CONCURRENTLY cannot run inside a transaction block")
    record(conn, "001_idx"); conn.execute("COMMIT")  # noqa: unreachable
except RuntimeError as e:
    conn.execute("ROLLBACK"); old_err = str(e)
print(f"  old: run aborted ({old_err}); index={index_valid(conn, 'idx_orders_status')} ledger={ledger_names(conn)}")
check("CTX04 old control: atomic-only recipe cannot handle the statement",
      not index_valid(conn, "idx_orders_status") and ledger_names(conn) == [])

# NEW preflight: same file WITHOUT the header declaration is rejected first.
undeclared = Mig("001_idx", declared_nontransactional=False, body_text=CIC_TEXT,
                 apply_outside=cic_apply,
                 postcondition=lambda c: index_valid(c, "idx_orders_status"))
conn = mem(); conn.execute("CREATE TABLE orders (status text)")
try:
    new_runner(conn, [undeclared], base_exists, newest_preledger_idx=0)
    outcome = "no error"
except NamedAbort as e:
    outcome = str(e)
print(f"  new preflight on undeclared file: {outcome}")
check("CTX04 new: undeclared nontransactional file rejected before anything runs",
      "preflight" in outcome and not index_valid(conn, "idx_orders_status"))

# NEW protocol: declared file is ledgered on the verified postcondition,
# and the following transactional migration still runs in the same run.
conn = mem(); conn.execute("CREATE TABLE orders (status text)")
rep = new_runner(conn, [cic, plain], base_exists, newest_preledger_idx=1)
print(f"  new protocol run: {rep} index={index_valid(conn, 'idx_orders_status')} ledger={ledger_names(conn)}")
check("CTX04 new: index verified in catalog before its ledger row exists",
      index_valid(conn, "idx_orders_status") and "001_idx" in ledger_names(conn))
check("CTX04 new: following transactional migration ran normally",
      table_exists(conn, "t2") and "002_t2" in ledger_names(conn))

# Crash between statement and ledger row: recovered by the precheck,
# the statement is NOT re-run.
conn = mem(); bootstrap(conn); conn.execute("CREATE TABLE orders (status text)")
apply_count["n"] = 0
r1 = nontransactional_protocol(conn, cic, crash_after_apply=True)
r2 = nontransactional_protocol(conn, cic)
print(f"  crash case: first={r1} second={r2} apply_count={apply_count['n']} ledger={ledger_names(conn)}")
check("CTX04 new: crash recovered by precheck, statement ran exactly once",
      r1 == "crashed-after-apply-before-record" and r2 == "recorded-from-precheck"
      and apply_count["n"] == 1 and "001_idx" in ledger_names(conn))

# =====================================================================
fails = [label for label, ok in RESULTS if not ok]
print(f"\nSUMMARY: {len(RESULTS) - len(fails)}/{len(RESULTS)} checks passed"
      + (f"; FAILING: {fails}" if fails else ""))
sys.exit(1 if fails else 0)
