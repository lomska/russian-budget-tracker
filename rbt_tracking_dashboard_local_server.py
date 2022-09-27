import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

from jupyter_dash import JupyterDash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from collections import OrderedDict
from dash import dash_table

# THE DATA *********************************************************************************************************************************
# ******************************************************************************************************************************************

df = pd.read_csv('final_data/russian_budget_data.csv', index_col=0)

# SMALL CARDS DATA *************************************************************************************************************************

data = df.query('(i1 == 1 & i3 == 1 & r3 == 0) | (i1 == 1 & i3 == 2 & s1 == 0) | (i1 == 1 & i3 in (5,6,7,8,9))').pivot(
    index=['year','region_eng'], columns='index', values='value').reset_index()

# defining donor regions
def donor(s):
    if s['tax_to_fed'] > s['reg_own_revenue']:
        return 1
    else:
        return 0
data['donor'] = data.apply(donor, axis=1)

# defining dependent regions
def dependent(s):
    if s['transfers_to_reg'] > s['reg_own_revenue']:
        return 1
    else:
        return 0
data['dependent'] = data.apply(dependent, axis=1)

# surplus/deficit = own revenue + federal transfers - spending
data['deficit'] = data['reg_own_revenue']+data['transfers_to_reg']-data['reg_spending']

# converting everything to $
data['tax_to_fed_usd'] = data['tax_to_fed']/data['rub_usd']
data['reg_own_revenue_usd'] = data['reg_own_revenue']/data['rub_usd']
data['transfers_to_reg_usd'] = data['transfers_to_reg']/data['rub_usd']
data['reg_spending_usd'] = data['reg_spending']/data['rub_usd']
data['deficit_usd'] = data['deficit']/data['rub_usd']

# counting all the sums
cards_by_year = data[['year', 'donor', 'dependent', 'tax_to_fed_usd', 'transfers_to_reg_usd',
                      'reg_own_revenue_usd', 'deficit_usd']].groupby('year').sum()

# converting everything to $ bln
cards_by_year[['tax_to_fed_usd', 'transfers_to_reg_usd', 'reg_own_revenue_usd', 'deficit_usd']] = (
    cards_by_year[['tax_to_fed_usd', 'transfers_to_reg_usd', 'reg_own_revenue_usd', 'deficit_usd']]/1000000000).round(1)

# final columns
cards_by_year.columns = ['donor', 'dependent', 'tax_to_fed_usd_bn', 'transfers_to_reg_usd_bn',
                         'reg_own_revenue_usd_bn', 'deficit_usd_bn']

# TREEMAP DATA ****************************************************************************************************************************

treemap_data = df.query('(i1 == 1 & r1 != 0 & r3 == 0) | (i1 == 1 & i3 == 2 & s1 == 0) | (i1 == 1 & 5 <= i3 <= 9) | (i1 == 1 & i3 == 2 & s1 in (7,9) & s2 == 0)')[['year', 'index', 'region_eng', 'value']].pivot(index=['year', 'region_eng'], columns='index', values='value').fillna(0)

# net cash flow from the state to the region
treemap_data['flow_to_fed'] = treemap_data['transfers_to_reg']-treemap_data['tax_to_fed']

# net cash flow from the state to the region, $ mln
treemap_data['flow_to_fed_usd'] = (treemap_data['flow_to_fed']/treemap_data['rub_usd']/1000000).round(1)

# absolute net cash flow from the state to the region or back, $ mln
treemap_data['flow_to_fed_usd_abs'] = abs(treemap_data['flow_to_fed_usd'])

# converting everything to $ mln
treemap_data['reg_own_revenue_usd'] = (treemap_data['reg_own_revenue']/treemap_data['rub_usd']/1000000).round(1)
treemap_data['tax_to_fed_usd'] = (treemap_data['tax_to_fed']/treemap_data['rub_usd']/1000000).round(1)
treemap_data['transfers_to_reg_usd'] = (treemap_data['transfers_to_reg']/treemap_data['rub_usd']/1000000).round(1)

# converting income per capita to $
treemap_data['income_usd_per_cap'] = (treemap_data['income_per_cap']/treemap_data['rub_usd']).round(1)

# defining donor and dependent regions for "parent" markers
def big_class(s):
    if s['flow_to_fed_usd'] > 0:
        return 'Absorbing Regions'
    elif s['flow_to_fed_usd'] < 0:
        return 'Donating Regions'
treemap_data['big_class'] = treemap_data.apply(big_class, axis=1)

# defining the type of money flow for hoverdata
def balance_type(s):
    if s['big_class'] == 'Donating Regions':
        return 'Donation'
    else:
        return 'Aid'
treemap_data['balance_type'] = treemap_data.apply(balance_type, axis=1)

# final columns
treemap_data = treemap_data[treemap_data['flow_to_fed_usd'].notna()].reset_index()[['year',
                                                                                    'big_class',
                                                                                    'region_eng',
                                                                                    'reg_own_revenue_usd',
                                                                                    'tax_to_fed_usd',
                                                                                    'transfers_to_reg_usd',
                                                                                    'flow_to_fed_usd',
                                                                                    'flow_to_fed_usd_abs',
                                                                                    'population',
                                                                                    'income_usd_per_cap',
                                                                                    'balance_type']]

