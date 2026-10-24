#!/usr/bin/env python3
"""Financial audit from statement exports. Read-only: this tool never touches
a bank, it only reads files the user supplies.

Usage:
    finance_audit.py ingest-csv statement.csv [--account "TD Chequing"] [--out txns.jsonl] [--date-format DMY|MDY]
    finance_audit.py ingest-text statement.txt [--account "TD Chequing"] [--year 2026] [--out txns.jsonl] [--date-format DMY|MDY]
    finance_audit.py ingest-plaid plaid-transactions.json [--out txns.jsonl]
    finance_audit.py audit txns.jsonl [more.jsonl ...] --config config.json [--out report.md] [--json-out summary.json]

Normalized transaction: {"date", "description", "merchant", "amount"
(negative = money out, positive = money in), "balance", "account"}.
"""
import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y",
                "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%m/%d/%y"]
FEE_RE = re.compile(r"\b(INTEREST|FEE|FEES|NSF|OVERLIMIT|OVERDRAFT|"
                    r"SERVICE CHARGE|CASH ADVANCE|ANNUAL FEE)\b", re.I)
DEFAULT_EXCLUDE = ["TRANSFER TO SAVINGS", "CREDIT CARD PAYMENT",
                   "PAYMENT - THANK YOU", "PAYMENT TO VISA",
                   "PAYMENT TO MASTERCARD",
                   r"ONLINE BANKING PAYMENT.*(VISA|MASTERCARD)"]
DEFAULT_CATEGORIES = {
    "groceries": ["LOBLAWS", "SOBEYS", "METRO", "FOOD BASICS", "NO FRILLS",
                  "FRESHCO", "WALMART", "COSTCO", "SUPERSTORE", "FARM BOY",
                  "BULK BARN", "M&M FOOD"],
    "dining": ["TIM HORTONS", "MCDONALD", "STARBUCKS", "SUBWAY", "PIZZA",
               "RESTAURANT", "UBER EATS", "DOORDASH", "SKIPTHEDISHES",
               "BARBURRITO", "SWISS CHALET", "KEG"],
    "telecom": ["ROGERS", "BELL", "TELUS", "FIDO", "KOODO", "VIRGIN PLUS",
                "FREEDOM MOBILE"],
    "subscriptions": ["NETFLIX", "SPOTIFY", "APPLE.COM", "APPLE SERVICES",
                      "GOOGLE", "AMAZON PRIME", "DISNEY", "YOUTUBE",
                      "XBOX", "PLAYSTATION", "NINTENDO"],
    "transport": ["PETRO", "SHELL", "ESSO", "PIONEER", "UBER", "LYFT",
                  "PRESTO", "PARKING"],
    "housing": ["RENT", "MORTGAGE", "ENBRIDGE", "HYDRO", "ALECTRA",
                "UNION GAS"],
    "health": ["SHOPPERS DRUG", "REXALL", "PHARMACY", "DENTAL", "YMCA",
               "GOODLIFE"],
}
STOP_TOKENS = {"INC", "LTD", "THE", "PURCHASE", "POS", "DEBIT", "VISA",
               "MASTERCARD", "WWW", "COM", "STORE", "PAYMENT", "INTERAC"}


def parse_date(text, date_format=None):
    """Parse a statement date. Slash dates are ambiguous (02/10/2026 is
    Feb 10 in MDY and Oct 2 in DMY), so callers that read a whole file
    first infer the file's convention with detect_slash_format and pass
    it as date_format ("DMY" or "MDY"); a matching format is tried first.
    Without a hint the historical DATE_FORMATS order applies."""
    text = (text or "").strip()
    formats = list(DATE_FORMATS)
    hinted = {"DMY": "%d/%m/%Y", "MDY": "%m/%d/%Y"}.get(
        (date_format or "").upper())
    if hinted and hinted in formats:
        formats.remove(hinted)
        formats.insert(0, hinted)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def detect_slash_format(values):
    """Infer DMY vs MDY for one file from its slash dates: a component
    above 12 settles it. Returns "DMY", "MDY", or None when every date
    in the file is ambiguous."""
    saw_dmy = saw_mdy = False
    for value in values:
        parts = (value or "").strip().split("/")
        if len(parts) != 3:
            continue
        try:
            first, second = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if first > 12:
            saw_dmy = True
        if second > 12:
            saw_mdy = True
    if saw_dmy and not saw_mdy:
        return "DMY"
    if saw_mdy and not saw_dmy:
        return "MDY"
    return None


