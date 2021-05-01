# test_account_balance.py

import unittest
from src.account_balance import AccountBalance, SymbolBalance


class TestAccountBalance(unittest.TestCase):
    def setUp(self) -> None:
        self.sb_btc = SymbolBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='initial')
        self.sb_bnb = SymbolBalance(name='bnb', free=2_000_000.0, locked=80_000.0, tag='initial')
        self.sb_eur = SymbolBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='initial', precision=2)
        self.ab_initial = AccountBalance(sb_list=[self.sb_btc, self.sb_bnb, self.sb_eur])

        self.sb_btc_2 = SymbolBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='actual')
        self.sb_bnb_2 = SymbolBalance(name='bnb', free=2_000_000.0, locked=80_000.0, tag='actual')
        self.sb_eur_2 = SymbolBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='actual', precision=2)
        self.ab_actual = AccountBalance(sb_list=[self.sb_btc_2, self.sb_bnb_2, self.sb_eur_2])

    def test_add(self):
        ab_add = self.ab_initial + self.ab_actual
        self.assertEqual(100_000.0, ab_add.ab[0].locked)
        self.assertEqual(4_160_000.0, ab_add.ab[1].get_total())
        self.assertEqual(20_000_000.0, ab_add.ab[2].free)

    def test_sub(self):
        ab_add = self.ab_initial - self.ab_actual
        self.assertEqual(0.0, ab_add.ab[0].locked)
        self.assertEqual(0.0, ab_add.ab[1].get_total())
        self.assertEqual(0.0, ab_add.ab[2].free)

    def test_log_print(self):
        self.ab_initial.log_print()


class TestSymbolBalance(unittest.TestCase):
    def setUp(self) -> None:
        self.sb1 = SymbolBalance(name='btc', free=1_000_000.0, locked=50_000.0, tag='test')
        self.sb2 = SymbolBalance(name='btc', free=2_000_000.0, locked=80_000.0, tag='test')
        self.sb3 = SymbolBalance(name='eur', free=10_000_000.0, locked=30_000.0, tag='test', precision=2)

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

    def test_log_print(self):
        self.sb1.log_print()
        self.sb2.log_print()
        self.sb3.log_print()