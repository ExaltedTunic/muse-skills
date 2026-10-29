#!/usr/bin/env python3
"""Flipp (Wishabi) flyer deals CLI. Public, keyless, unofficial API.

Usage:
    flipp.py search "chicken breast" [--postal "<postal code>"] [--limit 20] [--json]
    flipp.py flyers [--postal "<postal code>"] [--merchant sobeys] [--limit 30] [--json]
    flipp.py flyer 8130428 [--postal "<postal code>"] [--limit 40] [--json]

There is no built-in default postal code. Pass --postal on each call, or
set the FLIPP_POSTAL_CODE environment variable to your own postal code.
The API is unofficial, so keep request volume low: one call per command.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://backflipp.wishabi.com/flipp"
DEFAULT_POSTAL = os.environ.get("FLIPP_POSTAL_CODE")
HEADERS = {"User-Agent": "Mozilla/5.0 (personal flyer deal checker)"}


def get(path, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def day(value):
    return (value or "")[:10]


def money(value):
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return f"${float(text):,.2f}"
        except ValueError:
            return text if text.startswith("$") else f"${text}"
    return None


def price_text(item, key="current_price"):
    price = money(item.get(key))
    if not price:
        return ""
    out = price
    pre = (item.get("pre_price_text") or "").strip()
    post = (item.get("post_price_text") or "").strip()
    if pre:
        out = f"{pre} {out}"
    if post:
        out = f"{out}/{post}" if len(post) <= 5 and " " not in post else f"{out} {post}"
    return out


def norm_search_item(item):
    return {
        "name": item.get("name"),
        "price": price_text(item) or None,
        "price_value": item.get("current_price"),
        "original_price": item.get("original_price"),
        "merchant": item.get("merchant_name"),
        "valid_from": day(item.get("valid_from")),
        "valid_to": day(item.get("valid_to")),
        "flyer_id": item.get("flyer_id"),
        "sale_story": item.get("sale_story"),
        "image_url": item.get("clean_image_url"),
    }


def norm_flyer(flyer):
    return {
        "id": flyer.get("id"),
        "merchant": flyer.get("merchant"),
        "name": flyer.get("name"),
        "valid_from": day(flyer.get("valid_from")),
        "valid_to": day(flyer.get("valid_to")),
        "categories": flyer.get("categories_csv"),
    }


def norm_flyer_item(item):
    return {
        "name": item.get("name"),
        "price": price_text(item, key="price") or None,
        "discount": item.get("discount"),
        "valid_from": day(item.get("valid_from")),
        "valid_to": day(item.get("valid_to")),
    }


def cmd_search(args):
    data = get("/items/search", {"q": args.query, "postal_code": args.postal})
    items = [norm_search_item(i) for i in data.get("items", [])[: args.limit]]
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        for i in items:
            print(f"- {i['price'] or '(no price)'} | {i['merchant']} | {i['name']} "
                  f"| {i['valid_from']} to {i['valid_to']}")
        print(f"({len(items)} results)", file=sys.stderr)
    return 0


def cmd_flyers(args):
    data = get("/flyers", {"postal_code": args.postal})
    flyers = [norm_flyer(f) for f in data.get("flyers", [])]
    if args.merchant:
        needle = args.merchant.lower()
        flyers = [f for f in flyers if needle in (f["merchant"] or "").lower()]
    flyers = flyers[: args.limit]
    if args.json:
        print(json.dumps(flyers, indent=2, ensure_ascii=False))
    else:
        for f in flyers:
            print(f"- [{f['id']}] {f['merchant']} | {f['name']} "
                  f"| {f['valid_from']} to {f['valid_to']}")
        print(f"({len(flyers)} flyers)", file=sys.stderr)
    return 0


def cmd_flyer(args):
    data = get(f"/flyers/{args.flyer_id}", {"postal_code": args.postal})
    items = [norm_flyer_item(i) for i in data.get("items", [])[: args.limit]]
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        for i in items:
            disc = f" | {i['discount']}" if i["discount"] else ""
            print(f"- {i['price'] or '(no price)'}{disc} | {i['name']} "
                  f"| {i['valid_from']} to {i['valid_to']}")
        print(f"({len(items)} items shown)", file=sys.stderr)
    return 0


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--postal", default=DEFAULT_POSTAL)
    common.add_argument("--json", action="store_true")

    parser = argparse.ArgumentParser(description="Flipp flyer deals")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", parents=[common])
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    p_flyers = sub.add_parser("flyers", parents=[common])
    p_flyers.add_argument("--merchant")
    p_flyers.add_argument("--limit", type=int, default=30)
    p_flyers.set_defaults(func=cmd_flyers)

    p_flyer = sub.add_parser("flyer", parents=[common])
    p_flyer.add_argument("flyer_id", type=int)
    p_flyer.add_argument("--limit", type=int, default=40)
    p_flyer.set_defaults(func=cmd_flyer)

    args = parser.parse_args()
    if not args.postal:
        print("error: no postal code. Pass --postal or set FLIPP_POSTAL_CODE.",
              file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except urllib.error.HTTPError as e:
        print(f"error: Flipp API returned HTTP {e.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: could not reach Flipp API ({e.reason})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
