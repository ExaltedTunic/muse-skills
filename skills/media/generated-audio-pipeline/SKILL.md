---
name: generated-audio-pipeline
description: "Run a pre-generated audio catalogue as an engineered pipeline: a manifest as source of truth with per-asset engine and voice provenance, codec choice as an explicit compatibility decision, churn-controlled regeneration, orphan lifecycle management in shared object storage, a written two-engine cost policy, and byte-level output verification that catches silent empty renders. Use when generating TTS or narration audio at catalogue scale, choosing an audio format, validating a generated-audio store, or mixing hosted and local synthesis engines."
---

# Generated Audio Pipeline

A generated-audio catalogue fails in predictable ways: the app bloats because audio ships inside it, clips go stale because nothing compares them to their source text, a store fills with orphaned objects nobody dares delete, two engines' output mixes until nobody can say what made what, and an engine that cannot handle a language returns empty files with a success status. This skill is the operating discipline that prevents each of those: pre-generate, account for every asset in a manifest, and treat generation as a pipeline with provenance, not a pile of files.

## Architecture: pre-generate, serve from storage

- **Core content is pre-generated, never synthesized at runtime.** Generate every asset the product depends on ahead of time and serve it from object storage behind a CDN. The application ships a manifest, not audio weight.
- **Catalogue growth costs storage, not app size or latency.** At 32 kbps Opus mono, an hour of finished speech is roughly 14.4 MB before container overhead; at 24 kbps, it is roughly 10.8 MB. Assets stream per clip and cache at the edge, so a catalogue that doubles in hours of audio adds megabytes of cheap storage and nothing to the download or the page load.
- **Runtime synthesis is a fallback tier, not the pipeline.** A live TTS endpoint exists for content that cannot be pre-generated (user-specific or dynamic text) and as a degradation step when a pre-generated file cannot play. Core catalogue content never depends on it.

## The manifest is the source of truth

- **Every asset has a manifest entry** recording at least: storage path, the source text it was rendered from (or a fingerprint of it), the engine that rendered it, the voice, the model revision, the speaking rate, the language, and the format/codec. If an asset is not in the manifest, it does not exist as far as the product is concerned.
- **Fingerprints cover the full render specification.** Before hashing, canonicalize the source text: normalize to Unicode NFC, trim leading and trailing whitespace, and collapse internal whitespace runs to single spaces. Hash that canonical text together with the engine, voice, model revision, speaking rate, language, and format/codec. Generation and validation must assemble the render specification identically. Otherwise invisible text differences (an accented character in decomposed form, a trailing space from an editor) read as staleness and trigger paid regenerations of audio that never changed, while a voice, rate, or codec change with identical text would falsely read as unchanged instead of re-addressing and regenerating the asset.
- **Validation compares the manifest against the storage inventory,** in both directions: entries whose objects are missing, objects whose content no longer matches their entry (stale), and objects no protected-manifest entry claims (orphans). Report the three counts separately; they mean different things and have different fixes. Inventory answers existence and ownership; it does not prove that a client can fetch or play the object.
- **Name the mode behind every validation verdict.** An authoritative mode inventories the store through its authenticated API or listing call. A fallback mode probes public URLs one by one, and those probes flake through proxies and CDNs, reporting a different handful of phantom "missing" assets on every run. A "valid" claim is only meaningful from the authoritative mode; a fallback-mode failure is a prompt to re-run authoritatively, not a defect report. **Report delivery health separately from inventory:** authenticated inventory is authoritative for existence and ownership, while bounded probes over the actual public/client route report playback and delivery health on their own line. A reproducible public failure (a denied route, wrong MIME or CORS headers, or an undecodable response) is a delivery defect, not inventory noise; a one-off proxy-dependent miss remains a prompt to re-run.
- **Ship the client a slim manifest.** The full manifest embeds source texts for tooling; the client only needs paths and fingerprints. Deriving a slim client manifest from the full one (fingerprints in place of source text) cut one real manifest's transferred size by roughly a fifth raw and more after compression. The validator should fail if the two drift apart.

## Per-asset provenance

- **Record engine and voice on every asset at generation time.** Mixed catalogues are normal and expected: one engine voices the long-form content, another the short clips; a cost switch (below) splits a single batch down the middle. Provenance recorded per asset keeps all of that attributable after the fact.
- **Never describe a catalogue with a blanket engine claim.** "The audio is all engine X" is a claim the manifest either proves asset by asset or does not support. When asked what made an asset, answer from its entry.

## Codec choice is a compatibility decision

