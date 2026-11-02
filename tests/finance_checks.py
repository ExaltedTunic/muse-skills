#!/usr/bin/env python3
"""Regression checks for the financial-audit skill (fix waves W1-W2).

Covers the behaviours verified in the earlier 45-check round (re-derived
from SKILL.md's "Last verified" list and the script's own comments), the
W1 fixes F01-F08 and the W2 fixes F1-F7 (second external review round:
subscription stream separation, refund evidence, indicator precedence,
description-column binding, Plaid currency, ingest/load validation and
debt-name masking). Stdlib only. Run:

    python3 finance_checks.py

Exit code 0 only when every check passes.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from datetime import date

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "skills", "finance", "financial-audit", "scripts", "finance_audit.py")
SKILL_DIR = os.path.dirname(os.path.dirname(SCRIPT))

spec = importlib.util.spec_from_file_location("finance_audit", SCRIPT)
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def expect(cond, detail=""):
    if not cond:
        raise AssertionError(detail or "expectation failed")


def T(day, desc, amount, account="TD Chequing", balance=None):
    return {"date": day, "description": desc,
            "merchant": fa.merchant_key(desc), "amount": amount,
            "balance": balance, "account": account}


def write_tmp(directory, name, text):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def ingest_csv_quiet(path, account="TD Chequing", **kw):
    err = io.StringIO()
    with redirect_stderr(err):
        out = fa.ingest_csv(path, account, **kw)
    return out, err.getvalue()


# ---------------------------------------------------------------- parsing

@case
def parse_date_iso_and_hints():
    expect(fa.parse_date("2026-01-05") == date(2026, 1, 5))
    expect(fa.parse_date("02/10/2026", "DMY") == date(2026, 10, 2))
    expect(fa.parse_date("02/10/2026", "MDY") == date(2026, 2, 10))
    expect(fa.parse_date("not a date") is None)


@case
def detect_slash_format():
    expect(fa.detect_slash_format(["25/12/2025", "03/01/2026"]) == "DMY")
    expect(fa.detect_slash_format(["12/25/2025", "01/03/2026"]) == "MDY")
    expect(fa.detect_slash_format(["01/02/2026"]) is None)


@case
def parse_date_leap_year():
    expect(fa.parse_date("29/02/2024", "DMY") == date(2024, 2, 29))


@case
def parse_amount_forms():
    expect(fa.parse_amount("$1,234.56") == 1234.56)
    expect(fa.parse_amount("(50.00)") == -50.0)
    expect(fa.parse_amount("-25.5") == -25.5)
    expect(fa.parse_amount("abc") is None)
    expect(fa.parse_amount("") is None)
    expect(fa.parse_amount(None) is None)


@case
def merchant_key_and_cadence():
    key = fa.merchant_key("POS PURCHASE TIM HORTONS #1234")
    expect("TIM HORTONS" in key, key)
    expect(fa.cadence_label(7) == "weekly")
    expect(fa.cadence_label(14) == "biweekly")
    expect(fa.cadence_label(30) == "monthly")
    expect(fa.cadence_label(90) == "quarterly")
    expect(fa.cadence_label(200) == "irregular")


@case
def money_units():
    expect(fa.money(-50) == "$50.00")           # legacy magnitude form
    expect(fa.money(1234.5) == "$1,234.50")
    expect(fa.money(None) == "n/a")
    expect(fa.money_signed(-50) == "-$50.00")
    expect(fa.money_signed(50) == "$50.00")
    expect(fa.money_signed(0) == "$0.00")


@case
def mask_text_keeps_last_two():
    masked = fa.mask_text("CARD 4111111111111111 PURCHASE")
    expect("4111111111111111" not in masked, masked)
    expect("***11" in masked, masked)
    grouped = fa.mask_text("ACCT 4111 1111 1111 1111")
    expect("4111 1111" not in grouped, grouped)


# ------------------------------------------------------------- CSV ingest

PAIR_CSV = ("Date,Description,Debit,Credit,Balance\n"
            "2026-01-05,GROCERY STORE,50.00,,950.00\n"
            "2026-01-06,PAYROLL,,1500.00,2450.00\n")


@case
def csv_debit_credit_pair():
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", PAIR_CSV))
    expect(len(out) == 2, str(out))
    expect(out[0]["amount"] == -50.0, str(out[0]))
    expect(out[1]["amount"] == 1500.0, str(out[1]))
    expect(out[0]["balance"] == 950.0)


@case
def csv_single_amount_column():
    text = ("Date,Description,Amount\n"
            "2026-01-05,GROCERY STORE,-50.00\n"
            "2026-01-06,PAYROLL,1500.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect([t["amount"] for t in out] == [-50.0, 1500.0], str(out))


@case
def csv_indicator_column():
    # One "Debit/Credit" indicator column plus an Amount column: the
    # indicator must drive the sign, not be read as two money columns.
    text = ("Date,Description,Debit/Credit,Amount\n"
            "2026-01-05,GROCERY STORE,DR,50.00\n"
            "2026-01-06,PAYROLL,CR,1500.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect([t["amount"] for t in out] == [-50.0, 1500.0], str(out))


@case
def csv_amount_with_type_column():
    text = ("Date,Description,Amount,Type\n"
            "2026-01-05,GROCERY STORE,50.00,DR\n"
            "2026-01-06,PAYROLL,1500.00,CR\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(out[0]["amount"] == -50.0, str(out))
    expect(out[1]["amount"] == 1500.0, str(out))


@case
def csv_skip_accounting():
    text = ("Date,Description,Amount\n"
            "2026-01-05,GROCERY STORE,-50.00\n"
            "not-a-date,BAD ROW,10.00\n"
            "2026-01-07,COFFEE,-6.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, err = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(len(out) == 2, str(out))
    expect("skipped 1 rows" in err, err)


@case
def csv_slash_dates_inferred_dmy():
    text = ("Date,Description,Amount\n"
            "25/12/2025,GIFT SHOP,-25.00\n"
            "03/01/2026,GROCERY STORE,-40.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(out[0]["date"] == "2025-12-25", str(out))
    expect(out[1]["date"] == "2026-01-03", str(out))


@case
def csv_transaction_headers_bind():
    text = ("Transaction Date,Transaction Details,Amount\n"
            "2026-01-05,GROCERY STORE,-50.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(len(out) == 1 and out[0]["description"] == "GROCERY STORE",
           str(out))


@case
def csv_invert_amounts():
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", PAIR_CSV),
                                  invert_amounts=True)
    expect(out[0]["amount"] == 50.0, str(out))
    expect(out[1]["amount"] == -1500.0, str(out))


# ------------------------------------------------------------ text ingest

TEXT_STMT = ("Statement\n"
             "BEGINNING BALANCE $1,000.00\n"
             "Jan 5, 2026 GROCERY STORE 100.00 900.00\n"
             "Jan 6, 2026 PAYROLL DEPOSIT 500.00 1,400.00\n")


@case
def text_ingest_balance_inferred_sign():
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "s.txt", TEXT_STMT)
        err = io.StringIO()
        with redirect_stderr(err):
            out = fa.ingest_text(path, "Scotia Chequing", 2026)
    expect(len(out) == 2, str(out))
    expect(out[0]["amount"] == -100.0, str(out[0]))   # unsigned, balance fell
    expect(out[1]["amount"] == 500.0, str(out[1]))
    expect("1 signs inferred" in err.getvalue(), err.getvalue())


@case
def text_ingest_leap_day_month_name():
    text = ("OPENING BALANCE 1,000.00\n"
            "Feb 29 GROCERY STORE 25.00 975.00\n")
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "s.txt", text)
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_text(path, "Scotia Chequing", 2024)
    expect(len(out) == 1 and out[0]["date"] == "2024-02-29", str(out))
    expect(out[0]["amount"] == -25.0, str(out))


@case
def text_ingest_date_line_forms():
    text = ("Jan 5, 2026 STORE A 10.00\n"
            "5 Jan 2026 STORE B 20.00\n"
            "2026-01-07 STORE C 30.00\n")
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "s.txt", text)
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_text(path, "Scotia Chequing", 2026)
    dates = sorted(t["date"] for t in out)
    expect(dates == ["2026-01-05", "2026-01-05", "2026-01-07"], str(out))


@case
def text_ingest_three_amount_line():
    # Debit, credit, balance columns: amount is credit minus debit.
    text = "2026-01-05 PAYROLL ACME 100.00 200.00 1,200.00\n"
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "s.txt", text)
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_text(path, "Scotia Chequing", 2026)
    expect(len(out) == 1 and out[0]["amount"] == 100.0, str(out))
    expect(out[0]["balance"] == 1200.0, str(out))


@case
def text_ingest_unformatted_amount():
    text = "2026-01-05 BIG PURCHASE 1234.56\n"
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "s.txt", text)
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_text(path, "Scotia Chequing", 2026)
    expect(len(out) == 1 and out[0]["amount"] == 1234.56, str(out))


# ----------------------------------------------------------- plaid ingest

@case
def plaid_ingest_signs_pending_names():
    payload = {
        "accounts": [{"account_id": "a1", "name": "Chequing"}],
        "transactions": [
            {"account_id": "a1", "date": "2026-01-05",
             "name": "Grocery Store", "amount": 50.0, "pending": False},
            {"account_id": "a1", "date": "2026-01-06",
             "name": "Payroll", "amount": -1500.0, "pending": False},
            {"account_id": "a1", "date": "2026-01-07",
             "name": "Pending Thing", "amount": 10.0, "pending": True},
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "p.json", json.dumps(payload))
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_plaid(path)
    expect(len(out) == 2, str(out))
    expect(out[0]["amount"] == -50.0, str(out[0]))    # Plaid + means outflow
    expect(out[1]["amount"] == 1500.0, str(out[1]))
    expect(out[0]["account"] == "Chequing", str(out[0]))


# ------------------------------------------------------------------ audit

@case
def audit_monthly_cash_flow():
    txns = [T("2026-01-05", "PAYROLL", 2000.0),
            T("2026-01-06", "LOBLAWS", -200.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["income"] == 2000.0, str(jan))
    expect(jan["spending"] == 200.0, str(jan))
    expect(s["period"] == ["2026-01-05", "2026-01-06"], str(s["period"]))
    expect(s["transaction_count"] == 2)


@case
def audit_transfer_exclusion():
    txns = [T("2026-01-05", "PAYROLL", 2000.0),
            T("2026-01-06", "PAYMENT - THANK YOU", -500.0),
            T("2026-01-07", "TRANSFER TO SAVINGS", -300.0),
            T("2026-01-08", "LOBLAWS", -100.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["spending"] == 100.0, str(jan))
    expect(jan["income"] == 2000.0, str(jan))
    expect(jan["transfers"] == 800.0, str(jan))


@case
def audit_generic_etransfer_is_spending():
    txns = [T("2026-01-05", "SEND E-TFR TO FRIEND", -75.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(s["monthly"]["2026-01"]["spending"] == 75.0, str(s["monthly"]))


@case
def audit_refund_offsets_spending():
    txns = [T("2026-01-05", "STORE XYZ", -100.0),
            T("2026-01-20", "STORE XYZ REFUND", 100.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["spending"] == 0.0, str(jan))
    expect(jan["income"] == 0.0, str(jan))


@case
def audit_payroll_is_income_not_refund():
    txns = [T("2026-01-05", "ACME PAYROLL", 2000.0),
            T("2026-01-06", "LOBLAWS", -50.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(s["monthly"]["2026-01"]["income"] == 2000.0, str(s["monthly"]))


@case
def audit_fees_word_boundary():
    txns = [T("2026-01-05", "NSF FEE", -45.0),
            T("2026-01-06", "COFFEE SHOP", -6.0),
            T("2026-01-07", "MONTHLY SERVICE CHARGE", -10.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(s["fees_total"] == 55.0, str(s["fees_total"]))
    expect(len(s["fees"]) == 2, str(s["fees"]))


@case
def audit_categories_word_boundary():
    txns = [T("2026-01-05", "METROLINX", -25.0),
            T("2026-01-06", "TACO BELL", -12.0),
            T("2026-01-07", "BELL MOBILITY", -60.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    cats = s["categories"]
    expect(cats["other"]["2026-01"] == 25.0, str(cats))     # not transport
    expect(cats["dining"]["2026-01"] == 12.0, str(cats))    # phrase wins
    expect(cats["telecom"]["2026-01"] == 60.0, str(cats))


@case
def audit_category_budgets():
    cfg = {"budgets": {"groceries": 100}}
    txns = [T("2026-01-05", "LOBLAWS", -150.0)]
    s = fa.audit(txns, cfg, as_of="2026-01-31")
    expect(len(s["over_budget"]) == 1, str(s["over_budget"]))
    ob = s["over_budget"][0]
    expect(ob["category"] == "groceries" and ob["over"] == 50.0, str(ob))


@case
def audit_recurring_stable_monthly():
    txns = [T("2026-01-01", "NETFLIX", -15.99),
            T("2026-01-31", "NETFLIX", -15.99),
            T("2026-03-02", "NETFLIX", -15.99)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    expect(len(s["recurring"]) == 1, str(s["recurring"]))
    r = s["recurring"][0]
    expect(r["cadence"] == "monthly", str(r))
    expect(r["monthly_cost"] == 16.22, str(r))   # 15.99 * 30.44 / 30
    expect(r["count"] == 3, str(r))


@case
def audit_frequent_variable_separate():
    txns = [T("2026-01-01", "LOBLAWS", -80.0),
            T("2026-01-31", "LOBLAWS", -120.0),
            T("2026-03-02", "LOBLAWS", -95.0)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    expect(not s["recurring"], str(s["recurring"]))
    expect(len(s["frequent_variable"]) == 1, str(s["frequent_variable"]))


@case
def audit_creep_outside_stability_gate():
    # 10, 10, 15 is "unstable" by the ratio test, so the merchant lands
    # in frequent_variable; the creep check must still flag the hike.
    txns = [T("2026-01-01", "STREAMIO", -10.0),
            T("2026-01-31", "STREAMIO", -10.0),
            T("2026-03-02", "STREAMIO", -15.0)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    expect(len(s["price_increases"]) == 1, str(s["price_increases"]))
    c = s["price_increases"][0]
    expect(c["from"] == 10.0 and c["to"] == 15.0, str(c))


@case
def audit_creep_stable_series():
    txns = [T("2026-01-01", "MUSIC APP", -10.0),
            T("2026-01-31", "MUSIC APP", -10.0),
            T("2026-03-02", "MUSIC APP", -11.0)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    expect(len(s["price_increases"]) == 1, str(s["price_increases"]))
    expect(s["price_increases"][0]["pct"] == 10.0, str(s["price_increases"]))
    expect(len(s["recurring"]) == 1, str(s["recurring"]))


@case
def audit_same_day_charges_stay_recurring():
    txns = [T("2026-01-01", "HOSTING CO", -10.0),
            T("2026-01-01", "HOSTING CO", -10.0),
            T("2026-01-31", "HOSTING CO", -10.0),
            T("2026-03-02", "HOSTING CO", -10.0)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    expect(len(s["recurring"]) == 1, str(s["recurring"]))
    expect(s["recurring"][0]["cadence"] == "monthly", str(s["recurring"]))


@case
def audit_duplicates_within_three_days():
    txns = [T("2026-01-05", "STREAMIO", -10.0),
            T("2026-01-07", "STREAMIO", -10.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(len(s["possible_duplicates"]) == 1, str(s["possible_duplicates"]))


@case
def audit_large_transactions_threshold():
    txns = [T("2026-01-05", "BIG TV PURCHASE", -600.0),
            T("2026-01-06", "COFFEE", -5.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(len(s["large_transactions"]) == 1, str(s["large_transactions"]))
    expect(s["large_transactions"][0]["amount"] == -600.0)


@case
def audit_output_masking():
    txns = [T("2026-01-05", "PURCHASE CARD 4111111111111111", -900.0,
              account="TD Chequing 12345678")]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    desc = s["large_transactions"][0]["description"]
    expect("4111111111111111" not in desc, desc)
    expect("***11" in desc, desc)
    expect("12345678" not in " ".join(s["accounts"]), str(s["accounts"]))
    expect("***78" in " ".join(s["accounts"]), str(s["accounts"]))


@case
def audit_debt_interest_math():
    cfg = {"debts": [{"name": "Card", "balance": 2400.0, "apr": 0.2099,
                      "min_payment": 60}]}
    s = fa.audit([], cfg, as_of="2026-10-01")
    d = s["debts"][0]
    expect(d["monthly_interest"] == 41.98, str(d))  # 2400*.2099/12
    expect(d["min_payment"] == 60, str(d))


@case
def audit_promo_pace_explicit_as_of():
    # The pre-F01 behaviour, reproduced by passing the evaluation date
    # explicitly: it equals the statement's last transaction date.
    cfg = {"debts": [{"name": "Store promo", "balance": 650.0,
                      "promo_balance": 650.0, "promo_end": "2026-02-01"}]}
    txns = [T("2026-01-01", "LOBLAWS", -10.0)]
    s = fa.audit(txns, cfg, as_of="2026-01-01")
    d = s["debts"][0]
    expect(d["days_left"] == 31, str(d))
    expect(d["required_monthly"] == round(650.0 / (31 / 30.44), 2), str(d))
    expect(s["as_of"] == "2026-01-01", str(s["as_of"]))


@case
def audit_promo_passed_note():
    cfg = {"debts": [{"name": "Old promo", "balance": 300.0,
                      "promo_balance": 300.0, "promo_end": "2026-01-01"}]}
    s = fa.audit([], cfg, as_of="2026-02-01")
    d = s["debts"][0]
    expect(d["days_left"] < 0, str(d))
    expect(d["required_monthly"] is None, str(d))
    expect(d.get("note") == "promo end date has passed", str(d))


@case
def audit_empty_no_debts_report():
    s = fa.audit([], {}, as_of="2026-10-01")
    expect(s["period"] == [] and s["transaction_count"] == 0)
    report = fa.render_report(s, "CAD")
    expect("No transactions in period" in report, report)


@case
def audit_report_renders_sections():
    txns = [T("2026-01-01", "NETFLIX", -15.99),
            T("2026-01-31", "NETFLIX", -15.99),
            T("2026-03-02", "NETFLIX", -15.99),
            T("2026-03-05", "NSF FEE", -45.0)]
    s = fa.audit(txns, {}, as_of="2026-03-31")
    report = fa.render_report(s, "CAD")
    for needle in ("# Financial audit, 2026-01-01 to 2026-03-05",
                   "## Monthly cash flow", "## Recurring bills",
                   "## Fees and interest", "## Spending by category",
                   "Total recurring monthly cost: $16.22"):
        expect(needle in report, f"missing {needle!r} in report")


# ------------------------------------------------------- W1 fixes F01-F08

@case
def f01_default_evaluation_date_is_today():
    cfg = {"debts": [{"name": "Promo", "balance": 900.0,
                      "promo_balance": 900.0, "promo_end": "2027-06-01"}]}
    txns = [T("2026-01-01", "LOBLAWS", -10.0)]
    s = fa.audit(txns, cfg)
    expected = (date(2027, 6, 1) - date.today()).days
    expect(s["debts"][0]["days_left"] == expected,
           f"days_left {s['debts'][0]['days_left']} != {expected}")
    expect(s["as_of"] == date.today().isoformat(), str(s["as_of"]))
    expect(s["statement_as_of"] == "2026-01-01", str(s.get("statement_as_of")))


@case
def f01_header_shows_both_dates():
    cfg = {"debts": [{"name": "Promo", "balance": 900.0,
                      "promo_balance": 900.0, "promo_end": "2026-03-01"}]}
    txns = [T("2026-01-31", "LOBLAWS", -10.0)]
    s = fa.audit(txns, cfg, as_of="2026-01-01")
    expect(s["debts"][0]["days_left"] == 59, str(s["debts"][0]))
    report = fa.render_report(s, "CAD")
    expect("figures are as of 2026-01-31" in report, report[:400])
    expect("Deadlines evaluated as of 2026-01-01" in report, report[:400])


@case
def f01_cli_as_of():
    cfg = {"debts": [{"name": "Promo", "balance": 650.0,
                      "promo_balance": 650.0, "promo_end": "2026-02-01"}]}
    with tempfile.TemporaryDirectory() as td:
        txns_path = write_tmp(td, "txns.jsonl",
                              json.dumps(T("2026-01-01", "LOBLAWS", -10.0))
                              + "\n")
        cfg_path = write_tmp(td, "config.json", json.dumps(cfg))
        out_path = os.path.join(td, "summary.json")
        proc = subprocess.run(
            [sys.executable, SCRIPT, "audit", txns_path, "--config",
             cfg_path, "--as-of", "2026-01-01", "--json-out", out_path],
            capture_output=True, text=True)
        expect(proc.returncode == 0, proc.stderr)
        with open(out_path, encoding="utf-8") as fh:
            summary = json.load(fh)
    expect(summary["debts"][0]["days_left"] == 31, str(summary["debts"]))
    expect(summary["as_of"] == "2026-01-01", str(summary["as_of"]))


@case
def f02_promo_balance_zero_is_real():
    cfg = {"debts": [{"name": "Zero promo", "balance": 1000.0,
                      "promo_balance": 0, "promo_end": "2026-12-01"},
                     {"name": "Fallback promo", "balance": 1000.0,
                      "promo_end": "2026-12-01"}]}
    s = fa.audit([], cfg, as_of="2026-10-01")
    zero, fallback = s["debts"]
    expect(zero["days_left"] == 61, str(zero))
    expect(zero["required_monthly"] == 0, str(zero))
    expect(fallback["required_monthly"]
           == round(1000.0 / (61 / 30.44), 2), str(fallback))
    expect(fallback["required_monthly"] > 0, str(fallback))


@case
def f03_debts_render_with_no_transactions():
    cfg = {"debts": [{"name": "Store card promo", "balance": 1000.0,
                      "apr": 0.2999, "promo_balance": 500.0,
                      "promo_end": "2026-12-01"}]}
    s = fa.audit([], cfg, as_of="2026-10-01")
    report = fa.render_report(s, "CAD")
    expect("No transactions in period" in report, report)
    expect("## Debts and promo deadlines" in report, report)
    expect("Store card promo" in report, report)
    expect("61 days left" in report, report)
    expect("balance $1,000.00" in report, report)


@case
def f04_signed_rendering_in_tables():
    txns = [T("2026-01-05", "STORE XYZ", -50.0),
            T("2026-01-20", "STORE XYZ REFUND", 100.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    expect(s["monthly"]["2026-01"]["spending"] == -50.0, str(s["monthly"]))
    report = fa.render_report(s, "CAD")
    expect("| 2026-01 | $0.00 | -$50.00 | $50.00 |" in report, report)
    expect("| other | 2026-01 | -$50.00 |" in report, report)
    # Inherently non-negative cells keep the old unsigned look.
    expect("| 2026-01 | $0.00 |" in report, report)


@case
def f05_parallel_subscriptions_total_outflow():
    txns = []
    for day in ("2026-08-01", "2026-09-01", "2026-10-01"):
        txns.append(T(day, "STREAMIO", -10.0, account="Account A"))
        txns.append(T(day, "STREAMIO", -10.0, account="Account B"))
    s = fa.audit(txns, {}, as_of="2026-10-31")
    expect(len(s["recurring"]) == 1, str(s["recurring"]))
    cost = s["recurring"][0]["monthly_cost"]
    expect(19.9 <= cost <= 20.05, f"monthly_cost {cost}")
    # Single-subscription control: the estimate is unchanged.
    single = [T(day, "STREAMIO", -10.0)
              for day in ("2026-08-01", "2026-09-01", "2026-10-01")]
    s2 = fa.audit(single, {}, as_of="2026-10-31")
    cost2 = s2["recurring"][0]["monthly_cost"]
    expect(9.9 <= cost2 <= 10.05, f"single monthly_cost {cost2}")


@case
def f06_config_categories_take_precedence():
    with open(os.path.join(SKILL_DIR, "config.example.json"),
              encoding="utf-8") as fh:
        example = json.load(fh)
    txns = [T("2026-01-05", "YMCA MEMBERSHIP", -50.0),
            T("2026-01-06", "TACO BELL", -12.0)]
    s = fa.audit(txns, example, as_of="2026-01-31")
    cats = s["categories"]
    expect(cats.get("gym", {}).get("2026-01") == 50.0, str(cats))
    expect("health" not in cats, str(cats))
    expect(cats.get("dining", {}).get("2026-01") == 12.0, str(cats))
    # Control: with no config the same charge is built-in "health".
    s2 = fa.audit(txns[:1], {}, as_of="2026-01-31")
    expect(s2["categories"].get("health", {}).get("2026-01") == 50.0,
           str(s2["categories"]))


@case
def f07_withdrawals_deposits_headers():
    text = ("Date,Description,Withdrawals,Deposits\n"
            "2026-01-05,GROCERY STORE,50.00,\n"
            "2026-01-06,PAYROLL,,1500.00\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(len(out) == 2, str(out))
    expect(out[0]["amount"] == -50.0, str(out[0]))
    expect(out[1]["amount"] == 1500.0, str(out[1]))


@case
def f08_nonfinite_amounts_rejected():
    expect(fa.parse_amount("NaN") is None)
    expect(fa.parse_amount("inf") is None)
    expect(fa.parse_amount("-Infinity") is None)
    expect(fa.parse_amount("(NaN)") is None)
    text = ("Date,Description,Amount\n"
            "2026-01-05,GROCERY STORE,-50.00\n"
            "2026-01-06,WEIRD ROW,NaN\n"
            "2026-01-07,INF ROW,inf\n")
    with tempfile.TemporaryDirectory() as td:
        out, err = ingest_csv_quiet(write_tmp(td, "s.csv", text))
        expect(len(out) == 1, str(out))
        expect("skipped 2 rows" in err, err)
        jsonl_path = os.path.join(td, "out.jsonl")
        fa.write_jsonl(out, jsonl_path)
        with open(jsonl_path, encoding="utf-8") as fh:
            body = fh.read()
    expect("NaN" not in body and "Infinity" not in body, body)
    for line in body.splitlines():
        json.loads(line)  # strict parse: raises on invalid JSON


# ------------------------------------------------------- W2 fixes F1-F7

@case
def w2_f1_staggered_streams_sum_to_total():
    # Two $10 subscriptions at one merchant billed on the 1st and 2nd of
    # each month. Pooling the charge dates gives gaps 1,30,1,29,1, a
    # 1-day median, a "weekly" cadence and $304.40/month. The charges
    # must be separated into two monthly streams and summed: ~$20.
    txns = []
    for day in ("2026-08-01", "2026-08-02", "2026-09-01", "2026-09-02",
                "2026-10-01", "2026-10-02"):
        txns.append(T(day, "STREAMIO", -10.0))
    s = fa.audit(txns, {}, as_of="2026-10-31")
    expect(len(s["recurring"]) == 1, str(s["recurring"]))
    r = s["recurring"][0]
    expect(r["cadence"] == "monthly", str(r))
    expect(19.5 <= r["monthly_cost"] <= 20.5, str(r))
    expect(r["count"] == 6, str(r))


@case
def w2_f1_incoherent_stream_falls_back_irregular():
    # One stream whose gaps are wildly inconsistent (32 then 119 days)
    # must not be extrapolated from its median interval. The fallback
    # is a window estimate: total charged over the calendar months
    # covered, cadence "irregular".
    txns = [T("2026-01-01", "STREAMIO", -30.0),
            T("2026-02-02", "STREAMIO", -30.0),
            T("2026-06-01", "STREAMIO", -30.0)]
    s = fa.audit(txns, {}, as_of="2026-06-30")
    expect(len(s["recurring"]) == 1, str(s["recurring"]))
    r = s["recurring"][0]
    expect(r["cadence"] == "irregular", str(r))
    expect(r["monthly_cost"] == 30.0, str(r))   # 90 over Jan, Feb, Jun


@case
def w2_f2_etransfer_inflow_is_income():
    # Merchant equality alone is not refund evidence: a $100 outflow
    # cannot corroborate a $2,000 inflow at the same "merchant".
    txns = [T("2026-01-05", "E-TRANSFER", -100.0),
            T("2026-01-06", "E-TRANSFER", 2000.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["income"] == 2000.0, str(jan))
    expect(jan["spending"] == 100.0, str(jan))


@case
def w2_f2_genuine_return_with_evidence_is_refund():
    # No refund keyword, but a same-merchant earlier outflow of equal
    # amount within 90 days corroborates the return.
    txns = [T("2026-01-05", "STORE XYZ", -50.0),
            T("2026-01-20", "STORE XYZ", 50.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["spending"] == 0.0, str(jan))
    expect(jan["income"] == 0.0, str(jan))


@case
def w2_f2_inflow_above_prior_outflow_is_income():
    # The corroborating outflow must be at least the inflow's amount.
    txns = [T("2026-01-05", "STORE XYZ", -50.0),
            T("2026-01-20", "STORE XYZ", 80.0)]
    s = fa.audit(txns, {}, as_of="2026-01-31")
    jan = s["monthly"]["2026-01"]
    expect(jan["income"] == 80.0, str(jan))
    expect(jan["spending"] == 50.0, str(jan))


@case
def w2_f2_stale_outflow_is_not_evidence():
    # Corroboration expires: an outflow more than 90 days earlier does
    # not make a later same-merchant inflow a refund.
    txns = [T("2026-01-05", "STORE XYZ", -50.0),
            T("2026-06-20", "STORE XYZ", 50.0)]
    s = fa.audit(txns, {}, as_of="2026-06-30")
    expect(s["monthly"]["2026-06"]["income"] == 50.0, str(s["monthly"]))


@case
def w2_f3_indicator_beats_type_column():
    # An explicit Debit/Credit indicator column decides the sign even
    # when a separate Transaction Type column exists; "CARD" in the
    # type column must not leave a DR row positive.
    text = ("Date,Description,Debit/Credit,Amount,Transaction Type\n"
            "2026-01-05,GROCERY,DR,50.00,CARD\n"
            "2026-01-06,PAYROLL,CR,1500.00,CARD\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect([t["amount"] for t in out] == [-50.0, 1500.0], str(out))


@case
def w2_f4_merchant_column_wins_over_transaction_type():
    # "Transaction Type" is a kind column, not the description: the
    # merchant must come from the Merchant column, not the POS value.
    text = ("Date,Transaction Type,Merchant,Amount\n"
            "2026-01-05,POS,LOBLAWS,-50\n")
    with tempfile.TemporaryDirectory() as td:
        out, _ = ingest_csv_quiet(write_tmp(td, "s.csv", text))
    expect(len(out) == 1, str(out))
    expect(out[0]["description"] == "LOBLAWS", str(out[0]))
    expect(out[0]["merchant"] == "LOBLAWS", str(out[0]))
    expect(out[0]["amount"] == -50.0, str(out[0]))


@case
def w2_f5_plaid_currency_preserved_and_split():
    payload = {
        "accounts": [
            {"account_id": "cad1", "name": "CAD Chequing",
             "iso_currency_code": "CAD"},
            {"account_id": "usd1", "name": "USD Chequing",
             "iso_currency_code": "USD"}],
        "transactions": [
            {"account_id": "cad1", "date": "2026-01-05", "name": "STORE A",
             "amount": 100.0, "iso_currency_code": "CAD", "pending": False},
            {"account_id": "usd1", "date": "2026-01-06", "name": "STORE B",
             "amount": 100.0, "iso_currency_code": "USD", "pending": False},
            # No transaction currency: falls back to the account's.
            {"account_id": "usd1", "date": "2026-01-07", "name": "STORE C",
             "amount": 50.0, "pending": False}],
    }
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "p.json", json.dumps(payload))
        with redirect_stderr(io.StringIO()):
            out = fa.ingest_plaid(path)
    expect([t.get("currency") for t in out] == ["CAD", "USD", "USD"],
           str(out))
    s = fa.audit(out, {}, as_of="2026-01-31")
    by_cur = s["monthly_by_currency"]
    expect(by_cur["CAD"]["2026-01"]["spending"] == 100.0, str(by_cur))
    expect(by_cur["USD"]["2026-01"]["spending"] == 150.0, str(by_cur))
    # The headline monthly table is the configured currency only; the
    # USD amounts must not be folded into it.
    expect(s["monthly"]["2026-01"]["spending"] == 100.0, str(s["monthly"]))
    report = fa.render_report(s, "CAD")
    expect("Currencies CAD, USD" in report, report[:500])
    expect("## Monthly cash flow (USD)" in report, report)
    # Single-currency control: shape and rendering are unchanged.
    single = [T("2026-01-05", "LOBLAWS", -100.0)]
    s2 = fa.audit(single, {}, as_of="2026-01-31")
    expect(s2["monthly_by_currency"] == {"CAD": s2["monthly"]},
           str(s2["monthly_by_currency"]))
    report2 = fa.render_report(s2, "CAD")
    expect("Currency CAD." in report2, report2[:400])
    expect("## Monthly cash flow\n" in report2, report2)


@case
def w2_f6_plaid_nonfinite_amounts_skipped():
    payload = {
        "accounts": [{"account_id": "a1", "name": "Chequing"}],
        "transactions": [
            {"account_id": "a1", "date": "2026-01-05", "name": "WEIRD ROW",
             "amount": "NaN", "pending": False},
            {"account_id": "a1", "date": "2026-01-06", "name": "INF ROW",
             "amount": float("inf"), "pending": False},
            {"account_id": "a1", "date": "2026-02-05", "name": "PAYROLL",
             "amount": -500.0, "pending": False}],
    }
    with tempfile.TemporaryDirectory() as td:
        path = write_tmp(td, "p.json", json.dumps(payload))
        err = io.StringIO()
        with redirect_stderr(err):
            out = fa.ingest_plaid(path)
        expect(len(out) == 1, str(out))
        expect(out[0]["amount"] == 500.0, str(out[0]))
        expect("2 invalid" in err.getvalue(), err.getvalue())
        jsonl_path = os.path.join(td, "out.jsonl")
        fa.write_jsonl(out, jsonl_path)
        with open(jsonl_path, encoding="utf-8") as fh:
            body = fh.read()
    expect("NaN" not in body and "Infinity" not in body, body)
    for line in body.splitlines():
        json.loads(line)  # strict parse
    # A non-finite record can never be serialized, even hand-built.
    try:
        fa.write_jsonl([{"date": "2026-01-05", "amount": float("nan")}],
                       None)
    except ValueError:
        pass
    else:
        raise AssertionError("write_jsonl serialized a NaN amount")


def _expect_systemexit(fn, needle):
    try:
        fn()
    except SystemExit as exc:
        expect(needle in str(exc), f"{needle!r} not in {exc!r}")
        return
    raise AssertionError(f"expected SystemExit mentioning {needle!r}")


@case
def w2_f6_jsonl_loader_validates_records():
    good = json.dumps(T("2026-01-05", "LOBLAWS", -10.0))
    bad_date = json.dumps({**T("2026-01-05", "BAD DATE", -10.0),
                           "date": "not-a-date"})
    missing = json.dumps({k: v for k, v in
                          T("2026-01-05", "NO AMOUNT", -10.0).items()
                          if k != "amount"})
    nan_amount = ('{"date": "2026-01-05", "description": "NAN ROW", '
                  '"merchant": "NAN ROW", "amount": NaN, "balance": null, '
                  '"account": "Chequing"}')
    with tempfile.TemporaryDirectory() as td:
        ok_path = write_tmp(td, "ok.jsonl", good + "\n")
        expect(len(fa.load_jsonl(ok_path)) == 1)
        _expect_systemexit(
            lambda: fa.load_jsonl(write_tmp(td, "d.jsonl", bad_date + "\n")),
            "line 1")
        _expect_systemexit(
            lambda: fa.load_jsonl(write_tmp(td, "m.jsonl", missing + "\n")),
            "line 1")
        _expect_systemexit(
            lambda: fa.load_jsonl(write_tmp(td, "n.jsonl",
                                            good + "\n" + nan_amount + "\n")),
            "line 2")
        # The CLI fails the same way, with the line number on stderr.
        proc = subprocess.run(
            [sys.executable, SCRIPT, "audit",
             write_tmp(td, "m2.jsonl", missing + "\n")],
            capture_output=True, text=True)
        expect(proc.returncode != 0, proc.stdout)
        expect("line 1" in proc.stderr, proc.stderr)


@case
def w2_f7_debt_name_masked_everywhere():
    cfg = {"debts": [{"name": "Store Card 4111111111111111",
                      "balance": 1000.0, "apr": 0.1999,
                      "min_payment": 50}]}
    txns = [T("2026-01-05", "LOBLAWS", -10.0)]
    s = fa.audit(txns, cfg, as_of="2026-01-31")
    name = s["debts"][0]["name"]
    expect("4111111111111111" not in name, name)
    expect("***11" in name, name)
    report = fa.render_report(s, "CAD")
    expect("4111111111111111" not in report, report)
    expect("Store Card ***11" in report, report)


# ------------------------------------------------------------------ runner

def main():
    failures = 0
    for fn in CASES:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL  {fn.__name__}  -- {type(exc).__name__}: {exc}")
        else:
            print(f"PASS  {fn.__name__}")
    total = len(CASES)
    print(f"\n{total - failures}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
