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
    Output(component_id='btc-balance-chart', component_property='figure'),
    Output(component_id='eur-balance-chart', component_property='figure'),
    Output(component_id='bnb-balance-chart', component_property='figure'),
    Input(component_id='update', component_property='n_intervals')
)
def update_figure(timer):
    ab = session.bm.get_account_balance()
    btc_free = ab.s1.free
    btc_locked = ab.s1.locked
    eur_free = ab.s2.free
    eur_locked = ab.s2.locked
    bnb_free = ab.bnb.free
    bnb_locked = ab.bnb.locked

    df_btc = pd.DataFrame([
        dict(asset='btc', amount=btc_free, type='free'),
        dict(asset='btc', amount=btc_locked, type='locked'),
    ])
    df_eur = pd.DataFrame([
        dict(asset='eur', amount=eur_free, type='free'),
        dict(asset='eur', amount=eur_locked, type='locked'),
    ])
    df_bnb = pd.DataFrame([
        dict(asset='bnb', amount=bnb_free, type='free'),
        dict(asset='bnb', amount=bnb_locked, type='locked'),
    ])

    fig_btc = daux.get_balance_bar_chart(df=df_btc, asset='btc', y_max=0.2)
    fig_eur = daux.get_balance_bar_chart(df=df_eur, asset='eur', y_max=10000)
    fig_bnb = daux.get_balance_bar_chart(df=df_bnb, asset='bnb', y_max=55)
    return fig_btc, fig_eur, fig_bnb


@app.callback(
    Output(component_id='example-output', component_property='children'),
    [Input(component_id='new-pt-button', component_property='n_clicks')])
def on_button_click(n):
    if n is None:
        return ''
    else:
        shutdown_flask_server()
        session.quit(quit_mode=QuitMode.CANCEL_ALL_PLACED)
        return 'app stopped'


# @app.callback(
#     Output('completed-pt-balance-chart', 'figure'), Input('update', 'n_intervals'))
# def update_chart(timer):
#     df = session.get_all_orders_dataframe()
#     # get dataframe with orders from completed pt
#     completed_pt_df = daux.get_completed_pt_df(df=df)
#     fig = daux.get_completed_pt_chart(df=completed_pt_df)
#     return fig


@app.callback(
    Output('kpi-bar-chart', 'figure'), Input('update', 'n_intervals'))
def update_chart(timer):
    df = session.pob.get_pending_orders_kpi(cmp=session.last_cmp, buy_fee=0.0008, sell_fee=0.0008)
    fig = px.bar(
        data_frame=df,
        x='price',
        y='amount',
        text='amount',
        color='side',
        range_y=[0, 0.5],
        height=350,
        color_discrete_map={'BUY': 'LightSeaGreen', 'SELL': 'LightCoral'}
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_traces(texttemplate='%{y:,.2f}')
    fig.update_layout(
        showlegend=False,
        # paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        )
    return fig


# @app.callback(
#     Output("pt-group-chart", "figure"), [Input('update', 'n_intervals')])
# def update_bar_chart(timer):
#     df = session.get_all_orders_dataframe()
#     return daux.get_bar_chart(df=df)


@app.callback(
    Output('cycle-count', 'value'),
    Output('trades-to-new-pt', 'value'),
    Output('traded-balance', 'value'),
    Output('traded-price-balance', 'value'),
    Output('cycle-count-from-last', 'value'),
    Output('completed-pt-count', 'value'),
    Output('pending-pt-count', 'value'),
    Input('update', 'n_intervals')
)
def update_led(timer):
    cycle_count = session.ticker_count
    df = session.get_all_orders_dataframe()
    # get balance from orders from completed pt
    btc_balance_completed_pt, eur_balance_completed_pt = daux.get_completed_pt_balance(df=df)
    # balance = self.session.get_traded_balance_callback()
    satoshi_balance = btc_balance_completed_pt * 100_000_000
    trades_to_new_pt = session.partial_traded_orders_count
    # return f'{trades_to_new_pt:02.0f}', f'{satoshi_balance:.0f}'
    cycles_from_last = session.cycles_from_last_trade
    completed_df = daux.get_completed_pt_df(df=df)
    completed_pt_count = len(completed_df['pt_id'].unique())
    total_pt_count = len(df['pt_id'].unique())
    pending_pt_count = total_pt_count - completed_pt_count
    # completed_pt_count = 1000
    return f'{cycle_count:.0f}', f'{trades_to_new_pt:06.0f}', f'{satoshi_balance:06.0f}', \
           f'{eur_balance_completed_pt:,.2f}', f'{cycles_from_last:06.0f}', \
           f'{completed_pt_count:.0f}', f'{pending_pt_count:.0f}'


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
