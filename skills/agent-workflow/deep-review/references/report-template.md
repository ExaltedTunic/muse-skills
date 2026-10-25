# Deep Review Report Template

The deliverable's shape. Both halves are mandatory: the issues and the coverage. A report with only one half is not finished.

## Header

- **Material reviewed:** what it is, which version or state (date, revision, source location).
- **Scope as commissioned:** what the review was asked to cover.
- **Scope as executed:** identical to the above, or the difference stated explicitly with the reason.
- **Anchors used:** the verified sources claims were checked against, listed by category.

## Definite issues

One entry per issue, in the order a reader should act on them:

| # | Claim (as it appears) | Where | Anchor checked | Discrepancy |
|---|---|---|---|---|
| 1 | The exact value, sentence, or statement | File/section/line or page | The source of truth it was tested against | What the anchor says instead, with the size of the gap |

Rules for this list:

- Every entry was proven against its anchor. If it was not proven, it does not belong here; it belongs in Suspicions.
- Quote the claim exactly. A paraphrased claim cannot be re-checked by the reader.
- When one copied value is found, its neighbours were checked, and the result of that sweep is stated in the entry or in Coverage.

## Suspicions

| # | Claim | Why it is flagged | The check that would settle it |
|---|---|---|---|
| 1 | The exact value or statement | Sniff-test failure, pattern match, internal tension | The anchor, query, or test that would prove or clear it |

Suspicions are labelled unverified wherever they are mentioned, including summaries of this report. They are never deleted for being unsettled; an unsettled suspicion is carried forward visibly or handed to the owner as an open item.

## Coverage (checked and found clean)

Enumerated by category, not by adjective:

- Quantities and totals: recomputed / diffed against [anchor], N items, all match.
- Dates and deadlines: checked against [anchor], N items, all consistent.
- Names and identifiers: checked against [anchor], N items, all exact.
- Quotations: diffed character-for-character against [source], N items, all exact.
- Cross-references: every pointer followed, N items, all resolve.
- Behavioural promises: exercised where runnable, N items; the remainder listed as unverifiable with the reason.

A category that was not checked is listed here too, marked NOT CHECKED with the reason. Hidden gaps in coverage are the failure this section exists to prevent.

## Unverifiable claims

Claims for which no anchor exists, listed explicitly with what an anchor would have to be. Passing them silently is not an option; the reader decides whether to accept them.

## Verdict

One short paragraph: the count of definite issues, the count of suspicions, whether the material can be relied on as reviewed, and any scope finding (the commissioned scope was wrong, and how) stated plainly.
