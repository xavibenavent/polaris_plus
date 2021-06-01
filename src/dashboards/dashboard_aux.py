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
    # change monitor and placed to pending
    df.loc[(df.status_name == 'monitor'), 'status_name'] = 'pending'
    df.loc[(df.status_name == 'placed'), 'status_name'] = 'pending'
    # keep needed rows only
    df2 = df[['pt_id', 'signed_total', 'status_name', 'name']]
    # group bt pt_id
    # df2 = df1.groupby('pt_id', as_index=False).agg({'signed_total': 'sum'})
    # create chart
    fig = px.bar(
        data_frame=df2,
        x='pt_id',
        y='signed_total',
        color='status_name',
        barmode='group',
        text='name',
        height=800,
        color_discrete_map={'pending': 'LightCoral', 'traded': 'LightSeaGreen'},
        range_y=[-10000, 10000],
    )
    fig.update_traces(
        textfont_color='white',
        insidetextanchor='middle'
    )
    fig.update_xaxes(categoryorder='category ascending')
    return fig


def get_completed_pt_chart(df: pd.DataFrame) -> Figure:
    df['btc_net_balance'] = (df.signed_amount - df.btc_commission) * 1e8
    df1 = df.groupby('pt_id', as_index=False).agg({'btc_net_balance': 'sum'})
    fig = px.bar(
        data_frame=df1,
        x='pt_id',
        y='btc_net_balance',
        color='btc_net_balance',
        color_continuous_scale=px.colors.sequential.Greens
    )
    fig.update_xaxes(categoryorder='category ascending')
    return fig


def get_completed_pt_balance(df: pd.DataFrame) -> (float, float):
    # get pt that have been completed
    df_completed_pt = get_completed_pt_df(df)
    # get btc balance as SUM(amount - btc_commission)
    btc_balance = df_completed_pt.signed_amount.sum() \
        - df_completed_pt.btc_commission.sum()  # \
    eur_balance = df_completed_pt.signed_total.sum()
    return btc_balance, eur_balance


def get_completed_pt_df(df: pd.DataFrame) -> pd.DataFrame:
    df_pending = df[df.status.isin(['monitor', 'placed'])]
    df_traded = df[df.status.eq('traded')]
    # get pt_id in traded and not in pending -> completed pt list
    pt_in_pending = df_pending.pt_id.unique().tolist()
    pt_in_traded = df_traded.pt_id.unique().tolist()
    pt_completed = []
    for pt in pt_in_traded:
        if pt not in pt_in_pending:
            pt_completed.append(pt)
    # filter df and keep only completed pt
    df_completed_pt = df[df.pt_id.isin(pt_completed)]
    return df_completed_pt


def get_cmp_indicator(cmps: List[float]) -> Figure:
    # get last and first values
    last_cmp = 0.0
    first_cmp = 0.0
    if len(cmps) > 0:
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
            showticklabels=True
        ),
        xaxis=dict(
            title=None,
            showgrid=False,
            showticklabels=True
        ),
        height=150,
        width=500
    )
    # color green or red depending on difference between last cmp and first cmp
    diff = 0
    if len(cmps) > 0:
        diff = cmps[-1] - cmps[0]
    if diff > 0:
        return fig.update_traces(fill='tozeroy', line={'color': 'green'})
    else:
        return fig.update_traces(fill='tozeroy', line={'color': 'red'})


def get_depth_span_line_chart(df: pd.DataFrame) -> Figure:
    fig = px.line(
        df,
        x='rate',
        y=['span', 'depth'],
        # dynamic y-range
        range_y=[0, 1000],
    )
    fig.update_layout(
        margin=dict(t=0, r=0, l=0, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            title=None,
            showgrid=False,
            showticklabels=True
        ),
        xaxis=dict(
            title=None,
            showgrid=False,
            showticklabels=True
        ),
        height=300,
        # width=500
    )
    return fig


def get_tank(tank_id: str, tank_max: float, label: str, show_value: bool = False):
    tank = Tank(
        id=tank_id,
        min=0.0,
        max=tank_max,
        value=tank_max,
        style={'margin-left': '50px', 'font-size': '10px'},
        label=label,
        labelPosition='bottom',
        showCurrentValue=show_value
        # color='#34f533'
    )
    return tank


def get_datatable(table_id: str,
                  data: List[dict],  # due to the 'record' parameter of DataFrame.to_dict()
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
            {'id': 'bnb_commission', 'name': 'comm_bnb', 'type': 'numeric',
             'format': Format(
                 precision=6,
                 scheme=Scheme.fixed,
                 group=True
             )},
            {'id': 'btc_commission', 'name': 'comm_btc', 'type': 'numeric',
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
                    'filter_query': '{k_side} = SELL && {status_name} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status_name} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status_name} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_monitor
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status_name} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_monitor
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status_name} = traded',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_traded
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status_name} = traded',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_traded
            },
            {
                'if': {
                    'filter_query': '{status_name} = cmp',
                    'column_id': ['price', 'name', 'pt_id', 'signed_total'],
                },
                'color': 'orange'
            }
        ],
        sort_action='native'
    )
    return datatable


def get_pending_datatable(
        table_id: str,
        data: List[dict],
        buy_color_monitor='MintCream', sell_color_monitor='MintCream',
        buy_color_placed='MintCream', sell_color_placed='MintCream'
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
            {'id': 'compensation_count', 'name': 'compensation', 'type': 'numeric',
             'format': Format(
                 precision=0,
             )},
            {'id': 'split_count', 'name': 'split', 'type': 'numeric',
             'format': Format(
                 precision=0,
             )},
            {'id': 'concentration_count', 'name': 'concentration', 'type': 'numeric',
             'format': Format(
                 precision=0,
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
                    'filter_query': '{k_side} = SELL && {status_name} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status_name} = placed',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_placed
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status_name} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': sell_color_monitor
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status_name} = monitor',
                    'column_id': ['price', 'signed_amount', 'signed_total'],
                },
                'color': buy_color_monitor
            },
            {
                'if': {
                    'filter_query': '{status_name} = cmp',
                    'column_id': ['price', 'name', 'pt_id', 'signed_total'],
                },
                'color': 'orange'
            }
        ],
        sort_action='native'
    )
    return datatable
