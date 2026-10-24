"""Anonymous Amazon.ca search via Camoufox. Search-only: no login, no cookies
beyond the persistent profile's site state, no cart, no checkout.

Usage:
    venv/bin/python amazon_search.py "green christmas pajamas" [--limit 10] [--json]

Prints title, price (CAD as shown), rating and product URL per result.
Exits non-zero with a clear message if Amazon serves a block/captcha page.
"""
import argparse
import json
import os
import sys
import urllib.parse

os.environ.setdefault("TMPDIR", os.path.expanduser("~/workspace/tools/camoufox/tmp"))

from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/workspace/tools/camoufox/profile")
BLOCK_MARKERS = ["captcha", "robot check", "type the characters",
                 "enter the characters you see"]


def search(query: str, limit: int) -> list[dict]:
    url = "https://www.amazon.ca/s?k=" + urllib.parse.quote_plus(query)
    with Camoufox(headless=True, persistent_context=True,
                  user_data_dir=PROFILE) as context:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)
        html = page.content().lower()
        if any(m in html for m in BLOCK_MARKERS):
            raise RuntimeError("Amazon served a block/captcha page")
        out = []
        for r in page.query_selector_all('[data-component-type="s-search-result"]')[:limit]:
            t = r.query_selector("h2 span")
            p = r.query_selector(".a-price .a-offscreen")
            a = r.query_selector("a.a-link-normal[href*='/dp/']")
            rating = r.query_selector(".a-icon-alt")
            href = a.get_attribute("href") if a else None
            asin = r.get_attribute("data-asin")
            if asin:
                url = f"https://www.amazon.ca/dp/{asin}"
            elif href and href.startswith("/"):
                url = "https://www.amazon.ca" + href
            else:
                url = href
            out.append({
                "title": t.inner_text().strip() if t else None,
                "price": p.inner_text().strip() if p else None,
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
    args = ap.parse_args()
    try:
        results = search(args.query, args.limit)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            tag = " [sponsored]" if r.get("sponsored") else ""
            print(f"- {r['price'] or '(no price)'} | {r['rating'] or ''} | {r['title']}{tag}")
            if r["url"]:
                print(f"  {r['url']}")
    print(f"({len(results)} results)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
