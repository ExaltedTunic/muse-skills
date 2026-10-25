---
name: norway-job-search-flow
description: "Run a verification-first job search for roles in Norway when the candidate needs a skilled-worker residence permit: define a private search box, sweep Norwegian sources, verify employers in Brønnøysund and the staffing register, track permit support only on written evidence, keep a ledger as the source of truth, and tailor applications only after verification and per-listing approval."
---

# Norway Job Search Flow

A pipeline for a cross-border job search where a role has to pass two tests at once: it has to be a real career fit, and it has to work for a Norwegian skilled-worker residence permit. The method is verification first. Do not spend tailoring time on a vacancy until the employer, the employment arrangement, and the likely permit path have been checked.

This skill contains rules only. The candidate's personal facts, target list, application history, contacts, and documents belong in a private candidate profile and a private ledger outside the skill.

## Private inputs the candidate supplies

Before the first sweep, the candidate writes a private search profile. Keep it out of the skill and out of any shared repo. It should define:

- Current country of residence and the permit route being used.
- Planned home base in Norway, written as a place or region the candidate chooses to track privately.
- Maximum one-way commute by car, including ferry crossings and typical waits where relevant.
- Any named locations that are in range by exception, and the exact on-site frequency that makes an exception workable.
- The rule for offices beyond the commute limit, for example remote only with on-site presence at or below a set frequency.
- Target roles and seniority levels.
- Technical stack and evidence sources for tailoring.
- Norwegian language level and any language requirements that are hard blockers versus preferences.
- Education and qualification summary, in honest words. Never inflate a credential, and never call a qualification equivalent unless an official assessment says so.
- Availability windows, such as a planned Norway trip when in-person interviews are possible.
- Timing priorities. Do not invent an offer-by deadline unless the candidate sets one explicitly.

Update the private profile when the candidate confirms a fact changes. Do not fork personal facts into the reusable method.

## Objective and eligibility gate

Every target role must satisfy both conditions:

1. Real employment by a Norwegian-registered employer on Norwegian payroll, in an eligible arrangement below.
2. The employer is willing to complete the employer-side confirmation step in UDI's system so the candidate can apply for a skilled-worker residence permit.

Either condition failing is a blocker.

Eligibility by employment arrangement:

- **Direct**: employed by the Norwegian entity on Norwegian payroll. Eligible to keep verifying.
- **Staffing**: conditionally eligible. Only when the employer is in Arbeidstilsynet's staffing register and a client assignment can be confirmed up front where UDI requires it. Permits through staffing arrangements can run one year at a time. If either condition fails, the role is blocked, not parked hopefully.
- **Employer of record**: hold. Do not tailor or apply unless the provider confirms in writing that it will act as the employer on the skilled-worker application. Default assumption: these arrangements usually require existing Norwegian work authorization.
- **Contractor**: blocked for an employment-based permit route. Park it unless the candidate deliberately wants to explore a separate non-employment path.
- **Unknown**: the default. Most postings do not say. Unknown is an open question to resolve through the posting, the employer's careers page, or the permit question, before tailoring work is spent on the role.

Work-authorization facts to keep straight:

- The candidate applies for the permit; the employer's part is confirming the job offer through UDI's system when that step applies. Check the current UDI checklist before relying on the exact flow, because the steps for applications from abroad can change.
- The candidate cannot start the role until the permit is granted. Never promise a start date that ignores permit processing.
- The job normally has to be full-time; UDI accepts 80 percent or more for this route. Verify against the current checklist.
- Remote work has to be part of the job the permit is granted for. When an offer is close, ask for the home-office arrangement to be stated in the offer.

## Salary and qualification screening

Record the current UDI salary floor for the qualification the role requires, from udi.no, in the ledger. Where a collective agreement applies, its rate governs. Floors change, so re-check before relying on a stored number, and always re-check if the last verification is more than six months old.

Reference points from the 2026 checklist, to be verified before use: NOK 545,400 for positions that require a bachelor's-level qualification and NOK 624,700 for positions that require a master's-level qualification. Positions that do not require a degree fall under the rule that pay must not be poorer than normal for the occupation.

Qualification screening rules:

- A requirement written as a degree "eller tilsvarende" (or equivalent) is workable to keep verifying.
- A hard requirement with no equivalence clause gets a visible degree flag. Keep the role in the ledger with the flag, name it as friction during classification, and do not tailor or draft for it until the candidate says go for that specific role.
- Never state or imply to an employer that permit eligibility under a qualification requirement is settled when it is not. If it comes up, use the candidate's honest qualification wording plus relevant experience, and leave the decision to the employer and UDI.
- The qualification the employer states to UDI in an offer or confirmation must be one the candidate actually holds. Flag any mismatch before anything is confirmed.

