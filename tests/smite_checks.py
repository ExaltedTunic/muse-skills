#!/usr/bin/env python3
"""Mocked reproduction checks for fix wave W4 (smite-2-builds).

Each check targets one verified defect (G01-G04, CTX01/CTX02 mechanics).
Run against the pre-fix code these checks FAIL; against the fixed code
they PASS. No network: fetch/item_tier are stubbed throughout, except
the tier-cache checks which stub fetch and use the real item_tier.

Usage: python3 checks.py
Exit code 0 when every check passes, 1 otherwise.
"""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "skills", "games", "smite-2-builds", "scripts", "fetch_build.py")

spec = importlib.util.spec_from_file_location("fetch_build", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REAL_ITEM_TIER = mod.item_tier
REAL_FETCH_SKILLS = mod.fetch_skills
RESULTS = []


def check(name):
    def deco(fn):
        try:
            detail = fn()
            RESULTS.append((name, True, detail or ""))
            print(f"PASS {name} {detail or ''}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {name} {type(exc).__name__}: {exc}")
        return fn
    return deco


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def slug(name):
    return name.lower().replace("'", "").replace(" ", "-")


TIERS = {
    "alpha": "Tier 3", "beta": "Tier 3", "gamma": "Tier 3",
    "delta": "Tier 3", "epsilon": "Tier 3", "zeta": "Tier 3",
    "eta": "Tier 3", "theta": "Tier 3",
    "comp-x": "Tier 2", "mystery-item": None,
}


def stub_tiers():
    mod.item_tier = lambda s: TIERS.get(s, "Tier 3")


def make_build(items, role="jungle", starter="Bumba's Dagger",
               relic=None, aspect=None):
    def view(name):
        if not name:
            return None
        return {"item_name": name,
                "detail_href": f"/items/{slug(name)}",
                "icon_hash": "abc"}
    return {
        "played_role": role,
        "starter": view(starter),
        "relic": view(relic),
        "aspect": view(aspect),
        "items": {str(i + 1): view(n) for i, n in enumerate(items)},
    }


CORE6 = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]