# converting the names of the regions and classes to the title mode
treemap_data['region_eng'] = treemap_data['region_eng'].str.title()
treemap_data['big_class'] = treemap_data['big_class'].str.title()

# some improvements for better chart design
treemap_data['region_eng'] = treemap_data['region_eng'].replace('Autonomous Okrug', 'AO', regex=True)
treemap_data['region_eng'] = treemap_data['region_eng'].replace(' – Ugra', '', regex=True)

# BAR PLOTS DATA ***************************************************************************************************************************

# defining the top-10 for each category
top_donors = data[['year', 'region_eng', 'tax_to_fed_usd']].sort_values(by=['year', 'tax_to_fed_usd'],
                                                                        ascending=[True,False]).groupby('year').head(10)
top_takers = data[['year', 'region_eng', 'transfers_to_reg_usd']].sort_values(by=['year', 'transfers_to_reg_usd'],
                                                                              ascending=[True,False]).groupby('year').head(10)
top_earning = data[['year', 'region_eng', 'reg_own_revenue_usd']].sort_values(by=['year', 'reg_own_revenue_usd'],
                                                                              ascending=[True,False]).groupby('year').head(10)
top_deficits = data[['year', 'region_eng', 'deficit_usd']].sort_values(by=['year', 'deficit_usd'],
                                                                       ascending=[True,True]).groupby('year').head(10)

# converting the names of the regions to the title mode
top_donors['region_eng'] = top_donors['region_eng'].str.title()
top_takers['region_eng'] = top_takers['region_eng'].str.title()
top_earning['region_eng'] = top_earning['region_eng'].str.title()
top_deficits['region_eng'] = top_deficits['region_eng'].str.title()

# converting everything to $ bn
top_donors['tax_to_fed_usd'] = (top_donors['tax_to_fed_usd']/1000000000).round(1)
top_takers['transfers_to_reg_usd'] = (top_takers['transfers_to_reg_usd']/1000000000).round(1)
top_earning['reg_own_revenue_usd'] = (top_earning['reg_own_revenue_usd']/1000000000).round(1)
top_deficits['deficit_usd'] = (top_deficits['deficit_usd']/1000000000*(-1)).round(1)

# sorting the top-10
top_donors = top_donors.set_index('year').sort_values(by='tax_to_fed_usd')
top_takers = top_takers.set_index('year').sort_values(by='transfers_to_reg_usd')
top_earning = top_earning.set_index('year').sort_values(by='reg_own_revenue_usd')
top_deficits = top_deficits.set_index('year').sort_values(by='deficit_usd')

# some improvements for better chart design
top_donors['region_eng'] = top_donors['region_eng'].replace('Autonomous Okrug', 'AO', regex=True)
top_donors['region_eng'] = top_donors['region_eng'].replace(' – Ugra', '', regex=True)
top_donors['region_eng'] = top_donors['region_eng'].replace('Nizhny Novgorod', 'N.Novgorod', regex=True)
top_takers['region_eng'] = top_takers['region_eng'].replace('Autonomous Okrug', 'AO', regex=True)
top_takers['region_eng'] = top_takers['region_eng'].replace(' – Ugra', '', regex=True)
top_takers['region_eng'] = top_takers['region_eng'].replace('Nizhny Novgorod', 'N.Novgorod', regex=True)
top_earning['region_eng'] = top_earning['region_eng'].replace('Autonomous Okrug', 'AO', regex=True)
top_earning['region_eng'] = top_earning['region_eng'].replace(' – Ugra', '', regex=True)
top_earning['region_eng'] = top_earning['region_eng'].replace('Nizhny Novgorod', 'N.Novgorod', regex=True)
top_deficits['region_eng'] = top_deficits['region_eng'].replace('Autonomous Okrug', 'AO', regex=True)
top_deficits['region_eng'] = top_deficits['region_eng'].replace(' – Ugra', '', regex=True)
top_deficits['region_eng'] = top_deficits['region_eng'].replace('Nizhny Novgorod', 'N.Novgorod', regex=True)

# SCATTER PLOT DATA ***********************************************************************************************************************

# net cash flow from the state to the region as a percentage of the region's own revenue
data['reg_fed_flow_vs_rev'] = ((data['transfers_to_reg']-data['tax_to_fed'])/data['reg_own_revenue']*100).round(0)

# surplus/deficit as a percentage of the region's own revenue
data['deficit_vs_rev'] = (data['deficit']/data['reg_own_revenue']*100).round(0)

# income per capita
data['income_per_cap_usd'] = (data['income_per_cap']/data['rub_usd']).round(1)

#final columns
scatter_regions = data[['year', 'region_eng', 'reg_fed_flow_vs_rev', 'deficit_vs_rev', 'population', 'income_per_cap_usd']]

# TABLE DATA ******************************************************************************************************************************

