---
name: accessibility-design-guard
description: "Run an accessibility pass over a web app and freeze what it fixed as automated design-guard tests: keyboard-operable controls with accessible names, focus that moves and stays visible, no zoom locks, sane tab order through interactive text, timed-task accommodations that never move the pass bar, and design-system rules (banned copy, token-only colours, terminology standards) enforced as tests that fail on drift. Use when auditing a web UI for accessibility, adding an accommodation, or turning a design document's written rules into CI enforcement."
---

# Accessibility & Design Guard

An accessibility fix that is not guarded regresses. Someone restyles the slider, the invisible focus trap is back, and nobody notices because nothing failed. A design rule that lives only in a document is a wish: the banned phrase returns in the next copy edit, the raw palette colour creeps back in the next component. This skill has two halves. First, an audit pass that finds and fixes the barriers. Second, a guard pass that encodes every enforceable rule the audit relied on as automated tests, so drift fails the build instead of reaching users.

It composes with `verify-before-shipping`: that skill decides whether a change may be called done. This one decides what an accessibility pass must cover, how each fix is proven, and which of the design system's rules deserve to become tests.

## When this applies

- Before shipping a web UI surface that has never had a deliberate accessibility pass, or after one is reported broken.
- When adding an accommodation (extended time, reduced motion, text scaling) to a timed or scored task.
- When a design document states rules (voice and copy standards, colour tokens, terminology) that the codebase keeps quietly violating.
- When a review finds an accessibility defect class, not just an instance: fix the class, then guard it.

A single known defect with an obvious fix does not need the full pass; fix it, add the one guard assertion it earns, and move on.

## The audit checklist, in running order

Work the list in this order; later items assume the earlier ones hold.

1. **Pointer-only interactions get a keyboard and switch equivalent.** Any hold-to-X, drag, or press-and-hold control must also work as a discrete toggle: press to start, press again to stop or send, `aria-pressed` reflecting state, pointer behaviour unchanged. A voice-record button that only works while a finger or mouse is held down excludes every keyboard and switch user from speaking at all.
2. **Every control has an accessible name.** Sweep for icon-only buttons, custom record buttons, bare textareas, and clickable divs. The canonical find of every real pass is a control with no accessible name whatsoever, often the primary action on its surface. Names come from the app's string system, never a hardcoded label in one language.
3. **Step and view changes move focus.** When a wizard, lesson player, or multi-part form swaps its content, focus goes to the new step's heading (a `tabIndex={-1}` heading and a ref, or the platform equivalent) so keyboard and screen-reader users land where the change happened instead of being stranded at the top of a replaced view or on a removed element.
4. **Focus is visible on every focusable element, including custom-styled ones.** The classic trap is a native input made invisible for styling (an `opacity-0` range slider under a custom track): keyboard focus arrives on an element nobody can see. Put the visible ring on the wrapper, driven by the child's focus state (`:focus-visible` / `:focus-within`), in the design system's ring token, and assert the ring colour meets at least 3:1 contrast against its background.
5. **No zoom locks.** The viewport meta carries no `maximum-scale` and no `user-scalable=no`. Pinch zoom is an accessibility feature, not a layout bug. Prove the removal with a repo-wide search, not by reading the one file you edited.
6. **Interactive long text gets a sane tab order.** A reading passage where every word is a lookup target must not become hundreds of tab stops. Use a roving tabindex (the passage is one tab stop; arrow keys plus Home/End move within it) and put a skip link before the passage so keyboard users can jump past it entirely. Non-interactive text stays non-interactive, and the pointer lookup behaviour is preserved exactly.
7. **Timed tasks offer a time accommodation that never moves the pass bar.** See the accommodations section below; the checklist-level rule is that the accommodation exists wherever a countdown gates a scored result, and that it changes time only.
8. **Status and recording indicators are labelled in the UI language system.** Recording states, timers, and progress announcements are real strings in the translation registry, labelled for assistive technology, and worded for the interaction as it actually works now (a toggle says "press again to send", a hold button says "hold"). A hardcoded status line in one language is a defect even when it is the product's own primary language.
9. **Focus is not obscured by fixed or sticky elements (WCAG 2.2 SC 2.4.11, Focus Not Obscured — Minimum).** When an element receives keyboard focus, no sticky header, fixed bottom action bar, floating audio or chat bar, or consent banner may cover it. Give the scrollable content `scroll-margin-top` / `scroll-margin-bottom` at least equal to the fixed elements' heights, and prove it by tabbing through the surface, not by reading the CSS.
10. **Pointer targets meet the minimum size (WCAG 2.2 SC 2.5.8, Target Size — Minimum).** Interactive targets are at least 24×24 CSS px, or carry equivalent non-overlapping spacing so a 24 px target fits without hitting a neighbour. Primary mobile touch controls should be 44×44 CSS px. An undersized target that claims the spacing exception gets its spacing measured, not assumed.

## Accommodations design

