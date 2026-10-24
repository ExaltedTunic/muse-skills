#!/usr/bin/env python3
"""Fetch recent Smite 2 builds from SmiteBrain's SvelteKit data endpoint.

SmiteBrain has no documented public API. Its builds pages are backed by a
`__data.json` endpoint that returns the page data as devalue-flattened JSON.
This script decodes that payload and aggregates the top-player match builds
for one god and role into a single consensus build.

Usage:
    fetch_build.py <god> [--role <role>] [--json]

Examples:
    fetch_build.py thor --role jungle
    fetch_build.py "Da Ji" --role jungle --json

Stdlib only. One request per invocation (two on fallback). Human scale use.
"""

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter

BASE = "https://smitebrain.com"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def god_slug(name):
    s = name.strip().lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def unflatten(data):
    """Decode a devalue-flattened array. Integers are indices into the
    array, primitives are stored at their own index."""
    cache = {}

    def deref(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value < 0:
                return None
            return resolve(value)
        if isinstance(value, list):
            return [deref(v) for v in value]
        if isinstance(value, dict):
            return {k: deref(v) for k, v in value.items()}
        return value

    def resolve(idx):
        if idx in cache:
            return cache[idx]
        val = data[idx]
        if isinstance(val, dict):
            obj = {}
            cache[idx] = obj
            for k, v in val.items():
                obj[k] = deref(v)
            return obj
        if isinstance(val, list):
            arr = []
            cache[idx] = arr
            for v in val:
                arr.append(deref(v))
            return arr
        cache[idx] = val
        return val

    return resolve(0)


def decode_page(raw):
    """Return the decoded page-data dict (the node holding a builds list)."""
    payload = json.loads(raw)
    for node in payload.get("nodes", []):
        if not isinstance(node, dict) or node.get("type") != "data":
            continue
        data = node.get("data")
        if not isinstance(data, list) or not data:
            continue
        try:
            decoded = unflatten(data)
        except Exception:
            continue
        if isinstance(decoded, dict) and isinstance(decoded.get("builds"), list):
            return decoded
    return None


# SmiteBrain sometimes serves a pre-rename item name with no icon when an
# item was renamed in a later patch. Map known stale names to the current
# item so builds never show an item that no longer exists.
# Verified 2026-10-23 against wiki.smite2.com: Brawler's Ruin was renamed
# to Brawler's Beat Stick in OB15 when item anti-heal was removed.
RENAMED_ITEMS = {
    "brawler's ruin": {
        "name": "Brawler's Beat Stick",
        "slug": "brawlers-beat-stick",
        "icon": "https://images.smitebrain.com/images/items/icons/"
                "brawlers-beat-stick?v=691e59fb",
    },
}


def item_view(obj):
    if not isinstance(obj, dict):
        return None
    name = (obj.get("item_name") or "").strip()
    if not name or name == "Empty":
        return None
    renamed = RENAMED_ITEMS.get(name.lower())
    if renamed:
        return dict(renamed)
    href = obj.get("detail_href") or ""
    slug = href.rstrip("/").rsplit("/", 1)[-1] if href else god_slug(name)
    icon = None
    if obj.get("icon_hash"):
        icon = f"https://images.smitebrain.com/images/items/icons/{slug}?v={obj['icon_hash']}"
    return {"name": name, "slug": slug, "icon": icon}


# SmiteBrain records a starter in whatever form it was in at match end, so
# base and evolved forms of one starter line split the vote. Merge by family
# and report the family with its most common recorded form.
STARTER_FAMILIES = {
    "leather cowl": "Leather Cowl line",
    "hunter's cowl": "Leather Cowl line",
    "leader's cowl": "Leather Cowl line",
    "bumba's cudgel": "Bumba's line",
    "bumba's hammer": "Bumba's line",
    "bumba's spear": "Bumba's line",
    "bluestone pendant": "Bluestone line",
    "bluestone brooch": "Bluestone line",
    "corrupted bluestone": "Bluestone line",
    "death's toll": "Death's Toll line",
    "death's embrace": "Death's Toll line",
    "death's temper": "Death's Toll line",
    "warrior's axe": "Warrior's Axe line",
    "sundering axe": "Warrior's Axe line",
    "hero's axe": "Warrior's Axe line",
    "sentinel's gift": "Sentinel's line",
    "sentinel's boon": "Sentinel's line",
    "sentinel's embrace": "Sentinel's line",
    "vampiric shroud": "Vampiric Shroud line",
    "blood-soaked shroud": "Vampiric Shroud line",
    "sacrificial shroud": "Vampiric Shroud line",
}


def aggregate(builds, role):
    starter_forms = {}
    starter_families = Counter()
    relics, aspects = Counter(), Counter()
    item_count = Counter()
    item_positions = {}
    item_objs = {}
    used = 0
    for b in builds:
        if not isinstance(b, dict):
            continue
        if role and str(b.get("played_role", "")).lower() != role.lower():
            continue
        used += 1
        starter = item_view(b.get("starter"))
        if starter:
            family = STARTER_FAMILIES.get(starter["name"].lower(), starter["name"])
            starter_families[family] += 1
            starter_forms.setdefault(family, Counter())[starter["name"]] += 1
            item_objs[starter["name"]] = starter
        for key, counter in (("relic", relics), ("aspect", aspects)):
            view = item_view(b.get(key))
            if view:
                counter[view["name"]] += 1
                item_objs[view["name"]] = view
        items = b.get("items") or {}
        if isinstance(items, dict):
            seen = set()
            for slot in range(1, 7):
                view = item_view(items.get(str(slot)))
                if not view or view["name"] in seen:
                    continue
                seen.add(view["name"])
                item_count[view["name"]] += 1
                item_positions.setdefault(view["name"], []).append(slot)
                item_objs[view["name"]] = view
    if used == 0:
        return None

    def top(counter):
        if not counter:
            return None
        name, count = counter.most_common(1)[0]
        view = dict(item_objs[name])
        view["count"] = count
        return view

    starter = None
    if starter_families:
        family, count = starter_families.most_common(1)[0]
        form = starter_forms[family].most_common(1)[0][0]
        starter = dict(item_objs[form])
        starter["name"] = form
        starter["family"] = family
        starter["count"] = count

    ranked = sorted(
        item_count.items(),
        key=lambda kv: (-kv[1], sum(item_positions[kv[0]]) / len(item_positions[kv[0]])),
    )
    ordered = []
    for name, count in ranked:
        view = dict(item_objs[name])
        view["count"] = count
        view["avg_slot"] = round(sum(item_positions[name]) / len(item_positions[name]), 1)
        ordered.append(view)
    # A build always fills all six slots: the six most played distinct
    # items, in typical buy order. Anything past the six is a flex swap.
    core = sorted(ordered[:6], key=lambda v: v["avg_slot"])
    flex = ordered[6:9]

    return {
        "sample": used,
        "starter": starter,
        "relic": top(relics),
        "aspect": top(aspects),
        "core": core,
        "flex": flex,
    }


def fetch_skills(god_display, role):
    """Skill order from SmiteSource, ability names from SmiteBrain.

    SmiteSource embeds its builds in the page payload, each with an
    abilityLevelOrder array. Pick the build for the requested role with
    the highest matchScore. Returns None when nothing usable is found.
    """
    import urllib.parse

    names = {}
    try:
        raw = fetch(f"{BASE}/gods/{god_slug(god_display)}/abilities/__data.json")
        payload = json.loads(raw)
        for node in payload.get("nodes", []):
            if not isinstance(node, dict) or node.get("type") != "data":
                continue
            data = node.get("data")
            if not isinstance(data, list) or not data:
                continue
            try:
                decoded = unflatten(data)
            except Exception:
                continue
            if isinstance(decoded, dict) and isinstance(decoded.get("abilities"), list):
                for ab in decoded["abilities"]:
                    if isinstance(ab, dict) and ab.get("kind") == "active":
                        names[ab.get("slot")] = ab.get("display_name")
                break
    except Exception:
        pass

    try:
        html = fetch("https://smitesource.com/builds?god="
                     + urllib.parse.quote(god_display.strip().title()))
    except Exception:
        return None
    text = html.replace('\\"', '"').replace("\\\\", "\\")
    records = []
    for m in re.finditer(r'"abilityLevelOrder":\[([0-9,]+)\]', text):
        ctx = text[max(0, m.start() - 4000):m.end() + 4000]
        roles_m = re.findall(r'"roles":\[([^\]]*)\]', ctx)
        roles = re.findall(r'"([A-Za-z ]+)"', roles_m[-1]) if roles_m else []
        score_m = re.findall(r'"matchScore":(\d+)', ctx)
        title_m = re.findall(r'"title":"([^"]{1,60})"', ctx)
        order = [int(x) for x in m.group(1).split(",") if x]
        if len(order) >= 10:
            records.append({
                "order": order,
                "roles": roles,
                "score": int(score_m[-1]) if score_m else 0,
                "title": title_m[0] if title_m else None,
            })
    if not records:
        return None

    wanted = (role or "").strip().lower()
    aliases = {"adc": {"adc", "carry"}, "carry": {"adc", "carry"}}
    wanted_set = aliases.get(wanted, {wanted}) if wanted else set()
    matched = [r for r in records
               if any(x.lower() in wanted_set for x in r["roles"])] if wanted else []
    pick = max(matched or records, key=lambda r: r["score"])
    order = pick["order"]

    def maxed_level(ab):
        seen = 0
        for i, v in enumerate(order, 1):
            if v == ab:
                seen += 1
                if seen == 5:
                    return i
        return 99

    max_order = sorted([1, 2, 3], key=maxed_level)
    return {
        "start": order[:4],
        "max_order": [{"slot": ab, "name": names.get(ab)} for ab in max_order],
        "ult_levels": [i for i, v in enumerate(order, 1) if v == 4],
        "source_title": pick["title"],
        "source_roles": pick["roles"],
    }


def current_patch(god):
    try:
        html = fetch(f"{BASE}/gods/{god}/builds")
    except Exception:
        return None
    m = re.search(r"Open Beta \d+", html)
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser(description="SmiteBrain build aggregator")
    ap.add_argument("god", help="God name or slug, e.g. thor or 'Da Ji'")
    ap.add_argument("--role", default=None,
                    help="Jungle, Solo, Mid, ADC (or Carry), Support")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    ap.add_argument("--compact", action="store_true",
                    help="Emit the chat-ready compact build")
    args = ap.parse_args()

    god = god_slug(args.god)
    role = args.role.strip().lower() if args.role else None
    role_path = {"adc": "adc", "carry": "adc"}.get(role, role)

    page = None
    source_url = None
    tried = []
    if role_path:
        tried.append(f"{BASE}/gods/{god}/builds/{role_path}/__data.json")
    tried.append(f"{BASE}/gods/{god}/builds/__data.json")
    for url in tried:
        try:
            page = decode_page(fetch(url))
        except Exception:
            page = None
        if page:
            source_url = url
            break
    if not page:
        print(f"No build data found for {god} on SmiteBrain.", file=sys.stderr)
        return 1

    result = aggregate(page["builds"], args.role)
    if not result:
        print(f"No {args.role or 'any-role'} builds in the recent sample for {god}.",
              file=sys.stderr)
        return 1

    result["god"] = god
    result["role"] = args.role
    result["patch"] = current_patch(god)
    result["source"] = source_url
    result["skills"] = fetch_skills(args.god, args.role)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if args.compact:
        def pair(view):
            if not view:
                return None
            return view["name"]

        god_name = " ".join(w.capitalize() for w in god.split("-"))
        role_name = (args.role or "All roles").capitalize()
        print(f"**{god_name} · {role_name}** · {result['patch'] or 'patch ?'}"
              f" · {result['sample']} top builds, hourly data")
        chain = [pair(result["starter"])] + [pair(v) for v in result["core"]]
        print(" → ".join(p for p in chain if p))
        bits = []
        if result["relic"]:
            bits.append(f"Relic: {result['relic']['name']}")
        if result["aspect"]:
            bits.append(f"Aspect: {result['aspect']['name']}")
        if result["flex"]:
            bits.append("Flex: " + ", ".join(v["name"] for v in result["flex"][:2]))
        if bits:
            print(" · ".join(bits))
        sk = result.get("skills")
        if sk:
            start = "-".join(str(x) for x in sk["start"])
            maxo = " > ".join(str(x["slot"]) for x in sk["max_order"])
            ult = "/".join(str(x) for x in sk["ult_levels"])
            print(f"Skills: start {start} · max {maxo} · ult {ult}")
        return 0

    def fmt(view):
        if not view:
            return "(none in sample)"
        return f"{view['name']} ({view['count']}/{result['sample']})"

    print(f"{god} - {args.role or 'all roles'} - {result['patch'] or 'patch unknown'}"
          f" - sample {result['sample']} top-player builds - {source_url}")
    starter = result["starter"]
    if starter:
        print(f"Starter: {starter['name']} [{starter['family']}]"
              f" ({starter['count']}/{result['sample']})")
    else:
        print("Starter: (none in sample)")
    print(f"Relic:   {fmt(result['relic'])}")
    print(f"Aspect:  {fmt(result['aspect'])}")
    print("Core (six most played, in typical buy order):")
    for i, view in enumerate(result["core"], 1):
        icon = f" icon={view['icon']}" if view.get("icon") else ""
        print(f"  {i}. {view['name']} ({view['count']}/{result['sample']}){icon}")
    if result["flex"]:
        print("Flex pool (next most common):")
        for view in result["flex"]:
            print(f"  - {view['name']} ({view['count']}/{result['sample']})")
    sk = result.get("skills")
    if sk:
        start = "-".join(str(x) for x in sk["start"])
        maxo = " > ".join(
            f"{x['name']} ({x['slot']})" if x.get("name") else str(x["slot"])
            for x in sk["max_order"])
        ult = "/".join(str(x) for x in sk["ult_levels"])
        print(f"Skills: start {start} · max {maxo} · ult {ult}"
              f" (SmiteSource: {sk.get('source_title')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
