# pp_strategy.py

from typing import List
from binance import enums as k_binance
from src.pp_order import Order

K_MIN_CYCLES_FOR_FIRST_SPLIT = 100  # the rationale for this parameter is to give time to complete (b1, s1)
K_DISTANCE_FOR_FIRST_CHILDREN = 150  # 150
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


class Strategy:
    def __init__(self):
        pass

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
            if order.k_side == k_binance.SIDE_BUY:
                buy_count += 1
                if order.get_distance(last_cmp) > 150:
                    orders_to_balance.append(order)
            elif order.k_side == k_binance.SIDE_SELL:
                sell_count += 1
                if order.get_distance(last_cmp) > 150:
                    orders_to_balance.append(order)

        # concentration only if orders in both sides
        if buy_count == 0 and len(orders_to_balance) > 2:
            return orders_to_balance
        elif sell_count == 0 and len(orders_to_balance) > 2:
            return orders_to_balance
        return []