def run_main(argv, builds, patch="Open Beta 46", skills=None):
    """Call mod.main() fully stubbed; return (rc, stdout, stderr)."""
    stub_tiers()
    mod.decode_page = lambda raw: {"builds": builds}
    mod.fetch = lambda url: "raw-page"
    mod.current_patch = lambda god: patch
    if skills is None:
        skills = {"start": [1, 2, 3, 1],
                  "max_order": [{"slot": 2, "name": None},
                                {"slot": 1, "name": None},
                                {"slot": 3, "name": None}],
                  "ult_levels": [5, 9, 13, 17],
                  "source_title": "Stub", "source_roles": ["Jungle"]}
    mod.fetch_skills = lambda god, role: skills
    old_argv = sys.argv
    sys.argv = ["fetch_build.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mod.main()
    finally:
        sys.argv = old_argv
    return rc, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------- G01

@check("G01a component never enters core; build marked incomplete")
def _():
    stub_tiers()
    builds = [make_build(["Alpha", "Beta", "Gamma", "Delta", "Epsilon",
                          "Comp X"]) for _ in range(10)]
    res = mod.aggregate(builds, "jungle")
    names = [v["name"] for v in res["core"]]
    expect("Comp X" not in names, f"component in core: {names}")
    expect("Comp X" not in [v["name"] for v in res["flex"]],
           "component in flex")
    expect(len(res["core"]) == 5, f"core len {len(res['core'])} != 5")
    expect(res.get("complete") is False, f"complete={res.get('complete')}")
    expect(res.get("missing") == 1, f"missing={res.get('missing')}")
    return f"core={names} missing={res.get('missing')}"


@check("G01b unknown tier is unverified, excluded, counts as missing")
def _():
    stub_tiers()
    builds = [make_build(["Alpha", "Beta", "Gamma", "Delta", "Epsilon",
                          "Mystery Item"]) for _ in range(10)]
    res = mod.aggregate(builds, "jungle")
    names = [v["name"] for v in res["core"]]
    expect("Mystery Item" not in names, f"unverified item in core: {names}")
    unv = [v["name"] for v in res.get("unverified", [])]
    expect("Mystery Item" in unv, f"unverified list: {unv}")
    expect(res.get("complete") is False, "build wrongly complete")
    expect(res.get("missing") == 1, f"missing={res.get('missing')}")
    return f"unverified={unv}"


@check("G01c complete sample stays complete; flex holds only Tier 3")
def _():
    stub_tiers()
    builds = ([make_build(["Alpha", "Beta", "Gamma", "Delta", "Eta",
                           "Comp X"]) for _ in range(5)]
              + [make_build(CORE6) for _ in range(5)])
    res = mod.aggregate(builds, "jungle")
    expect(res.get("complete") is True, f"complete={res.get('complete')}")
    expect(res.get("missing") == 0, f"missing={res.get('missing')}")
    expect(len(res["core"]) == 6, f"core len {len(res['core'])}")
    flex = [v["name"] for v in res["flex"]]
    # 7 completed items (Alpha-Delta, Eta, Epsilon, Zeta): core takes 6,
    # flex gets the remaining Tier 3 only; Comp X appears nowhere.
    expect(flex == ["Zeta"], f"flex={flex} (want ['Zeta'], no components)")
    expect("Eta" in [v["name"] for v in res["core"]], "Eta missing from core")
    return f"core={[v['name'] for v in res['core']]} flex={flex}"


@check("G01d main: incomplete build exits 2 in JSON and compact")
def _():
    builds = [make_build(["Alpha", "Beta", "Gamma", "Delta", "Epsilon",
                          "Comp X"]) for _ in range(10)]
    rc, out, _ = run_main(["thor", "--role", "jungle", "--json"], builds)
    expect(rc == 2, f"json rc={rc} != 2")
    data = json.loads(out)
    expect(data.get("complete") is False, "json complete not false")
    expect(data.get("missing") == 1, f"json missing={data.get('missing')}")
    expect(len(data["core"]) == 5, "json core not 5")
    rc, out, _ = run_main(["thor", "--role", "jungle", "--compact"], builds)
    expect(rc == 2, f"compact rc={rc} != 2")
    expect("INCOMPLETE" in out and "5/6" in out,
           f"compact lacks incomplete notice: {out!r}")
    return "json+compact both rc=2 with incomplete marking"


# ---------------------------------------------------------------- G02

SS_HTML = ('{"title":"%s Build","roles":["%s"],"matchScore":80,'
           '"abilityLevelOrder":[1,2,3,1,2,3,1,2,4,1,2,3,1,2,3,4,1,2,3,4]}')


def ss_fetch(html):
    def fake_fetch(url):
        if "smitesource.com" in url:
            return html
        raise RuntimeError("no network in checks")
    return fake_fetch


@check("G02a fetch_skills: no role match -> missing note, no substitution")
def _():
    mod.fetch_skills = REAL_FETCH_SKILLS
    mod.fetch = ss_fetch(SS_HTML % ("Solo", "Solo"))
    res = mod.fetch_skills("Thor", "jungle")
    expect(isinstance(res, dict), f"expected dict, got {res!r}")
    expect(res.get("missing_note"), f"no missing_note in {res!r}")
    expect("start" not in res, "another role's order was substituted")
    return f"note={res['missing_note']!r}"


@check("G02b fetch_skills: role match behaviour unchanged")
def _():
    mod.fetch_skills = REAL_FETCH_SKILLS
    mod.fetch = ss_fetch(SS_HTML % ("Jungle", "Jungle"))
    res = mod.fetch_skills("Thor", "jungle")
    expect(res and res.get("start") == [1, 2, 3, 1], f"res={res!r}")
    expect(res.get("source_roles") == ["Jungle"], f"roles={res!r}")
    return "matched role returns its order"


@check("G02c main: skills null + note in JSON, note line in compact")
def _():
    builds = [make_build(CORE6) for _ in range(10)]
    note = ("SmiteSource has no build for Thor in the jungle role; "
            "no skill order available.")
    rc, out, _ = run_main(["thor", "--role", "jungle", "--json"], builds,
                          skills={"missing_note": note})
    expect(rc == 0, f"json rc={rc}")
    data = json.loads(out)
    expect(data.get("skills") is None, f"skills={data.get('skills')!r}")
    expect(data.get("skills_note") == note,
           f"skills_note={data.get('skills_note')!r}")
    rc, out, _ = run_main(["thor", "--role", "jungle", "--compact"], builds,
                          skills={"missing_note": note})
    expect(rc == 0, f"compact rc={rc}")
    expect(note in out, f"note missing from compact: {out!r}")
    expect("Skills:" not in out, "compact still prints a Skills line")
    return "note surfaced in both modes"


# ---------------------------------------------------------------- G03

@check("G03a patch unknown: abort exit 3, no build emitted")
def _():
    builds = [make_build(CORE6) for _ in range(10)]
    rc, out, err = run_main(["thor", "--role", "jungle", "--json"], builds,
                            patch=None)
    expect(rc == 3, f"rc={rc} != 3")
    expect(out.strip() == "", f"build emitted despite no patch: {out!r}")
    expect("patch" in err.lower(), f"no patch error message: {err!r}")
    return f"rc=3 err={err.strip()[:60]!r}"


@check("G03b tier cache is patch-versioned; legacy cache discarded")
def _():
    expect(hasattr(mod, "set_current_patch"),
           "set_current_patch() missing (patch threading not implemented)")
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    old_path = mod._TIER_CACHE_PATH
    mod._TIER_CACHE_PATH = path
    mod.item_tier = REAL_ITEM_TIER
    try:
        mod.set_current_patch("Open Beta 46")
        # Legacy flat cache: must be ignored, slug refetched.
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"old-slug": "Tier 1"}, fh)
        mod._TIER_CACHE = {}
        mod._TIER_CACHE_PATCH = object()
        payload = {"nodes": [{"type": "data", "data":
                              [{"item": 1}, {"tier": 2}, "Tier 3"]}]}
        mod.fetch = lambda url: json.dumps(payload)
        tier = mod.item_tier("old-slug")
        expect(tier == "Tier 3", f"legacy cache trusted, tier={tier!r}")
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
        expect(saved.get("patch") == "Open Beta 46",
               f"saved cache not patch-versioned: {saved!r}")
        expect(saved.get("tiers", {}).get("old-slug") == "Tier 3",
               f"saved tiers wrong: {saved!r}")
        # Stale patch label: discarded even though slug present.
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"patch": "Open Beta 45",
                       "tiers": {"y-slug": "Tier 2"}}, fh)
        mod._TIER_CACHE = {}
        mod._TIER_CACHE_PATCH = object()

        def boom(url):
            raise RuntimeError("offline")
        mod.fetch = boom
        tier = mod.item_tier("y-slug")
        expect(tier is None, f"stale-patch cache trusted, tier={tier!r}")
        # Current patch label: served from cache without fetching.
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"patch": "Open Beta 46",
                       "tiers": {"z-slug": "Tier 2"}}, fh)
        mod._TIER_CACHE = {}
        mod._TIER_CACHE_PATCH = object()
        tier = mod.item_tier("z-slug")
        expect(tier == "Tier 2", f"current-patch cache not used: {tier!r}")
    finally:
        mod._TIER_CACHE_PATH = old_path
        try:
            os.unlink(path)
        except OSError:
            pass
    return "legacy+stale discarded, current-patch cache honoured"


