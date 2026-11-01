---
name: agent-orchestration
description: "Run multi-agent build programs that survive contact with reality: scoped briefs with measured targets and stop conditions, isolated worktrees, a single integrator who merges one branch at a time, and verification that re-derives every claim from diffs and full gate logs instead of trusting worker summaries. Use when a job is split across two or more delegated agents or waves, when several branches must land on one mainline, or when a delegated result will be reported as done."
---

# Agent Orchestration

Delegated work rarely fails in the doing. It fails in the trusting: a coordinator reports tests green from a partial output tail, a worker reports a push that a hook rejected, two parallel branches each coin the same identifier and the merge quietly keeps the wrong one. This skill is the operating method that makes a multi-agent program land intact anyway. It assumes the workers are competent and their reports are still not evidence.

This skill sits **above** `verify-before-shipping`. That skill decides whether one finished change may be called shipped. This skill runs the program that produces the changes: who writes what, in what order it merges, and how every claim gets checked before it is repeated.

## When this applies

- A task is split across two or more delegated agents, coordinators, or waves.
- Several branches, worktrees, or parallel efforts must land on one mainline.
- The output of one agent becomes the input or baseline of another.
- You will report delegated results to someone who cannot see the workers.

A single agent doing a single pass does not need this. Use it when coordination itself is a risk, not as ceremony for small jobs.

## Topology: one integrator, nobody else merges

- **One integrator owns the mainline.** The integrator writes the briefs, assigns bases, merges, runs the final gates, pushes only within the scope the user approved for the program, and reports. Workers and coordinators never merge into the mainline and never push.
- **One worktree and one branch per worker**, all cut from the same named base commit. State the base in the brief; a worker on a stale base manufactures merge conflicts for everyone.
- **Baseline the fresh worktree before anyone builds on it.** Detect existing isolation instead of nesting a new worktree inside one. Confirm the worktree directory is git-ignored before creating anything in it, so a whole tree never gets committed into the repo by accident. Then run project setup and the baseline gate battery in the fresh tree and record the result in the ledger: a dirty baseline reported up front makes every later failure attributable, and one discovered late makes them all ambiguous.
- **Coordinators may fan out to their own workers**, but a coordinator's branch is still just a branch. The integrator integrates coordinator output exactly like worker output: by reading it.
- **Merge one branch at a time.** After each merge, run the gate battery on the combined tree before merging the next. Parallel merges hide which branch broke the tree.
- **The integrator does the integration work personally**: conflict resolution, cross-branch deduplication, and any fix pass the combination needs. That work is part of the program, not an admission that a worker failed.

## Brief anatomy: two layers, no improvisation

Every delegation gets two documents. Workers should never have to guess a standing rule.

**The shared brief** (one per program or wave-set) carries everything that must not vary between workers:

- Standing project rules the workers cannot see from their slice (invariants, forbidden edits, frozen files).
- Shared-resource policies: which external stores, generators, or services everyone touches, and the rule for switching or stopping (for example: generate with the primary tool until it refuses on quota, then the named fallback, and report which tool produced which artifact).
- Credential handling: fetch per use from the secret store, hold in a restricted temp file, destroy after use, never commit, log, or quote a value.
- The quality bar, stated as checkable conditions, not adjectives.
- The gate list and the reporting contract (below).

**The scoped brief** (one per worker) carries only that worker's slice:

- **Exact scope**: the modules, files, or surface owned, and the base commit.
- **Measured targets**: numbers the worker must hit and can measure (counts, sizes, minutes, percentages), with the measurement method named when it is not obvious.
- **Stop conditions**: the discoveries that mean "stop and report instead of improvising" (a needed migration nobody scoped, a missing asset, a rule conflict). A worker who hits a stop condition and reports has succeeded.
- **Explicit out-of-scope lines**: the neighbouring work that belongs to other workers or later waves. Most cross-branch damage comes from helpful workers wandering.
- **What may legitimately move**: which pins, ratchets, or counts this work is expected to change, and the form of the justification (a dated in-file comment explaining the delta).
- **Reporting contract**: per item, what was produced (ids, counts, totals measured not estimated), commit hashes, provenance for every generated artifact, and anything found but left undone, with reasons.
- **Dispatch configuration**: where the platform lets you choose the worker's model or effort level, choose deliberately by task complexity and state the choice here. Turn count beats token price: the cheapest worker routinely takes two to three times the turns on multi-step work and costs more overall, so reserve the cheapest tier for mechanical, fully specified tasks.

A brief template with fill-in sections is in `references/brief-template.md`.

## The program ledger

Every program keeps one ledger file, and its first line names the program or plan it belongs to; a ledger naming a different program is not yours to write in. The ledger records each task's completion with its commit range, every fix round and its outcome, and every ruling the integrator makes along the way.

The ledger outranks memory. After any interruption or compaction, the integrator resumes from the ledger and the git state, not from recollection: items the ledger marks complete are not re-dispatched, and a task left mid-fix-loop resumes at the next round. A program run from memory alone eventually re-dispatches finished work and loses rulings nobody wrote down.

## Pre-flight: the conflict scan

