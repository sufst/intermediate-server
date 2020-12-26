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
import common
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import asyncio


class Server:
    def __init__(self, ip: str, port: int, com: str, baud: int, verbose: str) -> None:
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
        self._event_stop = None

        self._xbee = xbee_devices.XBeeDevice(com, baud)

    def __enter__(self) -> Server:
        """
        Enter for use with "with as"
        :return:
        """
        self._xbee.open()
        self._xbee.add_data_received_callback(self._xbee_data_recv_cb)
        return self

    def _xbee_data_recv_cb(self, message: xbee_message.XBeeMessage) -> None:
        """
        XBee call back function for when xbee data is received.
        NOTE: This is called from an XBee library thread and not the server thread.
        :param message: The received message.
        """
        self._logger.info(f"XBee <- {message.data}")
        asyncio.run_coroutine_threadsafe(self._handle_recv(message.data), self._event_loop)

    async def _handle_recv(self, frame: bytes) -> None:
        """
        Handle a received frame asynchronously. This could be from either the XBee receive callback or from the
        server protocol factory.
        :param frame: The received frame.
        """
        self._logger.info(f"Handling raw frame: {frame}")

    def run(self) -> None:
        """
        Run the server asyncio loop
        """
        asyncio.run(self._loop())

    async def _loop(self) -> None:
        """
        The asyncio event loop for the server.
        """
        self._event_stop = asyncio.Event()

        self._logger.info("Running")
        self._event_loop = asyncio.get_running_loop()
        await self._event_stop.wait()
        self._logger.info("Stopped")

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
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

    print("Intermediate Server  Copyright (C) 2020  Nathan Rowley-Smith\n" +
          "This program comes with ABSOLUTELY NO WARRANTY;\n" +
          "This is free software, and you are welcome to redistribute it")

    args = parser.parse_args()

    logger = common.get_logger("root", "DEBUG")
    logger.info(args.__dict__)

    with Server(args.ip, args.port, args.com, args.baud, args.verbose) as server:
        server.run()
