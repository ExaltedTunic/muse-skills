# Changelog

## Initial release, 2026-10-24

The first published version of the collection: ten skills across five purpose folders.

- **Agent workflow:** identity-adaptation, external-review-intake, scrub-before-sharing (with a bundled stdlib scanner script), verify-before-shipping, memory-hygiene (with a small stdlib audit script).
- **Finance:** financial-audit, a read-only audit of statement exports with a Python script and example config.
- **Shopping:** amazon-search, anonymous region-agnostic Amazon search through a local Camoufox browser; price-history-check, deal verification against CamelCamelCamel price history and other retailers.
- **Games:** smite-2-builds, current-patch Smite 2 builds from live top-player data, with a Python script.
- **Fitness:** fitness-coach, interview-first program design and results-driven coaching.

Every skill carries YAML frontmatter in its SKILL.md alongside its skill.yaml, and was in daily use before it was published here.

## Update, 2026-10-25

- **Career:** norway-job-search-flow, a verification-first pipeline for a Norway job search that needs a skilled-worker residence permit. It covers the private search box, the five-source Norwegian sweep, Brønnøysund employer verification, the Arbeidstilsynet staffing-register check, a ledger with versioned approvals, and recruiter question templates. The published version is the method only: no candidate profile, ledger, contacts, or application history are included.

## Update, 2026-10-25 — seven methodology skills

Seven skills distilled from a large multi-agent curriculum overhaul program, published as method only.

- **Agent workflow:** agent-orchestration (multi-agent build programs with briefs, worktree isolation, and integrator verification), independent-review-swarm (fresh reviewers, assigned lenses, claim re-verification, fix bucketing), deep-review (the exhaustive-scrub depth standard for any review pass), schema-migration-safety (transactional migration ledgers, adoption rules, drift audits, code-derived constraints), accessibility-design-guard (accessibility audits frozen as design-guard tests).
- **Learning (new folder):** language-curriculum-engineering, CEFR-banded curriculum as data with input-mass budgeting, lexis measurement, and assessment integrity.
- **Media (new folder):** generated-audio-pipeline, pre-generated audio catalogues with manifest provenance, codec decisions, churn control, and a two-engine cost policy.

## Update, 2026-10-25 — corrections and additions across the collection

A full verification pass over every skill; the changes below are the user-visible results.

- **financial-audit:** statement parsing hardened (column binding, debit/credit indicator columns, word-boundary categories, unformatted amounts, leap-year and day/month dates, opening-balance variants); subscription price-hike detection no longer hides large jumps; refunds offset spending instead of counting as income; identifier masking keeps the last two digits everywhere, including the accounts list.
- **scrub-before-sharing:** the scanner no longer false-flags prose or timeout constants, fails loudly on a missing path, scans single files, counts flagged lines honestly, and recognises current API key shapes (OpenAI, Anthropic, GitHub fine-grained PATs, Google) and Canadian postal codes without flagging hex-like strings.
- **memory-hygiene:** the audit script also reports duplicates across files and stale TODO/pending markers, and exits nonzero when a file cannot be read; the pass now starts with a dated backup of the curated file.
- **smite-2-builds:** starter families completed (Conduit Gem, Sands of Time, Gilded Arrow, War Flag, Selflessness, Bumba's Dagger), flex slots can no longer hold build components, role-less runs refetch the god's primary-role sample, item tiers are cached on disk between runs, and a new --aspect flag filters a build to one aspect.
- **amazon-search:** price parsing covers every storefront currency in the skill's marketplace table; split whole/fraction prices are joined correctly; results now include unit price and review count where the page shows them; result waiting is selector-based instead of a fixed sleep.
- **price-history-check:** the CamelCamelCamel step names only the locales that exist; a Keepa step covers storefronts CamelCamelCamel does not.
- **Methodology skills:** review dispositions unified on VERIFIED / CORRECTED / REFUTED / UNVERIFIABLE across deep-review, independent-review-swarm, and external-review-intake; deep-review gains a fitness-for-purpose check; schema-migration-safety defines its fresh-only baseline and large-table constraint pattern; accessibility-design-guard adds WCAG 2.2 focus-obscured and target-size checks; language-curriculum-engineering adds a met-once lemma diagnostic; generated-audio-pipeline specifies text canonicalization before fingerprinting and a concrete byte floor; fitness-coach adds a fat floor, a protein sanity cap for high body weights, and weekly hard-set landmarks; norway-job-search-flow warns about Norway's public applicant list and structured portal fields; identity-adaptation moves its onboarding skeletons into references/ and adds a backup-before-rewrite rule; skill categories are standardized per folder.
