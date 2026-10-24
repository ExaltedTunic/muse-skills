"""Seed (or refresh) the Camoufox profile with the current egress proxy CA.

The egress proxy CA rotates when the runtime redeploys, which silently breaks
TLS in the browser (SEC_ERROR_UNKNOWN). Re-running this replaces the stored
HatchEgressCA with the current one from /run/hatch/egress-tls/.
"""
import os
import subprocess

profile = os.path.expanduser("~/workspace/tools/camoufox/profile")
os.makedirs(profile, exist_ok=True)  # certutil -N fails on a missing dir
ca = "/run/hatch/egress-tls/hatch-egress-ca.pem"
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
r = run(["certutil", "-L", "-d", db])
print(r.stdout)
