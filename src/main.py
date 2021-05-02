# main.py

import sys
import os
import inspect
import argparse


# Solution to include the project path to sys.path to avoid error
# when importing src.xb...
# print(sys.path)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# print(sys.path)

from src.pp_market import Market
from src.pp_session import Session


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # setup command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', type=str, required=True)
    parser.add_argument('--client_mode', type=str, required=False)
    arg = parser.parse_args()

    # TODO: setup logger
    # XBLogger()
    # logger = logging.getLogger('log')

    # TODO: check whether it is a valid conf before creating session
    # if not _get_params_from_file(configuration=arg.conf):
    #     sys.exit(f'wrong configuration passed to main: {arg.conf}')

    # check whether it is a valid client mode
    accepted_client_modes = ['binance', 'simulated']
    if arg.client_mode in accepted_client_modes:
        client_mode = arg.client_mode
    else:
        sys.exit(f'no valid client mode passed to main: {arg.client_mode}')

    # TODO: create session
    # session = Session(configuration=arg.conf, client_mode=client_mode)

    # TODO: remove when session created
    def st_callback(cmp: float):
        print(cmp)

    session = Session(client_mode=client_mode)

    print('configuration: ', arg.conf)
    print('client_mode: ', client_mode)

    # TODO: create cli_manager
    # cli_manager = XBCLIManager(session=session)
