---
name: independent-review-swarm
description: "Commission an independent multi-reviewer audit of a finished body of work: fresh reviewers who built none of it, one lens each, findings backed by file-and-line evidence, every load-bearing claim re-verified by the synthesizer before it is adopted, and a fix proposal bucketed into fix-now, owner-call, and parked. Use before shipping a large stack, after a multi-agent build program, or whenever the people who did the work would otherwise be the ones grading it."
---

# Independent Review Swarm

A body of work reviewed by the people who produced it converges on what they already believe. The builders know which parts they were careful with, so they look there; the defects live where nobody looked. A swarm breaks that: fresh reviewers who built nothing, each assigned one narrow lens, reporting to a synthesizer whose job is verification, not authorship.

## The core rule

Reviewers must not be builders. Every reviewer is a fresh agent with no stake in the work and no authorship in it. Commission each reviewer with the fixed target, the requirements, and a neutral brief that excludes builder verdicts and conclusions until the reviewer has recorded independent findings. The commissioning agent does not review its own program: it assigns lenses, collects reports, verifies claims, and synthesizes. If you built part of the stack, you may verify other people's claims about it, but your own reading of it is not a review.

## When this applies

- Before shipping a large accumulated stack, especially one assembled by multiple agents or sessions.
- After a build program where grading, review, and construction were done by the same hands.
- When a project's own claims about itself ("coverage is 98%", "the gates are honest", "the content is safe to learn from") have never been tested by anyone who didn't write them.

Scale the swarm to the surface. A handful of lenses suits a small stack; a full program can earn fifteen to twenty. One lens per reviewer, always: a reviewer asked to cover everything covers nothing deeply. Set and record a review budget before commissioning (reviewer count, passes, time, or spend); expanding it is an owner decision, not a silent overrun.

## Step 1: Freeze the target

Name the exact state under review: the commit, tree, or document set, and how it differs from what is live. Reviewers review a fixed target, not a moving one. State the target in every brief, and state whether reviewers are read-only (default: yes; a reviewer who edits the target destroys the evidence for everyone else).

## Step 2: Assign lenses

Decompose the review into independent lenses, each sized so one reviewer can cover it deeply in one pass. Typical lenses for a software-plus-content system: domain/content quality, exemplar fidelity, assessment integrity, runtime behaviour, backend correctness, frontend correctness, security, data layer, performance, dependencies, accessibility, design system, tests-and-gates reproducibility, AI / grading systems, deploy readiness, and a user walkthrough. The full catalog with scope notes is in `references/lens-catalog-and-templates.md`.

Always include one **adversarial lens**: its job is to test the claims the project makes about itself, one claim at a time, and try to refute them. Headline metrics survive because nobody attacks them; this lens exists to attack them.

Give every reviewer the same four things:

- **Scope:** the lens, the surfaces in bounds, the surfaces out of bounds.
- **Evidence standard:** every finding carries file-and-line evidence (or the equivalent locator in non-code material) and a quoted excerpt. A finding without a locator is an opinion, and gets reported as one.
- **Severity and certainty:** each finding is rated for severity and labelled **definite** (the evidence proves it) or **suspected** (the evidence suggests it; state what would settle it).
- **Report shape:** headline verdict first, then findings, then an explicit list of what was checked and found clean. "Clean" is a result; silence about a surface is not.

## Step 3: Grade content with graders, not impressions

When the work under review is content (lessons, exercises, documents, generated media), reviewers grade rather than opine:

- Publish the rubric and the exit bar **before** grading starts: the grade scale, what each grade requires, and the pass conditions for the whole set (for example: no failing grades anywhere, and the share of weak grades under a stated ceiling).
- Graders are fresh, like reviewers, and grade against the rubric, not against their own taste.
- Collect **raw grades per item**, not summaries. The distribution is the finding; an average hides the tail the exit bar exists to catch.

## Step 4: Verify every load-bearing claim before synthesis

Reviewer reports are claims, not facts. Before any claim enters the synthesis, the synthesizer re-checks it against the source: open the file, read the lines, rerun the count. This step is not optional and not sampled away for the claims the decision will rest on.

Expect three failure modes, all observed in practice:

- **Rendering artifacts.** A reviewer quotes a string that does not exist in that form in the source; the underlying text was already compliant. Check codepoints and exact bytes before adopting a "definite error."
- **Plausible, wrong, and alarming.** A confident claim about the data layer or the security posture that is simply false at the tree under review. The more consequential the claim, the more mechanical the check must be.
- **Stale quotes.** The reviewer read an older rendering of a file; the live defect nearby is real but different from the one quoted. Fix the live defect, record the claim as corrected.

Use exactly four dispositions for every claim: **VERIFIED**, **CORRECTED**, **REFUTED**, **UNVERIFIABLE** (with what would settle it). Refuted means the claim was checked against the source and is false. Corrected means the live defect nearby is real but different from the one the reviewer quoted. A claim corrected in the safe direction is still corrected; synthesis that silently upgrades reviewer claims into facts is how bad fixes get shipped.

## Step 5: Synthesize

The synthesis is a decision document, not a collage of reports. Its shape:

- **Headline verdict per lens**, one line each, in a table. A reader who stops here knows the state of the system.
- **Lenses not run:** list every commissioned lens that did not run, with the reason. An unrun lens is missing coverage, not a clean result.
- **The definite-fix list**, separated from suspicions. Definite findings with verified evidence go on the list; suspected findings are named as suspected, with the check that would settle them.
- **Pre-existing versus introduced.** For every material finding, say whether the work under review introduced it or merely inherited it. The distinction decides urgency and prevents a review of one stack from becoming a referendum on the whole history of the project.
- **A fix proposal in three buckets:**
  - **Fix-now:** verified, bounded, no change to intended behaviour or scope.
  - **Owner-call:** real findings whose fix is a scope-setting decision only the owner can make: a behaviour change, a product trade-off, a policy choice. Present the finding, the options, and the cost of each. Never auto-fix an owner-call, and never bury one inside fix-now.
  - **Parked:** real but not now, each with the reason recorded (depends on a future program, needs an external asset, deliberately accepted risk). Parked without a reason is just dropped.

## Step 6: Run the fix pass under the same discipline

- The owner approves buckets, not vibes. Work starts on approved buckets only.
- **Verify fixes item by item against the finding**, not against the fixer's summary. The reproduction or evidence that established the finding is re-run after the fix; both outcomes are recorded.
- When verification shows the original observation was itself misread (a transcript mistaken for a model, a duplicate that is actually a deliberate variant), reclassify it in the report with the evidence. Do not quietly fix or quietly drop it.
- **Re-pins and count changes carry dated reasons.** Any test pin, baseline, or threshold moved by a fix gets an in-place comment saying what changed, why, and when. A pin moved silently teaches the next reader that pins are negotiable.
- Frozen exceptions are recorded as frozen, with the reason (for example, text bound to a recording that cannot change without re-recording), not edited into a desync.

## Boundary

This skill commissions **your own** independent review of your own work. Verifying a review that an outside party produced and someone relayed to you is a different job (intake of foreign claims); the claim-verification step here borrows its discipline, but the swarm's reviewers are yours, briefed by you, and answerable to your evidence standard.

## Reporting

Report in the shape the verification supports: verdicts per lens, the verified definite-fix list, the claims that were corrected or unverifiable, and the three buckets with the owner-calls stated as decisions, not as findings. Never report a reviewer's green as the swarm's green until the synthesizer's own checks have run.
