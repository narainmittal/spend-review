#!/usr/bin/env python3
"""Local, evidence-first budget helpers. No network calls or password storage."""
import argparse
import calendar
import csv
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ['transaction_id', 'transaction_date', 'amount', 'currency', 'direction',
          'raw_description', 'cleaned_payee', 'transaction_type', 'included', 'emi',
          'review_required', 'source_file', 'source_row', 'link_evidence', 'notes']
REVIEW_FIELDS = ['transaction_id', 'fingerprint', 'decision', 'reviewer', 'reviewed_on', 'notes']
INSTALLMENTS = {'loan_emi', 'card_emi'}
REFUNDS = {'confirmed_refund', 'linked_refund', 'linked_reversal', 'linked_fee_reversal'}

def currency_settings(config, code):
    if code == config['currency']:
        return config
    values = config.get('currency_settings', {}).get(code)
    if values is None:
        raise ValueError('Explicit precision and thresholds required for currency: ' + code)
    return dict(config, **values, currency=code)

def account_settings(account, config):
    return currency_settings(config, account.get('currency', config['currency']))

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def load_csv(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))

def write_csv(path, rows, fields):
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def safe_child(root, value):
    value = Path(value)
    if value.is_absolute() or '..' in value.parts or not value.parts:
        raise ValueError('Source references must be nonempty relative paths without traversal')
    target = (root / value).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Source symlink escapes private sources directory')
    return target

def resolve_period(period):
    """Resolve explicit calendar presets, never infer a year or today's date."""
    frequency = period.get('frequency', 'custom')
    if frequency == 'custom':
        start, end = date.fromisoformat(period['start']), date.fromisoformat(period['end'])
    else:
        if frequency not in {'monthly', 'quarterly', 'half-yearly', 'yearly'}:
            raise ValueError('Unsupported period frequency')
        year = period.get('year')
        if type(year) is not int or not 1 <= year <= 9999:
            raise ValueError('Preset periods require an explicit valid year')
        field, width, count = {'monthly': ('month', 1, 12), 'quarterly': ('quarter', 3, 4),
                               'half-yearly': ('half', 6, 2), 'yearly': (None, 12, 1)}[frequency]
        index = period.get(field) if field else 1
        if type(index) is not int or not 1 <= index <= count:
            raise ValueError('Invalid period index: ' + str(field))
        first = 1 + (index - 1) * width
        last = first + width - 1
        start, end = date(year, first, 1), date(year, last, calendar.monthrange(year, last)[1])
        for key, value in [('start', start), ('end', end)]:
            if key in period and period[key] != value.isoformat():
                raise ValueError('Preset conflicts with explicit period ' + key)
    if start > end:
        raise ValueError('Period start follows end')
    return dict(period, frequency=frequency, start=start.isoformat(), end=end.isoformat())

