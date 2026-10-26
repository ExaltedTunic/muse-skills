# Guard test pattern (worked example)

A design-guard suite is one test file that scans the component tree and the
user-facing string sources, organised as a pattern record plus a copy scan.
The shapes below are framework-agnostic; the worked example used vitest over
a React/TypeScript tree, but any test runner with filesystem access does.

## 1. The pattern record

Each visual rule is a named regex with a `why` that teaches the replacement,
not just the ban. The suite walks every component file, counts matches per
rule per file, and asserts the total is zero.

```ts
const GUARD_PATTERNS: Record<string, { regex: RegExp; why: string; roots?: string[] }> = {
  rawPalette: {
    regex: /\b(?:text|bg|border|ring|fill|stroke)-(?:slate|gray|red|blue|green|…)-\d{2,3}\b/g,
    why: 'Raw palette colours bypass the tokens; use the named ink / paper / status tokens.'
  },
  arbitraryHex: {
    regex: /-\[#[0-9a-fA-F]{3,8}\]/g,
    why: 'Arbitrary hex colours bypass the tokens.'
  },
  inlineColorLiteral: {
    regex: /\b(?:color|background|backgroundColor|borderColor):\s*['"`](?:#[0-9a-fA-F]{3,8}|rgba?\()/g,
    why: 'Inline colour literals bypass the tokens; use var(--token).'
  },
  tinyText: {
    regex: /\btext-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/g,
    why: 'Nothing under 12px.'
  },
  emojiIcon: {
    regex: /🎯|💡|🔊|📚|🎧/g, // the chrome set your design doc bans
    why: 'Icons come from the icon library only; emoji are content, not UI chrome.'
  }
  // Optional per-rule `roots` restricts a rule to a subtree (e.g. a legacy
  // dialect ban that only applies where the new system is already adopted).
};
```

Rules that earn their place in a real suite, beyond the sketch above:
white/black utility classes (they break alternate themes), accent-colour
role limits (the primary-action colour used as decoration), and legacy alias
or dialect bans after a design-system rename (old token names, old type
classes), so a rename cannot quietly un-happen.

## 2. Exemptions that clean up after themselves

```ts
const EXEMPT_FILES = new Set(['components/third-party-sign-in-button.tsx']);

it('exempt files still exist (no stale exemptions)', () => {
  for (const rel of EXEMPT_FILES) expect(existsSync(join(ROOT, rel))).toBe(true);
});
```

An exemption for a deleted or renamed file fails the suite, so the exemption
list cannot rot into a junk drawer.

## 3. The banned-copy scan

Scan what users actually read: the translation table's string values (every
locale) and the specific pages that carry their own copy. Do not scan the
whole repo.

```ts
// Deliberately NOT banned: terms the design doc restricts in label contexts
// but that legitimately appear elsewhere (an account-deletion confirmation
// naming the data it erases; a settings label). Each non-ban is a decision;
// write the reason here so a future editor does not "fix" it into a ban that
// fails on the legitimate use instead of on new regressions.
const BANNED_PHRASES: Record<string, RegExp> = {
  'planner jargon one': /\b…\b/i,
  'planner jargon two': /\b…\b/i
  // one entry per forbidden phrase, in every UI language the doc governs
};

it('no translation value uses banned vocabulary', () => {
  const offenders: string[] = [];
  for (const [key, value] of Object.entries(TRANSLATIONS)) {
    for (const [phrase, regex] of Object.entries(BANNED_PHRASES)) {
      if (regex.test(value.en) || regex.test(value.no)) offenders.push(`${key}: "${phrase}"`);
    }
  }
  expect(offenders).toEqual([]);
});
```

## 4. Negative control (run once per new guard, report it)

1. Add the violation to a scratch location the guard scans (a throwaway
   translation value, a scratch component with a raw palette class).
2. Run the guard suite: it must fail, naming the seeded violation.
3. Remove the seed. Run again: green.
4. Record both runs in the change report. A guard never observed failing is
   assumed broken, however good its regex looks.

## 5. Audit pass worksheet

Run the checklist in this order; one row per surface touched.

| # | Check | Verify by |
|---|-------|-----------|
| 1 | Hold/drag/pointer-only controls have a toggle equivalent (`aria-pressed`) | Behavioural test: keyboard activation starts and stops the action |
| 2 | Every control has an accessible name | Automated name sweep + manual pass over icon-only and custom controls |
| 3 | Step/view changes move focus to the new heading | Test asserting `document.activeElement` after a step change |
| 4 | Focus ring visible on custom-styled inputs | Wrapper ring via `:focus-visible`/`:focus-within`; contrast assertion ≥ 3:1 for the ring token |
| 5 | No `maximum-scale` / `user-scalable=no` anywhere | Repo-wide search returns zero |
| 6 | Interactive long text: roving tabindex + skip link | Test: one tab stop for the passage; arrows/Home/End move; skip link jumps past |
| 7 | Timed tasks: accommodation scales time only | Test: countdown reflects the preference; start screen shows effective time and unchanged pass mark; payload carries the accommodation |
| 8 | Status/recording strings in the i18n registry | Search: no hardcoded status strings in the touched components |
| 9 | Focus is not obscured by fixed or sticky elements | Behavioural test: tab through the surface; the focused element remains fully uncovered under this skill's stricter policy, with scroll margins offsetting fixed/sticky elements |
| 10 | Pointer targets meet the minimum size | Measure: targets are at least 24×24 CSS px or carry qualifying non-overlapping spacing; primary mobile touch controls are 44×44 CSS px |

## 6. The dropped-check record

When a proposed guard proves undecidable (the utility-class "definedness"
check under a JIT CSS engine is the worked example: class strings are
composed, generated, and purged dynamically, so no source scan can decide
definedness without false positives), record it where the next pass will
find it:

- what the check was meant to catch, with the concrete instances found by hand;
- why the mechanical version fails (name the false-positive mechanism, not
  just "too noisy");
- the disposition: dropped deliberately, instances listed on the tidy list
  for human judgement.

Never ship the weaker regex that passes today. It will fail on legitimate
code within a few changes, someone will disable the whole suite to get their
work in, and the honest guards die with the fake one.
