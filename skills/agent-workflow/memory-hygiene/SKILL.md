---
name: memory-hygiene
description: "Audit an agent's long-term memory files on a cadence: merge duplicates, retire stale threads, resolve contradicted facts, propagate corrections, and hold the curated file to a density ceiling. Use when memory files grow, contradict themselves, or on a scheduled review."
---

# Memory Hygiene

An agent's memory fails the way a desk does: not all at once, but by accumulation. A fact gets written twice in different words. A plan changes and the old plan stays, still sounding current. A thread ends and its "pending" note keeps asking for follow-up forever. Eventually the file is long, mostly true, and quietly untrustworthy, and the agent starts confidently citing things that stopped being the case months ago. Hygiene is the scheduled pass that keeps memory an asset instead of a sediment.

This skill assumes the common shape: one curated long-term file (call it MEMORY.md) loaded every session, plus dated daily logs that hold the raw history. Adapt the names to your platform; the operations are the same.

## When to run it

- On a cadence. Monthly suits an active setup; quarterly is the floor. Put the cadence on a schedule or a session-start checklist that actually fires, not in a note to self.
- When the curated file passes its density ceiling (see below).
- When the user corrects the same fact twice. The second correction means the first one did not propagate.
- Before sharing, exporting, or migrating memory. Hygiene and scrubbing are different passes (this one is about truth and shape, not privacy), but a stale file should not travel.

## Measure first

Run the bundled `scripts/memory_audit.py` over the curated file and the recent logs. You want the starting facts: line and word counts, the section inventory, and any exact-duplicate lines. Report them before you touch anything; they are also how you prove the pass did something.

## The pass, in order

1. **Merge duplicates.** The same fact recorded twice, in the same words or different ones, becomes one entry: the clearest wording, the most context, the latest date. Duplicates are not harmless; when one copy gets corrected and the other does not, the file starts contradicting itself, which is worse than either version alone.
2. **Resolve contradictions.** Where two entries disagree, find out which is current: the user's latest explicit statement beats an older note, a verified record beats a recollection, and anything you cannot settle goes to the user as a question, not a coin flip. The curated file must end the pass with one version of every fact. The losing version's history, if it matters, lives in the dated logs, marked as superseded there.
3. **Retire dead threads.** Finished projects, past events, resolved follow-ups, and plans the user abandoned get closed: outcome recorded in a line, or the entry removed from the curated file entirely. A "pending" that has been pending past its own deadline with no movement is either re-confirmed with the user or retired. Memory that keeps surfacing finished business trains the user to ignore it.
4. **Propagate corrections.** When a fact changed, search the whole file set for every place the old version echoes: summaries, indexes, goal notes, standing instructions. A correction that only lands in the place it was spoken is a contradiction scheduled for later.
5. **Re-check salience.** The curated file is for what changes future behaviour: who the user is, what they prefer, what they decided, what is still open. Routine progress, transaction detail, and one-off trivia belong in the dated logs or nowhere. If an entry would not change how you act in a future conversation, it is not curated memory.
6. **Hold the density ceiling.** Set one and respect it: a line or word budget for the curated file that keeps it loadable and readable in full (a few thousand words suits most setups; the number matters less than having one). When the file is over, the answer is consolidation: merge the related, compress the verbose, retire the dead. Never solve size by writing smaller type or dropping the inconvenient.

## Rules that keep the pass safe

- **History is append-only; the curated file is not.** Dated logs record what was believed and when, including mistakes. Correct them with an explicit note that names what it replaces, never by silently rewriting the past. The curated file is the opposite: it should always read as currently true.
- **Attribute before you trust.** An entry that says who said something and when survives scrutiny; a bare assertion does not. When merging, keep the attribution.
- **Uncertainty survives the pass.** Do not let consolidation launder a "probably" into a fact. If the source was hedged, the merged entry stays hedged or gets verified.
- **Private stays private.** Memory files hold the most sensitive text the agent has. A hygiene pass never copies them to new locations, never quotes them to third parties, and treats any export as a separate, scrubbed operation.
- **The user owns deletions of substance.** Merging duplicates and retiring your own stale working notes is housekeeping. Deleting a fact the user deliberately recorded, or resolving a contradiction against their latest statement, is a decision: surface it first.

## Report

Close the pass with the measurements: before and after counts, what merged, what retired, what contradictions were resolved and which way, and what questions remain for the user. A pass that cannot list its changes did not happen; it was a reread.
