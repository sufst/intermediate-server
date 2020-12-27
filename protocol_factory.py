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
from typing import Callable

import common
import asyncio


class ProtocolFactory(asyncio.Protocol):
    def __init__(self, async_on_connect: Callable[[ProtocolFactory], asyncio.coroutine],
                 async_on_receive: Callable[[ProtocolFactory, bytes], asyncio.coroutine],
                 async_on_lost: Callable[[ProtocolFactory, Optional[Exception]], asyncio.coroutine],
                 verbose: str) -> None:
        """
        Initialise the asyncio Protocol class.
        See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.
        :param async_on_connect:    An async function for invoking when a new connection is opened and returns any
                                    bytes to send to the new client.
        :param async_on_receive:    An async function for invoking when data is received and returns any bytes to send
                                    back.
        :param async_on_lost:       An async function for invoking when a connection is lost.
        :param verbose:             Verbose level.
        """
        super().__init__()
        self._transport = None
        self._logger = None
        self._verbose = verbose
        self._async_on_receive = async_on_receive
        self._async_on_connect = async_on_connect
        self._async_on_lost = async_on_lost

        self.peer_ip = ""
        self.peer_port = ""

    def _on_async_connect_done(self, future: asyncio.Future) -> None:
        """
        Invoked once the async_receive_cb coroutine has finished and a result is available for any bytes to send back.
        :param future:  The future that is done.
        """
        out = future.result()
        self._logger.debug(f"Connect callback finished with outcome {out}")
        if out is not None:
            self._logger.info(f"<- {out}")
            self._transport.write(out)

    def connection_made(self, transport: asyncio.transports.BaseTransport) -> None:
        """
        Invoked when a new connected is made from a client.
        :param transport:   The transport object corresponding to this new connection.
        """
        self.peer_ip, self.peer_port = transport.get_extra_info("peername")
        self._logger = common.get_logger(f"{self.peer_ip}-{self.peer_port}", self._verbose)
        self._logger.info(f"New connection")
        self._transport = transport
        asyncio.create_task(self._async_on_connect(self)).add_done_callback(self._on_async_connect_done)

    def _on_async_receive_done(self, future: asyncio.Future) -> None:
        """
        Invoked once the async_receive_cb coroutine has finished and a result is available for any bytes to send back.
        :param future:  The future that is done.
        """
        out = future.result()
        self._logger.debug(f"Receive callback finished with outcome {out}")
        if out is not None:
            self._logger.info(f"<- {out}")
            self._transport.write(out)

    def data_received(self, data: bytes) -> None:
        """
        Invoked when data is received from the connected peer.
        :param data:    The received data.
        """
        self._logger.info(f"-> {data}")
        asyncio.create_task(self._async_on_receive(self, data)).add_done_callback(
            self._on_async_receive_done)

    def write(self, data: bytes) -> None:
        """
        Write bytes data to the peer.
        :param data:    Bytes to write.
        """
        self._logger.info(f"<- {data}")
        self._transport.write(data)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when the peer is lost.
        :param exc: An Exception if any occurred.
        """
        self._logger.warning("Lost connection")
        asyncio.create_task(self._async_on_lost(self, exc))

    def __hash__(self) -> int:
        """
        Hash function for getting a unique int representation of the factory for storing in dictionaries or sets.
        """
        # Hash the IP:Port as these are unique to the peer.
        return hash(f"{self.peer_ip}:{self.peer_port}")
