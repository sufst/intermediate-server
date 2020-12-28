"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2020 Nathan Rowley-Smith

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import annotations

from typing import Callable
from typing import Optional
from typing import Tuple
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects
import plotly.express as px
import numpy
import math

_SW_VERSION = 10000


class Shadow:
    _values = [0]

    def __init__(self) -> None:
        pass

    def put_values(self, values: list) -> None:
        self._values.extend(values)

    def get_values(self, n: int) -> list:
        return self._values[-n:]


_external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
_app = dash.Dash(__name__, external_stylesheets=_external_stylesheets)
_shadow = Shadow()


def build_header() -> html.Div:
    return html.Div([html.H3(f"GUI Emulator")])


def build_footer() -> html.Div:
    return html.Div([html.H6(f"GUI Emulator build {_SW_VERSION}. Copyright (C) 2020 Nathan Rowley-Smith.\n" +
                             "This program comes with ABSOLUTELY NO WARRANTY;\n" +
                             "This is free software, and you are welcome to redistribute it")])


def build_interval(component_id: str, interval_ms: int) -> html.Div:
    interval = dcc.Interval(id=component_id, interval=interval_ms, n_intervals=0, disabled=False)

    return html.Div([interval])


def get_line_graph(x: list, y: list, title: str, yaxis_range: Optional[list] = None) \
        -> plotly.graph_objects.Figure:
    return plotly.graph_objects.Figure(data=plotly.graph_objects.Scatter(x=x, y=y),
                                       layout_yaxis_range=yaxis_range, layout_title=title)


def build_line_graph(component_id: str, initial_x: list, initial_y: list, title: str,
                     yaxis_range: Optional[list] = None) -> html.Div:
    figure = get_line_graph(initial_x, initial_y, title, yaxis_range)

    return html.Div([(dcc.Graph(id=component_id, figure=figure))])


def boot_strap():
    _app.layout = html.Div([
        build_header(),
        build_interval("interval-1", 200),
        build_line_graph("graph-1", [0], [0], "Example line graph"),
        build_footer()
    ])


@_app.callback(
    Output(component_id='graph-1', component_property="figure"),
    Input(component_id='interval-1', component_property='n_intervals')
)
def update_graph(n_intervals: int) -> plotly.graph_objects.Figure:
    _shadow.put_values([_shadow.get_values(1)[0] + 1])
    y = [math.sin(math.radians(i*10)) for i in _shadow.get_values(40)]

    x = list(range(-len(y), 0))

    return get_line_graph(x, y, "Example line graph", [-1, 1])


if __name__ == '__main__':
    print(f"GUI Emulator build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    boot_strap()
    _app.run_server(debug=True)
