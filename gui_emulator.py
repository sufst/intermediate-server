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

import math
from typing import Optional
from typing import List
from typing import Dict
from typing import Tuple
import asyncio
import protocol
import protocol_factory
import common
import threading
import argparse

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
import plotly.graph_objects
import plotly.subplots
from dash.dependencies import Input, Output

_SW_VERSION = 10000
_CLIENT_NAME = "GUI-EMULATOR"

_DROPDOWN_MENU_OPTIONS = [
    {"label": "RPM", "value": protocol.RPM},
    {"label": "TPS", "value": protocol.TPS_PERC},
    {"label": "Water Temp C", "value": protocol.WATER_TEMP_C},
    {"label": "Speed KPH", "value": protocol.SPEED_KPH}
]


class Shadow:
    _rpm = [0]
    _tps = [0]
    _water_temp = [0]
    _speed = [0]
    counter = 0

    def __init__(self) -> None:
        pass

    def put_rpm(self, values: list) -> None:
        self._rpm.extend(values)

    def get_rpm(self, n: int) -> list:
        return self._rpm[-n:]

    def put_tps(self, values: list) -> None:
        self._tps.extend(values)

    def get_tps(self, n: int) -> list:
        return self._tps[-n:]

    def put_water_temp(self, values: list) -> None:
        self._water_temp.extend(values)

    def get_water_temp(self, n: int) -> list:
        return self._water_temp[-n:]

    def put_speed(self, values: list) -> None:
        self._speed.extend(values)

    def get_speed(self, n: int) -> list:
        return self._speed[-n:]


class Client(threading.Thread):
    def __init__(self, client_name: str, ip: str, port: int, verbose: str):
        super().__init__()
        self._logger = common.get_logger(client_name, verbose)
        self._client_name = client_name
        self._ip = ip
        self._port = port
        self._verbose = verbose

        self._event_loop = asyncio.new_event_loop()
        self._on_con_lost = None

        self._protocol_callbacks = protocol.ProtocolCallbacks()
        self._protocol_callbacks.on_connection = self._on_connection
        self._protocol_callbacks.on_lost = self._on_lost
        self._protocol_callbacks.on_aipdu = self._on_aipdu
        self._protocol_callbacks.on_acpdu = self._on_acpdu
        self._protocol_callbacks.on_aapdu = self._on_aapdu
        self._protocol_callbacks.on_adpdu = self._on_adpdu
        self._protocol_callbacks.on_appdu = self._on_appdu
        self._protocol_callbacks.on_aspdu = self._on_aspdu
        self._protocol_callbacks.on_ampdu = self._on_ampdu

    def run(self):
        asyncio.set_event_loop(self._event_loop)
        asyncio.run(self._run())

    async def _run(self):
        """
        The asyncio event loop for the client.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()
        self._on_con_lost = self._event_loop.create_future()

        self._logger.info(f"Creating client {self._ip}:{self._port}")

        self._logger.info(f"Creating Protocol for host: {self._ip}:{self._port}")
        self._protocol = protocol.Protocol(ip=self._ip, port=self._port, callbacks=self._protocol_callbacks,
                                           protocol_type=protocol.SOCKET, event_loop=self._event_loop,
                                           verbose=self._verbose, pdu_format=protocol_factory.JSON)
        self._protocol.run()

        self._logger.info("Client created")

        try:
            await self._on_con_lost
        finally:
            pass

    def _on_connection(self, factory: protocol_factory.ProtocolFactoryBase) -> None:
        """
        Invoked when a factory has made a new connection.
        :param factory: The factory that has a new connection.
        """
        self._logger.info(f"Handling connection from factory {factory.__hash__()}")
        self._protocol.write_aipdu(factory, protocol.GUI, _SW_VERSION, _CLIENT_NAME)

    def _on_lost(self, factory: protocol_factory.ProtocolFactoryBase, exc: Optional[Exception]) -> None:
        """
        Invoked when a factory has lost its connection.
        :param factory: The factory that has lost its connection.
        :param exc:     Any error that caused the lost.
        """
        self._logger.info(f"Handling lost from factory {factory.__hash__()}")
        self._on_con_lost.set_result(False)

    def _on_aipdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  client_type: int, sw_ver: int, client_name: str) -> None:
        """
        Invoked when a factory has received a AIPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AIPDU from factory {factory.__hash__()}")

    def _on_acpdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader, rpm: int,
                  water_temp_c: int, tps_perc: int, battery_mv: int, external_5v_mv: int, fuel_flow: int,
                  lambda_value: int, speed_kph: int) -> None:
        """
        Invoked when a factory has received a ACPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ACPDU from factory {factory.__hash__()}")
        _shadow.put_values([rpm])

    def _on_aapdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  evo_scanner1: int, evo_scanner2: int, evo_scanner3: int, evo_scanner4: int, evo_scanner5: int,
                  evo_scanner6: int, evo_scanner7: int) -> None:
        """
        Invoked when a factory has received a AAPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AAPDU from factory {factory.__hash__()}")

    def _on_adpdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader, ecu_status: int,
                  engine_status: int, battery_status: int, car_logging_status: int) -> None:
        """
        Invoked when a factory has received a ADPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ADPDU from factory {factory.__hash__()}")

    def _on_appdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  injection_time: int, injection_duty_cycle: int, lambda_pid_adjust: int, lambda_pid_target: int,
                  advance: int) -> None:
        """
        Invoked when a factory has received a APPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling APPDU from factory {factory.__hash__()}")

    def _on_aspdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  ride_height_fl_cm: int, ride_height_fr_cm: int, ride_height_flw_cm: int, ride_height_rear_cm: int) \
            -> None:
        """
        Invoked when a factory has received a ASPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ASPDU from factory {factory.__hash__()}")

    def _on_ampdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  lap_timer_s: int, accel_fl_x_mg: int, accel_fl_y_mg: int, accel_fl_z_mg: int) -> None:
        """
        Invoked when a factory has received a AMPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AMPDU from factory {factory.__hash__()}")


