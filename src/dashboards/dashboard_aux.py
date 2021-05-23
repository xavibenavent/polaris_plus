# dashboard_aux.py

from typing import List
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure, Indicator
from dash_daq.Tank import Tank
from dash_table import DataTable
from dash_table.Format import Format, Scheme


# ********** dashboard app.callback functions **********

def get_bar_chart(df: pd.DataFrame) -> Figure:
    # filter selected orders only
    df_traded = df[df.status.eq('traded')]
    # keep needed rows only
    df1 = df_traded[['pt_id', 'signed_total']]
    # group bt pt_id
    df2 = df1.groupby('pt_id', as_index=False).agg({'signed_total': 'sum'})
    # create chart
    fig = px.bar(
        data_frame=df2,
        x='pt_id',
        y='signed_total',
    )
    return fig


def get_order_tables(df: pd.DataFrame) -> (Figure, Figure):
    # sort by price
    dff = df.sort_values(by=['price'], ascending=False)
    # filter by status for eac table (monitor-placed & traded)
    df_pending = dff[dff.status.isin(['monitor', 'placed', 'cmp'])]
    df_traded = dff[dff.status.eq('traded')]
    return df_pending.to_dict('records'), df_traded.to_dict('records')


def get_cmp_indicator(cmps: List[float]) -> Figure:
    # get last and first values
    last_cmp = cmps[-1]
    first_cmp = cmps[0]
    # create indicator
    fig = Figure(Indicator(
        mode="number+delta",
        value=last_cmp,
        delta={'reference': first_cmp, 'relative': True, 'valueformat': '.2%'}))
    fig.update_traces(delta_font={'size': 14}, number_font_size=18, number_valueformat=',.2f')
    fig.update_layout(height=80, width=150)
    return fig


def get_cmp_line_chart(df: pd.DataFrame, cmps: List[float]) -> Figure:
    fig = px.line(
        df,
        x='rate',
        y='cmp',
        # dynamic y-range
        range_y=[df['cmp'].min(), df['cmp'].max()],
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
    # color green or red depending on difference between last cmp and first cmp
    diff = cmps[-1] - cmps[0]
    if diff > 0:
        return fig.update_traces(fill='tozeroy', line={'color': 'green'})
    else:
        return fig.update_traces(fill='tozeroy', line={'color': 'red'})


def get_tank(tank_id: str, tank_max: float, label: str):
    tank = Tank(
        id=tank_id,
        min=0.0,
        max=tank_max,
        value=tank_max,
        style={'margin-left': '50px'},
        label=label,
        labelPosition='bottom',
        # color='#34f533'
    )
    return tank


def get_datatable(table_id: str,
                  data: dict,
                  buy_color_monitor='MintCream', sell_color_monitor='MintCream',
                  buy_color_placed='MintCream', sell_color_placed='MintCream',
                  buy_color_traded='MintCream', sell_color_traded='MintCream'
                  ):
    datatable = DataTable(
        id=table_id,
        # columns=[{'name': i, 'id': i} for i in table_df],  # each column can be format individually
        columns=[
            {'id': 'pt_id', 'name': 'pt id', 'type': 'text'},
            {'id': 'name', 'name': 'name', 'type': 'text'},
            {'id': 'price', 'name': 'price', 'type': 'numeric',
             'format': Format(
                 scheme=Scheme.fixed,
                 precision=2,
                 group=True,
             )},
            {'id': 'signed_amount', 'name': 'amount', 'type': 'numeric',
             'format': Format(
                 precision=6,
                 scheme=Scheme.fixed)},
            {'id': 'signed_total', 'name': 'total', 'type': 'numeric',
             'format': Format(
                 precision=2,
                 scheme=Scheme.fixed,
                 group=True
             )},
            {'id': 'bnb_commission', 'name': 'commission', 'type': 'numeric',
             'format': Format(
                 precision=6,
                 scheme=Scheme.fixed,
                 group=True
             )}
        ],
        data=data,
        page_action='none',  # disable pagination (default is after 250 rows)
        style_table={'height': '800px', 'overflowY': 'auto'},  # , 'backgroundColor': K_BACKGROUND_COLOR},
        style_cell={'fontSize': 16, 'font-family': 'Arial'},
        # set table height and vertical scroll
        style_data={
            'width': '90px',
            'maxWidth': '90px',
            'minWidth': '50px',
            'border': 'none'
        },
        css=[{"selector": ".show-hide", "rule": "display: none"}],  # hide toggle button on top of the table
        style_header={'border': 'none', 'textAlign': 'center', 'fontSize': 16, 'fontWeight': 'bold'},
        fixed_rows={'headers': True},
        hidden_columns=['status', 'k_side'],
        style_cell_conditional=[
            {
                'if': {'column_id': ['pt_id', 'name']},
                'textAlign': 'center'
            }
        ],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_monitor
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_monitor
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = traded',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_traded
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = traded',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_traded
            },
            {
                'if': {
                    'filter_query': '{status} = cmp',
                    'column_id': ['price', 'name', 'pt_id', 'signed_total'],
                },
                'color': 'orange'
            }
        ]
    )
    return datatable
