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
from src.helpers import config
import functools
import asyncio
import serial
from digi.xbee import devices as xbee_devices
from digi.xbee.models import message as xbee_message
import struct

_event_handlers = {}
_pdus = {}
_conf = config.config['schema']


class _PDU:
    def __init__(self, name, header, body):
        self.name = name
        self.length = 0
        self._header = header
        self._body = body
        self._fields_names = []
        self.fields = {}

        self._struct_format = "<"

        c_type_lengths = {"c": 1, "b": 1, "B": 1, "?": 1, "h": 2, "H": 2, "i": 4, "I": 4,
                          "l": 4, "L": 4, "f": 4, "d": 4, "q": 8, "Q": 8}

        for entry in self._header + self._body:
            self._fields_names.extend([entry['name']])
            self.length += c_type_lengths[entry['cType']]
            self._struct_format += entry['cType']

        # Remove the valid_bitfield field.
        self._fields_names = self._fields_names[1:]

    def decode(self, bytes_in):
        unpacked = struct.unpack(self._struct_format, bytes_in)
        values = iter(struct.unpack(self._struct_format, bytes_in))
        print(unpacked)
        # The first value should be the valid bitfield.
        valid_bitfield = next(values)
        print(f"valid field is : {valid_bitfield}")

        # Create an array of valid fields in the PDU
        valid_fields = []
        for i in range(0, len(self._fields_names)):
            print(f"field names: {self._fields_names}")
            if (valid_bitfield >> i) & 1:
                print(f"valid bitfields {valid_bitfield}")
                valid_fields.extend([self._fields_names[i]])

        for field in self._fields_names:
            if field in valid_fields:
                self.fields[field] = next(values)
            else:
                next(values)


class _Socket(asyncio.Protocol):
    def connection_made(self, transport):
        if "connect" in _event_handlers:
            _event_handlers["connect"]()

    def data_received(self, data):
        try:
            _parse_data(data)
        except Exception as error:
            print(f'Schema parse error: {error}')

    def connection_lost(self, exc):
        if "disconnect" in _event_handlers:
            _event_handlers["disconnect"](exc)


class _XBee:
    def __init__(self, com, baud, mac_peer):
        self.com = com
        self.baud = baud
        self.mac_peer = mac_peer
        self.event_loop = asyncio.get_event_loop()

        self.xbee = xbee_devices.XBeeDevice(self.com, self.baud)
        self.xbee_remote = xbee_devices.RemoteXBeeDevice(
            self.xbee,
            xbee_devices.XBee64BitAddress.from_hex_string(self.mac_peer)
        )
        try:
            self.xbee.open()
            self.xbee.add_expl_data_received_callback(self._on_xbee_receive)
            if "connect" in _event_handlers:
                _event_handlers["connect"]()
        except serial.SerialException as err:
            if "disconnect" in _event_handlers:
                _event_handlers["disconnect"](err)

    def _on_xbee_receive(self, message: xbee_message.XBeeMessage):
        # data = bytes(message.data)
        address = message.remote_device.get_64bit_addr()
        data = message.data[27:]
        # print("Received data from %s: %s" % (address, data))
        # print(data.decode("utf8"))
        asyncio.run_coroutine_threadsafe(self._on_xbee_receive_async(data), self.event_loop)

    @staticmethod
    async def _on_xbee_receive_async(data):
        try:
            _parse_data(data)
        except Exception as error:
            print(error)


def _parse_data(data):
    index = 0
    # while index < len(data):
    if data[index] != config.schema['startByte']:
        print(f"received data index: {index}")
        raise Exception('Invalid start byte')
    index += 1

    pdu_type = data[index]
    if pdu_type in _pdus:
        index += 1
        if _pdus[pdu_type].length > len(data) - index:
            # print(f"expected length: {_pdus[pdu_type].length+index} ")
            # print(f"actual length: {len(data) - index}")
            raise Exception('Invalid data length')
        else:
            _pdus[pdu_type].decode(data[index:index + _pdus[pdu_type].length])
            if 'PDU' in _event_handlers:
                print(f"PDU type is : {pdu_type}")
                print(_event_handlers['PDU'](_pdus[pdu_type].fields))

            index += _pdus[pdu_type].length
    else:
        raise Exception('Invalid PDU type')


def on(event):
    def wrapper(func):
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            func(*args, **kwargs)

        _event_handlers[event] = decorator

        return decorator

    return wrapper


def load():
    for name, conf in config.schema['pdu'].items():
        _pdus[conf['id']] = _PDU(name, conf['header'], conf['body'])

    if _conf['source'] == 'socket':
        asyncio.get_event_loop().create_task(
            asyncio.get_event_loop().create_server(
                _Socket,
                _conf['Host'],
                _conf.getint('Port'))
        )
        print(f'schema socket serving {_conf["Host"]}:{_conf.getint("Port")}')
    else:
        _XBee(_conf['Com'], _conf.getint('Baud'), _conf['Mac'])
        print(f'schema XBee serving {_conf["Com"]}:{_conf.getint("Baud")}')
