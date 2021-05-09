# main.py

import sys
import os
import inspect
import argparse
import logging


# Solution to include the project path to sys.path to avoid error
# when importing src.xb...
# print(sys.path)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# print(sys.path)

from src.pp_market import Market
from src.pp_session import Session
from src.xb_logger import XBLogger
from src.pp_climanager import CLIManager


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # setup command line arguments
    parser = argparse.ArgumentParser()
    # parser.add_argument('--conf', type=str, required=False)
    parser.add_argument('--client_mode', type=str, required=False, default='binance')
    parser.add_argument('--new_master_session', type=bool, required=False, default=False)
    arg = parser.parse_args()

    XBLogger()
    log = logging.getLogger('log')

    # check whether it is a valid client mode
    accepted_client_modes = ['binance', 'simulated']
    if arg.client_mode in accepted_client_modes:
        client_mode = arg.client_mode
    else:
        sys.exit(f'no valid client mode passed to main: {arg.client_mode}')

    # create session
    session = Session(client_mode=client_mode,new_master_session=arg.new_master_session)

    clim = CLIManager(session=session)
    clim.start()
