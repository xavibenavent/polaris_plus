# pp_orders_book.py

import pandas as pd
import plotly.express as px
import logging
from typing import List
from binance import enums as k_binance

from src.pp_order import Order, OrderStatus
from src.xb_pt_calculator import get_compensation
from src.pp_dbmanager import DBManager
# from src.pp_session import DATABASE_FILE, PENDING_ORDERS_TABLE

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

    def compensate_order(self,
                         order: Order,
                         ref_mp: float,
                         ref_gap: float,
                         buy_fee: float,
                         sell_fee: float) -> List[Order]:
        # return a list with the two orders resulting from the compensation
        # if limits are exceeded, then the list is empty
        new_orders = []
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
                pt_id=order.pt_id,  # + '-CO',
                k_side=k_binance.SIDE_BUY,
                price=b1_p,
                amount=b1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name=order.name + '-CB-'
            )
            s1 = Order(
                session_id=order.session_id,
                order_id='COMPENSATED',
                pt_id=order.pt_id,  # + '-CO',
                k_side=k_binance.SIDE_SELL,
                price=s1_p,
                amount=s1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name=order.name + '-CS-'
            )
            # add new orders to appropriate list
            self.monitor.append(b1)
            self.monitor.append(s1)

            # add new orders to pending_orders table
            self.dbm.add_order(order=b1, table=self.table)
            self.dbm.add_order(order=s1, table=self.table)

            # delete original order from list
            self.monitor.remove(order)

            # delete original order from pending_orders table
            self.dbm.delete_order(order=order, table=self.table)

            # log
            log.info('////////// ORDER COMPENSATED //////////')
            log.info(f'initial order:  {order}')
            log.info(f'compensated b1: {b1}')
            log.info(f'compensated s1: {s1}')

            new_orders.append(b1)
            new_orders.append(s1)

            b1.compensation_count = order.compensation_count + 1
            s1.compensation_count = order.compensation_count + 1

        return new_orders

    def split_order(self, order: Order, d: float, child_count: int) -> List[Order]:
        # return a list with the child orders
        # child_count should be 2 or 3
        new_orders = []

        log.info('////////// ORDER SPLIT //////////')
        log.info(f'initial order:  {order}')

        left = Order(
            session_id=order.session_id,
            order_id='CHILD',
            pt_id=order.pt_id,  # + '-L',
            k_side=order.k_side,
            price=order.price - d,
            amount=order.amount / child_count,
            status=OrderStatus.MONITOR,
            uid=Order.get_new_uid(),
            name=order.name + 'L'
        )
        left.split_count = order.split_count + 1
        # add to monitor and pending_orders table
        self.monitor.append(left)
        self.dbm.add_order(order=left, table=self.table)
        log.info(f'left:   {left}')

        right = Order(
            session_id=order.session_id,
            order_id='CHILD',
            pt_id=order.pt_id,  # + '-R',
            k_side=order.k_side,
            price=order.price + d,
            amount=order.amount / child_count,
            status=OrderStatus.MONITOR,
            uid=Order.get_new_uid(),
            name=order.name + 'R'
        )
        right.split_count = order.split_count + 1
        # add to monitor and pending_orders table
        self.monitor.append(right)
        self.dbm.add_order(order=right, table=self.table)
        log.info(f'right:  {right}')

        if child_count == 3:
            center = Order(
                session_id=order.session_id,
                order_id='CHILD',
                pt_id=order.pt_id,  # + '-C',
                k_side=order.k_side,
                price=order.price,
                amount=order.amount / child_count,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name=order.name + 'C'
            )
            center.split_count = order.split_count + 1
            # add to monitor and pending_orders table
            self.monitor.append(center)
            self.dbm.add_order(order=center, table=self.table)
            log.info(f'center: {center}')

        # delete original order from orders book
        self.monitor.remove(order)

        # delete original order from pending orders table
        self.dbm.delete_order(order=order, table=self.table)

        return new_orders

    # ********* pandas methods **********

    def show_orders_graph(self):
        pass
        # cnx = DBManager.create_connection(file_name='src/database/orders.db')
        # df_po = pd.read_sql_query(f'SELECT * FROM pending_orders', cnx)
        # df_to = pd.read_sql_query(f'SELECT * FROM traded_orders', cnx)
        # df_po['status'] = 'monitor'
        # df_to['status'] = 'traded'
        # dff = df_po.append(other=df_to)
        #
        # fig = px.scatter(dff,
        #                  x='price',
        #                  y='amount',
        #                  color='side',
        #                  color_discrete_map={'BUY': 'green', 'SELL': 'red'},
        #                  symbol='status',
        #                  symbol_map={'monitor': 'circle', 'traded': 'cross'}
        #                  )
        # fig.update_traces(marker_size=25)
        #
        # fig.show()

    def get_pending_orders_df(self) -> pd.DataFrame:
        # create dataframe from orders list
        df_monitor = pd.DataFrame([order.__dict__ for order in self.monitor])
        df_monitor['status'] = 'monitor'
        df_placed = pd.DataFrame([order.__dict__ for order in self.placed])
        df_placed['status'] = 'placed'
        # append both dataframes
        df_pending = df_monitor.append(other=df_placed)
        return df_pending

    @staticmethod
    def get_depth() -> float:
        # difference between first sell and buy
        na, min_sell_price, max_buy_price, nb = OrdersBook.get_price_limits()
        # if there are no buy sells then both buy values are 0
        # the same applies for sell side
        return abs(min_sell_price - max_buy_price)

    @staticmethod
    def get_span() -> float:
        # difference between last sell and buy
        # df = OrdersBook.get_df_from_pending_orders_table()
        max_sell_price, na, nb, min_buy_price = OrdersBook.get_price_limits()
        return max_sell_price - min_buy_price

    @staticmethod
    def get_price_limits() -> (float, float, float, float):
        # default return values
        max_sell_price = 0
        min_sell_price = 0
        max_buy_price = 0
        min_buy_price = 0
        # get dataframe
        df = OrdersBook._get_df_from_pending_orders_table()
        # get max and min only if the element in a side is greater than 0
        if df[df['side'] == 'SELL'].shape[0] > 0:
            max_sell_price = df.loc[df['side'] == 'SELL', 'price'].max()
            min_sell_price = df.loc[df['side'] == 'SELL', 'price'].min()
        if df[df['side'] == 'BUY'].shape[0] > 0:
            min_buy_price = df.loc[df['side'] == 'BUY', 'price'].min()
            max_buy_price = df.loc[df['side'] == 'BUY', 'price'].max()
        # return 0 if no orders in one side (for each side)
        return max_sell_price, min_sell_price, max_buy_price, min_buy_price

    @staticmethod
    def _get_df_from_pending_orders_table() -> pd.DataFrame:
        # get dataframe from pending orders table in the database
        cnx = DBManager.create_connection(file_name='src/database/orders.db')
        df = pd.read_sql_query(f'SELECT * FROM pending_orders', cnx)
        return df
