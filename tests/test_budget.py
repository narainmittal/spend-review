import copy
import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('budget', ROOT/'skills/budget-analysis/scripts/budget.py')
budget=importlib.util.module_from_spec(spec);spec.loader.exec_module(budget)

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.run=Path(self.temp.name)/'run'
        shutil.copytree(ROOT/'examples/synthetic', self.run)

    def tearDown(self):
        self.temp.cleanup()

    def edit_json(self, name, action):
        p=self.run/name;data=budget.load_json(p);action(data);p.write_text(json.dumps(data))

    def edit_rows(self, account, action):
        p=self.run/'ledgers'/f'{account}.csv';rows=budget.load_csv(p);action(rows);budget.write_csv(p,rows,budget.FIELDS)

    def test_synthetic_totals_and_thresholds(self):
        result=budget.analyze(self.run)
        self.assertEqual(result['status'],'FINAL_WITH_LIMITATIONS')
        self.assertEqual(result['period_total'],'1350.00')
        self.assertEqual(result['emi_total'],'200.00')
        self.assertEqual(result['required_reviews'],8)
        self.assertEqual(result['major'],[{'account_id':'everyday-card','payee':'Demo store','amount':'550.00'}])
        self.assertEqual(result['monthly'],{'2030-01':'400.00','2030-02':'250.00','2030-03':'700.00'})
        self.assertEqual(result['special_reviews'][0]['included_expenses'],'550.00')

    def test_missing_account_file_is_error(self):
        # Recoverably rename a synthetic test fixture, never a user's file.
        p=self.run/'ledgers/everyday-card.csv';p.rename(p.with_suffix('.test-backup'))
        self.assertTrue(budget.analyze(self.run)['errors'])

    def test_unapproved_coverage_is_draft(self):
        self.edit_json('approvals.json',lambda x:x['accounts']['daily-bank'].update(coverage_approved=False))
        self.assertEqual(budget.analyze(self.run)['status'],'DRAFT')

    def test_changed_source_row_invalidates_review(self):
        self.edit_rows('everyday-card',lambda x:x[0].update(amount='301.00'))
        self.assertTrue(any('stale' in x for x in budget.analyze(self.run)['pending']))
        budget.prepare_reviews(self.run)
        rows=budget.load_csv(self.run/'reviews.csv')
        self.assertEqual(next(x for x in rows if x['transaction_id']=='CARD-1')['decision'],'pending')
        self.assertEqual(next(x for x in rows if x['transaction_id']=='CARD-2')['decision'],'accepted')

    def test_duplicate_id_rejected(self):
        self.edit_rows('everyday-card',lambda x:x[1].update(transaction_id='CARD-1'))
        self.assertTrue(any('duplicate' in x.lower() for x in budget.analyze(self.run)['errors']))

    def test_unlinked_credit_not_netted(self):
        self.edit_rows('everyday-card',lambda x:x[3].update(included='yes'))
        self.assertTrue(any('Unlinked credit' in x for x in budget.analyze(self.run)['errors']))

    def test_emi_not_double_counted(self):
        self.edit_rows('daily-bank',lambda x:x[3].update(included='yes'))
        self.assertTrue(any('double-counted' in x for x in budget.analyze(self.run)['errors']))

    def test_configurable_threshold_and_full_review(self):
        self.edit_json('config.json',lambda x:x.update(review_threshold='1000.00',major_expense_threshold='600.00'))
        # Old decisions cannot silently disappear after changing required-review policy.
        self.assertTrue(any('Review inventory' in x for x in budget.analyze(self.run)['errors']))
        with self.assertRaises(ValueError):budget.prepare_reviews(self.run)
        self.edit_json('config.json',lambda x:x['accounts'][0].update(full_review=True))
        self.assertTrue(any('BANK-1' in x for x in budget.analyze(self.run)['pending']))

    def test_unlimited_account_roster(self):
        def extra(c):
            c['accounts'] += [dict(id=f'account-{i}',name=f'Example account {i}',status='no_activity',evidence='Synthetic no-activity confirmation') for i in range(20)]
        self.edit_json('config.json',extra)
        for i in range(20):budget.write_csv(self.run/'ledgers'/f'account-{i}.csv',[],budget.FIELDS)
        self.assertEqual(len(budget.analyze(self.run)['account_expenses']),22)

    def test_currency_precision_and_nonfinite(self):
        config=budget.load_json(self.run/'config.json')
        with self.assertRaises(ValueError):budget.money('NaN',config)
        with self.assertRaises(ValueError):budget.money('1.001',config)
        config['minor_unit_digits']=3
        self.assertEqual(str(budget.money('1.001',config)),'1.001')

    def test_secret_configuration_rejected(self):
        config=budget.load_json(self.run/'config.json');config['passwords']=['synthetic-not-a-real-secret']
        with self.assertRaises(ValueError):budget.validate_config(config)

    def test_source_path_traversal_rejected(self):
        with self.assertRaises(ValueError):budget.safe_child(self.run/'sources','../config.json')

    def test_source_conflict_not_erased(self):
        self.edit_json('approvals.json',lambda x:x['accepted_limitations'].append(dict(description='Conflicting fictional source evidence remains',evidence='Synthetic source versus assertion')))
        result=budget.analyze(self.run)
        self.assertEqual(result['status'],'FINAL_WITH_LIMITATIONS')
        self.assertTrue(any('Conflicting' in x for x in result['warnings']))

    def test_init_refuses_overwrite_and_never_accepts_reviews(self):
        with self.assertRaises(ValueError):budget.init_run(ROOT/'config.example.json',self.run)
        fresh=Path(self.temp.name)/'fresh';budget.init_run(ROOT/'config.example.json',fresh)
        self.assertEqual(budget.load_csv(fresh/'reviews.csv'),[])
        self.assertEqual(budget.analyze(fresh)['status'],'DRAFT')

    def test_report_reconciles_and_retains_source_rows(self):
        result=budget.render_report(self.run)
        self.assertEqual(len(budget.load_csv(self.run/'reports/consolidated.csv')),10)
        self.assertIn('1,350.00',(self.run/'reports/spending-summary.md').read_text())
        self.assertEqual(result['account_expenses']['everyday-card'],'1050.00')

if __name__=='__main__':unittest.main()
