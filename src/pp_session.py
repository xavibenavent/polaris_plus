# pp_session.py
import logging
import pprint
import sys

from typing import List, Optional
from binance import enums as k_binance

from src.pp_market import Market
from src.pp_account_balance import AccountBalance
from src.pp_order import Order, OrderStatus
from src.pp_dbmanager import DBManager

log = logging.getLogger('log')

DATABASE_FILE = 'src/database/orders.db'
PENDING_ORDERS_TABLE = 'pending_orders'
TRADED_ORDERS_TABLE = 'traded_orders'

K_MINIMUM_DISTANCE_FOR_PLACEMENT = 30.0


class Session:
    def __init__(self, client_mode: str):

        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback,
            client_mode=client_mode
        )

        # create the database manager and fill pending orders list
        self.dbm = self.get_dbm()
        self.monitor: List[Order] \
            = self.dbm.get_orders_from_table(table=PENDING_ORDERS_TABLE)

        # create placed orders list (initially empty)
        self.placed: List[Order] = []

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol='BTCEUR')

        # show pending orders and already placed orders for user validation
        if self.is_initial_state_validated():
            self.market.start_sockets()
        else:
            sys.exit()

    # ********** socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        # 1. check conditions for new pt creation
        if self.is_new_pt_allowed():
            # 1. creation: (s: MONITOR, t: pending_orders, l: monitor)
            # self.create_new_pt()
            pass

        # 2. loop through monitoring orders and place to Binance when appropriate
        for order in self.monitor:
            if order.is_ready_for_placement(
                    cmp=cmp,
                    min_dist=K_MINIMUM_DISTANCE_FOR_PLACEMENT):
                # check balance
                is_balance_enough, balance_needed = self.is_balance_enough(order=order)
                if is_balance_enough:
                    # check filters
                    if order.filters_check_passed(filters=self.symbol_filters):
                        is_order_placed, new_status = self.place_order(order=order)
                        if is_order_placed:
                            if new_status == 'NEW':
                                # 2. placed: (s: PLACED, t: pending_orders, l: placed)
                                order.set_status(status=OrderStatus.PLACED)
                    else:
                        log.critical(f'error checking filters for {order}')
                else:
                    self.release_balance(balance_needed=balance_needed)
                    log.critical(f'balance is not enough for placing {order}')

        # print(cmp)

    def order_traded_callback(self, order_id: str, order_price: float, bnb_commission: float) -> None:
        print(f'price: {order_price}  commission: {bnb_commission} [BNB]')

    def account_balance_callback(self, ab: AccountBalance) -> None:
        pass

    def place_order(self, order) -> (bool,Optional[str]):
        order_placed = False
        status_received = None
        # place order
        d = self.market.place_order(order=order)
        if d:
            order_placed = True
            order.set_binance_id(new_id=d.get('binance_id'))
            status_received = d.get('status')
            log.debug(d)
        else:
            log.critical(f'error placing {order}')
        return order_placed, status_received

    def is_new_pt_allowed(self) -> bool:
        # TODO: implement it
        # conditions to check:
        #   1. elapsed time since last creation
        #   2. cmp vs last created mp
        #   3. balance
        return True

    def create_new_pt(self):
        # get parameters
        dp = self.get_dynamic_parameters()
        # create new orders
        b1, s1 = self.get_new_pt(dynamic_parameters=dp)
        # add orders to database
        self.dbm.add_order(table=PENDING_ORDERS_TABLE, order=b1)
        self.dbm.add_order(table=PENDING_ORDERS_TABLE, order=s1)
        # add orders to list
        self.monitor.append(b1)
        self.monitor.append(s1)

    def is_balance_enough(self, order: Order) -> (bool, Optional[float]):
        # if not enough balance, it returns the value of the balance needed
        is_balance_enough = False
        balance_needed = None
        # TODO: implement it
        # TODO: remove it
        is_balance_enough = True
        return is_balance_enough

    def release_balance(self, balance_needed: float):
        # TODO: implement it
        # assess the following:
        #  1. cancel placed orders
        #  2. force adequate placement/trading by:
        #       a) creating new pt
        #       b) compensating (1->2) existing monitoring orders
        pass

    def get_dynamic_parameters(self) -> dict:
        # TODO: implement it
        # check:
        #   1. proportion of sells vs buys
        #   2. balance needs
        d = {}
        return d

    def get_new_pt(self, dynamic_parameters: dict) -> (Order, Order):
        # TODO: implement it
        # legacy orders terminology
        b1: Order
        s1: Order
        return b1, s1

    def quit(self):
        # TODO: other actions (log them)
        self.market.stop()

    @staticmethod
    def get_test_order() -> Order:
        order = Order(
            session_id='S_20210502_2200',
            order_id='XAVI BENAVENT',
            pt_id='PT_000008',
            k_side=k_binance.SIDE_SELL,
            price=48_150.0,
            amount=0.001,
        )
        return order

    @staticmethod
    def get_dbm() -> DBManager:
        try:
            return DBManager(db_name=DATABASE_FILE,
                             order_tables=[PENDING_ORDERS_TABLE,
                                           TRADED_ORDERS_TABLE])
        except AttributeError as e:
            log.critical(e)
            sys.exit()

    def is_initial_state_validated(self) -> bool:
        allowed = False

        print('\n********** INITIAL SANITY X-CHECK (ISOLATED ORDERS) **********')

        print('\n********** pending orders LIST: (order status: MONITOR) **********')
        for order in self.monitor:
            print(order)

        print('\n********** pending orders TABLE: **********')
        for order in self.dbm.get_orders_from_table(table=PENDING_ORDERS_TABLE):
            print(order)

        print('\n********** active orders LIST: (order status: PLACED) **********')
        for order in self.placed:
            print(order)
        print('          (it should be empty)')

        print('\n********** traded orders TABLE: (order status: TRADED) **********')
        for order in self.dbm.get_orders_from_table(table=TRADED_ORDERS_TABLE):
            print(order)
        print('          (it should be empty)')

        user_input = input(f'\nvalidation needed before session start. is it ok? (y/n) ')
        if user_input == 'y':
            allowed = True

        return allowed
