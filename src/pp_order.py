# pp_order.py

import logging
import secrets
from datetime import datetime
from enum import Enum
from binance import enums as k_binance

log = logging.getLogger('log')

K_ACTIVATION_DISTANCE = 25.0


class OrderStatus(Enum):
    MONITOR = 1
    PLACED = 2
    TRADED = 3
    CANCELED = 4
    ISOLATED = 5


class Order:
    def __init__(self,
                 session_id: str,  # S_2021_05_01_20_08
                 order_id: str,  # not actually used
                 pt_id: str,  # PT_000001
                 k_side: k_binance,
                 price: float,
                 amount: float,
                 status: OrderStatus = OrderStatus.MONITOR,
                 uid: str = '',
                 bnb_commission=0.0,
                 binance_id=0  # int
                 ):
        self.session_id = session_id
        self.order_id = order_id
        self.pt_id = pt_id
        self.k_side = k_side
        self.price = price
        self.amount = amount
        self.status = status
        self.bnb_commission = bnb_commission
        self.binance_id = binance_id

        # session parameters
        self.activation_distance = K_ACTIVATION_DISTANCE

        self.creation = datetime.today()

        # set uid depending whether it is first creation or not
        if uid == '':
            self.uid = secrets.token_hex(8)
        else:
            self.uid = uid

        print(self)
        log.info(self)

    def __del__(self):
        log.info(f'{self} OBJECT DESTROYED')

    def is_ready_for_placement(self, cmp: float, min_dist: float) -> bool:
        return self.get_distance(cmp=cmp) < min_dist

    def get_distance(self, cmp: float) -> float:
        # return abs(cmp - self._price)
        if self.k_side == k_binance.SIDE_BUY:
            return cmp - self.price
        else:
            return self.price - cmp

    def get_price_str(self, precision: int = 2) -> str:
        price = '{:0.0{}f}'.format(self.price, precision)  # 2 for EUR
        return f'{self.price:0.0{precision}f}'
        # return price

    def get_amount(self, precision: int = 6) -> float:
        return round(self.amount, precision)  # 6 for BTC

    def get_total(self, precision: int = 2) -> float:
        return round(self.price * self.amount, precision)

    def set_bnb_commission(self, commission: float) -> None:
        self.bnb_commission = commission

    def set_status(self, status: OrderStatus):
        self.status = status
        log.info(self)
        print(self)

    def set_binance_id(self, new_id: int):
        self.binance_id = new_id

    def __repr__(self):
        return (f'{self.k_side:4} - {self.session_id} - {self.pt_id:9} - {self.order_id:9} - {self.price:10,.2f} '
                f'- {self.amount:12,.6f} - {self.bnb_commission:12,.6f} - {self.status.name:10}'
                f'- {self.binance_id} - {self.uid} - {self.creation}')

    def filters_check_passed(self, filters: dict) -> bool:
        return True