## Location and language screening

Take office locations from Brønnøysund, using the registered address and sub-units, not just the city named in the posting. A company can advertise in one city and still have an office inside the candidate's range. If a commute estimate is uncertain or close to the limit, record it as "check" and let the candidate decide.

For roles beyond the commute limit, apply the candidate's remote rule from the private profile. A common workable rule is: viable only when the role is remote from the planned home base and required on-site presence is quarterly or less. Anything more frequent goes to Parked with the reason "on-site frequency", unless the candidate overrides it for a specific role.

Language screening for Norwegian requirements:

- Park, rather than drop, when a requirement section (krav or kvalifikasjoner) includes phrases such as "flytende norsk", "norsk muntlig og skriftlig", "beherske norsk", "skandinavisk språk er et krav", or "gode norskkunnskaper".
- If the same kind of phrase appears under "ønskelig" or "fordel" (desired or an advantage), note it but do not park the role for language.
- Positive signals: the posting is written in English, it says English is the working language, it mentions an international team, or it mentions relocation support. These also raise the role in shortlist sorting.

## The sweep

Run all five legs, then deduplicate against the ledger, not against the latest shortlist.

1. **finn.no**: the primary Norwegian job board. Record finn ad IDs on the ledger entry. Search the candidate's configured region for local roles, and national IT categories with home-office or remote terms for remote roles.
2. **Arbeidsplassen (NAV)**: public, municipal, and enterprise openings that may not appear on commercial boards. Use the relevant occupation categories with the configured region and national remote filters.
3. **kode24 / kodejobb.no**: developer-focused roles, including scale-up and enterprise engineering roles.
4. **LinkedIn**: research and discovery only. Do not submit anything through LinkedIn unless the candidate explicitly chooses that channel for a specific listing. Filter to a Norwegian hiring entity and the configured region or remote.
5. **Startup and remote hubs**: sources such as thehub.io, We Work Remotely, and RemoteOK, for Norwegian employers hiring remotely. Treat aggregator copies as unverified until traced to a primary source.

Deduplication:

- Default key: organisation number plus normalized title. Normalization means lowercase text with punctuation and bracketed or parenthetical suffixes removed.
- Add every source ID and URL seen to the matching entry.
- Ambiguity rule: same organisation number and same normalized title is not automatically the same job. If location, team, posting ID, or deadline differs, keep separate entries until a posting ID or URL proves they are the same vacancy. Merging two different openings is a worse error than carrying a duplicate.
- Fallback key when the organisation number is unknown: "unknown-" plus the normalized source or agency name, plus the normalized title, plus the location. Fallback-key entries merge with each other only on a shared posting ID or URL. When the real organisation number is found, update the entry's key in place and note the change in its history.

**Public-sector transparency warning.** Leg 2 surfaces municipal, county, health-trust, and state roles. Applications to Norwegian public-sector bodies are subject to the public applicant list (offentlig søkerliste, Offentleglova § 25): the applicant's name, age, current job title, and municipality can become public record unless a statutory exemption applies. Surface this to the candidate before they apply to a public-sector role, not after; it is a legitimate reason to skip an otherwise good listing.

Every sweep reports which of the five legs actually ran, which failed or were inaccessible and why, and the date. A shortlist built from a partial sweep says so at the top.

## Verification protocol

Record two separate fields for every listing. Never let one stand in for the other.

- **Employer verdict** is about the legal entity only: does this Norwegian-registered entity exist, is it in an accepted legal form, does it employ people, and is the posting actually attached to this entity?
- **Employment arrangement** is about this vacancy only: direct, staffing, employer of record, contractor, or unknown. Set it from the posting text, the employer's careers page, or a written reply, and record the source in the ledger history.

### 1. Brønnøysund lookup

Use the Enhetsregisteret API:

- Main entity: `https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`
- Search by name: `https://data.brreg.no/enhetsregisteret/api/enheter?navn={name}`
- Sub-units: `https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={orgnr}`

Fields used: `organisasjonsform.kode`, `antallAnsatte`, `naeringskode1.kode`, `konkurs`, `underAvvikling`, `underTvangsavviklingEllerTvangsopplosning`, the main entity's `forretningsadresse`, and sub-units' `beliggenhetsadresse`. If a field is missing or named differently, record what the API actually returned. Do not guess.

Sibling rule: a name search routinely returns several entities, including holding or group entities with zero employees and unrelated companies with similar names. Before recording a verdict, scan every plausible entity for the operating entity that matches the posting (name, address, industry code, website), and check its sub-units. Never record a weak verdict just because the first hit has zero employees. When more than one plausible match existed, note in the ledger history which entities were checked.

