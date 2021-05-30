# pp_dash.py
import sys
import logging
import os
import inspect

import flask
from flask import request  # to stop the server
import pandas as pd
# import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
# import dash_daq as daq
# import plotly.graph_objects as go
# import dash_table
# from dash_table.Format import Format, Scheme
from dash_daq.LEDDisplay import LEDDisplay

# *********** to run from terminal project folder ***********
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# ***********************************************************

import src.main2
from src.dashboards import dashboard_aux as daux
from src.pp_session import Session
from src.xb_logger import XBLogger

K_INTERVAL = 1.0

K_BACKGROUND_COLOR = '#272b30'

# to create the initial datatable
K_INITIAL_DATA = dict(pt_id='-', name='-', k_side='BUY', price=45000, signed_amount='-', signed_total='-', status='cmp')


# class Dashboard:
#     def __init__(self,
#                  session: Session,
#                  get_orders_callback,
#                  get_account_balance_callback):

XBLogger()
log = logging.getLogger('log')

# TODO: remove, here the app arguments have been forced to simplify gunicorn test
session = Session(client_mode='simulated', new_master_session=True)

# self.session = session
get_orders_callback = session.get_orders_callback()
get_account_balance_callback = session.get_account_balance()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# app layout
app.layout = html.Div([
    dbc.Row([
        dbc.Col(html.H1("Session dashboard", style={'text-align': 'center'}))
    ]),
    dbc.Row([
        dbc.Col(
            children=daux.get_tank(tank_id='daq-tank-btc', tank_max=0.4, label='BTC (free)'),
            width={'size': 1, 'offset': 1}
        ),
        dbc.Col(
            children=daux.get_tank(tank_id='daq-tank-eur', tank_max=20_000.0, label='EUR (free)'),
            width={'size': 1, 'offset': 0}
        ),
        dbc.Col(
            children=[
                LEDDisplay(id='trades-to-new-pt', label='trades to new pt', value='0', color='SeaGreen'),
                LEDDisplay(id='traded-balance', label='traded orders balance', value='0',
                           color='SeaGreen'),
                LEDDisplay(id='traded-price-balance', label='traded price balance', value='0',
                           color='DarkSeaGreen'),
                LEDDisplay(id='cycle-count-from-last', label='cycles count from last traded order', value='0',
                           color='SeaGreen'),
                html.Br(),
                dbc.Button('STOP SIMULATION', id='new-pt-button', color='success', block=True),
                html.Span(id="example-output", style={"vertical-align": "middle"})
            ],
            width={'size': 2, 'offset': 1}
        ),
        dbc.Col([
            dcc.Graph(id='completed-pt-balance-chart'),
        ], width={'size': 6})
    ]),
    dbc.Row([
        dbc.Col(
            children=daux.get_pending_datatable(
                data=session.get_orders_callback().to_dict('records'),
                table_id='table',
                buy_color_monitor='LightSeaGreen', sell_color_monitor='LightCoral',
                buy_color_placed='SeaGreen', sell_color_placed='firebrick',
            ),
            width={'size': 6, 'offset': 0},
        ),
        dbc.Col(
            children=daux.get_datatable(
                data=session.get_orders_callback().to_dict('records'),
                table_id='table-traded',
                buy_color_traded='SeaGreen', sell_color_traded='firebrick'
            ),
            width={'size': 6, 'offset': 0}
        ),
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='pt-group-chart'),
            dcc.Graph(
                id='indicator-graph',
                figure={},
                config={'displayModeBar': False}
            ),
            dcc.Graph(id='daily-line', figure={}, config={'displayModeBar': False}),
        ]),
        dbc.Col([
            dcc.Graph(id='orders-depth', figure={}),
        ], width={'size': 4})
    ]),
    # component to update the app every n seconds
    dcc.Interval(id='update', n_intervals=0, interval=1000 * K_INTERVAL)
])

# ********** app callbacks **********
@app.callback(Output('example-output', 'children'),
                   [Input('new-pt-button', 'n_clicks')])
def on_button_click(n):
    if n is None:
        return 'not clicked yet!'
    else:
        # self.session.create_new_pt(cmp=session.cmps[-1])  # direct to create_new_pt(), not to assess_new_pt()
        # return f'pt created with the button: {self.session.pt_created_count}'
        # sys.exit('SIMULATION STOPPED')
        shutdown()
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
    Output("pt-group-chart", "figure"), [Input('update', 'n_intervals')])
def update_bar_chart(timer):
    df = session.get_orders_callback()
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
    return f'{trades_to_new_pt:02.0f}', f'{satoshi_balance:.0f}', \
           f'{eur_balance_completed_pt:,.2f}', f'{cycles_from_last}'

@app.callback(
    Output('daq-tank-btc', 'value'), Input('update', 'n_intervals')
)
def update_tank_btc(timer):
    account_balance = session.get_account_balance()
    return account_balance.s1.free  # , account_balance.s2.free

@app.callback(
    Output('daq-tank-eur', 'value'), Input('update', 'n_intervals')
)
def update_tank_eur(timer):
    account_balance = session.get_account_balance()
    return account_balance.s2.free

@app.callback(
    Output('table', 'data'), Output('table-traded', 'data'),
    Input('update', 'n_intervals')
)
def update_table(timer):
    df = session.get_orders_callback()
    return daux.get_order_tables(df=df)

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

@app.callback(
    Output('orders-depth', 'figure'), Input('update', 'n_intervals')
)
def update_depth_line_chart(timer):
    depths = session.orders_book_depth
    spans = session.orders_book_span
    df = pd.DataFrame(data=dict(depth=depths, span=spans))
    df['rate'] = df.index
    fig = daux.get_depth_span_line_chart(df=df)
    return fig


def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


if __name__ == '__main__':  # change path in line 31 when using this
    app.run_server(debug=True)