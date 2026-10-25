# Agent workflow

Skills that change how your Muse agent works with you day to day: how it builds an identity, how it handles outside reviews, how it verifies before claiming done, how it keeps its memory honest, and how it prepares anything that leaves the household.

- [identity-adaptation](identity-adaptation/) - Grow a durable, personal identity with your user over time, with a plain-words feedback contract and a periodic drift review.
- [external-review-intake](external-review-intake/) - Verify claims from relayed outside reviews against the source before acting, and fold in only what the user approves.
- [scrub-before-sharing](scrub-before-sharing/) - Strip private data from every file in a bundle and verify the clean copy before it is shared.
- [verify-before-shipping](verify-before-shipping/) - Require runnable evidence before claiming any script, skill or document works: smoke tests, doc-versus-behaviour cross-checks, full-output gate runs.
- [memory-hygiene](memory-hygiene/) - Audit long-term memory files on a cadence: merge duplicates, retire stale threads, resolve contradictions, hold a density ceiling. Includes a small stdlib audit script.
- [agent-orchestration](agent-orchestration/) - Run multi-agent build programs: scoped briefs, isolated worktrees, one integrator, and verification that re-derives every claim from diffs and gate logs.
- [independent-review-swarm](independent-review-swarm/) - Commission an independent multi-reviewer audit of finished work, with claim re-verification and fix-now / owner-call / parked bucketing.
- [deep-review](deep-review/) - The depth standard for any review pass: every load-bearing claim verified against a real anchor, plus a feasibility check; reports issues found and coverage checked.
- [schema-migration-safety](schema-migration-safety/) - Make hand-written SQL migrations trustworthy: transactional ledger, evidence-based adoption, frozen ORM journal, drift audits, code-derived CHECK constraints.
- [accessibility-design-guard](accessibility-design-guard/) - Audit a web app for accessibility and freeze the fixes as automated design-guard tests that fail on drift.
