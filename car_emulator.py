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
import asyncio
from typing import Optional

import common
import protocol

_SW_VERSION = 10000
SOCKET, XBEE = list(range(2))
_CLIENT_NAME = "CAR-EMULATOR"


class CarEmulator:
    def __init__(self, ip: str, port: int, com: str, baud: int, xbee_mac: str, emu_type: str, verbose: str) -> None:
        self._logger = common.get_logger(type(self).__name__, verbose)
        self._ip = ip
        self._port = port
        self._com = com
        self._baud = baud
        self._mac = xbee_mac
        if emu_type == "xbee":
            self._emu_type = XBEE
        else:
            self._emu_type = SOCKET
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

        self._rpm = 0
        self._water_temp = 0
        self._tps_perc = 0
        self._battery_mv = 0
        self._external_5v_mv = 0
        self._fuel_flow = 0
        self._lambda_val = 0
        self._speed_kph = 0
        self._evo_scanner1 = 0
        self._evo_scanner2 = 0
        self._evo_scanner3 = 0
        self._evo_scanner4 = 0
        self._evo_scanner5 = 0
        self._evo_scanner6 = 0
        self._evo_scanner7 = 0
        self._ecu_status = 0
        self._engine_status = 0
        self._battery_status = 0
        self._car_logging_status = 0
        self._injection_time = 0
        self._injection_duty_cycle = 0
        self._lambda_pid_adjust = 0
        self._lambda_pid_target = 0
        self._advance = 0
        self._ride_height_fl_cm = 0
        self._ride_height_fr_cm = 0
        self._ride_height_flw_cm = 0
        self._ride_height_rear_cm = 0
        self._lap_timer_s = 0
        self._accel_fl_x_mg = 0
        self._accel_fl_y_mg = 0
        self._accel_fl_z_mg = 0

    def __enter__(self) -> CarEmulator:
        """
        Enter for use with "with as"
        """
        return self

    def run(self) -> None:
        """
        Run the client asyncio loop
        """
        asyncio.run(self._run())

    async def _run(self) -> None:
        """
        The asyncio event loop for the client.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()
        self._on_con_lost = self._event_loop.create_future()

        if self._emu_type == SOCKET:
            self._logger.info(f"Creating client {self._ip}:{self._port}")
            self._protocol = protocol.ProtocolClient(ip=self._ip, port=self._port, callbacks=self._protocol_callbacks,
                                                     client_type=protocol.CAR_EMULATOR, sw_ver=_SW_VERSION,
                                                     client_name=_CLIENT_NAME, event_loop=self._event_loop,
                                                     verbose=self._verbose)
            self._protocol.run()
            try:
                await self._on_con_lost
            finally:
                pass
        else:
            self._logger.info(f"Creating client for XBee link: {self._mac}")

        self._logger.info("Stopped")

    def _on_connection(self, protocol_client: protocol.ProtocolClient) -> None:
        self._logger.info(f"Handling connection ")

    def _on_lost(self, protocol_client: protocol.ProtocolClient, exc: Optional[Exception]) -> None:
        self._logger.info("Handling lost")
        self._on_con_lost.set_result(False)

    def _on_aipdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, client_type: int,
                  sw_ver: int, client_name: str) -> None:
        self._logger.info("Handling AIPDU")
        asyncio.create_task(self.periodic_pdu_transmit(protocol_client))

    def _on_acpdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, rpm: int,
                  water_temp_c: int, tps_perc: int, battery_mv: int, external_5v_mv: int, fuel_flow: int,
                  lambda_value: int, speed_kph: int) -> None:
        self._logger.info("Handling ACPDU")

    def _on_aapdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, evo_scanner1: int,
                  evo_scanner2: int, evo_scanner3: int, evo_scanner4: int, evo_scanner5: int, evo_scanner6: int,
                  evo_scanner7: int) -> None:
        self._logger.info("Handling AAPDU")

    def _on_adpdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, ecu_status: int,
                  engine_status: int, battery_status: int, car_logging_status: int) -> None:
        self._logger.info("Handling ADPDU")

    def _on_appdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, injection_time: int,
                  injection_duty_cycle: int, lambda_pid_adjust: int, lambda_pid_target: int, advance: int) -> None:
        self._logger.info("Handling APPDU")

    def _on_aspdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader,
                  ride_height_fl_cm: int,
                  ride_height_fr_cm: int, ride_height_flw_cm: int, ride_height_rear_cm: int) -> None:
        self._logger.info("Handling ASPDU")

    def _on_ampdu(self, protocol_client: protocol.ProtocolClient, header: protocol.ProtocolHeader, lap_timer_s: int,
                  accel_fl_x_mg: int, accel_fl_y_mg: int, accel_fl_z_mg: int) -> None:
        self._logger.info("Handling AMPDU")

    async def periodic_pdu_transmit(self, client: protocol.ProtocolClient) -> None:
        """
        A recursive function which periodically goes through each frame and writes it.
        """
        await asyncio.sleep(1)
        client.write_acpdu(self._rpm, self._water_temp, self._tps_perc, self._battery_mv, self._external_5v_mv,
                           self._fuel_flow, self._lambda_val, self._speed_kph)
        self._rpm += 1
        self._water_temp += 1
        self._tps_perc += 1
        self._battery_mv += 1
        self._external_5v_mv += 1
        self._fuel_flow += 1
        self._lambda_val += 1
        self._speed_kph += 1

        await asyncio.sleep(1)
        client.write_aapdu(self._evo_scanner1, self._evo_scanner2, self._evo_scanner3, self._evo_scanner4,
                           self._evo_scanner5, self._evo_scanner6, self._evo_scanner7)
        self._evo_scanner1 += 1
        self._evo_scanner2 += 1
        self._evo_scanner3 += 1
        self._evo_scanner4 += 1
        self._evo_scanner5 += 1
        self._evo_scanner6 += 1
        self._evo_scanner7 += 1

        await asyncio.sleep(1)
        client.write_adpdu(self._ecu_status, self._engine_status, self._battery_status, self._car_logging_status)
        self._ecu_status = protocol.ECU_STATUS_CONNECTED
        self._engine_status = protocol.ENGINE_STATUS_IDLE
        self._battery_status = protocol.BATTERY_STATUS_HEALTHY
        self._car_logging_status = protocol.CAR_LOGGING_STATUS_OFF

        await asyncio.sleep(1)
        client.write_appdu(self._injection_time, self._injection_duty_cycle, self._lambda_pid_adjust,
                           self._lambda_pid_target, self._advance)
        self._injection_time += 1
        self._injection_duty_cycle += 1
        self._lambda_pid_adjust += 1
        self._lambda_pid_target += 1
        self._advance += 1

        await asyncio.sleep(1)
        client.write_aspdu(self._ride_height_fl_cm, self._ride_height_fr_cm, self._ride_height_flw_cm,
                           self._ride_height_rear_cm)
        self._ride_height_fl_cm += 1
        self._ride_height_fr_cm += 1
        self._ride_height_flw_cm += 1
        self._ride_height_rear_cm += 1

        await asyncio.sleep(1)
        client.write_ampdu(self._lap_timer_s, self._accel_fl_x_mg, self._accel_fl_y_mg, self._accel_fl_z_mg)
        self._lap_timer_s += 1
        self._accel_fl_x_mg += 1
        self._accel_fl_y_mg += 1
        self._accel_fl_z_mg += 1

        asyncio.create_task(self.periodic_pdu_transmit(client))

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
    parser.add_argument("--type", type=str, default="sockets", help="Type of emulation to do sockets or xbee")

    print(f"Car Emulator build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    with CarEmulator(args.ip, args.port, args.com, args.baud, args.mac, args.type, args.verbose) as emulator:
        emulator.run()
