# pp_dashboard.py

import pandas as pd
import plotly.express as px
# import plotly.graph_objects as go

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from src.pp_dbmanager import DBManager


class Dashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)

        # note no 'src/' in file_name=
        cnx = DBManager.create_connection(file_name='../database/orders.db')
        df_po = pd.read_sql_query(f'SELECT * FROM pending_orders', cnx)
        df_to = pd.read_sql_query(f'SELECT * FROM traded_orders', cnx)
        df_po['status'] = 'monitor'
        df_to['status'] = 'traded'
        self.df = df_po.append(other=df_to)

        self.df['pt'] = self.df['pt_id'].str[8]
        # print(self.df['pt'])
        # print(self.df)

        # app layout
        self.app.layout = html.Div([
            html.H1("Session dashboard", style={'text-align': 'center'}),
            dcc.Dropdown(id='select_pt',
                         options=[
                             {'label': 'PT_000001', 'value': '1'},  # the value must coincide with de one in the df
                             {'label': 'PT_000002', 'value': '3'}
                         ],
                         multi=False,
                         value='1',
                         style={'width': '40%'}),
            html.Div(id='output_container', children=[]),
            html.Br(),
            dcc.Graph(id='orders', figure={})
        ])

        # connect the plotly graphs with dash components
        @self.app.callback(  # note self.app
            # with only one output do not use the brackets
            [Output(component_id='output_container', component_property='children'),
             Output(component_id='orders', component_property='figure')],
            [Input(component_id='select_pt', component_property='value')]
        )
        def update_graph(option_selected):  # each argument connects to one input (value -> option_selected)
            print(option_selected)
            print(type(option_selected))

            container = f'The pt selected is {option_selected}'

            dff = self.df.copy()
            dff = dff[dff['pt'] == option_selected]

            fig = px.scatter(dff,
                             x='price',
                             y='amount',
                             color='side',
                             color_discrete_map={'BUY': 'green', 'SELL': 'red'},
                             symbol='status',
                             symbol_map={'monitor': 'circle', 'traded': 'cross'}
                             )
            fig.update_traces(marker_size=25)

            return container, fig  # each returned value connects to one Output


if __name__ == '__main__':
    db = Dashboard()
    db.app.run_server(debug=True)




