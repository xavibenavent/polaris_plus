# pp_orders_book.py

import logging
from typing import List
from binance import enums as k_binance

from src.pp_order import Order, OrderStatus
from src.xb_pt_calculator import get_compensation
from src.pp_dbmanager import DBManager

log = logging.getLogger('log')


class OrdersBook:
    def __init__(self, orders: List[Order], dbm: DBManager, table: str):
        # e = True
        # if e:
        #     raise AssertionError
        self.orders = []
        self.buy = []
        self.sell = []

        self.dbm = dbm
        self.table = table

        # add each order to its appropriate list
        for order in orders:
            # self.add_order(order)
            self.orders.append(order)

    def add_order(self, order: Order) -> None:
        self.orders.append(order)
        # if order.k_side == k_binance.SIDE_BUY:
        #     self.buy.append(order)
        # else:
        #     self.sell.append(order)

    def remove_order(self, order: Order) -> None:
        self.orders.remove(order)
        # if order.k_side == k_binance.SIDE_BUY:
        #     self.buy.remove(order)
        # else:
        #     self.sell.remove(order)

    def get_all_orders(self) -> List[Order]:
        # return self.buy + self.sell
        return self.orders

    def get_order(self, uid: str) -> Order:
        # for order in self.get_all_orders():
        for order in orders:
            if order.uid == uid:
                return order

    def count(self) -> int:
        # return len(self.get_all_orders())
        return len(self.orders)

    def buy_count(self) -> int:
        return len(self.buy)

    def sell_count(self) -> int:
        return len(self.sell)

    def get_side_diff(self) -> int:
        return self.sell_count() - self.buy_count()

    def compensate_order(self, order: Order, ref_mp: float, ref_gap: float, buy_fee: float, sell_fee: float) -> None:
        pass
        s1_p, b1_p, s1_qty, b1_qty = get_compensation(
            cmp=ref_mp,
            gap=ref_gap,
            qty_bal=order.get_signed_amount(),
            price_bal=order.get_signed_total(),
            buy_fee=buy_fee,
            sell_fee=sell_fee
        )

        # validate data received
        if s1_p < 0 or b1_p < 0 or s1_qty < 0 or b1_qty < 0:
            log.critical(f'!!!!!!!!!! negative value(s) after compensation: b1p: {b1_p} - b1q: {b1_qty} !!!!!!!!!!'
                         f'- s1p: {s1_p} - s1q: {s1_qty}')
        elif s1_qty > 0.4 or b1_qty > 0.4:
            log.critical(f'!!!!!!!!!! exceeded max qty:    b1q: {b1_qty} - s1q: {s1_qty} !!!!!!!!!!')
        else:
            # create both orders
            b1 = Order(
                session_id=order.session_id,
                order_id='COMPENSATED',
                pt_id=order.pt_id,
                k_side=k_binance.SIDE_BUY,
                price=b1_p,
                amount=b1_qty,
                status=OrderStatus.MONITOR,
                uid=order.uid
            )
            s1 = Order(
                session_id=order.session_id,
                order_id='COMPENSATED',
                pt_id=order.pt_id,
                k_side=k_binance.SIDE_SELL,
                price=s1_p,
                amount=s1_qty,
                status=OrderStatus.MONITOR,
                uid=order.uid
            )
            # add new orders to appropriate list
            self.orders.append(b1)
            self.orders.append(s1)
            # self.buy.append(b1)
            # self.sell.append(s1)
            # delete original order from list
            self.orders.remove(order)
            # self.remove_order(order)
            # delete original order from pending_orders table
            self.dbm.delete_order(order=order, table=self.table)