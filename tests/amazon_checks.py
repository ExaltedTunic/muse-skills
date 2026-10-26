"""W5 fix-program probes for amazon-search + price-history-check.

Run with python3 from the repository root (the Camoufox import is
stubbed below; these are unit probes and never start a browser):
    python3 tests/amazon_checks.py

Exit 0 only if every probe passes. Each probe is written against the
FIXED behaviour, so on the pre-fix tree the A01/A02/A03/A04/EXT3/D13
probes fail and after the fixes they pass.
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "skills", "shopping", "amazon-search")
PRICE_SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "skills", "shopping", "price-history-check")
SCRIPTS = os.path.join(SKILL, "scripts")

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail else ""))


def load_search_module():
    spec = importlib.util.spec_from_file_location(
        "amazon_search_under_test", os.path.join(SCRIPTS, "amazon_search.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


import types as _types
_cf = _types.ModuleType("camoufox")
_cf_sync = _types.ModuleType("camoufox.sync_api")
class _CamoufoxStub:
    def __init__(self, *a, **k):
        raise RuntimeError("camoufox stub: browsers are not available in unit tests")
_cf_sync.Camoufox = _CamoufoxStub
_cf.sync_api = _cf_sync
sys.modules.setdefault("camoufox", _cf)
sys.modules.setdefault("camoufox.sync_api", _cf_sync)

mod = load_search_module()

# ---------------- A01: marketplace validation ----------------
ACCEPT = {
    "amazon.ca": ("ca", "amazon.ca", "CAD"),
    "amazon.com": ("us", "amazon.com", "USD"),
    "amazon.co.uk": ("uk", "amazon.co.uk", "GBP"),
    "amazon.de": ("de", "amazon.de", "EUR"),
    "amazon.com.au": ("au", "amazon.com.au", "AUD"),
    "www.amazon.ca": ("ca", "amazon.ca", "CAD"),
    "AMAZON.CA": ("ca", "amazon.ca", "CAD"),
    "ca": ("ca", "amazon.ca", "CAD"),
    "uk": ("uk", "amazon.co.uk", "GBP"),
}
REJECT = [
    "amazon.example.invalid",
    "amazon.ca.evil.com",
    "amazon.ca:8443",
    "amazon.ca:8443/x",
    "https://www.amazon.de/path?q=1",
    "https://amazon.ca",
    "amazon.ca/path",
    "user" + "@" + "amazon.ca",
    "amazon.ca.",
    "notamazon.ca",
]
for raw, expected in ACCEPT.items():
    try:
        got = mod.resolve_marketplace(raw)
        check(f"A01 accept {raw!r}", got == expected, f"got={got} want={expected}")
    except SystemExit as e:
        check(f"A01 accept {raw!r}", False, f"SystemExit: {e}")
for raw in REJECT:
    try:
        got = mod.resolve_marketplace(raw)
        check(f"A01 reject {raw!r}", False, f"accepted as {got}")
    except SystemExit:
        check(f"A01 reject {raw!r}", True)

# ---------------- A03: unit-price suffix currencies ----------------
class FakeResult:
    def __init__(self, text):
        self._text = text

    def inner_text(self):
        return self._text


UNIT_CASES = [
    ("($2.99 /100g)", "$2.99 /100g"),          # prefix $, existing
    ("(£1.50 /100g)", "£1.50 /100g"),          # prefix pound, existing
    ("(€2,99 /100g)", "€2,99 /100g"),          # prefix euro, existing
    ("(2,99 €/100g)", "2,99 €/100g"),          # suffix euro, A03
    ("2,99 €/100g", "2,99 €/100g"),            # suffix euro, no parens, A03
    ("(2.99$ /100g)", "2.99$ /100g"),          # suffix $, A03 bonus gap
    ("(89,51 EUR/kg)", "89,51 EUR/kg"),        # suffix code, A03
    ("29,99 €", None),                          # plain price, not a unit price
    ("free shipping on orders", None),          # no price at all
]
for text, expected in UNIT_CASES:
    got = mod._unit_price(FakeResult(text))
    check(f"A03 unit_price {text!r}", got == expected, f"got={got!r} want={expected!r}")

# _PRICE_LINE: $-suffix support (same one-token change, applied to both)
m = mod._PRICE_LINE.search("2.99$")
check("A03 price_line $-suffix", bool(m) and m.group(0) == "2.99$",
      f"got={m.group(0) if m else None!r}")
m = mod._PRICE_LINE.search("29,99 €")
check("A03 price_line euro-suffix unchanged", bool(m) and m.group(0) == "29,99 €",
      f"got={m.group(0) if m else None!r}")

# ---------------- A02: empty-page classification ----------------
class FakePage:
    def __init__(self, html):
        self._html = html

    def goto(self, url, **kw):
        pass

    def wait_for_selector(self, sel, **kw):
        raise TimeoutError("no results")

    def query_selector_all(self, sel):
        return []

    def query_selector(self, sel):
        return None

    def content(self):
        return self._html


class FakeContext:
    def __init__(self, page):
        self._page = page

    def new_page(self):
        return self._page


class FakeCamoufox:
    page = None

    def __init__(self, **kw):
        pass

    def __enter__(self):
        return FakeContext(FakeCamoufox.page)

    def __exit__(self, *a):
        return False


def run_search(html):
    FakeCamoufox.page = FakePage(html)
    orig = mod.Camoufox
    mod.Camoufox = FakeCamoufox
    try:
        return ("ok", mod.search("anything", 10, "amazon.ca", None))
    except RuntimeError as e:
        return ("error", str(e))
    finally:
        mod.Camoufox = orig


# Block page: behaviour must be unchanged (same error).
kind, val = run_search("<html><body>Enter the characters you see below</body></html>")
check("A02 block page still block error",
      kind == "error" and val == "Amazon served a block/captcha page", f"{kind}: {val}")

# Genuine no-results page: must return [].
kind, val = run_search(
    "<html><body><h1>No results for \"zzqqx\"</h1>"
    "<p>Try checking your spelling or use more general terms</p></body></html>")
check("A02 genuine no-results returns []", kind == "ok" and val == [], f"{kind}: {val}")

# Unknown page: must raise the distinct unrecognized-page error, not [].
kind, val = run_search("<html><body><h1>Something went wrong</h1></body></html>")
check("A02 unknown page raises unrecognized error",
      kind == "error" and "unrecognized Amazon page" in val, f"{kind}: {val}")

# ---------------- A04: smoke_test assertions (stubbed browser) ----------------
STUB = '''
import os
class _Page:
    def goto(self, url, **kw): pass
    def title(self):
        return "Example Domain" if os.environ.get("SMOKE_MODE") == "good" else "Wrong Title"
    def evaluate(self, expr):
        good = os.environ.get("SMOKE_MODE") == "good"
        if "userAgent" in expr:
            return "Mozilla/5.0 (Windows NT 10.0; rv:156.0) Gecko/20100101 Firefox/156.0" if good else "Mozilla/5.0 Chrome/120.0"
        if "webdriver" in expr:
            return False if good else True
        if "platform" in expr:
            return "Win32" if good else ""
        return None
class _Ctx:
    def new_page(self): return _Page()
class Camoufox:
    def __init__(self, **kw): pass
    def __enter__(self): return _Ctx()
    def __exit__(self, *a): return False
'''


def run_smoke(mode):
    with tempfile.TemporaryDirectory() as td:
        pkg = os.path.join(td, "camoufox")
        os.makedirs(pkg)
        with open(os.path.join(pkg, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(pkg, "sync_api.py"), "w") as f:
            f.write(STUB)
        env = dict(os.environ, SMOKE_MODE=mode, PYTHONPATH=td)
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "smoke_test.py")],
            capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, (r.stdout + r.stderr)


rc, out = run_smoke("good")
check("A04 smoke good values exit 0", rc == 0, f"rc={rc} out={out.strip()[:120]!r}")
rc, out = run_smoke("bad")
check("A04 smoke bad values exit 1", rc == 1, f"rc={rc} out={out.strip()[:120]!r}")

# ---------------- EXT-3: browser build record in SKILL.md ----------------
with open(os.path.join(SKILL, "SKILL.md")) as f:
    skill_text = f.read()
check("EXT3 SKILL.md names a browser-build recording command",
      ("camoufox version" in skill_text or "camoufox active" in skill_text
       or "installed_verstr" in skill_text))
check("EXT3 SKILL.md says refetch/reinstall invalidates profile seeding",
      bool(re.search(r"(reinstall|refetch|re-fetch)[^.]{0,200}make_profile", skill_text, re.I | re.S))
      or bool(re.search(r"make_profile[^.]{0,200}(reinstall|refetch|re-fetch)", skill_text, re.I | re.S)))
with open(os.path.join(SCRIPTS, "smoke_test.py")) as f:
    smoke_src = f.read()
check("EXT3 smoke_test prints the browser build (not asserted)",
      "installed_verstr" in smoke_src or "camoufox" in smoke_src and "browser" in smoke_src.lower())

# ---------------- D13: price-history evidence handoff ----------------
with open(os.path.join(PRICE_SKILL, "SKILL.md")) as f:
    price_text = f.read()
for needle in ["seller", "fulfillment", "condition", "variant"]:
    check(f"D13 mentions {needle}", needle in price_text.lower())
check("D13 product-page verification is REQUIRED when identity unknown",
      bool(re.search(r"product-page verification[^.]{0,120}required|required[^.]{0,120}product-page verification",
                     price_text, re.I | re.S)))
check("D13 records comparison track + source URLs + last-observed time",
      "comparison track" in price_text.lower() and "last-observed" in price_text.lower())
check("D13 unknown/approximate verdict when evidence unobtainable",
      bool(re.search(r"unknown / approximate|unknown or approximate", price_text, re.I)))

print()
failed = [r for r in RESULTS if not r[1]]
print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
sys.exit(1 if failed else 0)