_external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
_app = dash.Dash(__name__, external_stylesheets=_external_stylesheets)
_shadow = Shadow()


def build_header() -> html.Div:
    return html.Div([html.H3(f"GUI Emulator")])


def build_footer() -> html.Div:
    return html.Div([html.H6(f"GUI Emulator build {_SW_VERSION}. Copyright (C) 2020 Nathan Rowley-Smith.\n" +
                             "This program comes with ABSOLUTELY NO WARRANTY;\n" +
                             "This is free software, and you are welcome to redistribute it")])


def build_interval_div(component_id: str, interval_ms: int) -> html.Div:
    interval = dcc.Interval(id=component_id, interval=interval_ms, n_intervals=0, disabled=False)

    return html.Div([interval])


def get_line_graph_figure(x: list, y: list, title: str, yaxis_range: Optional[list] = None) \
        -> plotly.graph_objects.Figure:
    return plotly.graph_objects.Figure(data=plotly.graph_objects.Scatter(x=x, y=y),
                                       layout_yaxis_range=yaxis_range, layout_title=title)


def get_line_graph(x: list, y: list) -> plotly.graph_objects.Scatter:
    return plotly.graph_objects.Scatter(x=x, y=y)


def build_line_graph_div(component_id: str, initial_x: list, initial_y: list, title: str,
                         yaxis_range: Optional[list] = None) -> html.Div:
    figure = get_line_graph_figure(initial_x, initial_y, title, yaxis_range)

    return html.Div([(dcc.Graph(id=component_id, figure=figure))])


def get_indicator(value: int, title: str) -> plotly.graph_objects.Figure:
    return plotly.graph_objects.Figure(data=plotly.graph_objects.Indicator(mode="number", value=value, title=title),
                                       layout_height=400)


def build_indicator_div(component_id: str, value: int, title: str, class_name: Optional[str] = Component.UNDEFINED) \
        -> html.Div:
    figure = get_indicator(value, title)

    return html.Div([(dcc.Graph(id=component_id, figure=figure))], className=class_name)


def get_gauge(value: int, title: str, y_range: List[min, max]) -> plotly.graph_objects.Figure:
    return plotly.graph_objects.Figure(data=plotly.graph_objects.Indicator(
        mode="gauge+number", value=value,
        title=title, gauge={"axis": {"range": y_range}}))


def build_gauge_div(component_id: str, value: int, title: str, y_range: List[min, max],
                    class_name: Optional[str] = Component.UNDEFINED) \
        -> html.Div:
    figure = get_gauge(value, title, y_range)

    return html.Div([(dcc.Graph(id=component_id, figure=figure))], className=class_name)


def build_dropdown_multi_menu_div(component_id: str, options: List[Dict[str: str]], default: str) -> html.Div:
    return html.Div([
        dcc.Dropdown(id=component_id, options=options, value=[default], multi=True)
    ])


