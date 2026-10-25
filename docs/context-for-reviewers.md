# Context for Reviewers: Muse Skills and This Repository

This document gives a reviewer (human or AI) the platform context needed to review the skills in this repository well. It is a merged and corrected version of an external research brief on Meta Muse and a corrections addendum written from inside a live Muse environment. Only claims that were verified against a real environment are stated as fact here. Where the original brief speculated about implementation internals (daemon names, model parameters, security plumbing) that cannot be observed from the agent's seat, this document says what is observable instead, and the speculation is omitted rather than repeated.

If you are about to review this repository, read this first. It will save you from the two failure modes outside reviews keep hitting: flagging deliberate conventions as defects, and aiming findings at platform mechanics that do not exist.

## 1. The platform, at the level a reviewer can rely on

- **Muse is a persistent personal agent, not a stateless chatbot.** Each user has a dedicated, persistent Linux virtual machine. Files, scheduled jobs, and background work survive between conversations. The agent has a shell, a real browser, a filesystem, and the ability to delegate subtasks to subagents.
- **Cognitive state is file-first.** The agent's persona, identity, operator profile, curated long-term memory, and operating conventions live in plain-text files at the home root (`SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, `AGENTS.md`, `TOOLS.md`). Durable work lives in goal workspaces anchored by a `GOAL.md`. Long conversations are compacted; files, not context, are the durable memory. A skill that assumes the agent will simply remember something across sessions is making an environment error.
- **Consequential actions are approval-gated.** Sending messages, publishing, pushing code, and purchases pass through explicit user approval. Skills in this repository state their approval boundaries explicitly; a skill that acts externally without a checkpoint is defective by this platform's rules, and a skill that asks for approval before read-only work is over-gated.
- **Credentials never enter the agent's context.** Saved logins live in a secure vault and are filled by the browser at the moment of use; connected services are OAuth-based. A skill that asks the user to paste a password, token, or card number into chat or into a file is defective, full stop.
- **Guaranteed script environment.** Linux, bash, Python 3 (standard library always available; virtualenvs work for more), Node for repository tooling. The scripts bundled in this repository deliberately restrict themselves to the Python standard library so they run anywhere; hold them to that.

## 2. Skills and connectors are different things

