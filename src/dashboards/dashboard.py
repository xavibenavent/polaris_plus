# pp_dashboard.py

import pandas as pd
import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from src.pp_dbmanager import DBManager

K_INTERVAL = 1.0


class Dashboard:
    def __init__(self,
                 get_last_cmp_callback,
                 last_cmp):
        self.get_last_cmp_callback = get_last_cmp_callback
        self.cmps = [last_cmp]

        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # note no 'src/' in file_name= and ../ because it is in the dashboard folder
        # cnx = DBManager.create_connection(file_name='../database/orders.db')
        cnx = DBManager.create_connection(file_name='src/database/orders.db')
        df_po = pd.read_sql_query(f'SELECT * FROM pending_orders', cnx)
        df_to = pd.read_sql_query(f'SELECT * FROM traded_orders', cnx)
        df_po['status'] = 'monitor'
        df_to['status'] = 'traded'
        self.df = df_po.append(other=df_to)

        self.df['pt'] = self.df['pt_id'].str[8]

        # app layout
        self.app.layout = html.Div([
            html.H1("Session dashboard", style={'text-align': 'center'}),
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        dbc.Card(
                            [
                                dbc.CardImg(src='assets/bitcoin.png', top=True, style={'width': '3rem'},),
                                dbc.CardBody(
                                    [
                                        dbc.Row([
                                            dbc.Col(
                                                [html.P('CHANGE (SESSION)')],
                                                width={'size': 6}),
                                            dbc.Col(
                                                [
                                                    dcc.Graph(
                                                    id='indicator-graph',
                                                    figure={},
                                                    config={'displayModeBar': False})
                                                ],
                                                width={'size': 3, 'offset': 1})
                                        ]),
                                        dbc.Row([
                                            dbc.Col(
                                                [dcc.Graph(id='daily-line', figure={},config={'displayModeBar': False})],
                                                width=12)
                                        ], style={'height': '3rem'})
                                    ]
                                )
                            ],
                            style={'width': '30rem', 'height': '15rem'},
                            className='mt-3',
                            color='light'
                        )
                    ], width=6),  # 6 is half (12 is 100%)
                    dbc.Col([
                        dcc.Graph(
                            id='balance',
                            figure={},
                            style={'width': '30rem', 'height': '25rem'},
                            className='mt-3'
                            # config={'displayModeBar': False}
                        )
                    ], width=6)
                ], justify='center', align='center'),
                dbc.Row([
                    dbc.Col([
                        html.H1('foo-baz-daz')
                    ])
                ])
            ]),
            # component to update the app every n seconds
            dcc.Interval(id='update', n_intervals=0, interval=1000 * K_INTERVAL)
        ])

        @self.app.callback(
            Output('balance', 'figure'),
            Input('update', 'n_intervals')
        )
        def update_graph(timer):
            fig = go.Figure(go.Bar(
                x=['BTC', 'EUR', 'BNB'],
                y=[200, 100, 300]
            ))
            # fig.update_layout(height=60, width=120)
            return fig

        @self.app.callback(
            Output('indicator-graph', 'figure'),
            Input('update', 'n_intervals')
        )
        def update_graph(timer):
            last = self.cmps[-1]
            first_cmp = self.cmps[0]
            fig = go.Figure(go.Indicator(
                mode="number+delta",
                value=last,
                delta={'reference': first_cmp, 'relative': True, 'valueformat': '.2%'}))
            fig.update_traces(delta_font={'size': 8}, number_font_size=12, number_valueformat=',.2f')
            fig.update_layout(height=40, width=80)
            return fig

        @self.app.callback(
            Output('daily-line', 'figure'),
            Input('update', 'n_intervals')
        )
        def update_graph(timer):
            dff = self.get_last_cmps_df().copy()
            fig = px.line(
                dff,
                x='rate',
                y='cmp',
                range_y=[dff['cmp'].min(), dff['cmp'].max()],
                height=150
            )
            fig.update_layout(
                margin=dict(t=0, r=0, l=0, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(
                    title=None,
                    showgrid=False,
                    showticklabels=False
                ),
                xaxis=dict(
                    title=None,
                    showgrid=False,
                    showticklabels=False
                )
            )
            cmp_start = self.cmps[0]
            cmp_end = self.cmps[-1]
            diff = cmp_end - cmp_start
            if diff > 0:
                return fig.update_traces(fill='tozeroy', line={'color': 'green'})
            else:
                return fig.update_traces(fill='tozeroy', line={'color': 'red'})

    def get_last_cmps_df(self) -> pd.DataFrame:
        # get last cmp
        last_cmp = self.get_last_cmp_callback()
        # update list
        self.cmps.append(last_cmp)
        # create dataframe from list
        df = pd.DataFrame(data=self.cmps, columns=['cmp'])
        df['rate'] = df.index
        return df


if __name__ == '__main__':  # change path in line 31 when using this
    db = Dashboard(get_last_cmp_callback=None, last_cmp=45_000.0)
    db.app.run_server(debug=True)




