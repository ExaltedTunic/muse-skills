# Generated Audio Pipeline — Checklists and Templates

Working templates for the `generated-audio-pipeline` skill. Copy, fill in, keep with the project.

## Manifest entry template

One entry per asset. The full (tooling) manifest keeps the source text; the client manifest keeps the fingerprint in its place.

```json
{
  "filePath": "audio/<pack>/<group>/<asset-id>.<hash>.<ext>",
  "sourceText": "The exact text that was rendered.",
  "sourceFingerprint": "<hash of sourceText>",
  "engine": "<engine identifier>",
  "voice": "<voice identifier>",
  "format": "<codec, bitrate, channels, sample rate>"
}
```

Rules:

- `sourceFingerprint` is a hash of the **canonicalized** `sourceText`: normalize to Unicode NFC, trim leading/trailing whitespace, and collapse internal whitespace runs to single spaces before hashing. Canonicalize identically at generation and validation time; an é as one codepoint vs two, or a trailing space, must not change the fingerprint.
- Path embeds a content hash, so a changed source produces a new path (and an orphan at the old one — see triage below).
- `engine` and `voice` are written at generation time, never reconstructed later.
- The client manifest is derived from the full manifest, never edited independently; validation fails on drift between them.

## Codec measurement worksheet

Run on a sample of ~100 representative clips before choosing a format for a catalogue.

| Candidate | Sample bytes | Projected catalogue total | Plays on (browsers/devices checked) | Notes |
| --- | --- | --- | --- | --- |
| Uncompressed WAV (baseline) | | | everywhere | The number every ratio is measured against |
| Opus, speech bitrate, mono | | | | Check older versions of every major browser |
| MP3, speech bitrate, mono | | | everywhere | Usually the compatibility floor |
| AAC, speech bitrate, mono | | | | Container support varies by platform |

Decision record (write it where the project keeps decisions):

- Chosen format and bitrate:
- Candidates within ~20% of the winner's size: (if any, size was not the decider — say what was)
- Clients that cannot play the chosen format:
- Degradation chain for those clients: pre-generated file → server TTS → client speech synthesis (adjust to the product, but never leave a step landing on silence)

## Generation-run protocol

1. **Smoke test first.** Render a handful of assets in every language and voice in the batch. Check byte sizes; listen to one per combination. An engine that returns empty audio for a language fails here, not mid-batch.
2. **Freeze the source text** for everything in the batch. Edits after this point are a new batch.
3. **Generate the delta only:** assets that are new or whose source text changed. Never re-render the whole catalogue to add a shelf to it.
4. **Verify per asset:** non-zero, plausible byte size; spot-check durations where tooling allows. Failed renders stay out of the manifest and are regenerated or routed to the fallback engine.
5. **Record provenance** (engine, voice) into each new manifest entry as it is produced, including which engine made which assets if the cost-policy switch fired mid-batch.
6. **Contain the churn:** revert any tracked audio files the run re-rendered without a source change. The commit should contain the manifest plus genuinely new/changed assets only.
7. **Validate in authoritative mode** (store inventory via API), and report missing / stale / orphaned separately (see the report template).
8. **Spot-listen** one asset per voice/language/batch before calling the run done.

## Orphan triage

An authoritative validation reports orphaned objects (in the store, claimed by no manifest entry). Work the list in order:

1. **Is generation in flight anywhere?** Another branch, job, or session writing to the same store will produce assets its own not-yet-merged manifest claims. Those are not orphans. Stop, identify the owner, re-validate after their manifest lands.
2. **Did a source text change recently?** A regenerated asset gets a new hash-path; the old object is a true orphan left by the change. It is yours to delete.
3. **Did a run die partway?** Interrupted uploads and abandoned experiments strand objects with no manifest anywhere. Yours to delete, once step 1 excludes a live owner.
4. **Delete deliberately** through the storage API (a scratch script against the storage SDK is normal; generation tooling rarely ships a delete). One orphan class at a time, re-validating between classes.
5. **Finish at orphaned: 0** in authoritative mode, or with a written ownership note for every remaining object. "Probably fine" is not a verdict.

## Validation report template

```
Audio validation (mode: authoritative inventory | fallback HEAD probes)
Assets in manifest: <n>   Total audio: <hours> h, <bytes>
Missing: <n>   Stale: <n>   Orphaned: <n>
Generated since last report: <n> assets (<engine A>: <n>, <engine B>: <n>)
Verdict: valid | blocked on missing/stale (defect) | orphan-only, ownership: <state>
```

A fallback-mode report is labelled as such and never carries an unqualified "valid".
