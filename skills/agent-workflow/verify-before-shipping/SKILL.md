---
name: verify-before-shipping
description: "Require runnable evidence before claiming any script, skill, config or document works: a smoke-test pass over edge-case inputs, a doc-versus-behaviour cross-check, and full-output gate runs. Use before stamping anything verified, done, fixed or shipped, before reporting a delegated worker's green result as your own, and whenever a change touches code that other instructions depend on."
---

# Verify Before Shipping

Most "it works" claims that turn out wrong were never lies. They were intentions reported as results: the fix was written, so it was described as working; the tests were run, so they were described as passing; the push was attempted, so it was described as shipped. This skill closes the gap between *did the step* and *proved the outcome*.

## The core rule

A claim is a test result, not an intention. Before you say something works, is fixed, passes, or shipped, you can point at the specific run that proves it: the command, its full output, and the line in that output that carries the claim. If you cannot point, you cannot claim. Say what you actually know instead ("the patch is written, the test run is still owed") and go run it.

## When this applies

- Before marking a script, skill, config, or document done, fixed, verified, or shipped, including stamping a "Last verified" line.
- Before reporting a delegated worker's or another session's success as fact. Their green is a claim like any other; re-run the decisive gate yourself before you repeat it.
- After any change to code that documentation describes, or documentation that code is supposed to follow. The two drift apart silently; the drift is the bug factory.

## The smoke matrix

Run the thing, not a reading of the thing. For a script or tool, cover at least:

- **Happy path:** one realistic input, checked against a hand-computed expected result, not just "it printed something."
- **Empty input:** an empty file, an empty list, zero records. Empty is where unguarded indexing and missing-period bugs live.
- **Negative and zero values,** wherever numbers flow: deficits, refunds, amounts below zero. Sign handling fails more often than arithmetic.
- **Malformed input:** a ragged row, a truncated file, a missing column, an unexpected extra field. Real exports are ragged; parsers should degrade, not crash.
- **Omitted optional flags and arguments:** every default path, exercised. The default invocation is the one users actually run, and it is the one that drifts from the docs (a flag omitted behaving differently from what the text promises).
- **Ambiguous input:** values that two conventions read differently (slash dates, unit assumptions, sign conventions). Decide what the tool does with them, on purpose, and check it does that.

Write the tests as small fixture files with known answers. A fixture whose expected output you computed by hand catches what a plausible-looking run never will. Keep the fixtures; they are the regression suite when the next change lands.

## The doc-versus-behaviour cross-check

Documentation is a set of claims about the code. Check the load-bearing ones mechanically:

- **Every command shown in the docs runs as written.** Copy it out and execute it. A usage line advertising a flag the parser rejects, or omitting a subcommand that exists, is a defect, not a typo.
- **Cross-check the help.** Run `--help` (or the platform equivalent) and compare the flag list against every flag the docs and docstrings mention, in both directions.
- **Every file, path, and function the docs name exists** at the stated place with the stated name.
- **Behavioural sentences get a test,** not a nod. "Omitting X selects the primary Y" is a claim about code: run it with X omitted and watch what it selects. If the sentence and the behaviour disagree, one of them is wrong, and it is not automatically the sentence.

## Evidence discipline

- **Capture full output.** Pipe gate runs to a file and read the summary from the file. A pass claim cites the summary lines, not a vibe. Never judge a long run by its last screenful: a failure above the tail is still a failure.
- **Exit codes are evidence; silence is not.** A command that printed nothing and exited 0 did a different thing from a command that verified something.
- **A push is real when the remote says so.** After pushing, read the remote state back (the branch head, the file contents, the commit metadata that matters) and compare it against what you intended to ship. An attempted push, an accepted API call, or a local commit is not a shipped change.
- **A fix is verified by the reproduction that failed before it.** Keep the failing case from the bug report, rerun it after the patch, and show both outcomes. New tests written after the fix prove the fix reads well; the old reproduction proves it works.

## The verified stamp

When a document carries a "Last verified" line (or you are about to write one), it must say what was actually run, when, and in what environment: which inputs, which storefront or account or dataset, what the result was. "Verified" with no run behind it is worse than no stamp, because it teaches the reader to stop checking. If part of the surface could not be verified (a region that would not load, a path that needs credentials you do not have), the stamp says so, naming what is unverified rather than letting the blanket claim cover it.

## Reporting

Report results in the shape the evidence supports: what ran, what passed, what failed, what remains unrun. A partial pass reported as a full pass is the failure this skill exists to prevent. When a gate fails, the report leads with the failure and the exact case that produced it, not with the parts that went well.
