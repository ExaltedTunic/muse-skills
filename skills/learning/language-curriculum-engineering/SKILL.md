---
name: language-curriculum-engineering
description: "Build and maintain a CEFR-banded language course as data with validation gates: input-mass budgeting in reading words, listening minutes and lemmas, declared-vs-delivered lexis measurement, assessment integrity with provable model answers, manifest-accounted course audio, and strict-vs-lenient metric honesty. Use when designing a language curriculum, adding or auditing lessons and vocabulary at scale, planning extensive-reading or listening volume, generating course audio, or preparing native-speaker recording material."
---

# Language Curriculum Engineering

A language course built by hand-waving drifts: word lists nobody delivers, model answers shorter than the minimum they demonstrate, listening tracks that are the reading read aloud, progress figures that flatter. This skill treats the curriculum as an engineered artifact. Content is data, every pedagogical claim is either machine-checked or written down as an honest diagnostic, and progress is measured in units a learner's brain actually consumes: words read, minutes heard, lemmas met in context.

## Curriculum as code

- **Content is data, not documents.** Lessons, vocabulary, grammar targets and assessments live in structured files validated on construction (schema/factory checks) and by a canonical gate battery: typecheck, test suite, curriculum audit, audio validation. A change is not done until the battery is green on the merged tree, re-run by whoever integrates it, not just by whoever wrote it.
- **Prose rules drift; gated rules do not.** Keep a contract file that inventories every invariant and how it is enforced today (by type, by test, by audit gate, by prose only, or not at all). The standing job is migrating rows from "prose only" toward "gated". A rule that lives only in a guide document will be forgotten mid-project; a rule behind a failing gate will not.
- **Verify curriculum facts, never assert them.** "Is this word already taught?", "what is the longest reading model in this unit?", "where was this rule introduced?" get answered by querying the pack (a lookup tool or a probe script run from the repo root), never from memory. An unverified negative is *unknown*, not *false*.

## Band the course

- **Assign every module a CEFR band** and derive its constraints from the band, not from taste: per-level caps on input-sentence length (for example 15 words at A2, slightly more at A2+), text-length floors and ceilings, and production targets.
- **State targets as numbers.** "More input" is not a target. Reading words, unique listening minutes, and receptive lemmas per band are (see the budget below). Every later measurement is a delta against those numbers.

## Lesson anatomy

Every lesson follows the same skeleton, so learners meet a predictable rhythm and auditors can check structure mechanically:

1. **Warm-up that recycles** earlier targets (retrieval, not new material).
2. **Input**: a reading and/or listening text at band, with the lesson's new lexis and grammar inside it.
3. **Gist-first comprehension**: the first question asks for the main idea, detail questions after. Never open with a detail hunt.
4. **Controlled practice** of the new forms, then freer production. A constrained model always precedes open production; free production is content-supplied, planning-framed, or model-adjacent, never unsupported invention.
5. **An exit task** that proves the lesson's can-do statement, carrying an explicit acceptance criteria text, a model answer, and a retry prompt for learners who miss.
6. **Homework authored inline with the lesson**, with all scaffolding fields present: rationale, acceptance criteria, model answer, retry prompt. Homework attached by a legacy mechanism that drops those fields is dead content; do not build on it.

No duplicate exercise prompts within a lesson. Every taught grammar target is carried by at least one scored drill or productive task inside its module, or it produces no mastery evidence and is decoration.

## Budget the input mass

Comprehension volume is the ceiling on everything else. Budget it in three currencies and measure the baseline before writing anything:

- **Reading words** in the course corpus. An ambitious self-study course aiming at strong B1 plans on the order of 100k words of graded reading.
- **Unique listening minutes.** Count unique graded audio, not replays. A 10-hour ambition against a 70-minute baseline is a building program, not an edit.
- **Lemmas** referenced and delivered, against the receptive band for the level (a B1 receptive band is roughly 2,750 lemmas).

Build volume in **tranches**, each with per-module quotas for all three currencies, and report measured deltas, never estimates. The volume engine is the **extensive-reading strand**: graded texts appended as extra lessons per unit, written to a fixed standard (gist-first exercises, gloss discipline, sentence caps). Two rules keep the strand honest:

