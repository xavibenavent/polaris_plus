# test_orders_book.py

import unittest

from src.pp_order import Order, OrderStatus
from src.pp_pending_orders_book import PendingOrdersBook
from binance import enums as k_binance

import pandas as pd


class FakeDBManager:
    def delete_order(self, table: str, order: Order):
        pass


class TestOrdersBook(unittest.TestCase):
    def setUp(self) -> None:
        m1 = Order(
            session_id='S_TEST',
            order_id='OR_M1',
            pt_id='PT_ID',
            k_side=k_binance.SIDE_BUY,
            price=47300.0,
            amount=0.012,
            uid='abcdef0123456789'
        )

        m2 = Order(
            session_id='S_TEST',
            order_id='OR_M2',
            pt_id='PT_ID',
            k_side=k_binance.SIDE_SELL,
            price=47900.0,
            amount=0.012,
            uid='0123456789abcdef'
        )
        orders = [m1, m2]
        dbm = FakeDBManager()
        table = 'test_table'

        # create orders book
        self.orders_book = PendingOrdersBook(orders=orders, dbm=dbm, table=table)

    def test_init(self):
        self.assertEqual(47300.0, self.orders_book.buy[0].price)

    def test_compensate_order_buy(self):
        self.orders_book.compensate_order(
            order=self.orders_book.buy[0],
            ref_mp=47600.0,
            ref_gap=100.0,
            buy_fee=0.00075,
            sell_fee=0.00075
        )
        print('buy list:')
        for order in self.orders_book.buy:
            print(order)
        print('sell list:')
        for order in self.orders_book.sell:
            print(order)

    def test_compensate_order_sell(self):
        self.orders_book.compensate_order(
            order=self.orders_book.sell[0],
            ref_mp=47600.0,
            ref_gap=100.0,
            buy_fee=0.00075,
            sell_fee=0.00075
        )
        print('buy list:')
        for order in self.orders_book.buy:
            print(order)
        print('sell list:')
        for order in self.orders_book.sell:
            print(order)

    def test_get_all_orders(self):
        all_orders = self.orders_book.get_monitor_orders()
        self.assertEqual(2, len(all_orders))
        # check creation of dataframe from objects list
        df = pd.DataFrame([order.__dict__ for order in all_orders])
        print(df)

    def test_get_order(self):
        order = self.orders_book.get_order(uid='0123456789abcdef')
        self.assertEqual(47900.0, order.price)

    def test_count(self):
        c = self.orders_book.count()
        self.assertEqual(2, c)

    def test_get_side_diff(self):
        diff = self.orders_book.get_side_diff()
        self.assertEqual(0, diff)
