# pp_climanager.py

from src.pp_session import Session


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
            d = dict(monitor=self.session.monitor, placed=self.session.placed)
            self.show_lists(d=d)
        elif user_input == '2':
            self.show_balance()
        elif user_input == 'q':
            self.quit = True
            self.session.quit()
        elif user_input == '9':
            self.create_market_order()
        print(f'option selected: [{user_input}]')

    @staticmethod
    def show_lists(d: dict):
        for k in d.keys():
            print(f'********** {k} **********')
            for order in d.get(k):
                print(order)

    def show_balance(self):
        # d = self.session.market.client.get_account()
        # for balance in d['balances']:
        #     if balance.get('asset') in ['BTC', 'BNB', 'EUR']:
        #         pprint(balance)
        self.session.initial_ab.log_print()
        self.session.current_ab.log_print()
        if self.session.net_ab:
            self.session.net_ab.log_print()

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
                    [1] print monitor and placed lists
                    [2] show balance
                    [9] place MARKET BUY 0.001 [BTC]
                    
                    [q] quit
                """
        return options_msg
