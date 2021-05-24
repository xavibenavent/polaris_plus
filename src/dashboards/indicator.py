# pp_dashboard.py

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

from src.dashboards import dashboard_aux as daux
from src.pp_session import Session

K_INTERVAL = 2.0

K_BACKGROUND_COLOR = '#272b30'

# to create the initial datatable
K_INITIAL_DATA = dict(pt_id='-', name='-', k_side='BUY', price=45000, signed_amount='-', signed_total='-', status='cmp')


class Dashboard:
    def __init__(self,
                 session: Session,
                 get_orders_callback,
                 get_account_balance_callback):
        self.session = session
        self.get_orders_callback = get_orders_callback
        self.get_account_balance_callback = get_account_balance_callback

        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # app layout
        self.app.layout = html.Div([
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
                        LEDDisplay(id='cycle-count-from-last', label='cycles count from last traded order', value='0',
                                   color='SeaGreen'),
                        html.Br(),
                        dbc.Button('Create new PT', id='new-pt-button', color='warning', block=True),
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
                    children=daux.get_datatable(
                        data=self.get_orders_callback().to_dict('records'),
                        table_id='table',
                        buy_color_monitor='LightSeaGreen', sell_color_monitor='LightCoral',
                        buy_color_placed='SeaGreen', sell_color_placed='firebrick',
                    ),
                    width={'size': 5, 'offset': 1},
                ),
                dbc.Col(
                    children=daux.get_datatable(
                        data=self.get_orders_callback().to_dict('records'),
                        table_id='table-traded',
                        buy_color_traded='SeaGreen', sell_color_traded='firebrick'
                    ),
                    width={'size': 5, 'offset': 1}
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
            ]),
            # component to update the app every n seconds
            dcc.Interval(id='update', n_intervals=0, interval=1000 * K_INTERVAL)
        ])

        # ********** app callbacks **********
        @self.app.callback(Output('example-output', 'children'), [Input('new-pt-button', 'n_clicks')])
        def on_button_click(n):
            if n is None:
                return 'not clicked yet!'
            else:
                self.session.pt_created_count += 1
                self.session.create_new_pt(cmp=session.cmps[-1])  # direct to create_new_pt(), not to assess_new_pt()
                # self.session.cycles_from_last_trade = 0  # equivalent to trading but without a trade
                self.session.partial_traded_orders_count -= 2
                return f'pt_created_count: {self.session.pt_created_count}'

        @self.app.callback(
            Output('completed-pt-balance-chart', 'figure'), Input('update', 'n_intervals'))
        def update_chart(timer):
            df = self.get_orders_callback()
            # get dataframe with orders from completed pt
            completed_pt_df = daux.get_completed_pt_df(df=df)
            fig = daux.get_completed_pt_chart(df=completed_pt_df)
            return fig

        @self.app.callback(
            Output("pt-group-chart", "figure"), [Input('update', 'n_intervals')])
        def update_bar_chart(timer):
            df = self.get_orders_callback()
            return daux.get_bar_chart(df=df)

        @self.app.callback(
            Output('trades-to-new-pt', 'value'),
            Output('traded-balance', 'value'),
            Output('cycle-count-from-last', 'value'),
            Input('update', 'n_intervals')
        )
        def update_led(timer):
            df = self.get_orders_callback()
            # get balance from orders from completed pt
            btc_balance_completed_pt = daux.get_completed_pt_balance(df=df)
            # balance = self.session.get_traded_balance_callback()
            satoshi_balance = btc_balance_completed_pt * 100_000_000
            trades_to_new_pt = self.session.partial_traded_orders_count
            # return f'{trades_to_new_pt:02.0f}', f'{satoshi_balance:.0f}'
            cycles_from_last = self.session.cycles_from_last_trade
            return f'{trades_to_new_pt:02.0f}', f'{satoshi_balance:.0f}', f'{cycles_from_last}'

        @self.app.callback(
            Output('daq-tank-btc', 'value'), Input('update', 'n_intervals')
        )
        def update_tank_btc(timer):
            account_balance = self.get_account_balance_callback()
            return account_balance.s1.free  # , account_balance.s2.free

        @self.app.callback(
            Output('daq-tank-eur', 'value'), Input('update', 'n_intervals')
        )
        def update_tank_eur(timer):
            account_balance = self.get_account_balance_callback()
            return account_balance.s2.free

        @self.app.callback(
            Output('table', 'data'), Output('table-traded', 'data'),
            Input('update', 'n_intervals')
        )
        def update_table(timer):
            df = self.get_orders_callback()
            return daux.get_order_tables(df=df)

        @self.app.callback(
            Output('indicator-graph', 'figure'), Input('update', 'n_intervals')
        )
        def update_cmp_indicator(timer):
            # get all session cmp
            cmps = self.session.cmps
            fig = daux.get_cmp_indicator(cmps=cmps)
            return fig

        @self.app.callback(
            Output('daily-line', 'figure'), Input('update', 'n_intervals')
        )
        def update_cmp_line_chart(timer):
            # get session cmps
            cmps = self.session.cmps
            # create dataframe from cmps list
            df = pd.DataFrame(data=cmps, columns=['cmp'])
            df['rate'] = df.index
            # create line chart
            fig = daux.get_cmp_line_chart(df=df, cmps=cmps)
            return fig


if __name__ == '__main__':  # change path in line 31 when using this
    db = Dashboard(
        session=None,
        get_orders_callback=None,
        get_account_balance_callback=None)
    db.app.run_server(debug=True)