- **Connectors** are the plumbing: authenticated access to a service (mail, calendar, a retailer's API), usually a CLI or MCP server with its own documentation.
- **Skills** are the playbooks: self-contained instruction packages that teach the agent when and how to orchestrate its tools, connectors, and bundled scripts to do a class of work reliably.

This repository contains skills only. When a skill references a connector or a platform tool by name, that reference is a Muse-specific seam; good skills name the seam so the workflow can be adapted elsewhere (see the README's Portability section).

## 3. Where skills live

A Muse environment has several skill locations with different jobs. Reviewers consistently get this wrong, so here it is precisely:

| Location | What it holds |
| :--- | :--- |
| `/opt/muse/skills/` | The product skill catalog shipped with Muse. Read-only. |
| `/opt/hatch/skills/` | A second, larger tree of connector-flavoured skill packages. Distinct from the product catalog, not a mirror of it. |
| `~/workspace/custom-skills/` | The user's live custom skills: authored and iterated in session. **This is the source of truth for every skill published in this repository.** |
| `~/workspace/skills/` | A legacy location under older naming. The actively maintained repertoire is `custom-skills/`. |

If a claim about a skill depends on which copy is newer, compare contents, not timestamps.

## 4. Anatomy of a skill in this repository

Every skill here is a **pair** of files, plus optional support folders:

```text
<skill-name>/
├── SKILL.md          # YAML frontmatter (name, description) + the playbook
├── skill.yaml        # Sidecar: name, title, description, category, include_in_prompt
├── scripts/          # Optional: deterministic helper scripts (stdlib only)
├── references/       # Optional: deep-dive material the playbook links to
└── config.example.json   # Optional: an example of user config kept outside the skill
```

Conventions that are **deliberate** and should not be flagged as inconsistencies:

- `SKILL.md` frontmatter `name` is kebab-case and matches the folder name. `skill.yaml` `name` is snake_case. The difference is a uniform convention of this collection, not drift.
- The `description` (in both files) is the routing index. It must say what the skill does **and** when to use it: expect a "Use when..." trigger clause. A description without a trigger condition is a real finding; `allowed-tools`, `triggers`, and similar keys from other harnesses are not part of this platform's convention and their absence is not.
- A frontmatter `description` containing a colon followed by a space must be quoted, or the frontmatter is invalid YAML. Strict-parse frontmatter before judging anything else about a skill.
- `category` in `skill.yaml` follows the purpose folder the skill sits in (all skills in `skills/agent-workflow/` carry the same category, and so on).
- Every file in `scripts/` and `references/` should be named or linked from `SKILL.md`. An unlinked reference file is dead weight a reader will never find; that is a real finding.
- User data never lives in the skill folder. Profiles, ledgers, configs with real figures, and statements live in the user's private workspace; the skill ships method and an example config only.

## 5. Progressive disclosure: how skills are loaded

Skills are consumed in three stages, and review criteria follow from this:

1. **Catalog stage.** Only frontmatter (name + description) across all installed skills is in context. Routing decisions are made from descriptions alone, which is why description quality is a correctness issue, not a style issue.
2. **Activation.** When a request matches, the full `SKILL.md` playbook enters context. Playbooks should be lean and procedural.
3. **On demand.** `references/` files are read only when the playbook sends the agent there; `scripts/` are executed, with only their output entering context. Heavy tables, templates, and long examples belong in references, not in the playbook body.

## 6. How this repository is published

- The repository is a **share copy, never the live folder.** Live skills are edited and verified in `~/workspace/custom-skills/`, then copied into a staging tree and pushed. Push mechanics can create and update files but never delete or rename, so a file removed locally needs an explicit remote cleanup; a "missing deletion" is a known workflow property, not carelessness.
- Commits use the platform's noreply author address. Any personal identifier appearing in any file (names, emails, home paths, postal codes) is a **release-blocking defect**. The repository's own `scrub-before-sharing` skill and its bundled scanner are the gate, and they apply to every file in a bundle, scripts and configs included, not just the visible document.
- Some skills are **local-only by design** because they hold a private profile; the published version, where one exists, is a generalization of the method. Review the generalization for method. Do not expect parity of personal detail, and do not flag the absence of the private original.
- Third-party work is **link-only** in this collection. A skill that builds on someone else's tool links upstream instead of mirroring it; the absence of a mirrored copy is deliberate.

## 7. The review standard for this repository

Evaluate each skill on:

1. **Routing precision.** Does the description state capability and trigger conditions precisely, without overlapping ambiguously with sibling skills or the product catalog? Could two skills both claim the same request?
2. **End-to-end coherence.** Does the file agree with itself? Claims in the prose must match the bundled scripts' actual behaviour, the README's description of the skill, the changelog, the skill's own examples, and its reference files. A workflow step that references a file, flag, or behaviour that does not exist is a defect. So is a number, default, or limit stated in one place and contradicted in another.
3. **Completeness.** Are there gaps: an edge case the workflow will obviously hit and does not handle, a promised output that is never defined, a setup step missing between download and first run? Distinguish a genuine gap from a deliberate scope boundary; the boundary is usually stated, and stated scope is not a gap.
4. **Progressive disclosure hygiene.** Is the playbook lean, with bulk in references and determinism in scripts? Is every bundled file reachable from the playbook?
5. **Environment fit.** Do paths, commands, and assumptions match the platform described in §1 and §3? Does the skill lean on files for durability instead of assuming memory?
6. **Approval and credential boundaries.** Are external actions gated, and does the skill keep secrets out of chat and files per §1?

And the protocol this repository's reviews are held to, on the reviewer's side:

- **Claims must be checkable.** Quote the line, name the file, give the reproduction. "This seems off" is not a finding.
- **Verify against the source, not against plausibility.** If a claim cannot be checked from the material available, label it unverifiable rather than asserting it.
- **Report dispositions in four buckets:** VERIFIED (proven true against a source), CORRECTED (real defect, wrong quoted detail or unsafe proposed fix), REFUTED (checked and wrong), UNVERIFIABLE (no anchor available). Keep definite issues and suspicions in separate lists.
- **Recommendations are proposals.** The repository's owner gates what lands. A review that assumes its own fixes will be applied wholesale has misunderstood its role.
