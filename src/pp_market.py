# pp_market.py
import pprint
import sys
import logging
from typing import Callable, Union, Any, Optional, List
from twisted.internet import reactor
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance import enums as k_binance
from binance import  exceptions

from binance.exceptions import BinanceAPIException
from binance.exceptions import BinanceRequestException
from binance.exceptions import BinanceOrderException
from binance.exceptions import BinanceOrderMinAmountException
from binance.exceptions import BinanceOrderMinPriceException
from binance.exceptions import BinanceOrderMinTotalException
from binance.exceptions import BinanceOrderUnknownSymbolException
from binance.exceptions import BinanceOrderInactiveSymbolException

from requests.exceptions import ConnectionError, ReadTimeout

from src.pp_order import Order
from src.pp_account_balance import AccountBalance, AssetBalance
from src.pp_simulated_client import SimulatedClient

log = logging.getLogger('log')


class Market:
    def __init__(self,
                 symbol_ticker_callback: Callable[[float], None],
                 order_traded_callback: Callable[[str, float, float], None],
                 account_balance_callback: Callable[[AccountBalance], None],
                 client_mode: str):

        self.symbol_ticker_callback: Callable[[float], None] = symbol_ticker_callback
        self.order_traded_callback: Callable[[str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[AccountBalance], None] = account_balance_callback
        self.client_mode = client_mode
        # symbol must be passed as argument o get from configuration file
        self.symbol = 'BTCEUR'

        # set control flags
        self.is_symbol_ticker_on = False  # when off symbol ticker socket U/S

        # create client depending on client_mode parameter
        self.client: Union[Client, SimulatedClient]
        self.client, self.simulator_mode = self.set_client(client_mode)

        # self.start_sockets()

    def start_sockets(self):
        if not self.simulator_mode:
            # sockets only started in binance mode (not in simulator mode)
            self._start_sockets()
        log.info(f'client initiated in {self.client_mode} mode')

    # ********** callback functions **********

    def binance_user_socket_callback(self, msg) -> None:
        # called from Binance API each time an order is traded and
        # each time the account balance changes
        event_type: str = msg['e']
        if event_type == 'executionReport':
            if (msg['x'] == 'TRADE') and (msg["X"] == 'FILLED'):
                # order traded
                order_id = str(msg['c'])
                order_price = float(msg['L'])
                bnb_commission = float(msg['n'])
                # trigger actions for traded order in session
                self.order_traded_callback(order_id, order_price, bnb_commission)
            elif (msg['x'] == 'NEW') and (msg["X"] == 'NEW'):
                # order accepted (PLACE confirmation)
                # not used by the moment
                pass

        elif event_type == 'outboundAccountPosition':
            # account balance change
            balances = msg['B']
            d = {}
            # create dictionary from msg to use in account balance instantiation
            for item in balances:
                # to avoid errors in case of having more assets
                if item['a'] in ['BTC', 'EUR', 'BNB']:
                    # set precision
                    if item['a'] in ['BTC', 'BNB']:
                        p = 8
                    else:
                        p = 2
                    ab = AssetBalance(
                        name=item['a'],
                        free=float(item['f']),
                        locked=float(item['l']),
                        tag='current',
                        precision=p)
                    d.update(ab.to_dict(symbol=self.symbol))
            account_balance = AccountBalance(d=d)
            self.account_balance_callback(account_balance)

    def binance_symbol_ticker_callback(self, msg: Any) -> None:
        # called from Binance API each time the cmp is updated
        if msg['e'] == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')
        elif msg['e'] == '24hrTicker':
            # trigger actions for new market price
            cmp = float(msg['c'])
            self.symbol_ticker_callback(cmp)
        else:
            log.critical(f'event type not expected: {msg["e"]}')

    # ********** calls to binance api **********

    def place_order(self, order: Order) -> Optional[dict]:
        # TODO: check and test it
        try:
            msg = self.client.create_order(
                symbol='BTCEUR',
                side=order.k_side,
                type=k_binance.ORDER_TYPE_LIMIT,
                timeInForce=k_binance.TIME_IN_FORCE_GTC,
                # TODO: check precision
                quantity=order.get_amount(precision=8),
                price=order.get_price_str(precision=8),
                newClientOrderId=order.uid)
            if msg:
                d = dict(binance_id=msg['orderId'], status=msg.get('status'))
                return d
            else:
                log.critical(f'error when placing order {order}')
        except (
                BinanceRequestException, BinanceAPIException,
                BinanceOrderException, BinanceOrderMinAmountException,
                BinanceOrderMinPriceException, BinanceOrderMinTotalException,
                BinanceOrderUnknownSymbolException,
                BinanceOrderInactiveSymbolException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout) as e:
            log.critical(e)
        return None  # msg['orderId'], msg['status'] == 'FILLED' or 'NEW'

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        # return dict with the required values for checking order values
        try:
            d = self.client.get_symbol_info(symbol)
            if d:
                base_precision = int(d.get('baseAssetPrecision'))  # symbol 1
                max_price = float(d.get('filters')[0].get('maxPrice'))
                min_price = float(d.get('filters')[0].get('minPrice'))
                max_qty = float(d.get('filters')[2].get('maxQty'))
                min_qty = float(d.get('filters')[2].get('minQty'))
                min_notional = float(d.get('filters')[3].get('minNotional'))  # price * qty
                quote_precision = int(d.get('quoteAssetPrecision'))  # symbol 2
                return dict(base_precision=base_precision,
                            max_price=max_price,
                            min_price=min_price,
                            max_qty=max_qty,
                            min_qty=min_qty,
                            min_notional=min_notional,
                            quote_precision=quote_precision)
            else:
                log.critical(f'no symbol info from Binance for {symbol}')
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        return None

    def get_asset_balance(self, asset: str, tag: str, p=8) -> AssetBalance:
        try:
            d = self.client.get_asset_balance(asset)
            free = float(d.get('free'))
            locked = float(d.get('locked'))
            return AssetBalance(name=asset, free=free, locked=locked, tag=tag, precision=p)
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)

    def cancel_all_placed_orders(self, orders: List[Order]):
        log.info('********** CANCELLING ALL PLACED ORDERS **********')
        for order in orders:
            try:
                d = self.client.cancel_order(symbol='BTCEUR', origClientOrderId=order.uid)
                log.info(f'{order} CANCELLED IN BINANCE')
            except (BinanceAPIException, BinanceRequestException) as e:
                log.critical(e)

    # ********** binance configuration methods **********

    @staticmethod
    def set_client(client_mode) -> (Union[Client, SimulatedClient], bool):
        client: Union[Client, SimulatedClient]
        is_simulator_mode = False
        if client_mode == 'binance':
            api_keys = {
                "key": "JkbTNxP0s6x6ovKcHTWYzDzmzLuKLh6g9gjwHmvAdh8hpsOAbHzS9w9JuyYD9mPf",
                "secret": "IWjjdrYPyaWK4yMyYPIRhdiS0I7SSyrhb7HIOj4vjDcaFMlbZ1ygR6I8TZMUQ3mW"
            }
            client = Client(api_keys['key'], api_keys['secret'])
        elif client_mode == 'simulated':
            client = SimulatedClient()
            is_simulator_mode = True
        else:
            log.critical(f'client_mode {client_mode} not accepted')
            sys.exit()
        return client, is_simulator_mode

    def _start_sockets(self):
        # init socket manager
        self._bsm = BinanceSocketManager(client=self.client)

        # symbol ticker socket
        self._symbol_ticker_s = self._bsm.start_symbol_ticker_socket(
            symbol=self.symbol,
            callback=self.binance_symbol_ticker_callback)

        # user socket
        self._user_s = self._bsm.start_user_socket(
            callback=self.binance_user_socket_callback
        )

        # start sockets
        self._bsm.start()

    def stop(self):
        self._bsm.stop_socket(self._symbol_ticker_s)
        self._bsm.stop_socket(self._user_s)

        # properly close the WebSocket, only if it is running
        # trying to stop it when it is not running, will raise an error
        if reactor.running:
            reactor.stop()

    """
        response RESULT (default response type):
        {
            "symbol": "BTCUSDT",
            "orderId": 28,
            "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
            "transactTime": 1507725176595,
            "price": "0.00000000",
            "origQty": "10.00000000",
            "executedQty": "10.00000000",
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "MARKET",
            "side": "SELL"
        }
    """
