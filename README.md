# Spend Review

**Turn your bank and credit-card statements into a personal spending report you can check.**

![Spend Review: personal budgeting and expense analysis](docs/assets/banner.svg)

Give your preferred AI assistant the workflow and your statements. It helps organize the transactions, flags questions for you to review, and saves account-by-account analyses. Local Python tools check the saved records and create a consolidated report and interactive charts.

**This is a guided workflow, not a bank-connected app or a one-click statement parser.** Your assistant reads the documents using its available tools; you approve uncertain transactions and account coverage. The helper does not extract arbitrary statements for you.

## What can I do with it?

| Feature | What you get |
| --- | --- |
| Flexible periods | Monthly, quarterly, half-yearly, yearly or custom-date analysis |
| Any account roster | As many bank accounts and credit cards as needed |
| Your preferred assistant | Model-neutral instructions for capable hosted assistants, local LLMs and coding agents |
| Statement reviews | PDFs, spreadsheets and images through your assistant's tools; missing or unreadable data stays visible |
| Configurable review limits | Inspect individual transactions above one threshold; highlight aggregated major payees above another. Smaller included expenses still count |
| Reviewed classifications | Separate expenses, linked refunds, transfers, card settlements, investments and actual installments |
| Special investigations | Review a merchant, selected accounts or personal transfers in and out |
| Multiple currencies | Separate totals, decimal precision and thresholds per currency; no guessed exchange rates |
| Interactive charts | Offline donut charts or signed bars, account/month filters and transaction drill-downs |
| Saved evidence | Source references, ledgers, review decisions, one analysis per account and a consolidated summary |

## 1. Try the demo first

**No installation, login or bank statement is needed.**

1. On GitHub, choose **Code → Download ZIP**, then unzip it. If you already have the release ZIP, unzip that instead.
2. Open **`examples/synthetic/dashboard.html`** in your browser.
3. Try the account and month filters, switch the chart type, and click a spending group to see its transactions.

The demo contains invented data only. Its total is **USD 1,350.00**, including USD 200.00 of actual installments. An unmatched credit is disclosed separately, not guessed to be a refund.

[Demo dashboard file](examples/synthetic/dashboard.html) · [Workflow diagram](docs/assets/workflow.svg)

GitHub shows HTML files as source code. Download the folder and open the dashboard locally to use it; no hosted website is required.

## 2. Analyze your own statements with an assistant

**Recommended starting point. You do not need to edit code.**

### Give the assistant the workflow

Open a new conversation or workspace in an assistant you trust with financial documents. Attach the downloaded project ZIP if it can read ZIP files. Otherwise attach these three files individually:

- [START_HERE.md](START_HERE.md): instructions for guiding your analysis.
- [Workflow guide](skills/budget-analysis/references/workflow.md): the review and reconciliation process.
- [config.example.json](config.example.json): available settings, not your personal configuration.

A local coding agent can read the project folder directly. Native skill/plugin installation is optional.

### Paste this starting message

> Help me analyze my personal spending using Spend Review. Read START_HERE.md and the workflow guide first. Ask me for my reporting dates, account list, currencies, review thresholds and exclusions, then create my private configuration. Do not assume the example settings are mine. Process one account at a time, show dated transactions for review, and ask for my approval before consolidating. Save account analyses, ledgers, review decisions, the final summary and a dashboard where supported. Tell me which checks you actually ran and which remain incomplete.

The assistant should help you choose your dates, complete account roster, currency settings and rules. For example, you might want to review every individual expense above a chosen limit but highlight only larger payee totals in the final summary. These limits are separate and use **strictly greater than**, not greater than or equal to.

### Supply and review one account at a time

Upload statements privately. Supply boundary statements if needed: statement cycles may not match your reporting dates. The assistant should check source totals and present missing data, unclear transactions and above-threshold amounts with their dates, original descriptions and proposed treatment.

Resolve questions and approve each account before requesting consolidation. Do not assume an account has no activity just because its statement is missing.

