# pp_traded_book.py

from typing import List

from src.pp_order import Order


class TradedBook:
    def __init__(self):
        self.completed: List[Order] = []
        self.pending: List[Order] = []
        self.completed_pt_id: List[str] = []

    def add_pending(self, order: Order):
        self.pending.append(order)

    def add_completed(self, order: Order):
        self.completed.append(order)
        self.completed_pt_id.append(order.pt_id)

    def get_all_traded_orders(self) -> List[Order]:
        return self.completed + self.pending

    def set_new_pt_id(self, new_pt_id: str, pt_id_list: List[str]) -> None:
        # change pt_id of orders with pt_id in the passed list
        for order in self.pending:
            if order.pt_id in pt_id_list:
                order.pt_id = new_pt_id



