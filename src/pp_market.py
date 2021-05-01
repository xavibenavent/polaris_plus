# pp_market.py

import logging
from typing import Any, Callable

log = logging.getLogger('log')


class Market:
    def __init__(self,
                 symbol_ticker_callback: Callable[[float], None],
                 order_traded_callback: Callable[[str, float, float], None]):

        self.symbol_ticker_callback: Callable[[float], None] = symbol_ticker_callback
        self.order_traded_callback: Callable[[str, float, float], None] = order_traded_callback


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
            self._update_global_balance_callback(msg['B'])

    def symbol_ticker_callback(self, msg) -> None:
        # called from Binance API each time the cmp is updated
        if msg['e'] == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')
        else:
            # trigger actions for new market price
            self.symbol_ticker_callback(float(msg['c']))
