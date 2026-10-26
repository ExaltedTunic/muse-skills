# muse-skills

Custom skills for Muse personal AI agents, built and tested in daily use and shared with friends. A living collection: new skills land here as they are built, and existing ones get updated in place as they improve. The collection currently holds 18 skills across eight purpose folders.

Skills are organized by purpose under `skills/`: [agent workflow](skills/agent-workflow/), [finance](skills/finance/), [shopping](skills/shopping/), [games](skills/games/), [fitness](skills/fitness/), [career](skills/career/), [learning](skills/learning/), and [media](skills/media/). Each purpose folder has its own index page.

Every skill in this repo has passed a whole-folder privacy scrub before publishing. Personal skills and third-party skills are not mirrored here; where a skill builds on someone else's work, it links upstream instead.

## For friends: start here

You do not need everything. Pick the one skill you want, or take the whole set.

**Easiest way:** give your Muse this repo link and tell it which skill you want. It can read the skill folder, copy it into your custom skills directory, and walk you through any setup in its SKILL.md.

**Manual way:** copy a skill's folder out of its purpose folder (for example `skills/finance/financial-audit/`) into your custom skills directory, keeping the skill folder whole. The purpose folders are just shelves; the skill folder is the install unit. Skills with a `scripts/` folder or a `config.example.json` need those files too; they are part of the skill, not extras.

**Staying current:** watch or star this repo, and check [CHANGELOG.md](CHANGELOG.md) to see what is new or changed. Updates are drop-in replacements of the skill folder, unless the changelog says otherwise.

## How skills compose

When skills overlap, the domain skill for the user's actual goal leads the task; review and verification skills supply standards inside that work rather than taking it over. Orchestration skills activate only when delegation is actually part of the work. If two skills claim the same surface (for example, search versus price-history checking, or curriculum design versus audio generation), the skill matching the actual goal leads and the other supports it.

## Verification

The collection's regression checks live in [tests/](tests/) and run with the Python standard library alone: `python3 tests/run_all.py`. They cover the bundled scripts and the migration recipes with synthetic fixtures, and CI runs them on every push. The "Last verified" line in a playbook records the most recent live verification behind its claims.

## Catalogue by purpose

### [Agent workflow](skills/agent-workflow/)

How your agent works with you day to day.

| Skill | What it does | Needs |
| --- | --- | --- |
| [identity-adaptation](skills/agent-workflow/identity-adaptation/) | Grow a durable, personal identity with your user over time: agent-owned identity files, a plain-words feedback contract, voice disciplines that keep replies human, and a periodic self-review for drift. | Nothing extra |
| [external-review-intake](skills/agent-workflow/external-review-intake/) | Verify claims from relayed outside reviews (other AIs, human reviewers, audits) against the source before acting, and fold in only what the user approves. | Nothing extra |
| [scrub-before-sharing](skills/agent-workflow/scrub-before-sharing/) | Prepare a file, folder, skill, or connector bundle for someone else by stripping private data from every file in it, scripts and configs included, and verifying the clean copy before it is shared. | Python script included |
| [verify-before-shipping](skills/agent-workflow/verify-before-shipping/) | Require runnable evidence before claiming any script, skill, config or document works: a smoke-test pass over edge-case inputs, a doc-versus-behaviour cross-check, and full-output gate runs. | Nothing extra |
| [memory-hygiene](skills/agent-workflow/memory-hygiene/) | Audit long-term memory files on a cadence: merge duplicates, retire stale threads, resolve contradicted facts, propagate corrections, and hold a density ceiling. | Python script included |
| [agent-orchestration](skills/agent-workflow/agent-orchestration/) | Run multi-agent build programs that survive contact with reality: scoped briefs with measured targets and stop conditions, isolated worktrees, one integrator merging one branch at a time, and verification that re-derives every claim from diffs and full gate logs instead of trusting worker summaries. | Nothing extra |
| [independent-review-swarm](skills/agent-workflow/independent-review-swarm/) | Commission an independent multi-reviewer audit of finished work: fresh reviewers who built none of it, one lens each, findings backed by file-and-line evidence, every load-bearing claim re-verified before adoption, and a fix proposal bucketed fix-now, owner-call, and parked. | Nothing extra |
| [deep-review](skills/agent-workflow/deep-review/) | The depth standard for any review pass: an exhaustive scrub that treats every load-bearing claim as a claim to verify against a real anchor, plus a feasibility check, and reports issues found and coverage checked rather than impressions. | Nothing extra |
| [schema-migration-safety](skills/agent-workflow/schema-migration-safety/) | Make hand-written SQL migrations trustworthy: a transactional applied-migration ledger, an evidence-based adoption rule for pre-ledger databases, a runner list pinned to the migration directory by test, a frozen ORM journal, drift audits, and CHECK constraints derived from the code's own writers. | Nothing extra |
| [accessibility-design-guard](skills/agent-workflow/accessibility-design-guard/) | Run an accessibility pass over a web app and freeze what it fixed as automated design-guard tests: keyboard-operable controls with accessible names, focus that moves and stays visible, no zoom locks, timed-task accommodations that never move the pass bar, and design-system rules enforced as tests that fail on drift. | Nothing extra |

