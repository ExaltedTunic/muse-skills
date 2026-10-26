# Changelog

## Update, 2026-10-25 — fix program from two full external reviews

Every verified finding from two independent full-collection reviews was fixed and re-proven against the fixture that exposed it. The regression suites now ship in [tests/](tests/) and run in CI.

- **scrub-before-sharing:** the scanner accounts for its own coverage (enumerated, scanned, excluded, unreadable), inspects archive members, and fails closed with a distinct verdict when content could not be inspected; findings print a short fingerprint instead of the matched text.
- **schema-migration-safety:** adoption seeds only the footprint-evidenced prefix; fresh-only baselines must prove their declared structural postconditions; runners take a single-runner lock and re-read the ledger inside each transaction; the CHECK-constraint guard is scoped to the target relation and definition; a boundary and protocol for nontransactional DDL (for example CREATE INDEX CONCURRENTLY) is defined.
- **financial-audit:** promo deadlines are evaluated against an explicit evaluation date (the report shows both the statement date and the evaluation date); an explicit zero promo balance is honoured; configured debts render even with no transactions; tables keep negative signs; parallel same-merchant subscriptions are no longer halved; user categories take precedence over built-ins; Withdrawals/Deposits statements ingest; non-finite amounts are rejected at parse.
- **smite-2-builds:** the script enforces the completed-item rule (no component backfill; an incomplete core exits non-zero and says so), refuses to build on an unknown patch or an indeterminable role, versions the item-tier cache by patch, never substitutes another role's skill order, and reports aspect/relic votes with their empty share. The playbook's boots absolute is replaced by live verification: Smite 2's item set now includes boots-named items.
- **amazon-search:** marketplace values are validated against the known storefront set; unrecognized pages are reported as such instead of as empty results; unit prices parse suffix-currency formats; the smoke test asserts its checks; setup records the downloaded browser build.
- **norway-job-search-flow:** staffing verification records the register's authorisation status (godkjent / under behandling / ikke godkjent) with source and check date; the tailoring default for unknown employment arrangements is unified; Norwegian-requirement screening compares against the candidate's recorded level; the start-date rule carries the police-confirmed early-start exception; commute decisions use the vacancy's actual worksite; recruiter templates derive residence wording from the candidate profile.
- **Methodology and remaining skills:** agent-orchestration gains the approval boundary it was missing; identity-adaptation and memory-hygiene have their backup and logging rules reconciled, with timestamped, collision-proof backups; the memory audit's duplicate detection is Unicode-safe; the curriculum's spoken-model gate now requires the full stated minimum; the accessibility worksheet covers all ten checks and cites the focus criteria accurately; generated-audio figures name their bitrate, fingerprints cover the full render specification, deletion requires a protected-manifest set and an approved dry-run batch, and generation stops at a stated budget; metadata descriptions agree between frontmatter and sidecars across the collection.

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
