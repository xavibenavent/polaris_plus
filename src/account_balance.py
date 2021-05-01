# account_balance.py
import logging
from typing import List

log = logging.getLogger('log')


class SymbolBalance:
    def __init__(self, name: str, free: float = 0.0, locked: float = 0.0, tag='no tag', precision=6):
        self.name = name
        self.free = free
        self.locked = locked
        self.tag = tag
        self.p = precision

    def __add__(self, other: 'SymbolBalance'):
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
        return SymbolBalance(name=name, free=free, locked=locked, tag=tag)

    def __sub__(self, other: 'SymbolBalance'):
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
        return SymbolBalance(name=name, free=free, locked=locked, tag=tag)

    def get_total(self) -> float:
        return self.free + self.locked

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
    def __init__(self, sb_list: List[SymbolBalance]):
        # account balance
        self.ab : List[SymbolBalance] = []
        for sb in sb_list:
            self.ab.append(sb)

    def __add__(self, other: 'AccountBalance') -> 'AccountBalance':
        add: List[SymbolBalance] = []
        if len(self.ab) != len(other.ab):
            log.critical('error adding account balances with different symbols list:')
            return self
        else:
            for sb in range(0, len(self.ab)):
                add.append(self.ab[sb] + other.ab[sb])
            return AccountBalance(sb_list=add)

    def __sub__(self, other: 'AccountBalance') -> 'AccountBalance':
        sub: List[SymbolBalance] = []
        if len(self.ab) != len(other.ab):
            log.critical('error subtracting account balances with different symbols list:')
            return self
        else:
            for sb in range(0, len(self.ab)):
                sub.append(self.ab[sb] - other.ab[sb])
            return AccountBalance(sb_list=sub)

    def log_print(self) -> None:
        for symbol_balance in self.ab:
            symbol_balance.log_print()