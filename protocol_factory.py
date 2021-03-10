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
import asyncio
import serial
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import xml.etree.ElementTree
import common


class ProtocolClient:
    def __init__(self, app_handler: callable):
        """
        Create an instance of the protocol client.

        The protocol client is an abstraction of the underlying protocol client that is in use (Either XBee or socket).
        This abstraction allows the application to interact with the client without having to worry about what
        the client is, through the common API provided here.

        The application should only use the recv() function as the others are intended for the ProtocolFactory to use.
        :param app_handler: The application callable handler for when handling the client.
        """
        self._queue = asyncio.Queue()
        self._app_handler = app_handler

    async def recv(self) -> bytes:
        """
        Await any received data from the client.

        If an error occurred in the client communication, this will be raised as an Exception.
        Designed to be similar to socket recv.
        :return: The bytes objection of received data.
        """
        bytes_in = await self._queue.get()
        if type(bytes_in) == Exception:
            raise bytes_in
        else:
            return bytes_in

    def put(self, item):
        """
        Put an item in the client queue for access by the serving application recv await.
        """
        asyncio.get_running_loop().create_task(self._queue.put(item))

    def connection_made(self):
        """
        Invoked by the client factory when a connection has been successfully made to the client.
        The application handler is invoked with self so the application can make use of recv().
        """
        asyncio.get_running_loop().create_task(self._app_handler(self))


class ProtocolFactorySocket(asyncio.Protocol):
    def __init__(self, client: ProtocolClient):
        """
        Initialise the asyncio Protocol class.
        See https://docs.python.org/3/library/asyncio-protocol.html for details of asyncio protocol and transports.

        The socket events are poked through to the application layer through the ProtocolClient sub class passed.
        The connect made invokes the application serve handler, the data received data is added to the queue, and
        connection lost is added to the queue as an Exception.
        """
        super().__init__()
        self._client = client

    def connection_made(self, transport):
        self._client.connection_made()

    def data_received(self, data: bytes):
        self._client.put(data)

    def connection_lost(self, exc):
        self._client.put(Exception())


class ProtocolFactoryXBee(asyncio.Protocol):
    def __init__(self, com: str, baud: int, mac_peer: str, client: ProtocolClient):
        """
        The XBee protocol factory. It is designed to spoof the asyncio socket factory to standardise the classes
        between these two clients types.

        The XBee events are poked through to the application layer through the ProtocolClient sub class passed.
        The connect made invokes the application serve handler, the data received data is added to the queue, and
        connection lost is added to the queue as an Exception.

        The XBee library it self is ran in another thread as it is not safe to run on the main thread (it doesn't
        play nice with the asyncio event loop). So, when a receive event occurs it is transferred from the
        XBee thread to the main thread for usage.
        :param com: COM port of the XBee.
        :param baud: Baud rate of the XBee.
        :param mac_peer: MAC address of the car.
        """
        self._com = com
        self._baud = baud
        self._mac_peer = mac_peer
        self._client = client
        self._event_loop = asyncio.get_event_loop()

        self._xbee_remote_first_message = True
        self._xbee = xbee_devices.XBeeDevice(self._com, self._baud)
        self._xbee_remote = xbee_devices.RemoteXBeeDevice(self._xbee, xbee_devices.XBee64BitAddress.from_hex_string(
            self._mac_peer))
        try:
            self._xbee.open()
            self._xbee.add_data_received_callback(self._on_xbee_receive)
            self.connection_made()
        except serial.SerialException as err:
            self.connection_lost(err)

    def _on_xbee_receive(self, message: xbee_message.XBeeMessage):
        data = bytes(message.data)

        asyncio.run_coroutine_threadsafe(self._on_xbee_receive_async(data), self._event_loop)

    async def _on_xbee_receive_async(self, data: bytes):
        self.data_received(data)

    def connection_made(self, transport=None):
        self._client.connection_made()

    def data_received(self, data: bytes):
        self._client.put(data)

    def connection_lost(self, exc):
        self._client.put(Exception())


class ProtocolFactory:
    def __init__(self):
        """
        Initialise the Protocol factory.

        The factory configuration in config.xml is used to determine which client to use (XBee or socket).
        Based on the client, the handler callable passed in serve() is invoked with the Client sub class
        which contains a common API to the underlying XBee or socket client that has connected.

        The protocol factory uses asyncio to serve the underlying client.
        """
        self._parse_configuration()

        self._logger = common.get_logger("ProtocolFactory", self._config["verbose"])

        self._logger.info(f"Configuration: {self._config}")

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}

        for field in config_root.iter("factory"):
            for config in field.findall("config"):
                self._config[config.attrib["name"]] = config.text

            for client in field.findall("client"):
                self._config[client.attrib["name"]] = {}
                for config in client.findall("config"):
                    self._config[client.attrib["name"]][config.attrib["name"]] = config.text

        assert("client" in self._config)
        assert("verbose" in self._config)
        assert("XBee" in self._config)
        assert("baud" in self._config["XBee"])
        assert("com" in self._config["XBee"])
        assert("mac" in self._config["XBee"])
        assert("socket" in self._config)
        assert("ip" in self._config["socket"])
        assert("port" in self._config["socket"])

        self._config["XBee"]["baud"] = int(self._config["XBee"]["baud"])
        self._config["socket"]["port"] = int(self._config["socket"]["port"])

    def serve(self, handler: callable) -> None:
        """
        Serve the protocol factory.

        Depending on the client configuration in config.xml, either the XBee client or a socket server for awaiting the
        client is started. When a connection is made to the client the handler callable will be invoked for usage by the
        application.
        :param handler: The application callable handler for handling the protocol client object.
        """
        client = ProtocolClient(handler)

        if self._config["client"] == "socket":
            asyncio.get_event_loop().create_task(
                asyncio.get_event_loop().create_server(lambda: ProtocolFactorySocket(client),
                                                       self._config["socket"]["ip"], self._config["socket"]["port"]))
            self._logger.info(
                f"Await socket client on {self._config['socket']['ip']}:{self._config['socket']['port']}")
        else:
            ProtocolFactoryXBee(
                self._config["XBee"]["com"], self._config["XBee"]["baud"], self._config["XBee"]["mac"], client)
