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

import asyncio
from typing import Optional

import serial
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message

import common

RAW, JSON = list(range(2))


async def create_client(ip: str, port: int, callbacks: ProtocolFactoryCallbacks, verbose: str,
                        event_loop: asyncio.AbstractEventLoop) -> asyncio.coroutine:
    """
    Create a socket client factory.
    :param ip:          IP to connect to.
    :param port:        Port to connect to.
    :param callbacks:   Callbacks for events.
    :param verbose:     Verbose level for logger.
    :param event_loop:  Event loop to create client on.
    """
    return await event_loop.create_connection(lambda: ProtocolFactorySocket(callbacks, verbose), ip, port)


async def create_server(ip: str, port: int, callbacks: ProtocolFactoryCallbacks, verbose: str,
                        event_loop: asyncio.AbstractEventLoop) -> asyncio.coroutine:
    """
    Create a socket server factory.
    :param ip:          IP to host on.
    :param port:        Port to host on.
    :param callbacks:   Callbacks for events.
    :param verbose:     Verbose level for logger.
    :param event_loop:  Event loop to create server on.
    """
    return await event_loop.create_server(lambda: ProtocolFactorySocket(callbacks, verbose), ip, port)


async def create_xbee(com: str, baud: int, mac_peer: str, callbacks: ProtocolFactoryCallbacks, verbose: str,
                      event_loop: asyncio.AbstractEventLoop) -> asyncio.coroutine:
    """
    Create a xbee client factory.
    :param com:         Com port of XBee to connect to.
    :param baud:        Baud rate of XBee to connect to.
    :param mac_peer:    MAC address of xbee to transmit to.
    :param callbacks:   Callbacks for events.
    :param verbose:     Verbose level for logger.
    :param event_loop:  Event loop to create xbee client on.
    """
    return ProtocolFactoryXBee(com, baud, mac_peer, callbacks, event_loop, verbose)


class ProtocolFactoryCallbacks:
    def on_connection(self, factory: ProtocolFactoryBase) -> None:
        raise NotImplementedError

    def on_lost(self, factory: ProtocolFactoryBase, exc: Optional[Exception]) -> None:
        raise NotImplementedError

    def on_receive(self, factory: ProtocolFactoryBase, data: bytes) -> None:
        raise NotImplementedError


class ProtocolFactoryBase(asyncio.Protocol):
    def connection_made(self, transport: Optional[asyncio.transports.BaseTransport]) -> None:
        raise NotImplementedError

    def data_received(self, data: bytes) -> None:
        raise NotImplementedError

    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def connection_lost(self, exc: Optional[Exception]) -> None:
        raise NotImplementedError

    def get_pdu_format_type(self) -> int:
        raise NotImplementedError

    def set_pdu_format_type(self, pdu_format: int) -> None:
        raise NotImplementedError


