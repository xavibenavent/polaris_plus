# pp_strategy.py

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
K_DISTANCE_FOR_CONCENTRATION = 150
K_GAP_CONCENTRATION = 50
K_INTERDISTANCE_AFTER_CONCENTRATION = 25.0

PT_BUY_FEE = 0.08 / 100
PT_SELL_FEE = 0.08 / 100


class Strategy:
    def __init__(self):
        pass

    def assess_concentration(self, cmp: float):
        sell_count = 0
        buy_count = 0
        orders_to_concentrate = []
        # get number of orders for each side with distance > K_DISTANCE_FOR_CONCENTRATION
        for order in self.orders_book.monitor:
            # filter compensated orders
            # if order.compensation_count >= 0 and order.concentration_count == 0:
            # if order.concentration_count == 0:

            if order.k_side == k_binance.SIDE_BUY and order.get_distance(self.last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
                buy_count += 1
                orders_to_concentrate.append(order)
            elif order.k_side == k_binance.SIDE_SELL and order.get_distance(self.last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
                sell_count += 1
                orders_to_concentrate.append(order)

            # if order.get_distance(cmp=self.last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
            #     orders_to_concentrate.append(order)

        # concentration only if orders in both sides
        if buy_count > 0 and sell_count > 0:
            # monitor_orders.sort(key=lambda x: x.price, reverse=True)
            # concentrate & split n (n=5)
            if self.orders_book.concentrate_list(
                    orders=orders_to_concentrate,
                    ref_mp=cmp,
                    ref_gap=K_GAP_CONCENTRATION,
                    n_for_split=3,
                    interdistance_after_concentration=K_INTERDISTANCE_AFTER_CONCENTRATION,
                    buy_fee=PT_BUY_FEE,
                    sell_fee=PT_SELL_FEE):
                # decrease only if compensation Ok
                # no need for decrease because there is not an increase in orders (2 -> 2)
                self.partial_traded_orders_count += len(orders_to_concentrate) - 2
                log.info('CONCENTRATION OK')
            else:
                log.critical('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                for order in orders_to_concentrate:
                    log.critical(f'CONCENTRATION failed for compensation reasons!!! {order}')
        elif buy_count > 0:
            pass
