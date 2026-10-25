---
name: schema-migration-safety
description: "Make hand-written SQL migrations trustworthy: an applied-migration ledger whose row is written in the same transaction as the migration body, an evidence-based adoption rule for databases that predate the ledger, a test pinning the runner's list to the migration directory, a frozen ORM journal, drift audits between the schema code and the migrated reality, and CHECK constraints whose value sets are derived from the code's own writers. Use when a project applies migrations by hand or at build time, when nobody can say exactly which migrations a given database has run, or before adding constraints, retention, or deletion logic on top of an unverified schema history."
---

# Schema Migration Safety

The dangerous state is not a broken migration. It is an *unrecorded* one. A project drifts into it innocently: migrations are hand-written files, a build script replays them and relies on every file being idempotent forever, the ORM's generated journal froze at some early migration and was never updated again, and the schema mapping in code describes the database the author *intended*, not the one that exists. From then on, three sources claim to describe the schema (the code, the files, the live database), none of them is provably complete, and every later change (a constraint, a deletion cascade, a retention job) is built on a guess. This skill is the retrofit that makes the history provable again, and the discipline that keeps it that way.

## The ledger: record in the same transaction

Keep a ledger table in the database itself: one row per applied migration, keyed by migration name. The rule that makes it trustworthy is transactional, not procedural:

- **The ledger row is written in the same transaction as the migration body.** A migration that fails rolls back unrecorded, so it will be retried; a migration that commits is recorded, so it never runs twice. Never record before applying, never record in a separate step after.
- **The runner consults the ledger, not the files.** On each run it applies only listed migrations with no ledger row, in order. Idempotence stops being a load-bearing property of every historical file.
- **Bootstrap is chicken-and-egg; solve it explicitly.** The ledger table must exist before the runner can decide whether the migration that creates it still needs to run. Carry the ledger DDL in the runner as a `CREATE TABLE IF NOT EXISTS`, and let the registered migration file carry the identical DDL as the reviewable record. Both are idempotent, so the two paths can never conflict.

## Adoption: databases that predate the ledger

Existing databases have run some unknown prefix of the list. Do not re-run everything (the files were written for a younger schema) and do not seed the ledger on a hunch. Decide from evidence:

- **Fresh:** no base schema. Apply the full list in order, recording each.
- **Complete pre-ledger:** the ledger is empty, the base schema exists, *and* the footprint of the newest pre-ledger migration is present (an object only that migration creates). The old process applied the list in order on every successful run, so the newest footprint proves the whole prefix ran. Seed the ledger with every listed name, in one transaction, touching no data.
- **Half-built:** base schema exists but the newest footprint is missing. Fall back to replaying the list, recording each migration as it completes. This is only safe if the pre-ledger files really are idempotent; verify that claim on the oldest files before trusting the fallback, and say so in the commit.

The footprint must be the *newest* migration's, not a convenient one. An older footprint proves an older prefix and would seed a lie.

## Prove the runner before you trust it

Worked templates for everything in this skill — the ledger DDL, the runner algorithm, the adoption decision table, the proof matrix, and the constraint derivation worksheet — are in `references/runner-and-proof-templates.md`.

Run the whole matrix against a disposable local database (an embedded or throwaway instance; never production) and keep the tests:

1. **Fresh apply:** empty database, full list applies, every migration recorded, result lists exactly what ran.
2. **Idempotent rerun:** second run applies nothing and reports everything as already recorded.
3. **Adoption:** a database built to the pre-ledger state (base schema plus newest footprint, plus a sentinel data row) adopts without re-running bodies, and the sentinel row is untouched.
4. **Failure atomicity:** a deliberately broken migration aborts, rolls back, and leaves no ledger row; the run reports which migration failed.

If any path is unproven, the ledger is a hope, not a record. Follow verify-before-shipping for the evidence standard: capture full output, cite summary lines.

## Registration discipline

A migration file that is not in the runner's list does not exist, however good its SQL is. Make that failure loud and immediate:

- **Register in the same change.** The commit that adds the file adds its entry to the build's run list, in order. Splitting them across commits is how a migration ships to every environment except the one that matters.
- **Pin list to directory with a test.** Assert the runner's list equals the migration directory's contents exactly: same names, no extras, no gaps. A file added without registration, or a registration without a file, fails the build.
- **Never edit an applied migration.** The ledger keys on the file's identity and it runs once; an edit to a shipped file silently never reaches any database that already ran it. Corrections are new migrations.