def parse_amount(text):
    if text is None:
        return None
    text = str(text).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def merchant_key(description):
    cleaned = re.sub(r"[^A-Za-z0-9 ]", " ", (description or "").upper())
    tokens = [t for t in cleaned.split()
              if t not in STOP_TOKENS and not t.isdigit() and len(t) > 1]
    return " ".join(tokens[:5]) or cleaned.strip()[:24]


def find_col(headers, *needles):
    for i, header in enumerate(headers):
        low = header.lower()
        if any(n in low for n in needles):
            return i
    return None


def _cell(row, idx):
    """Ragged-row safe cell access: short rows read as empty, not IndexError."""
    if idx is None or idx >= len(row):
        return ""
    return row[idx]


def ingest_csv(path, account, date_format=None):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header_idx = None
    for i, row in enumerate(rows[:15]):
        joined = " ".join(row).lower()
        if "date" in joined and ("debit" in joined or "credit" in joined
                                  or "amount" in joined):
            header_idx = i
            break
    if header_idx is None:
        raise SystemExit("error: could not find a statement header row "
                         "(need Date plus Debit/Credit or Amount columns)")
    headers = rows[header_idx]
    date_i = find_col(headers, "date")
    desc_i = find_col(headers, "description", "transaction", "details", "name")
    debit_i = find_col(headers, "debit", "withdrawal")
    credit_i = find_col(headers, "credit", "deposit")
    amount_i = find_col(headers, "amount")
    type_i = find_col(headers, "type")
    balance_i = find_col(headers, "balance")
    if not date_format:
        date_format = detect_slash_format(
            _cell(r, date_i) for r in rows[header_idx + 1:])
    out, skipped = [], 0
    for row in rows[header_idx + 1:]:
        if len(row) <= (date_i or 0) or not row[date_i].strip():
            continue
        day = parse_date(row[date_i], date_format)
        if day is None:
            skipped += 1
            continue
        if debit_i is not None or credit_i is not None:
            debit = parse_amount(_cell(row, debit_i)) if debit_i is not None else None
            credit = parse_amount(_cell(row, credit_i)) if credit_i is not None else None
            if debit is None and credit is None:
                skipped += 1
                continue
            amount = (credit or 0) - abs(debit or 0)
        elif amount_i is not None:
            amount = parse_amount(_cell(row, amount_i))
            if amount is None:
                skipped += 1
                continue
            if type_i is not None:
                kind = _cell(row, type_i).strip().upper()
                if kind in ("DR", "DEBIT", "WITHDRAWAL"):
                    amount = -abs(amount)
        else:
            raise SystemExit("error: no Debit/Credit or Amount column found")
        description = _cell(row, desc_i).strip() if desc_i is not None else ""
        out.append({
            "date": day.isoformat(), "description": description,
            "merchant": merchant_key(description), "amount": round(amount, 2),
            "balance": parse_amount(_cell(row, balance_i)) if balance_i is not None else None,
            "account": account,
        })
    print(f"ingested {len(out)} transactions, skipped {skipped} rows",
          file=sys.stderr)
    return out


MONEY_TOKEN = re.compile(r"^-?\(?\$?\d{1,3}(?:,\d{3})*\.\d{2}\)?$"
                         r"|^-?\$[\d,]+(?:\.\d{2})?$"
                         r"|^-?\d{1,3}(?:,\d{3})+$")
DATE_LINE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})\b\s*(.*)$")


def _fix_years(rows, year, date_format=None):
    """Assign years to month-name dates, rolling over Dec into Jan."""
    current, prev_month, out = year, None, []
    for day_text, rest in rows:
        parsed = None
        for fmt in ("%b %d",):
            try:
                parsed = datetime.strptime(day_text, fmt).date()
            except ValueError:
                pass
        if parsed is None:
            out.append((parse_date(day_text, date_format), rest))
            continue
        if prev_month is not None and parsed.month < prev_month - 6:
            current += 1
        prev_month = parsed.month
        out.append((date(current, parsed.month, parsed.day), rest))
    return out


