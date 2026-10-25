---
name: deep-review
description: "The depth standard for any review pass: an exhaustive scrub that treats every load-bearing claim in the material as a claim to verify against a real anchor, plus a feasibility check, and reports issues found and coverage checked rather than impressions. Use whenever asked to review, audit, check, proof, or pass over code, content, documents, plans, or data, and whenever a sync, migration, or template fill carries values from one place to another."
---

# Deep Review

Most failed reviews were never lazy. They were the wrong job done carefully: the document was proofread, the sync was completed, the summary was accurate, and the wrong value sitting in plain sight survived all of it because nobody's job, as they understood it, was to check whether the value was true. This skill fixes the job definition. A review is an audit against reality whose purpose is to find what is wrong.

## The core rule

Reviewing something means checking its claims against reality and reporting where they fail. Syncing, summarizing, restyling, reformatting, and confirming are different jobs, and none of them is a review, even when done on the same material in the same sitting.

When a task mixes jobs ("sync this into the template," "move these entries into the new sheet and check it over"), the review component does not shrink to fit the carrying work. Every value the sync carries across is validated at its destination as if it were newly written there. A value does not become true by being copied carefully.

## Every load-bearing claim is a claim to verify

A claim is anything a reader will rely on: a number, a date, a dose, a duration, a price, a count, a name, a quoted sentence, a stated limit, a promised behaviour. For each one, the review asks two questions:

- **What is the anchor?** The verified source the claim can be checked against: the source document, the label, the system's own records, the logged or measured actual, the earlier verified version. Check against the anchor, not against plausibility, memory, or the claim's own internal consistency. If no anchor exists, the claim is unverifiable, and the review says so instead of letting it pass by default.
- **Could this value be real?** The feasibility sniff test: is this number the right size for the kind of thing it describes? A human performance, a physical quantity, a price for that category, a duration for that process. Anchors catch transcription errors; the sniff test catches values that were faithfully copied from the wrong place.

The canonical failure is the copied value. A figure that is correct for item A is carried onto item B, where it is absurd, and survives multiple passes because each pass checked the copy's fidelity, not its truth. Neutral example: a spec sheet lists a 250 W motor drawing 1.1 A; the 1,500 W model is added to the same table and inherits the 1.1 A cell. The number is formatted perfectly, spelled perfectly, and wrong sixfold. Two proofreads miss it. A reviewer who treats the cell as a claim ("what should a 1,500 W motor draw?") catches it in seconds. When you find one copied value, check its neighbours: values travel in packs.

## How to run one

- **Inventory before reading.** List the categories of load-bearing claims the material makes (quantities, dates, names, quotations, cross-references, behavioural promises) so coverage is a checklist, not a hope.
- **Name the anchor for each category up front.** If a category has no anchor, decide how it will be handled (feasibility only, flagged as unverifiable) before starting, not after skipping it.
- **Check mechanically where a machine can.** Recompute totals, re-derive counts, diff the quotation against the source, run the command the document tells the reader to run. Mechanical checks do not get tired at item 140.
- **Record verdicts as you go.** Each claim or category ends in exactly one state: checked and clean, definite issue, or suspicion. A category with no recorded state was not reviewed, whatever the intention was.
- **Finish the asked scope before widening.** Complete coverage of what the review was commissioned to cover comes first. Interesting problems outside the scope are noted, not chased, until the scope is done.

## Definite errors and suspicions are different lists

- **Definite:** proven wrong against an anchor. The finding names the claim, the anchor, and the discrepancy. These are the review's hard output.
- **Suspected:** flagged by the sniff test or by pattern, not yet proven. Suspicions are reported in their own list, labelled as unverified, each with the check that would settle it.

Never promote a suspicion into the definite list because it feels right, and never quietly drop a suspicion because it could not be settled in the time available. A suspicion that disappears silently will be rediscovered later as a defect; a suspicion labelled honestly costs the reader one glance.

## Coverage is the deliverable

The review's output has two halves, and both are mandatory:

- **Issues found,** each with evidence and the anchor it failed against.
- **What was checked and found clean,** enumerated by category, so the reader can see the shape of the coverage.

A review that finds nothing states its coverage in full; the enumeration is what makes "nothing found" a result instead of a shrug. "Looks good," "seems fine," and a summary of what the material says are not review output. Neither is a list of changes made during a sync: changes are the sync's output, and they say nothing about what was verified.

## Scope discipline

The review covers what it was asked to cover, completely. If the work itself reveals that the commissioned scope was wrong (the real risk sits in the adjacent system, the asked-for section is a copy of an unreviewed original), say so explicitly in the deliverable, as its own point. Do not silently expand the review and deliver a thinner pass over a bigger area, and do not silently shrink it and let the report imply the original coverage. Scope changes are findings about the job, and they belong in the open.

## Review the review

Before delivery, the reviewer's own output goes through the same standard once: every finding re-read against its anchor, every quoted discrepancy re-checked at the source, every count in the report recomputed. A review that contains an unverified claim about the material has failed at its own job in the most embarrassing way available. This pass is short; it is also where the copied value in your own table gets caught.

## Composition

This skill is the depth standard for a single review pass: how thoroughly one reviewer checks. It composes with `independent-review-swarm`, which supplies what depth alone cannot (reviewers who did not build the work, assigned lenses), and with `verify-before-shipping`, the final gate that requires runnable evidence before anything is called done. A swarm run at skim depth is still a skim; a deep pass by the builder is still the builder. Use them together when the stakes earn both.
