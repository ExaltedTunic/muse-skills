"""Anonymous Amazon search via Camoufox, for any regional storefront.
Search-only: no login, no cookies beyond the persistent profile's site
state, no cart, no checkout.

Usage:
    venv/bin/python amazon_search.py "green christmas pajamas" [--limit 10] [--json]
    venv/bin/python amazon_search.py "whey protein" --marketplace us
    venv/bin/python amazon_search.py "whey protein" --domain amazon.co.uk

Marketplace resolution, first match wins: --marketplace/--domain flag,
AMAZON_MARKETPLACE environment variable, then the default in DEFAULT_MARKETPLACE
below. A marketplace may be a code from MARKETPLACES (ca, us, uk, de, ...)
or a bare Amazon domain (amazon.com, amazon.com.au, ...).

Prints title, price (in the storefront's currency, as shown), rating and
product URL per result, and names the storefront searched.
Exits non-zero with a clear message if Amazon serves a block/captcha page.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse

os.environ.setdefault("TMPDIR", os.path.expanduser("~/workspace/tools/camoufox/tmp"))
os.makedirs(os.environ["TMPDIR"], exist_ok=True)

from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/workspace/tools/camoufox/profile")
BLOCK_MARKERS = ["captcha", "robot check", "type the characters",
                 "enter the characters you see",
                 # amazon.com's explicit AI-agent block page (seen 2026-10-24:
                 # "Continued access by an unauthorized AI agent violates
                 # Amazon's Conditions of Use")
                 "unauthorized ai agent"]

# The storefront used when neither a flag nor AMAZON_MARKETPLACE is set.
# Change this one line (or set the env var) to make another region your default.
DEFAULT_MARKETPLACE = "ca"

# code -> (domain, currency). Codes are the usual country codes, with uk for
# the United Kingdom storefront. Prices are always passed through as shown on
# the page; the currency is reported so callers do not have to guess it.
MARKETPLACES = {
    "ca": ("amazon.ca", "CAD"),
    "us": ("amazon.com", "USD"),
    "uk": ("amazon.co.uk", "GBP"),
    "gb": ("amazon.co.uk", "GBP"),
    "de": ("amazon.de", "EUR"),
    "fr": ("amazon.fr", "EUR"),
    "it": ("amazon.it", "EUR"),
    "es": ("amazon.es", "EUR"),
    "nl": ("amazon.nl", "EUR"),
    "be": ("amazon.com.be", "EUR"),
    "ie": ("amazon.ie", "EUR"),
    "se": ("amazon.se", "SEK"),
    "pl": ("amazon.pl", "PLN"),
    "au": ("amazon.com.au", "AUD"),
    "jp": ("amazon.co.jp", "JPY"),
    "in": ("amazon.in", "INR"),
    "mx": ("amazon.com.mx", "MXN"),
    "br": ("amazon.com.br", "BRL"),
    "sg": ("amazon.sg", "SGD"),
    "ae": ("amazon.ae", "AED"),
    "sa": ("amazon.sa", "SAR"),
    "eg": ("amazon.eg", "EGP"),
    "tr": ("amazon.com.tr", "TRY"),
    "za": ("amazon.co.za", "ZAR"),
    "cn": ("amazon.cn", "CNY"),
}

# Reverse lookup for when a bare domain is given instead of a code.
_DOMAIN_TO_CODE = {}
for _code, (_domain, _currency) in MARKETPLACES.items():
    _DOMAIN_TO_CODE.setdefault(_domain, _code)


def resolve_marketplace(value: str) -> tuple[str, str, str | None]:
    """Return (code, domain, currency) for a code or bare domain."""
    v = value.strip().lower().removeprefix("https://").removeprefix("http://")
    v = v.removeprefix("www.").rstrip("/")
    if v in MARKETPLACES:
        domain, currency = MARKETPLACES[v]
        return v, domain, currency
    if v.startswith("amazon."):
        return _DOMAIN_TO_CODE.get(v, v), v, dict(
            (d, c) for d, c in MARKETPLACES.values()).get(v)
    raise SystemExit(
        f"error: unknown marketplace {value!r}. Use a code "
        f"({', '.join(sorted(set(MARKETPLACES)))}), a bare Amazon domain "
        "like amazon.com.au, or --domain.")


_PRICE_LINE = re.compile(
    r"(?:€|£|\$|EUR|USD|GBP|CAD|AUD|JPY|SEK|PLN)\s?[\d.,]+"
    r"|[\d.,]+\s?(?:€|£|EUR|USD|GBP|CAD|AUD|SEK|PLN)")


def _price_text(r) -> str | None:
    """Price as shown, across storefront layouts. The .a-offscreen span
    is the usual carrier, but some storefronts (amazon.de in testing)
    serve results without it, so fall back to composing the visible
    .a-price parts, then to the first currency-shaped line of the
    result's visible text."""
    off = r.query_selector(".a-price .a-offscreen")
    if off:
        text = off.inner_text().strip()
        if text:
            return text
    price = r.query_selector(".a-price")
    if price:
        whole = price.query_selector(".a-price-whole")
        if whole:
            frac = price.query_selector(".a-price-fraction")
            sym = price.query_selector(".a-price-symbol")
            text = whole.inner_text().strip()
            if frac:
                text += frac.inner_text().strip()
            if sym:
                symbol = sym.inner_text().strip()
                if symbol:
                    text = f"{text} {symbol}"
            if text:
                return text
        text = " ".join(price.inner_text().split())
        if text:
            return text
    for line in r.inner_text().splitlines():
        match = _PRICE_LINE.search(line.strip())
        if match:
            return match.group(0).strip()
    return None


