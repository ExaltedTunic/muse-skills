#!/usr/bin/env python3
"""Regression checks for the Flipp connector CLI (connectors/flipp).

Standard library only. No network: the module's HTTP layer is stubbed
with synthetic fixtures modelled on the live Wishabi response shapes
(verified 2026-10-29). Run directly or via tests/run_all.py.
"""

import contextlib
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import types
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(
    HERE, "..", "connectors", "flipp", "bin", "flipp.py"
)
CONNECTOR_PATH = os.path.join(
    HERE, "..", "connectors", "flipp", "CONNECTOR.md"
)

spec = importlib.util.spec_from_file_location("flipp", MODULE_PATH)
flipp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flipp)

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"  FAIL: {name} {detail}")
        FAILURES.append(name)


def make_args(**kw):
    base = dict(
        postal="M5V" + " 1J1", locale="en-ca", json=True, query="chicken",
        merchant=None, category=None, limit=20, flyer_id=1, max_flyers=20,
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def stub_get(payload_by_path):
    def fake_get(path, params, retries=1):
        for prefix in sorted(payload_by_path, key=len, reverse=True):
            payload = payload_by_path[prefix]
            if path.startswith(prefix):
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"unexpected path {path}")
    return fake_get


SEARCH_PAYLOAD = {
    "items": [
        {
            "flyer_item_id": 11, "id": 11, "name": "Fresh Chicken Breast",
            "merchant_name": "Test Grocery", "current_price": 5.99,
            "original_price": 7.99, "pre_price_text": None,
            "post_price_text": "/lb", "sale_story": None,
            "clean_image_url": "https://example.invalid/a.jpg",
            "clipping_image_url": "https://example.invalid/a-clip.jpg",
            "flyer_id": 101, "valid_from": "2026-10-29",
            "valid_to": "2026-11-04",
        },
        {
            "flyer_item_id": 12, "id": 12, "name": "Chicken Soup",
            "merchant_name": "Other Mart", "current_price": 1.29,
            "original_price": None, "pre_price_text": None,
            "post_price_text": "/100 g", "sale_story": "Save $0.50",
            "clean_image_url": None,
            "clipping_image_url": "https://example.invalid/b-clip.jpg",
            "flyer_id": 102, "valid_from": "2026-10-29",
            "valid_to": "2026-11-04",
        },
    ]
}

FLYERS_PAYLOAD = {
    "flyers": [
        {
            "id": 101, "merchant": "Test Grocery", "name": "Weekly Saver",
            "categories": ["All Flyers", "Groceries"],
            "categories_csv": "All Flyers,Groceries",
            "valid_from": "2026-10-29", "valid_to": "2026-11-04",
        },
        {
            "id": 102, "merchant": "Other Mart", "name": "Toy Days",
            "categories_csv": "All Flyers,General Merchandise",
            "valid_from": "2026-10-29", "valid_to": "2026-11-04",
        },
    ]
}

FLYER_PAYLOAD = {
    "items": [
        {
            "id": 21, "name": "Basmati Rice 4.54 kg", "brand": "TestBrand",
            "price": "13.99", "discount": 18,
            "cutout_image_url": "https://example.invalid/rice.jpg",
            "flyer_id": 101, "valid_from": "2026-10-29",
            "valid_to": "2026-11-04",
        },
        {
            "id": 22, "name": "Mystery Promo", "brand": None, "price": None,
            "discount": None, "cutout_image_url": None, "flyer_id": 101,
            "valid_from": "2026-10-29", "valid_to": "2026-11-04",
        },
    ]
}


def _search_item(item_id, name, merchant):
    return {
        "flyer_item_id": item_id, "id": item_id, "name": name,
        "merchant_name": merchant, "current_price": 2.50,
        "original_price": None, "pre_price_text": None,
        "post_price_text": None, "sale_story": None,
        "clean_image_url": None, "clipping_image_url": None,
        "flyer_id": 101, "valid_from": "2026-10-29",
        "valid_to": "2026-11-04",
    }


