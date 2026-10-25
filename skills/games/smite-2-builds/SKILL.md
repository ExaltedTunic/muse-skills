---
name: smite-2-builds
description: Build one current-patch, role-specific Smite 2 build from recent top player match data on SmiteBrain, cross-checked against SmiteSource, for when the user asks for a god build.
---

# Smite 2 Build Builder

## HARD GATE: live data or nothing (read this first)

Smite 1 is a different game with a different item shop, but its items and metas dominate training data and old guides. The worst failure of this skill is a build filled from memory instead of live data: that is how dead items, stale names and decade-old metas end up presented as current. (Field report, Oct 24, 2026: a Gemini run of this skill produced a Hades build from memory that matched the live consensus on only two of six items, with the wrong starter form and the wrong relic, while live Smite 2 data for Hades existed the whole time.)

- Every item named in the answer must be verified in this session against a live, current-patch Smite 2 source (the SmiteBrain item data or the official Smite 2 wiki). Verified means seen in the retrieved source, not remembered.
- Boots are the one absolute tell: Smite 2 has no boots, so anything listing Shoes of the Magi, Shoes of Focus, Warrior Tabi, Ninja Tabi, Reinforced Greaves or Talaria Boots is a Smite 1 build. Every other item is judged by one test only: it must appear in the live current-patch source you retrieved. Do not ban items from memory, because Smite 2 keeps re-adding legacy items mid-beta (Bancroft's Talon and Spear of the Magus are current-patch items as of Open Beta 46), and a memorized ban list goes stale and wrongly rejects real meta items.
- If live data cannot be retrieved in this session (no script, no browsing available), do not fill the build from memory. Present only what can be verified and label the build unverified, or say the data is unavailable. Never attach a sample size or match counts that were not actually computed.
- Final self-check before answering: re-read the items one by one and confirm each appeared in the live source. If one did not, replace it with a verified item or flag it in the answer.

## When to use

- Use this skill whenever the user asks for a Smite 2 build, item order, starter, relic, aspect or skill order for a god, with or without a role.

- Return one build, not a menu of builds. Keep the answer concise and factual, presented as the compact card defined in the Present section.

## Defaults

- When a god is named without a role, default to that god's most common role: the role with the largest recent sample for the god in the data (with the script, omit --role and it selects the god's primary role in the sample; when browsing, compare the per-role sample sizes). Never assume a role just because it is someone's favourite. If the most common role cannot be determined, ask which role instead of assuming one.

- Default the mode to Conquest. Every source below defaults to Conquest, and Arena or Assault builds are out of scope unless the user asks.

- Target top player meta as the definition of optimal. Recent data is a hard requirement, so a build from an older patch fails no matter how strong it looks.

- Break ties toward the early aggression dive and burst variant when two builds sit close in the data, and say in one line when the tiebreak decided the pick. If the user has a stated playstyle preference of their own, it wins over this default.

- Honour an aspect or variant the user names, such as tanky, basic attack or ability based, by filtering the sample to it instead of returning the generic consensus.

## API verdict

- Treat all three sources as having no public documented API. This was verified on 2026-10-23 for SmiteFire, SmiteSource and SmiteBrain, and none of them publishes developer docs, keys or an API reference.

- Use the machine readable route each site already exposes instead of scraping rendered pages. SmiteBrain serves its page data as structured JSON, and SmiteSource embeds its full build data in the page payload.

- Skip the official Hi-Rez developer API for builds. It is credential gated, built for the first Smite, and its recommended item data does not describe the current Smite 2 meta.

## Fetch the build

- Run the bundled script first for every request. It reads SmiteBrain, which rebuilds its pages hourly from real top player matches, and aggregates the sample into one consensus build.

```
python3 ~/workspace/custom-skills/smite-2-builds/scripts/fetch_build.py <god> --role <role>
```

- Pass the role as Jungle, Solo, Mid, ADC or Support. SmiteBrain calls the ADC role Carry, in both the page path and its data, and the script maps ADC to it. Run with `--json` to build the answer card, which is the default way to answer. Use `--compact` only for the plain text fallback format. Pass `--aspect <substring>` to filter the sample to one aspect before aggregation; if no sampled build uses that aspect, the script says so and exits without emitting a build.

- Read the script output as evidence with limits. The sample is the 10 most recent top player builds for that god and role, counts such as 7/10 are the support behind each pick, and the starter may be recorded in its evolved form, so the script groups starters by family line.

- Treat any item the data returns without an icon as suspect until verified. SmiteBrain sometimes serves a pre-rename name with no icon for an item that was renamed in a later patch, and the script already maps the known case, Brawler's Ruin to Brawler's Beat Stick, renamed in OB15. Verify a new suspect against the SmiteBrain items index or the official Smite 2 wiki before it goes on a card, and never annotate an item with a mechanic such as anti-heal unless the current patch item text says so.

