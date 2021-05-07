# pp_account_balance.py
import logging
from typing import Dict

log = logging.getLogger('log')

B_EUR_PER_BTC = 50000.0
B_BTC_PER_BNB = 0.012


class AssetBalance:
    def __init__(self, name: str, free: float = 0.0, locked: float = 0.0, tag='no tag', precision=8):
        self.name = name
        self.free = free
        self.locked = locked
        self.tag = tag
        self.p = precision

    def __add__(self, other: 'AssetBalance'):
        name = ''
        tag = ''
        if self.name != other.name:
            log.critical(f'error adding symbol balances with different name: {self.name} - {other.name}')
            name = 'error'
        else:
            name = self.name
            tag = self.tag
        free = self.free + other.free
        locked = self.locked + other.locked
        return AssetBalance(name=name, free=free, locked=locked, tag=tag)

    def __sub__(self, other: 'AssetBalance'):
        name = ''
        tag = ''
        if self.name != other.name:
            log.critical(f'error subtracting symbol balances with different name: {self.name} - {other.name}')
            name = 'error'
        else:
            name = self.name
            tag = self.tag
        free = self.free - other.free
        locked = self.locked - other.locked
        return AssetBalance(name=name, free=free, locked=locked, tag=tag)

    def get_total(self) -> float:
        return self.free + self.locked

    def to_dict(self, symbol: str):
        # comparing both to lowercase to do it case-insensitive
        key = ''
        if self.name.lower() == symbol[:3].lower():
            key = 's1'
        elif self.name.lower() == symbol[3:].lower():
            key = 's2'
        elif self.name.lower() == 'bnb':
            key = 'bnb'
        else:
            log.critical(f'name not allowed in asset balance {self}')
        return {key: self}

    def __repr__(self):
        return (f'-> -> BALANCE UPDATE: {self.tag:10} [{self.name}]:    '
                f'balance: {self.get_total():15,.{self.p}f}  -  '
                f'free: {self.free:15,.{self.p}f}  -  '
                f'locked: {self.locked:15,.{self.p}f}')

    def log_print(self):
        print(self)
        log.info(self)


class AccountBalance:
    def __init__(self, d: Dict[str, AssetBalance]):
        # account balance
        self.s1: AssetBalance = d['s1']  # btc
        self.s2 = d['s2']  # eur
        self.bnb = d['bnb']

    def get_free_price_s2(self) -> float:
        return self.s2.free

    def get_free_amount_s1(self) -> float:
        return self.s1.free

    def __add__(self, other: 'AccountBalance') -> 'AccountBalance':
        s1 = self.s1 + other.s1
        s1.tag = 'add'
        s2 = self.s2 + other.s2
        s2.tag = 'add'
        bnb = self.bnb + other.bnb
        bnb.tag = 'add'
        return AccountBalance(d={'s1': s1, 's2': s2, 'bnb': bnb})

    def __sub__(self, other: 'AccountBalance') -> 'AccountBalance':
        s1 = self.s1 - other.s1
        s1.tag = 'diff'
        s2 = self.s2 - other.s2
        s2.tag = 'diff'
        bnb = self.bnb - other.bnb
        bnb.tag = 'diff'
        return AccountBalance(d=dict([('s1', s1), ('s2', s2), ('bnb', bnb)]))

    def __repr__(self):
        log.info(self.s1)
        log.info(self.s2)
        log.info(self.bnb)

    def log_print(self) -> None:
        self.s1.log_print()
        self.s2.log_print()
        self.bnb.log_print()

    def get_btc_equivalent(self) -> float:
        initial_eur_to_btc = self.s2.get_total() / B_EUR_PER_BTC
        initial_bnb_to_btc = self.bnb.get_total() * B_BTC_PER_BNB
        initial_btc_equivalent = self.s1.get_total() + initial_eur_to_btc + initial_bnb_to_btc
        return initial_btc_equivalent


