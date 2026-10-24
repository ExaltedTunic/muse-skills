import os
from camoufox.sync_api import Camoufox

profile = os.path.expanduser("~/workspace/tools/camoufox/profile")

with Camoufox(headless=True, persistent_context=True, user_data_dir=profile) as context:
    page = context.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded", timeout=60000)
    print("title:", page.title())
    print("userAgent:", page.evaluate("navigator.userAgent"))
    print("webdriver:", page.evaluate("navigator.webdriver"))
    print("platform:", page.evaluate("navigator.platform"))
