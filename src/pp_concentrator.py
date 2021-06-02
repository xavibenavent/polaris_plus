# pp_concentrator.py

from typing import List
import logging
from binance import enums as k_binance

from src.pp_order import Order, OrderStatus
from src.pp_balance_manager import BalanceManager
from src.xb_pt_calculator import get_compensation
from src.pp_pending_orders_book import PendingOrdersBook
from src.pp_traded_orders_book import TradedOrdersBook

log = logging.getLogger('log')


class ConcentratorManager:
    def __init__(self,
                 pob: PendingOrdersBook,
                 tob: TradedOrdersBook,
                 buy_fee=0.0008,
                 sell_fee=0.0008
                 ):
        self.pob = pob
        self.tob = tob
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.concentrator_count = 0
        self.concentrated_pt_id = []  # each element a tuple (count, pt_id list)

    def concentrate_orders(self, orders: List[Order], ref_mp: float, ref_gap: float) -> bool:
        """concentration does not include n-split
        :param orders: list of orders to concentrate
        :param ref_mp: market price to concentrate to
        :param ref_gap: concentration gap
        :return: True if concentration is successful
        """
        # check orders list is not empty
        if len(orders) < 1:
            return False

        # get equivalent amount and total
        amount, total, _, _ = BalanceManager.get_balance_for_list(orders)

        # get equivalent pair b1-s1
        s1_p, b1_p, s1_qty, b1_qty = get_compensation(
            cmp=ref_mp,
            gap=ref_gap,
            qty_bal=amount,
            price_bal=total,
            buy_fee=self.buy_fee,
            sell_fee=self.sell_fee
        )

        # validate values received for b1 and s1
        if s1_p < 0 or b1_p < 0 or s1_qty < 0 or b1_qty < 0:
            log.critical(f'!!!!!!!!!! negative value(s) after compensation: b1p: {b1_p} - b1q: {b1_qty} !!!!!!!!!!'
                         f'- s1p: {s1_p} - s1q: {s1_qty}')
            return False
        else:
            # get pt_id of all orders to concentrate
            pt_ids = []
            for order in orders:
                if order.pt_id not in pt_ids:
                    pt_ids.append(order.pt_id)

            # increment counter and save mapping between count and pt_ids
            # at this point the concentration is sure and will return True
            self.concentrator_count += 1
            self.concentrated_pt_id.append((self.concentrator_count, pt_ids))
            print(self.concentrated_pt_id)

            # change pending orders with this pt_id to new pt_id
            new_pt_id = f'C-{self.concentrator_count:04}'
            for order in self.pob.get_pending_orders():
                if order.pt_id in pt_ids:
                    order.pt_id = new_pt_id
            # change pt_id also in traded orders
            self.tob.set_new_pt_id(new_pt_id=new_pt_id, pt_id_list=pt_ids)

            # create both orders
            session_id = orders[0].session_id  # same session_id
            b1 = Order(
                session_id=session_id,
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
                session_id=session_id,
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
            self.pob.monitor.append(b1)
            self.pob.monitor.append(s1)

            # delete original orders from list
            for order in orders:
                self.pob.monitor.remove(order)

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

            # update variables
            b1.compensation_count = 0
            b1.split_count = 0
            s1.compensation_count = 0
            s1.split_count = 0

            # split n
            # self.split_n_order(order=b1, inter_distance=interdistance_after_concentration, child_count=n_for_split)
            # self.split_n_order(order=s1, inter_distance=interdistance_after_concentration, child_count=n_for_split)

            return True

    def split_n_order(self, order: Order, inter_distance: float, child_count: int):
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
            self.pob.monitor.append(new_order)

        # delete original order from orders book
        self.pob.monitor.remove(order)
