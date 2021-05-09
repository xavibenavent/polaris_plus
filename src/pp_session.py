# pp_session.py

import logging
import sys
from icecream import ic
from datetime import datetime

from typing import List, Optional
from binance import enums as k_binance

from src.pp_market import Market
from src.pp_order import Order, OrderStatus
from src.pp_dbmanager import DBManager
from src.pp_account_balance import AccountBalance
from src.xb_pt_calculator import get_pt_values
from src.pp_orders_book import OrdersBook

log = logging.getLogger('log')

DATABASE_FILE = 'src/database/orders.db'
PENDING_ORDERS_TABLE = 'pending_orders'
TRADED_ORDERS_TABLE = 'traded_orders'

K_MINIMUM_DISTANCE_FOR_PLACEMENT = 35.0  # order activation distance
K_MAX_DISTANCE_FOR_REMAINING_PLACED = 100.0
K_MINIMUM_SHIFT_STEP = 15  # mp shift applied to equidistant point
K_MAX_SHIFT = 50.0
K_ORDER_PRICE_BUFFER = 5.0  # not used
K_AUGMENTED_FEE = 10 / 100

B_TOTAL_BUFFER = 1000.0  # remaining guaranteed EUR balance
B_AMOUNT_BUFFER = 0.02  # remaining guaranteed BTC balance

# one placement per cycle control flag
K_ONE_PLACE_PER_CYCLE_MODE = True

# pt creation
PT_CREATED_COUNT_MAX = 500  # max number of pt created per session
PT_CMP_CYCLE_COUNT = 20  # approximately secs (cmp update elapsed time)

PT_NET_AMOUNT_BALANCE = 0.000010
PT_S1_AMOUNT = 0.01
PT_BUY_FEE = 0.09 / 100
PT_SELL_FEE = 0.09 / 100
PT_GROSS_EUR_BALANCE = 0.0

COMPENSATION_GAP = 500.0  # applied gap for compensated orders