# ---------------------------------------------------------------- G04

@check("G04 no --role and sample has no role data: stop exit 3")
def _():
    builds = [make_build(CORE6, role="") for _ in range(10)]
    for b in builds:
        b.pop("played_role", None)
    rc, out, err = run_main(["thor", "--json"], builds)
    expect(rc == 3, f"rc={rc} != 3 (build pooled/emitted?) out={out[:80]!r}")
    expect(out.strip() == "", f"build emitted: {out[:80]!r}")
    expect("role" in err.lower(), f"no role message: {err!r}")
    return f"rc=3 err={err.strip()[:60]!r}"


@check("G04b no --role with role data: primary role path unchanged")
def _():
    builds = [make_build(CORE6, role="jungle") for _ in range(10)]
    rc, out, err = run_main(["thor", "--json"], builds)
    expect(rc == 0, f"rc={rc} err={err!r}")
    data = json.loads(out)
    expect(data.get("role") == "jungle", f"role={data.get('role')!r}")
    return "primary role determined and build emitted"


# --------------------------------------------------------------- CTX02

@check("CTX02 aspect/relic votes carry the empty denominator")
def _():
    stub_tiers()
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6,
            relic="Blink Rune" if i < 3 else None,
            aspect="Aspect of Thunderstruck" if i < 2 else None))
    res = mod.aggregate(builds, "jungle")
    asp = res.get("aspect") or {}
    expect(asp.get("count") == 2, f"aspect count={asp.get('count')}")
    expect(asp.get("empty") == 8, f"aspect empty={asp.get('empty')}")
    rel = res.get("relic") or {}
    expect(rel.get("count") == 3, f"relic count={rel.get('count')}")
    expect(rel.get("empty") == 7, f"relic empty={rel.get('empty')}")
    return f"aspect 2/10 (empty 8), relic 3/10 (empty 7)"