For encrypted PDFs, use a secure session-only password prompt if available, or unlock the files privately before uploading. Never put passwords in persistent configuration or public issues. See [password-protected PDFs](#password-protected-pdfs).

### Collect your results

Ask for:

- A table of **account/card name, total expenses and aggregated major payees**.
- Separate installment totals, monthly breakdowns and currency-separated totals.
- One saved analysis per account, transaction ledgers and dated review decisions.
- Special-review results, notes-only exclusions and disclosed limitations.
- An offline **`dashboard.html`**, when the Python helper can run.

**Assistant capabilities vary.** Reading files does not guarantee Python execution or downloadable reports. If it cannot execute the helper, ask for normalized records and use the local steps below. A plain-text workflow can guide review, but dashboard generation requires the helper and its template from the full project. Uploading the ZIP does not automatically install a skill or guarantee extraction.

## 3. Run the helper locally

Use this route in Terminal, VS Code or a coding agent. You need **Python 3.10+**. The core helper needs no extra packages, network connection or model API key.

Open a terminal in the repository's top-level folder. If your system calls Python `python` instead of `python3`, substitute that command after checking its version.

### Try a complete synthetic run

Copy the demo into a private folder, validate it, then generate fresh reports:

```sh
python3 -c "import shutil; shutil.copytree('examples/synthetic', 'data/demo')"
python3 skills/budget-analysis/scripts/budget.py validate data/demo
python3 skills/budget-analysis/scripts/budget.py report data/demo
```

The copy command refuses to overwrite an existing `data/demo`. If it exists, reuse it or choose a new folder name in all three commands.

Open **`data/demo/reports/dashboard.html`** in your browser and **`data/demo/reports/spending-summary.md`** in your editor. Expected result: `FINAL_WITH_LIMITATIONS`, a separate unmatched-credit warning, and USD 1,350.00 total.

### Create a real private run

1. Save a copy of `config.example.json` as **`data/my-config.json`**. Edit this private copy with your real dates, account list and rules, preferably with your assistant's help. Set the account roster **before** initializing the run.
2. Initialize:

```sh
python3 skills/budget-analysis/scripts/budget.py init --config data/my-config.json --output data/my-budget
```

3. Put statements in `data/my-budget/sources/`. Have your assistant register them in `intake.csv`, extract and verify transactions into `ledgers/<account-id>.csv`, and record actual approval evidence. **The helper does not do this extraction.** See [the file format](docs/DATA_FORMAT.md).
4. Prepare the review list:

```sh
python3 skills/budget-analysis/scripts/budget.py prepare-reviews data/my-budget
```

5. Review the required rows and account approvals with your assistant. Pending decisions are intentional; do not mark them accepted just to pass validation. Then run:

```sh
python3 skills/budget-analysis/scripts/budget.py validate data/my-budget
python3 skills/budget-analysis/scripts/budget.py report data/my-budget
```

Outputs appear in **`data/my-budget/reports/`**. An invalid run is rejected. A draft report is incomplete, not a final total. Exit codes: `0` final, possibly with limitations; `2` draft; `1` invalid or failed.

## Customize your analysis

Change your private configuration, not the public examples.

| Change | Setting or guide |
| --- | --- |
| Reporting frequency or fiscal/custom dates | `period`; [period examples](docs/PERIODS.md) |
| Bank/card roster | `accounts`; no fixed account count |
| Individual transaction review limit | `review_threshold` |
| Major payee summary limit | `major_expense_threshold` |
| Currency and precision | `currency`, `minor_unit_digits`, account `currency`, `currency_settings` |
| Multiple currencies | [Multi-currency example](config.multicurrency.example.json); set both thresholds per currency |
| Number/currency display | `locale`, such as `en-US`, `en-IN`, `de-DE` or `ja-JP` |
| Transfers and other exclusions | `excluded_transaction_types`; confirm the rules for your analysis |
| Review every row in an account | Account `full_review` |
| Merchant or transfer investigations | `special_reviews`; views of existing records, not extra expenses |

## Privacy and password-protected PDFs

Keep statements, screenshots, passwords, personal settings and real reports under ignored `data/` or outside this checkout. A real dashboard embeds your transactions and must stay private.

The helper and dashboard run locally with no network requests. **A hosted AI assistant may still receive your uploaded statements.** Check its privacy policies before sharing financial documents.

### Password-protected PDFs

The optional accessibility helper accepts any number of hidden candidates, tries the empty password first, and does not save their values. It checks whether a PDF opens, not whether extraction is correct.

In a private virtual environment, install `pypdf[crypto]`, then run:

```sh
python3 tools/pdf_probe.py path/to/private-statement.pdf
```

Enter passwords only at its hidden prompts, never as command arguments or in configuration. See [security guidance](SECURITY.md) and [pypdf's encryption documentation](https://pypdf.readthedocs.io/en/stable/user/encryption-decryption.html).

## What this does not do

- Connect to banks or guarantee automatic parsing of every PDF, spreadsheet or image.
- Prove an assistant read every page correctly or that every account was supplied.
- Guess missing transactions, refund links, exchange rates or transfer purposes.
- Combine unlike currencies without a separate evidenced conversion process.
- Calculate budget variance or savings rates without your actual budget or income baseline.
- Provide accounting certification, investment recommendations or tax advice.

## For contributors and publishers

Public examples must be synthetic. Keep personal inputs and outputs private.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_public.py
python3 tools/package_public.py --output dist/spend-review-public.zip
```

The ZIP includes only the explicit public allowlist. The checker is a safeguard, not a guarantee of anonymity. Review staged files and Git history before publication; ignore rules do not remove previously committed data. These commands do not push to GitHub or post social content.

[Publishing checklist](docs/PUBLISHING.md) · [Data format](docs/DATA_FORMAT.md) · [Security](SECURITY.md) · [MIT License](LICENSE)