def build_empty_subplots_div(component_id: str) -> html.Div:
    return html.Div([
        dcc.Graph(id=component_id)
    ])


def build_core_gauges_row_div() -> html.Div:
    return html.Div([
        build_gauge_div("RPM-gau", 0, "RPM", [0, 10000], class_name="three columns"),
        build_gauge_div("TPS-gau", 0, "TPS %", [0, 100], class_name="three columns"),
        build_gauge_div("Water-gau", 0, "Water C", [0, 160], class_name="three columns"),
        build_gauge_div("Speed-gau", 0, "Speed KPH", [0, 60], class_name="three columns"),
    ], className="row")


def build_acpdu_div() -> html.Div:
    return html.Div([
        build_core_gauges_row_div()
    ])


def build_select_graph_div() -> html.Div:
    return html.Div([
        build_dropdown_multi_menu_div("graphs-drop", _DROPDOWN_MENU_OPTIONS, protocol.RPM)
    ])


def boot_strap(ip: str, port: int, verbose: str) -> None:
    client = Client(_CLIENT_NAME, ip, port, verbose)
    client.start()

    _app.layout = html.Div([
        build_header(),
        build_interval_div("interval-1", 100),
        build_acpdu_div(),
        build_select_graph_div(),
        build_empty_subplots_div("multi-graphs"),
        build_footer()
    ])


@_app.callback(
    Output(component_id='RPM-gau', component_property="figure"),
    Output(component_id='TPS-gau', component_property="figure"),
    Output(component_id='Water-gau', component_property="figure"),
    Output(component_id='Speed-gau', component_property="figure"),
    Input(component_id='interval-1', component_property='n_intervals')
)
def update_gauges(n_intervals: int) -> Tuple[plotly.graph_objects.Figure, plotly.graph_objects.Figure,
                                             plotly.graph_objects.Figure, plotly.graph_objects.Figure]:
    _shadow.put_rpm([5000 * math.sin(math.radians(_shadow.counter)) + 5000])
    _shadow.put_tps([50 * math.sin(math.radians(_shadow.counter)) + 50])
    _shadow.put_water_temp([80 * math.sin(math.radians(_shadow.counter)) + 80])
    _shadow.put_speed([30 * math.sin(math.radians(_shadow.counter)) + 30])
    _shadow.counter += 1

    rpm = get_gauge(_shadow.get_rpm(1)[0], "RPM", [0, 10000])
    tps = get_gauge(_shadow.get_tps(1)[0], "TPS %", [0, 100])
    water = get_gauge(_shadow.get_water_temp(1)[0], "Water C", [0, 160])
    speed = get_gauge(_shadow.get_speed(1)[0], "Speed KPH", [0, 60])

    return rpm, tps, water, speed


@_app.callback(
    Output(component_id='multi-graphs', component_property='figure'),
    Input(component_id='graphs-drop', component_property='value'),
    Input(component_id='interval-1', component_property='n_intervals')
)
def update_dropdown_multi(value: List, n_intervals: int) -> plotly.graph_objects.Figure:
    graphs = []
    titles = []

    if protocol.RPM in value:
        y = _shadow.get_rpm(40)
        x = list(range(-len(y), 0))
        graphs.append({"graph": get_line_graph(x, y), "ranges": [0, 10000]})
        titles.append("RPM")

    if protocol.WATER_TEMP_C in value:
        y = _shadow.get_water_temp(40)
        x = list(range(-len(y), 0))
        graphs.append({"graph": get_line_graph(x, y), "ranges": [0, 160]})
        titles.append("Water Temp C")

    figure = plotly.subplots.make_subplots(rows=len(value), cols=1, subplot_titles=tuple(titles))

    row = 1
    for graph in graphs:
        figure.add_trace(graph["graph"], row=row, col=1)
        figure.update_yaxes(range=graph["ranges"], row=row, col=1)
        row += 1

    figure.update_layout(height=500*len(value))
    return figure


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an intermediate server.")

    parser.add_argument("--port", type=int, default=19900, help="The port to host the server on.")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="The IP address to host the server on.")
    parser.add_argument("--verbose", type=str, default="WARN",
                        help="The verbose level of the server: DEBUG, INFO, WARN, ERROR")

    print(f"Car Emulator build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    boot_strap(args.ip, args.port, args.verbose)
    _app.run_server(debug=True)