def search(query: str, limit: int, domain: str,
           language: str | None) -> list[dict]:
    base = f"https://www.{domain}"
    url = base + "/s?k=" + urllib.parse.quote_plus(query)
    if language:
        url += "&language=" + urllib.parse.quote_plus(language)
    with Camoufox(headless=True, persistent_context=True,
                  user_data_dir=PROFILE) as context:
        page = context.new_page()
        load_timed_out = False
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
        except Exception as e:
            # Several storefronts intermittently stall navigation from
            # some networks while still rendering results; only give up
            # when the DOM has nothing either (checked below).
            if "timeout" not in str(e).lower():
                raise
            load_timed_out = True
        page.wait_for_timeout(4000)
        nodes = page.query_selector_all('[data-component-type="s-search-result"]')
        if not nodes:
            # Decide block vs genuine no-results only when there is nothing
            # to return: scanning raw HTML for marker words while results
            # exist can false-trigger on page text, and a real block page
            # has no result nodes at all.
            html = page.content().lower()
            captcha_form = page.query_selector(
                "form[action*='captcha'], #captchacharacters")
            if captcha_form or any(m in html for m in BLOCK_MARKERS):
                raise RuntimeError("Amazon served a block/captcha page")
            if load_timed_out:
                raise RuntimeError(
                    "Amazon page load timed out with no results rendered")
            return []
        out = []
        for r in nodes[:limit]:
            t = r.query_selector("h2 span")
            a = r.query_selector("a.a-link-normal[href*='/dp/']")
            rating = r.query_selector(".a-icon-alt")
            href = a.get_attribute("href") if a else None
            asin = r.get_attribute("data-asin")
            if asin:
                url = f"{base}/dp/{asin}"
            elif href and href.startswith("/"):
                url = base + href
            else:
                url = href
            out.append({
                "title": t.inner_text().strip() if t else None,
                "price": _price_text(r),
                "rating": rating.inner_text().strip() if rating else None,
                "sponsored": r.query_selector(".puis-sponsored-label-text") is not None,
                "url": url,
            })
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--marketplace", "--region", dest="marketplace",
                    default=None,
                    help="Storefront code (ca, us, uk, de, au, jp, ...) or "
                         "bare domain. Default: AMAZON_MARKETPLACE env var, "
                         "else the script's DEFAULT_MARKETPLACE.")
    ap.add_argument("--domain", dest="domain", default=None,
                    help="Alias for --marketplace, for when a full domain "
                         "reads clearer than a code.")
    ap.add_argument("--language", dest="language", default=None,
                    help="Optional Amazon language code, e.g. en_US, de_DE. "
                         "Passed through to the storefront as-is.")
    args = ap.parse_args()
    chosen = (args.domain or args.marketplace
              or os.environ.get("AMAZON_MARKETPLACE") or DEFAULT_MARKETPLACE)
    code, domain, currency = resolve_marketplace(chosen)
    try:
        results = search(args.query, args.limit, domain, args.language)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for r in results:
        r["marketplace"] = code
        r["domain"] = domain
        r["currency"] = currency
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            tag = " [sponsored]" if r.get("sponsored") else ""
            print(f"- {r['price'] or '(no price)'} | {r['rating'] or ''} | {r['title']}{tag}")
            if r["url"]:
                print(f"  {r['url']}")
    cur = f" {currency}" if currency else ""
    print(f"({len(results)} results from {domain}{cur})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
