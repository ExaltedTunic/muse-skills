"""Seed (or refresh) the Camoufox profile with the current egress proxy CA.

The egress proxy CA rotates when the runtime redeploys, which silently breaks
TLS in the browser (SEC_ERROR_UNKNOWN). Re-running this replaces the stored
HatchEgressCA with the current one from /run/hatch/egress-tls/.
"""
import os
import subprocess
import sys

profile = os.path.expanduser("~/workspace/tools/camoufox/profile")
os.makedirs(profile, exist_ok=True)  # certutil -N fails on a missing dir
ca = "/run/hatch/egress-tls/hatch-egress-ca.pem"
if sys.platform != "linux" or not os.path.exists(ca):
    # Off a Muse VM there is no Hatch egress proxy CA to seed (and on
    # Windows certutil is a different tool entirely). Skip, do not fail.
    print("note: skipping Hatch proxy CA injection (non-container environment)")
    sys.exit(0)
db = f"sql:{profile}"

def run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=30)


if not os.path.exists(os.path.join(profile, "cert9.db")):
    r = run(["certutil", "-N", "-d", db, "--empty-password"])
    print("init:", r.returncode, r.stderr.strip()[:200])
r = run(["certutil", "-D", "-n", "HatchEgressCA", "-d", db])
print("delete old:", r.returncode)
r = run(["certutil", "-A", "-n", "HatchEgressCA", "-t", "CT,C,c",
         "-i", ca, "-d", db])
print("add current:", r.returncode, r.stderr.strip()[:200])
if r.returncode != 0:
    # Without the CA seeded, every later search fails with a TLS error
    # that looks like a network problem. Fail here, at the cause.
    print("error: certutil could not add the CA; profile seeding failed",
          file=sys.stderr)
    sys.exit(1)
r = run(["certutil", "-L", "-d", db])
print(r.stdout)
