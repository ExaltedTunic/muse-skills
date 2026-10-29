#!/usr/bin/env python3
"""Flipp deal lookup CLI (unofficial Wishabi backend, no auth required).

Commands:
  search QUERY   keyword search across current flyers near a postal code
  flyers         list current flyers near a postal code
  flyer ID       dump the items in one flyer
  scan QUERY     bounded scan of full flyer contents (comprehensive fallback)

Postal code resolution: --postal flag, else the FLIPP_POSTAL_CODE
environment variable. There is deliberately no built-in default: a deal
checker that silently searches the wrong town is worse than one that
stops and says so. If neither is set, the command exits 2.

Output contract: on success, results go to stdout (text, or JSON with
--json) and the exit code is 0. On failure, a JSON error object goes to
stderr and the exit code is nonzero: 2 for bad arguments, 1 for network,
HTTP, rate-limit, JSON, or schema failures. Upstream schema drift is a
schema_error, never a silent empty result.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://backflipp.wishabi.com/flipp"
HEADERS = {"User-Agent": "Mozilla/5.0 (personal flyer deal checker)"}
POSTAL_RE = re.compile(r"^[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d$")
LOCALE_RE = re.compile(r"^[a-z]{2}-[a-z]{2}$")
SEARCH_CAP = 150
LB_TO_KG = 2.20462


class FlippError(Exception):
    """Structured failure: stable code, human message, process exit code."""

    def __init__(self, code, message, exit_code=1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def bad_args(message):
    return FlippError("bad_args", message, exit_code=2)


# ---------------------------------------------------------------- HTTP layer

def get(path, params, retries=1):
    """GET one API path and return the decoded top-level JSON object.

    Retries once on a transient network error. Every failure mode raises
    FlippError; nothing returns None or a partial result.
    """
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise FlippError(
                    "rate_limited",
                    "Flipp API rate limit hit (HTTP 429); wait and retry.",
                )
            raise FlippError(
                "http_error", f"Flipp API returned HTTP {e.code} for {path}."
            )
        except urllib.error.URLError as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.0)
                continue
            raise FlippError(
                "network_error", f"Could not reach the Flipp API: {e.reason}."
            )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise FlippError(
            "invalid_json", f"Flipp API returned non-JSON for {path}."
        )
    if not isinstance(data, dict):
        raise FlippError(
            "schema_error",
            f"Flipp API response for {path} is not a JSON object.",
        )
    return data


def require_list(data, key, path):
    """Return data[key] as a list, or raise schema_error.

    A present-but-empty list is a valid 'no results'. A missing, null, or
    non-list field means the upstream shape changed, and that must never
    masquerade as an empty result set.
    """
    if key not in data:
        raise FlippError(
            "schema_error",
            f"Flipp API response for {path} is missing the '{key}' field; "
            "the upstream schema may have changed.",
        )
    value = data[key]
    if not isinstance(value, list):
        raise FlippError(
            "schema_error",
            f"Flipp API field '{key}' for {path} is "
            f"{type(value).__name__}, expected a list.",
        )
    return value


# ------------------------------------------------------- formatting helpers

def as_number(value):
    """Best-effort numeric view of an upstream price field.

    Returns a float for numeric input and for clean numeric strings,
    else None. Promotional strings ('2 for $5', 'FREE') yield None so the
    raw value survives untouched in price_raw instead.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().lstrip("$").replace(",", ""))
        except ValueError:
            return None
    return None


def money(value):
    """Format a numeric price as $X.XX; pass free text through unchanged."""
    num = as_number(value)
    if num is not None:
        return f"${num:.2f}"
    if value is None:
        return None
    text = str(value)
    return text if text.startswith("$") else text