def validate_config(config):
    config = dict(config, period=resolve_period(config['period']))
    start, end = date.fromisoformat(config['period']['start']), date.fromisoformat(config['period']['end'])
    if start > end:
        raise ValueError('Period start follows end')
    if not re.fullmatch(r'[A-Z]{3}', config['currency']):
        raise ValueError('Use an explicit three-letter currency; no implicit conversion')
    digits = config['minor_unit_digits']
    if type(digits) is not int or not 0 <= digits <= 4:
        raise ValueError('minor_unit_digits must be an integer from 0 to 4')
    for field in ['review_threshold', 'major_expense_threshold']:
        number = money(config[field], config)
        if number < 0:
            raise ValueError('Thresholds must be nonnegative')
    for code, values in config.get('currency_settings', {}).items():
        if code == config['currency'] or not re.fullmatch(r'[A-Z]{3}', code):
            raise ValueError('Additional currency codes must be distinct three-letter codes')
        if not {'minor_unit_digits', 'review_threshold', 'major_expense_threshold'} <= values.keys():
            raise ValueError('Each additional currency needs explicit precision and both thresholds')
        digits = values['minor_unit_digits']
        if type(digits) is not int or not 0 <= digits <= 4:
            raise ValueError('Currency precision must be an integer from 0 to 4')
        effective = currency_settings(config, code)
        if any(money(values[field], effective) < 0 for field in ['review_threshold', 'major_expense_threshold']):
            raise ValueError('Currency thresholds must be nonnegative')
    if not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', config.get('locale', 'en-US')):
        raise ValueError('locale must be a language/region tag, for example en-US or de-DE')
    ids = [a['id'] for a in config['accounts']]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', x) for x in ids):
        raise ValueError('Account IDs must be unique safe lowercase slugs')
    names = [a['name'] for a in config['accounts']]
    if len(names) != len(set(names)) or any(not x.strip() for x in names):
        raise ValueError('Account display names must be nonempty and unique')
    for account in config['accounts']:
        account_settings(account, config)
        if account['status'] not in {'expected', 'received', 'no_activity', 'out_of_scope'}:
            raise ValueError('Invalid account status')
        if type(account.get('full_review', False)) is not bool:
            raise ValueError('full_review must be boolean')
        if account['status'] in {'no_activity', 'out_of_scope'} and not account.get('evidence'):
            raise ValueError('No-activity/out-of-scope accounts require evidence')
    if config.get('password_policy') != {'input': 'interactive', 'try_empty_first': True}:
        raise ValueError('Only interactive/in-memory password policy is supported; do not store candidates')
    def reject_secrets(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {'password', 'passwords', 'password_list', 'password_candidates', 'api_key', 'token', 'secret'}:
                    raise ValueError('Secret fields are prohibited in persisted configuration')
                reject_secrets(item)
        elif isinstance(value, list):
            for item in value:
                reject_secrets(item)
    reject_secrets(config)
    special_names = []
    for special in config.get('special_reviews', []):
        special_names.append(special['name'])
        if not set(special.get('accounts', [])) <= set(ids):
            raise ValueError('Special review references unknown account')
        if special.get('description_regex'):
            re.compile(special['description_regex'])
    if len(special_names) != len(set(special_names)):
        raise ValueError('Special review names must be unique')
    return config

def money(value, config):
    if not isinstance(value, str):
        raise ValueError('Store monetary inputs as decimal strings, not binary floats')
    number = Decimal(value)
    precision = Decimal(1).scaleb(-config['minor_unit_digits'])
    if not number.is_finite() or number != number.quantize(precision):
        raise ValueError('Invalid amount or precision incompatible with currency configuration')
    return number

def init_run(config_path, output):
    config = validate_config(load_json(config_path))
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Refusing to overwrite a nonempty run directory')
    output.mkdir(parents=True, exist_ok=True)
    for directory in ['sources', 'ledgers', 'reports']:
        (output / directory).mkdir()
    (output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    approvals = {'accounts': {}, 'accepted_limitations': []}
    for account in config['accounts']:
        write_csv(output / 'ledgers' / (account['id'] + '.csv'), [], FIELDS)
        approvals['accounts'][account['id']] = dict(classification_approved=False,
            coverage_approved=False, reconciliation_approved=False, evidence='')
    (output / 'approvals.json').write_text(json.dumps(approvals, indent=2) + '\n')
    write_csv(output / 'intake.csv', [], ['source_file', 'account_id', 'statement_start', 'statement_end', 'notes'])
    write_csv(output / 'reviews.csv', [], REVIEW_FIELDS)
    return output

def required(row, account, config):
    config = account_settings(account, config)
    inside = config['period']['start'] <= row['transaction_date'] <= config['period']['end']
    return inside and (money(row['amount'], config) > money(config['review_threshold'], config)
                      or account.get('full_review', False) or row['review_required'] == 'yes')

def prepare_reviews(run):
    run = Path(run)
    config = validate_config(load_json(run / 'config.json'))
    old = load_csv(run / 'reviews.csv')
    if len({x['transaction_id'] for x in old}) != len(old):
        raise ValueError('Duplicate existing review IDs; resolve before preparing reviews')
    by_id = {x['transaction_id']: x for x in old}
    result, seen = [], set()
    for account in config['accounts']:
        path = run / 'ledgers' / (account['id'] + '.csv')
        if not path.exists():
            continue
        for row in load_csv(path):
            tid = row['transaction_id']
            if tid in seen:
                raise ValueError('Duplicate ledger transaction ID')
            seen.add(tid)
            if not required(row, account, config):
                continue
            signature = fingerprint(row)
            previous = by_id.get(tid)
            if previous and previous['fingerprint'] == signature:
                result.append(previous)
            else:
                result.append(dict(transaction_id=tid, fingerprint=signature, decision='pending',
                                   reviewer='', reviewed_on='', notes='Input changed; review again' if previous else ''))
    stale = set(by_id) - {x['transaction_id'] for x in result}
    if stale:
        raise ValueError('Existing decisions no longer match required rows; archive/reconcile reviews before retrying')
    write_csv(run / 'reviews.csv', result, REVIEW_FIELDS)
    return len(result)

def analyze(run):
    run = Path(run)
    errors, pending, warnings = [], [], []
    config = validate_config(load_json(run / 'config.json'))
    start, end = config['period']['start'], config['period']['end']
    account_map = {a['id']: a for a in config['accounts']}
    if not account_map:
        pending.append('No account roster configured')
    if config.get('inventory_approved') is not True or not config.get('inventory_evidence'):
        pending.append('Expected account inventory not explicitly approved')
    actual = {p.stem for p in (run / 'ledgers').glob('*.csv')}
    if actual != set(account_map):
        errors.append('Ledger file inventory differs from configured account roster')
    intake_rows = load_csv(run / 'intake.csv')
    sources = {(x['account_id'], x['source_file']) for x in intake_rows}
    if len(sources) != len(intake_rows):
        errors.append('Duplicate account/source intake record')
    for source in intake_rows:
        if source['account_id'] not in account_map or not safe_child(run / 'sources', source['source_file']).is_file():
            errors.append('Invalid account or missing source in intake')
    review_rows = load_csv(run / 'reviews.csv')
    reviews = {x['transaction_id']: x for x in review_rows}
    if len(reviews) != len(review_rows):
        errors.append('Duplicate review ID')
    approvals = load_json(run / 'approvals.json')
    totals, major, months = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
    gross, credits, emi_totals = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
    rows, seen, required_ids = [], set(), set()
    for account in config['accounts']:
        aid = account['id']
        effective = account_settings(account, config)
        totals[aid] += Decimal(0)
        if account['status'] == 'expected':
            pending.append('Expected account still missing: ' + aid)
        approval = approvals.get('accounts', {}).get(aid, {})
        if account['status'] == 'received':
            for flag in ['classification_approved', 'coverage_approved', 'reconciliation_approved']:
                if approval.get(flag) is not True or not approval.get('evidence'):
                    pending.append(aid + ': ' + flag + ' not evidenced')
        path = run / 'ledgers' / (aid + '.csv')
        if not path.exists():
            continue
        account_rows = load_csv(path)
        if account['status'] == 'received' and not account_rows:
            pending.append('Received account has no rows; confirm no_activity if appropriate: ' + aid)
        if account['status'] in {'no_activity', 'out_of_scope'} and account_rows:
            errors.append('Nonempty ledger contradicts no_activity/out_of_scope: ' + aid)
        for row in account_rows:
            if not set(FIELDS) <= set(row) or any(row[k] is None for k in FIELDS):
                raise ValueError('Ledger header or required column malformed')
            tid = row['transaction_id']
            if not tid or tid in seen:
                errors.append('Missing or duplicate transaction ID: ' + tid)
            seen.add(tid)
            date.fromisoformat(row['transaction_date'])
            value = money(row['amount'], effective)
            if value < 0 or row['currency'] != effective['currency'] or row['direction'] not in {'debit', 'credit'}:
                errors.append('Invalid amount/currency/direction: ' + tid)
            for flag in ['included', 'emi', 'review_required']:
                if row[flag] not in {'yes', 'no'}:
                    errors.append('Invalid yes/no flag: ' + tid)
            if not row['raw_description'] or not row['source_row'] or not row['transaction_type']:
                errors.append('Missing description/type/source row: ' + tid)
            if (aid, row['source_file']) not in sources or not safe_child(run / 'sources', row['source_file']).is_file():
                errors.append('Unregistered or missing ledger source: ' + tid)
            inside = start <= row['transaction_date'] <= end
            included, is_emi = row['included'] == 'yes', row['emi'] == 'yes'
            if included and (row['transaction_type'] in config['excluded_transaction_types'] or row['transaction_type'] in INSTALLMENTS):
                errors.append('Excluded movement marked as expense: ' + tid)
            if included and not row['cleaned_payee']:
                errors.append('Included expense needs verified cleaned payee: ' + tid)
            if included and row['direction'] == 'credit' and (row['transaction_type'] not in REFUNDS or not row['link_evidence']):
                errors.append('Unlinked credit cannot reduce expenses: ' + tid)
            if row['transaction_type'] in REFUNDS and row['direction'] != 'credit':
                errors.append('Expense refund must be a credit: ' + tid)
            if row['transaction_type'] in INSTALLMENTS and (not is_emi or not row['link_evidence']):
                errors.append('Installment needs separate EMI contribution and evidence: ' + tid)
            if is_emi and (included or row['direction'] != 'debit' or row['transaction_type'] not in INSTALLMENTS):
                errors.append('Invalid or double-counted EMI: ' + tid)
            if required(row, account, config):
                required_ids.add(tid)
                review = reviews.get(tid, {})
                valid_review = (review.get('fingerprint') == fingerprint(row) and review.get('decision') == 'accepted'
                                and review.get('reviewer') and review.get('reviewed_on'))
                if not valid_review:
                    pending.append('Review missing, pending or stale: ' + tid)
                else:
                    date.fromisoformat(review['reviewed_on'])
            contribution = value * (1 if row['direction'] == 'debit' else -1) if inside and included else Decimal(0)
            emi = value if inside and is_emi else Decimal(0)
            totals[aid] += contribution
            major[(aid, row['cleaned_payee'])] += contribution
            months[(effective['currency'], row['transaction_date'][:7])] += contribution + emi
            emi_totals[aid] += emi
            if inside and included:
                if row['direction'] == 'debit':
                    gross[aid] += value
                else:
                    credits[aid] += value
            if inside and row['direction'] == 'credit' and not included and row['transaction_type'] != 'credit_card_payment':
                warnings.append('Separate credit not netted: ' + tid)
            rows.append(dict(row, account_id=aid, in_period='yes' if inside else 'no', expense_contribution=str(contribution), emi_contribution=str(emi)))
    if set(reviews) != required_ids:
        errors.append('Review inventory differs from required ledger rows; prepare/reconcile reviews')
    for limitation in approvals.get('accepted_limitations', []):
        if not limitation.get('description') or not limitation.get('evidence'):
            errors.append('Accepted limitation needs description and evidence')
        else:
            warnings.append(limitation['description'])
    special_results = []
    for special in config.get('special_reviews', []):
        matches = []
        for row in rows:
            if row['in_period'] != 'yes':
                continue
            if special.get('accounts') and row['account_id'] not in special['accounts']:
                continue
            if special.get('description_regex') and not re.search(special['description_regex'], row['raw_description']):
                continue
            if special.get('transaction_types') and row['transaction_type'] not in special['transaction_types']:
                continue
            matches.append(row)
        special_currencies = sorted({x['currency'] for x in matches})
        subtotals = {}
        for code in special_currencies:
            subset = [x for x in matches if x['currency']==code]
            subtotals[code] = dict(included_expenses=str(sum((Decimal(x['expense_contribution']) for x in subset), Decimal(0))),
                gross_debits=str(sum((Decimal(x['amount']) for x in subset if x['direction']=='debit'), Decimal(0))),
                gross_credits=str(sum((Decimal(x['amount']) for x in subset if x['direction']=='credit'), Decimal(0))))
        single = subtotals[special_currencies[0]] if len(special_currencies)==1 else dict(included_expenses=None,gross_debits=None,gross_credits=None)
        special_results.append(dict(name=special['name'], transaction_ids=[x['transaction_id'] for x in matches], totals_by_currency=subtotals, **single))
    by_currency, emi_by_currency = defaultdict(Decimal), defaultdict(Decimal)
    account_currencies = {}
    for account in config['accounts']:
        aid = account['id'];code = account_settings(account, config)['currency']
        account_currencies[aid] = code
        by_currency[code] += totals[aid] + emi_totals[aid]
        emi_by_currency[code] += emi_totals[aid]
    single_currency = next(iter(by_currency)) if len(by_currency)==1 else None
    total = str(by_currency[single_currency]) if single_currency else None
    monthly_by_currency = {code:{m:str(v) for (c,m),v in sorted(months.items()) if c==code and start[:7]<=m<=end[:7]} for code in by_currency}
    return dict(status='INVALID' if errors else 'DRAFT' if pending else 'FINAL_WITH_LIMITATIONS' if warnings else 'FINAL',
        errors=errors, pending=pending, warnings=warnings, currency=single_currency,
        account_currencies=account_currencies, totals_by_currency={k:str(v) for k,v in by_currency.items()},
        emi_by_currency={k:str(v) for k,v in emi_by_currency.items()}, monthly_by_currency=monthly_by_currency,
        account_expenses={k:str(v) for k,v in totals.items()}, gross_included={k:str(v) for k,v in gross.items()},
        linked_credits={k:str(v) for k,v in credits.items()}, account_emi={k:str(v) for k,v in emi_totals.items()},
        emi_total=str(emi_by_currency[single_currency]) if single_currency else None, period_total=total,
        monthly=monthly_by_currency.get(single_currency, {}),
        major=[dict(account_id=k[0], payee=k[1], amount=str(v)) for k,v in sorted(major.items()) if v>money(account_settings(account_map[k[0]],config)['major_expense_threshold'],account_settings(account_map[k[0]],config))],
        special_reviews=special_results, required_reviews=len(required_ids), transaction_count=len(rows), rows=rows)

def render_report(run):
    run = Path(run)
    result = analyze(run)
    if result['errors']:
        raise ValueError('Cannot report structurally invalid data; run validate first')
    config = validate_config(load_json(run / 'config.json'))
    output = run / 'reports'
    output.mkdir(exist_ok=True)
    fmt = lambda x, code: f"{Decimal(x):,.{currency_settings(config,code)['minor_unit_digits']}f}"
    esc = lambda x: str(x).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    table = ['| Account / card | Currency | Recorded expenses | Major payee aggregates |', '| --- | --- | ---: | --- |']
    for code, value in sorted(result['emi_by_currency'].items()):
        table.append('| EMI | '+code+' | '+fmt(value,code)+' | Actual installments, counted once |')
    for account in config['accounts']:
        aid = account['id']
        code = result['account_currencies'][aid]
        notes = '; '.join(esc(x['payee'])+' '+fmt(x['amount'],code) for x in result['major'] if x['account_id']==aid)
        value = result['account_expenses'][aid]
        label = account['name'] + (' (not received)' if account['status']=='expected' else '')
        table.append('| '+esc(label)+' | '+code+' | '+('unavailable' if account['status']=='expected' else fmt(value,code))+' | '+notes+' |')
        details = ['| Date | Original description | Direction | Amount | Expense contribution |', '| --- | --- | --- | ---: | ---: |']
        details += ['| '+ ' | '.join([x['transaction_date'],esc(x['raw_description']),x['direction'],fmt(x['amount'],code),fmt(x['expense_contribution'],code)])+' |' for x in result['rows'] if x['account_id']==aid]
        (output / (aid+'.md')).write_text('# '+account['name']+'\n\nStatus: '+result['status']+'. Currency: '+code+'\n\n'+'\n'.join(details)+'\n')
    for code,value in sorted(result['totals_by_currency'].items()):
        table.append('| **Recorded total including EMI** | **'+code+'** | **'+fmt(value,code)+'** | |')
    text = '# Budget analysis\n\nPeriod: '+config['period']['start']+' to '+config['period']['end']+'. Currencies are kept separate; no exchange rate or mixed-currency grand total is inferred.\n\nStatus: '+result['status']+'. Draft totals are partial, not a complete-period spending claim.\n\n'+'\n'.join(table)
    text += '\n\n## Monthly recorded spending\n\n| Month | Currency | Expenses plus EMI |\n| --- | --- | ---: |\n'+'\n'.join('| '+month+' | '+code+' | '+fmt(value,code)+' |' for code,months in result['monthly_by_currency'].items() for month,value in months.items())
    text += '\n\n## Pending decisions and limitations\n\n'+'\n'.join('- '+x for x in result['pending']+result['warnings'])
    text += '\n\n## Special reviews (already included where applicable; do not add again)\n\n'+'\n'.join('- '+x['name']+' ('+code+'): included expenses '+fmt(values['included_expenses'],code)+', gross debits '+fmt(values['gross_debits'],code)+', gross credits '+fmt(values['gross_credits'],code) for x in result['special_reviews'] for code,values in x['totals_by_currency'].items())
    text += '\n\nUnlinked credits remain separate. Transfers/card payments and configured exclusions are not expenses. No budget variance or savings rate is inferred without a baseline. Review source evidence and every model extraction.\n'
    (output/'spending-summary.md').write_text(text)
    if result['rows']:
        write_csv(output/'consolidated.csv', result['rows'], list(result['rows'][0]))
    summary = {k:v for k,v in result.items() if k!='rows'}
    (output/'validation.json').write_text(json.dumps(summary, indent=2)+'\n')
    write_dashboard(output/'dashboard.html', result, config)
    return result

def write_dashboard(path, result, config):
    """Offline report. Keep real runs private; only synthetic demos may be public."""
    accounts = {a['id']:a for a in config['accounts']}
    codes = sorted(result['totals_by_currency']) or [config['currency']]
    payload = dict(status=result['status'], period=config['period'], locale=config.get('locale','en-US'),
        currencies={code:dict(digits=currency_settings(config,code)['minor_unit_digits']) for code in codes},
        accounts=[dict(id=a['id'],name=a['name'],currency=account_settings(a,config)['currency']) for a in config['accounts']],
        warnings=result['pending']+result['warnings'], rows=[])
    for row in result['rows']:
        if row['in_period']!='yes':
            continue
        digits=currency_settings(config,row['currency'])['minor_unit_digits']
        payload['rows'].append(dict(id=row['transaction_id'],date=row['transaction_date'],currency=row['currency'],
            account=row['account_id'],payee=row['cleaned_payee'],description=row['raw_description'],
            expense=str(int(Decimal(row['expense_contribution'])*(10**digits))),
            emi=str(int(Decimal(row['emi_contribution'])*(10**digits)))))
    template=Path(__file__).resolve().parents[1]/'assets/dashboard-template.html'
    encoded=json.dumps(payload,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(path).write_text(template.read_text().replace('__BUDGET_DATA__',encoded),encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--config', required=True, type=Path)
    init.add_argument('--output', required=True, type=Path)
    for name in ['prepare-reviews', 'validate', 'report']:
        cmd = sub.add_parser(name)
        cmd.add_argument('run', type=Path)
    args = parser.parse_args()
    try:
        if args.command=='init':
            print('Initialized private run:', init_run(args.config, args.output));return 0
        if args.command=='prepare-reviews':
            print('Required review rows prepared:', prepare_reviews(args.run));return 0
        result = render_report(args.run) if args.command=='report' else analyze(args.run)
        print(json.dumps({k:v for k,v in result.items() if k!='rows'}, indent=2))
        return 1 if result['errors'] else 2 if result['pending'] else 0
    except (ValueError, KeyError, TypeError, OSError, InvalidOperation, csv.Error) as error:
        print('Cannot complete safely:', error)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