class Session:
    def __init__(self, client_mode: str, new_master_session: bool):

        # used in quit() method
        self.new_master_session = new_master_session

        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback,
            client_mode=client_mode
        )

        # set account balance variables
        self.initial_ab = self.get_account_balance(tag='initial')
        self.current_ab = self.get_account_balance(tag='current')
        self.net_ab = self.current_ab - self.initial_ab

        self.session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'
        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0

        self.new_pt_permission_granted = True
        # self.one_place_per_cycle_mode = True
        self.new_placement_allowed = True

        self.balance_total_needed = False
        self.balance_amount_needed = False

        # create the database manager and fill pending orders list
        self.dbm = self.get_dbm(new_master_session=new_master_session)

        orders_from_previous_sessions = self.dbm.get_orders_from_table(table=PENDING_ORDERS_TABLE)
        self.orders_book = OrdersBook(orders=orders_from_previous_sessions, dbm=self.dbm, table=PENDING_ORDERS_TABLE)

        # get session data from previous
        session = self.dbm.get_last_session()
        print('previous session: ', session)

        # create placed orders list (initially empty)
        # self.placed: List[Order] = []
        self.traded: List[Order] = []

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol='BTCEUR')

        # show pending orders and already placed orders for user validation
        if self.is_initial_state_validated():
            self.market.start_sockets()
        else:
            sys.exit()

    def get_account_balance(self, tag: str) -> AccountBalance:
        btc_bal = self.market.get_asset_balance(asset='BTC', tag=tag)
        eur_bal = self.market.get_asset_balance(asset='EUR', tag=tag, p=2)
        bnb_bal = self.market.get_asset_balance(asset='BNB', tag=tag)
        d = dict(s1=btc_bal, s2=eur_bal, bnb=bnb_bal)
        return AccountBalance(d)

    # ********** socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        # update cmp count to control timely pt creation
        self.cmp_count += 1

        # 1. check conditions for new pt creation
        if self.new_pt_permission_granted and self.is_new_pt_allowed():
            # 1. creation: (s: MONITOR, t: pending_orders, l: monitor)
            self.create_new_pt(cmp=cmp)

        # 2. loop through monitoring orders and place to Binance when appropriate
        self.new_placement_allowed = True
        for order in self.orders_book.monitor:
            if self.new_placement_allowed and order.is_ready_for_placement(
                    cmp=cmp,
                    min_dist=K_MINIMUM_DISTANCE_FOR_PLACEMENT):
                # check balance
                is_balance_enough, balance_needed = self.is_balance_enough(order=order)
                if is_balance_enough:
                    self.orders_book.place_order(order=order)
                    is_order_placed, new_status = self.place_order(order=order)
                    if is_order_placed:
                        # 2. placed: (s: PLACED, t: pending_orders, l: placed)
                        order.set_status(status=OrderStatus.PLACED)
                        # to control one new placement per cycle mode
                        if K_ONE_PLACE_PER_CYCLE_MODE:
                            self.new_placement_allowed = False

                    else:
                        self.orders_book.place_back_order(order=order)
                        log.critical(f'for unknown reason the order has not been placed: {order}')
                # else:
                #     self.release_balance(balance_needed=balance_needed)
                    # log.critical(f'balance is not enough for placing {order}')
        # loop through placed orders and move to monitor list if isolated
        for order in self.orders_book.placed:
            if order.is_isolated(cmp=cmp, max_dist=K_MAX_DISTANCE_FOR_REMAINING_PLACED):
                self.orders_book.place_back_order(order=order)
                # cancel order in Binance
                self.market.cancel_orders(orders=[order])

    @staticmethod
    def move_order(order: Order, from_list: List[Order], to_list: List[Order]) -> None:
        from_list.remove(order)
        to_list.append(order)

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        print(f'********** ORDER TRADED:    price: {order_price} [EUR] - commission: {bnb_commission} [BNB]')
        # get the order by uid
        for order in self.orders_book.placed:
            if order.uid == uid:
                # update buy & sell count
                if order.k_side == k_binance.SIDE_BUY:
                    self.buy_count += 1
                else:
                    self.sell_count += 1
                # set commission and price
                order.bnb_commission = bnb_commission
                order.price = order_price
                # log
                log.info(f'********** ORDER TRADED ********** {order}')
                # change status
                order.set_status(status=OrderStatus.TRADED)
                # add to traded_orders table
                self.dbm.add_order(table=TRADED_ORDERS_TABLE, order=order)
                # remove from pending_orders table
                self.dbm.delete_order(table=PENDING_ORDERS_TABLE, order=order)
                # remove from placed list
                self.orders_book.placed.remove(order)
                # add to traded list
                self.traded.append(order)

    def account_balance_callback(self, ab: AccountBalance) -> None:
        self.current_ab = ab
        self.net_ab = ab - self.initial_ab
        self.net_ab.s2.p = 2

    # ********** check methods **********

    def is_new_pt_allowed(self) -> bool:
        result = False
        if self.pt_created_count < PT_CREATED_COUNT_MAX:
            if self.cmp_count > PT_CMP_CYCLE_COUNT:
                self.cmp_count = 0
                result = True
        return result

    def is_balance_enough(self, order: Order) -> (bool, float):
        # if not enough balance, it returns False and the balance needed
        is_balance_enough = False
        balance_needed = 0.0
        # compare allowance with needed depending on the order side
        if order.k_side == k_binance.SIDE_BUY:
            balance_allowance = self.current_ab.get_free_price_s2()
            balance_needed = order.get_total()
            if (balance_allowance - balance_needed) > B_TOTAL_BUFFER:
                is_balance_enough = True
                self.balance_total_needed = False
            else:
                # force next pt to be market in sell side
                self.balance_total_needed = True
        else:
            balance_allowance = self.current_ab.get_free_amount_s1()
            balance_needed = order.amount
            if (balance_allowance - balance_needed) > B_AMOUNT_BUFFER:
                is_balance_enough = True
                self.balance_amount_needed = False
            else:
                # force next pt to be market in buy side
                self.balance_amount_needed = True

        # log.info(f'$$ BALANCE CHECK $$  allowance: {balance_allowance} - needed: {balance_needed} - enough: {is_balance_enough}')

        return is_balance_enough, balance_needed  # in fact the balance needed will be less

    def place_order(self, order) -> (bool, Optional[str]):
        order_placed = False
        status_received = None
        # place order
        d = self.market.place_order(order=order)
        if d:
            order_placed = True
            order.set_binance_id(new_id=d.get('binance_id'))
            status_received = d.get('status')
            log.debug(f'********** ORDER PLACED **********      msg: {d}')
        else:
            log.critical(f'error placing {order}')
        return order_placed, status_received

    # ********** new perfect trade related **********

    def release_balance(self, balance_needed: float):
        # TODO: implement it
        # assess the following:
        #  1. cancel placed orders
        #  2. force adequate placement/trading by:
        #       a) creating new pt
        #       b) compensating (1->2) existing monitoring orders
        pass

    def get_dynamic_parameters(self, cmp: float) -> (dict, bool):
        #   1. proportion of sells vs buys
        mp_shift = 0.0
        buy_fee = PT_BUY_FEE
        sell_fee = PT_SELL_FEE
        if not self.balance_amount_needed and not self.balance_total_needed:
            mp_shift = (self.sell_count - self.buy_count) * K_MINIMUM_SHIFT_STEP
            if abs(mp_shift) > K_MAX_SHIFT:
                mp_shift = K_MAX_SHIFT
            log.info(f'++++++++++ SHIFT SETTING: mp_shift: {mp_shift} - buy_count: {self.buy_count} '
                     f'- sell_count: {self.sell_count} ++++++++++')
        elif self.balance_total_needed:
            # force sell side => shift to the left (down)
            mp_shift = -100.0
            buy_fee = PT_BUY_FEE * (1 + K_AUGMENTED_FEE)
            sell_fee = PT_SELL_FEE * (1 + K_AUGMENTED_FEE)
            log.info(f'++++++++++ FORCED SELL SIDE: mp_shift: {mp_shift} - buy_count: {self.buy_count} '
                     f'- sell_count: {self.sell_count} ++++++++++')
        elif self.balance_amount_needed:
            # force buy side => balance to the right (up)
            mp_shift = 100.0
            buy_fee = PT_BUY_FEE * (1 + K_AUGMENTED_FEE)
            sell_fee = PT_SELL_FEE * (1 + K_AUGMENTED_FEE)
            log.info(f'++++++++++ FORCED BUY SIDE: mp_shift: {mp_shift} - buy_count: {self.buy_count} '
                     f'- sell_count: {self.sell_count} ++++++++++')

        mp = cmp + mp_shift
        d = dict(
            mp=mp,
            nab=PT_NET_AMOUNT_BALANCE,
            s1_qty=PT_S1_AMOUNT,
            buy_fee=buy_fee,
            sell_fee=sell_fee,
            geb=PT_GROSS_EUR_BALANCE
        )
        return d, mp_shift == 0  # return True if no shift

    def create_new_pt(self, cmp: float):
        # get parameters
        dp, is_default = self.get_dynamic_parameters(cmp=cmp)
        # create new orders
        b1, s1 = self.get_new_pt(dynamic_parameters=dp, is_default=is_default)

        if b1 and s1:
            # add orders to database
            self.dbm.add_order(table=PENDING_ORDERS_TABLE, order=b1)
            self.dbm.add_order(table=PENDING_ORDERS_TABLE, order=s1)
            # add orders to list
            self.orders_book.monitor.append(b1)
            self.orders_book.monitor.append(s1)
        else:
            log.critical('the pt (b1, s1) can not be created:')
            log.critical(f'b1: {b1}')
            log.critical(f's1: {s1}')
            print('\n********** CRITICAL ERROR CREATING PT **********\n')

    def get_new_pt(self,
                   dynamic_parameters: dict,
                   is_default: bool) -> (Optional[Order], Optional[Order]):
        b1 = None
        s1 = None

        if is_default:
            order_id = 'DEFAULT'
        else:
            order_id = 'SHIFTED'

        self.pt_created_count += 1
        pt_id = f'PT_{self.pt_created_count:06}'

        # get perfect trade
        b1_qty, b1_price, s1_price, g = get_pt_values(**dynamic_parameters)
        s1_qty = dynamic_parameters.get('s1_qty')

        # check filters before creating order
        if Order.is_filter_passed(filters=self.symbol_filters, qty=b1_qty, price=b1_price):
            # create orders
            b1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id=pt_id,
                k_side=k_binance.SIDE_BUY,
                price=b1_price,
                amount=b1_qty
            )
        if Order.is_filter_passed(filters=self.symbol_filters, qty=s1_qty, price=s1_price):

            s1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id=pt_id,
                k_side=k_binance.SIDE_SELL,
                price=s1_price,
                amount=s1_qty
            )
        return b1, s1

    def quit(self):
        print('********** CANCELLING ALL PLACED ORDERS **********')
        self.market.cancel_orders(self.orders_book.placed)

        # check for correct cancellation of all orders
        btc_bal = self.market.get_asset_balance(asset='BTC',
                                                tag='check for zero locked')
        eur_bal = self.market.get_asset_balance(asset='EUR',
                                                tag='check for zero locked')
        if btc_bal.locked != 0 or eur_bal.locked != 0:
            log.critical('after cancellation of all orders, locked balance should be 0')
            log.critical(btc_bal)
            log.critical(eur_bal)
        else:
            log.info(f'LOCKED BALANCE CHECK CORRECT: btc_balance: {btc_bal} - eur_balance: {eur_bal}')

        if self.new_master_session:
            # save session data
            session = {
                'session_id': self.session_id,
                'btc': self.current_ab.s1.get_total(),
                'eur': self.current_ab.s2.get_total(),
                'bnb': self.current_ab.bnb.get_total(),
                'btc_equivalent': self.current_ab.get_btc_equivalent()
            }
            print('session: ', session)
            self.dbm.add_session(session=session)

        self.market.stop()

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float, float):
        balance_amount = 0.0
        balance_total = 0.0
        balance_commission = 0.0
        for order in orders:
            balance_amount += order.get_signed_amount()
            balance_total += order.get_signed_total()
            balance_commission += order.bnb_commission
        return balance_amount, balance_total, balance_commission

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
    def get_dbm(new_master_session: bool) -> DBManager:
        try:
            return DBManager(db_name=DATABASE_FILE,
                             order_tables=[PENDING_ORDERS_TABLE,
                                           TRADED_ORDERS_TABLE],
                             new_master_session=new_master_session)
        except AttributeError as e:
            log.critical(e)
            sys.exit()

    def is_initial_state_validated(self) -> bool:
        allowed = False

        print('\n********** INITIAL SANITY X-CHECK (ISOLATED ORDERS) **********')

        print('\n********** (monitor) pending orders LIST: (order status: MONITOR) **********')
        for order in self.orders_book.monitor:
            print(order)

        print('\n********** pending orders TABLE: **********')
        pending_orders_table = self.dbm.get_orders_from_table(table=PENDING_ORDERS_TABLE)
        for order in pending_orders_table:
            print(order)

        print('\n********** active orders LIST: (order status: PLACED) **********')
        for order in self.orders_book.placed:
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
