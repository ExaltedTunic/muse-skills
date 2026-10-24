# Financial Audit

Audit bills, spending, fees and debt deadlines from statement exports or Plaid data, and produce a plain Markdown report. This skill gathers the evidence; decisions about what to do with the findings (which debt to attack, whether a purchase is affordable, a payoff plan) belong to the `financial_planning` skill.

## When to use

- The user asks where the money went, wants bills or subscriptions audited, suspects overspending or fee creep, or needs debt and promo deadlines watched.
- As the recurring evidence step under a broader spending or debt review.

## Hard rules

- **Read only, always.** This skill never moves money, pays a bill, or changes an account, and it never asks to. Findings are reported; acting on them is a separate, explicitly approved step.
- **Credentials never pass through the agent.** Plaid linking happens only through the Plaid connector's own connect flow, completed by the user. Statement downloads happen in the user's own banking session. Never ask for, receive, or store bank logins.
- **Masked identities only.** Name accounts in words, with masked last digits when needed to tell them apart. Never print or repeat a full account, card or routing number, even if a statement file contains one. Transaction descriptions in the JSONL and the report can still carry numbers copied from the statement, so mask them whenever you quote a row.
- **Private data stays out of the skill folder.** Config, statements, JSONL, reports and summaries live in the user's private working folder, `~/workspace/finance/`. Never write them to `~/workspace/custom-skills/financial-audit/`. That separation is what makes the skill safe to share.

## Intake: pick what is available

1. **Statement CSV (cleanest, works everywhere).** The user exports CSV from online banking (TD EasyWeb, Scotiabank, and most Canadian banks offer a transactions download per account) and drops the files somewhere the agent can read. Copy them into `~/workspace/finance/` before ingesting.
2. **PDF statements (very common).** Two routes. Preferred: extract the text with `pdftotext -layout statement.pdf statement.txt` (or any text extraction the platform offers), then `ingest-text`. When text extraction mangles the layout, read the PDF directly and transcribe each transaction row into normalized JSONL yourself (see Hand transcription). Either way, reconcile before auditing: compare the parsed count and net movement against the statement's own opening and closing balances, and report the result.
3. **Screenshots and photos.** The user may send screenshots of a statement or an app's transaction list. Transcribe every visible row into normalized JSONL (see Hand transcription), note in the report that the source was a screenshot transcription, and reconcile against any totals visible in the image. Digits in images are easy to misread (0 and 8, 1 and 7) and rows can be cropped off, so treat screenshot audits as approximate: fine for spotting bills, fees and creep, not for exact debt math. Ask for a CSV or PDF when precision matters.
4. **Plaid (where offered).** Run `/opt/hatch/bin/plaid status`. If connected, pull the period with `transactions-get` into a JSON file in `~/workspace/finance/` and feed it to `ingest-plaid`. Plaid availability depends on the account's region: if `status` returns `connector_country_not_allowed`, do not retry it, fall back to statements. Follow the Plaid connector doc for its reads and its reporting rules.
5. **Never browse a bank as the agent.** Bank logins, MFA and identity checks are the user's to complete in their own session, every time.

## Workflow

1. Collect one statement file per account for the period. Note which accounts and dates the set covers; a missing account is unknown, not zero.
2. Ingest each file into normalized JSONL with a friendly account name.
3. Create or refresh `~/workspace/finance/config.json` from the skill's `config.example.json`: monthly category budgets, debts (balance, APR, minimum, and for deferred-interest promos the `promo_end` date and `promo_balance`), extra transfer-exclusion patterns, extra category keywords.
4. Run the audit. It writes a Markdown report and can write a JSON summary.
5. Present findings in plain language, in the order: cash flow, recurring bills total, price increases, fees, over-budget categories, debt deadlines, duplicates, large items. Check the raw rows behind any surprising number before presenting it, because merchant grouping is heuristic.

## Commands

Run every command from `~/workspace/finance/`, in the same shell call as the `cd`, and call the script by its full path. Relative file names then resolve inside the private folder, never the skill folder.

```
cd ~/workspace/finance && python3 ~/workspace/custom-skills/financial-audit/scripts/finance_audit.py ingest-csv statement.csv --account "TD Chequing" --out td.jsonl
cd ~/workspace/finance && python3 ~/workspace/custom-skills/financial-audit/scripts/finance_audit.py ingest-text statement.txt --account "Scotia Chequing" --year 2026 --out scotia.jsonl
cd ~/workspace/finance && python3 ~/workspace/custom-skills/financial-audit/scripts/finance_audit.py ingest-plaid plaid-transactions.json --out plaid.jsonl
cd ~/workspace/finance && python3 ~/workspace/custom-skills/financial-audit/scripts/finance_audit.py audit td.jsonl visa.jsonl --config config.json --out report.md --json-out summary.json
```

- `ingest-csv` auto-detects Debit/Credit column pairs or a single Amount column, and the common date formats. It reports how many rows were skipped; a high skip count means the export format differs, so inspect the file header before trusting output.
- `ingest-text` parses a plain-text statement dump (typically `pdftotext -layout` output). It reads lines that start with a date, takes trailing money columns as amount and running balance, and infers an amount's sign from the balance movement when the statement prints debits unsigned. It reports how many signs were inferred and how many rows could not be balance-checked; rows it cannot check deserve a spot-check against the statement before the audit is quoted.
- `ingest-plaid` takes the saved JSON from the Plaid connector's `transactions-get`, maps account names, flips Plaid's sign convention (positive means outflow), and skips pending rows.
- `audit` accepts several JSONL files at once, one per account, and merges them.

