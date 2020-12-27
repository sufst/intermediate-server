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

        self._event_loop = None
        self._on_methods = {protocol.AIPDU: self._on_aipdu, protocol.ACPDU: self._on_acpdu,
                            protocol.AAPDU: self._on_aapdu, protocol.ADPDU: self._on_adpdu,
                            protocol.APPDU: self._on_appdu, protocol.ASPDU: self._on_aspdu,
                            protocol.AMPDU: self._on_ampdu}

        self._xbee = xbee_devices.XBeeDevice(com, baud)
        self._xbee_remote = xbee_devices.RemoteXBeeDevice(self._xbee, xbee_devices.XBee64BitAddress.from_hex_string(
            xbee_mac))

    def __enter__(self) -> Server:
        """
        Enter for use with "with as"
        """
        try:
            self._xbee.open()
            self._xbee.add_data_received_callback(self._xbee_data_receive_cb)
        except serial.SerialException:
            self._logger.warning(f"Unable to connect to Xbee device {self._com}:{self._baud}")
        return self

    def _on_async_xbee_data_handle_done(self, future: asyncio.Future) -> None:
        """
        Invoked once the _handle_receive has finished as a result of an xbee received message.
        Used to handle sending any response back to the XBee.
        :param future:  The done future.
        """
        out = future.result()
        self._logger.info(f"XBee message handle done with outcome {out}")
        if out is not None:
            self._logger.info(f"Xbee <- {out}")
            self._xbee.send_data_async(self._xbee_remote, out)

    def _xbee_data_receive_cb(self, message: xbee_message.XBeeMessage) -> None:
        """
        XBee call back function for when xbee data is received.
        NOTE: This is called from an XBee library thread and not the server thread.
        :param message: The received message.
        """
        data = bytes(message.data)
        self._logger.info(f"XBee -> {data}")

        asyncio.run_coroutine_threadsafe(self._handle_receive(data), self._event_loop).add_done_callback(
            self._on_async_xbee_data_handle_done)

    def _on_aipdu(self, aipdu: protocol.ProtocolAIPDU) -> Optional[bytes]:
        """
        Handle a received AIPDU frame.
        :param aipdu:   The received AIPDU frame.
        """
        self._logger.info("Got frame AIPDU")
        return aipdu.pack_raw()

    def _on_acpdu(self, acpdu: protocol.ProtocolACPDU) -> Optional[bytes]:
        """
        Handle a received ACPDU frame.
        :param acpdu:   The received ACPDU frame.
        """
        self._logger.info("Got frame ACPDU")
        return None

    def _on_aapdu(self, aapdu: protocol.ProtocolAAPDU) -> Optional[bytes]:
        """
        Handle a received AAPDU frame.
        :param aapdu:   The received AAPDU frame.
        """
        self._logger.info("Got frame AAPDU")
        return None

    def _on_adpdu(self, adpdu: protocol.ProtocolADPDU) -> Optional[bytes]:
        """
        Handle a received ADPDU frame.
        :param adpdu:   The received ADPDU frame.
        """
        self._logger.info("Got frame ADPDU")
        return None

    def _on_appdu(self, appdu: protocol.ProtocolAPPDU) -> Optional[bytes]:
        """
        Handle a received APPDU frame.
        :param appdu:   The received APPDU frame.
        """
        self._logger.info("Got frame APPDU")
        return None

    def _on_aspdu(self, aspdu: protocol.ProtocolASPDU) -> Optional[bytes]:
        """
        Handle a received ASPDU frame.
        :param aspdu:   The received ASPDU frame.
        """
        self._logger.info("Got frame ASPDU")
        return None

    def _on_ampdu(self, ampdu: protocol.ProtocolAMPDU) -> Optional[bytes]:
        """
        Handle a received AMPDU frame.
        :param ampdu:   The received AMPDU frame.
        """
        self._logger.info("Got frame AMPDU")
        return None

    def run(self) -> None:
        """
        Run the server asyncio loop
        """
        asyncio.run(self._loop())

    async def _handle_receive(self, factory: protocol_factory.ProtocolFactory, frame: bytes) -> Optional[bytes]:
        """
        Handle a received frame asynchronously. This could be from either the XBee receive callback or from the
        server protocol factory.
        :param frame: The received frame.
        """
        self._logger.info(f"Handling data {frame} from factory {factory.__hash__()}")

        pdu = protocol.get_frame_from_buffer(frame)
        if pdu is not None:
            self._logger.info(str(pdu))
            if pdu.header.frame_type in self._on_methods:
                return self._on_methods[pdu.header.frame_type](pdu)
        else:
            self._logger.error("Failed to decode frame from buffer")

    async def _handle_connection_made(self, factory: protocol_factory.ProtocolFactory) -> Optional[bytes]:
        """
        Invoked when the protocol factory has made a new connection.
        :param factory: The factory corresponding to the new connection.
        """
        self._logger.info(f"Handling new connection with factory hash {factory.__hash__()}")

        return None

    async def _handle_connection_lost(self, factory: protocol_factory.ProtocolFactory, exc: Optional[Exception]) \
            -> Optional[bytes]:
        """
        Invoked when the protocol factory has made a new connection.
        :param exc:     Any exception that caused the connection lost.
        :param factory: The factory corresponding to the new connection.
        """
        self._logger.info(f"Factory {factory.__hash__()} lost connection")
        if exc is not None:
            self._logger.info(repr(exc))

        return None

    async def _loop(self) -> None:
        """
        The asyncio event loop for the server.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()

        self._logger.info(f"Creating server {self._ip}:{self._port}")
        server_factory = await self._event_loop.create_server(
            lambda: protocol_factory.ProtocolFactory(self._handle_connection_made, self._handle_receive,
                                                     self._handle_connection_lost, self._verbose), self._ip, self._port)

        self._logger.info(f"Server created")
        async with server_factory:
            await server_factory.serve_forever()

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

        if self._xbee.is_open():
            self._xbee.close()


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