- Fill the six slots with completed Tier 3 items only. Match data records what a player held at match end, so unfinished Tier 1 and Tier 2 components appear in final builds, and a component is not a build item. The script checks each candidate's tier on its SmiteBrain item page and drops known components from the core and flex. (Learned 2026-10-24 when a Skeggox, a Tier 2 component, shipped as a sixth item.)

- Take the skill order from the same script run. It extracts the ability level order of the best matching SmiteSource build for the role and the ability names from SmiteBrain, and reports the start sequence, the max priority and the ultimate levels.

- Quote the patch from the script output, which reads it from the live SmiteBrain page. Only current patch data counts toward the build.

## Cross-check the build

- Open the SmiteSource builds page for the same god with `browser.open` when you need its win rate or the script found no skill order there. SmiteSource carries curated builds with a win rate that SmiteBrain does not publish, and its ability level order is the fallback skill order source.

- Prefer SmiteBrain for the item core when the two disagree, because its sample is recent match data. Prefer SmiteSource for skill order and any short build notes.

- Say in one line when SmiteSource has no build for that god or role, then ship the SmiteBrain build and flag the missing skill order as the Present section requires. Thin coverage on off meta picks is normal there.

- Open SmiteFire only when the user asks why a build works or the two data sources conflict. Use only guides tagged for Smite 2 with a recent date, and never take its top listed guide at face value, because the site interleaves first game guides with Smite 2 guides.

- Discard any guide or build showing first game tells, such as boot items, Season 8 to 10 or Year 10 in the title, or relics that no longer exist. A build with boots is never a Smite 2 build.

## Present the build

- Fill all six item slots in every build. The core is the six most played distinct items for that god and role in typical buy order, and the starter sits in front of them. A card with open slots is a failed build, and the flex line only names swaps beyond the six.

- Present the build as a small HTML widget card with `widget.create_html_widget` so the icon size is set in CSS and actually holds. Plain chat images render at the client size no matter what the file or URL says, which is why both earlier attempts came out huge.

  - Build the card from the script `--json` output in this shape: a header line with god, role, patch and sample, one row of items in buy order with each icon at 38px and its name under it, the starter tagged, and a muted footer with two lines, one for relic, aspect and at most two flex swaps, and one for the skill order as start sequence, max priority and ultimate levels.
  - Show the name alone in a cell when the script returns an item without an icon, which happens in the data. Never invent an icon URL to fill the gap.
  - Keep the card to one row of items plus the footer. No extra sections, stats or prose inside the card.
  - Treat a build with no skill order as incomplete. When neither the script nor the SmiteSource page yields one, say so in the one sentence outside the card instead of guessing.

- Fall back to the plain text build when a widget cannot render, such as an external messaging channel. Line one gives the god, role, patch and sample, line two is the buy order as one chain of item names joined by arrows with the starter first, line three gives the relic, the aspect and at most two flex swaps, and line four gives the skill order. The script `--compact` output is already in this shape.

- Add at most one short sentence outside the card when a tiebreak or a source disagreement matters. No closing explanation paragraph.

- Present the majority archetype as the build when the sample splits between two, such as ability based and basic attack based, and name the minority archetype with its share inside the header line.

- Adjust only the flex slots when the user provides the enemy composition. State the swap and its reason in one line and leave the core untouched.

- Never invent an item, a stat, a win rate or a skill order. Quote a win rate only when it was read from the SmiteSource page in this request, and attribute it there.

## When it breaks

- Fall back to opening the SmiteBrain builds page for the god and role with `browser.open` when the script errors or finds no data, and read the builds from the page text.

- Fall back to SmiteSource alone when SmiteBrain is unreachable, and say the match data source was down so the build rests on the curated source only.

- Report a god with no data on either source plainly instead of filling the gap from memory. Item pools change every patch and a remembered build goes stale fast.

- Run the script once per request. Do not loop it across the roster, because the value is a single checked build at human scale.

## Websites

- [SmiteBrain](https://smitebrain.com/gods/thor/builds/jungle) for the primary build data. The pattern is /gods/<god slug>/builds/<role>, the script reads the same data as JSON, and the page header states the current patch and hourly update claim to verify against the script output.

- [SmiteSource](https://smitesource.com/builds?god=Thor) for the curated cross-check. The pattern is /builds?god=<god name>, and the page must actually show a build for the requested role before its win rate or skill order is quoted.

- [SmiteFire](https://www.smitefire.com/smite/god/thor-22) for written guide rationale only. The pattern is /smite/god/<god slug>-<site id>, the id differs per god, and every guide there needs the Smite 2 tag and date check from the cross-check section before any of it is used.

Last verified: 2026-10-25 from a Muse VM. SmiteBrain returned live Open Beta 46 data with a match timestamp from the same day. The script produced full six slot builds for Thor, Pele, Bastet and Fenrir in Jungle, with skill order extraction confirmed on Thor, Pele and Fenrir, aspect filtering and the on-disk item-tier cache verified live, and the card format is the compact one described above.
