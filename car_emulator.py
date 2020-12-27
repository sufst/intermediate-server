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
import datetime
import logging
from typing import Optional

import common
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import protocol

_SW_VERSION = 10000
SOCKET, XBEE = list(range(2))


class Client:
    class _ClientProtocolFactory(asyncio.Protocol):
        def __init__(self, on_con_lost: asyncio.Future, client_master: Client, logger_handle: logging.Logger):
            """
            Initialise the asyncio Protocol class.
            See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.
            :param logger_handle:  Logger to log to.
            """
            self._on_con_lost = on_con_lost
            self._logger = logger_handle
            self._transport = None
            self._seq_num = 1
            self._master = client_master

        def connection_made(self, transport: asyncio.Transport) -> None:
            """
            Invoked when the connection is made.
            :param transport:   The asyncio transport instance.
            """
            self._transport = transport
            self._logger.info("Connection made")

            out = self._master.get_aipdu_raw()

            self._logger.info(f"<- {out}")
            self._transport.write(out)

        def data_received(self, data: bytes) -> None:
            """
            Invoked when data is received.
            :param data:    The received data.
            """
            self._logger.info(f"-> {data}")
            
            asyncio.create_task(self._master.handle_recv(data))

        def connection_lost(self, exc):
            self._logger.critical("The server closed the connection")
            self._on_con_lost.set_result(True)

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

        self._event_loop = None
        self._transport = None
        self._protocol = None
        self._on_con_lost = None
        self._on_methods = {protocol.AIPDU: self._on_aipdu, protocol.ACPDU: self._onacpdu,
                            protocol.AAPDU: self._onaapdu, protocol.ADPDU: self._onadpdu,
                            protocol.APPDU: self._onappdu, protocol.ASPDU: self._onaspdu,
                            protocol.AMPDU: self._onaspdu}

        self.aipdu = protocol.ProtocolAIPDU()
        self.acpdu = protocol.ProtocolACPDU()
        self.aapdu = protocol.ProtocolAAPDU()
        self.adpdu = protocol.ProtocolADPDU()
        self.appdu = protocol.ProtocolAPPDU()
        self.aspdu = protocol.ProtocolASPDU()
        self.ampdu = protocol.ProtocolAMPDU()
        self._seq_num = 0

        if self._emu_type == XBEE:
            self._xbee = xbee_devices.XBeeDevice(com, baud)
            self._xbee_remote = xbee_devices.RemoteXBeeDevice(self._xbee, xbee_devices.XBee64BitAddress.from_hex_string(
                xbee_mac))

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
        self._on_con_lost = self._event_loop.create_future()

        if self._emu_type == SOCKET:
            self._logger.info(f"Creating client {self._ip}:{self._port}")

            self._transport, self._protocol = await self._event_loop.create_connection(
                lambda: self._ClientProtocolFactory(self._on_con_lost, self, self._logger), self._ip, self._port)

            self._logger.info("Client created")

            try:
                await self._on_con_lost
            finally:
                self._transport.close()
        else:
            self._logger.info(f"Creating client for XBee link: {self._mac}")

            self._xbee.open()
            self._xbee.add_data_received_callback(self._xbee_data_recv_cb)

            out = self.get_aipdu_raw()
            self._write(out)
            try:
                await self._on_con_lost
            finally:
                self._xbee.close()
        self._logger.info("Stopped")

    def _write(self, buffer: bytes):
        if self._emu_type == SOCKET:
            self._logger.info(f"socket <- {buffer}")
            self._transport.write(buffer)
        else:
            self._logger.info(f"xbee <- {buffer}")
            self._xbee.send_data_async(self._xbee_remote, buffer)

    async def periodic_pdu_transmit(self):
        await asyncio.sleep(1)
        out = self.getacpdu_raw()
        self._write(out)

        await asyncio.sleep(1)
        out = self.getaapdu_raw()
        self._write(out)

        await asyncio.sleep(1)
        out = self.getadpdu_raw()
        self._write(out)

        await asyncio.sleep(1)
        out = self.getappdu_raw()
        self._write(out)

        await asyncio.sleep(1)
        out = self.getaspdu_raw()
        self._write(out)

        await asyncio.sleep(1)
        out = self.getampdu_raw()
        self._write(out)

        asyncio.create_task(self.periodic_pdu_transmit())

    def get_aipdu_raw(self) -> bytes:
        """
        Get an AIPDU frame in raw format.
        """
        self.aipdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.aipdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

        self.aipdu.client_type = protocol.CAR_EMULATOR
        self.aipdu.sw_ver = _SW_VERSION
        self.aipdu.client_name = "emulator"

        out = self.aipdu.pack_raw()
        self._logger.info(f"{str(self.aipdu)}")

        return out

    def getacpdu_raw(self) -> bytes:
        """
        Get an ACPDU frame in raw format.
        """
        self.acpdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.acpdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.acpdu.rpm += 1
        self.acpdu.water_temp += 1
        self.acpdu.tps_perc += 1
        self.acpdu.battery_mv += 1
        self.acpdu.external_5v_mv += 1
        self.acpdu.fuel_flow += 1
        self.acpdu.lambda_val += 1
        self.acpdu.speed_kph += 1

        out = self.acpdu.pack_raw()
        self._logger.info(f"{str(self.acpdu)}")

        return out

    def getaapdu_raw(self) -> bytes:
        """
        Get an AAPDU frame in raw format.
        """
        self.aapdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.aapdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.aapdu.evo_scanner1 += 1
        self.aapdu.evo_scanner2 += 1
        self.aapdu.evo_scanner3 += 1
        self.aapdu.evo_scanner4 += 1
        self.aapdu.evo_scanner5 += 1
        self.aapdu.evo_scanner6 += 1
        self.aapdu.evo_scanner7 += 1

        out = self.aapdu.pack_raw()
        self._logger.info(f"{str(self.aapdu)}")

        return out

    def getadpdu_raw(self) -> bytes:
        """
        Get an ADPDU frame in raw format.
        """
        self.adpdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.adpdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.adpdu.ecu_status = protocol.ECU_STATUS_CONNECTED
        self.adpdu.engine_status = protocol.ENGINE_STATUS_IDLE
        self.adpdu.battery_status = protocol.BATTERY_STATUS_HEALTHY
        self.adpdu.car_logging_status = protocol.CAR_LOGGING_STATUS_OFF

        out = self.adpdu.pack_raw()
        self._logger.info(f"{str(self.adpdu)}")

        return out

    def getappdu_raw(self) -> bytes:
        """
        Get an APPDU frame in raw format.
        """
        self.appdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.appdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.appdu.injection_time += 1
        self.appdu.injection_duty_cycle += 1
        self.appdu.lambda_pid_adjust += 1
        self.appdu.lambda_pid_target += 1

        out = self.appdu.pack_raw()
        self._logger.info(f"{str(self.appdu)}")

        return out

    def getaspdu_raw(self) -> bytes:
        """
        Get an ASPDU frame in raw format.
        """
        self.aspdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.aspdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.aspdu.ride_height_fl_cm += 1
        self.aspdu.ride_height_fr_cm += 1
        self.aspdu.ride_height_flw_cm += 1
        self.aspdu.ride_height_rear_cm += 1

        out = self.aspdu.pack_raw()
        self._logger.info(f"{str(self.aspdu)}")

        return out

    def getampdu_raw(self) -> bytes:
        """
        Get an AMPDU frame in raw format.
        """
        self.ampdu.header.seq_num = self._seq_num
        self._seq_num += 1
        now = datetime.datetime.now()
        self.ampdu.header.epoch = int(
            (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
        self.ampdu.lap_timer_s += 1
        self.ampdu.accel_fl_x_mg += 1
        self.ampdu.accel_fl_y_mg += 1
        self.ampdu.accel_fl_z_mg += 1

        out = self.ampdu.pack_raw()
        self._logger.info(f"{str(self.ampdu)}")

        return out

    def _on_async_xbee_data_handle_done(self, future: asyncio.Future) -> None:
        """
        Invoked once the handle_recv has finished as a result of an xbee received message.
        Used to handle sending any response back to the XBee.
        :param future:  The done future.
        """
        out = future.result()
        self._logger.info(f"XBee message handle done with outcome {out}")
        if out is not None:
            self._write(out)

    def _xbee_data_recv_cb(self, message: xbee_message.XBeeMessage) -> None:
        """
        XBee call back function for when xbee data is received.
        NOTE: This is called from an XBee library thread and not the server thread.
        :param message: The received message.
        """
        data = bytes(message.data)
        self._logger.info(f"XBee -> {data}")

        asyncio.run_coroutine_threadsafe(self.handle_recv(data), self._event_loop).add_done_callback(
            self._on_async_xbee_data_handle_done)

    async def handle_recv(self, frame: bytes) -> Optional[bytes]:
        """
        Handle an XBee received frame asynchronously.
        :param frame: The received frame.
        """
        self._logger.info(f"Handling raw frame: {frame}")

        pdu = protocol.get_frame_from_buffer(frame)
        if pdu is not None:
            self._logger.info(str(pdu))
            if pdu.header.frame_type in self._on_methods:
                return self._on_methods[pdu.header.frame_type](pdu)
        else:
            self._logger.error("Failed to decode frame from buffer")

    def _on_aipdu(self, aipdu: protocol.ProtocolAIPDU) -> Optional[bytes]:
        """
        Handle a received AIPDU frame.
        :param aipdu:   The received AIPDU frame.
        """
        self._logger.info("Got frame AIPDU")
        if aipdu == self.aipdu:
            self._logger.info("AIPDU match")
            asyncio.create_task(self.periodic_pdu_transmit())
        else:
            self._logger.error("AIPDU do not match")
        return None

    def _onacpdu(self, acpdu: protocol.ProtocolACPDU) -> Optional[bytes]:
        """
        Handle a received ACPDU frame.
        :param acpdu:   The received ACPDU frame.
        """
        self._logger.info("Got frame ACPDU")
        return None

    def _onaapdu(self, aapdu: protocol.ProtocolAAPDU) -> Optional[bytes]:
        """
        Handle a received AAPDU frame.
        :param aapdu:   The received AAPDU frame.
        """
        self._logger.info("Got frame AAPDU")
        return None

    def _onadpdu(self, adpdu: protocol.ProtocolADPDU) -> Optional[bytes]:
        """
        Handle a received ADPDU frame.
        :param adpdu:   The received ADPDU frame.
        """
        self._logger.info("Got frame ADPDU")
        return None

    def _onappdu(self, appdu: protocol.ProtocolAPPDU) -> Optional[bytes]:
        """
        Handle a received APPDU frame.
        :param appdu:   The received APPDU frame.
        """
        self._logger.info("Got frame APPDU")
        return None

    def _onaspdu(self, aspdu: protocol.ProtocolASPDU) -> Optional[bytes]:
        """
        Handle a received ASPDU frame.
        :param aspdu:   The received ASPDU frame.
        """
        self._logger.info("Got frame ASPDU")
        return None

    def _onampdu(self, ampdu: protocol.ProtocolAMPDU) -> Optional[bytes]:
        """
        Handle a received AMPDU frame.
        :param ampdu:   The received AMPDU frame.
        """
        self._logger.info("Got frame AMPDU")
        return None

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

    print(f"Intermediate Server build {_SW_VERSION} Copyright (C) 2020 Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    with Client(args.ip, args.port, args.com, args.baud, args.mac, args.type, args.verbose) as client:
        client.run()
