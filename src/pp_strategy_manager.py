# pp_strategy_manager.py

from typing import List
import logging
from binance import enums as k_binance
from src.pp_order import Order
from src.pp_pending_orders_book import PendingOrdersBook
from src.pp_concentrator import ConcentratorManager

log = logging.getLogger('log')

K_MIN_CYCLES_FOR_FIRST_SPLIT = 100  # the rationale for this parameter is to give time to complete (b1, s1)
K_DISTANCE_FOR_FIRST_CHILDREN = 200  # 150
K_DISTANCE_FOR_SECOND_CHILDREN = 300
K_DISTANCE_INTER_FIRST_CHILDREN = 50.0  # 50
K_DISTANCE_INTER_SECOND_CHILDREN = 50.0
K_DISTANCE_FIRST_COMPENSATION = 200  # 200.0
K_DISTANCE_SECOND_COMPENSATION = 350.0
K_GAP_FIRST_COMPENSATION = 50  # 50.0
K_GAP_SECOND_COMPENSATION = 120.0

# K_SPAN_FOR_CONCENTRATION = 500
K_DISTANCE_FOR_CONCENTRATION = 350
K_GAP_CONCENTRATION = 50
K_INTERDISTANCE_AFTER_CONCENTRATION = 25.0

PT_BUY_FEE = 0.08 / 100
PT_SELL_FEE = 0.08 / 100


class StrategyManager:
    def __init__(self,
                 pob: PendingOrdersBook,
                 cm: ConcentratorManager):
        self.pob = pob
        self.cm = cm

    def assess_strategy_actions(self, cmp: float) -> int:
        # main strategy
        trades_to_new_pt_delta = 0

        # assess n-child in monitor list
        trades_to_new_pt_delta += self.check_monitor_list_for_n_child(cmp=cmp)

        # assess compensation in monitor list
        # trades_to_new_pt_delta += self.check_monitor_list_for_compensation(cmp=cmp)

        # assess extreme pairs b1-s1 to concentrate
        # TODO: implement it

        # assess isolated side orders to balance
        # TODO: implement it

        return trades_to_new_pt_delta

    def check_monitor_list_for_compensation(self, cmp: float) -> int:
        trades_to_new_pt_delta = 0
        for order in self.pob.monitor:
            # first compensation
            if order.compensation_count == 0 \
                    and order.split_count == 1 \
                    and order.get_distance(cmp=cmp) > K_DISTANCE_FIRST_COMPENSATION:  # 200
                # compensate
                if self.cm.concentrate_orders(  # return true if compensation Ok
                        orders=[order],
                        ref_mp=cmp,
                        ref_gap=K_GAP_FIRST_COMPENSATION):
                    # decrease only if compensation Ok
                    trades_to_new_pt_delta -= 1
                else:
                    log.critical(f'compensation failed!!! {order}')
        return trades_to_new_pt_delta

    def check_monitor_list_for_n_child(self, cmp: float) -> int:
        trades_to_new_pt_delta = 0
        for order in self.pob.monitor:
            # first split
            if order.cycles_count > K_MIN_CYCLES_FOR_FIRST_SPLIT \
                    and order.compensation_count == 0 \
                    and order.split_count == 0 \
                    and order.get_distance(cmp=cmp) > K_DISTANCE_FOR_FIRST_CHILDREN:  # 150
                # split into n children
                child_count = 2
                self.cm.split_n_order(
                    order=order,
                    inter_distance=K_DISTANCE_INTER_FIRST_CHILDREN,
                    child_count=child_count,
                )
                trades_to_new_pt_delta -= (child_count - 1)
        return trades_to_new_pt_delta


    def assess_concentration(self, last_cmp: float, check_orders: List[Order]) -> List[Order]:
        sell_count = 0
        buy_count = 0
        orders_to_concentrate: List[Order] = []
        # get number of orders for each side with distance > K_DISTANCE_FOR_CONCENTRATION
        for order in check_orders:
            if order.k_side == k_binance.SIDE_BUY and order.get_distance(last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
                buy_count += 1
                orders_to_concentrate.append(order)
            elif order.k_side == k_binance.SIDE_SELL and order.get_distance(last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
                sell_count += 1
                orders_to_concentrate.append(order)

        # concentration only if orders in both sides
        if buy_count > 0 and sell_count > 0:
            return orders_to_concentrate
        return []

    def assess_side_balance(self, last_cmp: float, check_orders: List[Order]) -> List[Order]:
        sell_count = 0
        buy_count = 0
        orders_to_balance: List[Order] = []
        # get number of orders for each side with distance > K_DISTANCE_FOR_CONCENTRATION
        for order in check_orders:
            if order.concentration_count == 0:
                if order.k_side == k_binance.SIDE_BUY:
                    buy_count += 1
                    if order.get_distance(last_cmp) > 1000:
                        orders_to_balance.append(order)
                elif order.k_side == k_binance.SIDE_SELL:
                    sell_count += 1
                    if order.get_distance(last_cmp) > 1000:
                        orders_to_balance.append(order)

        # concentration only if at least 3 orders in one single side with d>150
        if buy_count == 0 and len(orders_to_balance) > 2:
            return orders_to_balance
        elif sell_count == 0 and len(orders_to_balance) > 2:
            return orders_to_balance
        return []