Before the first wave is dispatched, scan the briefs against each other and write the scan down. One row for every pair of workers that share a file or an interface: what one produces, what the other consumes, and what the scan found. One row for every brief checked against itself: measured targets against scope, scope against stop conditions. Rule on every conflict the scan surfaces and record the ruling in the ledger before dispatch. A scan reported as "clean" with no rows behind it is not a scan that ran.

## Verification discipline: summaries are claims

Treat every worker report the way `verify-before-shipping` treats a green checkmark.

- **Re-derive from the diff.** Read the actual changes. Confirm the counts, totals, and identifiers in the report exist in the tree, spelled the way the report spells them.
- **Gates capture full output to files.** A pass claim cites the summary lines from the log file. Never accept a result judged from the last screenful of output; failures hide above the tail.
- **The integrator re-runs the decisive gates on the merged tree** before reporting any branch as landed. A branch that was green alone can be red in combination, and combination is the state that ships.
- **A push is real only when the remote ref is read back** at the expected commit. An attempted push, a hook that usually passes, and a worker's word are all non-evidence.
- **Deployment is verified at the destination**: the deployed commit matches, a health endpoint answers, and at least one artifact unique to this change is fetched live. "Merged" is not "live".
- **A worker's false green is a known failure mode**, not a scandal. When you catch one, say what the log actually showed, fix forward, and tighten the reporting contract for the next wave. The worked antidotes are in `references/incident-playbook.md`.
- **Review dispatches stay clean.** Never instruct a reviewer to ignore or downgrade a class of finding ("do not flag X", "at most Minor"). A suppressed finding is not a resolved one; findings are adjudicated when they come back, in the fix loop, where the adjudication gets written down.

## The fix loop: capped rounds, written adjudication

When review of a worker's branch produces findings, they are fixed in rounds on the worker's branch; workers still never merge, and the integrator re-verifies every round. The loop is capped at five rounds per task or branch:

- **Rounds 1-3 resume the original worker.** It holds the context of its own choices; send it the open findings verbatim.
- **Rounds 4-5 hand the branch to a fresh worker**, with the brief, the original worker's report, and the open findings. A loop that survives three resumes usually means the original worker cannot see its own problem; fresh eyes are the fix, not a sixth resume.
- **Every round ends with a scoped re-review** that verdicts each finding addressed or not addressed, and examines only the fix diff for new breakage. New critical or important breakage in the fix diff joins the open findings; observations outside the diff go to the ledger, not the loop.
- **Minor findings never enter the loop.** Record them in the ledger as they arrive and triage them at the final review; a roll-up nobody reads at the end is a silent discard with extra steps.
- **At the cap, the integrator adjudicates in writing.** Each still-open finding is either parked with a ruling (why the code stands, or why it is real but deferred) or ruled on with the smallest load-bearing fix that unblocks dependent work. Adjudicating early to end a loop early is pre-judging by another name, and discarding a finding silently is forbidden at any round.

Record each round in the ledger as it closes: findings addressed, findings still open, and the commit range it produced.

## Merge arithmetic: preserve both sides, let gates arbitrate

Parallel branches change the same counters, registries, and manifests. Resolve conflicts by rule, not by picking the side you read last:

- **Additive counts combine.** If branch A moved a total from 100 to 130 and branch B moved it to 120, the merged expectation is 150, not either number. Compute the combination, write it with a comment showing the arithmetic, and let the gate confirm or correct it.
- **Keyed collections union by key.** Manifests, registries, and catalogs merge as the union of entries, keyed by their natural id. One side's entries never silently replace the other's.
- **Identical generated artifacts dedupe by content.** If two branches generated the same artifact and its name or hash derives from its content, identical names mean identical inputs: keep one copy. If the contents differ under one name, that is a real collision; stop and resolve it deliberately.
- **Duplicate concepts get rewired to one canonical entry.** When two branches independently add the same concept under different ids, keep one id, rewrite the other branch's references to it, and remove the duplicate entry. Shipping both teaches the system the concept twice.
- **Both-sides-preserved is the default.** A resolution that deletes one branch's work to end the conflict is a last resort and gets reported as a loss, not absorbed silently.
- **Gates arbitrate the true numbers.** After resolving by arithmetic, run the battery. Where a measured value disagrees with your computed expectation, the measured value wins and the pin is corrected to it, with the delta explained in a dated comment. Never adjust a pin blind to make a red gate turn green.

## Integration sequence

For each branch, in order:

1. Read the worker's report against the diff; list every claim you could not re-derive.
2. Merge the branch alone onto the current mainline.
3. Resolve conflicts by the merge arithmetic above.
4. Do the integration fixes the combination needs (dedupe, rewiring, completion passes one branch left visibly undone) as integrator commits, labelled as such.
5. Run the full gate battery on the merged tree, full output to log files.
6. Only then merge the next branch.

At the end of the program: one final battery on the final tree, push (within the recorded approval boundary; if the boundary does not cover this push, stop and obtain approval first), read the remote ref back, verify the deployment live, then write the closeout report from the logs, including what was left undone and why.

## Reporting

Report the program the way the evidence supports: per wave, what landed (measured), what the gates said on the merged tree (quoted from logs), what integration work the combination required, and what remains open with its reason. A closeout that lists only successes teaches the next program to hide its seams.