def price_text(item):
    """Compose display price from pre/current/post fields, flyer style."""
    cur = item.get("current_price")
    if cur is None:
        cur = item.get("price")
    parts = []
    pre = item.get("pre_price_text")
    if pre:
        parts.append(str(pre))
    if cur is not None:
        parts.append(money(cur) or "")
    post = item.get("post_price_text")
    if post:
        post = str(post)
        # Short glued-on units ('/lb', 'ea.') attach; sentences do not.
        if len(post) <= 6 and " " not in post.strip("/"):
            if parts:
                parts[-1] = parts[-1] + post
            else:
                parts.append(post)
        else:
            parts.append(post)
    return " ".join(p for p in parts if p) or "(no price)"


# --------------------------------------------------------- unit-price logic

_UNIT_RES = (
    (re.compile(r"^/?\s*100\s*g$", re.I), "100g"),
    (re.compile(r"^/?\s*lb\.?$", re.I), "lb"),
    (re.compile(r"^/?\s*kg\.?$", re.I), "kg"),
    (re.compile(r"^/?\s*(ea\.?|each)$", re.I), "each"),
)


def parse_unit(post_text):
    """Map a post_price_text unit to lb / kg / 100g / each, else None."""
    if not post_text:
        return None
    text = str(post_text).strip()
    for pattern, unit in _UNIT_RES:
        if pattern.match(text):
            return unit
    return None


def unit_price_per_kg(price_value, unit, pre_text):
    """Deterministic per-kg price, or None when it cannot be safe.

    Only single-unit weight pricing converts. Multipack or conditional
    offers (a pre_price_text like '2 for') and per-item pricing return
    None rather than a confident wrong number.
    """
    if price_value is None or price_value <= 0 or unit is None:
        return None
    if pre_text and "for" in str(pre_text).lower():
        return None
    if unit == "lb":
        return round(price_value * LB_TO_KG, 2)
    if unit == "kg":
        return round(price_value, 2)
    if unit == "100g":
        return round(price_value * 10, 2)
    return None


# ------------------------------------------------------------- normalizers
# One shared item contract for search and flyer items. Fields the upstream
# endpoint does not provide stay null; nothing is fabricated. Field names
# verified against the live API on 2026-10-29.

def norm_search_item(item):
    unit = parse_unit(item.get("post_price_text"))
    price_value = as_number(item.get("current_price"))
    return {
        "id": item.get("flyer_item_id") or item.get("id"),
        "name": item.get("name"),
        "merchant": item.get("merchant_name") or item.get("merchant"),
        "brand": item.get("brand"),
        "price_value": price_value,
        "price_raw": item.get("current_price"),
        "original_price": as_number(item.get("original_price")),
        "price_text": price_text(item),
        "pre_price_text": item.get("pre_price_text"),
        "post_price_text": item.get("post_price_text"),
        "unit": unit,
        "unit_price_per_kg": unit_price_per_kg(
            price_value, unit, item.get("pre_price_text")
        ),
        "sale_story": item.get("sale_story"),
        "image_url": item.get("clean_image_url")
        or item.get("clipping_image_url"),
        "flyer_id": item.get("flyer_id"),
        "valid_from": item.get("valid_from"),
        "valid_to": item.get("valid_to"),
    }


def norm_flyer_item(item, merchant=None):
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "merchant": merchant,
        "brand": item.get("brand"),
        "price_value": as_number(item.get("price")),
        "price_raw": item.get("price"),
        "original_price": None,
        "price_text": price_text(item),
        "pre_price_text": None,
        "post_price_text": None,
        "unit": None,
        "unit_price_per_kg": None,
        "sale_story": None,
        "discount": item.get("discount"),
        "image_url": item.get("cutout_image_url"),
        "flyer_id": item.get("flyer_id"),
        "valid_from": item.get("valid_from"),
        "valid_to": item.get("valid_to"),
    }


def norm_flyer(flyer):
    categories = flyer.get("categories")
    if not isinstance(categories, list) or not categories:
        csv = flyer.get("categories_csv") or ""
        categories = [c.strip() for c in csv.split(",") if c.strip()]
    return {
        "id": flyer.get("id"),
        "merchant": flyer.get("merchant"),
        "name": flyer.get("name"),
        "categories": categories,
        "valid_from": flyer.get("valid_from"),
        "valid_to": flyer.get("valid_to"),
    }


