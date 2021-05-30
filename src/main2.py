# main.py

import sys
import os
import threading
import inspect
import argparse
import logging
import flask


# Solution to include the project path to sys.path to avoid error
# when importing src.xb...
# print(sys.path)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# print(sys.path)

from src.dashboards.indicator import Dashboard
from src.pp_market import Market
from src.pp_session import Session
from src.xb_logger import XBLogger
from src.pp_climanager import CLIManager
from src.sockets.server import Server


def start_server(clm: CLIManager):
    while True:
        server = Server(clm=clm)

def main():
    XBLogger()
    log = logging.getLogger('log')

    # TODO: remove, here the app arguments have been forced to simplify gunicorn test
    session = Session(client_mode='simulated',new_master_session=True)

    # # create dashboard
    # db = Dashboard(
    #     session=session,
    #     get_orders_callback=session.get_orders_callback,
    #     get_account_balance_callback=session.get_account_balance,
    # )
    # print(type(db.app.server))
    # app = db.app
    # server = flask.Flask(__name__)

    # TODO: uncomment when not using gunicorn
    # db.app.run_server(debug=False, dev_tools_silence_routes_logging=True)

    # clim = CLIManager(session=session)

    # # create server for remote control
    # x = threading.Thread(target=start_server, args=(clim,))
    # x.start()
    #
    # clim.start()


# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
