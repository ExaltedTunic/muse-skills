import os
import sys

from camoufox.sync_api import Camoufox

profile = os.path.expanduser("~/workspace/tools/camoufox/profile")

# The package pin (camoufox==0.5.8) does not identify the downloaded
# browser build. Print it (not asserted: the build legitimately changes
# on refetch) so a setup log records which browser actually ran.
try:
    from camoufox.pkgman import installed_verstr

    print("browser:", installed_verstr())
except Exception as e:
    print("browser: (unavailable)", e)

failures = []

with Camoufox(headless=True, persistent_context=True, user_data_dir=profile) as context:
    page = context.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded", timeout=60000)
    title = page.title()
    user_agent = page.evaluate("navigator.userAgent")
    webdriver = page.evaluate("navigator.webdriver")
    platform = page.evaluate("navigator.platform")
    print("title:", title)
    print("userAgent:", user_agent)
    print("webdriver:", webdriver)
    print("platform:", platform)

    if "Example" not in (title or ""):
        failures.append(f"title does not contain 'Example': {title!r}")
    if not user_agent or "Firefox" not in user_agent:
        failures.append(f"user agent is not the spoofed Firefox UA: {user_agent!r}")
    if webdriver is not False:
        failures.append(f"navigator.webdriver is not False: {webdriver!r}")
    if not platform:
        failures.append(f"navigator.platform is empty: {platform!r}")

if failures:
    for failure in failures:
        print("FAIL:", failure, file=sys.stderr)
    sys.exit(1)
print("smoke test passed")
