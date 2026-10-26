# Brief Template

Two documents per delegation. The shared brief is written once per program or
wave-set and referenced by every scoped brief. Keep both short enough that a
worker actually reads them; put standing rules here, not in chat messages the
worker may never see.

## Shared brief (one per wave-set)

```markdown
# <Program>, <Wave-set> — shared rules for all coordinators

Base for every branch: `<commit>` (current mainline, live). One worktree and
branch per coordinator, named in your assignment. Never push. Commits under
the repo identity; never override it. <Integrator> is sole integrator; waves
merge one at a time.

## Approval boundary
- May be pushed or published without re-asking: <targets, branches, releases,
  or other actions covered by the user's approval for this program>.
- Needs fresh approval before action: <anything outside that recorded scope>.

## Standing project rules
- <Invariant 1, stated as a checkable condition.>
- <Frozen surface: what must not be edited, and what to do if the work seems
  to require editing it: stop and report.>

## Shared-resource policy
- <Generator/service everyone uses, the switch-or-stop rule, and the
  provenance reporting it requires: which tool produced which artifact.>

## Credentials
- Fetch <credential> per use via <secret-store route>. Hold it only in a
  restricted temp file (0600), use it, then destroy it. Never commit, log,
  or report a credential value.

## Quality bar
- <Standard 1, checkable.>
- <Standard 2, checkable.>

## Gates and reporting
- Full gates on your branch tip: <gate list>. Capture full output to
  `<log dir>/<wave>-gate-*.log` and quote the summary lines from the files
  in your report. A claim without a log line does not count.
- Report per item: what was produced (ids, counts, totals measured — not
  estimated), commit hashes, provenance for every generated artifact, and
  anything found but left undone, with reasons.
- Exit bar applied at integration: <the standard merged work must meet>.
```

## Scoped brief (one per worker)

```markdown
# <Program>, <Wave X> — <slice name>

Read the shared brief first; it is part of this brief.
Worktree `<path>`, branch `<branch>`, base `<commit>`.

## Scope — <owned surface> only
1. **<Work item>**: <what to produce>. Target: **<measured range or count>**,
   measured by <method>. <Quality conditions specific to this item.>
2. **<Work item>**: ...

## Rules specific to this slice
- <Pins this work may legitimately move, and the justification form
  (dated in-file comment explaining the delta). No other pin moves.>
- <Stop conditions: discoveries that mean stop and report.>

Out of scope: <neighbouring surfaces owned by other workers or later waves,
named explicitly>.
```

## What the template is doing

- **The base commit is named in both layers.** A worker who starts from the
  wrong base manufactures conflicts the integrator pays for.
- **Targets are ranges with a measurement method**, not vibes. "Improve
  coverage" cannot be verified; "+8,000 to +10,000 words, measured on the
  assembled pack" can.
- **Stop conditions are successes.** Naming them in advance converts a
  worker's hardest judgement call ("do I improvise here?") into a report.
- **The out-of-scope line is load-bearing.** Most cross-branch damage is a
  helpful worker fixing something in a sibling's slice.
- **The reporting contract is quoted log lines or it did not happen.** This
  single clause prevents the majority of false-green incidents.
