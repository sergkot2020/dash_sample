import random
import sys
from collections import deque, defaultdict
from dash_app.db import DataSource
import dash
import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
# from dash_app import  dbc
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

GRAPH_ID = 'live-graph'
CONTAINER_ID = 'container'
DROPDOWN_ID = 'ticker_dropdown'
INTERVAL_ID = 'graph-update'
SLIDER_ID = 'slider'


# TODO need remove
def utc_now():
    return datetime.now().replace(tzinfo=timezone.utc)


class App:
    def __init__(self, *, name, update_interval, db_config):
        self.name = name
        self.update_interval = update_interval
        self.db = DataSource(**db_config)
        self.app = dash.Dash(
            self.name,
            suppress_callback_exceptions=True,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
        )
        self.x_cache = defaultdict(deque)
        self.y_cache = defaultdict(deque)
        self.ticker_map = {}
        self.last_update = {}
        self.slider_range = None
        self.stop_stream = False
        self.current_ticker = None  # TODO port to client side
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
                dbc.Container(id=CONTAINER_ID)
            ]
        )

        self.graph = lambda ticker, slider_args, slider_value: html.Div([
            dbc.Row(f'{ticker}', justify='center', class_name='mt-3'),
            dcc.Graph(id=GRAPH_ID, animate=True),
            dcc.Slider(*slider_args, value=slider_value, id=SLIDER_ID),
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
                        State(SLIDER_ID, 'value')
                    ],

                )
            ),
            (
                self.select_ticker,
                (
                    Output(CONTAINER_ID, 'children'),
                    Input(DROPDOWN_ID, 'value'),
                )
            ),
        ]

    def move_slider(self, value):
        self.stop_stream = True
        if value == len(self.slider_range) - 1:
            self.stop_stream = False
        print(value)

    def update_graph_scatter(self, _, current_ticker, slider_value):
        is_not_end = slider_value < len(self.slider_range) - 1

        if not current_ticker:
            raise PreventUpdate

        last_date = self.last_update.get(current_ticker)
        ticker_id = self.ticker_map[current_ticker]

        if is_not_end:
            start = self.slider_range[slider_value]
            end = start + timedelta(minutes=1)
            rowset = self.db.get_data_by_range(ticker_id, start, end)
            self.last_update[current_ticker] = None
        elif not last_date:
            rowset = self.db.get_last_data(ticker_id, limit=60)
            _, last_ts = rowset[-1]
            self.last_update[current_ticker] = last_ts  # todo тоже не надо делать глобальный
        else:
            rowset = self.db.get_update(ticker_id, last_date)
            if rowset:
                _, last_ts = rowset[-1]
                self.last_update[current_ticker] = last_ts

        if not rowset:
            raise PreventUpdate

        y, x = list(zip(*rowset))

        if not self.x_cache.get(current_ticker):  # TODO перенести создание очередей в ИНИТ метод
            self.x_cache[current_ticker] = deque(maxlen=60)
        if not self.y_cache.get(current_ticker):
            self.y_cache[current_ticker] = deque(maxlen=60)

        self.x_cache[current_ticker].extend(x)
        self.y_cache[current_ticker].extend(y)
        x = list(self.x_cache[current_ticker])
        y = list(self.y_cache[current_ticker])

        data = plotly.graph_objs.Scatter(
            x=x,
            y=y,
            name='Scatter',
            mode='lines+markers'
        )
        return [{
            'data': [data],
            'layout': go.Layout(
                xaxis=dict(range=[min(x), max(x)]),
                yaxis=dict(range=[min(y), max(y)]),
            )
        }]

    def select_ticker(self, ticker):
        if not ticker:
            raise PreventUpdate

        self.slider_range = self.db.get_date_range(self.ticker_map[ticker])
        end = len(self.slider_range) - 1
        return [self.graph(ticker, [0, end, 1], end)]

    def run_server(self, *args, **kwargs):
        self.ticker_map = dict(self.db.get_tickers())
        self.app.layout = self.layout(list(self.ticker_map))

        for callback, callback_args in self.callbacks:
            self.app.callback(callback_args)(callback)

        print('================')
        print(sys.path)
        self.app.run_server(*args, **kwargs)
