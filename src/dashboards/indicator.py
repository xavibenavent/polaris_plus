# pp_dashboard.py

import pandas as pd
import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.graph_objects as go
import dash_table
import dash_table.FormatTemplate as FormatTemplate
from dash_table.Format import Format, Symbol, Sign, Scheme, Prefix

from src.pp_dbmanager import DBManager

K_INTERVAL = 2.0


class Dashboard:
    def __init__(self,
                 get_last_cmp_callback,
                 get_pending_orders_callback,
                 last_cmp):
        self.get_last_cmp_callback = get_last_cmp_callback
        self.get_pending_orders_callback = get_pending_orders_callback
        self.cmps = [last_cmp]

        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

        pending_orders_df: pd.DataFrame = self.get_pending_orders_callback()
        table_df = pending_orders_df.sort_values(by=['price'], ascending=False)
        print(table_df)
        print(table_df.describe())

        # app layout
        self.app.layout = html.Div([
            dbc.Row([
                dbc.Col(html.H1("Session dashboard", style={'text-align': 'center'}))
            ]),
            dbc.Row([
                dbc.Col(
                    dash_table.DataTable(
                        id='table',
                        # columns=[{'name': i, 'id': i} for i in table_df],  # each column can be format individually
                        columns=[
                            {'id': 'pt_id', 'name': 'pt id', 'type': 'text'},
                            {'id': 'name', 'name': 'name', 'type': 'text'},
                            {'id': 'k_side', 'name': 'side', 'type': 'text'},
                            {'id': 'price', 'name': 'price', 'type': 'numeric',
                             'format': Format(
                                 scheme=Scheme.fixed,
                                 precision=2,
                                 symbol=Symbol.yes,
                                 symbol_suffix=' €',
                             ), 'width': '80px'},
                            {'id': 'amount', 'name': 'amount', 'type': 'numeric',
                             'format': Format(
                                precision=8,
                                scheme=Scheme.fixed)},
                            {'id': 'status', 'name': 'status', 'type': 'text'}
                        ],
                        # data=table_df.to_dict('records'),
                        data = {},
                        page_action='none',  # disable pagination (default is after 250 rows)
                        style_cell={'fontSize': 18, 'font-family': 'monospace', 'backgroundColor': 'black'},
                        style_table={'height': '500px', 'overflowY': 'auto', 'backgroundColor': 'black'},  # set table height and vertical scroll
                        style_data={
                            'width': '80px',
                            'maxWidth': '80px',
                            'minWidth': '80px',
                            'border': 'none'
                        },
                        style_header={'border': 'none'},
                        fixed_rows={'headers': True},
                        hidden_columns=['status', 'k_side'],
                        style_data_conditional=[
                            {
                                'if': {
                                    'filter_query': '{k_side} = SELL',
                                    'column_id': 'price'
                                },
                                'color': 'Tomato'
                            },
                            {
                                'if': {
                                    'filter_query': '{k_side} = BUY',
                                    'column_id': 'price'
                                },
                                'color': 'Green'
                            },

                        ]
                    ),  width={'size': 4, 'offset': 1}
                ),
                dbc.Col(daq.Gauge(id='my-daq-gauge', min=0, max=10, value=6),
                        width=2)
            ]),
            dcc.Graph(
                id='indicator-graph',
                figure={},
                config={'displayModeBar': False}
            ),
            dcc.Graph(id='daily-line', figure={}, config={'displayModeBar': False}),
            dcc.Graph(
                id='balance',
                figure={},
                # style={'width': '30rem', 'height': '25rem'},
                className='mt-3'
                # config={'displayModeBar': False}
            ),
            html.H1('foo-baz-daz'),

            # component to update the app every n seconds
            dcc.Interval(id='update', n_intervals=0, interval=1000 * K_INTERVAL)
        ],
        # style={'background-color': 'tomato'})
        )

        @self.app.callback(
            Output('table', 'data'),
            Input('update', 'n_intervals')
        )
        def update_table(timer):
            pending_orders_df = self.get_pending_orders_callback()
            table_df = pending_orders_df.sort_values(by=['price'], ascending=False)
            return table_df.to_dict('records')

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
            fig.update_traces(delta_font={'size': 14}, number_font_size=18, number_valueformat=',.2f')
            fig.update_layout(height=80, width=150)
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
                ),
                height=150,
                width=500
            )
            cmp_start = self.cmps[0]
            cmp_end = self.cmps[-1]
            diff = cmp_end - cmp_start
            if diff > 0:
                return fig.update_traces(fill='tozeroy', line={'color': 'green'})
            else:
                return fig.update_traces(fill='tozeroy', line={'color': 'red'})

        @self.app.callback(
            Output('balance', 'figure'),
            Input('update', 'n_intervals')
        )
        def update_graph(timer):
            fig = go.Figure(go.Bar(
                x=['BTC', 'EUR', 'BNB'],
                y=[200, 100, 300]
            ))
            fig.update_layout(height=500, width=500)
            return fig

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




