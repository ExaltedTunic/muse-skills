# Changelog

What is new in the collection, newest first. Friends: this is the page to check after an update drops.

## 2026-10-24: external review fixes and portability pass

Fixes from a full external review of the d512960 tree, each verified against the source before and after:

- financial-audit: the monthly Net column now keeps its sign (a deficit month printed as a surplus before, because the formatter dropped it); ingest-text captures an undated OPENING BALANCE line, so the first transaction's sign can be balance-checked; slash dates are inferred per file (DMY vs MDY) with a `--date-format` override for all-ambiguous files; ragged CSV rows are read bounds-safely instead of crashing; an empty audit prints a graceful "no transactions" report instead of crashing; the usage docstring matches the actual CLI.
- smite-2-builds: omitting `--role` now selects the god's primary role in the sample, as the skill text always claimed (it pooled all roles before); skill-order pairing on SmiteSource is bounded per build instead of using a wide text window that could pair a build with a neighbour's roles and score.
- amazon-search: the search is region-agnostic (any storefront by code or domain, one default); setup scripts create the directories they use; block detection runs only when no results rendered, recognises amazon.com's AI-agent block page, and reports load timeouts as load failures. Known limits, verified live: amazon.com blocks agent traffic outright, amazon.de renders no prices on search cards in anonymous sessions, amazon.co.uk loads intermittently from datacenter networks.
- Portability: every SKILL.md now carries YAML frontmatter; the smite skill's defaults section is user-agnostic in this bundle; the README names which pieces are Muse-specific per skill; scrub-before-sharing ships a small stdlib scanner script and is discoverable in the bundle index; CONTRIBUTING records the naming convention (folder kebab-case, skill.yaml name snake_case, frontmatter name matches the folder).

## 2026-10-24: Organized by purpose

Skills now live under purpose folders: `skills/agent-workflow/`, `skills/finance/`, `skills/shopping/`, and `skills/games/`, each with its own index page. If you copied a skill from the flat layout earlier today, its new home is the same skill folder inside its purpose folder; the skill folders themselves are unchanged.

## 2026-10-24: Initial collection

Six skills:

- identity-adaptation
- external-review-intake
- scrub-before-sharing
- financial-audit
- amazon-search
- smite-2-builds (includes the Oct 24 hard gate: live data or nothing)