# max federal tax item for each region
dft = df.query('(i1 == 1 & r1 == 3 & r3 != 0 & r4 == 0) | (i1 == 1 & r1 == 3 & r3 != 0 & r4 != 0 & r5 == 0)').iloc[:, 10:]
dft['max'] = dft.groupby(['year', 'region_eng'])['value'].transform('max')
dft = dft[(dft['value'] == dft['max']) & (dft['value'] != 0)]
dft = dft.set_index(['year', 'region_eng'])[['index', 'value']]
dft.columns = ['key_tax_to_fed', 'key_tax_to_fed_amount']

# max own revenue item for each region
dfr = df.query('(i1 == 1 & r1 == 1 & r3 in (1,3) & r4 != 0 & r5 == 0) | (i1 == 1 & r1 == 1 & r3 not in (0,1,3) & r4 == 0)').iloc[:, 10:]
dfr['max'] = dfr.groupby(['year', 'region_eng'])['value'].transform('max')
dfr = dfr[(dfr['value'] == dfr['max']) & (dfr['value'] != 0)]
dfr = dfr.set_index(['year', 'region_eng'])[['index', 'value']]
dfr.columns = ['key_revenue', 'key_revenue_amount']

# max spending item for each region
dfs = df.query('(i1 == 1 & i3 == 2 & 0 < s1 < 13 & s2 == 0)').iloc[:, 10:]
dfs['max'] = dfs.groupby(['year', 'region_eng'])['value'].transform('max')
dfs = dfs[(dfs['value'] == dfs['max']) & (dfs['value'] != 0)]
dfs = dfs.set_index(['year', 'region_eng'])[['index', 'value']]
dfs.columns = ['key_spending', 'key_spending_amount']

# exchange rate for the year
usdrub = df.query('i1 == 1 & i3 == 9').iloc[:, 11:].set_index(['year', 'region_eng'])

# concatinating the regional data:
key_sums = dft.join([dfr, dfs, usdrub])

# fixing the tax/revenue name
key_sums['key_tax_to_fed'] = key_sums['key_tax_to_fed'].replace('corporate income tax full', 'corporate income tax', regex=True)
key_sums['key_revenue_amount'] = key_sums['key_revenue_amount'].replace('corporate income tax full', 'corporate income tax', regex=True)

# convertiong everything to $
key_sums['key_tax_to_fed_amount_usd'] = key_sums['key_tax_to_fed_amount']/key_sums['value']
key_sums['key_revenue_amount_usd'] = key_sums['key_revenue_amount']/key_sums['value']
key_sums['key_spending_amount_usd'] = key_sums['key_spending_amount']/key_sums['value']

# the name and the amount of key revenue, tax, and spending for each region
key_sums = key_sums[['key_tax_to_fed', 'key_tax_to_fed_amount_usd', 'key_revenue',
                     'key_revenue_amount_usd', 'key_spending', 'key_spending_amount_usd']]

# merging all the data
regional_cards = data[['year', 'region_eng', 'reg_own_revenue_usd', 'tax_to_fed_usd', 'transfers_to_reg_usd',
                       'reg_spending_usd', 'deficit_usd', 'population', 'income_per_cap_usd', 'real_income']]
regional_cards = regional_cards.set_index(['year', 'region_eng']).join(key_sums).reset_index()

# converting everything to $ mln
regional_cards[['reg_own_revenue_usd', 'tax_to_fed_usd', 'transfers_to_reg_usd', 'reg_spending_usd', 'deficit_usd',
                'key_tax_to_fed_amount_usd', 'key_revenue_amount_usd', 'key_spending_amount_usd']] = (
    regional_cards[['reg_own_revenue_usd', 'tax_to_fed_usd', 'transfers_to_reg_usd', 'reg_spending_usd', 'deficit_usd',
                    'key_tax_to_fed_amount_usd', 'key_revenue_amount_usd', 'key_spending_amount_usd']]/1000000).round(1)

# final columns
regional_cards.columns = ['year', 'region_eng', 'reg_own_revenue_usdmln', 'tax_to_fed_usdmln', 'transfers_to_reg_usdmln',
                          'reg_spending_usdmln', 'deficit_usdmln', 'population', 'income_per_cap_usd', 'real_income',
                          'key_tax_to_fed', 'key_tax_to_fed_amount_usdmln', 'key_revenue', 'key_revenue_amount_usdmln',
                          'key_spending', 'key_spending_amount_usdmln']

# THE DASHBOARD ***************************************************************************************************************************
# *****************************************************************************************************************************************

app = JupyterDash(__name__, external_stylesheets=[dbc.themes.LUX])

# LAYOUT **********************************************************************************************************************************

