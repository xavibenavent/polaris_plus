# pp_session.py

from src.pp_market import Market
from src.pp_account_balance import AccountBalance


class Session:
    def __init__(self, client_mode: str):
        # TODO: remove
        self.status = 0

        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback,
            client_mode=client_mode
        )

    # ********** socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        print(cmp)

    def order_traded_callback(self, order_id: str, order_price: float, bnb_commission: float) -> None:
        pass

    def account_balance_callback(self, ab: AccountBalance) -> None:
        pass
