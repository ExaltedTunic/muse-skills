# muse-skills

Custom skills for Muse personal AI agents, built and tested in daily use and shared with friends. A living collection: new skills land here as they are built, and existing ones get updated in place as they improve.

Skills are organized by purpose under `skills/`: [agent workflow](skills/agent-workflow/), [finance](skills/finance/), [shopping](skills/shopping/), and [games](skills/games/). Each purpose folder has its own index page.

Every skill in this repo has passed a whole-folder privacy scrub before publishing. Personal skills and third-party skills are not mirrored here; where a skill builds on someone else's work, it links upstream instead.

## For friends: start here

You do not need everything. Pick the one skill you want, or take the whole set.

**Easiest way:** give your Muse this repo link and tell it which skill you want. It can read the skill folder, copy it into your custom skills directory, and walk you through any setup in its SKILL.md.

**Manual way:** copy a skill's folder out of its purpose folder (for example `skills/finance/financial-audit/`) into your custom skills directory, keeping the skill folder whole. The purpose folders are just shelves; the skill folder is the install unit. Skills with a `scripts/` folder or a `config.example.json` need those files too; they are part of the skill, not extras.

**Staying current:** watch or star this repo, and check [CHANGELOG.md](CHANGELOG.md) to see what is new or changed. Updates are drop-in replacements of the skill folder, unless the changelog says otherwise.

## Catalogue by purpose

### [Agent workflow](skills/agent-workflow/)

How your agent works with you day to day.

| Skill | What it does | Needs |
| --- | --- | --- |
| [identity-adaptation](skills/agent-workflow/identity-adaptation/) | Grow a durable, personal identity with your user over time: agent-owned identity files, a plain-words feedback contract, voice disciplines that keep replies human, and a periodic self-review for drift. | Nothing extra |
| [external-review-intake](skills/agent-workflow/external-review-intake/) | Verify claims from relayed outside reviews (other AIs, human reviewers, audits) against the source before acting, and fold in only what the user approves. | Nothing extra |
| [scrub-before-sharing](skills/agent-workflow/scrub-before-sharing/) | Prepare a file, folder, skill, or connector bundle for someone else by stripping private data from every file in it, scripts and configs included, and verifying the clean copy before it is shared. | Nothing extra |

### [Finance](skills/finance/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [financial-audit](skills/finance/financial-audit/) | Read-only audit of bank statements (CSV, PDF, or screenshots): cash flow, recurring bills, subscription price creep, fees, and deferred-interest deadlines. Never moves money. Private figures live in your own config outside the skill folder. | Python script included; example config included. Statement ingest is portable; the optional Plaid step is Muse-specific, skip it elsewhere |

### [Shopping](skills/shopping/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [amazon-search](skills/shopping/amazon-search/) | Real Amazon listings with live search-page prices from any regional storefront (amazon.ca, amazon.com, amazon.co.uk, amazon.de, and more) through a local Camoufox browser. Search only: no login, no cart, no checkout. | Camoufox setup; built for a Muse VM, so its paths and setup notes are Muse-specific |

### [Games](skills/games/)

| Skill | What it does | Needs |
| --- | --- | --- |
| [smite-2-builds](skills/games/smite-2-builds/) | One current-patch, role-specific Smite 2 build from recent top-player match data on SmiteBrain, cross-checked against SmiteSource, with a hard gate against Smite 1 items: live data or nothing. | Python script included. Script is portable; the presentation steps name Muse's widget and browser tools, adapt those on other platforms |

## Portability

Every `SKILL.md` carries YAML frontmatter (name, description) so other agent platforms can load these alongside the `skill.yaml`. Most skills are plain method and travel as-is. The Muse-specific pieces are named where they occur: financial-audit's optional Plaid step, amazon-search's VM paths and proxy-CA setup, smite-2-builds' widget presentation, and identity-adaptation's assumption that the platform auto-loads the agent's `SOUL.md` and `IDENTITY.md` files. On another platform, adapt or skip those named pieces; the rest of each workflow stands on its own.

## Sharing back

Friends are welcome to share skills back. See [CONTRIBUTING.md](CONTRIBUTING.md) for the house rules: the short version is tested in real use, generic by design, and privacy-scrubbed across every file before it lands.

## License

MIT, see [LICENSE](LICENSE).
