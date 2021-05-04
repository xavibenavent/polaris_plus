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
            if user_input in ['1', '2', '9', 'q']:
                self.process(user_input=user_input)

    def process(self, user_input: str):
        # entry point for remote controlled actions
        if user_input == 'q':
            self.quit = True
            self.session.quit()
        elif user_input == '9':
            self.create_market_order()
        print(f'option selected: [{user_input}]')

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
                    [1] ...
                    [9] MARKET BUY 0.001 [BTC]
                    
                    [q] quit
                """
        return options_msg
