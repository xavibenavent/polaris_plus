# pp_session.py
import logging
import pprint
import sys

from binance import enums as k_binance

from src.pp_market import Market
from src.pp_account_balance import AccountBalance
from src.pp_order import Order, OrderStatus

log = logging.getLogger('log')


class Session:
    def __init__(self, client_mode: str):
        # TODO: remove
        self.status = 0

        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback,
            client_mode=client_mode
        )

        # get filters that will be checked before placing an order
        # TODO: use to check before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol='BTCEUR')

        # test place order
        order = Order(
            order_id='XAVI BENAVENT',
            pt_id='PT_ID',
            k_side=k_binance.SIDE_SELL,
            price=48_150.0,
            amount=0.001,
        )
        # check filters
        if order.filters_check_passed(self.symbol_filters):
            # place order
            d = self.market.place_order(order=order)
            if d:
                order.set_binance_id(new_id=d.get('binance_id'))
                # update status and check potential errors
                status = d.get('status')
                if status == 'NEW':
                    # at this point we have the evidence that
                    # the order has been accepted
                    order.set_status(status=OrderStatus.PLACED)
                elif status != 'FILLED':
                    logging.critical(f'error status received after placing {order}')
                pprint.pprint(d)
            else:
                log.critical(f'error placing {order}')
        else:
            log.critical(f'error checking filters for {order}')

        self.market.stop()
        sys.exit()


    # ********** socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        print(cmp)

    def order_traded_callback(self, order_id: str, order_price: float, bnb_commission: float) -> None:
        pass

    def account_balance_callback(self, ab: AccountBalance) -> None:
        pass