### [Finance](skills/finance/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [financial-audit](skills/finance/financial-audit/) | Read-only audit of bank statements (CSV, PDF, or screenshots): cash flow, recurring bills, subscription price creep, fees, and deferred-interest deadlines. Never moves money. Private figures live in your own config outside the skill folder. | Python script included; example config included. Statement ingest is portable; the optional Plaid step is Muse-specific, skip it elsewhere |

### [Shopping](skills/shopping/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [amazon-search](skills/shopping/amazon-search/) | Real Amazon listings with live search-page prices from any regional storefront (amazon.ca, amazon.com, amazon.co.uk, amazon.de, and more) through a local Camoufox browser, including unit prices and review counts where the page shows them. Search only: no login, no cart, no checkout. | Camoufox setup; built for a Muse VM, so its paths and setup notes are Muse-specific |
| [price-history-check](skills/shopping/price-history-check/) | Check whether an Amazon price is actually a deal: cross-check an ASIN against CamelCamelCamel and Keepa price history and other retailers before calling a sale price good. | Nothing extra |

### [Games](skills/games/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [smite-2-builds](skills/games/smite-2-builds/) | One current-patch, role-specific Smite 2 build from recent top-player match data on SmiteBrain, cross-checked against SmiteSource, with a hard gate against Smite 1 items: live data or nothing. | Python script included. Script is portable; the presentation steps name Muse's widget and browser tools, adapt those on other platforms |

### [Fitness](skills/fitness/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [fitness-coach](skills/fitness/fitness-coach/) | Build and run a research and results driven workout program: a thorough intake interview before anything is written, a program designed from the user's goals, schedule, equipment and constraints, then week-to-week coaching from their logged results. | Nothing extra |

### [Career](skills/career/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [norway-job-search-flow](skills/career/norway-job-search-flow/) | Verification-first pipeline for a Norway job search that needs a skilled-worker residence permit: private search box, five-source sweep, Brønnøysund and staffing-register verification, ledger-first shortlist, written-evidence permit status, and per-listing approval before anything is sent or submitted. | Nothing extra. The candidate supplies a private profile and ledger outside the skill |

### [Learning](skills/learning/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [language-curriculum-engineering](skills/learning/language-curriculum-engineering/) | Build and maintain a CEFR-banded language course as data with validation gates: input-mass budgeting in reading words, listening minutes and lemmas, declared-vs-delivered lexis measurement, assessment integrity with provable model answers, and strict-vs-lenient metric honesty. | Nothing extra |

### [Media](skills/media/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [generated-audio-pipeline](skills/media/generated-audio-pipeline/) | Run a pre-generated audio catalogue as an engineered pipeline: a manifest as source of truth with per-asset engine and voice provenance, codec choice as an explicit compatibility decision, churn-controlled regeneration, orphan lifecycle management in shared object storage, and a written two-engine cost policy. | Nothing extra |

## Portability

Every `SKILL.md` carries YAML frontmatter (name, description) so other agent platforms can load these alongside the `skill.yaml`. Most skills are plain method and travel as-is. The Muse-specific pieces are named where they occur: financial-audit's optional Plaid step, amazon-search's VM paths and proxy-CA setup, smite-2-builds' widget presentation, and identity-adaptation's assumption that the platform auto-loads the agent's `SOUL.md` and `IDENTITY.md` files. On another platform, adapt or skip those named pieces; the rest of each workflow stands on its own.

## Sharing back

Friends are welcome to share skills back. See [CONTRIBUTING.md](CONTRIBUTING.md) for the house rules: the short version is tested in real use, generic by design, and privacy-scrubbed across every file before it lands.

## License

MIT, see [LICENSE](LICENSE).
