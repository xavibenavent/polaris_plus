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
        self.monitor = []
        self.placed = []

        self.dbm = dbm
        self.table = table

        # add each order to its appropriate list
        for order in orders:
            self.monitor.append(order)

    def add_order(self, order: Order) -> None:
        self.monitor.append(order)

    def remove_order(self, order: Order) -> None:
        self.monitor.remove(order)

    def place_order(self, order: Order) -> None:
        if order in self.monitor:
            self.monitor.remove(order)
            self.placed.append(order)
            # in session, once placement confirmed, will be set to status PLACED
            order.set_status(OrderStatus.TO_BE_PLACED)
        else:
            log.critical(f'trying to place an order not found in the monitor list: {order}')

    def place_back_order(self, order: Order) -> None:
        if order in self.placed:
            self.placed.remove(order)
            self.monitor.append(order)
            order.set_status(OrderStatus.MONITOR)
        else:
            log.critical(f'trying to place back to monitor an order not found in the placed list: {order}')

    def get_all_orders(self) -> List[Order]:
        return self.monitor

    def get_order(self, uid: str) -> Order:
        # for order in self.get_all_orders():
        for order in self.monitor:
            if order.uid == uid:
                return order

    def count(self) -> int:
        return len(self.monitor)

    # def buy_count(self) -> int:
    #     return len(self.buy)
    #
    # def sell_count(self) -> int:
    #     return len(self.sell)

    # def get_side_diff(self) -> int:
    #     return self.sell_count() - self.buy_count()

    def compensate_order(self, order: Order, ref_mp: float, ref_gap: float, buy_fee: float, sell_fee: float) -> bool:
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
        elif s1_qty > 0.07 or b1_qty > 0.07:
            log.critical(f'!!!!!!!!!! exceeded max qty:    b1q: {b1_qty} - s1q: {s1_qty} !!!!!!!!!!')
        else:
            # create both orders
            b1 = Order(
                session_id=order.session_id,
                order_id='COMPENSATED',
                pt_id=order.pt_id + '-C',
                k_side=k_binance.SIDE_BUY,
                price=b1_p,
                amount=b1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid()
            )
            s1 = Order(
                session_id=order.session_id,
                order_id='COMPENSATED',
                pt_id=order.pt_id + '-C',
                k_side=k_binance.SIDE_SELL,
                price=s1_p,
                amount=s1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid()
            )
            # add new orders to appropriate list
            # self.monitor.append(b1)
            # self.monitor.append(s1)
            # add new orders to pending_orders table
            # TODO: check it
            # self.dbm.add_order(order=b1, table=self.table)
            # delete original order from list
            self.monitor.remove(order)
            # delete original order from pending_orders table
            self.dbm.delete_order(order=order, table=self.table)
            # log
            # log.info('////////// ORDER COMPENSATED //////////')
            # log.info(f'initial order:  {order}')
            # log.info(f'compensated b1: {b1}')
            # log.info(f'compensated s1: {s1}')

            # split into 3 orders
            self._split_order(order=b1, d=25)
            self._split_order(order=s1, d=25)

            return True
        # if not compensated
        order.order_id = 'COMPENSATED_FINAL'
        return False

    def split_order(self, order: Order, d: float):
        self._split_order(order=order, d=d)
        # remove now because it is not done in _split_order(), since
        # the order passed from compensate_order() has not been added to
        # the monitor list neither to the table
        self.monitor.remove(order)
        self.dbm.delete_order(order=order, table=self.table)

    def _split_order(self, order: Order, d: float):
        # create 3 new orders
        left = Order(
            session_id=order.session_id,
            order_id='COMPENSATED_SPLIT',
            pt_id=order.pt_id + '-L',
            k_side=order.k_side,
            price=order.price - d,
            amount=order.amount / 2.0,
            status=OrderStatus.MONITOR,
            uid=Order.get_new_uid()
        )
        # center = Order(
        #     session_id=order.session_id,
        #     order_id='COMPENSATED_SPLIT',
        #     pt_id=order.pt_id + '-CC',
        #     k_side=order.k_side,
        #     price=order.price,
        #     amount=order.amount / 3.0,
        #     status=OrderStatus.MONITOR,
        #     uid=Order.get_new_uid()
        # )
        right = Order(
            session_id=order.session_id,
            order_id='COMPENSATED_SPLIT',
            pt_id=order.pt_id + '-R',
            k_side=order.k_side,
            price=order.price + d,
            amount=order.amount / 2.0,
            status=OrderStatus.MONITOR,
            uid=Order.get_new_uid()
        )

        # add orders to orders book
        self.monitor.append(left)
        # self.monitor.append(center)
        self.monitor.append(right)
        # delete original order from orders book
        # self.monitor.remove(order)
        # add orders to pending orders table
        # TODO: check it
        self.dbm.add_order(order=left, table=self.table)
        # self.dbm.add_order(order=center, table=self.table)
        self.dbm.add_order(order=right, table=self.table)
        # delete original order from pending orders table
        # self.dbm.delete_order(order=order, table=self.table)
        # log
        log.info('////////// ORDER SPLIT //////////')
        log.info(f'initial order:  {order}')
        log.info(f'left:   {left}')
        # log.info(f'center: {center}')
        log.info(f'right:  {right}')
