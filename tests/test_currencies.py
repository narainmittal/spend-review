import json
import shutil
import tempfile
import unittest
from pathlib import Path
from test_budget import ROOT, budget

class CurrencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.run=Path(self.temp.name)/'run';shutil.copytree(ROOT/'examples/synthetic',self.run)

    def tearDown(self):self.temp.cleanup()

    def set_currency(self, account, code, digits=2, review='100.00', major='500.00'):
        config=budget.load_json(self.run/'config.json')
        next(x for x in config['accounts'] if x['id']==account)['currency']=code
        config.setdefault('currency_settings',{})[code]=dict(minor_unit_digits=digits,review_threshold=review,major_expense_threshold=major)
        (self.run/'config.json').write_text(json.dumps(config))
        path=self.run/'ledgers'/f'{account}.csv';rows=budget.load_csv(path)
        for row in rows:row['currency']=code
        budget.write_csv(path,rows,budget.FIELDS)
        old=budget.load_csv(self.run/'reviews.csv')
        for review_row in old:
            match=next((x for x in rows if x['transaction_id']==review_row['transaction_id']),None)
            if match:review_row['fingerprint']=budget.fingerprint(match)
        budget.write_csv(self.run/'reviews.csv',old,budget.REVIEW_FIELDS)

    def test_mixed_currencies_never_summed(self):
        self.set_currency('everyday-card','EUR')
        result=budget.analyze(self.run)
        self.assertEqual(result['errors'],[])
        self.assertIsNone(result['period_total'])
        self.assertIsNone(result['emi_total'])
        self.assertEqual(result['totals_by_currency'],{'USD':'300.00','EUR':'1050.00'})
        self.assertEqual(result['monthly_by_currency']['EUR']['2030-02'],'250.00')
        budget.render_report(self.run)
        text=(self.run/'reports/spending-summary.md').read_text()
        self.assertIn('EUR',text);self.assertIn('USD',text)
        self.assertIn('no exchange rate',text)

    def test_missing_currency_policy_rejected(self):
        config=budget.load_json(self.run/'config.json');config['accounts'][1]['currency']='EUR'
        with self.assertRaisesRegex(ValueError,'Explicit precision'):budget.validate_config(config)

    def test_account_currency_mismatch_rejected(self):
        self.set_currency('everyday-card','EUR')
        path=self.run/'ledgers/everyday-card.csv';rows=budget.load_csv(path);rows[0]['currency']='USD';budget.write_csv(path,rows,budget.FIELDS)
        self.assertTrue(any('currency' in x for x in budget.analyze(self.run)['errors']))

    def test_zero_decimal_currency(self):
        self.set_currency('everyday-card','JPY',digits=0,review='100',major='500')
        result=budget.analyze(self.run)
        self.assertEqual(result['errors'],[])
        budget.render_report(self.run)
        text=(self.run/'reports/everyday-card.md').read_text()
        self.assertIn('| 300 |',text)
        self.assertNotIn('300.00',text)

    def test_three_decimal_currency_precision(self):
        self.set_currency('everyday-card','KWD',digits=3,review='100.000',major='500.000')
        config=budget.load_json(self.run/'config.json');effective=budget.currency_settings(config,'KWD')
        self.assertEqual(str(budget.money('1.001',effective)),'1.001')
        with self.assertRaises(ValueError):budget.money('1.0001',effective)
        budget.render_report(self.run)
        self.assertIn('300.000',(self.run/'reports/everyday-card.md').read_text())

    def test_per_currency_major_threshold(self):
        self.set_currency('everyday-card','EUR',major='600.00')
        self.assertEqual(budget.analyze(self.run)['major'],[])

    def test_mixed_special_review_preserves_separate_amounts(self):
        self.set_currency('everyday-card','EUR')
        config=budget.load_json(self.run/'config.json');config['special_reviews']=[dict(name='All synthetic',description_regex='DEMO')]
        (self.run/'config.json').write_text(json.dumps(config))
        special=budget.analyze(self.run)['special_reviews'][0]
        self.assertIsNone(special['included_expenses'])
        self.assertEqual(special['totals_by_currency']['USD']['included_expenses'],'100.00')
        self.assertEqual(special['totals_by_currency']['EUR']['included_expenses'],'1050.00')

    def test_dashboard_contains_only_period_rows_and_escapes_data(self):
        path=self.run/'ledgers/everyday-card.csv';rows=budget.load_csv(path)
        rows[0]['raw_description']='</script><script>UNTRUSTED_MARKER</script>';budget.write_csv(path,rows,budget.FIELDS)
        budget.prepare_reviews(self.run)
        budget.render_report(self.run)
        html=(self.run/'reports/dashboard.html').read_text()
        self.assertNotIn('</script><script>UNTRUSTED_MARKER',html)
        self.assertIn('\\u003c/script\\u003e',html)
        self.assertNotIn('BANK-5',html)
        self.assertIn("connect-src 'none'",html)
        self.assertIn('BigInt',html)

if __name__=='__main__':unittest.main()