An accommodation that is not part of the record did not happen. Build timed-task accommodations in four parts:

- **Preference:** a user setting stored with the app's existing settings storage (client-side key, sensible default of standard time), with a small set of named levels such as Standard / 1.5× / 2× / No time limit.
- **Application:** the countdown scales multiplicatively from the stored preference. Nothing else changes: not the questions, not the scoring, above all not the pass mark.
- **Disclosure:** the start screen shows the effective time and states plainly that the pass mark is unchanged. An accommodation the user has to discover mid-attempt is a trap, not an accommodation.
- **Record:** the attempt payload carries the accommodation and the server stores it with the result, so the record of what happened includes the conditions it happened under. If the current schema genuinely cannot carry the field yet, ship the client half, verify the server dropping the field is harmless (an ignored unknown field, not an error), and write the exact server follow-up (migration, schema field, insert) onto the project's tracked tidy list in the same change. Never let the follow-up live only in a commit message or a chat.

## Verification: behaviour, not eyeballs

- **Every fix gets a behavioural test,** in the DOM test environment the project already uses: render the surface, drive it with keyboard events, activate the control, assert focus landed where the fix promises, assert the toggle's pressed state flips, assert the countdown reflects the accommodation. A screenshot or a visual once-over is not verification of behaviour.
- **Keyboard-walk every touched surface** in a real browser when one is available: tab order, focus visibility, activation. Report what was walked. Surfaces verified only by trace and tests get reported as exactly that, not upgraded to "checked in the browser".
- **Negative controls for every new guard.** A guard that cannot fail is decoration. Seed the violation (the banned phrase in a scratch string, the raw palette class in a scratch file), watch the guard fail, remove the seed, watch it pass. Report the negative control with the guard.
- **Run the full gate output to files** and cite summary lines from the files, per `verify-before-shipping`.

## Design guards as tests

A worked guard-test pattern — named patterns with recorded reasons, zero-count assertions, self-cleaning exemptions, and negative controls — is in `references/guard-test-pattern.md`.

After the audit, convert the design system's enforceable rules into a guard test suite that runs in CI:

- **What to encode.** Banned vocabulary in user-facing copy (planner or engineering jargon the design document forbids in favour of plain user language); token-only colour (raw palette utility classes, white/black utilities, arbitrary hex classes, inline colour literals all banned in favour of named tokens); minimum text size; icon-source discipline (one icon library; emoji are content, not chrome); accent-colour role limits; legacy class dialect bans after a rename. Add a contrast-pair test for the token file itself so the tokens the guards force people onto are themselves compliant.
- **Guard shape.** Each rule is a named pattern with a recorded reason ("why" text that teaches the fix, not just the ban). Counts are zero and stay zero: there is no baseline file to raise. If a count is not zero, the change that raised it is the bug.
- **Scope the scan to what users actually read.** For copy rules, scan translation values and the pages that carry their own copy, not every string in the repository. Internal identifiers, comments, test names, and data-domain strings are out of scope; scanning them manufactures false failures and teaches people to disable the guard.
- **Exemptions are explicit and self-cleaning.** A file that legitimately contains a banned literal (a third-party brand mark is the usual case) goes on a named exemption set, and a separate assertion fails when an exempted file no longer exists, so exemptions cannot rot silently.
- **Deliberate non-bans are recorded in the test.** A term the design document restricts in one context but that legitimately appears in another (a settings label, an account-deletion confirmation naming the data it erases) stays unbanned, with the reason written beside the pattern set. A known gap recorded as a decision is maintainable; a gap nobody wrote down reads as an oversight and gets "fixed" into a false failure later.
- **Terminology fixes ride along honestly.** When a guard is born from a copy defect, the copy fix and the guard land together; if the same document's terminology standard indicts copy outside the guard's current scope (a sibling label the guard does not yet scan), list it on the tidy list rather than silently widening or silently skipping it.

## The undecidable-check rule

Some attractive checks cannot be made mechanical. Whether a utility class is "defined" under a JIT CSS engine whose class strings are composed in template literals, generated from data, and purged dynamically has no decidable answer from source text: any regex strict enough to catch real dead classes also fails live code, and any regex loose enough to pass live code catches nothing. When a proposed guard hits this wall:

- Drop the check deliberately, in the change that proposed it, and say why in the report.
- Record the concrete dead ends it was meant to catch (the specific dead class hooks, the specific unguarded files) on the project's tidy list as items needing human judgement.
- Never fake coverage with a weaker pattern that passes today and means nothing. A missing guard is honest; a guard that cries wolf gets disabled, and then it guards nothing while claiming to.

## Reporting

Report per checklist item: what changed, how it was verified (test names, the keyboard walk, the negative control), and what was found but left, with the reason. Left items go on a written tidy list in the project, each with enough context for a future pass to pick it up cold: the surface, the defect, and why it was deferred. An accessibility pass whose leftovers live in chat has not finished; it has stopped.
