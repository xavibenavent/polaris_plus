# pp_market.py

import sys
import logging
from typing import Callable, Union, Any
from twisted.internet import reactor
from binance.client import Client
from binance.websockets import BinanceSocketManager

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

        # symbol must be passed as argument o get from configuration file
        self.symbol = 'BTCEUR'

        # set control flags
        self.is_symbol_ticker_on = False  # when off symbol ticker socket U/S

        # create client depending on client_mode parameter
        self.client: Union[Client, SimulatedClient]
        self.client, simulator_mode = self.set_client(client_mode)

        if not simulator_mode:
            # sockets only started in binance mode (not in simulator mode)
            self._start_sockets()

        log.info(f'client initiated in {client_mode} mode')

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
                # TODO: do not use BNB in symbol because a known error would be raised
                if item['a'] in [self.symbol[:3], self.symbol[3:], 'BNB']:
                    ab = AssetBalance(name=item['a'], free=float(item['f']), locked=float(item['l']))
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
