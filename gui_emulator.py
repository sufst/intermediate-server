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
import asyncio
import protocol
import protocol_factory
import common
import threading
import argparse

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects
from dash.dependencies import Input, Output

_SW_VERSION = 10000
_CLIENT_NAME = "GUI-EMULATOR"


class Shadow:
    _values = [0]

    def __init__(self) -> None:
        pass

    def put_values(self, values: list) -> None:
        self._values.extend(values)

    def get_values(self, n: int) -> list:
        return self._values[-n:]


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


def boot_strap(ip: str, port: int, verbose: str) -> None:
    client = Client(_CLIENT_NAME, ip, port, verbose)
    client.start()

    _app.layout = html.Div([
        build_header(),
        build_interval("interval-1", 100),
        build_line_graph("graph-1", [0], [0], "Example line graph"),
        build_footer()
    ])


@_app.callback(
    Output(component_id='graph-1', component_property="figure"),
    Input(component_id='interval-1', component_property='n_intervals')
)
def update_graph(n_intervals: int) -> plotly.graph_objects.Figure:
    y = _shadow.get_values(40)
    x = list(range(-len(y), 0))

    return get_line_graph(x, y, "Example line graph", [0, 10000])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an intermediate server.")

    parser.add_argument("--port", type=int, default=19900, help="The port to host the server on.")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="The IP address to host the server on.")
    parser.add_argument("--verbose", type=str, default="INFO",
                        help="The verbose level of the server: DEBUG, INFO, WARN, ERROR")

    print(f"Car Emulator build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    boot_strap(args.ip, args.port, args.verbose)
    _app.run_server(debug=True)
