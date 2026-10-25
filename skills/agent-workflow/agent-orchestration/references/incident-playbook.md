# Incident Playbook

Failure modes observed in real multi-agent programs, each with the signal that
betrays it and the standing fix. None of these are hypothetical; each one cost
real time before it had a name.

## The false green

**What happens:** a worker reports gates passing. The run actually failed, or
covered less than claimed. Variants: the verdict was read from the tail of the
output (failures sat above it), a summary of the run was trusted instead of
the run's own log, or a background completion notice was mistaken for the
result.

**Signal:** the claim cites no log file, or the numbers in the claim do not
reconcile with the base tree's numbers plus the branch's own deltas.

**Fix:** gate output is captured in full to a file, and the claim quotes the
summary lines from that file. The integrator re-runs the decisive gates on
the merged tree regardless. When you catch a false green, correct the record
in the same report that carries the fix; do not let the original claim stand
anywhere downstream.

## The phantom push

**What happens:** a push is reported complete. It was rejected (commonly by
a pre-push hook running the gate battery, which takes minutes and fails
quietly in the background) or never left the machine.

**Signal:** the remote ref does not show the branch at the expected commit.

**Fix:** a push is verified by reading the remote state back and comparing
the commit. Local success messages, hook output, and exit codes from a
backgrounded push are not the remote's word.

## Cross-branch phantom orphans

**What happens:** parallel branches share an external store (an object store,
a CDN bucket, a generated-asset registry). Each branch's validator inventories
the whole store against its own manifest, so every branch flags its siblings'
new assets as orphans. A worker may "fix" this by deleting assets that a
sibling branch is about to reference.

**Signal:** validation fails only on orphan/extra entries; the missing and
stale counts are zero; every flagged path belongs to a sibling's slice.

**Fix:** brief all waves on the shared store in advance. During the wave, the
verdict is read split: missing and stale are the branch's real signals;
orphans belonging to sibling slices are expected and are never deleted. The
store-level verdict (no orphans at all) can only be judged after every
branch's manifest has merged.

## Ephemeral scratch space

**What happens:** helper scripts, staged credentials, and gate tooling kept in
the machine's temp directory vanish when the runtime restarts mid-program.
The work is intact; the tooling is gone, and the loss is discovered at the
worst moment (usually mid-merge).

**Signal:** a script or staged file that existed an hour ago does not exist.

**Fix:** anything the program needs twice lives in durable storage: the goal
or project workspace, not temp. Temp is for single-use scratch only. Recreate
lost tooling without drama and move the durable copy into place the same day.

## The reaped background run

**What happens:** a long gate suite or generation job runs in the background
and the session reaper kills it mid-run. Worse variant: the process group
survives a reported termination, and a duplicate gets launched on top of it.

**Signal:** the run's log stops mid-suite with no summary; or two writers are
producing the same outputs.

**Fix:** verify completion from the log file on disk, never from the
runner's status. For very long suites, shard the run (thirds of a test suite,
per-module generation) so each shard completes and logs independently, then
assemble the verdict from the shard logs. Before relaunching anything that
"was terminated," check whether the original process is actually alive.

## Non-deterministic regeneration churn

**What happens:** a generator re-synthesizes every artifact in a set when
asked to add a few, producing byte-different versions of artifacts nobody
meant to touch. The diff fills with churn, review becomes impossible, and
downstream stores accumulate orphans.

**Signal:** a small content change produces a huge artifact diff.

**Fix:** generation is additive where the tooling allows (targeted runs for
the missing keys only). Where it does not, revert the churned tracked
artifacts after the run and keep only the genuinely new ones plus the
manifest. Never commit a regeneration sweep as if it were a change.

## Duplicate concepts across branches

**What happens:** two workers independently add the same concept (a term, a
registry entry, a helper) under different ids. Both branches are correct
alone; merged, the system teaches or stores the concept twice, and a
uniqueness invariant may break in ways neither branch's gates could see.

**Signal:** merge conflicts cluster in the shared registry, or a merged-tree
gate reports a duplicate neither branch reported.

**Fix:** at integration, pick one canonical id, rewrite the other branch's
references to it, remove the duplicate entry. Note the dedupe in the closeout
report with both ids named, so the next wave-set can pre-assign ids for
predictable collisions.

## The honest leftover

**What happens:** a worker leaves a visible defect in its own slice (a
diagnostic it chose not to close, a check it judged out of scope) while its
siblings closed the same class of issue in theirs. The branch is green; the
program is uneven.

**Signal:** the merged diagnostics show findings concentrated in one slice.

**Fix:** this is integrator work. Close the gap at integration (it is usually
mechanical once found), or record it as a named residual with a reason in the
closeout report. Never let a wave's local judgement silently set the
program's quality floor.
