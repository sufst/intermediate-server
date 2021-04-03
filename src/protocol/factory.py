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


class Socket(asyncio.Protocol):
    def __init__(self, protocol):
        self.protocol = protocol

    def connection_made(self, transport):
        self.protocol.connection_made()

    def data_received(self, data):
        self.protocol.data_received(data)

    def connection_lost(self, exc):
        self.protocol.connection_lost(exc)


class XBee:
    def __init__(self, com, baud, mac_peer, protocol):
        self.com = com
        self.baud = baud
        self.mac_peer = mac_peer
        self.protocol = protocol
        self.event_loop = asyncio.get_event_loop()

        self.xbee = xbee_devices.XBeeDevice(self.com, self.baud)
        self.xbee_remote = xbee_devices.RemoteXBeeDevice(
            self.xbee,
            xbee_devices.XBee64BitAddress.from_hex_string(self.mac_peer)
        )
        try:
            self.xbee.open()
            self.xbee.add_data_received_callback(self._on_xbee_receive)
            self.connection_made()
        except serial.SerialException as err:
            self.connection_lost(err)

    def _on_xbee_receive(self, message: xbee_message.XBeeMessage):
        data = bytes(message.data)

        asyncio.run_coroutine_threadsafe(self._on_xbee_receive_async(data), self.event_loop)

    async def _on_xbee_receive_async(self, data: bytes):
        self.data_received(data)

    def connection_made(self):
        self.protocol.connection_made()

    def data_received(self, data: bytes):
        self.protocol.data_received(data)

    def connection_lost(self, exc):
        self.protocol.put(exc)
