# main_dash.py

import sys
import logging
import os
import inspect

from flask import request  # to stop the server
import pandas as pd

import dash
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

# *********** to run from terminal project folder ***********
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ***********************************************************

from src.dashboards import dashboard_aux as daux
from src.pp_session import Session, QuitMode
from src.xb_logger import XBLogger
import src.dashboards.layout as main_layout

# dashboard refresh/update rate
K_INTERVAL = 1.0

# K_BACKGROUND_COLOR = '#272b30'

XBLogger()
log = logging.getLogger('log')

# TODO: remove, here the app arguments have been forced to simplify gunicorn test
session = Session(client_mode='simulated')  # , new_master_session=True)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# app layout
app.layout = main_layout.get_layout(interval=K_INTERVAL)


# ********** app callbacks **********
@app.callback(
    Output(component_id='example-output', component_property='children'),
    [Input(component_id='new-pt-button', component_property='n_clicks')])
def on_button_click(n):
    if n is None:
        return 'not clicked yet!'
    else:
        shutdown_flask_server()
        session.quit(quit_mode=QuitMode.CANCEL_ALL_PLACED)
        return 'app stopped'


@app.callback(
    Output('completed-pt-balance-chart', 'figure'), Input('update', 'n_intervals'))
def update_chart(timer):
    df = session.get_orders_callback()
    # get dataframe with orders from completed pt
    completed_pt_df = daux.get_completed_pt_df(df=df)
    fig = daux.get_completed_pt_chart(df=completed_pt_df)
    return fig


@app.callback(
    Output('kpi-bar-chart', 'figure'), Input('update', 'n_intervals'))
def update_chart(timer):
    df = session.pob.get_pending_orders_kpi(cmp=session.last_cmp, buy_fee=0.0008, sell_fee=0.0008)
    fig = px.bar(
        data_frame=df,
        x='price',
        y='amount',
        # text='amount',
        color='side',
        range_y=[0, 1],
    )
    return fig


@app.callback(
    Output("pt-group-chart", "figure"), [Input('update', 'n_intervals')])
def update_bar_chart(timer):
    # df = session.get_orders_callback()
    df = session.get_all_orders_dataframe()
    return daux.get_bar_chart(df=df)


@app.callback(
    Output('trades-to-new-pt', 'value'),
    Output('traded-balance', 'value'),
    Output('traded-price-balance', 'value'),
    Output('cycle-count-from-last', 'value'),
    Input('update', 'n_intervals')
)
def update_led(timer):
    df = session.get_orders_callback()
    # get balance from orders from completed pt
    btc_balance_completed_pt, eur_balance_completed_pt = daux.get_completed_pt_balance(df=df)
    # balance = self.session.get_traded_balance_callback()
    satoshi_balance = btc_balance_completed_pt * 100_000_000
    trades_to_new_pt = session.partial_traded_orders_count
    # return f'{trades_to_new_pt:02.0f}', f'{satoshi_balance:.0f}'
    cycles_from_last = session.cycles_from_last_trade
    return f'{trades_to_new_pt:06.0f}', f'{satoshi_balance:.0f}', \
           f'{eur_balance_completed_pt:,.2f}', f'{cycles_from_last:06.0f}'


@app.callback(
    Output('daq-tank-btc', 'value'),
    Output('daq-tank-eur', 'value'),
    Output('daq-tank-bnb', 'value'),
    Input('update', 'n_intervals')
)
def update_tank_btc(timer):
    account_balance = session.bm.get_account_balance()
    return account_balance.s1.free, account_balance.s2.free, account_balance.bnb.free


@app.callback(
    Output('table', 'data'), Output('table-traded', 'data'),
    Input('update', 'n_intervals')
)
def update_table(timer):
    df = session.get_all_orders_dataframe_with_cmp()
    # sort by price
    df1 = df.sort_values(by=['price'], ascending=False)
    # filter by status for each table (monitor-placed & traded)
    df_pending = df1[df1.status_name.isin(['monitor', 'placed', 'cmp'])]
    df_traded = df1[df1.status_name.eq('traded')]
    return df_pending.to_dict('records'), df_traded.to_dict('records')


@app.callback(
    Output('indicator-graph', 'figure'), Input('update', 'n_intervals')
)
def update_cmp_indicator(timer):
    # get all session cmp
    cmps = session.cmps
    fig = daux.get_cmp_indicator(cmps=cmps)
    return fig


@app.callback(
    Output('daily-line', 'figure'), Input('update', 'n_intervals')
)
def update_cmp_line_chart(timer):
    # get session cmps
    cmps = session.cmps
    # create dataframe from cmps list
    df = pd.DataFrame(data=cmps, columns=['cmp'])
    df['rate'] = df.index
    # create line chart
    fig = daux.get_cmp_line_chart(df=df, cmps=cmps)
    return fig


def shutdown_flask_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


if __name__ == '__main__':  # change path in line 31 when using this
    app.run_server(debug=True)
