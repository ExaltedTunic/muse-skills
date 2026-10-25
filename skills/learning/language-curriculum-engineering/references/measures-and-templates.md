# Measures and Templates

Companion to `language-curriculum-engineering`. The numbers below are starting points from one production course; re-derive them for your band and learner goal, but keep the definitions exact, because every figure in a report should be reproducible from its definition alone.

## Measure definitions

| Measure | Definition | Notes |
|---|---|---|
| Reading words | Total word tokens across all reading texts in the assembled course pack | Count from the runtime pack, not source files, so attached material is included |
| Unique listening minutes | Sum of durations of unique graded audio assets registered in the manifest | Measure with a probe (e.g. ffprobe) on the stored files, not from transcript word counts |
| Declared items | Sum over lessons of declared vocabulary (`vocabItemIds` + `targetVocab`) | Per-lesson declaration is what the lesson claims to teach |
| Delivered items (lenient) | Declared items credited under the shipped instrument's rule | Record the rule beside the figure; lenient rules typically credit explicit references plus lemma occurrence anywhere in the lesson object |
| Delivered items (strict) | Declared items whose article-stripped catalog lemma occurs as a consecutive whole-token sequence inside the lesson's activity text only | No substring credit, no credit for homework, exit task, or the lesson's own word list |
| Delivery band | Per-lesson delivered ÷ declared; every declaring lesson must sit in the top band (80–100%) | A course average hides a starved lesson; the band does not |
| Companion similarity | Jaccard token similarity between a reading text and its listening companion | Hard ceiling 0.6; aim 0.2–0.35 |
| Spoken model invariant | Model answer words ÷ 2.0 (words per second) ≥ 0.8 × stated `minSeconds` | The 2.0 wps rate is the course's own speech model; keep it consistent everywhere |
| Written model check | Model answer word count ≥ stated `minWords` | Apply to every exit, not only the ones a gated check samples |
| Unglossed findings | Activities whose input text contains content words covered by no glossary entry, catalog item, or declared target | Target: zero. Gloss surface forms, not citation forms |
| Taught-once findings | Grammar rules presented in exactly one module with no later recurrence | Each is either a build task (give it a later home) or a written waiver |

## Gate catalogue template

Keep one contract file per course. Every invariant gets a row; the enforcement tag is the honest part.

| Invariant | Stated where | Enforced by | Gap / build target |
|---|---|---|---|
| (example) No duplicate exercise prompts within a lesson | lesson standard | TEST | covered |
| (example) Reading model not a re-render of the listening transcript | lesson standard | AUDIT (similarity ceiling) | extend to remaining modules |
| (example) Every taught grammar target is tested in its module | contract | NONE, diagnostic only | author scored carriers, then promote |

Enforcement tags: `TYPE` (schema/factory), `TEST`, `AUDIT` (blocking gate), `DIAGNOSTIC` (visible, non-blocking), `PROSE` (documented only), `NONE`. The maintenance job is moving rows right, one at a time, and never letting a tag claim more than the mechanism does.

## Dual-recording template (metric honesty)

When an instrument is found lenient, add a contract entry in this shape. Do not alter the instrument or its pins in the same change.

```markdown
## Metric honesty — <instrument name> (recorded <date>, base <commit>)

**Lenient instrument (the gated one).** <What it counts, exactly, including
the leniencies and known false positives, with a concrete example of each.>
- Lenient result at <commit>: <figure>.

**Strict instrument (this recording).** <The strict rule, exactly.>
- Strict result at <commit>: <figure>. <Per-module breakdown if useful.>

**Reading.** <Which figure to quote for what. What the gap between the two
figures is made of.>
```

## Lesson skeleton checklist

- [ ] Warm-up recycles earlier targets; introduces nothing new
- [ ] Input text(s) inside the band's sentence-length cap (e.g. 15 words at A2)
- [ ] First comprehension question is gist; details follow
- [ ] Listening companion similarity under the ceiling (if the lesson has one)
- [ ] Controlled practice precedes any free production
- [ ] Every new lemma is in the catalog, the module list, and the lesson wiring, with an audio clip
- [ ] Exit task has acceptance criteria, a model answer that provably meets its own minimum, and a retry prompt
- [ ] Homework is inline with rationale, acceptance criteria, model answer, retry prompt
- [ ] Unglossed scan clean for the lesson's activities
- [ ] No exercise prompt duplicates another in the lesson

## Tranche plan skeleton

```markdown
## Tranche <n> targets (baseline measured <date>: <figures>)
1. Reading: +<x> words (per-module quotas: <...>)
2. Listening: +<x> minutes unique audio (companions + standalone texts)
3. Lexis: +<x> catalog lemmas toward the band, frequency-prioritized,
   wired catalog + module list + lessons; clips for every new lemma/form
4. Strands: <any themed strand, e.g. a messaging-thread strand ending in
   a fast multi-party simulation>

Exit bar: fresh independent grading of every new lesson (no failing
grades, mediocre share < 15%), all canonical gates green on the merged
tree, audio validation clean (missing 0, stale 0), integrator line-check
of a content sample plus all assessment keys, measured deltas reported.
```

## Recording pack skeleton

```markdown
# Recording Pack — <dialect / variety>

<Plain intro: what this is, what it is for, why this speaker.>

## How to record
- Phone is fine. Quiet room, door closed, no background TV or music.
- One line per take, one file per line. Each line has an ID.
- Natural speed, natural voice. Do not perform or slow down.
- Spellings are guides, not scripture: if a written form is not how you
  would say it, say it your way and tell us the line ID afterwards.
- Flubbed a line? Re-record that file only.

## How the files come back
- Name each file with its line ID only (extension as recorded).
- Total: <N> files. Send them <channel the speaker already uses>.

## Part 1 — <primary dialect> mini-corpus
### 1a. Core lines
| ID | Dialect | Standard | Feature |
### 1b. <Feature set: e.g. dropped endings>
| ID | Dialect | Standard | What changes |
### 1c. <Feature set: e.g. softened consonants>
| ID | Dialect | Standard | Key word |
### 1d. Everyday lines (the features doing ordinary work)
| ID | Dialect | Standard |

## Part 2 — <secondary dialect> script (brief)
| ID | Dialect | Standard | Feature |
```
