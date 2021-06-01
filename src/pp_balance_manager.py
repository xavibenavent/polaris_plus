# pp_balance_manager.py

from src.pp_account_balance import AccountBalance
from src.pp_market import Market

class BalanceManager:
    def __init__(self, market: Market):
        self.market = market
        self.initial_ab = self.get_account_balance(tag='initial')
        self.current_ab = self.get_account_balance(tag='current')

        self.balance_total_needed = False
        self.balance_amount_needed = False

    def get_account_balance(self, tag='') -> AccountBalance:
        btc_bal = self.market.get_asset_balance(asset='BTC', tag=tag)
        eur_bal = self.market.get_asset_balance(asset='EUR', tag=tag, p=2)
        bnb_bal = self.market.get_asset_balance(asset='BNB', tag=tag)
        d = dict(s1=btc_bal, s2=eur_bal, bnb=bnb_bal)
        return AccountBalance(d)
