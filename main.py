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

import common
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import asyncio


class Server:
    class _ServerProtocolFactory(asyncio.Protocol):
        def __init__(self, async_recv_cb: Callable[[bytes], asyncio.coroutine], verbose: str) -> None:
            """
            Initialise the asyncio Protocol class.
            See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.
            :param verbose:
            """
            super().__init__()
            self._transport = None
            self._logger = None
            self._peer_ip = ""
            self._peer_port = ""
            self._verbose = verbose
            self._async_recv_cb = async_recv_cb

        def connection_made(self, transport: asyncio.transports.BaseTransport) -> None:
            """
            Invoked when a new connected is made from a client.
            :param transport:   The transport object corresponding to this new connection.
            """
            self._peer_ip, self._peer_port = transport.get_extra_info("peername")
            self._logger = common.get_logger(f"{self._peer_ip}-{self._peer_port}", self._verbose)
            self._logger.info(f"New connection")
            self._transport = transport

        def _on_async_recv_cb_done(self, future: asyncio.Future) -> None:
            """
            Invoked once the _on_async_recv_cb_done coroutine has finished.
            This means when _handle_recv has finished handling the frame and returns a byte array (or None) to send back
            to the peer.
            :param future:  The future that is done.
            """
            out = future.result()
            self._logger.debug(f"Recv callback finished with outcome {out}")
            if out is not None:
                self._logger.info(f"<- {out}")
                self._transport.write(out)

        def data_received(self, data: bytes) -> None:
            """
            Invoked when data is received from the connected peer.
            :param data:    The received data.
            """
            self._logger.info(f"-> {data}")
            asyncio.create_task(self._async_recv_cb(data)).add_done_callback(self._on_async_recv_cb_done)

        def connection_lost(self, exc: Optional[Exception]) -> None:
            """
            Invoked when the peer is lost.
            :param exc: An Exception if any occurred.
            """
            self._logger.warning("Lost connection")
            if exc is not None:
                self._logger.error(f"{repr(exc)}")

            del self

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

        self._xbee = xbee_devices.XBeeDevice(com, baud)
        self._xbee_remote = xbee_devices.RemoteXBeeDevice(self._xbee, xbee_devices.XBee64BitAddress.from_hex_string(
            xbee_mac))

    def __enter__(self) -> Server:
        """
        Enter for use with "with as"
        :return:
        """
        self._xbee.open()
        self._xbee.add_data_received_callback(self._xbee_data_recv_cb)
        return self

    def _on_async_xbee_data_handle_done(self, future: asyncio.Future) -> None:
        """
        Invoked once the _handle_recv has finished as a result of an xbee received message.
        Used to handle sending any response back to the XBee.
        :param future:  The done future.
        """
        out = future.result()
        self._logger.info(f"XBee message handle done with outcome {out}")
        if out is not None:
            self._logger.info(f"Xbee <- {out}")
            self._xbee.send_data_async(self._xbee_remote, out)

    def _xbee_data_recv_cb(self, message: xbee_message.XBeeMessage) -> None:
        """
        XBee call back function for when xbee data is received.
        NOTE: This is called from an XBee library thread and not the server thread.
        :param message: The received message.
        """
        data = bytes(message.data)
        self._logger.info(f"XBee -> {data}")

        asyncio.run_coroutine_threadsafe(self._handle_recv(data), self._event_loop).add_done_callback(
            self._on_async_xbee_data_handle_done)

    async def _handle_recv(self, frame: bytes) -> Optional[bytes]:
        """
        Handle a received frame asynchronously. This could be from either the XBee receive callback or from the
        server protocol factory.
        :param frame: The received frame.
        """
        self._logger.info(f"Handling raw frame: {frame}")

        return frame

    def run(self) -> None:
        """
        Run the server asyncio loop
        """
        asyncio.run(self._loop())

    async def _loop(self) -> None:
        """
        The asyncio event loop for the server.
        """
        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()

        self._logger.info(f"Creating server {self._ip}:{self._port}")
        server_factory = await self._event_loop.create_server(
            lambda: self._ServerProtocolFactory(self._handle_recv, self._verbose), self._ip, self._port)

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

    print("Intermediate Server  Copyright (C) 2020  Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    with Server(args.ip, args.port, args.com, args.baud, args.mac, args.verbose) as server:
        server.run()
