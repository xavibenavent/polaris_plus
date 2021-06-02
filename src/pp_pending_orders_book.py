# pp_pending_orders_book.py

import pandas as pd
import logging
from typing import List
from enum import Enum

from src.pp_order import Order, OrderStatus
from src.xb_pt_calculator import get_compensation
from polaris_old.pp_dbmanager import DBManager

log = logging.getLogger('log')


class PendingOrdersBook:
    def __init__(self, orders: List[Order]):

        self.monitor = []
        self.placed = []

        self.concentrated_count = 1

        # add each order to its appropriate list
        for order in orders:
            self.monitor.append(order)

    def get_monitor_df(self) -> pd.DataFrame:
        df = pd.DataFrame(data=self.monitor)
        return df

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

    def get_monitor_orders(self) -> List[Order]:
        return self.monitor

    def get_pending_orders(self) -> List[Order]:
        return self.monitor + self.placed

    def get_pending_pt_id(self) -> List[str]:
        # return the list of pt_id not completed
        pending_pt_id = []
        for order in self.get_pending_orders():
            if order.pt_id not in pending_pt_id:
                pending_pt_id.append(order.pt_id)
        return pending_pt_id

    def has_completed_pt_id(self, order: Order) -> bool:
        if order.pt_id in self.get_pending_pt_id():
            return False
        else:
            return True

    def get_order(self, uid: str) -> Order:
        # for order in self.get_all_orders():
        for order in self.monitor:
            if order.uid == uid:
                return order

    def count(self) -> int:
        return len(self.monitor)

    # ********* pandas methods **********
    def show_orders_graph(self):
        pass

    def get_pending_orders_df(self) -> pd.DataFrame:
        # create dataframe from orders list
        df_monitor = pd.DataFrame([order.__dict__ for order in self.monitor])
        df_monitor['status'] = 'monitor'
        df_placed = pd.DataFrame([order.__dict__ for order in self.placed])
        df_placed['status'] = 'placed'
        # append both dataframes
        df_pending = df_monitor.append(other=df_placed)
        return df_pending

    def get_pending_orders_kpi(self, cmp: float, buy_fee: float, sell_fee: float) -> pd.DataFrame:
        # create all pending orders list
        pending_orders = self.monitor + self.placed  # check it
        # filter orders by distance
        for order in pending_orders:
            if order.get_distance(cmp=cmp) < 250:
                pending_orders.remove(order)
        # get equivalent balance
        amount, total = PendingOrdersBook.get_balance_for_list(orders=pending_orders)

        # create empty dataframe (only column names)
        # df = pd.DataFrame(columns=['kpi', 'price', 'amount', 'side'])
        data_list = []

        # get equivalent pair for each gap
        gap_list = [100, 200, 300, 400, 500]
        for gap in gap_list:
            s1_p, b1_p, s1_qty, b1_qty = get_compensation(
                cmp=cmp,
                gap=gap,
                qty_bal=amount,
                price_bal=total,
                buy_fee=buy_fee,
                sell_fee=sell_fee
            )
            # create new data
            sell_kpi = dict(kpi=gap, price=s1_p, amount=s1_qty, side='SELL')
            buy_kpi = dict(kpi=gap, price=b1_p, amount=b1_qty, side='BUY')
            # append to list
            data_list.append(buy_kpi)
            data_list.append(sell_kpi)
        # create dataframe
        df = pd.DataFrame(data=data_list, columns=['kpi', 'price', 'amount', 'side'])
        # df1 = df.append(other=data_list, ignore_index=True)
        return df

    @staticmethod
    def get_depth() -> float:
        # difference between first sell and buy
        na, min_sell_price, max_buy_price, nb = PendingOrdersBook.get_price_limits()
        # if there are no buy sells then both buy values are 0
        # the same applies for sell side
        return abs(min_sell_price - max_buy_price)

    @staticmethod
    def get_span() -> float:
        # difference between last sell and buy
        # df = OrdersBook.get_df_from_pending_orders_table()
        max_sell_price, na, nb, min_buy_price = PendingOrdersBook.get_price_limits()
        return max_sell_price - min_buy_price

    @staticmethod
    def get_price_limits() -> (float, float, float, float):
        # default return values
        max_sell_price = 0
        min_sell_price = 0
        max_buy_price = 0
        min_buy_price = 0
        # get dataframe
        df = PendingOrdersBook._get_df_from_pending_orders_table()
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

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float):
        amount = 0.0
        total = 0.0
        for order in orders:
            amount += order.get_signed_amount()
            total += order.get_signed_total()
        return amount, total

