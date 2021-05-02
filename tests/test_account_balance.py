# test_account_balance.py

import unittest
from src.pp_account_balance import AccountBalance, AssetBalance


class TestAccountBalance(unittest.TestCase):
    def setUp(self) -> None:
        self.sb_btc = AssetBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='initial')
        self.sb_bnb = AssetBalance(name='bnb', free=2_000_000.0, locked=80_000.0, tag='initial')
        self.sb_eur = AssetBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='initial', precision=2)
        self.ab_initial = AccountBalance(d={'s1': self.sb_btc, 's2': self.sb_bnb, 'bnb': self.sb_eur})

        self.sb_btc_2 = AssetBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='actual')
        self.sb_bnb_2 = AssetBalance(name='bnb', free=2_000_000.0, locked=80_000.0, tag='actual')
        self.sb_eur_2 = AssetBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='actual', precision=2)
        self.ab_actual = AccountBalance(d={'s1': self.sb_btc, 's2': self.sb_bnb, 'bnb': self.sb_eur})

    def test_add(self):
        ab_add = self.ab_initial + self.ab_actual
        self.assertEqual(100_000.0, ab_add.s1.locked)
        self.assertEqual(4_160_000.0, ab_add.s2.get_total())
        self.assertEqual(20_000_000.0, ab_add.bnb.free)

    def test_sub(self):
        ab_add = self.ab_initial - self.ab_actual
        self.assertEqual(0.0, ab_add.s1.locked)
        self.assertEqual(0.0, ab_add.s2.get_total())
        self.assertEqual(0.0, ab_add.bnb.free)

    def test_log_print(self):
        self.ab_initial.log_print()


class TestAssetBalance(unittest.TestCase):
    def setUp(self) -> None:
        self.sb1 = AssetBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='test')
        self.sb2 = AssetBalance(name='btc', free=2_000_000.0, locked=80_000.0, tag='test')
        self.sb3 = AssetBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='test', precision=2)

    def test_add(self):
        # test __add__ (+)
        sb3 = self.sb1 + self.sb2
        self.assertEqual('btc', sb3.name)
        self.assertEqual(1_000_000.0 + 2_000_000.0, sb3.free)
        self.assertEqual(50_000.0 + 80_000.0, sb3.locked)
        self.assertEqual('test', sb3.tag)

    def test_sub(self):
        # test __sub__ (-)
        sb = self.sb1 - self.sb2
        self.assertEqual('btc', sb.name)
        self.assertEqual(1_000_000.0 - 2_000_000.0, sb.free)
        self.assertEqual(50_000.0 - 80_000.0, sb.locked)
        self.assertEqual('test', sb.tag)

    def test_get_total(self):
        total = self.sb1.get_total()
        self.assertEqual(1_000_000.0 + 50_000.0, total)

    def test_to_dict(self):
        self.assertDictEqual({'s1': self.sb1}, self.sb1.to_dict(symbol='BTCEUR'))

    def test_log_print(self):
        self.sb1.log_print()
        self.sb2.log_print()
        self.sb3.log_print()