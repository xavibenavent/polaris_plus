# layout.py

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from dash_daq.LEDDisplay import LEDDisplay
import plotly.express as px

import src.dashboards.dashboard_aux as daux

# ********** dashboard layout **********
def get_layout(interval: float):
    layout = html.Div([
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
                    data=[{}],  # session.get_orders_callback().to_dict('records'),
                    table_id='table',
                    buy_color_monitor='LightSeaGreen', sell_color_monitor='LightCoral',
                    buy_color_placed='SeaGreen', sell_color_placed='firebrick',
                ),
                width={'size': 6, 'offset': 0},
            ),
            dbc.Col(
                children=daux.get_datatable(
                    data=[{}],  # due to the 'records' parameter of DataFrame.to_dict()
                    table_id='table-traded',
                    buy_color_traded='SeaGreen', sell_color_traded='firebrick'
                ),
                width={'size': 6, 'offset': 0}
            ),
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='kpi-bar-chart'),
            ], width={'size': 9})
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='pt-group-chart', figure={}),
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
        dcc.Interval(id='update', n_intervals=0, interval=1000 * interval)
    ])
    return layout