## Freeze the ORM generator

Once migrations are hand-written, the ORM's generate/push commands become the hazard: they diff the code schema against the frozen journal snapshot and would emit a mega-migration recreating years of schema, or bypass the ledger and apply the code schema directly.

- **Freeze the journal where it is.** Do not regenerate it, do not delete it; its staleness is the point.
- **Put the stop warning where hands actually land:** a banner at the top of the ORM config file ("migrations here are hand-written; do not run generate or push; the journal is frozen on purpose and here is why"), and a short README *in the migrations directory* describing the hand-written flow: how to add a file, the registration rule, the ledger, the prohibitions.
- **Pin the journal with a guard test** that fails if the journal entries or snapshot set change. Treat that failure as "someone ran the generator," not as a test bug.
- **The schema mapping in code is a query-builder convenience, not schema truth.** The applied migrations are the truth. Say so in the README, because every newcomer will assume the opposite.

## Drift audit: code schema versus migrated reality

With the ledger in place, audit the gap between what the code declares and what the migrations create: referential actions on foreign keys, nullability, defaults, constraint presence. Work item by item:

- For each difference, decide which side is the long-standing behaviour. Runtime code usually already compensates for the database as it actually is; in that common case the database is the truth and the *declaration* is the bug. Fix the code to match the migrated reality, with a comment citing the migration that created the real behaviour.
- Fix the database instead only when the code's behaviour is the intended one and a new migration can move the database deliberately, with the evidence cited in the commit.
- Correct stale comments that describe the wrong behaviour. A comment claiming a cascade the migration never created is tomorrow's data-loss bug, because someone will eventually believe it and stop compensating.

## CHECK constraints from derived closed sets

Some text columns are enums in all but name: a status, a tier, an event type, written by a handful of code paths and validated in a few schemas. Give them CHECK constraints, but derive the value set; never write it from memory:

- **Enumerate every writer and validator** of the column across the codebase: route handlers, services, background jobs, seed scripts, and the validation schemas. The set is the union. Derivation has a known failure mode: the one writer nobody remembered (a feature in another subsystem appending its own event type) is exactly the value a hand-written list omits, and the constraint then rejects live traffic.
- **Document exclusions in the migration header.** Columns that are genuinely open vocabularies or free text stay unconstrained *on purpose*; the header says which columns were considered and why each was left open, so a future reader does not "fix" the omission.
- **Write replay-safe DDL:** guard each constraint's creation (check the catalog first, or an equivalent idempotent form) so the file can run against a database where it partially landed. Note honestly that a CHECK validates existing rows when added: run it against a production-shaped copy first if the table is large or the data is suspect.

## One clock, owned retention, proven deletion

Three smaller disciplines that belong to the same hardening pass:

- **One clock.** Application code that reasons about "today" (due queues, streaks, daily plans) takes the date from a single resolver, typically the client's local date passed in and threaded through. A mix of the database's `CURRENT_DATE` and application dates guarantees off-by-one behaviour at timezone edges that no test in the office timezone will catch. Grep for the database clock in application code; the one legitimate home for it is inside migrations and defaults.
- **Retention needs an owner and a horizon.** Telemetry and event tables grow forever until someone decides: name the mechanism (an admin-triggered prune endpoint is enough where no scheduler exists), the horizon (a rolling window, stated in days), and the protected set. Learning, billing, and audit history are never pruned by a telemetry cleanup; enumerate them as untouchable in the same change.
- **Deletion coverage is a test, not a claim.** Account deletion must reach every table keyed by the user. Write the test that enumerates all user-keyed tables from the schema and requires deletion evidence for each in the deletion handler. When a new user-keyed table lands without a deletion path, the test fails, which is the only reliable moment to notice.

## Reporting

Report the state of the history, not just the change: which of the proof matrix paths ran and their results, whether the target database adopted, replayed, or applied fresh, any drift items found and which side was corrected for each, and the constraint sets with their derivations and exclusions. If a database's state could not be inspected, say the history there is still unproven rather than letting the green local proofs imply it.