Accepted employer forms include AS, ASA, NUF (Norwegian branch of a foreign company), SA, SPA, KOMM (municipality), FYLK (county), KF and IKS (municipal enterprises), STAT, ORGL and SF (state bodies and enterprises), HF (health trust), and STI (foundation). Flag any other form for the candidate.

Employer verdicts:

- **Confirmed**: organisation number found, accepted form, employee count above zero, no bankruptcy or liquidation flag, and the posting's employer is this exact entity. This confirms the entity only. It does not confirm the vacancy's arrangement or anything about the permit.
- **Likely**: organisation number and accepted form found, but employee evidence is still zero or missing on the operating entity after the sibling check, or it is still unclear which group entity is hiring.
- **Possible**: the company hires in the region or in Europe, but no Norwegian organisation number has been found yet.
- **Unconfirmed**: recruiter or aggregator listing where the employer is unnamed or not yet traced.
- **Blocked**: bankruptcy or liquidation flag set. Drop it and record the reason.

### 2. Staffing check

Run this check when the employer places people at clients: staffing agencies, consultancies that deliver at client sites, and employers of record.

Automatic triggers, so the check does not depend on reading the ad's tone:

- The Brønnøysund industry code `naeringskode1.kode` is 78.200 (temporary agency work) or 62.200 (IT consultancy) under SN2025.
- The activity or purpose text mentions "utleie av arbeidskraft", "bemanning", or consultancy services delivered at clients, regardless of code.
- An older code appears in legacy data: SN2007 used 62.020 for IT consultancy. Treat 62.020 as a legacy trigger if it shows up in older records or screenshots. Note that 62.100 under SN2025 is computer programming, not consultancy, and is not a trigger by itself.

Then search Arbeidstilsynet's register of staffing agencies (bemanningsforetaksregisteret) for the organisation number.

- If the employer is registered, record staffing as "registered". For these employers, UDI can require a list of planned assignments confirmed by clients, and permits can run one year at a time. The permit question for these employers must ask whether a client assignment can be confirmed up front.
- If the arrangement looks like an employer of record, default the permit-support status to unlikely. Change it only on written confirmation that the provider will act as the employer on a skilled-worker application.

### 3. Permit-support status

Track this conservatively. Use written evidence only.

- **Unknown**: default for every new listing.
- **Unlikely**: the posting requires existing Norwegian work authorization or EEA citizenship, or the arrangement is an employer-of-record setup with no written exception.
- **Asked**: the permit question has been sent. Record the date, channel, and person.
- **Confirmed**: a written yes from someone who can commit, such as a recruiter, hiring manager, or HR contact. Record who, when, and the key sentence.
- **Declined**: a written no. Record who and when, then park the listing.

A vague reply such as "we can look into it" stays at asked. Only a written yes or no moves the status to confirmed or declined. If there is no reply after 7 days, draft one follow-up for the candidate to approve. After 7 more days with no reply, flag it for the candidate. Do not send further messages without approval.

## Scam and staleness detection

- Aggregator clones and generic scrapers are unverified until the role is traced to the employer's own careers page, finn.no, or Arbeidsplassen.
- Deadlines: parse the stated deadline (søknadsfrist). Past the deadline: drop. "Snarest" or "fortløpende" (as soon as possible, or rolling review): prioritize, because the role can close early. No deadline and older than about 60 days: flag as possibly stale.
- A named Norwegian recruitment firm hiring "på vegne av vår kunde" (on behalf of our client) is normal in Norway. Mark the employer verdict unconfirmed until the client is named, but do not treat anonymity alone as proof of a scam. An anonymous client through an unknown party is a red flag.
- Red flags: application funnels that redirect away from the employer's domain, requests for payment, and requests for passport details, ID numbers, or bank details before an offer.

## Ledger and shortlist

### Ledger: the source of truth

Keep one durable ledger, one record per listing, updated in place by key. A JSONL file works well if the process is partly automated. Never delete an entry. Change its status instead, so dropped, declined, and rejected roles do not resurface later as if they were new.

Useful fields:

- Key, company, organisation number, title, location.
- Source IDs and URLs.
- Deadline (søknadsfrist).
- Employer verdict and employment arrangement.
- Staffing status.
- Permit-support status and its evidence.
- Requirement flags, such as a hard degree requirement, a language blocker, or an on-site question.
- Commute estimate in minutes, or "check".
- On-site frequency.
- Technical-fit notes against the candidate's private profile.
- Status and reason.
- Contacts, with name, role, channel, and date.
- Approved artifacts, with file paths, SHA-256 hashes, and approval dates, present only while the entry is approved or later.
- History: dated notes, checks performed, and replies received.
- Last updated.

