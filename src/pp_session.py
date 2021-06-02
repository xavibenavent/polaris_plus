# pp_session.py

import logging
from datetime import datetime
from enum import Enum
import pandas as pd

from typing import Optional
from binance import enums as k_binance

from src.pp_market import Market
from src.pp_order import Order, OrderStatus
from src.pp_account_balance import AccountBalance
from src.xb_pt_calculator import get_pt_values
from src.pp_pending_orders_book import PendingOrdersBook
from src.pp_traded_orders_book import TradedOrdersBook
from src.pp_strategy_manager import StrategyManager
from src.pp_balance_manager import BalanceManager
from src.pp_concentrator import ConcentratorManager

log = logging.getLogger('log')

K_MINIMUM_DISTANCE_FOR_PLACEMENT = 35.0  # order activation distance
K_MAX_DISTANCE_FOR_REMAINING_PLACED = 100.0
K_MINIMUM_SHIFT_STEP = 15  # mp shift applied to equidistant point
K_MAX_SHIFT = 50.0
K_ORDER_PRICE_BUFFER = 5.0  # not used
K_AUGMENTED_FEE = 10 / 100

K_MIN_CYCLES_FOR_FIRST_SPLIT = 100  # the rationale for this parameter is to give time to complete (b1, s1)
K_DISTANCE_FOR_FIRST_CHILDREN = 100  # 150
K_DISTANCE_INTER_FIRST_CHILDREN = 25.0  # 50
K_DISTANCE_FIRST_COMPENSATION = 150  # 200.0
K_GAP_FIRST_COMPENSATION = 35  # 50.0

# K_SPAN_FOR_CONCENTRATION = 500
K_DISTANCE_FOR_CONCENTRATION = 150
K_GAP_CONCENTRATION = 200
K_INTERDISTANCE_AFTER_CONCENTRATION = 50.0

# one placement per cycle control flag
K_ONE_PLACE_PER_CYCLE_MODE = True

K_INITIAL_PT_TO_CREATE = 1

# pt creation
PT_CREATED_COUNT_MAX = 100  # max number of pt created per session
PT_CMP_CYCLE_COUNT = 30  # approximately secs (cmp update elapsed time)

PT_NET_AMOUNT_BALANCE = 0.00002  # 0.000020
PT_S1_AMOUNT = 0.023  # 0.022
PT_BUY_FEE = 0.08 / 100
PT_SELL_FEE = 0.08 / 100
PT_GROSS_EUR_BALANCE = 0.0

COMPENSATION_GAP = 500.0  # applied gap for compensated orders


class QuitMode(Enum):
    CANCEL_ALL_PLACED = 1
    PLACE_ALL_PENDING = 2


