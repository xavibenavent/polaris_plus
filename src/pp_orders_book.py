# pp_orders_book.py

import pandas as pd
import plotly.express as px
import logging
from typing import List
from binance import enums as k_binance
from enum import Enum

from src.pp_order import Order, OrderStatus
from src.xb_pt_calculator import get_compensation
from src.pp_dbmanager import DBManager
# from src.pp_session import DATABASE_FILE, PENDING_ORDERS_TABLE

log = logging.getLogger('log')


class SplitDirection(Enum):
    TO_BUY_SIDE = 0
    TO_SELL_SIDE = 1


class OrdersBook:
    def __init__(self, orders: List[Order], dbm: DBManager, table: str):
        # e = True
        # if e:
        #     raise AssertionError
        self.monitor = []
        self.placed = []

        self.concentrated_count = 1

        self.dbm = dbm
        self.table = table

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

    def get_all_orders(self) -> List[Order]:
        return self.monitor

    def get_order(self, uid: str) -> Order:
        # for order in self.get_all_orders():
        for order in self.monitor:
            if order.uid == uid:
                return order

    def count(self) -> int:
        return len(self.monitor)

    def compensate_order(self,
                         order: Order,
                         ref_mp: float,
                         ref_gap: float,
                         buy_fee: float,
                         sell_fee: float) -> bool:

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
            log.info(f'compensation count: {order.compensation_count}')
            log.info(f'compensated b1: {b1}')
            log.info(f'compensated s1: {s1}')

            # new_orders.append(b1)
            # new_orders.append(s1)

            b1.compensation_count = order.compensation_count + 1
            b1.split_count = order.split_count
            s1.compensation_count = order.compensation_count + 1
            s1.split_count = order.split_count
            return True
        return False

    def concentrate_list(self,
                         orders: List[Order],
                         ref_mp: float,
                         ref_gap: float,
                         n_for_split: int,
                         interdistance_after_concentration: float,
                         buy_fee: float,
                         sell_fee: float) -> bool:

        # get equivalent balance
        amount, total = OrdersBook.get_balance_for_list(orders=orders)

        s1_p, b1_p, s1_qty, b1_qty = get_compensation(
            cmp=ref_mp,
            gap=ref_gap,
            qty_bal=amount,
            price_bal=total,
            buy_fee=buy_fee,
            sell_fee=sell_fee
        )

        # validate data received
        if s1_p < 0 or b1_p < 0 or s1_qty < 0 or b1_qty < 0:
            log.critical(f'!!!!!!!!!! negative value(s) after compensation: b1p: {b1_p} - b1q: {b1_qty} !!!!!!!!!!'
                         f'- s1p: {s1_p} - s1q: {s1_qty}')
        else:
            # get pt_id of all orders to concentrate
            pt_ids = []
            for order in orders:
                if order.pt_id not in pt_ids:
                    pt_ids.append(order.pt_id)
            # change orders with this pt_id to new pt_id
            new_pt_id = f'C-{self.concentrated_count:03}'
            all_orders = self.monitor
            all_orders.extend(self.placed)
            for order in all_orders:
                if order.pt_id in pt_ids:
                    order.pt_id = new_pt_id
            # change pt_id also in traded orders
            traded_orders = self.dbm.get_orders_from_table(table='traded_orders')
            for order in traded_orders:
                if order.pt_id in pt_ids:
                    log.info(f'order before updating: {order}')
                    self.dbm.update_order_pt_id(table='traded_orders', new_pt_id=new_pt_id, uid=order.uid)

            # create both orders
            b1 = Order(
                session_id=orders[0].session_id,  # session id of the first order (it might be from another session)
                order_id='CONCENTRATED',
                pt_id=new_pt_id,
                k_side=k_binance.SIDE_BUY,
                price=b1_p,
                amount=b1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name='con-b1'
            )
            s1 = Order(
                session_id=orders[0].session_id,
                order_id='CONCENTRATED',
                pt_id=new_pt_id,
                k_side=k_binance.SIDE_SELL,
                price=s1_p,
                amount=s1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name='con-s1'
            )

            # add new orders to appropriate list
            self.monitor.append(b1)
            self.monitor.append(s1)

            # add new orders to pending_orders table
            self.dbm.add_order(order=b1, table=self.table)
            self.dbm.add_order(order=s1, table=self.table)

            # delete original orders from list
            for order in orders:
                self.monitor.remove(order)
                # delete original order from pending_orders table
                self.dbm.delete_order(order=order, table=self.table)

            # log
            log.info('////////// ORDER COMPENSATED //////////')
            for order in orders:
                log.info(f'initial order:  {order}')
                log.info(f'compensation count: {order.compensation_count}')
            log.info(f'compensated b1: {b1}')
            log.info(f'compensated s1: {s1}')

            # update concentrated variables and inverse counter
            b1.concentration_count = 1
            s1.concentration_count = 1
            self.concentrated_count += 1
            # if self.concentrated_count < 100:
            #     log.critical(f'concentrated count reaching 0: {self.concentrated_count}')

            # update variables
            b1.compensation_count = orders[0].compensation_count
            b1.split_count = orders[0].split_count
            s1.compensation_count = orders[-1].compensation_count
            s1.split_count = orders[-1].split_count

            # split n
            self.split_n_order(order=b1, inter_distance=interdistance_after_concentration, child_count=n_for_split)  # n = 5
            self.split_n_order(order=s1, inter_distance=interdistance_after_concentration, child_count=n_for_split)

            return True
        return False

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
        left.compensation_count = order.compensation_count
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
        right.compensation_count = order.compensation_count
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
            center.compensation_count = order.compensation_count
            # add to monitor and pending_orders table
            self.monitor.append(center)
            self.dbm.add_order(order=center, table=self.table)
            log.info(f'center: {center}')

        # delete original order from orders book
        self.monitor.remove(order)

        # delete original order from pending orders table
        self.dbm.delete_order(order=order, table=self.table)

        return new_orders

    def split_n_order(self, order: Order, inter_distance: float, child_count: int):  # direction: SplitDirection):
        # calculate new amount
        new_amount = order.amount / child_count

        # create positions list
        positions = []
        if (child_count % 2) != 0:
            positions.append(0)  # child_count is odd
        # add positive
        positions += [x for x in range(1, 1 + int(child_count / 2))]  # if n=4: [1, 2]
        # add negative
        positions += [-x for x in range(1, 1 + int(child_count / 2))]  # if n=4: [1, 2, -1, -2]

        # loop positions
        for n in positions:
            new_price = order.price + inter_distance * n
            new_order = Order(
                session_id=order.session_id,
                order_id=f'CHILD({n:+})',
                pt_id=order.pt_id,
                k_side=order.k_side,
                price=new_price,
                amount=new_amount,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name=order.name + f'({n:+})'
            )
            new_order.split_count = order.split_count + 1
            new_order.compensation_count = order.compensation_count
            new_order.concentration_count = order.concentration_count
            # add to monitor and pending_orders table
            self.monitor.append(new_order)
            self.dbm.add_order(order=new_order, table=self.table)

        # delete original order from orders book
        self.monitor.remove(order)

        # delete original order from pending orders table
        self.dbm.delete_order(order=order, table=self.table)

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
        print(f'pending orders: {pending_orders}')
        # filter orders by distance
        for order in pending_orders:
            if order.get_distance(cmp=cmp) < 250:
                pending_orders.remove(order)
        # get equivalent balance
        amount, total = OrdersBook.get_balance_for_list(orders=pending_orders)

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

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float):
        amount = 0.0
        total = 0.0
        for order in orders:
            amount += order.get_signed_amount()
            total += order.get_signed_total()
        return amount, total

