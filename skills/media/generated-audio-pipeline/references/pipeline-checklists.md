# Generated Audio Pipeline — Checklists and Templates

Working templates for the `generated-audio-pipeline` skill. Copy, fill in, keep with the project.

## Manifest entry template

One entry per asset. The full (tooling) manifest keeps the source text; the client manifest keeps the fingerprint in its place.

```json
{
  "filePath": "audio/<pack>/<group>/<asset-id>.<hash>.<ext>",
  "sourceText": "The exact text that was rendered.",
  "sourceFingerprint": "<hash of canonical sourceText>",
  "renderFingerprint": "<hash of canonical sourceText plus the full render specification>",
  "engine": "<engine identifier>",
  "voice": "<voice identifier>",
  "modelRevision": "<engine model revision>",
  "speakingRate": "<speaking rate>",
  "language": "<language code>",
  "format": "<codec, bitrate, channels, sample rate>"
}
```

Rules:

- `sourceFingerprint` is a hash of the **canonicalized** `sourceText`: normalize to Unicode NFC, trim leading/trailing whitespace, and collapse internal whitespace runs to single spaces before hashing. Canonicalize identically at generation and validation time; an é as one codepoint vs two, or a trailing space, must not change the text component.
- `renderFingerprint` hashes that canonical text together with engine, voice, model revision, speaking rate, language, and format/codec. Path embeds the render-specification hash, so a changed text or render input produces a new path (and an orphan at the old one — see triage below).
- The full render specification is written at generation time, never reconstructed later.
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
3. **Generate the delta only:** assets that are new or whose render specification changed. Never re-render the whole catalogue to add a shelf to it.
4. **Verify per asset:** non-zero, plausible byte size; spot-check durations where tooling allows. Failed renders stay out of the manifest and are regenerated or routed to the fallback engine.
5. **Record provenance** (engine, voice) into each new manifest entry as it is produced, including which engine made which assets if the cost-policy switch fired mid-batch.
6. **Contain the churn:** revert any tracked audio files the run re-rendered without a source or render-specification change. The commit should contain the manifest plus genuinely new/changed assets only.
7. **Validate in authoritative mode** (store inventory via API), and report missing / stale / orphaned separately (see the report template).
8. **Probe delivery separately:** run bounded probes over the actual public/client route and report delivery/playback health separately from inventory. A reproducible public failure is a delivery defect, not inventory noise.
9. **Spot-listen** one asset per voice/language/batch before calling the run done.

## Orphan triage

An authoritative validation reports orphaned objects (in the store, claimed by no entry in the protected-manifest set). Work the list in order:

1. **Build the protected-manifest set.** Include the current release, every still-supported prior release, rollback targets, and cached-client manifests within their stated lifetime. An object referenced by any protected manifest is not an orphan and is not deletion-eligible.
2. **Is generation in flight anywhere?** Another branch, job, or session writing to the same store will produce assets its own not-yet-merged manifest claims. Those are not orphans. Stop, identify the owner, re-validate after their manifest lands.
3. **Did source text or another render-specification input change recently?** A regenerated asset gets a new hash-path; the old object is a true orphan left by the change, subject to the staged deletion step below.
4. **Did a run die partway?** Interrupted uploads and abandoned experiments strand objects with no manifest anywhere. They are deletion candidates once steps 1–2 exclude a protected reference or live owner.
5. **Delete in stages, with approval of the exact batch.** Let the applicable grace period expire, tombstone each candidate, and produce a dry-run deletion manifest listing every candidate and its reason. Obtain explicit approval of that exact batch, then delete deliberately through the storage API (a scratch script against the storage SDK is normal; generation tooling rarely ships a delete). One orphan class at a time, re-validating between classes.
6. **Finish at orphaned: 0 against the protected-manifest set** in authoritative mode, or with a written ownership/protection note for every remaining object. "Probably fine" is not a verdict.

## Validation report template

```
Audio validation (mode: authoritative inventory | fallback HEAD probes)
Assets in manifest: <n>   Total audio: <hours> h, <bytes>
Missing: <n>   Stale: <n>   Orphaned: <n>
Delivery health: <pass | fail; public/client route probed and failures>
Generated since last report: <n> assets (<engine A>: <n>, <engine B>: <n>)
Verdict: valid | blocked on missing/stale (defect) | orphan-only, ownership: <state>
```

A fallback-mode report is labelled as such and never carries an unqualified "valid".