class Session:
    def __init__(self, client_mode: str):

        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback,
            client_mode=client_mode
        )

        # ********** managers **********
        self.bm = BalanceManager(market=self.market)
        self.pob = PendingOrdersBook(orders=[])
        self.tob = TradedOrdersBook()

        self.cm = ConcentratorManager(pob=self.pob, tob=self.tob)

        self.sm = StrategyManager(pob=self.pob, cm=self.cm)

        # *********** concentrator **********

        self.cmps = []
        self.cycles_serie = []
        self.orders_book_depth = []
        self.orders_book_span = []

        self.session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'
        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0

        # self.dashboard = None

        self.new_pt_permission_granted = True

        self.cycles_from_last_trade = 0

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol='BTCEUR')

        self.market.start_sockets()

        self.last_cmp = self.market.get_cmp('BTCEUR')

        self.ticker_count = 0

        self.partial_traded_orders_count = 0

    # ********** dashboard callback functions **********

    def get_all_orders_dataframe(self) -> pd.DataFrame:
        # get list with all orders: pending (monitor + placed) & traded (completed + pending_pt_id)
        all_orders = self.pob.get_pending_orders() + self.tob.get_all_traded_orders()
        # create dataframe
        df = pd.DataFrame([order.__dict__ for order in all_orders])
        # delete status column because it returns a tuple and raises an error in the dash callback
        df1 = df.drop(columns='status', axis=1)
        return df1

    def get_all_orders_dataframe_with_cmp(self) -> pd.DataFrame:
        df = self.get_all_orders_dataframe()
        # create cmp order-like and add to dataframe
        cmp_order = dict(pt_id='CMP', status_name='cmp', price=self.last_cmp)
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1

    # ********** Binance socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        # 0.1: create first pt
        if self.ticker_count == 0 and cmp > 20000.0:
            self.create_new_pt(cmp=cmp)

        # 0.2: update cmp count to control timely pt creation
        self.cmp_count += 1
        self.ticker_count += 1

        # these two lists will be used to plot
        self.cmps.append(cmp)
        self.cycles_serie.append(self.cmp_count)

        self.last_cmp = cmp
        self.cycles_from_last_trade += 1

        # 2. loop through placed orders and move to monitor list if isolated
        self.check_placed_list_for_move_back(cmp=cmp)

        # strategy manager
        self.partial_traded_orders_count += self.sm.assess_strategy_actions(cmp=cmp)

        # 3. check for possible compensations
        # TODO: check it
        # self.check_monitor_list_for_compensation(cmp=cmp)

        # 4. loop through monitoring orders and place to Binance when appropriate
        self.check_monitor_list_for_placing(cmp=cmp)

        # 5. check inactivity
        if self.cycles_from_last_trade > 125:  # TODO: magic number (5')
            # create new pt
            self.create_new_pt(cmp=cmp)  # direct to create_new_pt(), not to assess_new_pt()
            self.cycles_from_last_trade = 0  # equivalent to trading but without a trade

        # # 6. check span reduction (concentration)
        # orders_to_concentrate = self.sm.assess_concentration(
        #     last_cmp=cmp,
        #     check_orders=self.orders_book.monitor)
        #
        # if len(orders_to_concentrate) > 0:
        #     if self.orders_book.concentrate_list(
        #             orders=orders_to_concentrate,
        #             traded_book=self.traded_book,
        #             ref_mp=cmp,
        #             ref_gap=K_GAP_CONCENTRATION,
        #             n_for_split=2,
        #             interdistance_after_concentration=K_INTERDISTANCE_AFTER_CONCENTRATION,
        #             buy_fee=PT_BUY_FEE,
        #             sell_fee=PT_SELL_FEE):
        #         # decrease only if compensation Ok
        #         self.partial_traded_orders_count += len(orders_to_concentrate) - 2
        #         log.info('CONCENTRATION OK')
        #     else:
        #         log.critical('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        #         for order in orders_to_concentrate:
        #             log.critical(f'CONCENTRATION failed for concentration reasons!!! {order}')

        # 7. check side balance
        child_count = 0  # TODO: set to 3
        orders_to_balance = self.sm.assess_side_balance(
            last_cmp=cmp,
            check_orders=self.pob.monitor)
        if len(orders_to_balance) > 0:
            if self.cm.concentrate_orders(
                    orders=orders_to_balance,
                    ref_mp=cmp,
                    ref_gap=100,
                    ):
                # decrease only if compensation Ok
                # TODO: correct it
                self.partial_traded_orders_count += len(orders_to_balance) - 2 - child_count
                log.info('SIDE BALANCE OK')
            else:
                log.critical('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                for order in orders_to_balance:
                    log.critical(f'SIDE BALANCE failed for concentration reasons!!! {order}')

    def check_placed_list_for_move_back(self, cmp: float):
        for order in self.pob.placed:
            if order.is_isolated(cmp=cmp, max_dist=K_MAX_DISTANCE_FOR_REMAINING_PLACED):
                self.pob.place_back_order(order=order)
                # cancel order in Binance
                self.market.cancel_orders(orders=[order])

    def check_monitor_list_for_placing(self, cmp: float):
        new_placement_allowed = True
        for order in self.pob.monitor:
            order.cycles_count += 1
            if new_placement_allowed and order.is_ready_for_placement(
                    cmp=cmp,
                    min_dist=K_MINIMUM_DISTANCE_FOR_PLACEMENT):
                # check balance
                is_balance_enough, balance_needed = self.bm.is_balance_enough(order=order)
                if is_balance_enough:
                    self.pob.place_order(order=order)
                    is_order_placed, new_status = self.place_order(order=order)
                    if is_order_placed:
                        # 2. placed: (s: PLACED, t: pending_orders, l: placed)
                        order.set_status(status=OrderStatus.PLACED)
                        # to control one new placement per cycle mode
                        if K_ONE_PLACE_PER_CYCLE_MODE:
                            new_placement_allowed = False

                    else:
                        self.pob.place_back_order(order=order)
                        log.critical(f'for unknown reason the order has not been placed: {order}')
                # else:
                #     self.release_balance(balance_needed=balance_needed)
                # log.critical(f'balance is not enough for placing {order}')

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        print(f'********** ORDER TRADED:    price: {order_price} [EUR] - commission: {bnb_commission} [BNB]')
        # get the order by uid
        for order in self.pob.placed:
            if order.uid == uid:
                # set the cycle in which the order has been traded
                order.traded_cycle = self.cmp_count
                # reset counter
                self.cycles_from_last_trade = 0
                # update buy & sell count
                if order.k_side == k_binance.SIDE_BUY:
                    self.buy_count += 1
                else:
                    self.sell_count += 1
                # set commission and price
                order.set_bnb_commission(
                    commission=bnb_commission,
                    bnbbtc_rate=self.market.get_cmp(symbol='BNBBTC'))
                order.price = order_price
                # change status
                order.set_status(status=OrderStatus.TRADED)
                # remove from placed list
                self.pob.placed.remove(order)
                # add to traded list (once removed from placed list) depending on whether is pt_id completed or not
                if self.pob.has_completed_pt_id(order=order):
                    # completed
                    self.tob.add_completed(order=order)
                else:
                    self.tob.add_pending(order=order)

                # update counter for next pt
                self.partial_traded_orders_count += 1
                # check whether a new pt is allowed or not
                if self.pt_created_count < PT_CREATED_COUNT_MAX and self.partial_traded_orders_count >= 0:
                    self.create_new_pt(cmp=self.last_cmp)
                else:
                    log.info('no new pt created after the last traded order')
                # since the traded orders has been identified, do not check more orders
                break

    def account_balance_callback(self, ab: AccountBalance) -> None:
        # update of current balance from Binance
        self.bm.update_current(last_ab=ab)

    # ********** check methods **********
    def place_order(self, order) -> (bool, Optional[str]):
        order_placed = False
        status_received = None
        # place order
        d = self.market.place_order(order=order)
        if d:
            order_placed = True
            order.set_binance_id(new_id=d.get('binance_id'))
            status_received = d.get('status')
            # log.debug(f'********** ORDER PLACED **********      msg: {d}')
        else:
            log.critical(f'error placing {order}')
        return order_placed, status_received

    # ********** new perfect trade related **********
    def create_new_pt(self, cmp: float):
        # get parameters
        dp = dict(
            mp=cmp,
            nab=PT_NET_AMOUNT_BALANCE,
            s1_qty=PT_S1_AMOUNT,
            buy_fee=PT_BUY_FEE,
            sell_fee=PT_SELL_FEE,
            geb=PT_GROSS_EUR_BALANCE)

        # create new orders
        b1, s1 = self.get_b1s1(dynamic_parameters=dp)

        if b1 and s1:
            # add orders to list
            self.pob.monitor.append(b1)
            self.pob.monitor.append(s1)

            # ********** update control variables **********
            # increase created counter
            self.pt_created_count += 1
            # set pt_id based on created counter
            pt_id = f'{self.pt_created_count:03}'
            b1.pt_id = pt_id
            s1.pt_id = pt_id
            # set number of trades needed for next pt creation
            self.partial_traded_orders_count -= 2
        else:
            log.critical('the pt (b1, s1) can not be created:')
            log.critical(f'b1: {b1}')
            log.critical(f's1: {s1}')
            print('\n********** CRITICAL ERROR CREATING PT **********\n')

    def get_b1s1(self,
                 dynamic_parameters: dict,
                 ) -> (Optional[Order], Optional[Order]):
        b1 = None
        s1 = None

        order_id = 'NA'

        # get perfect trade
        b1_qty, b1_price, s1_price, g = get_pt_values(**dynamic_parameters)
        s1_qty = dynamic_parameters.get('s1_qty')

        # check filters before creating order
        if Order.is_filter_passed(filters=self.symbol_filters, qty=b1_qty, price=b1_price):
            # create orders
            b1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
                k_side=k_binance.SIDE_BUY,
                price=b1_price,
                amount=b1_qty,
                name='b1'
            )
        else:
            log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        if Order.is_filter_passed(filters=self.symbol_filters, qty=s1_qty, price=s1_price):
            s1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
                k_side=k_binance.SIDE_SELL,
                price=s1_price,
                amount=s1_qty,
                name='s1'
            )
        else:
            log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        return b1, s1

    def quit(self, quit_mode: QuitMode):
        # action depending upon quit mode
        if quit_mode == QuitMode.CANCEL_ALL_PLACED:
            print('********** CANCELLING ALL PLACED ORDERS **********')
            self.market.cancel_orders(self.pob.placed)
        elif quit_mode == QuitMode.PLACE_ALL_PENDING:
            print('********** PLACE ALL PENDING ORDERS **********')
            for order in self.pob.monitor:
                self.market.place_order(order)

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

        self.market.stop()