- **Reading/listening companions, not copies.** Each extensive text ships with a listening companion telling the same story differently. Enforce a similarity ceiling (Jaccard token similarity below 0.6 as a hard gate; aim for 0.2–0.35). Above the ceiling the listening is just the reading read aloud and trains nothing new.
- **Reading supports writing.** A unit's longest reading model must be at least as long as its largest writing target. Learners cannot be asked to produce what they have never read at length.

## Engineer the lexis

- **One catalog is the registry of record.** Every lemma lives there once, with its translation, level, and frequency band. If the design has a fixed-size seed syllabus (say exactly 40 items per module), new lexis never goes into the seeds; it goes through the catalog, the module's vocabulary list, and lesson wiring (`vocabItemIds` / `targetVocab`).
- **Select by frequency.** When adding lexis, spend the budget on the highest-frequency missing items for the band first; a rare word taught early is a common word not taught.
- **Measure declared vs delivered per lesson.** A lesson declares the items it teaches; delivery means the item actually surfaces in the lesson's activities. Hold every declaring lesson to a minimum band (80% delivered is a workable floor) and gate it. Declared-but-never-presented vocabulary is the most common silent failure in a growing course.
- **Gloss until the scan is clean.** Run the unglossed-content scan and add glosses until it reports zero. Gloss the **surface form**, the inflected token the learner actually meets ("the tasks", "answered"), not just the citation form; the scan counts surface tokens, and so does the learner's confusion.
- **Duplicate-lemma discipline at integration.** Parallel builders independently coin the same high-frequency lemma under different ids. At integration, detect same-lemma/different-id pairs mechanically, keep one catalog entry, and rewire the other side's lesson and module references to it. Two entries for one lemma split its delivery evidence and its audio.
- **Met-once lemma diagnostic.** Declared-vs-delivered checks whether a lemma surfaces in the lesson that declares it; nothing checks whether the learner ever meets it again. Run the met-once diagnostic across the catalog: lemmas delivered in one module that recur in no later lesson, reading, listening text, or drill. Each hit undermines spaced retrieval — a single exposure is an introduction, not learning. Fix it deliberately: wire a recurrence into a later module's warm-up, extensive text, or drill set, or record a waiver in the contract with a reason (a foundational item taught once on purpose). Report the met-once count alongside the delivery figures.

The measurement definitions and worked templates behind this section (delivery measurement, the strict sweep, tranche reporting) are in `references/measures-and-templates.md`.

## Assessment integrity

- **Every scored question is keyed to its text.** Verify each answer key against the passage it claims to test, programmatically where the format allows. A key that drifted from its text teaches the learner that being right is wrong.
- **Model answers must provably satisfy the stated minimum.** Written exits: model word count ≥ the task's `minWords`. Spoken exits: apply the duration invariant, model words ÷ speaking rate (use 2.0 words/second) ≥ 0.8 × the stated `minSeconds`. Check this over **all** exits, including the ones your gated check's denominator skips (see metric honesty).
- **Pass bars at parity across modes.** A spoken exit and its written twin are the same claim about the learner, so they are scored to the same standard (for example overall score ≥ 70 AND task completion ≥ 70 in both modes). Do not let one mode become the soft option.
- **Spoken-duration ladders.** When the course ends in a timed spoken performance (an exam interaction, an interview), build the durations up in steps across the final modules, each unit's exits a rung, so the target performance is rehearsed progressively instead of appearing as a cliff at the end.
- **Server-resolved grading anchors.** Where an AI or human grader scores production, prompt, criteria, and length anchors come from the server's copy of the task, never from the client's request. A grader that trusts client-sent criteria grades whatever the client says the task was.

## Generated audio

