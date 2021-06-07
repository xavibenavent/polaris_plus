# layout.py

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

import src.dashboards.dashboard_aux as daux


# ********** dashboard layout **********
def get_layout(interval: float):
    layout = html.Div([
        dbc.Row([
            dbc.Col(html.H1("Session dashboard", style={'text-align': 'center'})),
        ]),
        dbc.Row([
            dbc.Button('STOP SIMULATION', id='new-pt-button', color='success', block=True),
            html.Span(id="example-output", style={"vertical-align": "middle"}),
            html.Br(),
        ]),
        dbc.Row([
            # ********** balance bar charts **********
            dbc.Col(
                dcc.Graph(id='btc-balance-chart'),
                width={'size': 1, 'offset': 0},
            ),
            dbc.Col(
                dcc.Graph(id='eur-balance-chart'),
                width={'size': 1, 'offset': 0}
            ),
            dbc.Col(
                dcc.Graph(id='bnb-balance-chart'),
                width={'size': 1, 'offset': 0}
            ),
            # ********** monitoring LEDs **********
            dbc.Col(
                children=[
                    daux.get_led_display(led_id='cycle-count', led_label='from start'),
                    daux.get_led_display(led_id='cycle-count-from-last', led_label='from last trade'),
                    daux.get_led_display(led_id='trades-to-new-pt', led_label='trades to new pt'),
                    daux.get_led_display(led_id='traded-balance', led_label='balance [satoshi]'),
                    daux.get_led_display(led_id='traded-price-balance', led_label='balance [eur]'),
                    daux.get_led_display(led_id='completed-pt-count', led_label='completed pt'),
                    daux.get_led_display(led_id='pending-pt-count', led_label='pending pt'),
                ],
                width={'size': 2, 'offset': 0},
            ),
            # ********** symbol lone graph **********
            dbc.Col([
                dcc.Graph(
                    id='indicator-graph',
                    figure={},
                    config={'displayModeBar': False}
                ),
                dcc.Graph(id='daily-line', figure={}, config={'displayModeBar': False}),
            ], width={'size': 2}),
            # ********** concentration for different gaps (100, 200, ..., 500) **********
            dbc.Col([
                dcc.Graph(id='kpi-bar-chart'),
            ], width={'size': 5})
        ]),
        # ********** order tables (pending & traded) **********
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
        ]),
        # ********** interval **********
        dcc.Interval(id='update', n_intervals=0, interval=1000 * interval)
    ])
    return layout