app.layout = dbc.Container([
    html.Div([
        dbc.Row([
            dbc.Col(html.H1("Regions' Budgets Tracker"), width=7, align="center"),
            dbc.Col(html.A("About the project", href='https://github.com/lomska/russian-budget-tracker.git', target="_blank"),
                    width=2, align="center"),
            dbc.Col([html.H6('Select a Year:', style={'width':'100%', 'height':'20%'}),
                     dcc.Dropdown(id='slct_year', options=[
                         {'label':'2011', 'value':2011},
                         {'label':'2012', 'value':2012},
                         {'label':'2013', 'value':2013},
                         {'label':'2014', 'value':2014},
                         {'label':'2015', 'value':2015},
                         {'label':'2016', 'value':2016},
                         {'label':'2017', 'value':2017},
                         {'label':'2018', 'value':2018},
                         {'label':'2019', 'value':2019},
                         {'label':'2020', 'value':2020},
                         {'label':'2021', 'value':2021}],
                                  multi=False, value=2021, clearable=False, style={'width':'100%', 'height':'20%'}
                                 )
                    ], width=3)
        ], className='mb-2 mt-2'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(['Donor', html.Br(), 'Regions'], style={'width':'100%', 'height':'20%'}, className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-donors', children='00', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6('Dependent Regions', style={'width':'100%', 'height':'20%'}, className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-dependent', children='00', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Cumulative Own Revenues", style={'width':'100%', 'height':'20%'}, className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-ownrev', children='000', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6('Tribute to the state', style={'width':'100%', 'height':'20%'}, className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-tax-to-fed', children='000', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6('Transfers from the state', style={'width':'100%', 'height':'20%'}, className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-transfers', children='00', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(id='content-defsur', children='Deficit', style={'width':'100%', 'height':'20%'},
                                className="card-title"),
                        html.H6(' ', style={'width':'100%', 'height':'10%'}),
                        html.H4(id='content-deficit', children='00', style={'width':'100%', 'height':'20%'})
                    ])
                ], style={'height':'85%', 'textAlign':'center'}, color="dark", outline=True)
            ], width=2)
        ], className='mb-0 mt-2'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.H4("Federal money suppliers, absorbers, and their input", className="card-title mt-3",
                            style={'margin-left':'20px'}),
                    html.H6("Hover over the region to see info for the year:", className="card-subtitle",
                            style={'margin-left':'20px'}),
                    dbc.CardBody([
                        dcc.Graph(id='treemap', figure={}),
                    ])
                ], color="dark", outline=True)
            ], width=12),
        ], className='mb-2 mt-0'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.H4("Leaders of the year", className="card-title mt-3", style={'margin-left':'20px'}),
                    html.H6("Choose your top-10:", className="card-subtitle", style={'margin-left':'20px'}),
                    dbc.CardBody([
                        html.Div(
                            [dbc.RadioItems(
                                id="radios",
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-primary btn-sm",
                                labelCheckedClassName="active",
                                options=[
                                    {"label": "Donors", "value": 1},
                                    {"label": "Absorbers", "value": 2},
                                    {"label": "Earners", "value": 3},
                                    {'label': 'Deficits', 'value': 4}
                                ],
                                value=1,
                                label_style={'font-size':9}
                            )], className="radio-group")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(id='bar-chart', figure={}),
                    ])
                ], color="dark", outline=True)
            ], width=4),
            dbc.Col([
                dbc.Card([
                    html.H4("Regional money flows and balances", className="card-title mt-3", style={'margin-left':'20px'}),
                    html.H6("Hover over the region to see info for the year:", className="card-subtitle",
                            style={'margin-left':'20px'}),
                    dbc.CardBody([
                        dcc.Graph(id='scatter-chart', figure={}),
                        dcc.Store(id='store')
                    ]),
                    dbc.CardBody([
                        html.Tr([
                            html.Td(html.H6('REGION INFO: ', style={'width':'120px'})),
                            html.Td(html.H6(id='region_name', children='NA',
                                            style={'padding-left': '10px', 'width':'200px', 'height':'20px'})),
                            html.Td(dcc.Dropdown(id='regions-dpdn',
                                                 options=[],
                                                 multi=False,
                                                 value='All',
                                                 clearable=True,
                                                 style={'width':'100%', 'height':'20%',
                                                       'padding-left': '200px'}
                                                )
                                   )
                        ]),
                        dash_table.DataTable(id='datatable',
                                             data=[{}],
                                             columns=[{'name': '1', 'id': "1"},
                                                      {'name': '2', 'id': "2"},
                                                      {'name': '3', 'id': "3"},
                                                      {'name': '4', 'id': "4"}],
                                             style_cell_conditional=[
                                                 {'if': {'column_id': '1'},
                                                  'width': '25%', 'fontWeight':'bold'},
                                                 {'if': {'column_id': '2'},
                                                  'width': '17%'},
                                                 {'if': {'column_id': '3'},
                                                  'width': '25%', 'fontWeight':'bold'}
                                             ],
                                             style_cell={'fontSize':12, 'font-family':'sans-serif'},
                                             style_header = {'display': 'none'},
                                             style_table={'height': 173},
                                             style_as_list_view=True)
                    ])
                ], color="dark", outline=True)
            ], width=8),
        ], className='mb-2 mt-0')
    ])
], fluid=True)

# SMALL CARDS *****************************************************************************************************************************

