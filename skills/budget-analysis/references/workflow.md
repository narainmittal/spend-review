# Repeatable workflow

## Intake

Agree the period, currency, minor-unit precision, review/major thresholds and the complete account roster in private configuration. `accounts` is an arbitrary-length list, not a fixed set of banks. Account IDs are safe slugs; display names are user-defined. Mark missing expected accounts as expected, not zero. `no_activity` or `out_of_scope` requires decision evidence in the account configuration.

Copy original files unchanged to the private run's `sources/` and record each in `intake.csv`. Record printed cycles separately from transaction dates. Obtain prior/following statements around period boundaries or explicit no-spending confirmations for exact gaps. Approval alone cannot override contradictory source evidence. Never reverse-engineer purchases from cashback tables.

## Extraction and reconciliation

Accounts can use different currencies. Define explicit precision and review/major thresholds for every additional currency in `currency_settings`, and optionally assign `currency` per account. Preserve the statement's currency; never infer it from an ambiguous symbol. Keep per-currency totals, special reviews and actual installments separate. No exchange-rate conversion or mixed-currency scalar total is generated. `locale` controls only dashboard display formatting.

Inspect every transaction page, continuation, wrapped description and credit indicator. Preserve `source_file`, `source_row`, `raw_description`, `transaction_date`, positive `amount` and debit/credit direction. Keep out-of-period rows for reconciliation; they contribute zero to the report. `source_file` is relative to `sources/`, never an absolute private path. Keep a stable account-qualified `transaction_id`; repeated amount/date alone is not proof of duplication.

For savings accounts, check every signed balance change. For cards, check purchase totals, credit totals and opening + debits - credits = closing. Record evidence and exceptions in `approvals.json`; the helper cannot verify source arithmetic from ledgers alone. Terms examples, reward points, cashback earning breakdowns and previous balances are not posted expenses.

## Classification and review

Ledger fields are defined in `docs/DATA_FORMAT.md`. Amounts are unsigned; credits get their negative sign during reporting. Mark actual included spending with `included=yes`. A confirmed refund also has `included=yes`, an approved credit type and `link_evidence`; it reduces spending once. Unlinked credits must have `included=no`. Never infer linkage just from equal amounts or similar merchants.

Configured excluded types are not expenses. Genuine installments use `loan_emi` or `card_emi`, `included=no`, `emi=yes`, and evidence of the actual installment. EMI eligibility is not sufficient. Reversed transfers affect their exact original movement, not a different account's similarly sized transaction. Cash spending must have its own evidence.

Run `prepare-reviews` to list every in-period amount strictly over the review threshold, every account configured for full review, and every `review_required=yes` item. It preserves existing decisions and flags stale rows after input changes. Present date, raw description, direction, amount and proposed treatment. Record the user's decision, reviewer, date and evidence; do not auto-approve.

Special reviews are arbitrary named filters in configuration. A filter may scope account IDs, match `description_regex`, or match `transaction_types`. Matches do not establish a refund link or category. Report included signed spending separately from gross debit/credit movements and never add a special-review total a second time to expenses. For personal transfers, distinguish external flows from matching internal appearances. Uncertain spelling or truncated references remain uncertain.

## Account approval

For each account, record explicit `classification_approved`, `coverage_approved`, `reconciliation_approved` and supporting evidence in private `approvals.json`. Keep any accepted limitations in the same file. Display gross charges, applied refunds, expense total, EMI, separate credits, major verified payee groups and complete review rows. Approval of a partial report is not full period coverage.

## Consolidation

The helper validates roster equality, source registration, safe file references, unique IDs, explicit review signatures, credit linkage, exclusions, precision and date boundaries. It computes signed contributions with Decimal and emits per-account reports, account totals, monthly totals, special-review results, a consolidated ledger and a final/draft summary. It does not OCR PDFs, authenticate a user assertion, match every transfer automatically or prove that a review was actually done.

Final requires no numeric/structural errors, explicit roster approval, signed required reviews and all required account approvals. Accepted source limitations remain visible in a final recorded-spending report; do not call it fully refund-adjusted if unmatched credits remain. Missing approvals produce draft, not fabricated zero spending. A later account reopens the analysis and supersedes old outputs. Never overwrite original source files.

## Privacy and reuse

The report helper also produces a self-contained offline dashboard with currency, account and month filters, payee/account grouping, a donut or signed bars and transaction drill-down. Exact sums use integer minor units in the browser. Never discard negative refund-adjusted groups to make a pie chart work. Real dashboards embed transaction data and remain private; public chart examples and social screenshots must be synthetic. Public workflow diagrams may show the process, not real account data.

Keep real records and passwords out of the public toolkit and release archive. Upload statements only to a service/account whose privacy controls the user accepts. Model output requires review. Example data must be synthetic from scratch, not redacted real transactions. No financial recommendation, tax opinion, savings-rate claim or budget variance is implied by a spending summary.
