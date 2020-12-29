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
import argparse
from typing import Optional
from typing import Callable
import serial

import common
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import asyncio
import protocol
import protocol_factory

_SW_VERSION = 10000


class Server:
    def __init__(self, ip: str, port: int, com: str, baud: int, xbee_mac: str, verbose: str) -> None:
        """
        Initialise the Server singleton instance.
        :param ip:      IP to host the server on.
        :param port:    Port to host the server on.
        :param com:     Com port of the attached XBee device.
        :param baud:    Baud rate of the attached XBee device.
        :param verbose: Logger verbose level.
        """
        self._logger = common.get_logger(type(self).__name__, verbose)
        self._ip = ip
        self._port = port
        self._com = com
        self._baud = baud
        self._verbose = verbose

        self._protocol = None
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

        self._event_loop = None
        self._on_stop = None

    def __enter__(self) -> Server:
        """
        Enter for use with "with as"
        """
        return self

    def _on_connection(self, factory: protocol_factory.ProtocolFactoryBase) -> None:
        """
        Invoked when a factory has made a new connection.
        :param factory: The factory that has a new connection.
        """
        self._logger.info(f"Handling connection from factory {factory.__hash__()}")

    def _on_lost(self, factory: protocol_factory.ProtocolFactoryBase, exc: Optional[Exception]) -> None:
        """
        Invoked when a factory has lost its connection.
        :param factory: The factory that has lost its connection.
        :param exc:     Any error that caused the lost.
        """
        self._logger.info(f"Handling lost from factory {factory.__hash__()}")

    def _on_aipdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  client_type: int, sw_ver: int, client_name: str) -> None:
        """
        Invoked when a factory has received a AIPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling AIPDU from factory {factory.__hash__()}")
        self._protocol.write_aipdu(factory, client_type, sw_ver, client_name)

    def _on_acpdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader, rpm: int,
                  water_temp_c: int, tps_perc: int, battery_mv: int, external_5v_mv: int, fuel_flow: int,
                  lambda_value: int, speed_kph: int) -> None:
        """
        Invoked when a factory has received a ACPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling ACPDU from factory {factory.__hash__()}")

    def _on_aapdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  evo_scanner1: int,
                  evo_scanner2: int, evo_scanner3: int, evo_scanner4: int, evo_scanner5: int, evo_scanner6: int,
                  evo_scanner7: int) -> None:
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
                  injection_time: int,
                  injection_duty_cycle: int, lambda_pid_adjust: int, lambda_pid_target: int, advance: int) -> None:
        """
        Invoked when a factory has received a APPDU frame.
        :param factory: The factory that received the frame.
        """
        self._logger.info(f"Handling APPDU from factory {factory.__hash__()}")

    def _on_aspdu(self, factory: protocol_factory.ProtocolFactoryBase, header: protocol.ProtocolHeader,
                  ride_height_fl_cm: int,
                  ride_height_fr_cm: int, ride_height_flw_cm: int, ride_height_rear_cm: int) -> None:
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

    def run(self) -> None:
        """
        Run the server asyncio loop
        """
        asyncio.run(self._run())

    async def _run(self) -> asyncio.coroutine:
        """
        The asyncio event loop for the server.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()
        self._on_stop = asyncio.Future()

        self._logger.info(f"Creating Protocol {self._ip}:{self._port}")
        self._protocol = protocol.Protocol(ip=self._ip, port=self._port, com="COM4", baud=115200,
                                           mac="0013A20041559318", callbacks=self._protocol_callbacks,
                                           protocol_type=protocol.SERVER, event_loop=self._event_loop,
                                           verbose=self._verbose)
        self._protocol.run()

        try:
            await self._on_stop
        finally:
            self._logger.info("Stopped")

    def __exit__(self, exc_type: Optional[Exception], exc_val: Optional[Exception], exc_tb: Optional[Exception]) \
            -> None:
        """
        Exit for use with "with as"
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        """
        if exc_type is not None:
            self._logger.error(f"{exc_type}\n{exc_val}\n{exc_tb}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an intermediate server.")

    parser.add_argument("--port", type=int, default=19900, help="The port to host the server on.")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="The IP address to host the server on.")
    parser.add_argument("--verbose", type=str, default="INFO",
                        help="The verbose level of the server: DEBUG, INFO, WARN, ERROR")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate for the attached XBee.")
    parser.add_argument("--com", type=str, default="COM0", help="Com port for the attached XBee e.g. COM1")
    parser.add_argument("--mac", type=str, default="FFFFFFFFFFFFFFFF", help="MAC address of car XBee.")

    print(f"Intermediate Server build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    with Server(args.ip, args.port, args.com, args.baud, args.mac, args.verbose) as server:
        server.run()