@check("CTX02b compact shows aspect share / honest majority-empty line")
def _():
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6, relic="Blink Rune",
            aspect="Aspect of Thunderstruck" if i < 2 else None))
    rc, out, _ = run_main(["thor", "--role", "jungle", "--compact"], builds)
    expect(rc == 0, f"rc={rc}")
    expect("Aspect: none recorded in most builds (8/10)" in out,
           f"majority-empty line missing: {out!r}")
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6, relic="Blink Rune",
            aspect="Aspect of Thunderstruck" if i < 7 else None))
    rc, out, _ = run_main(["thor", "--role", "jungle", "--compact"], builds)
    expect(rc == 0, f"rc={rc}")
    expect("Aspect: Aspect of Thunderstruck (7/10)" in out,
           f"share line missing: {out!r}")
    return "compact carries the denominator both ways"


@check("CTX02c full mode shows empty count next to the winner")
def _():
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6, relic="Blink Rune" if i < 3 else None,
            aspect="Aspect of Thunderstruck" if i < 2 else None))
    rc, out, _ = run_main(["thor", "--role", "jungle"], builds)
    expect(rc == 0, f"rc={rc}")
    # Empty-majority aspect uses the honest majority line, which still
    # carries the empty denominator; the relic winner carries its own.
    expect("Aspect:  none recorded in most builds (8/10)" in out,
           f"aspect empty count missing in full mode: {out!r}")
    expect("7/10 with none recorded" in out,
           f"relic empty count missing in full mode: {out!r}")
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6, relic="Blink Rune",
            aspect="Aspect of Thunderstruck" if i < 7 else None))
    rc, out, _ = run_main(["thor", "--role", "jungle"], builds)
    expect(rc == 0, f"rc={rc}")
    expect("Aspect of Thunderstruck (7/10) - 3/10 with none recorded" in out,
           f"winner empty count missing in full mode: {out!r}")
    return "full mode carries empty counts"


# ------------------------------------------------------- preserved behaviour

@check("PRESERVE aspect filter: match builds, zero-match exits 1")
def _():
    builds = []
    for i in range(10):
        builds.append(make_build(
            CORE6, aspect="Aspect of Thunderstruck" if i < 4 else None))
    rc, out, _ = run_main(
        ["thor", "--role", "jungle", "--json", "--aspect", "thunderstruck"],
        builds)
    expect(rc == 0, f"filtered rc={rc}")
    data = json.loads(out)
    expect(data.get("sample") == 4, f"sample={data.get('sample')}")
    rc, out, err = run_main(
        ["thor", "--role", "jungle", "--json", "--aspect", "nonexistent"],
        builds)
    expect(rc == 1, f"zero-match rc={rc} != 1")
    expect("No builds for aspect" in err, f"zero-match message: {err!r}")
    return "filter and its exit-1 message intact"


def main():
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
