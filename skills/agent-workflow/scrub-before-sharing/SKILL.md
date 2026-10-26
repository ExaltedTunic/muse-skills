---
name: scrub-before-sharing
description: Prepare a file, folder, skill or connector bundle for someone outside the household by stripping the user's private data from every file in it and verifying the clean copy before it is shared. Use when a bundle, document, skill or repo is about to be handed to someone outside the household, sent for an outside review, or published.
---

# Scrub Before Sharing

## Build a share copy, never share the live folder

- Copy the file or folder into a separate share copy and scrub only that copy, so the live original keeps working with the user's own settings.

- Treat a request to send a working tool to another person as a method transfer by default, and leave the user's personal facts, figures and history out unless the user explicitly opts a specific item in.

- Give the recipient a self contained copy with its own setup notes, so they never need the user's live folder, accounts or defaults to use it.

## Sweep every file, not just the prose

- Search the whole share copy, including scripts, code defaults, config files, examples, comments, data files and archives inside it, because private values hide in defaults and helpers as easily as in documents.

- Remove or replace names, home and work addresses, postal codes, phone numbers, email addresses, account and case identifiers, balances and personal figures, tokens and keys, and stories about the user or their family.

- Replace a personal default value with a neutral placeholder or a required input with no default, and say in the setup notes what the recipient must supply themselves.

- Check any outside review or second opinion copy the same way before it leaves, since a scrubbed main document does not clean an attachment or a bundled script.

## Verify the clean copy and report the exclusions

- Verify the finished share copy before it goes anywhere: run the bundled `scripts/scrub_scan.py` over it as a mechanical first pass (identifier shapes: emails, phone numbers, postal and ZIP codes, home paths, IP addresses, key-shaped tokens), then run `muse.exec` text searches for each specific value you removed, and fix any hit.

- Make the extra patterns personal, every time: pass the user's own identifiers to the scanner via `--extra-regex` as a matter of routine — their name, handles, employer, and city, taken from their profile. The built-in patterns only catch shapes; the most likely leftover is the user's own name sitting in a default, a comment, or an example, and no generic pattern will catch it.

- Report the verification as counts the user can check, naming what was removed or replaced and stating that the search found zero remaining hits.

- Present that exclusion report before any share link, archive or message goes out, and let the user confirm the copy rather than discovering a leak after it was sent.

- Keep the live original untouched during the scrub, and say plainly if a value reached a recipient before you caught it so the user can decide what to do next.

## Scanner verdicts, coverage and the allowlist

The bundled scanner (`scripts/scrub_scan.py`) reports findings as `path:line:label` plus a short SHA-256 fingerprint of the matched text. It never prints the matched text itself: a scan meant to prevent disclosure must not become another copy of the secret in tool output or logs. Use the fingerprint to confirm a value you already know; read the file directly to see the hit.

Exit codes:

- **0, clean**: everything enumerated was inspected and nothing was flagged.
- **1, findings**: at least one pattern matched in inspected content.
- **2, usage error**: the target does not exist.
- **3, incomplete**: some content could not be inspected (undecodable or unreadable files, inaccessible directories, corrupt archives, unreadable archive members). The affected paths are listed. An exit 3 is not a clean bill: inspect or disposition the named content before the copy goes out. Exit 3 takes precedence over exit 1 when both apply.

Every run prints a coverage line (enumerated / scanned / archives with members inspected / excluded / unreadable). A zero-hit result is only meaningful when the coverage accounts for every file in the tree. Archives (`.zip`, `.tar`, `.tar.gz`/`.tgz`) are opened and their text members scanned with the same patterns. The scanner's own source is excluded explicitly and reported as excluded ("scanner source, verify separately") because it legitimately contains the pattern shapes.

Deliberately non-text artifacts (images, fonts, compiled blobs) that cannot be text-scanned can be excluded deliberately instead of failing the run: put a `.scrub-allowlist` file in the scanned root, one glob per line (for example `*.png`), matched against file name and root-relative path. Allowlisted files are counted and named in the output, and do not trigger the incomplete verdict. Allowlisting is a visible decision, not a silent skip: report every allowlisted path in the exclusion report.

## Publishing to a public repo

- Build the repo from share copies only. Never make a live working folder public in place, and never push first and scrub later: history keeps everything.

- Handle identity before the first commit. When the user does not want their name attached, publish under a neutral organization name or a pseudonymous account, and set the repo-local git author to a pen name with the host's noreply email address. Author names and emails are permanent in commit history, so a real-name identity in the first commit cannot be scrubbed afterward without rewriting history.

- Third-party material gets a link, not a mirror. Only redistribute third-party work when its license clearly allows it, with attribution and the license text traveling with the copy.

- Run the final sweep on the exact tree being pushed, not on a copy scrubbed earlier. Check the ignore rules cover caches, local configs and generated files, and read the first commit's author line before the push happens.

## Alternatives for better results

- Send less when the recipient only needs the method, such as a single clean skill file instead of a whole working folder with its data and defaults.

- Ask the user to name anything that may stay in, such as a public project name, instead of guessing which private details are safe to keep.

- Rebuild the share copy from the live folder each time it is shared again, because a copy scrubbed last month can drift back toward the live files.
