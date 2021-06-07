# pp_balance_manager.py

from typing import List
from binance import enums as k_binance

from src.pp_account_balance import AccountBalance
from src.pp_market import Market
from src.pp_order import Order

EUR_MIN_BALANCE = 1000.0  # 2000.0  # remaining guaranteed EUR balance
BTC_MIN_BALANCE = 0.02  # 0.04  # remaining guaranteed BTC balance

# below _MIN_BALANCE + BUFFER some liquidity will be forced
EUR_BUFFER = 1000.0
BTC_BUFFER = 0.02


class BalanceManager:
    def __init__(self, market: Market):
        self.market = market

        # account balances: initial, current and diff
        self.initial_ab = self.get_account_balance(tag='initial')
        self.current_ab = self.get_account_balance(tag='current')
        self.net_ab = self.current_ab - self.initial_ab

    def update_current(self, last_ab: AccountBalance) -> None:
        self.current_ab = last_ab
        self.net_ab = last_ab - self.initial_ab

    def is_s2_below_buffer(self):
        buffer = EUR_BUFFER + EUR_MIN_BALANCE
        return self.current_ab.s2.get_total() < buffer  # total = free + locked

    def is_s1_below_buffer(self):
        buffer = BTC_BUFFER + BTC_MIN_BALANCE
        return self.current_ab.s1.get_total() < buffer

    def get_account_balance(self, tag='') -> AccountBalance:
        btc_bal = self.market.get_asset_balance(asset='BTC', tag=tag)
        eur_bal = self.market.get_asset_balance(asset='EUR', tag=tag, p=2)
        bnb_bal = self.market.get_asset_balance(asset='BNB', tag=tag)
        d = dict(s1=btc_bal, s2=eur_bal, bnb=bnb_bal)
        return AccountBalance(d)

    def is_balance_enough(self, order: Order) -> (bool, float):
        # if not enough balance, it returns False and the balance needed
        is_balance_enough = False
        if order.k_side == k_binance.SIDE_BUY:
            balance_allowance = self.current_ab.get_free_price_s2()
            available_liquidity = balance_allowance - EUR_MIN_BALANCE  # [EUR]
            if (available_liquidity - order.get_total()) > 0:
                is_balance_enough = True
        else:  # SIDE_SELL
            balance_allowance = self.current_ab.get_free_amount_s1()
            available_liquidity = balance_allowance - BTC_MIN_BALANCE  # [BTC]
            if (available_liquidity - order.amount) > 0:
                is_balance_enough = True

        return is_balance_enough

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float, float, float):
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