@app.callback(
    Output('content-donors', 'children'),
    Output('content-dependent', 'children'),
    Output('content-ownrev', 'children'),
    Output('content-tax-to-fed', 'children'),
    Output('content-transfers', 'children'),
    Output('content-defsur', 'children'),
    Output('content-deficit', 'children'),
    Input('slct_year', 'value')
)
def update_totals(year):
    donors_num = int(cards_by_year.loc[year]['donor'])
    dependent_num = int(cards_by_year.loc[year]['dependent'])
    ownrev_sum = '$' + str(int(cards_by_year.loc[year]['reg_own_revenue_usd_bn'].round(0))) + 'B'
    tax_to_fed_sum = '$' + str(int(cards_by_year.loc[year]['tax_to_fed_usd_bn'].round(0))) + 'B'
    transfers_sum = '$' + str(int(cards_by_year.loc[year]['transfers_to_reg_usd_bn'].round(0))) + 'B'
    ds = int(cards_by_year.loc[year]['deficit_usd_bn'].round(0))
    if ds >= 0:
        defsur = 'Cumulative Surplus'
        deficit_sum = '${}B'.format(int(cards_by_year.loc[year]['deficit_usd_bn'].round(0)))
    else:
        defsur = 'Cumulative Deficit'
        deficit_sum = '-${}B'.format(int(abs(cards_by_year.loc[year]['deficit_usd_bn'].round(0))))
        
    return donors_num, dependent_num, ownrev_sum, tax_to_fed_sum, transfers_sum, defsur, deficit_sum

# TREEMAP *********************************************************************************************************************************

@app.callback(
    Output('treemap', 'figure'),
    Input('slct_year', 'value')
)

def update_treemap(year):
    tr_regions = treemap_data.copy()
    
    colorscale=[
        [0, "#209bd0"],
        [0.125, "#209bd0"],
        [0.125, "#67a1a3"],
        [0.250, "#67a1a3"],
        [0.250, "#aba778"],
        [0.375, "#aba778"],
        [0.375, "#f0ad4d"],
        [0.500, "#f0ad4d"],
        [0.500, "#eb974d"],
        [0.625, "#eb974d"],
        [0.625, "#e5804e"],
        [0.750, "#e5804e"],
        [0.750, "#e06a4e"],
        [0.875, "#e06a4e"],
        [0.875, "#da534f"],
        [1.000, "#da534f"]
    ]
    
    fig_treemap = px.treemap(treemap_data[treemap_data['year'] == year],
                             path=[px.Constant("Russia"), 'big_class', 'region_eng'],
                             values='flow_to_fed_usd_abs',
                             color='income_usd_per_cap',
                             custom_data=['region_eng',
                                          'reg_own_revenue_usd',
                                          'tax_to_fed_usd',
                                          'transfers_to_reg_usd',
                                          'balance_type',
                                          'flow_to_fed_usd_abs',
                                          'income_usd_per_cap',
                                          'population'],
                             color_continuous_scale=colorscale,
                             range_color=[0,2000],
                             height=250)
    fig_treemap.update_layout(margin = dict(t=0, l=0, r=0, b=0),
                              coloraxis_colorbar=dict(
                                  title=dict(text='MONTHLY<br>INCOME<br>PER CAPITA', font=dict(size=9)),
                                  tickvals=[250, 500, 750, 1000, 1250, 1500, 1750],
                                  ticktext=["$250", "$500", "$750", "$1000", "$1250", "$1500", "$1750"],
                                  tickfont=dict(size=9),
                                  thicknessmode="pixels", thickness=20,
                                  lenmode="pixels", len=265, ticks="outside")
                             )
    # counting the data for the parent markers
    for i, v in enumerate(fig_treemap.data[0].customdata):
        n=0
        dependent_indices = []
        donor_indices = []
        for x in fig_treemap.data[0].customdata[:, 4][:-3]:
            if x == 'Aid':
                dependent_indices.append(n)
            else:
                donor_indices.append(n)
            n+=1
            
        if fig_treemap.data[0].customdata[i, 0] == fig_treemap.data[0].customdata[-3, 0]:
            v[0] = 'Absorbing Regions'
            v[1] = sum(fig_treemap.data[0].customdata[dependent_indices, 1]) # total Dependent income
            v[2] = sum(fig_treemap.data[0].customdata[dependent_indices, 2]) # total Dependent tax
            v[3] = sum(fig_treemap.data[0].customdata[dependent_indices, 3]) # total Dependent transfers
            v[4] = 'Aid'
            v[5] = abs(sum(fig_treemap.data[0].customdata[dependent_indices, 3]) - sum(fig_treemap.data[0].customdata[dependent_indices, 2])) # total Dependent balance
            v[6] = fig_treemap.data[0].customdata[dependent_indices, 6].mean()
            fig_treemap.data[0].marker.colors[-3] = fig_treemap.data[0].customdata[dependent_indices, 6].mean()
            v[7] = sum(fig_treemap.data[0].customdata[dependent_indices, 7]) 
            
        if fig_treemap.data[0].customdata[i, 0] == fig_treemap.data[0].customdata[-2, 0]:
            v[0] = 'Donating Regions'
            v[1] = sum(fig_treemap.data[0].customdata[donor_indices, 1]) # total Donor income
            v[2] = sum(fig_treemap.data[0].customdata[donor_indices, 2]) # total Donor tax
            v[3] = sum(fig_treemap.data[0].customdata[donor_indices, 3]) # total Donor transfers
            v[4] = 'Donation'
            v[5] = abs(sum(fig_treemap.data[0].customdata[donor_indices, 3]) - sum(fig_treemap.data[0].customdata[donor_indices, 2])) # total Donor balance
            v[6] = fig_treemap.data[0].customdata[donor_indices, 6].mean()
            fig_treemap.data[0].marker.colors[-2] = fig_treemap.data[0].customdata[donor_indices, 6].mean()
            v[7] = sum(fig_treemap.data[0].customdata[donor_indices, 7])
            
        if fig_treemap.data[0].customdata[i, 0] == fig_treemap.data[0].customdata[-1, 0]:
            v[0] = 'All Regions'
            v[1] = sum(fig_treemap.data[0].customdata[:, 1][:-3]) # total Russia income
            v[2] = sum(fig_treemap.data[0].customdata[:, 2][:-3]) # total Russia tax
            v[3] = sum(fig_treemap.data[0].customdata[:, 3][:-3]) # total Russia transfers
            v[5] = abs(sum(fig_treemap.data[0].customdata[:, 3][:-3]) - sum(fig_treemap.data[0].customdata[:, 2][:-3])) # total Russia balance
            if sum(fig_treemap.data[0].customdata[:, 3][:-3]) - sum(fig_treemap.data[0].customdata[:, 2][:-3]) > 0:
                v[4] = 'Aid'
            else:
                v[4] = 'Donation'
            v[6] = fig_treemap.data[0].customdata[:, 6][:-3].mean()
            fig_treemap.data[0].marker.colors[-1] = fig_treemap.data[0].customdata[:, 6][:-3].mean()
            v[7] = sum(fig_treemap.data[0].customdata[:, 7][:-3])
    
    # hover cards design
    fig_treemap.update_traces(hovertemplate='<b>%{customdata[0]}</b><br><br>\
    Earned For Own Needs: <b>%{customdata[1]:$,.0f}M</b><br>\
    Donated To The Center: <b>%{customdata[2]:$,.0f}M</b><br>\
    Got From The Center: <b>%{customdata[3]:$,.0f}M</b><br><br>\
    Net %{customdata[4]}: <b>%{customdata[5]:$,.0f}M</b><br><br>\
    Population: <b>%{customdata[7]:,}</b><br>\
    Monthly Income Per Capita: <b>%{customdata[6]:$,.0f}</b>')
    
    return fig_treemap

