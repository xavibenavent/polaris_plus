# test_order.py

import unittest
from binance import enums as k_binance

from src.pp_order import Order, OrderStatus


class TestOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.order = Order(
            session_id='S_20210501_2008',
            order_id='ORDER_ID',
            pt_id='PT_ID',
            k_side=k_binance.SIDE_BUY,
            price=50_000.0,
            amount=1.0,
        )

        self.order_2 = Order(
            session_id='S_20210501_2008',
            order_id='OR_000001',
            pt_id='PT_000001',
            k_side=k_binance.SIDE_SELL,
            price=60_000.88,
            amount=1.0876548765,
            uid='0123456789abcdef'
        )

    def test_init(self):
        self.assertNotEqual('', self.order.uid)
        print(self.order)
        self.assertEqual('0123456789abcdef', self.order_2.uid)
        self.assertEqual('MONITOR', self.order.status.name)
        print(self.order_2)

    def test_is_ready_for_placement(self):
        self.assertTrue(self.order.is_ready_for_placement(cmp=50_020.0, min_dist=25))
        self.assertTrue(self.order.is_ready_for_placement(cmp=49_000.0, min_dist=25))
        self.assertFalse(self.order.is_ready_for_placement(cmp=50_050.0, min_dist=25))
        self.assertTrue(self.order_2.is_ready_for_placement(cmp=59_975.0, min_dist=30))
        self.assertTrue(self.order_2.is_ready_for_placement(cmp=60_100.0, min_dist=25))
        self.assertFalse(self.order_2.is_ready_for_placement(cmp=59_500.0, min_dist=100))

    def test_get_distance(self):
        self.assertEqual(500.0, self.order.get_distance(cmp=50500.0))
        self.assertEqual(-500.0, self.order.get_distance(cmp=49500.0))
        self.assertAlmostEqual(0.88, self.order_2.get_distance(cmp=60_000.0))
        self.assertAlmostEqual(-0.12, self.order_2.get_distance(cmp=60_001.0))

    def test_get_price_str(self):
        self.assertEqual('60000.88', self.order_2.get_price_str())
        self.assertEqual('60000.880000', self.order_2.get_price_str(precision=6))

    def test_get_amount(self):
        self.assertEqual(1.087655, self.order_2.get_amount())
        self.assertEqual(1.09, self.order_2.get_amount(precision=2))

    def test_get_total(self):
        self.assertAlmostEqual(50_000.0, self.order.get_total())
