# Lens Catalog and Templates

Companion to `independent-review-swarm`. Pick lenses that match the system under review; not every swarm needs every lens. One reviewer per lens, sized so a single pass covers it deeply.

## Lens catalog

| Lens | Scope | Typical evidence |
|---|---|---|
| Domain / content quality | Correctness of the subject matter itself: facts, language, worked examples, answer keys | Quoted item + the correction, with a source or rule citation |
| Exemplar fidelity | Models, templates, and sample answers measured against the standard they teach (length, required moves, stated criteria) | The exemplar, the standard, the measured gap (counts, not impressions) |
| Assessment integrity | Whether scores mean what they claim: keys correct, totals sum, pass bars enforced, partial work cannot pass | Recomputed totals, traced scoring paths |
| Runtime behaviour | What the running system actually does with the material: rendering, fallbacks, empty states, dead ends | Traced code paths, reproduced states |
| Adversarial claim-testing | The project's own headline claims, attacked one by one | Each claim, the test applied, VERIFIED / CORRECTED / REFUTED / UNVERIFIABLE |
| User walkthrough | The experience end to end in role: first-run, pacing, framing, where a real user stalls | Step-by-step narrative tied to specific screens or items |
| Deploy readiness | Whether the exact target can ship: build, config, secrets scan, rollback surface | Command output, scan results, diff inventory |
| Backend correctness | Server logic integrity: authorization scoping, write paths, evidence/state mutation rules | Route-by-route walk, file-and-line per finding |
| Frontend correctness | Client state bugs: stale state across navigation, paging over live queries, remount behaviour | Component traces, reproduction steps |
| Performance | Measured cost of the shipped surface: payload sizes, query patterns, generation/storage growth | Measurements with method stated, ranked fixes |
| Security | Auth coverage, injection sinks, credential handling, cost-abuse vectors | Route inventory, sink grep results, scenario per finding |
| Tests & gates | Whether the safety net is real: gate numbers reproducible from a clean run, pins honest, skips documented | Independent rerun with full-output logs compared line by line |
| AI / grading systems | Model-graded paths: prompt plumbing, criteria actually reaching the grader, output parsing, clamping, failure handling | Prompt construction traced, malformed-output behaviour |
| Data layer | Schema vs code drift, migration discipline, constraints, indexes, retention | Mechanical list comparisons, drift table |
| Dependencies | Dead packages, vulnerable or outdated ranges, license surprises | Manifest audit, usage grep per suspect package |
| Accessibility | Focus management, keyboard paths, accessible names, contrast, motion/zoom restrictions | Per-barrier reproduction, token/contrast measurements |
| Design system | Token discipline, component reuse, banned vocabulary, drift at the edges | Guard-test results plus manual sweep of outliers |

## Reviewer brief template

```
TARGET: <exact commit / tree / document set>. Note how it differs from what is live.
ROLE: You are a fresh reviewer. You built none of this. Read-only: do not edit the target.
LENS: <one lens>. IN SCOPE: <surfaces>. OUT OF SCOPE: <surfaces>.
EVIDENCE STANDARD: Every finding carries a file-and-line locator and a quoted
excerpt. Rate severity (blocker / major / minor / nit) and certainty
(definite / suspected — if suspected, state what would settle it).
REPORT SHAPE:
  1. Headline verdict, one or two lines.
  2. Findings, most severe first, each with locator, excerpt, and the
     smallest fix that would resolve it.
  3. Scope walkthrough: what you checked and found clean. Silence about a
     surface will be read as "not checked", not as "clean".
DELIVERABLE: the report only. Do not fix anything.
```

## Grading setup template (content work)

```
RUBRIC: <grade scale; what each grade requires, in observable terms>.
EXIT BAR: no item below <floor grade>; weak-grade share (at or below
<weak grade>) under <ceiling>%; measured on raw per-item grades.
GRADERS: fresh agents who authored none of the items. Grade against the
rubric only. Return the raw grade per item plus the rubric clause that
decided any grade at or below <weak grade>.
```

## Synthesis template

```
# Swarm Synthesis — <target> (<date>)

<N> fresh reviewers, none of them builders. Full reports: <location>.
Load-bearing claims verified against source before adoption (marked ✓).
This step is not optional and not sampled away.

## Verdicts at a glance
| # | Lens | Verdict |
|---|------|---------|

## Verified claim checks ✓
- <claim> — VERIFIED / CORRECTED / REFUTED / UNVERIFIABLE, with the locator
  (and, for UNVERIFIABLE, what would settle it).

## Definite fixes vs suspicions
- Definite: <findings whose evidence the synthesizer verified>
- Suspicions: <findings labelled suspected, each with the check that would settle it>

## Pre-existing vs introduced
- <finding>: pre-existing | introduced by the work under review

## Bucket A — fix-now (verified, bounded, no behaviour change)
## Bucket B — owner-call (decision required; finding, options, costs)
## Bucket C — parked (each with its reason)

## Bottom line
<What the work actually is, what the swarm's real catches were, and the
recommended sequence.>
```

## Fix-pass report template

```
# Fix Pass — <date>
Scope: buckets approved by the owner on <date>. Other buckets untouched.

## Gates on the merged tree
<Summary lines quoted from full-output logs, per gate.>

## Per bucket
- <finding>: fix applied; verified by <the original evidence re-run>,
  result <before → after>.

## Pins changed
- <pin> <old> → <new>: <dated reason, tied to the approved fix that moved it>.

## Corrections to the review itself
- <claim>: reclassified on verification — <evidence>. 

## Not done (by design)
- <owner-calls and parked items, restated so the boundary is auditable.>
```
