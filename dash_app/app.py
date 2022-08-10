import logging
from time import monotonic

import dash
import dash_bootstrap_components as dbc
import plotly
import plotly.graph_objects as go
from dash import dcc
from dash import html
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

from dash_app.db import DataSource
from utils.helpers import str_to_dt

logger = logging.getLogger(__name__)

GRAPH_ID = 'live-graph'
CONTAINER_ID = 'container'
DROPDOWN_ID = 'ticker_dropdown'
INTERVAL_ID = 'graph-update'
SLIDER_ID = 'slider'
STORE_ID = 'store'
BUTTON_ID = 'stream_button'

SLIDER_ON = 1
SLIDER_OFF = 0


class App:
    def __init__(self, *, name, update_interval, row_limit, db_config):
        self.name = name
        self.row_limit = row_limit
        self.update_interval = update_interval
        self.db = DataSource(**db_config)
        self.app = dash.Dash(
            self.name,
            suppress_callback_exceptions=True,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
        )
        self.x_cache = {}
        self.y_cache = {}
        self.ticker_map = {}
        self.last_update = {}
        self.slider_marks = None
        self.stop_stream = False
        # TODO move to shared cache
        self.interval_was_updated = None
        self.layout = lambda tickers: dbc.Container(
            [
                dbc.Card(
                    [
                        dbc.CardHeader('Select ticker'),
                        dbc.CardBody(
                            dcc.Dropdown(tickers, id=DROPDOWN_ID, multi=False),
                        ),
                    ],
                    style={'width': '100%'},
                    class_name='mt-3',
                ),
                dbc.Container(id=CONTAINER_ID),
                dcc.Store(id=STORE_ID)
            ]
        )

        self.graph = lambda ticker, slider_args, slider_value, marks: html.Div([
            dbc.Row(f'{ticker}', justify='center', class_name='mt-3'),
            dcc.Graph(id=GRAPH_ID, animate=True),
            dcc.Slider(*slider_args, value=slider_value, id=SLIDER_ID, marks=marks),
            dcc.Interval(id=INTERVAL_ID, interval=1000, n_intervals=0),
        ])

        self.callbacks = [
            (
                self.update_graph_scatter,
                (
                    Output(GRAPH_ID, 'figure'),
                    [
                        Input(INTERVAL_ID, 'n_intervals'),
                        State(DROPDOWN_ID, 'value'),
                        Input(GRAPH_ID, 'relayoutData'),
                        State(STORE_ID, 'data'),
                    ],

                )
            ),
            (
                self.select_ticker,
                (
                    Output(CONTAINER_ID, 'children'),
                    Input(DROPDOWN_ID, 'value'),
                ),

            ),
            (
                self.change_slider,
                (
                    Output(STORE_ID, 'data'),
                    Input(SLIDER_ID, 'value'),
                )
            )
        ]

    def update_graph_scatter(self, n_interval, current_ticker, relayout_data, store_data):
        is_stream = store_data and store_data.get('slider_state') == 1

        is_relayout_event = (
            relayout_data and (
                relayout_data.get('dragmode') or
                relayout_data.get('xaxis.autorange') or
                relayout_data.get('xaxis.showspikes')
            )
        )
        if not current_ticker:
            raise PreventUpdate

        if is_relayout_event and not is_stream:
            raise PreventUpdate

        if is_stream and self.interval_was_updated == n_interval:
            raise PreventUpdate

        start_x = end_x = start_y = end_y = None
        if relayout_data:
            if relayout_data.get('xaxis.range[0]'):
                start_x = str_to_dt(relayout_data['xaxis.range[0]'])
                end_x = str_to_dt(relayout_data['xaxis.range[1]'])
            elif relayout_data.get('xaxis.range'):
                start_x = str_to_dt(relayout_data['xaxis.range'][0])
                end_x = str_to_dt(relayout_data['xaxis.range'][1])

            if relayout_data.get('yaxis.range'):
                start_y = relayout_data['yaxis.range'][0]
                end_y = relayout_data['yaxis.range'][1]
            elif relayout_data.get('yaxis.range[0]'):
                start_y = relayout_data['yaxis.range[0]']
                end_y = relayout_data['yaxis.range[1]']

        ticker_id = self.ticker_map[current_ticker]

        t1 = monotonic()

        if start_x and end_x and not is_stream:
            rowset = self.db.get_data_by_range(ticker_id, start_x, end_x)
            logging.info(f'Load hist. data from DB {monotonic() - t1}sec.')
        else:
            rowset = self.db.get_last_data(ticker_id, limit=self.row_limit)
            logging.info(f'Load new data from DB {monotonic() - t1}sec.')

        if not rowset:
            raise PreventUpdate

        y, x = list(zip(*rowset))

        if is_stream or not (start_x and end_x):
            start_x = min(x)
            end_x = max(x)
            start_y = min(y)
            end_y = max(y)

        data = plotly.graph_objs.Scatter(
            x=x,
            y=y,
            name='Scatter',
            mode='lines'
        )
        self.interval_was_updated = n_interval
        return [
            {
                'data': [data],
                'layout': go.Layout(
                    xaxis=dict(range=[start_x, end_x]),
                    yaxis=dict(range=[start_y, end_y]),
                )
            },
        ]

    def select_ticker(self, ticker: str):
        if not ticker:
            raise PreventUpdate

        marks = {
            SLIDER_OFF: {'label': f'OFF'},
            SLIDER_ON: {'label': f'ON'},
        }

        return [self.graph(ticker, [SLIDER_OFF, SLIDER_ON, 1], SLIDER_ON, marks)]

    @staticmethod
    def change_slider(slider_value):
        print(f'Slider ON: {slider_value == SLIDER_ON}')
        return [{
            'slider_state': slider_value
        }]

    def run_server(self, *args, **kwargs):
        self.ticker_map = dict(self.db.get_tickers())
        self.app.layout = self.layout(list(self.ticker_map))

        for callback, callback_args in self.callbacks:
            self.app.callback(callback_args)(callback)

        self.app.run_server(*args, **kwargs)
