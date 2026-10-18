# Private run format

Use `init` to create a private run under ignored `data/`. Configuration, sources and reports in that directory must not be committed. The public sample uses invented labels and amounts only.

## Configuration and approvals

Edit the private run's `config.json`. `accounts` accepts any number of unique `{id, name, status, full_review}` records. Status is `expected`, `received`, `no_activity` or `out_of_scope`; the last two require a nonempty `evidence` string and an empty ledger. Every configured ID has a ledger file. Add/change the private roster and ledger files together. Final reporting requires `inventory_approved: true` with `inventory_evidence` containing actual confirmation.

Money inputs are decimal strings with the configured `minor_unit_digits` (0-4). Thresholds use the same precision. The top-level `currency` is the default; an account can override it with `currency`. Define every additional code in `currency_settings` with explicit `minor_unit_digits`, `review_threshold` and `major_expense_threshold`. A row must match its account currency. Values from different currencies are never added and conversion is not automatic. Review and major thresholds are strict `>` comparisons in the account's currency. `locale` affects browser display only, not parsing or arithmetic; source dates and decimal input strings remain unambiguous ISO/decimal values.

`approvals.json` has this shape:

```json
{
  "accounts": {
    "daily-bank": {
      "classification_approved": false,
      "coverage_approved": false,
      "reconciliation_approved": false,
      "evidence": ""
    }
  },
  "accepted_limitations": []
}
```

Record a date and who approved what in `evidence`. A limitation is `{description, evidence}`. Setting flags is an assertion, not independent authentication of review. A contradictory source must remain visible even if a user accepts a limited report.

## Source intake

`intake.csv` columns: `source_file,account_id,statement_start,statement_end,notes`.

`source_file` is a nonempty relative path under `sources/`; absolute paths, traversal and symlink escapes are rejected. Preserve original sources unchanged and inspect every relevant transaction page. Statement cycles do not replace calendar-period transaction filtering. Source reconciliation must be recorded by the reviewing person/assistant; the helper does not read source PDFs to certify its truth.

## Account ledgers

One `ledgers/<account-id>.csv` per account, with these columns:

| Field | Meaning |
| --- | --- |
| `transaction_id` | Globally unique, stable account-qualified source reference |
| `transaction_date` | Evidenced date in ISO format, YYYY-MM-DD |
| `amount` | Unsigned decimal string, not a currency symbol or thousands-separated display value |
| `currency` | Must match the account's configured currency |
| `direction` | `debit` or `credit` |
| `raw_description` | Original source text |
| `cleaned_payee` | Verified grouping identity, not a guessed category |
| `transaction_type` | Evidence-supported type, e.g. purchase, credit_card_payment, linked_refund, loan_emi |
| `included` | `yes` for approved expense debits and linked expense credits, otherwise `no` |
| `emi` | `yes` only for actual loan/card installment debits, excluded from account expenses |
| `review_required` | `yes` adds a review even below threshold; automatic threshold/full-account rules still apply |
| `source_file` | Registered relative file path under sources/ |
| `source_row` | Page, row, serial or other source locator |
| `link_evidence` | Required for included credits and actual installments; exact link or approved merchant/period aggregate |
| `notes` | Missing independent date, accepted category limits or other evidence notes |

Credit refund types allowed to reduce expenses: `confirmed_refund`, `linked_refund`, `linked_reversal`, `linked_fee_reversal`. An unlinked merchant credit must be excluded. Direction supplies the sign; do not store negative amounts. For actual `loan_emi`/`card_emi`, set `included=no`, `emi=yes` and explain evidence. A source's EMI eligibility wording does not qualify.

## Reviews

Run `prepare-reviews` after extracting/editing rows. It writes required review IDs and a fingerprint of each complete source-normalized row to `reviews.csv`. Fill `decision=accepted`, `reviewer`, `reviewed_on` (ISO date), and decision notes only after review. Other decisions remain pending; change the ledger to reflect an approved exclusion, then prepare/review it again. Any row change makes its previous decision stale. No code auto-accepts reviews.

The helper requires every in-period amount strictly above the review threshold, every in-period row for a full-review account and every explicit in-period review flag. Stale/unmatched old review rows are not silently discarded.

## Reports and limitations

`report` writes `reports/spending-summary.md`, one `<account-id>.md`, `consolidated.csv`, `validation.json` and an offline `dashboard.html`. Reports are generated outputs, not source evidence. Account totals include all included in-period expenses, minus approved linked credits. EMI is counted separately once. Monthly totals reconcile within each currency. Special-review filters report their included contribution and gross movements per currency without adding anything again.

Validation JSON includes `totals_by_currency`, `emi_by_currency`, `monthly_by_currency` and `account_currencies`. For a single-currency run, scalar `period_total`, `emi_total` and `monthly` fields are available. For a mixed-currency run the scalar totals are null and `monthly` is empty; use the currency-separated fields. Never treat null as zero.

`INVALID` means structural/numeric errors. `DRAFT` means missing roster/reviews/approval. `FINAL_WITH_LIMITATIONS` retains separate credits or accepted source caveats. A machine pass does not prove that omitted source data never existed. Reports can be regenerated, so keep originals and private decision evidence separately.
