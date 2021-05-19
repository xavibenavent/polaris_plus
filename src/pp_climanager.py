# pp_climanager.py

from src.pp_session import Session, QuitMode
from src.pp_account_balance import AccountBalance


class CLIManager:
    def __init__(self, session: Session):
        self.session = session
        self.quit = False

    def start(self):
        while not self.quit:
            print(CLIManager.get_options_msg())
            user_input = input('\nenter option: ')
            self.process(user_input=user_input)

    def process(self, user_input: str):
        # entry point for remote controlled actions
        if user_input == '1':
            d = dict(monitor=self.session.orders_book.monitor, placed=self.session.orders_book.placed, traded=self.session.traded)
            self.show_lists(d=d)
        elif user_input == '2':
            self.show_balance()
        elif user_input == '3':
            self.session.new_pt_permission_granted = not self.session.new_pt_permission_granted
            print(f'pt permission granted: {self.session.new_pt_permission_granted}')
        elif user_input == '4-t':
            self.show_partial_balance(self.session.traded)
        elif user_input == '4-p':
            pending_orders = self.session.orders_book.monitor + self.session.orders_book.placed
            self.show_partial_balance(pending_orders)
        elif user_input == 'q':
            self.quit = True
            self.session.quit(quit_mode=QuitMode.PLACE_ALL_PENDING)
        elif user_input == 'q-ncm':
            self.quit = True
            self.session.market.stop()
        elif user_input == '8':
            self.session.orders_book.show_orders_graph()
            # self.session.dashboard.
        elif user_input == '9':
            self.create_market_order()
        elif user_input == '+':
            self.session.market.client.update_cmp(step=20.0)
        elif user_input == '-':
            self.session.market.client.update_cmp(step=-20.0)
        print(f'\noption selected: [{user_input}]')

    @staticmethod
    def show_lists(d: dict):
        for k in d.keys():
            print(f'\n********** {k} **********')
            # get list
            orders_list = d.get(k)
            # sort by price
            orders_list.sort(
                key=lambda item: item.price,
                reverse=True
            )
            # show
            for order in orders_list:
                print(order)

    def show_partial_balance(self, orders):
        ba, bt, bc = self.session.get_balance_for_list(orders)
        print('********** PARTIAL BALANCE **********')
        print(f'amount: {ba} [BTC] - total: {bt} [EUR] - commission: {bc} [BNB]')
        btceur = self.session.market.get_cmp(symbol='BTCEUR')
        bnbbtc = self.session.market.get_cmp(symbol='BNBBTC')
        bnbeur = self.session.market.get_cmp(symbol='BNBEUR')
        a_eur = round(ba * btceur, 2)
        t_eur = round(bt,2)
        c_eur = round(bc * bnbeur, 2)
        balance_eur = a_eur + t_eur - c_eur
        print(f'amount: {a_eur} [EUR] - total: {t_eur} [EUR] - commission: {c_eur} [EUR] - balance: {balance_eur} [EUR]')
        a_btc = round(ba, 8)
        t_btc = round(bt / btceur, 8)
        c_btc = round(bc * bnbbtc, 8)
        balance_btc = a_btc + t_btc - c_btc
        print(f'amount: {a_btc} [BTC] - total: {t_btc} [BTC] - commission: {c_btc} [BTC] - balance: {balance_btc} [BTC]')

    def show_balance(self):
        # d = self.session.market.client.get_account()
        # for balance in d['balances']:
        #     if balance.get('asset') in ['BTC', 'BNB', 'EUR']:
        #         pprint(balance)
        print('********** INITIAL BALANCE **********')
        self.session.initial_ab.log_print()
        print('********** CURRENT BALANCE **********')
        self.session.current_ab.log_print()
        if self.session.net_ab:
            print('**********   NET BALANCE   **********')
            self.session.net_ab.log_print()
        print('********** BTC EQUIVALENT AMOUNT **********')
        # get euro converted to btc
        # in order to compare appropriately a fixed rate is used
        eur_per_btc = 50000.0  # self.session.market.get_cmp(symbol='BTCEUR')
        btc_per_bnb = 0.02  # self.session.market.get_cmp(symbol='BNBBTC')

        initial = self.session.initial_ab.get_btc_equivalent()
        current = self.session.current_ab.get_btc_equivalent()
        diff = current - initial

        print(f'btc equivalent amount:     initial: {initial:12,.8f} '
              f'- current: {current:12,.8f} - net balance: {diff:12,.8f} [BTC]')

    def create_market_order(self) -> None:
        order = self.session.market.client.order_market_buy(
            symbol='BTCEUR',
            quantity=0.001
        )
        print(order)

    @staticmethod
    def get_options_msg() -> str:
        options_msg = \
                """
                Options:
                    [1] show orders lists
                    [2] show account balance
                    [3] toggle (on/off) new pt permission
                    [4-t] show partial traded balance
                    [4-p] show partial pending balance
                    [8] show orders graph
                    [9] place MARKET BUY 0.001 [BTC]
                    
                    [q] quit
                    [q-ncm] quit (non-cancel mode)
                    [+][-] cmp control
                """
        return options_msg