# BAR PLOTS *******************************************************************************************************************************

@app.callback(
    Output('bar-chart', 'figure'),
    Input('slct_year', 'value'),
    Input('radios', 'value')
)
def update_bar(year, button):
    donors = top_donors.copy()
    takers = top_takers.copy()
    earning = top_earning.copy()
    deficits = top_deficits.copy()

    if button == 1:
        fig_bar = px.bar(donors.loc[year], x='tax_to_fed_usd', y='region_eng', orientation='h', range_x = [0, 62])
        x = donors.loc[year]['tax_to_fed_usd']
        y = donors.loc[year]['region_eng']
        fig_bar.update_traces(marker_color='#209bd0', marker_line=dict(color='#18749c', width=1),
                              hovertemplate='<b>%{x:$.1f}B</b>')
    if button == 2:
        fig_bar = px.bar(takers.loc[year], x='transfers_to_reg_usd', y='region_eng', orientation='h', range_x = [0, 3.5])
        x = takers.loc[year]['transfers_to_reg_usd']
        y = takers.loc[year]['region_eng']
        fig_bar.update_traces(marker_color='#f0ad4d', marker_line=dict(color='#db8912', width=1),
                          hovertemplate='<b>%{x:$.1f}B</b>')
    if button == 3:
        fig_bar = px.bar(earning.loc[year], x='reg_own_revenue_usd', y='region_eng', orientation='h', range_x = [0, 55])
        x = earning.loc[year]['reg_own_revenue_usd']
        y = earning.loc[year]['region_eng']
        fig_bar.update_traces(marker_color='#e5804e', marker_line=dict(color='#c9561d', width=1),
                          hovertemplate='<b>%{x:$.1f}B</b>')
    if button == 4:
        fig_bar = px.bar(deficits.loc[year], x='deficit_usd', y='region_eng', orientation='h', range_x = [0, 5.6])
        x = deficits.loc[year]['deficit_usd']
        y = deficits.loc[year]['region_eng']
        fig_bar.update_traces(marker_color='#da534f', marker_line=dict(color='#b82b27', width=1),
                              hovertemplate='<b>%{x:$.1f}B</b>')
        
    annotations = []
    for yd, xd in zip(y, x):
        if button == 1:
            annotations.append(dict(xref='x1', yref='y1', y=yd, x=xd + 8, text='$' + str(xd) + 'B', align='left',
                                    font=dict(size=11, color='#18749c'), showarrow=False))

        if button == 2:
            annotations.append(dict(xref='x1', yref='y1', y=yd, x=xd + 0.45, text='$' + str(xd) + 'B',
                                    font=dict(size=11, color='#db8912'), showarrow=False))
        if button == 3:
            annotations.append(dict(xref='x1', yref='y1', y=yd, x=xd + 7, text='$' + str(xd) + 'B', align='left',
                                    font=dict(size=11, color='#c9561d'), showarrow=False))
            
        if button == 4:
            annotations.append(dict(xref='x1', yref='y1', y=yd, x=xd + 0.7, text='$' + str(xd) + 'B',
                                    font=dict(size=11, color='#b82b27'), showarrow=False))
    
    fig_bar.update_layout(
        height=467,
        yaxis=dict(showgrid=False, showline=False, showticklabels=True, ticklen=0, tickfont = dict(size=10)),
        xaxis=dict(zeroline=False, showline=False, showticklabels=False, showgrid=True, ticklen=0, tickfont = dict(size=10)),
        margin=dict(l=140, r=10, t=10, b=2),
        paper_bgcolor='#f7f9fa',
        plot_bgcolor='#f7f9fa',
        annotations=annotations)
        
    for axis in fig_bar.layout:
        if type(fig_bar.layout[axis]) == go.layout.YAxis:
            fig_bar.layout[axis].title.text = ''
            fig_bar.layout[axis].title.standoff = 0
        if type(fig_bar.layout[axis]) == go.layout.XAxis:
            fig_bar.layout[axis].title.text = ''
            fig_bar.layout[axis].title.standoff = 0
    
    fig_bar.update_yaxes(tickangle=0)
    
    return fig_bar

