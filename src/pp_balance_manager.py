# pp_balance_manager.py

from typing import List
from binance import enums as k_binance

from src.pp_account_balance import AccountBalance
from src.pp_market import Market
from src.pp_order import Order

B_TOTAL_BUFFER = 2000.0  # remaining guaranteed EUR balance
B_AMOUNT_BUFFER = 0.04  # remaining guaranteed BTC balance


class BalanceManager:
    def __init__(self, market: Market):
        self.market = market

        # account balances: initial, current and diff
        self.initial_ab = self.get_account_balance(tag='initial')
        self.current_ab = self.get_account_balance(tag='current')
        self.net_ab = self.current_ab - self.initial_ab

        # self.balance_total_needed = False
        # self.balance_amount_needed = False

    def update_current(self, last_ab: AccountBalance) -> None:
        self.current_ab = last_ab
        self.net_ab = last_ab - self.initial_ab

    def get_account_balance(self, tag='') -> AccountBalance:
        btc_bal = self.market.get_asset_balance(asset='BTC', tag=tag)
        eur_bal = self.market.get_asset_balance(asset='EUR', tag=tag, p=2)
        bnb_bal = self.market.get_asset_balance(asset='BNB', tag=tag)
        d = dict(s1=btc_bal, s2=eur_bal, bnb=bnb_bal)
        return AccountBalance(d)

    def is_balance_enough(self, order: Order) -> (bool, float):
        # if not enough balance, it returns False and the balance needed
        is_balance_enough = False
        balance_needed = 0.0
        balance_amount_needed = False
        balance_total_needed = False
        # compare allowance with needed depending on the order side
        if order.k_side == k_binance.SIDE_BUY:
            balance_allowance = self.current_ab.get_free_price_s2()
            balance_needed = order.get_total()
            if (balance_allowance - balance_needed) > B_TOTAL_BUFFER:
                is_balance_enough = True
            else:
                # eur needed => SELL
                balance_total_needed = True
        else:
            balance_allowance = self.current_ab.get_free_amount_s1()
            balance_needed = order.amount
            if (balance_allowance - balance_needed) > B_AMOUNT_BUFFER:
                is_balance_enough = True
            else:
                # btc needed => BUY
                balance_amount_needed = True

        return is_balance_enough, balance_needed  # in fact the balance needed will be less

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float, float):
        balance_amount = 0.0
        balance_total = 0.0
        balance_commission = 0.0
        comm_btc = 0.0
        for order in orders:
            balance_amount += order.get_signed_amount()
            balance_total += order.get_signed_total()
            balance_commission += order.bnb_commission
            comm_btc += order.btc_commission
        return balance_amount, balance_total, balance_commission, comm_btc