## Hand transcription

The PDF fallback and screenshot intake produce JSONL by hand, so it must match what the ingest commands write. The script defines that format. Before transcribing, copy the field names, date format and sign convention from a JSONL file the script already wrote, or from `scripts/finance_audit.py`, and match them exactly.

## What the audit checks

- **Monthly cash flow:** income, spending and net per month, with transfers between the user's own accounts and payments to their own cards excluded from both sides. Exclusion patterns ship with defaults (savings transfers, card payments, "payment thank you" lines) and the config extends them.
  - **Canadian Interac e-Transfer caution:** generic `E-TRANSFER` or `SEND E-TFR` lines look identical whether sent to a friend/merchant or to the user's own account at another bank. Never add a blanket regex that excludes all e-Transfers; only exclude specific self-transfer patterns configured in `config.json` or pairs that match an equal-and-opposite deposit in another ingested account file within the same window.
  - **Card payments need the card's statement:** payments to the user's own cards are excluded as transfers, so if a card's statement was not ingested, nothing charged to that card counts as spending. Name the missing card in the report and ask for its statement before treating spending as final.
- **Recurring bills and subscriptions:** merchants charged at least three times over at least 40 days with a stable amount (within 20 percent). Reports cadence, average, last charge and estimated monthly cost, plus the total.
- **Frequent variable spending:** merchants that recur with unstable amounts, such as groceries, listed separately so they never inflate the bills total.
- **Price increases:** recurring charges whose baseline was flat (first two charges equal) and whose latest charge rose more than 3 percent. The classic subscription creep pattern. Subscriptions billed in a foreign currency (USD software, for example) change in CAD every month with the exchange rate, so their first two charges rarely match and this check skips them. Review those by hand, and do not report an exchange-rate swing as a price increase.
- **Fees and interest:** every outflow matching fee or interest wording, totalled and itemized. Matching is word-boundary based so a transfer is never mistaken for an NSF fee and coffee is never a fee.
- **Category budgets:** spending grouped by keyword categories (defaults cover common Canadian merchants; the config adds more) against the config's monthly budgets, flagging each month over budget and by how much.
- **Debts and promo deadlines:** for each configured debt, the balance, the APR, the rough monthly interest cost and the minimum. For a promo balance with an end date, the days left and the monthly pace required to clear it before the deadline, which is the number that matters on deferred-interest plans.
- **Possible duplicates:** same merchant and amount within three days.
- **Large transactions:** outflows over the config threshold (default 500), largest first.

## Limits and honesty

- Merchant grouping and categorization are keyword heuristics. Two differently named charges can be one merchant, and one name can hide several. Verify before accusing a charge of being a duplicate or a bill of being dead.
- **Low-frequency bills and annual renewals:** Because the recurring-bill detector requires at least three charges over at least 40 days, a 1-to-3-month statement set will not automatically flag bi-monthly, quarterly (such as municipal water or property tax installments), or annual subscriptions. State this in the report whenever the statement window is under a year, and scan large or one-off software/service charges manually if the user is hunting for annual renewals.
- **Ambiguous e-Transfers:** If the statement shows large or frequent outgoing Interac e-Transfers without recipient names on the statement line, ask the user which ones are self-transfers versus real spending before treating net cash flow as final.
- **Real exports differ from fixtures:** The parsers were verified on synthetic fixtures only. On the first real file from each bank, check the skip count and reconcile against the statement before quoting any number.
- PDF and screenshot intake is transcription, however it is produced. Text extraction can scramble columns, and image transcription can misread digits. The reconciliation step (parsed totals against the statement's own balances) is what makes these routes trustworthy; skip it and the audit is a draft, so say so.
- Balances in the config are snapshots the user supplies; the audit does not fetch live balances. Plaid balances, where available, are last-reported and can lag the bank.
- A charge missing from the data means the statement set did not cover it, not that it does not exist. Every report states its period and accounts for this reason.
- This is bookkeeping, not financial advice. Tax, legal, investment and refinance questions go to the `financial_planning` skill's guidance and, where it says so, to a qualified professional.

## Sharing and fresh setup

- The bundle is this folder: `SKILL.md`, `skill.yaml`, `config.example.json`, and `scripts/finance_audit.py`. The script uses only the Python 3 standard library, so there is nothing to install.
- Setup: put the folder at `~/workspace/custom-skills/financial-audit/`, create `~/workspace/finance/`, copy `config.example.json` to `~/workspace/finance/config.json`, and fill in your budgets and debts. Then export one CSV from your bank into `~/workspace/finance/` and run `ingest-csv` and `audit`.
- Share the skill freely. Never share your config, your statements, or a generated report that contains your figures; those are the private part.

Last verified: 2026-10-21 on synthetic TD-format CSV, PDF-style text and Plaid JSON fixtures. Checked: monthly cash flow, transfer exclusion, recurring bills, subscription price increases, fee totals, duplicate detection, category budgets, promo payoff pace and balance-inferred amount signs.
