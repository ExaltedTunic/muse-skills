# muse-skills

Custom skills for Muse personal AI agents, built and tested in daily use and shared with friends. A living collection: new skills land here as they are built, and existing ones get updated in place as they improve.

Every skill in this repo has passed a whole-folder privacy scrub before publishing. Personal skills and third-party skills are not mirrored here; where a skill builds on someone else's work, it links upstream instead.

## For friends: start here

You do not need everything. Pick the one skill you want, or take the whole set.

**Easiest way:** give your Muse this repo link and tell it which skill you want. It can read the skill folder, copy it into your custom skills directory, and walk you through any setup in its SKILL.md.

**Manual way:** copy a folder from `skills/` into your custom skills directory, keeping the folder whole. Skills with a `scripts/` folder or a `config.example.json` need those files too; they are part of the skill, not extras.

**Staying current:** watch or star this repo, and check [CHANGELOG.md](CHANGELOG.md) to see what is new or changed. Updates are drop-in replacements of the skill folder, unless the changelog says otherwise.

## Catalogue

### Working with your agent

| Skill | What it does | Needs |
| --- | --- | --- |
| [identity-adaptation](skills/identity-adaptation/) | Grow a durable, personal identity with your user over time: agent-owned identity files, a plain-words feedback contract, voice disciplines that keep replies human, and a periodic self-review for drift. | Nothing extra |
| [external-review-intake](skills/external-review-intake/) | Verify claims from relayed outside reviews (other AIs, human reviewers, audits) against the source before acting: split into claims, check mechanically, report verified / corrected / unverifiable, and fold in only what the user approves. | Nothing extra |
| [scrub-before-sharing](skills/scrub-before-sharing/) | Prepare a file, folder, skill, or connector bundle for someone else by stripping private data from every file in it, scripts and configs included, and verifying the clean copy before it is shared. | Nothing extra |

### Money and shopping

| Skill | What it does | Needs |
| --- | --- | --- |
| [financial-audit](skills/financial-audit/) | Read-only audit of bank statements (CSV, PDF, or screenshots): cash flow, recurring bills, subscription price creep, fees, and deferred-interest deadlines. Never moves money. Private figures live in your own config outside the skill folder. | Python script included; example config included |
| [amazon-search](skills/amazon-search/) | Real Amazon.ca listings with live search-page prices through a local Camoufox browser. Search only: no login, no cart, no checkout. | Camoufox setup; built for a Muse VM, so its paths and setup notes are Muse-specific |

### Games

| Skill | What it does | Needs |
| --- | --- | --- |
| [smite-2-builds](skills/smite-2-builds/) | One current-patch, role-specific Smite 2 build from recent top-player match data on SmiteBrain, cross-checked against SmiteSource, with a hard gate against Smite 1 items. | Python script included |

## Sharing back

Friends are welcome to share skills back. See [CONTRIBUTING.md](CONTRIBUTING.md) for the house rules: the short version is tested in real use, generic by design, and privacy-scrubbed across every file before it lands.

## License

MIT, see [LICENSE](LICENSE).