- **Pre-generate the course's own audio; runtime synthesis is a fallback** for learner-submitted text and error paths. Pre-generation fixes cost, voice, and quality in advance and makes every listening asset reviewable before a learner hears it. Listening minutes are one of the three budget currencies, so generation belongs in the tranche plan, with its cost estimated like any other line item and the engine policy decided before the tranche starts, not mid-build.
- **Keep every asset registered in a manifest** that validation checks against storage. The curriculum-level point is accountability: at any moment you can prove which audio exists, which assets went stale after a transcript edit, and how many unique minutes the course actually contains. Validation should report missing, stale, and orphaned assets as separate counts, not one boolean; quote all three.
- **Record provenance per asset** (engine and voice, in the manifest entry). A course built over months will mix engines; provenance is what lets you budget regeneration, explain a voice change between units, and decide what to re-record when quality standards move.
- For pipeline mechanics (codec choice as a compatibility trade-off, non-deterministic regeneration churn, orphan lifecycle in shared storage, and engine cost policy), see the `generated-audio-pipeline` skill.

## Metric honesty

- **Every instrument is lenient somewhere.** A delivery check that credits a lemma for appearing as a substring anywhere in the lesson object, or an exit check whose denominator quietly excludes the spoken exits, produces headlines that overstate the course. When you discover a lenient instrument, do not re-baseline its pins to the strict number and do not quietly fix the instrument mid-program. Record **both** figures, with their definitions, in the contract: the lenient gated value and a strict sweep (for vocabulary: the article-stripped lemma as a consecutive whole-token sequence inside activity text only; for exits: the full denominator). Quote the strict figure when describing the course; quote the lenient one only as "the gated value".
- **Blocking gates vs visible diagnostics.** Keep not-yet-clean checks as non-blocking diagnostics with their findings listed, and promote a check to blocking only once it is clean. Never suppress, relabel, or delete a diagnostic to manufacture a green run.
- **Waivers are documents, not silence.** A finding that is correct by design (a foundational rule taught in one module on purpose) gets a written waiver in the contract: the evidence, the reasoning, and a re-check point. When the re-check shows the lapse condition has resolved, retire the waiver. An undocumented exception is indistinguishable from drift.

## Native-speaker elicitation

Some material only a native speaker can supply, above all dialect audio. Prepare a **recording pack** the speaker can act on alone, with no technician present:

- **Plain intro**: what this is, what it is for, and why this speaker (their dialect is the one the learners will actually hear).
- **Recording rules a non-technical person can follow**: phone is fine, quiet room, one line per take and one file per line, natural speed and natural voice, do not perform or over-enunciate, re-record a flubbed line only. File naming is the line ID and nothing else.
- **The speaker's ear outranks the spelling.** Written dialect forms are guides. Tell the speaker explicitly: if a written form is not how you would say it, say it your way and report the line ID afterwards so the written version can be fixed to match the recording.
- **Lines organized by feature.** Group the corpus by the phenomenon it teaches (for example one labelled set for dropped endings, one for a consonant softening), each line with its standard-language equivalent beside it and the feature named, plus an everyday set where the features do ordinary work. Expand the highest-value dialect (the one learners will meet in real life) into a real mini-corpus; brief scripts suffice for dialects the course only touches.
- **A return checklist** that states the exact file count and naming scheme, so completeness is checkable at a glance when the files come back.

## Review discipline

- **Fresh graders, raw grades.** New content gets graded by reviewers who did not build it, against the band standard, and the grades are recorded raw (no averaging away a bad lesson). A workable exit bar for a content tranche: no failing grades, and the share of mediocre grades under a fixed ceiling (for example C-share under 15%).
- **The integrator line-verifies** a sample of the new content personally, plus **all** assessment keys, before anything merges. Summaries from builders are claims; the diff and the gate logs are evidence.
- **Two rounds before calling a module done**: a learner-flow walk (meet the module as a learner does, in order) and an adversarial findings review by someone who did not build it. Findings are fixed in closure commits and re-verified, not negotiated away.

## Reporting

Report measured deltas against the budget (words, minutes, lemmas, delivery shares), quoted from the instruments that produced them, with the strict figure wherever a lenient headline exists. Name the honest residuals: what the tranche did not reach, what was waived and why, what remains a diagnostic rather than a gate. A report that only lists what shipped teaches the next builder to stop checking.