def ingest_text(path, account, year, date_format=None):
    """Best-effort parse of a plain-text statement dump, such as the output
    of `pdftotext -layout statement.pdf out.txt`. Amount signs are taken as
    printed when marked, and otherwise inferred from the running balance."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    opening_balance = None
    raw = []
    for line in lines:
        match = DATE_LINE.match(line)
        if not match:
            # An OPENING BALANCE line often carries no leading date, so the
            # date filter below would drop it and the first transaction's
            # sign could not be balance-checked. Capture its amount here.
            stripped = line.strip()
            if stripped.upper().startswith("OPENING BALANCE"):
                tokens = stripped.split()
                while tokens:
                    value = parse_amount(tokens.pop())
                    if value is not None:
                        opening_balance = value
                        break
            continue
        day_text, rest = match.group(1), match.group(2).strip()
        second = DATE_LINE.match(rest)  # posting-date column
        if second:
            rest = second.group(2).strip()
        tokens = rest.split()
        amounts = []
        while tokens and MONEY_TOKEN.match(tokens[-1]):
            value = parse_amount(tokens.pop())
            if value is None:
                break
            amounts.insert(0, value)
        if not amounts:
            continue
        raw.append((day_text, " ".join(tokens), amounts))
    if not date_format:
        date_format = detect_slash_format(d for d, _, _ in raw)
    dated = _fix_years([(d, (desc, amts)) for d, desc, amts in raw], year,
                       date_format)
    out, prev_balance, inferred, uninferred = [], opening_balance, 0, 0
    for day, (description, amounts) in dated:
        if day is None:
            continue
        upper_desc = description.upper()
        if upper_desc.startswith("OPENING BALANCE"):
            if amounts:
                prev_balance = amounts[-1]
            continue
        if upper_desc.startswith("CLOSING BALANCE"):
            continue
        if len(amounts) >= 3:
            amount = amounts[1] - amounts[0]
            balance = amounts[2]
        elif len(amounts) == 2:
            amount, balance = amounts
        else:
            amount, balance = amounts[0], None
        if balance is not None and prev_balance is not None \
                and len(amounts) == 2:
            delta = round(balance - prev_balance, 2)
            if abs(abs(delta) - abs(amount)) < 0.011:
                if (delta < 0) != (amount < 0):
                    inferred += 1
                amount = delta if delta else amount
            else:
                uninferred += 1
        if balance is not None:
            prev_balance = balance
        out.append({"date": day.isoformat(), "description": description,
                    "merchant": merchant_key(description),
                    "amount": round(amount, 2), "balance": balance,
                    "account": account})
    print(f"ingested {len(out)} transactions from text "
          f"({inferred} signs inferred from balance, {uninferred} rows "
          "could not be balance-checked)", file=sys.stderr)
    return out


def ingest_plaid(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    body = data.get("body", data)
    names = {}
    for acct in body.get("accounts", []):
        key = (acct.get("_plaid_source", {}).get("credential_id"),
               acct.get("account_id"))
        names[key] = acct.get("name") or acct.get("official_name") or "Account"
    out, pending = [], 0
    for txn in body.get("transactions", []):
        if txn.get("pending"):
            pending += 1
            continue
        key = (txn.get("_plaid_source", {}).get("credential_id"),
               txn.get("account_id"))
        description = txn.get("merchant_name") or txn.get("name") or ""
        out.append({
            "date": txn.get("date"), "description": description,
            "merchant": merchant_key(description),
            "amount": round(-float(txn.get("amount", 0)), 2),
            "balance": None, "account": names.get(key, "Plaid account"),
        })
    print(f"ingested {len(out)} Plaid transactions, skipped {pending} pending",
          file=sys.stderr)
    return out


def write_jsonl(txns, path):
    text = "".join(json.dumps(t) + "\n" for t in txns)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


def cadence_label(days):
    if days <= 9:
        return "weekly"
    if days <= 18:
        return "biweekly"
    if days <= 40:
        return "monthly"
    if days <= 100:
        return "quarterly"
    return "irregular"


def audit(txns, config):
    txns = sorted(txns, key=lambda t: t["date"])
    as_of = date.fromisoformat(txns[-1]["date"]) if txns else date.today()
    exclude_res = [re.compile(p, re.I) for p in
                   DEFAULT_EXCLUDE + config.get("exclude_patterns", [])]
    categories = {k: [w.upper() for w in v] for k, v in
                  DEFAULT_CATEGORIES.items()}
    for name, words in config.get("categories", {}).items():
        categories[name] = [w.upper() for w in words]
    budgets = config.get("budgets", {})
    threshold = config.get("large_threshold", 500)

    def is_transfer(t):
        return any(r.search(t["description"]) for r in exclude_res)

    def category_of(t):
        upper = t["description"].upper()
        for name, words in categories.items():
            if any(w in upper for w in words):
                return name
        return "other"

    monthly = defaultdict(lambda: {"income": 0.0, "spending": 0.0,
                                    "transfers": 0.0})
    fees, cat_month = [], defaultdict(float)
    outflows = []
    for t in txns:
        month = t["date"][:7]
        if is_transfer(t):
            monthly[month]["transfers"] += abs(t["amount"])
            continue
        if t["amount"] > 0:
            monthly[month]["income"] += t["amount"]
        elif t["amount"] < 0:
            monthly[month]["spending"] += -t["amount"]
            outflows.append(t)
            cat_month[(category_of(t), month)] += -t["amount"]
            if FEE_RE.search(t["description"]):
                fees.append(t)

    groups = defaultdict(list)
    for t in outflows:
        groups[t["merchant"]].append(t)
    recurring, frequent_variable, creep = [], [], []
    for merchant, items in groups.items():
        if len(items) < 3:
            continue
        days = [date.fromisoformat(i["date"]) for i in items]
        span = (max(days) - min(days)).days
        if span < 40:
            continue
        gaps = [(b - a).days for a, b in zip(sorted(days), sorted(days)[1:])]
        interval = statistics.median(gaps) if gaps else 0
        if not interval:
            continue
        amounts = [-i["amount"] for i in items]
        avg = statistics.mean(amounts)
        entry = {"merchant": merchant, "count": len(items),
                 "cadence": cadence_label(interval),
                 "average": round(avg, 2), "last": round(amounts[-1], 2),
                 "last_date": items[-1]["date"],
                 "monthly_cost": round(avg * 30.44 / interval, 2)}
        stable = min(amounts) > 0 and max(amounts) / min(amounts) <= 1.2
        if stable:
            recurring.append(entry)
            # A price increase only means something on a charge whose
            # baseline was flat, such as a subscription.
            first = amounts[0]
            if len(amounts) >= 3 and amounts[1] == first and first > 0 \
                    and amounts[-1] > first * 1.03:
                creep.append({"merchant": merchant, "from": round(first, 2),
                              "to": round(amounts[-1], 2),
                              "pct": round((amounts[-1] - first) / first
                                           * 100, 1),
                              "first_date": items[0]["date"],
                              "last_date": items[-1]["date"]})
        else:
            frequent_variable.append(entry)
    recurring.sort(key=lambda r: -r["monthly_cost"])
    frequent_variable.sort(key=lambda r: -r["monthly_cost"])

    ordered = sorted(outflows, key=lambda t: (t["merchant"], t["amount"],
                                              t["date"]))
    duplicates = []
    for a, b in zip(ordered, ordered[1:]):
        if a["merchant"] == b["merchant"] and a["amount"] == b["amount"]:
            gap = abs((date.fromisoformat(b["date"])
                       - date.fromisoformat(a["date"])).days)
            if gap <= 3:
                duplicates.append({"merchant": a["merchant"],
                                   "amount": a["amount"], "dates": [a["date"],
                                                                    b["date"]]})
    large = sorted(outflows, key=lambda t: t["amount"])[:10]
    large = [{"date": t["date"], "description": t["description"],
              "amount": t["amount"]} for t in large
             if -t["amount"] >= threshold]

    debts = []
    for d in config.get("debts", []):
        entry = {"name": d["name"], "balance": d.get("balance"),
                 "apr": d.get("apr"),
                 "monthly_interest": round(d["balance"] * d["apr"] / 12, 2)
                 if d.get("balance") and d.get("apr") else None,
                 "min_payment": d.get("min_payment")}
        if d.get("promo_end"):
            end = date.fromisoformat(d["promo_end"])
            days_left = (end - as_of).days
            entry["promo_end"] = d["promo_end"]
            entry["days_left"] = days_left
            promo_balance = d.get("promo_balance") or d.get("balance")
            if days_left > 0 and promo_balance:
                entry["required_monthly"] = round(
                    promo_balance / (days_left / 30.44), 2)
            elif days_left <= 0:
                entry["required_monthly"] = None
                entry["note"] = "promo end date has passed"
        debts.append(entry)

    cat_summary = {}
    for (cat, month), total in sorted(cat_month.items()):
        cat_summary.setdefault(cat, {})[month] = round(total, 2)
    over_budget = []
    for cat, budget in budgets.items():
        for month, total in cat_summary.get(cat, {}).items():
            if total > budget:
                over_budget.append({"category": cat, "month": month,
                                    "spent": total, "budget": budget,
                                    "over": round(total - budget, 2)})

    return {
        "as_of": as_of.isoformat(),
        "accounts": sorted({t["account"] for t in txns if t.get("account")}),
        "period": [txns[0]["date"], txns[-1]["date"]] if txns else [],
        "transaction_count": len(txns),
        "monthly": {m: {k: round(v, 2) for k, v in vals.items()}
                    for m, vals in sorted(monthly.items())},
        "fees_total": round(sum(-t["amount"] for t in fees), 2),
        "fees": [{"date": t["date"], "description": t["description"],
                  "amount": t["amount"]} for t in fees],
        "recurring": recurring, "frequent_variable": frequent_variable,
        "price_increases": creep,
        "categories": cat_summary, "budgets": budgets,
        "over_budget": over_budget,
        "possible_duplicates": duplicates, "large_transactions": large,
        "debts": debts,
    }


def money(value):
    return f"${abs(value):,.2f}" if isinstance(value, (int, float)) else "n/a"


def money_signed(value):
    """money() with the sign kept: for values that can be negative, such
    as a month's net, where stripping the sign would print a deficit as
    a surplus."""
    if not isinstance(value, (int, float)):
        return "n/a"
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def render_report(s, currency):
    if not s["period"]:
        return "# Financial audit\n\nNo transactions in period.\n"
    lines = [f"# Financial audit, {s['period'][0]} to {s['period'][1]}",
             "",
             f"Currency {currency}. Covers {s['transaction_count']} "
             f"transactions from {', '.join(s['accounts']) or 'statements'}. "
             f"Figures are as of {s['as_of']}. Own-account transfers and card "
             "payments are excluded from income and spending.", "",
             "## Monthly cash flow", "",
             "| Month | Income | Spending | Net | Moved between own accounts |",
             "|---|---|---|---|---|"]
    for month, v in s["monthly"].items():
        net = v["income"] - v["spending"]
        lines.append(f"| {month} | {money(v['income'])} | "
                     f"{money(v['spending'])} | {money_signed(net)} | "
                     f"{money(v['transfers'])} |")
    lines += ["", "## Recurring bills and subscriptions", "",
              "| Merchant | Cadence | Average | Last | Monthly cost |",
              "|---|---|---|---|---|"]
    for r in s["recurring"]:
        lines.append(f"| {r['merchant']} | {r['cadence']} | "
                     f"{money(r['average'])} | {money(r['last'])} "
                     f"({r['last_date']}) | {money(r['monthly_cost'])} |")
    lines.append(f"\nTotal recurring monthly cost: "
                 f"{money(sum(r['monthly_cost'] for r in s['recurring']))}")
    if s.get("frequent_variable"):
        lines += ["", "## Frequent variable spending (not fixed bills)", "",
                  "| Merchant | Times | Average | Rough monthly |",
                  "|---|---|---|---|"]
        for r in s["frequent_variable"]:
            lines.append(f"| {r['merchant']} | {r['count']} | "
                         f"{money(r['average'])} | "
                         f"{money(r['monthly_cost'])} |")
    if s["price_increases"]:
        lines += ["", "## Price increases on recurring charges", ""]
        for c in s["price_increases"]:
            lines.append(f"- {c['merchant']}: {money(c['from'])} on "
                         f"{c['first_date']} to {money(c['to'])} on "
                         f"{c['last_date']} (+{c['pct']}%)")
    lines += ["", "## Fees and interest", "",
              f"Total in period: {money(s['fees_total'])}", ""]
    for f in s["fees"]:
        lines.append(f"- {f['date']} | {f['description']} | "
                     f"{money(f['amount'])}")
    lines += ["", "## Spending by category", "",
              "| Category | Month | Spent | Budget | Over by |",
              "|---|---|---|---|---|"]
    budgets_hit = {(o["category"], o["month"]): o for o in s["over_budget"]}
    for cat, months in s["categories"].items():
        for month, total in months.items():
            over = budgets_hit.get((cat, month))
            budget = s.get("budgets", {}).get(cat)
            lines.append(f"| {cat} | {month} | {money(total)} | "
                         f"{money(budget) if budget else ''} | "
                         f"{money(over['over']) if over else ''} |")
    if s["debts"]:
        lines += ["", "## Debts and promo deadlines", ""]
        for d in s["debts"]:
            line = (f"- {d['name']}: balance {money(d['balance'])}"
                    + (f", APR {d['apr'] * 100:.2f}%" if d.get("apr") else "")
                    + (f", about {money(d['monthly_interest'])} interest a "
                       "month" if d.get("monthly_interest") else "")
                    + (f", minimum {money(d['min_payment'])}"
                       if d.get("min_payment") else ""))
            if d.get("promo_end"):
                line += (f". Promo ends {d['promo_end']} "
                         f"({d['days_left']} days left)"
                         + (f", needs {money(d['required_monthly'])} a month "
                            "to clear in time"
                            if d.get("required_monthly") else "")
                         + (f". {d['note']}" if d.get("note") else ""))
            lines.append(line)
    if s["possible_duplicates"]:
        lines += ["", "## Possible duplicate charges", ""]
        for d in s["possible_duplicates"]:
            lines.append(f"- {d['merchant']}: {money(d['amount'])} on "
                         f"{d['dates'][0]} and {d['dates'][1]}")
    if s["large_transactions"]:
        lines += ["", "## Large transactions", ""]
        for t in s["large_transactions"]:
            lines.append(f"- {t['date']} | {t['description']} | "
                         f"{money(t['amount'])}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Financial audit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_csv = sub.add_parser("ingest-csv")
    p_csv.add_argument("file")
    p_csv.add_argument("--account", default="Statement account")
    p_csv.add_argument("--out")
    p_csv.add_argument("--date-format", choices=["DMY", "MDY"], default=None,
                       help="Slash-date convention for this file; default "
                            "infers it per file from unambiguous dates")

    p_text = sub.add_parser("ingest-text")
    p_text.add_argument("file")
    p_text.add_argument("--account", default="Statement account")
    p_text.add_argument("--year", type=int, default=date.today().year)
    p_text.add_argument("--out")
    p_text.add_argument("--date-format", choices=["DMY", "MDY"], default=None,
                        help="Slash-date convention for this file; default "
                             "infers it per file from unambiguous dates")

    p_plaid = sub.add_parser("ingest-plaid")
    p_plaid.add_argument("file")
    p_plaid.add_argument("--out")

    p_audit = sub.add_parser("audit")
    p_audit.add_argument("files", nargs="+")
    p_audit.add_argument("--config")
    p_audit.add_argument("--out")
    p_audit.add_argument("--json-out")

    args = parser.parse_args()
    if args.command == "ingest-csv":
        write_jsonl(ingest_csv(args.file, args.account, args.date_format),
                    args.out)
    elif args.command == "ingest-text":
        write_jsonl(ingest_text(args.file, args.account, args.year,
                                args.date_format), args.out)
    elif args.command == "ingest-plaid":
        write_jsonl(ingest_plaid(args.file), args.out)
    elif args.command == "audit":
        config = {}
        if args.config:
            with open(args.config, encoding="utf-8") as fh:
                config = json.load(fh)
        txns = []
        for path in args.files:
            with open(path, encoding="utf-8") as fh:
                txns += [json.loads(line) for line in fh if line.strip()]
        summary = audit(txns, config)
        report = render_report(summary, config.get("currency", "CAD"))
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
