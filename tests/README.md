# Regression checks

The skills in this repository make verifiable claims, so the checks that
back those claims ship with the collection and can be rerun by anyone:

    python3 tests/run_all.py

Exit code 0 means every suite passed. Each suite is Python-standard-library
only, builds its own synthetic fixtures in a temporary directory, and needs
no network, browser, account, or private data. Live end-to-end checks (a
real Amazon search, a real SmiteBrain build) are deliberately not part of
this suite; the "Last verified" lines in the playbooks record those.

| Suite | Covers |
| --- | --- |
| `finance_checks.py` | financial-audit: parsing, signs, categories, recurring estimates, promo deadlines and the evaluation-date policy |
| `scrub_memory_checks.py` | scrub scanner coverage accounting, archive inspection, output redaction; memory audit Unicode-safe duplicate detection; frontmatter/sidecar description agreement across all skills |
| `migration_models.py` | schema-migration-safety: executable models of the adoption, baseline, concurrency, constraint-guard, and nontransactional-DDL rules, each with the pre-fix behaviour as a failing control |
| `smite_checks.py` | smite-2-builds: completed-item gate, role fallback, patch freshness, tier-cache versioning, aspect/relic vote denominators (network stubbed) |
| `amazon_checks.py` | amazon-search: marketplace validation, page classification, price and unit-price parsing, smoke-test assertions (browser stubbed); price-history evidence-handoff wording |

Fixtures assemble credential-shaped strings at runtime instead of storing
them literally, so this folder passes the repository's own scrub scan.