# SCATTER PLOT ****************************************************************************************************************************

@app.callback(
    Output('scatter-chart', 'figure'),
    Output('store', 'data'),
    Input('slct_year', 'value'),
    Input('regions-dpdn', 'value')
)

def update_scatter(year, region):
    sc_regions = scatter_regions.copy()
    sc_regions['region_eng'] = sc_regions['region_eng'].str.title()
    dff = sc_regions[(sc_regions['year'] == year)].dropna().reset_index(drop=True)
    
    colorscale=[
        [0, "#209bd0"],
        [0.125, "#209bd0"],
        [0.125, "#67a1a3"],
        [0.250, "#67a1a3"],
        [0.250, "#aba778"],
        [0.375, "#aba778"],
        [0.375, "#f0ad4d"],
        [0.500, "#f0ad4d"],
        [0.500, "#eb974d"],
        [0.625, "#eb974d"],
        [0.625, "#e5804e"],
        [0.750, "#e5804e"],
        [0.750, "#e06a4e"],
        [0.875, "#e06a4e"],
        [0.875, "#da534f"],
        [1.000, "#da534f"]
    ]
    
    fig_scatter = px.scatter(data_frame=dff,
                             x='reg_fed_flow_vs_rev',
                             y='deficit_vs_rev',
                             size='population',
                             color='income_per_cap_usd',
                             hover_name = 'region_eng',
                             opacity=0.9,
                             range_x = [-1250,700],
                             range_y = [-60, 60],
                             height=300,
                             custom_data=['region_eng'],
                             color_continuous_scale = colorscale,
                             range_color=[0,2000]
                            )
    
    x = dff['reg_fed_flow_vs_rev']
    y = dff['deficit_vs_rev']
    
    annotations = []
    annotations.append(dict(xref='x1', yref='y1', x=-1090, y=5, text='<b>SURPLUS</b>', align='right',
                            font=dict(size=15, color='#cdd8db'), showarrow=False))
    annotations.append(dict(xref='x1', yref='y1', x=-1100, y=-5, text='<b>DEFICIT</b>', align='right',
                            font=dict(size=15, color='#cdd8db'), showarrow=False))
    annotations.append(dict(xref='x1', yref='y1', x=-450, y=55, text='<b>TO THE FEDERAL CENTER</b>', align='right',
                            font=dict(size=15, color='#cdd8db'), showarrow=False))
    annotations.append(dict(xref='x1', yref='y1', x=300, y=55, text='<b>TO THE REGION</b>', align='left',
                            font=dict(size=15, color='#cdd8db'), showarrow=False))
    
    fig_scatter.update_layout(margin=dict(l=0, r=0, t=30, b=20), clickmode='event+select',
                              coloraxis_colorbar=dict(tickvals=[250, 500, 750, 1000, 1250, 1500, 1750],
                                                      ticktext=["$250", "$500", "$750", "$1000", "$1250", "$1500", "$1750"],
                                                      tickfont=dict(size=9),
                                                      title=dict(text='MONTHLY<br>INCOME<br>PER CAPITA', font=dict(size=9)),
                                                      thicknessmode="pixels", thickness=20, lenmode="pixels", len=265,
                                                      ticks="outside", dtick=3),
                              xaxis = dict(tickfont = dict(size=9), ticksuffix='%',
                                           title_text="<b>«───────────────────────── TO THE FEDERAL BUDGET TO THE REGION ────»</b>",
                                           titlefont = dict(size = 9), zeroline=True, zerolinewidth=3, zerolinecolor='white'),
                              yaxis = dict(tickfont = dict(size=9), ticksuffix='%',
                                           title_text="<b>«───────── DEFICIT      SURPLUS ────────»</b>",
                                           titlefont = dict(size = 9), zeroline=True, zerolinewidth=3, zerolinecolor='white'),
                              paper_bgcolor='#f7f9fa', plot_bgcolor='#f7f9fa',
                              annotations=annotations)
    
    if region == 'All' or region is None:
        selectedpoints=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,
                        37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,
                        71,72,73,74,75,76,77,78,79,80,81,82,83,84]
    else:
        selectedpoints=[dff[dff['region_eng'] == region].index[0]]
        
    fig_scatter.update_traces(hovertemplate='<b>%{customdata[0]}</b> <br>\
    Net Cash Flow with the Center: <b>%{x}</b> of revenue <br>\
    Surplus/Deficit(-): <b>%{y}</b> of revenue <br>\
    Population: <b>%{marker.size:,}</b> <br>\
    Monthly Income Per Capita: <b>%{marker.color:$.0f}</b>', selectedpoints=selectedpoints
                             )
    
    for axis in fig_scatter.layout:
        if type(fig_scatter.layout[axis]) == go.layout.YAxis:
            fig_scatter.layout[axis].title.text = ''
            fig_scatter.layout[axis].title.standoff = 0
        if type(fig_scatter.layout[axis]) == go.layout.XAxis:
            fig_scatter.layout[axis].title.text = ''
            fig_scatter.layout[axis].title.standoff = 0
    
    return fig_scatter, region