- **Measure before committing.** Take a representative sample (around a hundred clips), render or transcode it into each candidate format at a speech-appropriate bitrate, and project the totals. In one real measurement of a ~1,300-clip short-form catalogue, uncompressed WAV totalled ~59 MB; Opus at 32 kbps mono landed at ~5 MB (−91%), with MP3 and AAC at the same bitrate within ~20% of Opus. When candidates land that close, size is not the deciding factor; compatibility is.
- **A small size win never justifies a compatibility sacrifice on its own.** Check playback across the browsers and devices the audience actually uses, including older versions. A codec that one major browser only recently learned to play, and previously played only inside a proprietary container nothing else uses, is a compatibility loss no matter how good the ratio looks.
- **If you accept a compatibility loss, write down the degradation chain.** An asset that cannot play in some client must degrade along a documented path (pre-generated file → server-side TTS → the client's built-in speech synthesis), and the decision record names the clients that land on each step. Degrading to a fallback voice is an acceptable trade; degrading to silence is not, and it is what happens when nobody writes the chain down.

## Regeneration churn

- **Non-deterministic engines re-render everything differently on every run.** A full-catalogue regeneration produces a diff on every single file even when no source text changed. That churn is noise, and committing it buries the real changes.
- **Additions-only is the default.** After a generation run, revert churned tracked files and keep only the manifest plus the genuinely new or changed assets. Generate the delta, not the catalogue.
- **When the source text or any other render-specification input changes,** regenerate that asset deliberately, expect its content hash (and therefore its storage path) to change, and follow the orphan procedure below for the object it leaves behind.

## Orphan lifecycle

- **Orphans are stranded objects:** files in the store that no entry in the protected-manifest set claims. They appear when a regenerated asset's hash changes its path, when a generation run is interrupted, or when work is abandoned. An authoritative inventory validation fails while unexplained orphans exist; that failure is the mechanism working, not a nuisance to silence.
- **Missing and stale are the true failure signals.** Missing means the manifest promises audio the store does not have; stale means the object no longer matches its source. Either one is a defect to fix before shipping. Orphans require an ownership check first.
- **Never delete an asset another in-flight job may own.** When several branches or generation jobs write into one shared store concurrently, a sibling job's brand-new assets look exactly like orphans until that job's manifest lands. Deleting them destroys finished work. The correct response to orphan-only failures on a shared store is to identify ownership, wait for the owning manifest to merge, and re-validate.
- **Deletion eligibility starts with the protected-manifest set.** Before calling an object an orphan, build the protected set: the current release manifest, every still-supported prior release, rollback targets, and cached-client manifests within their stated lifetime. An object referenced by any protected manifest is not an orphan and is not deletion-eligible.
- **Delete proven orphans deliberately, in stages.** Once the protected-set and ownership checks exclude an object, let the applicable grace period expire, tombstone the candidate, and produce a dry-run deletion manifest listing every candidate with its reason. Obtain explicit approval of that exact batch before hard deletion through the storage API; do not assume the audio tooling ships a delete path, because it often does not, and a scratch script against the storage SDK is a normal way to do it. Re-run the authoritative validation afterwards and report orphaned: 0.

## Cost policy: write it down before you generate

- **One-time generation is cheap; churn is the spend.** A full catalogue pass typically costs a few dollars of hosted-engine credit at most. The real cost driver is regeneration during editing: every text revision that re-renders finished audio pays again. Freeze text before mass generation wherever the workflow allows it.
- **Budget the batch before generation.** Estimate the batch's characters or expected duration against the selected provider's current pricing, state the approved budget and maximum call count, and stop or switch engines when either limit is reached. A quota or credit refusal is a fallback signal, not the cost-control mechanism.
- **State a two-engine policy explicitly.** The pattern that works: a premium hosted neural TTS engine generates until the approved batch budget or maximum call count is reached, then a local neural TTS engine (open-source, running on your own hardware) takes over. If the hosted engine refuses on credit or quota before those limits, that refusal also triggers the switch and is reported. The remaining generation proceeds on the local engine, and per-asset provenance (above) makes the exact split auditable afterwards.
- **Estimate with storage math, not anxiety.** Hours of speech are roughly 14.4 MB per hour at 32 kbps Opus mono before container overhead, or roughly 10.8 MB per hour at 24 kbps, on the store and fractions of a cent to a few cents per short asset to generate. "Generating audio for every module will be huge" is a checkable claim, and checking it takes one sample render and a multiplication.

## Silent failure: verify output bytes, not status codes

- **An engine that cannot synthesize a language or a voice may fail silently,** returning truncated or zero-byte audio with a success status. This is a per-engine, per-language property; discover it in a smoke test before the batch, not from user reports after it.
- **Check byte size on every generated asset.** A zero-byte or implausibly small render is a failed render: exclude it from the manifest, regenerate it or route it to the fallback engine, and never ship it. Use a floor, not just non-zero: at speech bitrates (~32 kbps) a real render exceeds roughly 1 KB and runs to at least ~100 bytes per word of source text. A synthesis failure often returns a valid-looking container of 200–400 bytes holding 0.0 seconds of audio; that passes a `size > 0` check and must be caught by the floor. Duration checks are a cheap second signal where the tooling supports them.
- **Spot-listen a sample** from every batch, voice, and language combination. Automated checks catch empty files; only an ear catches a confident render of the wrong text.

## Reporting a pipeline state

Report the manifest totals (assets, hours, bytes), the validation mode, and the missing / stale / orphaned counts as separate numbers, with engine attribution for anything generated since the last report. An orphan-only failure on a shared store mid-merge is a state report ("waiting on two sibling manifests"), not a defect and not a pass; say which one it is.

See `references/pipeline-checklists.md` for the manifest field template, the codec measurement worksheet, the generation-run protocol, and the orphan triage steps.