class ProtocolFactoryXBee(ProtocolFactoryBase):
    def __init__(self, com: str, baud: int, mac_peer: str, callbacks: ProtocolFactoryCallbacks,
                 event_loop: asyncio.AbstractEventLoop, verbose: str) -> None:
        self._com = com
        self._baud = baud
        self._mac_peer = mac_peer
        self._callbacks = callbacks
        self._event_loop = event_loop
        self._verbose = verbose
        self._logger = common.get_logger(type(self).__name__, verbose)

        self._pdu_format = RAW
        self._xbee_remote_first_message = True
        self._xbee = xbee_devices.XBeeDevice(self._com, self._baud)
        self._xbee_remote = xbee_devices.RemoteXBeeDevice(self._xbee, xbee_devices.XBee64BitAddress.from_hex_string(
            self._mac_peer))
        try:
            self._xbee.open()
            self._xbee.add_data_received_callback(self.on_xbee_receive)
            self.connection_made(None)
        except serial.SerialException:
            self._logger.warning(f"Unable to connect to Xbee device {self._com}:{self._baud}")

    def on_xbee_receive(self, message: xbee_message.XBeeMessage) -> None:
        """
        XBee call back function for when xbee data is received.
        NOTE: This is called from an XBee library thread and not the server thread.
        :param message: The received message.
        """
        data = bytes(message.data)
        self._logger.info(f"XBee -> {data}")

        asyncio.run_coroutine_threadsafe(self.on_xbee_receive_async(data), self._event_loop)

    async def on_xbee_receive_async(self, data: bytes) -> asyncio.coroutine:
        """
        This function is used to get back on the thread the client event loop is running on to invoke the common API
        data_receive.
        :param data:
        """
        self._logger.info(f"Handling xbee data {data}")
        self.data_received(data)

    def connection_made(self, transport: Optional[asyncio.transports.BaseTransport]) -> None:
        """
        Invoked when a new connected is made from a client.
        :param transport:   The transport object corresponding to this new connection.
        """
        self._logger.info(f"New connection")
        self._callbacks.on_connection(self)

    def data_received(self, data: bytes) -> None:
        """
        Invoked when data is received from the connected peer.
        :param data:    The received data.
        """
        self._logger.info(f"-> {data}")
        self._callbacks.on_receive(self, data)

    def write(self, data: bytes) -> None:
        """
        Write bytes data to the peer.
        :param data:    Bytes to write.
        """
        self._logger.info(f"Xbee <- {data}")
        self._xbee.send_data_async(self._xbee_remote, data)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when the peer is lost.
        :param exc: An Exception if any occurred.
        """
        self._callbacks.on_lost(self, exc)

    def get_pdu_format_type(self) -> int:
        """
        Get the PDU format this factory is operating with.
        """
        return self._pdu_format

    def set_pdu_format_type(self, pdu_format: int) -> None:
        """
        Set the PDU format this factory is operating with.
        :param pdu_format:  The pdu format.
        """
        self._pdu_format = pdu_format

    def __hash__(self) -> int:
        """
        Hash function for getting a unique int representation of the factory for storing in dictionaries or sets.
        """
        # Hash the COM:Baud as these are unique to the xbee.
        return hash(f"{self._com}:{self._baud}")


class ProtocolFactorySocket(ProtocolFactoryBase):
    def __init__(self, callbacks: ProtocolFactoryCallbacks, verbose: str) -> None:
        """
        Initialise the asyncio Protocol class.
        See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.
        :param callbacks:   Event callbacks.
        :param verbose:     Verbose level.
        """
        super().__init__()
        self._transport = None
        self._logger = None
        self._verbose = verbose
        self._callbacks = callbacks
        self.peer_ip = ""
        self.peer_port = ""
        self._pdu_format = JSON

    def connection_made(self, transport: asyncio.transports.BaseTransport) -> None:
        """
        Invoked when a new connected is made from a client.
        :param transport:   The transport object corresponding to this new connection.
        """
        self.peer_ip, self.peer_port = transport.get_extra_info("peername")
        self._logger = common.get_logger(f"{self.peer_ip}-{self.peer_port}", self._verbose)
        self._logger.info(f"New connection")
        self._transport = transport
        self._callbacks.on_connection(self)

    def data_received(self, data: bytes) -> None:
        """
        Invoked when data is received from the connected peer.
        :param data:    The received data.
        """
        self._logger.info(f"-> {data}")
        self._callbacks.on_receive(self, data)

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
        self._callbacks.on_lost(self, exc)

    def get_pdu_format_type(self) -> int:
        """
        Get the PDU format this factory is operating with.
        """
        return self._pdu_format

    def set_pdu_format_type(self, pdu_format: int) -> None:
        """
        Set the PDU format this factory is operating with.
        :param pdu_format:  The pdu format.
        """
        self._pdu_format = pdu_format

    def __hash__(self) -> int:
        """
        Hash function for getting a unique int representation of the factory for storing in dictionaries or sets.
        """
        # Hash the IP:Port as these are unique to the peer.
        return hash(f"{self.peer_ip}:{self.peer_port}")
