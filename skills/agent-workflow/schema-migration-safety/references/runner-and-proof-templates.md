# Runner and Proof Templates

Worked templates for schema-migration-safety. Names are neutral examples; adapt freely. SQL is PostgreSQL-flavoured.

## Ledger DDL

Carry this in the runner bootstrap *and* as the body of the registered migration that introduces the ledger. Both forms are `IF NOT EXISTS`, so the paths cannot conflict.

```sql
CREATE TABLE IF NOT EXISTS "schema_migration_ledger" (
  "name"       text PRIMARY KEY,
  "applied_at" timestamptz NOT NULL DEFAULT now()
);
```

Recording a migration (inside the migration's own transaction):

```sql
INSERT INTO "schema_migration_ledger" ("name") VALUES ($1)
ON CONFLICT ("name") DO NOTHING;
```

## Runner algorithm

```
preflight: scan every listed file; a file whose body contains a nontransactional
           statement but whose header lacks the "transactional: no" declaration
           is rejected here, before anything runs (see Nontransactional migrations)

acquire the single-runner lock for the whole run
           -- PostgreSQL: SELECT pg_advisory_lock(<one fixed key for this database>);
           -- other engines: the engine's named lock, or an exclusive file lock on a
           -- lockfile beside the database. If the lock is already held, wait for it
           -- or exit reporting "another runner holds the lock"; never proceed unlocked.
bootstrap ledger DDL
applied := SELECT name FROM schema_migration_ledger

if applied is empty and base schema exists:
    determine the evidenced prefix: probe each listed migration's footprint (an
    object only that migration creates); the prefix is every name up to and
    including the NEWEST migration whose footprint is present
    if the newest pre-ledger migration's footprint exists:
        BEGIN
          record every name in the evidenced prefix   -- the prefix only, never
        COMMIT                                        -- the whole list
        applied := evidenced prefix names        -- adopted; no bodies ran
        -- names after the prefix stay unrecorded and run normally below, this run
    -- else: half-built; fall through and replay

for each migration in list order:
    if the migration's header declares "transactional: no":
        run it under the nontransactional protocol (below), not this loop
        continue
    BEGIN
      recorded := SELECT name FROM schema_migration_ledger WHERE name = this migration
      -- re-read inside the transaction, every time: the bootstrap snapshot goes
      -- stale the moment another process commits. This re-read is NOT
      -- concurrency protection: the lock is the only mutual-exclusion
      -- mechanism, and two unlocked runners whose transactions interleave
      -- can both re-read an empty ledger and both proceed. What the re-read
      -- buys is idempotency across retries and restarts: a rerun after a
      -- competing run has committed skips cleanly on the re-read row.
      if recorded is not empty: skip (report as recorded); COMMIT; continue
      if migration is fresh-only and base schema exists:
          verify every structural postcondition declared in the baseline's header
          against the catalog
          if any postcondition is missing:
              ROLLBACK; abort the run, naming the missing postcondition
              -- never record an unverified baseline (see Fresh-only, defined)
          record it without running         -- verified present, not assumed present
          COMMIT
          continue
      run migration body
      record migration name
    COMMIT                                 -- on any error: ROLLBACK, abort the run,
                                           -- name the failed migration
release the runner lock
report { appliedNow, skippedRecorded, adoptedPreLedger }
```

**Fresh-only, defined.** A migration is marked fresh-only when it is a squashed baseline: instead of replaying history, it creates the full current schema in one file, and it exists for databases built from nothing. The baseline's header must declare its structural postconditions — the tables, columns, and constraints it creates, in a form the runner can probe in the catalog. On a database that already has a base schema, base existence alone proves nothing about the rest of the baseline: a half-built or older base can carry the base table while missing later columns and constraints. So before recording the baseline without running it, the runner verifies every declared postcondition against the catalog. All present: record it — the schema it describes is verified present, not assumed present. Any missing: the baseline is not eligible, the runner stops and names the missing postcondition, and nothing is recorded. Applying the baseline (or the missing pieces) to a partial base is then an explicit owner decision, made with the gap named, never a silent runner default. A migration that changes existing objects is never fresh-only; only a baseline squash earns the mark, and the mark belongs in the migration file's header where a reviewer can challenge it.

Rules the pseudocode encodes: one runner at a time, enforced by the lock alone — it is the only mutual-exclusion mechanism, and the in-transaction re-read is idempotency across retries and restarts, not a second line of defence; the record insert shares the body's transaction; adoption seeds only the evidenced prefix, in one transaction, touching no data; a failure aborts the whole run rather than skipping ahead, because later migrations may depend on the failed one.

## Nontransactional migrations

The one-transaction rule has a hard boundary: some statements cannot run inside a transaction block at all. In PostgreSQL, `CREATE INDEX CONCURRENTLY` is the common one; `ALTER TYPE ... ADD VALUE` historically could not run in a transaction block either, and the new value still cannot be used in the same transaction that adds it. A migration file containing such statements must declare it in its header (`transactional: no`); the runner's preflight rejects an undeclared file that contains them, before anything runs, and never ledgers such a file under the atomic rule it cannot honour. Declared files run in list order, under this separate protocol instead:

```
precheck: probe the file's declared postcondition in the catalog
          (the index exists and is valid — indisvalid in PostgreSQL;
          the enum value is present in pg_enum)
if the postcondition already holds:
    record the ledger row; done        -- a previous run crashed after the
                                        -- statement but before the record,
                                        -- or the change was applied by hand
run the statement(s) outside any transaction, each written idempotently
          (CREATE INDEX CONCURRENTLY IF NOT EXISTS;
          ALTER TYPE ... ADD VALUE IF NOT EXISTS)
verify:   probe the postcondition again; if it does not hold,
          abort the run and record nothing
BEGIN; record the ledger row; COMMIT
```

State the weaker guarantee plainly wherever this protocol is described: there is no rollback. A crash between the statement and the ledger row leaves the change applied but unrecorded, and the next run recovers through the precheck (postcondition holds, so it records the row without re-running the statement), not through atomicity. That recovery only works if the postcondition is probed honestly — an index that exists but is invalid (`indisvalid` false, the usual scar of an interrupted concurrent build) does not satisfy it: drop the invalid index and rebuild, as an owner-visible step, rather than recording over it.

## Adoption decision table

| Ledger rows | Base schema | Newest pre-ledger footprint | Verdict | Action |
|---|---|---|---|---|
| any | any | any | Ledger is authoritative | Apply only unrecorded migrations |
| none | absent | absent | Fresh | Apply the full list in order |
| none | present | present | Complete pre-ledger | Seed the ledger with the evidenced prefix only (every listed name up to and including the newest footprint-evidenced migration), run nothing for those |
| none | present | present, but the list also contains migrations newer than the newest pre-ledger one | Adoption with post-ledger files in the list | Seed the evidenced prefix; the newer names are not seeded and apply normally in the same run |
| none | present | absent | Half-built | Replay the list, recording each as it completes |
| migration unrecorded | present | — | Fresh-only baseline in the list | Verify every postcondition declared in the baseline's header against the catalog: all present, record it without running; any missing, stop and name it, record nothing (see the definition above) |
| migration unrecorded | any | — | File declares `transactional: no` | Run the nontransactional protocol: precheck the postcondition, apply outside a transaction, verify the postcondition, then record (see Nontransactional migrations) |

Choosing the footprint: pick an object created *only* by the newest pre-ledger migration — a table, a column, a named constraint. Probe it with the catalog (`to_regclass`, `information_schema`, or the engine's equivalent), not by attempting DDL.

## Proof matrix (disposable database, keep as tests)

| Scenario | Setup | Expected result | What it proves |
|---|---|---|---|
| Fresh apply | Empty database | All migrations run once, all recorded | The list is self-contained and ordered |
| Idempotent rerun | Result of fresh apply | Nothing runs; all reported recorded | The ledger, not file idempotence, carries safety |
| Adoption | Base schema + newest footprint + sentinel data row, empty ledger | Adoption reported; no bodies re-run; sentinel row intact | Pre-ledger databases upgrade without data risk |
| Adoption with post-ledger files | Adoption setup, and the runner list also contains a migration written after the ledger was introduced | Only the evidenced prefix is adopted; the newer migration is not seeded — its body runs in the same run and its objects exist afterwards; sentinel row intact | Adoption never attests to migrations no footprint evidences |
| Fresh-only eligibility | Database with the base table but missing one postcondition the baseline's header declares | Run stops, naming the missing postcondition; the baseline has no ledger row | A partial base is never recorded as the full baseline |
| Concurrent runners | Two runner processes started against the same database at the same time | One acquires the lock and completes; the other waits or exits reporting the lock is held; every migration body ran exactly once | The lock, not timing luck, serializes runners |
| Nontransactional protocol | List contains a header-declared nontransactional migration (a concurrent index build), plus a transactional migration after it | The index exists and is valid in the catalog before its ledger row is written; the following migration then runs transactionally; an undeclared file containing the same statement is rejected in preflight | Nontransactional work is ledgered on verified postconditions, not on an atomic rule it cannot use |
| Failure atomicity | List plus one deliberately broken migration | Run aborts at the broken one; it has no ledger row; earlier migrations stay recorded | A failed migration is never recorded as applied |

Also worth pinning while you are here: applying the list to a database shaped like production (a restored snapshot) before the real deploy, whenever the change adds constraints that validate existing rows.

## Test recipes

**List equals directory.** Read the migrations directory, read the runner's registered list, assert exact equality of the name sets and the order. Failure messages should name the symmetric difference — "file present but unregistered" and "registered but missing" are different mistakes.

**Journal guard.** Hash or snapshot the ORM journal's entry list and snapshot-file set; assert unchanged. On failure, the message should say the generator was probably run and point at the migrations README, not merely report a diff.

**Deletion coverage.** Enumerate every table whose schema has a user-id column (from the code schema or the catalog), then for each, require evidence in the account-deletion handler: a delete statement, a cascading foreign key verified against the migrations, or an explicit documented exemption. Fail listing the uncovered tables.

## Constraint derivation worksheet

Fill one row per candidate column *before* writing the migration:

| Column | Writers (files) | Validators (schemas) | Derived value set | Verdict |
|---|---|---|---|---|
| `orders.status` | checkout service, admin panel, refund job | order schema, admin schema | placed, paid, shipped, refunded, cancelled | Constrain |
| `events.kind` | event logger, import tool, webhook receiver | event schema | login, logout, purchase, import, webhook_received | Constrain |
| `events.source` | set from request metadata | none | (unbounded) | Leave open — free text, noted in header |
| `notes.category` | user input via API | length only | (user vocabulary) | Leave open — user vocabulary, noted in header |

Derivation habits that matter:

- Search for the column name *and* for the values; a writer may build the value in a constant in another module.
- Check validation schemas in every layer; the API schema and the internal schema disagree more often than either is wrong alone.
- Re-derive at review time, not from the worksheet's first draft. The set that ships is the one in the migration header, with exclusions and their reasons beside it.

## Guarded CHECK constraint pattern

The guard compares definitions through a quote-aware normalizer. Ship this helper with the runner bootstrap (beside the ledger DDL) or at the head of the migration that carries the guard; it must exist before the guard runs.

```sql
CREATE OR REPLACE FUNCTION normalize_constraint_def(p_def text)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $func$
DECLARE
  t           text := rtrim(p_def);
  i           integer := 1;
  n           integer;
  c           text;
  result      text := '';
  in_single   boolean := false;
  in_double   boolean := false;
  pending_sp  boolean := false;
BEGIN
  -- pg_get_constraintdef appends ' NOT VALID' to the deparsed definition of
  -- an unvalidated constraint. The suffix encodes validation state, which
  -- convalidated already carries; the guard compares the expression, so one
  -- trailing suffix is stripped here. It can only occur at the very end,
  -- outside any literal (a literal at the end of the definition is followed
  -- by its closing quote and the definition's closing parentheses).
  IF t LIKE '% NOT VALID' THEN
    t := left(t, length(t) - length(' NOT VALID'));
  END IF;
  n := length(t);
  WHILE i <= n LOOP
    c := substr(t, i, 1);
    IF in_single THEN
      result := result || c;
      IF c = '''' THEN
        IF substr(t, i + 1, 1) = '''' THEN
          result := result || '''';
          i := i + 2;
          CONTINUE;
        END IF;
        in_single := false;
      END IF;
    ELSIF in_double THEN
      result := result || c;
      IF c = '"' THEN
        IF substr(t, i + 1, 1) = '"' THEN
          result := result || '"';
          i := i + 2;
          CONTINUE;
        END IF;
        in_double := false;
      END IF;
    ELSIF c ~ '\s' THEN
      IF result <> '' THEN
        pending_sp := true;
      END IF;
    ELSE
      IF pending_sp THEN
        result := result || ' ';
        pending_sp := false;
      END IF;
      result := result || lower(c);
      IF c = '''' THEN
        in_single := true;
      ELSIF c = '"' THEN
        in_double := true;
      END IF;
    END IF;
    i := i + 1;
  END LOOP;
  RETURN result;
END
$func$;
```

```sql
DO $$
DECLARE
  found_def   text;
  found_valid boolean;
  -- The intended definition in normalized form: the output of
  -- normalize_constraint_def (above) applied to pg_get_constraintdef's
  -- deparsed text — case and whitespace folded only outside quoted literals
  -- and identifiers, literal contents preserved byte-for-byte, and any
  -- trailing NOT VALID stripped. Do not hand-write this string: create the
  -- constraint exactly as written below on a scratch database, read
  -- pg_get_constraintdef back, run it through normalize_constraint_def, and
  -- paste the result here. The exact casts in the real output depend on the
  -- column's type.
  intended CONSTANT text :=
    '<normalized pg_get_constraintdef output for the constraint below>';
BEGIN
  SELECT normalize_constraint_def(pg_get_constraintdef(c.oid)),
         c.convalidated
    INTO found_def, found_valid
    FROM pg_constraint c
   WHERE c.conname  = 'orders_status_closed_set'
     AND c.conrelid = 'orders'::regclass;

  IF NOT FOUND THEN
    -- absent: add it
    ALTER TABLE "orders"
      ADD CONSTRAINT "orders_status_closed_set"
      CHECK ("status" IN ('placed', 'paid', 'shipped', 'refunded', 'cancelled'));
  ELSIF found_def IS DISTINCT FROM intended THEN
    -- present on this table, but it is not the derived set: fail loudly.
    -- A silent skip would leave the table guarded by somebody else's set
    -- while the ledger attests to yours.
    RAISE EXCEPTION 'constraint orders_status_closed_set on orders exists with a different definition: %', found_def;
  ELSIF NOT found_valid THEN
    -- the right constraint, landed NOT VALID by an earlier, committed step
    -- and never validated: run the validation instead of re-adding
    ALTER TABLE "orders" VALIDATE CONSTRAINT "orders_status_closed_set";
  END IF;
  -- present, identical definition, validated: a true no-op
END $$;
```

The guard is scoped, never name-only. It matches the constraint name *and* the target relation (`conrelid`), because PostgreSQL allows the same constraint name on many tables — a name-only guard reads a same-named constraint on another table as "already landed" and skips, leaving this table unguarded while the migration records success. And it compares the normalized `pg_get_constraintdef` output against the intended definition, because the same name on the right table can still carry the wrong value set. The comparison is of the expression alone: the normalizer strips the trailing `NOT VALID` that `pg_get_constraintdef` appends to an unvalidated constraint's definition, so validation state never masquerades as a different definition — `convalidated` carries the state and drives the validate branch — and it folds case and whitespace only outside quoted literals and identifiers, so a difference inside a literal (`'PAID'` for `'paid'`, a doubled space) is a different definition, while purely cosmetic differences in the deparsed text are not. Three states get three distinct outcomes (absent: add; identical but `NOT VALID`: validate; different definition: fail loudly, naming what was found), and only the fourth state — present, identical, validated — is a no-op. That is what makes the file replay-safe: a database where the constraint already landed (partial deploy, manual run) does not fail the migration, and a database where something *else* landed under the same name does not quietly pass it either. Remember the constraint validates existing rows at creation; a violating legacy row fails the migration, which is information — clean the data in an earlier migration, not by widening the set.

**Large live tables.** Adding a CHECK constraint scans the whole table while holding an ACCESS EXCLUSIVE lock. Two defences, used together on any table that takes live writes: set `SET LOCAL lock_timeout = '5s';` inside the migration transaction, so a busy table fails the migration fast instead of queueing writes behind the scan; and add the constraint in the metadata-only form, `ADD CONSTRAINT ... CHECK (...) NOT VALID`, which takes only a brief lock — then let that migration COMMIT before `VALIDATE CONSTRAINT` runs, as a separate migration or as a separate committed step. The commit boundary is load-bearing, not a nicety: PostgreSQL holds every lock a transaction acquires until the transaction ends, so an `ADD` and a `VALIDATE` inside one transaction keep the add's ACCESS EXCLUSIVE lock for the entire validation scan, and the weaker-lock benefit never materializes. Only when the add has committed does validation scan under its weaker lock (SHARE UPDATE EXCLUSIVE), which allows concurrent writes. The scoped guard above drives both steps across that boundary: it is what tells a replay whether the constraint is absent (add it, `NOT VALID` on a live table), present but unvalidated (validate it), already validated (done), or present with a different definition (stop and fail) — so a partially landed constraint still replays safely, on either path.
