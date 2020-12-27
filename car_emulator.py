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
from typing import Optional
import common
import protocol
import argparse
import asyncio
import logging
import datetime

_SW_VERSION = 10000


class Client:
    class _ClientProtocolFactory(asyncio.Protocol):
        def __init__(self, on_con_lost: asyncio.Future, logger: logging.Logger):
            """
            Initialise the asyncio Protocol class.
            See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.
            :param verbose:
            """
            self._on_con_lost = on_con_lost
            self._logger = logger
            self._transport = None
            self._seq_num = 1

            self._aipdu = protocol.ProtocolAIPDU()
            self._acpdu = protocol.ProtocolACPDU()
            self._aapdu = protocol.ProtocolAAPDU()
            self._adpdu = protocol.ProtocolADPDU()
            self._appdu = protocol.ProtocolAPPDU()
            self._aspdu = protocol.ProtocolASPDU()
            self._ampdu = protocol.ProtocolAMPDU()

        def connection_made(self, transport: asyncio.Transport) -> None:
            """
            Invoked when the connection is made.
            :param transport:   The asyncio transport instance.
            """
            self._transport = transport
            self._logger.info("Connection made")

            out = self._get_aipdu_raw()

            self._logger.info(f"<- {out}")
            self._transport.write(out)

        async def _periodic_pdu_transmit(self):
            await asyncio.sleep(1)
            out = self._get_acpdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            await asyncio.sleep(1)
            out = self._get_aapdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            await asyncio.sleep(1)
            out = self._get_adpdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            await asyncio.sleep(1)
            out = self._get_appdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            await asyncio.sleep(1)
            out = self._get_aspdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            await asyncio.sleep(1)
            out = self._get_ampdu_raw()
            self._logger.info(f"<- {out}")
            self._transport.write(out)

            asyncio.create_task(self._periodic_pdu_transmit())

        def _get_aipdu_raw(self) -> bytes:
            """
            Get an AIPDU frame in raw format.
            """
            self._aipdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._aipdu.header.epoch = int((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

            self._aipdu.client_type = protocol.CAR_EMULATOR
            self._aipdu.sw_ver = _SW_VERSION
            self._aipdu.client_name = "emulator"

            out = self._aipdu.pack_raw()
            self._logger.info(f"{str(self._aipdu)}")

            return out

        def _get_acpdu_raw(self) -> bytes:
            """
            Get an ACPDU frame in raw format.
            """
            self._acpdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._acpdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._acpdu.rpm += 1
            self._acpdu.water_temp += 1
            self._acpdu.tps_perc += 1
            self._acpdu.battery_mv += 1
            self._acpdu.external_5v_mv += 1
            self._acpdu.fuel_flow += 1
            self._acpdu.lambda_val += 1
            self._acpdu.speed_kph += 1

            out = self._acpdu.pack_raw()
            self._logger.info(f"{str(self._acpdu)}")

            return out

        def _get_aapdu_raw(self) -> bytes:
            """
            Get an AAPDU frame in raw format.
            """
            self._aapdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._aapdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._aapdu.evo_scanner1 += 1
            self._aapdu.evo_scanner2 += 1
            self._aapdu.evo_scanner3 += 1
            self._aapdu.evo_scanner4 += 1
            self._aapdu.evo_scanner5 += 1
            self._aapdu.evo_scanner6 += 1
            self._aapdu.evo_scanner7 += 1

            out = self._aapdu.pack_raw()
            self._logger.info(f"{str(self._aapdu)}")

            return out

        def _get_adpdu_raw(self) -> bytes:
            """
            Get an ADPDU frame in raw format.
            """
            self._adpdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._adpdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._adpdu.ecu_status = protocol.ECU_STATUS_CONNECTED
            self._adpdu.engine_status = protocol.ENGINE_STATUS_IDLE
            self._adpdu.battery_status = protocol.BATTERY_STATUS_HEALTHY
            self._adpdu.car_logging_status = protocol.CAR_LOGGING_STATUS_OFF

            out = self._adpdu.pack_raw()
            self._logger.info(f"{str(self._adpdu)}")

            return out

        def _get_appdu_raw(self) -> bytes:
            """
            Get an APPDU frame in raw format.
            """
            self._appdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._appdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._appdu.injection_time += 1
            self._appdu.injection_duty_cycle += 1
            self._appdu.lambda_pid_adjust += 1
            self._appdu.lambda_pid_target += 1

            out = self._appdu.pack_raw()
            self._logger.info(f"{str(self._appdu)}")

            return out

        def _get_aspdu_raw(self) -> bytes:
            """
            Get an ASPDU frame in raw format.
            """
            self._aspdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._aspdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._aspdu.ride_height_fl_cm += 1
            self._aspdu.ride_height_fr_cm += 1
            self._aspdu.ride_height_flw_cm += 1
            self._aspdu.ride_height_rear_cm += 1

            out = self._aspdu.pack_raw()
            self._logger.info(f"{str(self._aspdu)}")

            return out

        def _get_ampdu_raw(self) -> bytes:
            """
            Get an AMPDU frame in raw format.
            """
            self._ampdu.header.seq_num = self._seq_num
            self._seq_num += 1
            now = datetime.datetime.now()
            self._ampdu.header.epoch = int(
                (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
            self._ampdu.lap_timer_s += 1
            self._ampdu.accel_fl_x_mg += 1
            self._ampdu.accel_fl_y_mg += 1
            self._ampdu.accel_fl_z_mg += 1

            out = self._ampdu.pack_raw()
            self._logger.info(f"{str(self._ampdu)}")

            return out

        def data_received(self, data: bytes) -> None:
            """
            Invoked when data is received.
            :param data:    The received data.
            """
            self._logger.info(f"-> {data}")

            pdu = protocol.get_frame_from_buffer(data)
            if pdu is not None:
                self._logger.info(str(pdu))
                if pdu.header.frame_type == protocol.AIPDU:
                    if pdu == self._aipdu:
                        self._logger.info("AIPDU match")
                        out = self._get_acpdu_raw()

                        self._logger.info(f"<- {out}")
                        self._transport.write(out)
                        asyncio.create_task(self._periodic_pdu_transmit())
                    else:
                        self._logger.error("AIPDU do not match")

        def connection_lost(self, exc):
            self._logger.critical("The server closed the connection")
            self._on_con_lost.set_result(True)

    def __init__(self, ip: str, port: int, com: str, baud: int, mac: str, verbose: str) -> None:
        self._logger = common.get_logger(type(self).__name__, verbose)
        self._ip = ip
        self._port = port
        self._com = com
        self._baud = baud
        self._verbose = verbose

        self._event_loop = None
        self._transport = None
        self._protocol = None
        self._on_con_lost = None

    def __enter__(self) -> Client:
        """
        Enter for use with "with as"
        """
        return self

    def run(self) -> None:
        """
        Run the client asyncio loop
        """
        asyncio.run(self._loop())

    async def _loop(self) -> None:
        """
        The asyncio event loop for the client.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()

        self._logger.info(f"Creating client {self._ip}:{self._port}")

        self._on_con_lost = self._event_loop.create_future()

        self._transport, self._protocol = await self._event_loop.create_connection(
            lambda: self._ClientProtocolFactory(self._on_con_lost, self._logger), self._ip, self._port)

        self._logger.info("Client created")

        try:
            await self._on_con_lost
        finally:
            self._transport.close()

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

    with Client(args.ip, args.port, args.com, args.baud, args.mac, args.verbose) as client:
        client.run()