# -------------------------------------------------------------- validation

def resolve_postal(args):
    postal = args.postal or os.environ.get("FLIPP_POSTAL_CODE")
    if not postal:
        raise bad_args(
            "no postal code: pass --postal or set the FLIPP_POSTAL_CODE "
            "environment variable."
        )
    postal = postal.strip()
    if not POSTAL_RE.match(postal):
        raise bad_args(f"invalid Canadian postal code: {postal!r}")
    return postal


def resolve_locale(args):
    locale = (args.locale or "en-ca").strip().lower()
    if not LOCALE_RE.match(locale):
        raise bad_args(f"invalid locale: {locale!r} (expected e.g. en-ca)")
    return locale


def check_limit(value, maximum, label="--limit"):
    if value < 1:
        raise bad_args(f"{label} must be at least 1, got {value}")
    return min(value, maximum)


def emit(args, payload, text_lines):
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for line in text_lines:
            print(line)


# ---------------------------------------------------------------- commands

def cmd_search(args):
    postal = resolve_postal(args)
    locale = resolve_locale(args)
    limit = check_limit(args.limit, SEARCH_CAP)
    path = "/items/search"
    data = get(path, {"q": args.query, "postal_code": postal, "locale": locale})
    items = require_list(data, "items", path)
    shown = [norm_search_item(i) for i in items[:limit]]
    if args.merchant:
        needle = args.merchant.lower()
        shown = [i for i in shown if needle in (i["merchant"] or "").lower()]
    coverage = {
        "returned": len(items),
        "shown": len(shown),
        "limit": limit,
        "api_cap": SEARCH_CAP,
        "ranked_by": "relevance",
        "note": (
            "Keyword search returns a relevance-ranked first page only. "
            "'Cheapest' from search means cheapest among returned results; "
            "use `scan` for a bounded full-flyer comparison."
        ),
    }
    lines = [
        f"{i['price_text']} | {i['name']} | {i['merchant'] or '?'} | "
        f"flyer {i['flyer_id']} | to {i['valid_to']}"
        for i in shown
    ] or ["(no matches)"]
    if len(items) >= limit:
        lines.append(
            f"-- showing {len(shown)} of {len(items)} returned; "
            "results are relevance-ranked, not exhaustive"
        )
    emit(args, {"query": args.query, "coverage": coverage, "items": shown}, lines)
    return 0


def fetch_flyers(postal, locale):
    path = "/flyers"
    data = get(path, {"postal_code": postal, "locale": locale})
    return [norm_flyer(f) for f in require_list(data, "flyers", path)]


def cmd_flyers(args):
    postal = resolve_postal(args)
    locale = resolve_locale(args)
    limit = check_limit(args.limit, 500)
    flyers = fetch_flyers(postal, locale)
    shown = flyers
    if args.category:
        needle = args.category.lower()
        shown = [
            f for f in shown
            if any(needle in c.lower() for c in f["categories"])
        ]
    if args.merchant:
        needle = args.merchant.lower()
        shown = [
            f for f in shown if needle in (f["merchant"] or "").lower()
        ]
    total = len(shown)
    shown = shown[:limit]
    coverage = {"total_available": total, "shown": len(shown), "limit": limit}
    lines = [
        f"{f['id']} | {f['merchant']} | {f['name']} | "
        f"{', '.join(f['categories'])} | to {f['valid_to']}"
        for f in shown
    ] or ["(no flyers)"]
    emit(args, {"coverage": coverage, "flyers": shown}, lines)
    return 0


def fetch_flyer_items(flyer_id, postal, locale):
    path = f"/flyers/{flyer_id}"
    data = get(path, {"postal_code": postal, "locale": locale})
    return require_list(data, "items", path)