# R2 fixtures: the merchant match sits beyond the limit boundary.
SEARCH_TWO_STORES = {"items": [
    _search_item(31, "Chicken Wings", "OtherStore"),
    _search_item(32, "Chicken Breast", "TargetMart"),
]}
SEARCH_THREE = {"items": [
    _search_item(33, "Chicken Wings", "TargetMart"),
    _search_item(34, "Chicken Soup", "OtherStore"),
    _search_item(35, "Chicken Breast", "TargetMart"),
]}


def run_json(fn, args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(args)
    assert rc == 0, f"expected rc 0, got {rc}"
    return json.loads(buf.getvalue())


def expect_error(name, fn, args, code):
    try:
        fn(args)
    except flipp.FlippError as e:
        check(name, e.code == code, f"(code was {e.code})")
        return
    check(name, False, "(no error raised)")


def expect_error_loose(name, fn, args, code):
    """expect_error that records a wrong exception type as a failure.

    Used for the schema/timeout claims, where the pre-fix behaviour is an
    unhandled AttributeError or TimeoutError escaping the command rather
    than a FlippError: that must show up as FAIL, not crash the suite.
    """
    try:
        fn(args)
    except flipp.FlippError as e:
        check(name, e.code == code, f"(code was {e.code})")
        return e
    except Exception as e:  # noqa: BLE001 - the escape IS the failure mode
        check(name, False, f"(raised {type(e).__name__}: {e})")
        return None
    check(name, False, "(no error raised)")
    return None


# ------------------------------------------------------- CLI subprocesses
# Parse-level and error-envelope checks run the real CLI in a subprocess.
# The runner stubs urllib.request.urlopen with the synthetic payloads, so
# no network is touched; reaching the command layer is observable as a
# clean exit 0 with JSON on stdout.

RUNNER = r'''
import importlib.util, json, os, re, sys
spec = importlib.util.spec_from_file_location("flipp", os.environ["FLIPP_MODULE"])
flipp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flipp)
payloads_file = os.environ.get("FLIPP_PAYLOADS")
if payloads_file:
    with open(payloads_file) as fh:
        payloads = json.load(fh)
    class FakeResp:
        def __init__(self, body):
            self._body = body
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False
        def read(self):
            return self._body
    def fake_urlopen(req, timeout=None):
        url = req.full_url
        if "/items/search" in url:
            body = payloads["search"]
        elif re.search(r"/flyers/\d+", url):
            body = payloads["flyer"]
        else:
            body = payloads["flyers"]
        return FakeResp(json.dumps(body).encode())
    flipp.urllib.request.urlopen = fake_urlopen
sys.argv = ["flipp.py"] + json.loads(os.environ["FLIPP_ARGV"])
raise SystemExit(flipp.main())
'''


def run_cli(argv, stub_network=False):
    """Run flipp.py's real main() in a subprocess; return (rc, out, err)."""
    tmp = tempfile.mkdtemp(prefix="flipp-cli-")
    runner_path = os.path.join(tmp, "runner.py")
    with open(runner_path, "w") as fh:
        fh.write(RUNNER)
    env = dict(os.environ)
    env.pop("FLIPP_POSTAL_CODE", None)
    env["FLIPP_MODULE"] = MODULE_PATH
    env["FLIPP_ARGV"] = json.dumps(argv)
    if stub_network:
        payloads_path = os.path.join(tmp, "payloads.json")
        with open(payloads_path, "w") as fh:
            json.dump({
                "search": SEARCH_PAYLOAD,
                "flyers": FLYERS_PAYLOAD,
                "flyer": FLYER_PAYLOAD,
            }, fh)
        env["FLIPP_PAYLOADS"] = payloads_path
    proc = subprocess.run(
        [sys.executable, runner_path],
        capture_output=True, text=True, env=env, timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


def documented_commands():
    """Extract every flipp.py example from CONNECTOR.md, instantiated.

    The postal placeholder is filled with a real-shaped code and the
    bracketed optional groups are included (brackets stripped), so each
    returned argv is a command a reader could paste verbatim.
    """
    with open(CONNECTOR_PATH, encoding="utf-8") as fh:
        text = fh.read()
    commands = []
    in_block = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block and "bin/flipp.py" in line:
            cmd = line.split("bin/flipp.py", 1)[1].strip()
            cmd = cmd.replace('"<postal code>"', '"' + "M5V" + " 1J1" + '"')
            cmd = cmd.replace("[", " ").replace("]", " ")
            commands.append(shlex.split(cmd))
    return commands


def globals_first(argv):
    """Move --postal/--locale/--json ahead of the subcommand token."""
    subs = {"search", "flyers", "flyer", "scan"}
    idx = next(i for i, tok in enumerate(argv) if tok in subs)
    head, rest = [], [argv[idx]]
    i = idx + 1
    while i < len(argv):
        tok = argv[i]
        if tok in ("--postal", "--locale"):
            head += argv[i:i + 2]
            i += 2
        elif tok == "--json":
            head.append(tok)
            i += 1
        else:
            rest.append(tok)
            i += 1
    return head + rest


def main():
    orig_get = flipp.get
    orig_env = os.environ.pop("FLIPP_POSTAL_CODE", None)
    try:
        # --- formatting helpers (F5) ---
        check("money FREE stays text", flipp.money("FREE") == "FREE")
        check("money numeric", flipp.money(2.5) == "$2.50")
        check("money promo string untouched",
              flipp.money("2 for $5") == "2 for $5")
        check("money None", flipp.money(None) is None)
        check("as_number numeric string", flipp.as_number("25.0") == 25.0)
        check("as_number promo string", flipp.as_number("2 for $5") is None)
        check("price_text glues unit",
              flipp.price_text({"current_price": 5.99,
                                "post_price_text": "/lb"}) == "$5.99/lb")
        check("price_text post-only no crash",
              flipp.price_text({"post_price_text": "/lb"}) == "/lb")

        # --- unit parsing and per-kg (F5, Phase 4) ---
        check("unit /lb", flipp.parse_unit("/lb") == "lb")
        check("unit /100 g", flipp.parse_unit("/100 g") == "100g")
        check("unit ea.", flipp.parse_unit("ea.") == "each")
        check("unit junk", flipp.parse_unit("save big") is None)
        check("per-kg from lb",
              flipp.unit_price_per_kg(5.99, "lb", None) == 13.21)
        check("per-kg from 100g",
              flipp.unit_price_per_kg(1.29, "100g", None) == 12.9)
        check("per-kg each is None",
              flipp.unit_price_per_kg(3.0, "each", None) is None)
        check("per-kg multipack refused",
              flipp.unit_price_per_kg(5.0, "lb", "2 for") is None)

        # --- search success + contract (F1, F2, F3) ---
        flipp.get = stub_get({"/items/search": SEARCH_PAYLOAD})
        out = run_json(flipp.cmd_search, make_args())
        check("search returns items", len(out["items"]) == 2)
        first = out["items"][0]
        check("search keeps sale_story key", "sale_story" in first)
        check("search image prefers clean url",
              first["image_url"].endswith("a.jpg"))
        check("search image falls back to clipping",
              out["items"][1]["image_url"].endswith("b-clip.jpg"))
        check("search per-kg computed",
              first["unit_price_per_kg"] == 13.21)
        check("search coverage present",
              out["coverage"]["returned"] == 2
              and out["coverage"]["ranked_by"] == "relevance")
        out = run_json(flipp.cmd_search, make_args(merchant="other"))
        check("search merchant filter", len(out["items"]) == 1)

        # --- valid empty vs schema drift (F1, F7) ---
        flipp.get = stub_get({"/items/search": {"items": []}})
        out = run_json(flipp.cmd_search, make_args())
        check("empty items is a valid empty result", out["items"] == [])
        flipp.get = stub_get({"/items/search": {"ads": []}})
        expect_error("missing items key is schema_error",
                     flipp.cmd_search, make_args(), "schema_error")
        flipp.get = stub_get({"/items/search": {"items": None}})
        expect_error("null items is schema_error",
                     flipp.cmd_search, make_args(), "schema_error")
        flipp.get = stub_get({"/items/search": {"items": {"x": 1}}})
        expect_error("non-list items is schema_error",
                     flipp.cmd_search, make_args(), "schema_error")

        # --- flyers: categories array + csv fallback (F4) ---
        flipp.get = stub_get({"/flyers": FLYERS_PAYLOAD})
        out = run_json(flipp.cmd_flyers, make_args())
        check("flyers list both", len(out["flyers"]) == 2)
        check("categories array used",
              out["flyers"][0]["categories"] == ["All Flyers", "Groceries"])
        check("categories csv fallback",
              out["flyers"][1]["categories"]
              == ["All Flyers", "General Merchandise"])
        check("flyers coverage totals",
              out["coverage"]["total_available"] == 2)
        out = run_json(flipp.cmd_flyers, make_args(category="groceries"))
        check("flyers category filter", len(out["flyers"]) == 1)
        out = run_json(flipp.cmd_flyers, make_args(merchant="other"))
        check("flyers merchant filter", len(out["flyers"]) == 1)

        # --- flyer detail contract (F2 corrected scope) ---
        flipp.get = stub_get({"/flyers/": FLYER_PAYLOAD})
        out = run_json(flipp.cmd_flyer, make_args())
        rice = out["items"][0]
        check("flyer price string parsed", rice["price_value"] == 13.99)
        check("flyer price raw kept", rice["price_raw"] == "13.99")
        check("flyer discount kept", rice["discount"] == 18)
        check("flyer brand kept", rice["brand"] == "TestBrand")
        check("flyer absent fields are null, not invented",
              rice["sale_story"] is None and rice["original_price"] is None)
        check("flyer priceless item survives",
              out["items"][1]["price_value"] is None)
        check("flyer coverage totals", out["coverage"]["total_items"] == 2)

        # --- scan: full-flyer fallback (F3, Phase 4) ---
        flipp.get = stub_get({
            "/flyers": FLYERS_PAYLOAD,
            "/flyers/101": FLYER_PAYLOAD,
            "/flyers/102": {"items": []},
        })
        out = run_json(flipp.cmd_scan, make_args(query="basmati rice"))
        check("scan finds flyer-only item", len(out["items"]) == 1)
        check("scan enriches merchant",
              out["items"][0]["merchant"] == "Test Grocery")
        check("scan coverage exhaustive",
              out["coverage"]["exhaustive"] is True
              and out["coverage"]["flyers_scanned"] == 2)

        # --- argument validation (F7) ---
        expect_error("bad postal rejected",
                     flipp.cmd_search, make_args(postal="123" + "45"), "bad_args")
        expect_error("missing postal rejected",
                     flipp.cmd_search, make_args(postal=None), "bad_args")
        expect_error("zero limit rejected",
                     flipp.cmd_search, make_args(limit=0), "bad_args")
        expect_error("negative limit rejected",
                     flipp.cmd_search, make_args(limit=-3), "bad_args")
        expect_error("bad locale rejected",
                     flipp.cmd_search, make_args(locale="english"),
                     "bad_args")
        check("search limit clamps to API cap",
              flipp.check_limit(9999, flipp.SEARCH_CAP) == 150)

        # --- HTTP layer failures (F7) ---
        flipp.get = orig_get  # exercise the real HTTP layer now
        class FakeResp:
            def __init__(self, body):
                self._body = body

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return self._body

        real_urlopen = flipp.urllib.request.urlopen
        try:
            flipp.urllib.request.urlopen = (
                lambda req, timeout=None: FakeResp(b"not json"))
            try:
                flipp.get("/items/search", {})
                check("invalid JSON raises", False)
            except flipp.FlippError as e:
                check("invalid JSON raises", e.code == "invalid_json")

            def raise_429(req, timeout=None):
                raise urllib.error.HTTPError(
                    req.full_url, 429, "Too Many", {}, None)

            flipp.urllib.request.urlopen = raise_429
            try:
                flipp.get("/items/search", {})
                check("HTTP 429 is rate_limited", False)
            except flipp.FlippError as e:
                check("HTTP 429 is rate_limited", e.code == "rate_limited")

            def raise_500(req, timeout=None):
                raise urllib.error.HTTPError(
                    req.full_url, 500, "Server Error", {}, None)

            flipp.urllib.request.urlopen = raise_500
            try:
                flipp.get("/items/search", {})
                check("HTTP 500 is http_error", False)
            except flipp.FlippError as e:
                check("HTTP 500 is http_error", e.code == "http_error")
        finally:
            flipp.urllib.request.urlopen = real_urlopen

        # --- R1: documented command forms parse (globals after subcommand) ---
        docs = documented_commands()
        check("CONNECTOR.md yields four command examples", len(docs) == 4,
              f"(got {len(docs)})")
        for argv in docs:
            label = " ".join(argv[:2])
            rc, out, err = run_cli(argv, stub_network=True)
            try:
                json.loads(out)
                parsed = True
            except ValueError:
                parsed = False
            check(f"documented form parses: {label}",
                  rc == 0 and parsed,
                  f"(rc={rc}, stderr={err.strip()[:120]})")
            rc, out, err = run_cli(globals_first(argv), stub_network=True)
            check(f"globals-first form parses: {label}",
                  rc == 0, f"(rc={rc}, stderr={err.strip()[:120]})")

        # --- R1: argparse failures emit the JSON error envelope ---
        for argv, label in [
            (["search", "chicken", "--bogus"], "unknown flag"),
            (["search", "chicken", "--limit", "abc"], "non-integer limit"),
            (["boguscmd"], "unknown subcommand"),
            ([], "no arguments"),
        ]:
            rc, out, err = run_cli(argv)
            try:
                payload = json.loads(err)
            except ValueError:
                payload = {}
            check(f"argparse failure is JSON bad_args: {label}",
                  rc == 2 and payload.get("error") == "bad_args",
                  f"(rc={rc}, stderr={err.strip()[:120]})")

        # --- R2: merchant filter runs before the limit slice ---
        flipp.get = stub_get({"/items/search": SEARCH_TWO_STORES})
        out = run_json(flipp.cmd_search,
                       make_args(merchant="target", limit=1))
        check("match beyond limit survives merchant filter",
              [i["name"] for i in out["items"]] == ["Chicken Breast"])
        cov = out["coverage"]
        check("coverage distinguishes returned/matched/shown",
              cov.get("returned") == 2 and cov.get("matched") == 1
              and cov.get("shown") == 1,
              f"(coverage={cov})")
        flipp.get = stub_get({"/items/search": SEARCH_THREE})
        out = run_json(flipp.cmd_search,
                       make_args(merchant="target", limit=1))
        cov = out["coverage"]
        check("limit truncates matched set, counts stay distinct",
              cov.get("returned") == 3 and cov.get("matched") == 2
              and cov.get("shown") == 1 and len(out["items"]) == 1,
              f"(coverage={cov})")
        out = run_json(flipp.cmd_search, make_args(limit=2))
        cov = out["coverage"]
        check("no merchant filter: matched equals returned",
              cov.get("returned") == 3 and cov.get("matched") == 3
              and cov.get("shown") == 2,
              f"(coverage={cov})")

        # --- R3a: timeouts are retryable network failures ---
        flipp.get = orig_get
        real_urlopen = flipp.urllib.request.urlopen
        real_sleep = flipp.time.sleep
        flipp.time.sleep = lambda s: None
        try:
            calls = {"n": 0}

            def raise_timeout(req, timeout=None):
                calls["n"] += 1
                raise TimeoutError("timed out")

            flipp.urllib.request.urlopen = raise_timeout
            try:
                flipp.get("/items/search", {})
                check("timeout ends in network_error", False,
                      "(no error raised)")
            except flipp.FlippError as e:
                check("timeout ends in network_error",
                      e.code == "network_error", f"(code was {e.code})")
            except Exception as e:  # noqa: BLE001 - the escape is the bug
                check("timeout ends in network_error", False,
                      f"(escaped as {type(e).__name__})")
            check("timeout was retried before failing", calls["n"] == 2,
                  f"(urlopen calls={calls['n']})")

            state = {"n": 0}

            def timeout_then_ok(req, timeout=None):
                state["n"] += 1
                if state["n"] == 1:
                    raise TimeoutError("timed out")
                return FakeResp(b'{"items": []}')

            flipp.urllib.request.urlopen = timeout_then_ok
            try:
                data = flipp.get("/items/search", {})
                check("timeout then success returns data",
                      data == {"items": []})
            except Exception as e:  # noqa: BLE001
                check("timeout then success returns data", False,
                      f"(raised {type(e).__name__}: {e})")

            def raise_urlerror(req, timeout=None):
                raise urllib.error.URLError("connection refused")

            flipp.urllib.request.urlopen = raise_urlerror
            try:
                flipp.get("/items/search", {})
                check("URLError ends in network_error", False,
                      "(no error raised)")
            except flipp.FlippError as e:
                check("URLError ends in network_error",
                      e.code == "network_error", f"(code was {e.code})")
        finally:
            flipp.urllib.request.urlopen = real_urlopen
            flipp.time.sleep = real_sleep

        # --- R3b: non-object records in upstream lists are schema_error ---
        flipp.get = stub_get({"/items/search": {"items": [None]}})
        expect_error_loose("null search item is schema_error",
                           flipp.cmd_search, make_args(), "schema_error")
        flipp.get = stub_get({"/items/search": {
            "items": [SEARCH_PAYLOAD["items"][0], 42]}})
        e = expect_error_loose("non-object search item is schema_error",
                               flipp.cmd_search, make_args(), "schema_error")
        check("schema_error names the record index",
              e is not None and "index 1" in e.message,
              f"(message={getattr(e, 'message', None)!r})")
        flipp.get = stub_get({"/flyers": {"flyers": [None]}})
        expect_error_loose("null flyer record is schema_error",
                           flipp.cmd_flyers, make_args(), "schema_error")
        flipp.get = stub_get({"/flyers/": {"items": ["oops"]}})
        expect_error_loose("non-object flyer item is schema_error",
                           flipp.cmd_flyer, make_args(), "schema_error")
        flipp.get = stub_get({
            "/flyers": FLYERS_PAYLOAD,
            "/flyers/101": {"items": [None]},
            "/flyers/102": {"items": []},
        })
        expect_error_loose("null item inside scan is schema_error",
                           flipp.cmd_scan, make_args(), "schema_error")
        flipp.get = stub_get({"/flyers": {"flyers": [None]}})
        expect_error_loose("null flyer record inside scan is schema_error",
                           flipp.cmd_scan, make_args(), "schema_error")
    finally:
        flipp.get = orig_get
        if orig_env is not None:
            os.environ["FLIPP_POSTAL_CODE"] = orig_env

    print()
    if FAILURES:
        print(f"flipp_checks: {len(FAILURES)} FAILURES: {FAILURES}")
        return 1
    print("flipp_checks: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
