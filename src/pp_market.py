# pp_market.py

import logging
from typing import Callable, Optional

from pp_account_balance import AccountBalance, AssetBalance

log = logging.getLogger('log')


class Market:
    def __init__(self,
                 symbol_ticker_callback: Callable[[float], None],
                 order_traded_callback: Callable[[str, float, float], None],
                 account_balance_callback: Callable[[AccountBalance], None]):

        self.symbol_ticker_callback: Callable[[float], None] = symbol_ticker_callback
        self.order_traded_callback: Callable[[str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[AccountBalance], None] = account_balance_callback

        self.symbol = 'BTCEUR'

    # ********** callback functions **********

    def user_socket_callback(self, msg) -> None:
        # called from Binance API each time an order is traded and
        # each time the account balance changes
        event_type: str = msg['e']
        if event_type == 'executionReport':
            # order traded
            if (msg['x'] == 'TRADE') and (msg["X"] == 'FILLED'):
                # get id, price and commission
                order_id = str(msg['c'])
                order_price = float(msg['L'])
                bnb_commission = float(msg['n'])
                # trigger actions for traded order in session
                self.order_traded_callback(order_id, order_price, bnb_commission)

        elif event_type == 'outboundAccountPosition':
            # account balance change
            balances = msg['B']
            d = {}
            # create dictionary from msg to use in account balance instantiation
            for item in balances:
                # to avoid errors in case of having more assets
                if item['a'] in [self.symbol[:3], self.symbol[3:], 'BNB']:
                    ab = AssetBalance(name=item['a'], free=item['f'], locked=item['l'])
                    d.update(ab.to_dict(symbol=self.symbol))
            account_balance = AccountBalance(d=d)
            self.account_balance_callback(account_balance)

    def symbol_ticker_callback(self, msg) -> None:
        # called from Binance API each time the cmp is updated
        if msg['e'] == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')
        else:
            # trigger actions for new market price
            cmp = float(msg['c'])
            self.symbol_ticker_callback(cmp)
