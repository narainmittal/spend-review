import unittest
from test_budget import budget, ROOT

class PeriodTests(unittest.TestCase):
    def test_presets(self):
        cases = [({'frequency':'monthly','year':2032,'month':2}, '2032-02-01','2032-02-29'),
                 ({'frequency':'quarterly','year':2030,'quarter':3}, '2030-07-01','2030-09-30'),
                 ({'frequency':'half-yearly','year':2030,'half':2}, '2030-07-01','2030-12-31'),
                 ({'frequency':'yearly','year':2030}, '2030-01-01','2030-12-31')]
        for source, start, end in cases:
            with self.subTest(source=source):
                result=budget.resolve_period(source)
                self.assertEqual((result['start'],result['end']),(start,end))
                self.assertEqual(budget.resolve_period(result),result)

    def test_custom_and_legacy(self):
        result=budget.resolve_period({'start':'2030-04-06','end':'2031-04-05'})
        self.assertEqual(result['frequency'],'custom')
        self.assertEqual(result['end'],'2031-04-05')

    def test_invalid_or_conflicting_presets(self):
        for source in [{'frequency':'monthly','month':1},
                       {'frequency':'quarterly','year':2030,'quarter':5},
                       {'frequency':'half-yearly','year':2030,'half':True},
                       {'frequency':'yearly','year':2030,'start':'2030-02-01'},
                       {'frequency':'weekly','year':2030},
                       {'start':'2030-02-01','end':'2030-01-01'}]:
            with self.subTest(source=source), self.assertRaises((ValueError,KeyError)):
                budget.resolve_period(source)

    def test_validated_config_resolves_preset(self):
        config=budget.load_json(ROOT/'config.example.json')
        config['period']={'frequency':'monthly','year':2032,'month':2}
        result=budget.validate_config(config)
        self.assertEqual(result['period']['end'],'2032-02-29')
        self.assertNotIn('end',config['period'])