Statuses: new, shortlisted, prepared, approved, applied, interviewing, offer, rejected, parked, dropped.

Define the application stages tightly, and never report a later stage than the entry shows:

- **Prepared** means tailored materials exist and have passed review, but the candidate has not approved them yet.
- **Approved** means the candidate explicitly approved that specific application and those specific files.
- **Applied** means submission is confirmed by a confirmation screen, a confirmation email, or the application appearing in the employer's portal.

Approval attaches to exact file versions, not to a listing in the abstract. When a status becomes approved, record each approved file's path and SHA-256 hash plus the approval date. Before submitting, recompute the hashes. If any file changed after approval, the approval is void: return the entry to prepared, show the candidate the change, and get a fresh sign-off.

Ledger write protocol:

1. Before a batch of updates, back up the ledger with a timestamped filename that cannot collide with another batch the same day. State the timezone used.
2. Write changes to a temporary file and rename it over the ledger. Never edit the live file line by line.
3. After every write, validate: every record parses, the entry count matches expectations, and no key appears twice. If validation fails, restore from the backup and report the failure instead of silently retrying.
4. Re-read the ledger immediately before writing if any other session may have touched it. One writer at a time.

When a reply arrives, update the entry immediately. A new posting from an employer with an earlier rejected or declined entry gets its own entry, and appears under the previously declined section of the shortlist with the earlier outcome shown.

### Shortlist: a rendered view

The shortlist is generated from the ledger. Never edit it directly.

Sections:

1. High-priority apply list.
2. Local roles inside the configured commute limit, including any named exceptions with their on-site conditions marked.
3. National remote roles inside the configured on-site rules.
4. Previously declined employers with new postings.
5. Parked roles, always with a reason: on-site frequency, language, arrangement, declined, staffing, or other.

Sort within each section by:

1. Permit-support status: confirmed first, then asked or unknown with positive signals (English posting, English working language, international team, relocation support), then the rest.
2. Timing: processes already in flight first, then roles that can plausibly reach an interview during the candidate's stated availability windows, then rolling-review listings. Do not sort against an offer-by deadline the candidate has not set.
3. Employer verdict: confirmed, then likely, then the rest.
4. Technical and seniority fit against the private profile.

## Tailor, classify, then ask for sign-off

For each role the candidate wants to pursue:

1. Build an evidence map from the posting requirements to the candidate's source resume or profile. Tailor only from supported evidence.
2. Tailor the CV and any application letter (søknad) in the working language the employer expects.
3. Run a quality pass for inflated wording, unsupported claims, inconsistent dates, layout problems, and anything that reads as generic filler. Application documents should sound like a person wrote them, because a person is accountable for them.
4. Classify the application before asking for approval:
   - **Clean to file**: every requirement maps to evidence, there are no unresolved judgment calls, and the permit question uses the standard wording.
   - **Needs the candidate's input**: name the exact friction, one line each. Examples: an unconfirmed claim, a hard degree flag, a language flag, an on-site question, or an arrangement that is still unknown.

Portal fields are their own deliverable. Webcruiter, Jobbnorge, ReachMee, and similar portals compute seniority (ansiennitet) and qualification eligibility from their structured chronological education and work fields, not from the attached PDF CV. A tailored PDF on top of careless portal fields still scores as careless: before submission, review the structured fields field by field against the same evidence map used for the CV.

A classification is a recommendation, not permission. Nothing is submitted, sent, or posted without the candidate's explicit sign-off on that specific listing and that specific version of the materials.

## Outreach rules

Nothing goes out without the candidate's explicit sign-off on that specific message: applications, emails, LinkedIn messages, contact forms, and call scripts. Draft it, show it, wait.

Default timing: send the permit question with the application, not before it. Tailoring is usually cheap compared with waiting a week per company for an answer before even applying. Ask first only when applying is expensive, such as a long assessment, a case task, or a very long form.

Do not use the word "sponsor" or "sponsorship" with Norwegian employers. It reads as cost and legal exposure, and a contact who has never done this will default to no. Describe the actual, small ask instead. The templates live in `references/recruiter-questions.md`.

Relocation framing rules:

- Describe the move as a permanent relocation to the candidate's planned home base, in the candidate's own words from the private profile.
- Never claim a home is set up unless a lease or purchase is actually signed. Say the relocation plans are established.
- Mention availability windows only when they are real, for example a planned Norway trip when the candidate can meet in person.
- Never promise a start date that ignores permit processing.

## Pause rule

When the candidate says the search is paused, sweeps, outreach drafts, and follow-ups stop. Ledger and shortlist maintenance the candidate asks for still happens. Do not restart a sweep, nudge a contact, or revive a held draft because a deadline or a new posting appears. Surface it once, briefly, and let the candidate decide.
