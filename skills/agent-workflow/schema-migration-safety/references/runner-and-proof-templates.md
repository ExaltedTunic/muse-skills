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
bootstrap ledger DDL
applied := SELECT name FROM schema_migration_ledger

if applied is empty and base schema exists:
    if footprint of newest pre-ledger migration exists:
        BEGIN
          record every listed migration name
        COMMIT
        applied := all listed names        -- adopted; no bodies ran
    -- else: half-built; fall through and replay

for each migration in list order:
    if name in applied: skip (report as recorded)
    if migration is fresh-only and base schema exists:
        record it without running         -- its content is by definition present
        continue
    BEGIN
      run migration body
      record migration name
    COMMIT                                 -- on any error: ROLLBACK, abort the run,
                                           -- name the failed migration
report { appliedNow, skippedRecorded, adoptedPreLedger }
```

**Fresh-only, defined.** A migration is marked fresh-only when it is a squashed baseline: instead of replaying history, it creates the full current schema in one file, and it exists for databases built from nothing. On a database that already has a base schema, everything the baseline creates is by definition already present, so the runner records it without running it (the branch in the pseudocode above). A migration that changes existing objects is never fresh-only; only a baseline squash earns the mark, and the mark belongs in the migration file's header where a reviewer can challenge it.

Rules the pseudocode encodes: the record insert shares the body's transaction; adoption is one transaction and touches no data; a failure aborts the whole run rather than skipping ahead, because later migrations may depend on the failed one.

## Adoption decision table

| Ledger rows | Base schema | Newest pre-ledger footprint | Verdict | Action |
|---|---|---|---|---|
| any | any | any | Ledger is authoritative | Apply only unrecorded migrations |
| none | absent | absent | Fresh | Apply the full list in order |
| none | present | present | Complete pre-ledger | Seed ledger with all listed names, run nothing |
| none | present | absent | Half-built | Replay the list, recording each as it completes |
| migration unrecorded | present | — | Fresh-only baseline in the list | Record it without running; its content is by definition present in the base schema (see the definition above) |

Choosing the footprint: pick an object created *only* by the newest pre-ledger migration — a table, a column, a named constraint. Probe it with the catalog (`to_regclass`, `information_schema`, or the engine's equivalent), not by attempting DDL.

## Proof matrix (disposable database, keep as tests)

| Scenario | Setup | Expected result | What it proves |
|---|---|---|---|
| Fresh apply | Empty database | All migrations run once, all recorded | The list is self-contained and ordered |
| Idempotent rerun | Result of fresh apply | Nothing runs; all reported recorded | The ledger, not file idempotence, carries safety |
| Adoption | Base schema + newest footprint + sentinel data row, empty ledger | Adoption reported; no bodies re-run; sentinel row intact | Pre-ledger databases upgrade without data risk |
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

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'orders_status_closed_set'
  ) THEN
    ALTER TABLE "orders"
      ADD CONSTRAINT "orders_status_closed_set"
      CHECK ("status" IN ('placed', 'paid', 'shipped', 'refunded', 'cancelled'));
  END IF;
END $$;
```

The catalog guard makes the file replay-safe: a database where the constraint already landed (partial deploy, manual run) does not fail the migration. Remember the constraint validates existing rows at creation; a violating legacy row fails the migration, which is information — clean the data in an earlier migration, not by widening the set.

**Large live tables.** Adding a CHECK constraint scans the whole table while holding an ACCESS EXCLUSIVE lock. Two defences, used together on any table that takes live writes: set `SET LOCAL lock_timeout = '5s';` inside the migration transaction, so a busy table fails the migration fast instead of queueing writes behind the scan; and add the constraint in the metadata-only form, `ADD CONSTRAINT ... CHECK (...) NOT VALID`, which takes only a brief lock, then run `VALIDATE CONSTRAINT` as a separate step — validation scans under a weaker lock that allows concurrent writes. The guard query above applies to both steps: check the catalog before adding, and before validating, so a partially landed constraint still replays safely.
