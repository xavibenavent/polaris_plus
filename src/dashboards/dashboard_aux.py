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
    df1 = df[df.status.ne('cmp')]
    # change monitor and placed to pending
    # df1.loc[(df.status.isin(['monitor', 'placed'])), 'status'] = 'pending'
    df1.loc[(df.status == 'monitor'), 'status'] = 'pending'
    df1.loc[(df.status == 'placed'), 'status'] = 'pending'
    # keep needed rows only
    df2 = df1[['pt_id', 'signed_total', 'status', 'name']]
    # group bt pt_id
    # df2 = df1.groupby('pt_id', as_index=False).agg({'signed_total': 'sum'})
    # create chart
    fig = px.bar(
        data_frame=df2,
        x='pt_id',
        y='signed_total',
        # template='plotly_dark',
        color='status',
        barmode='group',
        text='name',
        height=800,
        color_discrete_map={'pending': 'LightCoral', 'traded': 'LightSeaGreen'},
        range_y=[-8000, 8000],
        # range_x=[-1, 7],
    )
    fig.update_traces(
        # width=0.4,
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
        # text='btc_net_balance',
        color='btc_net_balance',
    )
    fig.update_xaxes(categoryorder='category ascending')
    return fig


def get_order_tables(df: pd.DataFrame) -> (Figure, Figure):
    # sort by price
    dff = df.sort_values(by=['price'], ascending=False)
    # filter by status for eac table (monitor-placed & traded)
    df_pending = dff[dff.status.isin(['monitor', 'placed', 'cmp'])]
    df_traded = dff[dff.status.eq('traded')]
    return df_pending.to_dict('records'), df_traded.to_dict('records')


def get_completed_pt_balance(df: pd.DataFrame) -> float:
    # get pt that have been completed
    df_completed_pt = get_completed_pt_df(df)
    # get btc balance as SUM(amount - btc_commission)
    btc_balance = df_completed_pt.signed_amount.sum() - df_completed_pt.btc_commission.sum()
    return btc_balance


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
    diff = 0
    if len(cmps) > 0:
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
        ],
        sort_action='native'
    )
    return datatable