def cmd_flyer(args):
    postal = resolve_postal(args)
    locale = resolve_locale(args)
    limit = check_limit(args.limit, 2000)
    raw = fetch_flyer_items(args.flyer_id, postal, locale)
    items = [norm_flyer_item(i) for i in raw]
    total = len(items)
    shown = items[:limit]
    coverage = {"total_items": total, "shown": len(shown), "limit": limit}
    lines = [
        f"{i['price_text']} | {i['name']} | to {i['valid_to']}"
        + (f" | -{i['discount']}%" if i["discount"] else "")
        for i in shown
    ] or ["(flyer has no items)"]
    emit(
        args,
        {"flyer_id": args.flyer_id, "coverage": coverage, "items": shown},
        lines,
    )
    return 0


def cmd_scan(args):
    """Bounded full-flyer fallback: read whole flyers, match every term.

    Keyword search is relevance-ranked and can miss flyer items entirely.
    Scan reads up to --max-flyers flyers (default 20, hard cap 50) and
    matches items whose name contains every query term. Coverage in the
    output states exactly how much of the flyer set was covered.
    """
    postal = resolve_postal(args)
    locale = resolve_locale(args)
    max_flyers = check_limit(args.max_flyers, 50, "--max-flyers")
    terms = [t.lower() for t in args.query.split() if t.strip()]
    if not terms:
        raise bad_args("scan query must contain at least one term")
    flyers = fetch_flyers(postal, locale)
    if args.merchant:
        needle = args.merchant.lower()
        flyers = [f for f in flyers if needle in (f["merchant"] or "").lower()]
    available = len(flyers)
    matches = []
    items_scanned = 0
    scanned = 0
    for flyer in flyers[:max_flyers]:
        raw = fetch_flyer_items(flyer["id"], postal, locale)
        scanned += 1
        items_scanned += len(raw)
        for item in raw:
            name = (item.get("name") or "").lower()
            if all(t in name for t in terms):
                matches.append(norm_flyer_item(item, merchant=flyer["merchant"]))
    matches.sort(
        key=lambda i: (i["price_value"] is None, i["price_value"] or 0)
    )
    coverage = {
        "flyers_available": available,
        "flyers_scanned": scanned,
        "items_scanned": items_scanned,
        "matches": len(matches),
        "exhaustive": scanned >= available,
        "note": (
            "Matches cover the scanned flyers only; exhaustive is true "
            "only when every available flyer was scanned."
        ),
    }
    lines = [
        f"{i['price_text']} | {i['name']} | {i['merchant'] or '?'} | "
        f"flyer {i['flyer_id']} | to {i['valid_to']}"
        for i in matches
    ] or ["(no matches in scanned flyers)"]
    lines.append(
        f"-- scanned {scanned} of {available} flyers, "
        f"{items_scanned} items, {len(matches)} matches"
    )
    emit(args, {"query": args.query, "coverage": coverage, "items": matches}, lines)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Flipp deal lookup")
    parser.add_argument("--postal", help="Canadian postal code")
    parser.add_argument(
        "--locale", default="en-ca", help="locale, e.g. en-ca or fr-ca"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="keyword search across flyers")
    p.add_argument("query")
    p.add_argument("--merchant", help="filter by merchant name substring")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("flyers", help="list current flyers")
    p.add_argument("--category", help="filter by category substring")
    p.add_argument("--merchant", help="filter by merchant name substring")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(fn=cmd_flyers)

    p = sub.add_parser("flyer", help="dump one flyer's items")
    p.add_argument("flyer_id", type=int)
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(fn=cmd_flyer)

    p = sub.add_parser("scan", help="bounded full-flyer scan for a query")
    p.add_argument("query")
    p.add_argument("--merchant", help="restrict to merchant name substring")
    p.add_argument("--max-flyers", type=int, default=20)
    p.set_defaults(fn=cmd_scan)

    args = parser.parse_args()
    try:
        return args.fn(args)
    except FlippError as e:
        print(
            json.dumps({"error": e.code, "message": e.message}),
            file=sys.stderr,
        )
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