# REGIONS DROPDOWN ************************************************************************************************************************

# populate the options of counties dropdown based on year dropdown
@app.callback(
    Output('regions-dpdn', 'options'),
    Input('slct_year', 'value')
)
def select_region_options(year):
    sc_regions = scatter_regions.copy()
    sc_regions['region_eng'] = sc_regions['region_eng'].str.title()
    
    dff = sc_regions[(sc_regions['year'] == year)].dropna().reset_index(drop=True)   
    dff_list = [{'label':c, 'value':c} for c in dff.region_eng.str.title().unique()]
    dff_list.append(dict({'label':'All', 'value':'All'}))
    return dff_list

# populate initial values of regions dropdown
@app.callback(
    Output('regions-dpdn', 'value'),
    Input('regions-dpdn', 'options')
)

def set_region_value(available_options):
    return available_options[-1]['value']

# TABLE ***********************************************************************************************************************************

@app.callback(
    Output('region_name', 'children'),
    Output('datatable', 'data'),
    Input('slct_year', 'value'),
    Input('store', 'data')
)

def update_table(year, chosen_scatter_region):

    rgnl_cards = regional_cards.copy()
    
    rgnl_cards['key_revenue'] = rgnl_cards['key_revenue'].replace('corporate income tax full', 'corporate income tax',
                                                                  regex=True)
    rgnl_cards['key_tax_to_fed'] = rgnl_cards['key_tax_to_fed'].replace('corporate income tax full', 'corporate income tax',
                                                                        regex=True)
    
    rgnl_cards['region_eng'] = rgnl_cards['region_eng'].str.title()
    rgnl_cards['key_revenue'] = rgnl_cards['key_revenue'].str.title()
    rgnl_cards['key_tax_to_fed'] = rgnl_cards['key_tax_to_fed'].str.title()
    rgnl_cards['key_spending'] = rgnl_cards['key_spending'].str.title()
    
    if chosen_scatter_region in ('All', None):
        region = 'Adygea'
    else:
        region = chosen_scatter_region

    region_name = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[1].str.title()    
    
    own_rev = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[2, 0])) + 'M'
    tax_to_fed = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[3, 0])) + 'M'
    transfers = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[4, 0])) + 'M'
    spending = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[5, 0])) + 'M'
    deficit = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[6, 0])) + 'M'
    population = '{:,}'.format(int(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[7, 0]))
    incpercap = '$' + str(int(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[8, 0]))
    
    key_tax_to_fed = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[10, 0]
    key_tax_to_fed_amount = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[11, 0])) + 'M'
    key_revenue = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[12, 0]
    key_revenue_amount = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[13, 0])) + 'M'
    key_spending = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[14, 0]
    key_spending_amount = '$' + str('{:,}'.format(rgnl_cards[(rgnl_cards['year'] == year) & (
        rgnl_cards['region_eng'] == region)].T.iloc[15, 0])) + 'M'
    
    dos = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[6, 0]
    if dos >= 0:
        deforsur = 'Surplus'
        deficit = '${}M'.format(round(dos, 1))
    else:
        deforsur = 'Deficit'
        deficit = '-${}M'.format(abs(round(dos, 1)))
    
    ttf = rgnl_cards[(rgnl_cards['year'] == year) & (rgnl_cards['region_eng'] == region)].T.iloc[3, 0]
    if ttf >= 0:
        tax_to_fed = '${}M'.format(round(ttf, 1))
    else:
        tax_to_fed = '-${}M'.format(abs(round(ttf, 1)))    
    
    data = OrderedDict(
        [
            ('1', ["Own Revenue", "Tax To Federal Center", "Spending", "Incoming Transfers", deforsur]),
            ('2', [own_rev, tax_to_fed, spending, transfers, deficit]),
            ('3', ["Key Own Revenue", "Key Tax To Federal Center", "Key Spending", "Population", "Monthly Income Per Capita"]),
            ('4', ['{} ({})'.format(key_revenue, key_revenue_amount), '{} ({})'.format(key_tax_to_fed, key_tax_to_fed_amount),
                   '{} ({})'.format(key_spending, key_spending_amount), population, incpercap]),
        ]
    )
    
    df = pd.DataFrame(data)
    return region, df.to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)