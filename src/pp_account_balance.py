# pp_account_balance.py
import logging
from typing import List, Dict

log = logging.getLogger('log')


class AssetBalance:
    def __init__(self, name: str, free: float = 0.0, locked: float = 0.0, tag='no tag', precision=6):
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
            log.critical(f'name not allowed in asset balance {self.print()}')
        return {key: self}

    def log(self):
        balance = format(self.get_total(), f"12,.{self.p}f")
        free = format(self.free, f"12,.{self.p}f")
        locked = format(self.locked, f"12,.{self.p}f")
        log.info(f'({self.tag}) [{self.name}]:    balance: {balance}   free: {free}   locked: {locked}')

    def print(self):
        balance = format(self.get_total(), f"12,.{self.p}f")
        free = format(self.free, f"12,.{self.p}f")
        locked = format(self.locked, f"12,.{self.p}f")
        print(f'({self.tag}) [{self.name}]:    balance: {balance}   free: {free}   locked: {locked}')

    def log_print(self):
        self.log()
        self.print()


class AccountBalance:
    def __init__(self, d: Dict[str, AssetBalance]):
        # account balance
        self.s1 = d['s1']  # btc
        self.s2 = d['s2']  # eur
        self.bnb = d['bnb']

    def get_free_price_s2(self) -> float:
        return self.s2.free

    def get_free_amount_s1(self) -> float:
        return self.s1.free

    def __add__(self, other: 'AccountBalance') -> 'AccountBalance':
        s1 = self.s1 + other.s1
        s2 = self.s2 + other.s2
        bnb = self.bnb + other.bnb
        return AccountBalance(d={'s1': s1, 's2': s2, 'bnb': bnb})

    def __sub__(self, other: 'AccountBalance') -> 'AccountBalance':
        s1 = self.s1 - other.s1
        s2 = self.s2 - other.s2
        bnb = self.bnb - other.bnb
        return AccountBalance(d=dict([('s1', s1), ('s2', s2), ('bnb', bnb)]))

    def log_print(self) -> None:
        self.s1.log_print()
        self.s2.log_print()
        self.bnb.log_print()