# test_market.py

import unittest
from typing import Optional

from src.pp_market import Market
from src.pp_account_balance import AccountBalance


class TestMarket(unittest.TestCase):
    def setUp(self) -> None:
        self.market = Market(
            symbol_ticker_callback=self.fake_symbol_ticker_callback,
            order_traded_callback=self.fake_order_traded_callback,
            account_balance_callback=self.fake_account_balance_callback,
            client_mode='simulated'
        )
        self.cmp = 0.0
        self.test_order_id = ''
        self.test_order_price = 0.0
        self.test_bnb_commission = 0.0
        self.test_account_balance: Optional[AccountBalance] = None

    def fake_symbol_ticker_callback(self, cmp: float) -> None:
        self.cmp = cmp

    def fake_order_traded_callback(self,
                                   order_id: str,
                                   order_price: float,
                                   bnb_commission: float) -> None:
        self.test_order_id = order_id
        self.test_order_price = order_price
        self.test_bnb_commission = bnb_commission

    def fake_account_balance_callback(self, ab: AccountBalance) -> None:
        self.test_account_balance = ab

    def test_binance_symbol_ticker_callback_1(self):
        msg = {
                  "e": "24hrTicker",  # Event type
                  "s": "BTCEUR",  # Symbol
                  "c": "60_000.88"  # Last price
                }
        self.market.binance_symbol_ticker_callback(msg=msg)
        # since ic calls the fake callback function, the test is against self.cmp
        self.assertEqual(60_000.88, self.cmp)

    def test_binance_symbol_ticker_callback_2(self):
        msg = {
                  "e": "error",  # Event type
                  "m": "this is the error message"
                }
        self.market.binance_symbol_ticker_callback(msg=msg)

    def test_binance_user_socket_callback_1(self):
        msg = {
                "e": "executionReport",  # Event type
                "E": 1499405658658,  # Event time
                "s": "ETHBTC",  # Symbol
                "c": "mUvoqJxFIILMdfAW5iGSOW",  # Client order ID
                "S": "BUY",  # Side
                "o": "LIMIT",  # Order type
                "f": "GTC",  # Time in force
                "q": "1.00000000",  # Order quantity
                "p": "0.10264410",  # Order price
                "C": "OR_00000001",  # Original client order ID; This is the ID of the order being canceled
                "x": "TRADE",  # Current execution type
                "X": "FILLED",  # Current order status
                "r": "NONE",  # Order reject reason; will be an error code.
                "i": 4293153,  # Order ID
                "L": "49000.88",  # Last executed price
                "n": "0.00038859",  # Commission amount
                "N": "BNB",  # Commission asset
                "T": 1499405658657,  # Transaction time
                "O": 1499405658650,  # Order creation time
                }
        self.market.binance_user_socket_callback(msg=msg)
        self.assertEqual('mUvoqJxFIILMdfAW5iGSOW', self.test_order_id)
        self.assertEqual(49_000.88, self.test_order_price)
        self.assertEqual(0.00038859, self.test_bnb_commission)

    def test_binance_user_socket_callback_2(self):
        msg = {
                "e": "executionReport",  # Event type
                "E": 1499405658658,  # Event time
                "s": "ETHBTC",  # Symbol
                "c": "mUvoqJxFIILMdfAW5iGSOW",  # Client order ID
                "S": "BUY",  # Side
                "o": "LIMIT",  # Order type
                "f": "GTC",  # Time in force
                "q": "1.00000000",  # Order quantity
                "p": "0.10264410",  # Order price
                "C": "OR_00000001",  # Original client order ID; This is the ID of the order being canceled
                "x": "NEW",  # Current execution type
                "X": "NEW",  # Current order status
                "r": "NONE",  # Order reject reason; will be an error code.
                "i": 4293153,  # Order ID
                "L": "49000.88",  # Last executed price
                "n": "0.00038859",  # Commission amount
                "N": "BNB",  # Commission asset
                "T": 1499405658657,  # Transaction time
                "O": 1499405658650,  # Order creation time
                }
        self.market.binance_user_socket_callback(msg=msg)
        self.assertEqual('', self.test_order_id)
        self.assertEqual(0.0, self.test_order_price)
        self.assertEqual(0.0, self.test_bnb_commission)

    def test_binance_user_socket_callback_3(self):
        msg = {
                "e": "outboundAccountPosition",  # Event type
                "E": 1564034571105,  # Event Time
                "u": 1564034571073,  # Time of last account update
                "B": [  # Balances Array
                        {
                            "a": "BTC",  # Asset
                            "f": "80.09080706",  # Free
                            "l": "0.000567"  # Locked
                        },
                        {
                            "a": "BNB",  # Asset
                            "f": "10000.000000",  # Free
                            "l": "1.000000"  # Locked
                        },
                        {
                            "a": "EUR",  # Asset
                            "f": "10000000.08",  # Free
                            "l": "10.04"  # Locked
                        },
                        {
                            "a": "ETH",  # Asset
                            "f": "10000.000000",  # Free
                            "l": "0.000000"  # Locked
                        }
                ]
            }
        self.market.binance_user_socket_callback(msg=msg)
        self.assertAlmostEqual(80.09080706, self.test_account_balance.s1.free)
        self.assertAlmostEqual(10.04, self.test_account_balance.s2.locked)
        self.assertAlmostEqual(1.0, self.test_account_balance.bnb.locked)
        self.assertAlmostEqual(80.09080706, self.test_account_balance.get_free_amount_s1())
        self.assertAlmostEqual(10000000.08, self.test_account_balance.get_free_price_s2())

        self.market.symbol = 'BNBBTC'
        # TODO: it raises an error at AccountBalance __init__() because only 2 parameters are passed
        # self.market.binance_user_socket_callback(msg=msg)
        # self.assertAlmostEqual(10_000.0, self.test_account_balance.s1.free)

