---
name: scrub-before-sharing
description: Prepare a file, folder, skill or connector bundle for someone outside the household by stripping the user's private data from every file in it and verifying the clean copy before it is shared.
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

- Run a text search over the finished share copy (the bundled `scripts/scrub_scan.py`, or your platform's file-search tool) for each value and identifier class you removed, and fix any hit before the copy goes anywhere.

- Report the verification as counts the user can check, naming what was removed or replaced and stating that the search found zero remaining hits.

- Present that exclusion report before any share link, archive or message goes out, and let the user confirm the copy rather than discovering a leak after it was sent.

- Keep the live original untouched during the scrub, and say plainly if a value reached a recipient before you caught it so the user can decide what to do next.

## Publishing to a public repo

- Build the repo from share copies only. Never make a live working folder public in place, and never push first and scrub later: history keeps everything.

- Handle identity before the first commit. When the user does not want their name attached, publish under a neutral organization name or a pseudonymous account, and set the repo-local git author to a pen name with the host's noreply email address. Author names and emails are permanent in commit history, so a real-name identity in the first commit cannot be scrubbed afterward without rewriting history.

- Third-party material gets a link, not a mirror. Only redistribute third-party work when its license clearly allows it, with attribution and the license text traveling with the copy.

- Run the final sweep on the exact tree being pushed, not on a copy scrubbed earlier. Check the ignore rules cover caches, local configs and generated files, and read the first commit's author line before the push happens.

## Available connectors

- If your agent platform has a connector or skill directory, search it to find related connectors and skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Send less when the recipient only needs the method, such as a single clean skill file instead of a whole working folder with its data and defaults.

- Ask the user to name anything that may stay in, such as a public project name, instead of guessing which private details are safe to keep.

- Rebuild the share copy from the live folder each time it is shared again, because a copy scrubbed last month can drift back toward the live files.
